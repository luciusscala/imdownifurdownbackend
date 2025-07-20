"""
Travel Data Parser API - FastAPI Application
"""

import asyncio
import logging
from datetime import datetime, timezone
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.models.requests import FlightParseRequest, LodgingParseRequest
from app.models.responses import ErrorResponse, FlightParseResponse, LodgingParseResponse
from app.services.universal_parser import UniversalParser

# Configure logging
logging.basicConfig(level=logging.INFO)
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


# Global exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with consistent error response format."""
    logger.error(f"HTTP Exception: {exc.status_code} - {exc.detail} - URL: {request.url}")
    
    error_response = ErrorResponse(
        error=f"HTTP_{exc.status_code}",
        message=str(exc.detail),
        timestamp=datetime.now(timezone.utc)
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(mode='json')
    )


@app.exception_handler(StarletteHTTPException)
async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle Starlette HTTP exceptions with consistent error response format."""
    logger.error(f"Starlette HTTP Exception: {exc.status_code} - {exc.detail} - URL: {request.url}")
    
    error_response = ErrorResponse(
        error=f"HTTP_{exc.status_code}",
        message=str(exc.detail),
        timestamp=datetime.now(timezone.utc)
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(mode='json')
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors with consistent error response format."""
    logger.error(f"Validation Error: {exc.errors()} - URL: {request.url}")
    
    error_response = ErrorResponse(
        error="VALIDATION_ERROR",
        message=f"Request validation failed: {exc.errors()}",
        timestamp=datetime.now(timezone.utc)
    )
    
    return JSONResponse(
        status_code=422,
        content=error_response.model_dump(mode='json')
    )


@app.exception_handler(ValidationError)
async def pydantic_validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors with consistent error response format."""
    logger.error(f"Pydantic Validation Error: {exc.errors()} - URL: {request.url}")
    
    error_response = ErrorResponse(
        error="VALIDATION_ERROR",
        message=f"Data validation failed: {exc.errors()}",
        timestamp=datetime.now(timezone.utc)
    )
    
    return JSONResponse(
        status_code=422,
        content=error_response.model_dump(mode='json')
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions with consistent error response format."""
    logger.error(f"Unhandled Exception: {type(exc).__name__}: {str(exc)} - URL: {request.url}", exc_info=True)
    
    error_response = ErrorResponse(
        error="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred",
        timestamp=datetime.now(timezone.utc)
    )
    
    return JSONResponse(
        status_code=500,
        content=error_response.model_dump(mode='json')
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
    parser: UniversalParser = Depends(get_universal_parser)
):
    """
    Parse flight booking URL and extract structured flight data.
    
    Args:
        request: Flight parse request containing the booking URL
        parser: Universal parser instance (injected dependency)
        
    Returns:
        FlightParseResponse: Structured flight data
        
    Raises:
        HTTPException: Various HTTP errors based on failure type
    """
    url = str(request.link)
    logger.info(f"Processing flight parsing request for URL: {url}")
    
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
        
        logger.info(f"Successfully parsed flight data from {url}")
        return response
        
    except asyncio.TimeoutError:
        logger.error(f"Flight parsing timeout for URL: {url}")
        raise HTTPException(
            status_code=500,
            detail=f"Request timeout exceeded ({timeout_seconds}s). The flight booking page took too long to process."
        )
        
    except ValueError as e:
        # Handle parsing-specific errors (invalid URL, unsupported platform, etc.)
        error_msg = str(e)
        logger.error(f"Flight parsing validation error for {url}: {error_msg}")
        
        # Determine appropriate HTTP status code based on error type
        if "invalid url" in error_msg.lower() or "malformed url" in error_msg.lower():
            status_code = 400
            error_code = "INVALID_URL"
        elif "not supported" in error_msg.lower() or "unsupported platform" in error_msg.lower():
            status_code = 400
            error_code = "UNSUPPORTED_PLATFORM"
        elif "no meaningful text" in error_msg.lower() or "parsing failed" in error_msg.lower():
            status_code = 500
            error_code = "PARSING_FAILED"
        else:
            status_code = 500
            error_code = "PARSING_ERROR"
            
        raise HTTPException(
            status_code=status_code,
            detail=f"{error_code}: {error_msg}"
        )
        
    except Exception as e:
        # Handle HTTP client errors, network issues, and LLM API errors
        error_msg = str(e)
        logger.error(f"Flight parsing error for {url}: {error_msg}", exc_info=True)
        
        # Determine error type and appropriate response
        if "connection" in error_msg.lower() or "network" in error_msg.lower():
            status_code = 500
            error_code = "URL_UNREACHABLE"
            detail = f"Unable to reach the provided URL: {error_msg}"
        elif "404" in error_msg or "not found" in error_msg.lower():
            status_code = 500
            error_code = "URL_UNREACHABLE"
            detail = f"The provided URL was not found: {error_msg}"
        elif "403" in error_msg or "forbidden" in error_msg.lower():
            status_code = 500
            error_code = "URL_UNREACHABLE"
            detail = f"Access to the URL was forbidden: {error_msg}"
        elif "429" in error_msg or "rate limit" in error_msg.lower():
            status_code = 429
            error_code = "RATE_LIMITED"
            detail = f"Rate limit exceeded. Please try again later: {error_msg}"
        elif "anthropic" in error_msg.lower() or "llm" in error_msg.lower() or "api" in error_msg.lower():
            status_code = 500
            error_code = "LLM_API_ERROR"
            detail = f"LLM API error occurred: {error_msg}"
        else:
            status_code = 500
            error_code = "INTERNAL_SERVER_ERROR"
            detail = f"An unexpected error occurred while parsing flight data: {error_msg}"
            
        raise HTTPException(
            status_code=status_code,
            detail=f"{error_code}: {detail}"
        )
        
    finally:
        # Ensure parser resources are cleaned up
        try:
            await parser.close()
        except Exception as cleanup_error:
            logger.warning(f"Error during parser cleanup: {cleanup_error}")


