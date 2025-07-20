"""
Unit tests for the centralized error handler.

This module tests the ErrorHandler class functionality including error response creation,
logging capabilities, error code mapping, and specific error handling for different
failure scenarios.
"""

import json
import logging
import time
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

import pytest
from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from anthropic import APIError, RateLimitError, APITimeoutError

from app.core.error_handler import ErrorHandler, ErrorCode
from app.models.responses import ErrorResponse


class TestErrorCode:
    """Test the ErrorCode enumeration."""
    
    def test_error_code_values(self):
        """Test that error codes have expected string values."""
        # HTTP-specific error codes
        assert ErrorCode.HTTP_400.value == "HTTP_400"
        assert ErrorCode.HTTP_404.value == "HTTP_404"
        assert ErrorCode.HTTP_405.value == "HTTP_405"
        assert ErrorCode.HTTP_429.value == "HTTP_429"
        assert ErrorCode.HTTP_500.value == "HTTP_500"
        
        # Application-specific error codes
        assert ErrorCode.INVALID_URL.value == "INVALID_URL"
        assert ErrorCode.UNSUPPORTED_PLATFORM.value == "UNSUPPORTED_PLATFORM"
        assert ErrorCode.VALIDATION_ERROR.value == "VALIDATION_ERROR"
        assert ErrorCode.URL_UNREACHABLE.value == "URL_UNREACHABLE"
        assert ErrorCode.PARSING_FAILED.value == "PARSING_FAILED"
        assert ErrorCode.TIMEOUT.value == "TIMEOUT"
        assert ErrorCode.RATE_LIMITED.value == "RATE_LIMITED"
        assert ErrorCode.LLM_API_ERROR.value == "LLM_API_ERROR"
        assert ErrorCode.LLM_RATE_LIMITED.value == "LLM_RATE_LIMITED"
        assert ErrorCode.LLM_QUOTA_EXCEEDED.value == "LLM_QUOTA_EXCEEDED"


