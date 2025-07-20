"""
Travel Data Parser API - FastAPI Application
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from anthropic import APIError, RateLimitError, APITimeoutError

from app.core.config import settings
from app.core.error_handler import error_handler, ErrorCode
from app.models.requests import FlightParseRequest, LodgingParseRequest
from app.models.responses import ErrorResponse, FlightParseResponse, LodgingParseResponse
from app.services.universal_parser import UniversalParser

# Configure comprehensive logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(context)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Create custom formatter that handles context
class ContextFormatter(logging.Formatter):
    def format(self, record):
        if not hasattr(record, 'context'):
            record.context = '{}'
        else:
            import json
            record.context = json.dumps(record.context) if isinstance(record.context, dict) else str(record.context)
        return super().format(record)

# Apply custom formatter to all handlers
for handler in logging.root.handlers:
    handler.setFormatter(ContextFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s - Context: %(context)s'
    ))

logger = logging.getLogger(__name__)

# Create FastAPI application instance
app = FastAPI(
    title="Travel Data Parser API",
    version="1.0.0",
    description="API for parsing travel booking data from various platforms"
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency injection for UniversalParser
async def get_universal_parser() -> UniversalParser:
    """Dependency to provide UniversalParser instance."""
    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="Anthropic API key not configured"
        )
    
    return UniversalParser(anthropic_api_key=settings.ANTHROPIC_API_KEY)


# Global exception handlers using centralized error handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with centralized error handler."""
    request_id = str(uuid.uuid4())
    
    # Map HTTP status codes to HTTP-specific error codes
    if exc.status_code == 400:
        error_code = ErrorCode.HTTP_400
    elif exc.status_code == 404:
        error_code = ErrorCode.HTTP_404
    elif exc.status_code == 405:
        error_code = ErrorCode.HTTP_405
    elif exc.status_code == 429:
        error_code = ErrorCode.HTTP_429
    elif exc.status_code >= 500:
        error_code = ErrorCode.HTTP_500
    else:
        error_code = ErrorCode.HTTP_500
    
    error_handler.log_error(
        error_code=error_code,
        message=str(exc.detail),
        request=request,
        request_id=request_id,
        additional_context={"http_status_code": exc.status_code}
    )
    
    # Create error response but preserve original HTTP status code
    error_response = error_handler.create_error_response(error_code, str(exc.detail))
    return JSONResponse(
        status_code=exc.status_code,  # Preserve original status code
        content=error_response.model_dump(mode='json')
    )


@app.exception_handler(StarletteHTTPException)
async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle Starlette HTTP exceptions with centralized error handler."""
    request_id = str(uuid.uuid4())
    
    # Map HTTP status codes to HTTP-specific error codes
    if exc.status_code == 400:
        error_code = ErrorCode.HTTP_400
    elif exc.status_code == 404:
        error_code = ErrorCode.HTTP_404
    elif exc.status_code == 405:
        error_code = ErrorCode.HTTP_405
    elif exc.status_code == 429:
        error_code = ErrorCode.HTTP_429
    elif exc.status_code >= 500:
        error_code = ErrorCode.HTTP_500
    else:
        error_code = ErrorCode.HTTP_500
    
    error_handler.log_error(
        error_code=error_code,
        message=str(exc.detail),
        request=request,
        request_id=request_id,
        additional_context={"http_status_code": exc.status_code}
    )
    
    # Create error response but preserve original HTTP status code
    error_response = error_handler.create_error_response(error_code, str(exc.detail))
    return JSONResponse(
        status_code=exc.status_code,  # Preserve original status code
        content=error_response.model_dump(mode='json')
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors with centralized error handler."""
    request_id = str(uuid.uuid4())
    return error_handler.handle_validation_error(exc, request, request_id)