@app.post("/parse-lodging", response_model=LodgingParseResponse)
async def parse_lodging(
    request: LodgingParseRequest,
    parser: UniversalParser = Depends(get_universal_parser)
):
    """
    Parse lodging booking URL and extract structured accommodation data.
    
    Args:
        request: Lodging parse request containing the booking URL
        parser: Universal parser instance (injected dependency)
        
    Returns:
        LodgingParseResponse: Structured lodging data
        
    Raises:
        HTTPException: Various HTTP errors based on failure type
    """
    url = str(request.link)
    logger.info(f"Processing lodging parsing request for URL: {url}")
    
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
        
        logger.info(f"Successfully parsed lodging data from {url}")
        return response
        
    except asyncio.TimeoutError:
        logger.error(f"Lodging parsing timeout for URL: {url}")
        raise HTTPException(
            status_code=500,
            detail=f"Request timeout exceeded ({timeout_seconds}s). The lodging booking page took too long to process."
        )
        
    except ValueError as e:
        # Handle parsing-specific errors (invalid URL, unsupported platform, etc.)
        error_msg = str(e)
        logger.error(f"Lodging parsing validation error for {url}: {error_msg}")
        
        # Determine appropriate HTTP status code based on error type
        if "invalid url" in error_msg.lower() or "malformed url" in error_msg.lower():
            status_code = 400
            error_code = "INVALID_URL"
        elif "not supported" in error_msg.lower() or "unsupported platform" in error_msg.lower():
            status_code = 400
            error_code = "UNSUPPORTED_PLATFORM"
        elif "no meaningful text" in error_msg.lower() or "parsing failed" in error_msg.lower():
            status_code = 500
            error_code = "PARSING_FAILED"
        else:
            status_code = 500
            error_code = "PARSING_ERROR"
            
        raise HTTPException(
            status_code=status_code,
            detail=f"{error_code}: {error_msg}"
        )
        
    except Exception as e:
        # Handle HTTP client errors, network issues, and LLM API errors
        error_msg = str(e)
        logger.error(f"Lodging parsing error for {url}: {error_msg}", exc_info=True)
        
        # Determine error type and appropriate response
        if "connection" in error_msg.lower() or "network" in error_msg.lower():
            status_code = 500
            error_code = "URL_UNREACHABLE"
            detail = f"Unable to reach the provided URL: {error_msg}"
        elif "404" in error_msg or "not found" in error_msg.lower():
            status_code = 500
            error_code = "URL_UNREACHABLE"
            detail = f"The provided URL was not found: {error_msg}"
        elif "403" in error_msg or "forbidden" in error_msg.lower():
            status_code = 500
            error_code = "URL_UNREACHABLE"
            detail = f"Access to the URL was forbidden: {error_msg}"
        elif "429" in error_msg or "rate limit" in error_msg.lower():
            status_code = 429
            error_code = "RATE_LIMITED"
            detail = f"Rate limit exceeded. Please try again later: {error_msg}"
        elif "anthropic" in error_msg.lower() or "llm" in error_msg.lower() or "api" in error_msg.lower():
            status_code = 500
            error_code = "LLM_API_ERROR"
            detail = f"LLM API error occurred: {error_msg}"
        else:
            status_code = 500
            error_code = "INTERNAL_SERVER_ERROR"
            detail = f"An unexpected error occurred while parsing lodging data: {error_msg}"
            
        raise HTTPException(
            status_code=status_code,
            detail=f"{error_code}: {detail}"
        )
        
    finally:
        # Ensure parser resources are cleaned up
        try:
            await parser.close()
        except Exception as cleanup_error:
            logger.warning(f"Error during parser cleanup: {cleanup_error}")