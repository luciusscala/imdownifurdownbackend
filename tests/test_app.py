"""Integration tests for FastAPI application, CORS, and middleware."""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone
from app.main import app


@pytest.fixture
def client():
    """Create test client for FastAPI application."""
    return TestClient(app)


class TestApplicationConfiguration:
    """Test cases for basic application configuration."""
    
    def test_app_title_and_version(self, client):
        """Test that app has correct title and version."""
        response = client.get("/docs")
        assert response.status_code == 200
        # The OpenAPI spec should contain our app info
        openapi_response = client.get("/openapi.json")
        assert openapi_response.status_code == 200
        openapi_data = openapi_response.json()
        
        assert openapi_data["info"]["title"] == "Travel Data Parser API"
        assert openapi_data["info"]["version"] == "1.0.0"
        assert "API for parsing travel booking data from various platforms" in openapi_data["info"]["description"]
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns correct information."""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "Travel Data Parser API"
        assert data["version"] == "1.0.0"
        assert data["docs"] == "/docs"
    
    def test_health_check_endpoint(self, client):
        """Test health check endpoint returns correct status."""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "travel-data-parser"


class TestCORSFunctionality:
    """Test cases for CORS middleware functionality."""
    
    def test_cors_preflight_request(self, client):
        """Test CORS preflight OPTIONS request."""
        headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type"
        }
        
        response = client.options("/health", headers=headers)
        assert response.status_code == 200
        
        # Check CORS headers
        assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
        assert "POST" in response.headers.get("access-control-allow-methods", "")
        assert "content-type" in response.headers.get("access-control-allow-headers", "").lower()
    
    def test_cors_actual_request_from_allowed_origin(self, client):
        """Test actual request from allowed origin includes CORS headers."""
        headers = {"Origin": "http://localhost:3000"}
        
        response = client.get("/health", headers=headers)
        assert response.status_code == 200
        
        # Check CORS headers in response
        assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
        assert response.headers.get("access-control-allow-credentials") == "true"
    
    def test_cors_post_request_from_allowed_origin(self, client):
        """Test POST request from allowed origin includes CORS headers."""
        headers = {
            "Origin": "http://localhost:3000",
            "Content-Type": "application/json"
        }
        
        # Test with a simple POST to root (even though it's not implemented)
        response = client.post("/", json={}, headers=headers)
        
        # Even if endpoint doesn't exist, CORS headers should be present
        assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
        assert response.headers.get("access-control-allow-credentials") == "true"
    
    def test_cors_request_from_disallowed_origin(self, client):
        """Test request from disallowed origin doesn't include CORS headers."""
        headers = {"Origin": "http://malicious-site.com"}
        
        response = client.get("/health", headers=headers)
        assert response.status_code == 200
        
        # CORS headers should not be present for disallowed origins
        assert response.headers.get("access-control-allow-origin") is None
    
    def test_cors_without_origin_header(self, client):
        """Test request without Origin header works normally."""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"


class TestGlobalExceptionHandlers:
    """Test cases for global exception handlers."""
    
    def test_404_not_found_exception_handler(self, client):
        """Test 404 exception returns consistent error format."""
        response = client.get("/nonexistent-endpoint")
        assert response.status_code == 404
        
        data = response.json()
        assert "error" in data
        assert "message" in data
        assert "timestamp" in data
        
        assert data["error"] == "HTTP_404"
        assert "Not Found" in data["message"]
        
        # Validate timestamp format
        timestamp = datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
        assert isinstance(timestamp, datetime)
    
    def test_405_method_not_allowed_exception_handler(self, client):
        """Test 405 exception returns consistent error format."""
        # Try to POST to GET-only endpoint
        response = client.post("/health")
        assert response.status_code == 405
        
        data = response.json()
        assert "error" in data
        assert "message" in data
        assert "timestamp" in data
        
        assert data["error"] == "HTTP_405"
        assert "Method Not Allowed" in data["message"]
    
    def test_422_validation_error_exception_handler(self, client):
        """Test validation error returns consistent error format."""
        # Create a mock endpoint that expects JSON but send invalid data
        # Since we don't have endpoints yet, we'll test with malformed JSON
        headers = {"Content-Type": "application/json"}
        
        # Send malformed JSON to trigger validation error
        response = client.post("/", data="invalid-json", headers=headers)
        
        # Should get a validation error or similar
        assert response.status_code in [400, 422, 405]  # Could be method not allowed since POST / doesn't exist
        
        data = response.json()
        assert "error" in data
        assert "message" in data
        assert "timestamp" in data
    
    def test_exception_handler_includes_timestamp(self, client):
        """Test that all exception handlers include proper timestamp."""
        response = client.get("/nonexistent")
        assert response.status_code == 404
        
        data = response.json()
        timestamp_str = data["timestamp"]
        
        # Parse timestamp and verify it's recent
        timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        time_diff = now - timestamp
        
        # Timestamp should be within the last minute
        assert time_diff.total_seconds() < 60
        assert time_diff.total_seconds() >= 0
    
    def test_exception_handler_cors_headers_preserved(self, client):
        """Test that exception handlers preserve CORS headers."""
        headers = {"Origin": "http://localhost:3000"}
        
        response = client.get("/nonexistent", headers=headers)
        assert response.status_code == 404
        
        # CORS headers should still be present even in error responses
        assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
        
        # Response should still have consistent error format
        data = response.json()
        assert data["error"] == "HTTP_404"


class TestApplicationStartup:
    """Test cases for application startup and configuration."""
    
    def test_application_can_start(self, client):
        """Test that application starts successfully."""
        # If we can make any request, the app started successfully
        response = client.get("/health")
        assert response.status_code == 200
    
    def test_openapi_documentation_available(self, client):
        """Test that OpenAPI documentation is available."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        openapi_data = response.json()
        assert "openapi" in openapi_data
        assert "info" in openapi_data
        assert "paths" in openapi_data
        
        # Should have our health endpoint documented
        assert "/health" in openapi_data["paths"]
        assert "get" in openapi_data["paths"]["/health"]
    
    def test_docs_ui_available(self, client):
        """Test that Swagger UI documentation is available."""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
    
    def test_redoc_ui_available(self, client):
        """Test that ReDoc UI documentation is available."""
        response = client.get("/redoc")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")


class TestMiddlewareIntegration:
    """Test cases for middleware integration."""
    
    def test_cors_middleware_order(self, client):
        """Test that CORS middleware is properly configured."""
        # Make a preflight request to ensure CORS middleware is active
        headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Content-Type"
        }
        
        response = client.options("/health", headers=headers)
        assert response.status_code == 200
        
        # CORS headers should be present
        required_cors_headers = [
            "access-control-allow-origin",
            "access-control-allow-methods"
        ]
        
        for header in required_cors_headers:
            assert header in response.headers
        
        # Check specific values
        assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
        assert "GET" in response.headers.get("access-control-allow-methods", "")
    
    def test_exception_handling_with_cors(self, client):
        """Test that exception handling works correctly with CORS middleware."""
        headers = {"Origin": "http://localhost:3000"}
        
        # Trigger a 404 error
        response = client.get("/does-not-exist", headers=headers)
        assert response.status_code == 404
        
        # Should have both error response format AND CORS headers
        data = response.json()
        assert data["error"] == "HTTP_404"
        assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"