@app.exception_handler(ValidationError)
async def pydantic_validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors with centralized error handler."""
    request_id = str(uuid.uuid4())
    return error_handler.handle_validation_error(exc, request, request_id)


@app.exception_handler(RateLimitError)
async def anthropic_rate_limit_handler(request: Request, exc: RateLimitError):
    """Handle Anthropic API rate limit errors."""
    request_id = str(uuid.uuid4())
    error_code, message = error_handler.handle_anthropic_error(exc, request, request_id)
    return error_handler.create_json_response(error_code, message)


@app.exception_handler(APITimeoutError)
async def anthropic_timeout_handler(request: Request, exc: APITimeoutError):
    """Handle Anthropic API timeout errors."""
    request_id = str(uuid.uuid4())
    error_code, message = error_handler.handle_anthropic_error(exc, request, request_id)
    return error_handler.create_json_response(error_code, message)


@app.exception_handler(APIError)
async def anthropic_api_error_handler(request: Request, exc: APIError):
    """Handle Anthropic API errors."""
    request_id = str(uuid.uuid4())
    error_code, message = error_handler.handle_anthropic_error(exc, request, request_id)
    return error_handler.create_json_response(error_code, message)


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions with centralized error handler."""
    request_id = str(uuid.uuid4())
    
    error_handler.log_error(
        error_code=ErrorCode.INTERNAL_SERVER_ERROR,
        message=f"Unhandled exception: {str(exc)}",
        request=request,
        exception=exc,
        request_id=request_id,
        additional_context={"exception_type": type(exc).__name__}
    )
    
    return error_handler.create_json_response(
        ErrorCode.INTERNAL_SERVER_ERROR,
        "An unexpected error occurred"
    )


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Travel Data Parser API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "travel-data-parser"}


@app.post("/parse-flight", response_model=FlightParseResponse)
async def parse_flight(
    request: FlightParseRequest,
    http_request: Request,
    parser: UniversalParser = Depends(get_universal_parser)
):
    """
    Parse flight booking URL and extract structured flight data.
    
    Args:
        request: Flight parse request containing the booking URL
        http_request: FastAPI request object for context
        parser: Universal parser instance (injected dependency)
        
    Returns:
        FlightParseResponse: Structured flight data
        
    Raises:
        HTTPException: Various HTTP errors based on failure type
    """
    url = str(request.link)
    request_id = str(uuid.uuid4())
    
    # Start request timing for performance metrics
    error_handler.start_request_timing(request_id)
    
    logger.info(f"Processing flight parsing request for URL: {url}", extra={
        "context": {"request_id": request_id, "url": url, "endpoint": "parse-flight"}
    })
    
    try:
        # Set timeout for the entire parsing operation
        timeout_seconds = settings.REQUEST_TIMEOUT
        
        # Execute parsing with timeout
        flight_data = await asyncio.wait_for(
            parser.parse_flight_data(url),
            timeout=timeout_seconds
        )
        
        # Create and validate response
        response = FlightParseResponse(**flight_data)
        
        # Log successful completion with performance metrics
        duration = error_handler.get_request_duration(request_id)
        logger.info(f"Successfully parsed flight data from {url}", extra={
            "context": {
                "request_id": request_id,
                "url": url,
                "duration_seconds": duration,
                "success": True
            }
        })
        
        return response
        
    except asyncio.TimeoutError as e:
        error_handler.log_error(
            error_code=ErrorCode.TIMEOUT,
            message=f"Flight parsing timeout after {timeout_seconds}s",
            request=http_request,
            exception=e,
            request_id=request_id,
            url=url,
            additional_context={"timeout_seconds": timeout_seconds}
        )
        raise HTTPException(
            status_code=500,
            detail=f"TIMEOUT: Request timeout exceeded ({timeout_seconds}s). The flight booking page took too long to process."
        )
        
    except ValueError as e:
        # Handle parsing-specific errors using centralized error handler
        error_code, message = error_handler.handle_parsing_error(e, http_request, request_id, url)
        raise HTTPException(
            status_code=error_handler.ERROR_STATUS_MAPPING[error_code],
            detail=f"{error_code.value}: {message}"
        )
        
    except (RateLimitError, APITimeoutError, APIError) as e:
        # Handle Anthropic API errors using centralized error handler
        error_code, message = error_handler.handle_anthropic_error(e, http_request, request_id, url)
        raise HTTPException(
            status_code=error_handler.ERROR_STATUS_MAPPING[error_code],
            detail=f"{error_code.value}: {message}"
        )
        
    except Exception as e:
        # Handle HTTP client errors, network issues, and other errors
        error_code, message = error_handler.handle_http_error(e, http_request, request_id, url)
        raise HTTPException(
            status_code=error_handler.ERROR_STATUS_MAPPING[error_code],
            detail=f"{error_code.value}: {message}"
        )
        
    finally:
        # Ensure parser resources are cleaned up
        try:
            await parser.close()
        except Exception as cleanup_error:
            logger.warning(f"Error during parser cleanup: {cleanup_error}", extra={
                "context": {"request_id": request_id, "cleanup_error": str(cleanup_error)}
            })


