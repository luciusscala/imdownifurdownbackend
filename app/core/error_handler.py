"""
Centralized error handling for the Travel Data Parser API.

This module provides comprehensive error handling with consistent error response formatting,
specific error codes for different failure scenarios, and detailed logging capabilities.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple
from enum import Enum

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from anthropic import APIError, RateLimitError, APITimeoutError

from app.models.responses import ErrorResponse


class ErrorCode(str, Enum):
    """Enumeration of error codes for different failure scenarios."""
    
    # HTTP status code specific errors
    HTTP_400 = "HTTP_400"
    HTTP_404 = "HTTP_404"
    HTTP_405 = "HTTP_405"
    HTTP_429 = "HTTP_429"
    HTTP_500 = "HTTP_500"
    
    # Client errors (4xx)
    INVALID_URL = "INVALID_URL"
    UNSUPPORTED_PLATFORM = "UNSUPPORTED_PLATFORM"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    
    # Server errors (5xx)
    URL_UNREACHABLE = "URL_UNREACHABLE"
    PARSING_FAILED = "PARSING_FAILED"
    TIMEOUT = "TIMEOUT"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    MISSING_DATA = "MISSING_DATA"
    
    # Rate limiting (429)
    RATE_LIMITED = "RATE_LIMITED"
    
    # LLM API specific errors
    LLM_API_ERROR = "LLM_API_ERROR"
    LLM_RATE_LIMITED = "LLM_RATE_LIMITED"
    LLM_QUOTA_EXCEEDED = "LLM_QUOTA_EXCEEDED"
    LLM_TIMEOUT = "LLM_TIMEOUT"
    LLM_INVALID_RESPONSE = "LLM_INVALID_RESPONSE"


class ErrorHandler:
    """
    Centralized error handling class with consistent error response formatting.
    
    This class provides methods to handle different types of errors that can occur
    during travel data parsing, including HTTP errors, validation errors, LLM API errors,
    and general exceptions. It ensures consistent error response formatting and
    comprehensive logging.
    """
    
    # Error code to HTTP status code mapping
    ERROR_STATUS_MAPPING: Dict[ErrorCode, int] = {
        # HTTP status code specific errors
        ErrorCode.HTTP_400: 400,
        ErrorCode.HTTP_404: 404,
        ErrorCode.HTTP_405: 405,
        ErrorCode.HTTP_429: 429,
        ErrorCode.HTTP_500: 500,
        
        # Client errors (4xx)
        ErrorCode.INVALID_URL: 400,
        ErrorCode.UNSUPPORTED_PLATFORM: 400,
        ErrorCode.VALIDATION_ERROR: 422,
        ErrorCode.MISSING_REQUIRED_FIELD: 400,
        
        # Server errors (5xx)
        ErrorCode.URL_UNREACHABLE: 500,
        ErrorCode.PARSING_FAILED: 500,
        ErrorCode.TIMEOUT: 500,
        ErrorCode.INTERNAL_SERVER_ERROR: 500,
        ErrorCode.MISSING_DATA: 500,
        ErrorCode.LLM_API_ERROR: 500,
        ErrorCode.LLM_TIMEOUT: 500,
        ErrorCode.LLM_INVALID_RESPONSE: 500,
        
        # Rate limiting (429)
        ErrorCode.RATE_LIMITED: 429,
        ErrorCode.LLM_RATE_LIMITED: 429,
        ErrorCode.LLM_QUOTA_EXCEEDED: 429,
    }
    
    # Error code to default message mapping
    ERROR_MESSAGES: Dict[ErrorCode, str] = {
        # HTTP status code specific errors
        ErrorCode.HTTP_400: "Bad Request",
        ErrorCode.HTTP_404: "Not Found",
        ErrorCode.HTTP_405: "Method Not Allowed",
        ErrorCode.HTTP_429: "Too Many Requests",
        ErrorCode.HTTP_500: "Internal Server Error",
        
        # Application-specific errors
        ErrorCode.INVALID_URL: "Invalid or malformed URL provided",
        ErrorCode.UNSUPPORTED_PLATFORM: "Platform not supported for parsing",
        ErrorCode.VALIDATION_ERROR: "Request validation failed",
        ErrorCode.MISSING_REQUIRED_FIELD: "Required field is missing from request",
        ErrorCode.URL_UNREACHABLE: "Unable to reach the provided URL",
        ErrorCode.PARSING_FAILED: "Failed to parse data from the URL",
        ErrorCode.TIMEOUT: "Request timeout exceeded",
        ErrorCode.INTERNAL_SERVER_ERROR: "An unexpected error occurred",
        ErrorCode.MISSING_DATA: "Required data not found on the page",
        ErrorCode.RATE_LIMITED: "Rate limit exceeded, please try again later",
        ErrorCode.LLM_API_ERROR: "LLM API error occurred",
        ErrorCode.LLM_RATE_LIMITED: "LLM API rate limit exceeded",
        ErrorCode.LLM_QUOTA_EXCEEDED: "LLM API quota exceeded",
        ErrorCode.LLM_TIMEOUT: "LLM API request timeout",
        ErrorCode.LLM_INVALID_RESPONSE: "LLM API returned invalid response",
    }
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the ErrorHandler.
        
        Args:
            logger: Optional logger instance. If not provided, creates a new logger.
        """
        self.logger = logger or logging.getLogger(__name__)
        self._request_start_times: Dict[str, float] = {}
    
    def start_request_timing(self, request_id: str) -> None:
        """
        Start timing a request for performance metrics.
        
        Args:
            request_id: Unique identifier for the request
        """
        self._request_start_times[request_id] = time.time()
    
    def get_request_duration(self, request_id: str) -> Optional[float]:
        """
        Get the duration of a request in seconds.
        
        Args:
            request_id: Unique identifier for the request
            
        Returns:
            Duration in seconds, or None if request timing wasn't started
        """
        start_time = self._request_start_times.get(request_id)
        if start_time:
            duration = time.time() - start_time
            # Clean up the stored start time
            del self._request_start_times[request_id]
            return duration
        return None
    
    def create_error_response(
        self,
        error_code: ErrorCode,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> ErrorResponse:
        """
        Create a standardized error response.
        
        Args:
            error_code: The error code enum value
            message: Optional custom error message. If not provided, uses default message.
            details: Optional additional error details
            
        Returns:
            ErrorResponse: Standardized error response object
        """
        final_message = message or self.ERROR_MESSAGES.get(error_code, "Unknown error")
        
        if details:
            final_message = f"{final_message}. Details: {details}"
        
        return ErrorResponse(
            error=error_code.value,
            message=final_message,
            timestamp=datetime.now(timezone.utc)
        )
    
    def log_error(
        self,
        error_code: ErrorCode,
        message: str,
        request: Optional[Request] = None,
        exception: Optional[Exception] = None,
        request_id: Optional[str] = None,
        url: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log error with comprehensive context information.
        
        Args:
            error_code: The error code enum value
            message: Error message
            request: Optional FastAPI request object
            exception: Optional exception that caused the error
            request_id: Optional unique request identifier
            url: Optional URL being processed
            additional_context: Optional additional context information
        """
        # Build context information
        context = {
            "error_code": error_code.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        if request:
            context.update({
                "method": request.method,
                "url": str(request.url),
                "client_ip": getattr(request.client, 'host', 'unknown') if request.client else 'unknown',
                "user_agent": request.headers.get("user-agent", "unknown"),
            })
        
        if request_id:
            context["request_id"] = request_id
            # Add performance metrics if available
            duration = self.get_request_duration(request_id)
            if duration:
                context["duration_seconds"] = round(duration, 3)
        
        if url:
            context["target_url"] = url
        
        if additional_context:
            context.update(additional_context)
        
        # Log the error with full context
        log_message = f"{error_code.value}: {message}"
        
        if exception:
            self.logger.error(
                log_message,
                extra={"context": context},
                exc_info=True
            )
        else:
            self.logger.error(
                log_message,
                extra={"context": context}
            )
    
    def handle_anthropic_error(
        self,
        error: Exception,
        request: Optional[Request] = None,
        request_id: Optional[str] = None,
        url: Optional[str] = None
    ) -> Tuple[ErrorCode, str]:
        """
        Handle Anthropic API specific errors and return appropriate error code and message.
        
        Args:
            error: The Anthropic API error
            request: Optional FastAPI request object
            request_id: Optional unique request identifier
            url: Optional URL being processed
            
        Returns:
            Tuple of (ErrorCode, error_message)
        """
        error_message = str(error)
        
        if isinstance(error, RateLimitError):
            error_code = ErrorCode.LLM_RATE_LIMITED
            message = f"Anthropic API rate limit exceeded: {error_message}"
            
            # Check if it's a quota exceeded error
            if "quota" in error_message.lower() or "billing" in error_message.lower():
                error_code = ErrorCode.LLM_QUOTA_EXCEEDED
                message = f"Anthropic API quota exceeded: {error_message}"
                
        elif isinstance(error, APITimeoutError):
            error_code = ErrorCode.LLM_TIMEOUT
            message = f"Anthropic API timeout: {error_message}"
            
        elif isinstance(error, APIError):
            error_code = ErrorCode.LLM_API_ERROR
            message = f"Anthropic API error: {error_message}"
            
            # Check for specific API error types
            if hasattr(error, 'status_code'):
                if error.status_code == 429:
                    error_code = ErrorCode.LLM_RATE_LIMITED
                elif error.status_code >= 500:
                    message = f"Anthropic API server error (HTTP {error.status_code}): {error_message}"
                elif error.status_code >= 400:
                    message = f"Anthropic API client error (HTTP {error.status_code}): {error_message}"
        else:
            error_code = ErrorCode.LLM_API_ERROR
            message = f"Unknown Anthropic API error: {error_message}"
        
        # Log the error with context
        self.log_error(
            error_code=error_code,
            message=message,
            request=request,
            exception=error,
            request_id=request_id,
            url=url,
            additional_context={"anthropic_error_type": type(error).__name__}
        )
        
        return error_code, message
    
    def handle_parsing_error(
        self,
        error: Exception,
        request: Optional[Request] = None,
        request_id: Optional[str] = None,
        url: Optional[str] = None
    ) -> Tuple[ErrorCode, str]:
        """
        Handle parsing-related errors and return appropriate error code and message.
        
        Args:
            error: The parsing error
            request: Optional FastAPI request object
            request_id: Optional unique request identifier
            url: Optional URL being processed
            
        Returns:
            Tuple of (ErrorCode, error_message)
        """
        error_message = str(error).lower()
        
        if isinstance(error, ValueError):
            if "invalid url" in error_message or "malformed url" in error_message:
                error_code = ErrorCode.INVALID_URL
                message = f"Invalid URL format: {str(error)}"
            elif "not supported" in error_message or "unsupported platform" in error_message:
                error_code = ErrorCode.UNSUPPORTED_PLATFORM
                message = f"Platform not supported: {str(error)}"
            elif "no meaningful text" in error_message or "parsing failed" in error_message:
                error_code = ErrorCode.PARSING_FAILED
                message = f"Failed to parse content: {str(error)}"
            elif "missing data" in error_message or "required data not found" in error_message:
                error_code = ErrorCode.MISSING_DATA
                message = f"Required data missing: {str(error)}"
            else:
                error_code = ErrorCode.PARSING_FAILED
                message = f"Parsing error: {str(error)}"
        else:
            error_code = ErrorCode.PARSING_FAILED
            message = f"Unexpected parsing error: {str(error)}"
        
        # Log the error with context
        self.log_error(
            error_code=error_code,
            message=message,
            request=request,
            exception=error,
            request_id=request_id,
            url=url,
            additional_context={"parsing_error_type": type(error).__name__}
        )
        
        return error_code, message
    
    def handle_http_error(
        self,
        error: Exception,
        request: Optional[Request] = None,
        request_id: Optional[str] = None,
        url: Optional[str] = None
    ) -> Tuple[ErrorCode, str]:
        """
        Handle HTTP-related errors and return appropriate error code and message.
        
        Args:
            error: The HTTP error
            request: Optional FastAPI request object
            request_id: Optional unique request identifier
            url: Optional URL being processed
            
        Returns:
            Tuple of (ErrorCode, error_message)
        """
        error_message = str(error).lower()
        
        if "connection" in error_message or "network" in error_message:
            error_code = ErrorCode.URL_UNREACHABLE
            message = f"Network connection error: {str(error)}"
        elif "404" in error_message or "not found" in error_message:
            error_code = ErrorCode.URL_UNREACHABLE
            message = f"URL not found (404): {str(error)}"
        elif "403" in error_message or "forbidden" in error_message:
            error_code = ErrorCode.URL_UNREACHABLE
            message = f"Access forbidden (403): {str(error)}"
        elif "429" in error_message or "rate limit" in error_message:
            error_code = ErrorCode.RATE_LIMITED
            message = f"Rate limit exceeded: {str(error)}"
        elif "timeout" in error_message:
            error_code = ErrorCode.TIMEOUT
            message = f"Request timeout: {str(error)}"
        else:
            error_code = ErrorCode.URL_UNREACHABLE
            message = f"HTTP error: {str(error)}"
        
        # Log the error with context
        self.log_error(
            error_code=error_code,
            message=message,
            request=request,
            exception=error,
            request_id=request_id,
            url=url,
            additional_context={"http_error_type": type(error).__name__}
        )
        
        return error_code, message
    
    def create_json_response(
        self,
        error_code: ErrorCode,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> JSONResponse:
        """
        Create a JSON response for an error.
        
        Args:
            error_code: The error code enum value
            message: Optional custom error message
            details: Optional additional error details
            
        Returns:
            JSONResponse: FastAPI JSON response with appropriate status code
        """
        error_response = self.create_error_response(error_code, message, details)
        status_code = self.ERROR_STATUS_MAPPING.get(error_code, 500)
        
        return JSONResponse(
            status_code=status_code,
            content=error_response.model_dump(mode='json')
        )
    
    def handle_validation_error(
        self,
        error: ValidationError,
        request: Optional[Request] = None,
        request_id: Optional[str] = None
    ) -> JSONResponse:
        """
        Handle Pydantic validation errors.
        
        Args:
            error: The validation error
            request: Optional FastAPI request object
            request_id: Optional unique request identifier
            
        Returns:
            JSONResponse: Error response for validation failure
        """
        error_details = error.errors()
        message = f"Validation failed: {error_details}"
        
        self.log_error(
            error_code=ErrorCode.VALIDATION_ERROR,
            message=message,
            request=request,
            exception=error,
            request_id=request_id,
            additional_context={"validation_errors": error_details}
        )
        
        return self.create_json_response(
            ErrorCode.VALIDATION_ERROR,
            message,
            {"validation_errors": error_details}
        )


# Global error handler instance
error_handler = ErrorHandler()