class TestErrorHandler:
    """Test the ErrorHandler class functionality."""
    
    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger for testing."""
        return Mock(spec=logging.Logger)
    
    @pytest.fixture
    def error_handler(self, mock_logger):
        """Create an ErrorHandler instance with mock logger."""
        return ErrorHandler(logger=mock_logger)
    
    @pytest.fixture
    def mock_request(self):
        """Create a mock FastAPI request object."""
        request = Mock(spec=Request)
        request.method = "POST"
        request.url = "http://localhost:8000/parse-flight"
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.headers = {"user-agent": "test-agent"}
        return request
    
    def test_error_status_mapping(self, error_handler):
        """Test that error codes map to correct HTTP status codes."""
        # Client errors (4xx)
        assert error_handler.ERROR_STATUS_MAPPING[ErrorCode.INVALID_URL] == 400
        assert error_handler.ERROR_STATUS_MAPPING[ErrorCode.UNSUPPORTED_PLATFORM] == 400
        assert error_handler.ERROR_STATUS_MAPPING[ErrorCode.VALIDATION_ERROR] == 422
        
        # Server errors (5xx)
        assert error_handler.ERROR_STATUS_MAPPING[ErrorCode.URL_UNREACHABLE] == 500
        assert error_handler.ERROR_STATUS_MAPPING[ErrorCode.PARSING_FAILED] == 500
        assert error_handler.ERROR_STATUS_MAPPING[ErrorCode.TIMEOUT] == 500
        assert error_handler.ERROR_STATUS_MAPPING[ErrorCode.INTERNAL_SERVER_ERROR] == 500
        
        # Rate limiting (429)
        assert error_handler.ERROR_STATUS_MAPPING[ErrorCode.RATE_LIMITED] == 429
        assert error_handler.ERROR_STATUS_MAPPING[ErrorCode.LLM_RATE_LIMITED] == 429
        assert error_handler.ERROR_STATUS_MAPPING[ErrorCode.LLM_QUOTA_EXCEEDED] == 429
    
    def test_error_messages(self, error_handler):
        """Test that error codes have default messages."""
        assert "Invalid or malformed URL" in error_handler.ERROR_MESSAGES[ErrorCode.INVALID_URL]
        assert "Platform not supported" in error_handler.ERROR_MESSAGES[ErrorCode.UNSUPPORTED_PLATFORM]
        assert "Unable to reach" in error_handler.ERROR_MESSAGES[ErrorCode.URL_UNREACHABLE]
        assert "Rate limit exceeded" in error_handler.ERROR_MESSAGES[ErrorCode.RATE_LIMITED]
    
    def test_create_error_response_default_message(self, error_handler):
        """Test creating error response with default message."""
        response = error_handler.create_error_response(ErrorCode.INVALID_URL)
        
        assert isinstance(response, ErrorResponse)
        assert response.error == "INVALID_URL"
        assert "Invalid or malformed URL" in response.message
        assert isinstance(response.timestamp, datetime)
    
    def test_create_error_response_custom_message(self, error_handler):
        """Test creating error response with custom message."""
        custom_message = "Custom error message"
        response = error_handler.create_error_response(ErrorCode.PARSING_FAILED, custom_message)
        
        assert response.error == "PARSING_FAILED"
        assert response.message == custom_message
    
    def test_create_error_response_with_details(self, error_handler):
        """Test creating error response with additional details."""
        details = {"url": "https://example.com", "status_code": 404}
        response = error_handler.create_error_response(
            ErrorCode.URL_UNREACHABLE, 
            details=details
        )
        
        assert "Details:" in response.message
        assert str(details) in response.message
    
    def test_request_timing(self, error_handler):
        """Test request timing functionality."""
        request_id = "test-request-123"
        
        # Start timing
        error_handler.start_request_timing(request_id)
        
        # Simulate some processing time
        time.sleep(0.1)
        
        # Get duration
        duration = error_handler.get_request_duration(request_id)
        
        assert duration is not None
        assert duration >= 0.1
        assert duration < 1.0  # Should be less than 1 second
        
        # Second call should return None (cleaned up)
        duration2 = error_handler.get_request_duration(request_id)
        assert duration2 is None
    
    def test_log_error_basic(self, error_handler, mock_logger):
        """Test basic error logging functionality."""
        error_handler.log_error(
            error_code=ErrorCode.INVALID_URL,
            message="Test error message"
        )
        
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        
        # Check the log message
        assert "INVALID_URL: Test error message" in call_args[0][0]
        
        # Check the context
        assert "context" in call_args[1]["extra"]
        context = call_args[1]["extra"]["context"]
        assert context["error_code"] == "INVALID_URL"
        assert "timestamp" in context
    
    def test_log_error_with_request(self, error_handler, mock_logger, mock_request):
        """Test error logging with request context."""
        error_handler.log_error(
            error_code=ErrorCode.PARSING_FAILED,
            message="Parsing failed",
            request=mock_request
        )
        
        mock_logger.error.assert_called_once()
        context = mock_logger.error.call_args[1]["extra"]["context"]
        
        assert context["method"] == "POST"
        assert "localhost:8000" in context["url"]
        assert context["client_ip"] == "127.0.0.1"
        assert context["user_agent"] == "test-agent"
    
    def test_log_error_with_exception(self, error_handler, mock_logger):
        """Test error logging with exception information."""
        test_exception = ValueError("Test exception")
        
        error_handler.log_error(
            error_code=ErrorCode.PARSING_FAILED,
            message="Parsing failed",
            exception=test_exception
        )
        
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        
        # Should include exc_info=True when exception is provided
        assert call_args[1]["exc_info"] is True
    
    def test_log_error_with_performance_metrics(self, error_handler, mock_logger):
        """Test error logging with performance metrics."""
        request_id = "test-request-456"
        
        # Start timing
        error_handler.start_request_timing(request_id)
        time.sleep(0.05)  # Small delay
        
        error_handler.log_error(
            error_code=ErrorCode.TIMEOUT,
            message="Request timeout",
            request_id=request_id
        )
        
        mock_logger.error.assert_called_once()
        context = mock_logger.error.call_args[1]["extra"]["context"]
        
        assert context["request_id"] == request_id
        assert "duration_seconds" in context
        assert context["duration_seconds"] >= 0.05
    
    def test_handle_anthropic_rate_limit_error(self, error_handler, mock_logger):
        """Test handling Anthropic rate limit errors."""
        # Create a mock RateLimitError with required parameters
        mock_response = Mock()
        mock_response.status_code = 429
        rate_limit_error = RateLimitError(
            message="Rate limit exceeded",
            response=mock_response,
            body={"error": {"message": "Rate limit exceeded"}}
        )
        
        error_code, message = error_handler.handle_anthropic_error(rate_limit_error)
        
        assert error_code == ErrorCode.LLM_RATE_LIMITED
        assert "rate limit exceeded" in message.lower()
        mock_logger.error.assert_called_once()
    
    def test_handle_anthropic_quota_exceeded_error(self, error_handler, mock_logger):
        """Test handling Anthropic quota exceeded errors."""
        # Create a mock RateLimitError with quota message
        mock_response = Mock()
        mock_response.status_code = 429
        quota_error = RateLimitError(
            message="Your account has exceeded its quota",
            response=mock_response,
            body={"error": {"message": "Your account has exceeded its quota"}}
        )
        
        error_code, message = error_handler.handle_anthropic_error(quota_error)
        
        assert error_code == ErrorCode.LLM_QUOTA_EXCEEDED
        assert "quota exceeded" in message.lower()
    
    def test_handle_anthropic_timeout_error(self, error_handler, mock_logger):
        """Test handling Anthropic timeout errors."""
        # Create a mock APITimeoutError
        mock_request = Mock()
        timeout_error = APITimeoutError(request=mock_request)
        
        error_code, message = error_handler.handle_anthropic_error(timeout_error)
        
        assert error_code == ErrorCode.LLM_TIMEOUT
        assert "timeout" in message.lower()
    
    def test_handle_anthropic_api_error(self, error_handler, mock_logger):
        """Test handling general Anthropic API errors."""
        # Create a mock APIError with required parameters
        mock_request = Mock()
        api_error = APIError(
            message="API error occurred", 
            request=mock_request,
            body={"error": {"message": "API error occurred"}}
        )
        
        error_code, message = error_handler.handle_anthropic_error(api_error)
        
        assert error_code == ErrorCode.LLM_API_ERROR
        assert "API error" in message
    
    def test_handle_anthropic_api_error_with_status_code(self, error_handler, mock_logger):
        """Test handling Anthropic API errors with HTTP status codes."""
        # Create a mock APIError with status code
        mock_request = Mock()
        api_error = APIError(
            message="Server error",
            request=mock_request,
            body={"error": {"message": "Server error"}}
        )
        # Set status_code attribute after creation
        api_error.status_code = 500
        
        error_code, message = error_handler.handle_anthropic_error(api_error)
        
        assert error_code == ErrorCode.LLM_API_ERROR
        assert "HTTP 500" in message
    
    def test_handle_parsing_error_invalid_url(self, error_handler, mock_logger):
        """Test handling parsing errors for invalid URLs."""
        parsing_error = ValueError("Invalid URL format")
        
        error_code, message = error_handler.handle_parsing_error(parsing_error)
        
        assert error_code == ErrorCode.INVALID_URL
        assert "Invalid URL format" in message
    
    def test_handle_parsing_error_unsupported_platform(self, error_handler, mock_logger):
        """Test handling parsing errors for unsupported platforms."""
        parsing_error = ValueError("Platform not supported")
        
        error_code, message = error_handler.handle_parsing_error(parsing_error)
        
        assert error_code == ErrorCode.UNSUPPORTED_PLATFORM
        assert "Platform not supported" in message
    
    def test_handle_parsing_error_parsing_failed(self, error_handler, mock_logger):
        """Test handling parsing failures."""
        parsing_error = ValueError("No meaningful text found")
        
        error_code, message = error_handler.handle_parsing_error(parsing_error)
        
        assert error_code == ErrorCode.PARSING_FAILED
        assert "Failed to parse content" in message
    
    def test_handle_parsing_error_missing_data(self, error_handler, mock_logger):
        """Test handling missing data errors."""
        parsing_error = ValueError("Required data not found")
        
        error_code, message = error_handler.handle_parsing_error(parsing_error)
        
        assert error_code == ErrorCode.MISSING_DATA
        assert "Required data missing" in message
    
    def test_handle_http_error_connection(self, error_handler, mock_logger):
        """Test handling HTTP connection errors."""
        http_error = Exception("Connection failed")
        
        error_code, message = error_handler.handle_http_error(http_error)
        
        assert error_code == ErrorCode.URL_UNREACHABLE
        assert "Network connection error" in message
    
    def test_handle_http_error_404(self, error_handler, mock_logger):
        """Test handling HTTP 404 errors."""
        http_error = Exception("404 Not Found")
        
        error_code, message = error_handler.handle_http_error(http_error)
        
        assert error_code == ErrorCode.URL_UNREACHABLE
        assert "URL not found (404)" in message
    
    def test_handle_http_error_403(self, error_handler, mock_logger):
        """Test handling HTTP 403 errors."""
        http_error = Exception("403 Forbidden")
        
        error_code, message = error_handler.handle_http_error(http_error)
        
        assert error_code == ErrorCode.URL_UNREACHABLE
        assert "Access forbidden (403)" in message
    
    def test_handle_http_error_rate_limit(self, error_handler, mock_logger):
        """Test handling HTTP rate limit errors."""
        http_error = Exception("429 Rate limit exceeded")
        
        error_code, message = error_handler.handle_http_error(http_error)
        
        assert error_code == ErrorCode.RATE_LIMITED
        assert "Rate limit exceeded" in message
    
    def test_handle_http_error_timeout(self, error_handler, mock_logger):
        """Test handling HTTP timeout errors."""
        http_error = Exception("Request timeout")
        
        error_code, message = error_handler.handle_http_error(http_error)
        
        assert error_code == ErrorCode.TIMEOUT
        assert "Request timeout" in message
    
    def test_create_json_response(self, error_handler):
        """Test creating JSON response for errors."""
        response = error_handler.create_json_response(
            ErrorCode.INVALID_URL,
            "Custom error message"
        )
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == 400
        
        # Parse the response content
        content = json.loads(response.body.decode())
        assert content["error"] == "INVALID_URL"
        assert content["message"] == "Custom error message"
        assert "timestamp" in content
    
    def test_handle_validation_error(self, error_handler, mock_logger):
        """Test handling Pydantic validation errors."""
        # Create a mock validation error
        validation_error = Mock(spec=ValidationError)
        validation_error.errors.return_value = [
            {"loc": ["field"], "msg": "field required", "type": "value_error.missing"}
        ]
        
        response = error_handler.handle_validation_error(validation_error)
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == 422
        
        # Check that error was logged
        mock_logger.error.assert_called_once()
        
        # Parse response content
        content = json.loads(response.body.decode())
        assert content["error"] == "VALIDATION_ERROR"
        assert "Validation failed" in content["message"]
    
    def test_error_handler_without_logger(self):
        """Test ErrorHandler initialization without providing a logger."""
        handler = ErrorHandler()
        
        # Should create its own logger
        assert handler.logger is not None
        assert isinstance(handler.logger, logging.Logger)
    
    def test_comprehensive_error_context(self, error_handler, mock_logger, mock_request):
        """Test that comprehensive context is logged for errors."""
        request_id = "comprehensive-test"
        url = "https://example.com/booking"
        additional_context = {"custom_field": "custom_value"}
        
        error_handler.start_request_timing(request_id)
        time.sleep(0.01)
        
        error_handler.log_error(
            error_code=ErrorCode.LLM_API_ERROR,
            message="Comprehensive error test",
            request=mock_request,
            request_id=request_id,
            url=url,
            additional_context=additional_context
        )
        
        mock_logger.error.assert_called_once()
        context = mock_logger.error.call_args[1]["extra"]["context"]
        
        # Check all context fields are present
        assert context["error_code"] == "LLM_API_ERROR"
        assert context["request_id"] == request_id
        assert context["target_url"] == url
        assert context["method"] == "POST"
        assert context["client_ip"] == "127.0.0.1"
        assert context["custom_field"] == "custom_value"
        assert "duration_seconds" in context
        assert "timestamp" in context


class TestErrorHandlerIntegration:
    """Integration tests for error handler with real scenarios."""
    
    @pytest.fixture
    def error_handler(self):
        """Create a real ErrorHandler instance for integration tests."""
        return ErrorHandler()
    
    def test_real_validation_error_handling(self, error_handler):
        """Test handling real Pydantic validation errors."""
        from pydantic import BaseModel, Field
        
        class TestModel(BaseModel):
            required_field: str = Field(..., min_length=1)
        
        try:
            TestModel(required_field="")
        except ValidationError as e:
            response = error_handler.handle_validation_error(e)
            
            assert response.status_code == 422
            content = json.loads(response.body.decode())
            assert content["error"] == "VALIDATION_ERROR"
            assert "validation_errors" in content["message"]
    
    def test_error_response_serialization(self, error_handler):
        """Test that error responses can be properly serialized."""
        response = error_handler.create_error_response(
            ErrorCode.PARSING_FAILED,
            "Test parsing failure",
            {"additional": "data"}
        )
        
        # Should be able to serialize to dict
        response_dict = response.model_dump(mode='json')
        
        assert response_dict["error"] == "PARSING_FAILED"
        assert "Test parsing failure" in response_dict["message"]
        assert isinstance(response_dict["timestamp"], str)
        
        # Should be able to serialize to JSON
        json_str = json.dumps(response_dict)
        assert json_str is not None
        
        # Should be able to deserialize back
        parsed = json.loads(json_str)
        assert parsed["error"] == "PARSING_FAILED"
    
    def test_concurrent_request_timing(self, error_handler):
        """Test that request timing works correctly with concurrent requests."""
        import threading
        import time
        
        results = {}
        
        def time_request(request_id: str, sleep_time: float):
            error_handler.start_request_timing(request_id)
            time.sleep(sleep_time)
            duration = error_handler.get_request_duration(request_id)
            results[request_id] = duration
        
        # Start multiple concurrent requests
        threads = []
        for i in range(3):
            thread = threading.Thread(
                target=time_request,
                args=(f"request-{i}", 0.1 + i * 0.05)
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check results
        assert len(results) == 3
        for i in range(3):
            request_id = f"request-{i}"
            assert request_id in results
            assert results[request_id] >= 0.1 + i * 0.05