@app.post("/parse-lodging", response_model=LodgingParseResponse)
async def parse_lodging(
    request: LodgingParseRequest,
    http_request: Request,
    parser: UniversalParser = Depends(get_universal_parser)
):
    """
    Parse lodging booking URL and extract structured accommodation data.
    
    Args:
        request: Lodging parse request containing the booking URL
        http_request: FastAPI request object for context
        parser: Universal parser instance (injected dependency)
        
    Returns:
        LodgingParseResponse: Structured lodging data
        
    Raises:
        HTTPException: Various HTTP errors based on failure type
    """
    url = str(request.link)
    request_id = str(uuid.uuid4())
    
    # Start request timing for performance metrics
    error_handler.start_request_timing(request_id)
    
    logger.info(f"Processing lodging parsing request for URL: {url}", extra={
        "context": {"request_id": request_id, "url": url, "endpoint": "parse-lodging"}
    })
    
    try:
        # Set timeout for the entire parsing operation
        timeout_seconds = settings.REQUEST_TIMEOUT
        
        # Execute parsing with timeout
        lodging_data = await asyncio.wait_for(
            parser.parse_lodging_data(url),
            timeout=timeout_seconds
        )
        
        # Create and validate response
        response = LodgingParseResponse(**lodging_data)
        
        # Log successful completion with performance metrics
        duration = error_handler.get_request_duration(request_id)
        logger.info(f"Successfully parsed lodging data from {url}", extra={
            "context": {
                "request_id": request_id,
                "url": url,
                "duration_seconds": duration,
                "success": True
            }
        })
        
        return response
        
    except asyncio.TimeoutError as e:
        error_handler.log_error(
            error_code=ErrorCode.TIMEOUT,
            message=f"Lodging parsing timeout after {timeout_seconds}s",
            request=http_request,
            exception=e,
            request_id=request_id,
            url=url,
            additional_context={"timeout_seconds": timeout_seconds}
        )
        raise HTTPException(
            status_code=500,
            detail=f"TIMEOUT: Request timeout exceeded ({timeout_seconds}s). The lodging booking page took too long to process."
        )
        
    except ValueError as e:
        # Handle parsing-specific errors using centralized error handler
        error_code, message = error_handler.handle_parsing_error(e, http_request, request_id, url)
        raise HTTPException(
            status_code=error_handler.ERROR_STATUS_MAPPING[error_code],
            detail=f"{error_code.value}: {message}"
        )
        
    except (RateLimitError, APITimeoutError, APIError) as e:
        # Handle Anthropic API errors using centralized error handler
        error_code, message = error_handler.handle_anthropic_error(e, http_request, request_id, url)
        raise HTTPException(
            status_code=error_handler.ERROR_STATUS_MAPPING[error_code],
            detail=f"{error_code.value}: {message}"
        )
        
    except Exception as e:
        # Handle HTTP client errors, network issues, and other errors
        error_code, message = error_handler.handle_http_error(e, http_request, request_id, url)
        raise HTTPException(
            status_code=error_handler.ERROR_STATUS_MAPPING[error_code],
            detail=f"{error_code.value}: {message}"
        )
        
    finally:
        # Ensure parser resources are cleaned up
        try:
            await parser.close()
        except Exception as cleanup_error:
            logger.warning(f"Error during parser cleanup: {cleanup_error}", extra={
                "context": {"request_id": request_id, "cleanup_error": str(cleanup_error)}
            })