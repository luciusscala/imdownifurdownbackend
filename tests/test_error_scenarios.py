"""
Comprehensive error scenario testing for network failures, LLM API errors, and parsing failures.
Tests various failure modes and error handling across the application.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch, Mock
from fastapi.testclient import TestClient
from httpx import AsyncClient
import httpx

from app.main import app, get_universal_parser
from app.services.universal_parser import UniversalParser
from tests.fixtures import ErrorScenarioFixtures, TestDataGenerator


class TestNetworkFailures:
    """Test network-related failure scenarios."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_parser_connection_error(self):
        """Mock parser that raises connection errors."""
        mock_parser = AsyncMock(spec=UniversalParser)
        mock_parser.parse_flight_data.side_effect = httpx.ConnectError("Connection failed")
        mock_parser.parse_lodging_data.side_effect = httpx.ConnectError("Connection failed")
        mock_parser.close = AsyncMock()
        return mock_parser
    
    @pytest.fixture
    def mock_parser_timeout_error(self):
        """Mock parser that raises timeout errors."""
        mock_parser = AsyncMock(spec=UniversalParser)
        mock_parser.parse_flight_data.side_effect = httpx.TimeoutException("Request timeout")
        mock_parser.parse_lodging_data.side_effect = httpx.TimeoutException("Request timeout")
        mock_parser.close = AsyncMock()
        return mock_parser
    
    @pytest.fixture
    def mock_parser_http_error(self):
        """Mock parser that raises HTTP errors."""
        mock_parser = AsyncMock(spec=UniversalParser)
        
        # Create mock response for HTTP errors
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        
        http_error = httpx.HTTPStatusError("404 Not Found", request=Mock(), response=mock_response)
        mock_parser.parse_flight_data.side_effect = http_error
        mock_parser.parse_lodging_data.side_effect = http_error
        mock_parser.close = AsyncMock()
        return mock_parser
    
    @pytest.fixture
    def mock_parser_dns_error(self):
        """Mock parser that raises DNS resolution errors."""
        mock_parser = AsyncMock(spec=UniversalParser)
        mock_parser.parse_flight_data.side_effect = httpx.ConnectError("DNS resolution failed")
        mock_parser.parse_lodging_data.side_effect = httpx.ConnectError("DNS resolution failed")
        mock_parser.close = AsyncMock()
        return mock_parser
    
    def test_connection_error_flight_endpoint(self, client, mock_parser_connection_error):
        """Test flight endpoint handling of connection errors."""
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser_connection_error
        try:
            response = client.post(
                "/parse-flight",
                json={"link": "https://flights.google.com/flights?test=connection_error"}
            )
        finally:
            app.dependency_overrides.clear()
        
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "URL_UNREACHABLE" in data["message"]
        assert "connection" in data["message"].lower()
    
    def test_connection_error_lodging_endpoint(self, client, mock_parser_connection_error):
        """Test lodging endpoint handling of connection errors."""
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser_connection_error
        try:
            response = client.post(
                "/parse-lodging",
                json={"link": "https://www.airbnb.com/rooms/connection_error"}
            )
        finally:
            app.dependency_overrides.clear()
        
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "URL_UNREACHABLE" in data["message"]
    
    def test_timeout_error_handling(self, client, mock_parser_timeout_error):
        """Test timeout error handling."""
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser_timeout_error
        try:
            response = client.post(
                "/parse-flight",
                json={"link": "https://flights.google.com/flights?test=timeout"}
            )
        finally:
            app.dependency_overrides.clear()
        
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "timeout" in data["message"].lower()
    
    def test_http_404_error_handling(self, client, mock_parser_http_error):
        """Test HTTP 404 error handling."""
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser_http_error
        try:
            response = client.post(
                "/parse-flight",
                json={"link": "https://flights.google.com/nonexistent-page"}
            )
        finally:
            app.dependency_overrides.clear()
        
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "URL_UNREACHABLE" in data["message"]
    
    def test_dns_resolution_error(self, client, mock_parser_dns_error):
        """Test DNS resolution error handling."""
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser_dns_error
        try:
            response = client.post(
                "/parse-lodging",
                json={"link": "https://nonexistent-domain-12345.com/hotel"}
            )
        finally:
            app.dependency_overrides.clear()
        
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "URL_UNREACHABLE" in data["message"]
    
    @pytest.mark.asyncio
    async def test_network_error_with_retries(self):
        """Test network error handling with retry logic."""
        from app.services.http_client import AsyncHttpClient
        
        # Mock httpx client to fail first few attempts, then succeed
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            # First two calls fail, third succeeds
            mock_client.get.side_effect = [
                httpx.ConnectError("Connection failed"),
                httpx.ConnectError("Connection failed"),
                Mock(status_code=200, text="<html>Success</html>")
            ]
            
            http_client = AsyncHttpClient()
            
            # Should eventually succeed after retries
            response = await http_client.get("https://example.com/test")
            assert response.status_code == 200
            
            # Verify retry attempts were made
            assert mock_client.get.call_count == 3
    
    def test_multiple_concurrent_network_errors(self, client):
        """Test handling of multiple concurrent network errors."""
        mock_parser = AsyncMock(spec=UniversalParser)
        mock_parser.parse_flight_data.side_effect = httpx.ConnectError("Network error")
        mock_parser.parse_lodging_data.side_effect = httpx.ConnectError("Network error")
        mock_parser.close = AsyncMock()
        
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser
        try:
            # Make multiple concurrent requests that will all fail
            responses = []
            for i in range(5):
                response = client.post(
                    "/parse-flight",
                    json={"link": f"https://flights.google.com/flights?test={i}"}
                )
                responses.append(response)
            
            # All should fail gracefully
            for response in responses:
                assert response.status_code == 500
                data = response.json()
                assert "error" in data
                assert "URL_UNREACHABLE" in data["message"]
        finally:
            app.dependency_overrides.clear()


class TestLLMAPIErrors:
    """Test LLM API error scenarios."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_parser_llm_rate_limit(self):
        """Mock parser that raises LLM API rate limit errors."""
        mock_parser = AsyncMock(spec=UniversalParser)
        mock_parser.parse_flight_data.side_effect = Exception("429 Rate limit exceeded - Anthropic API")
        mock_parser.parse_lodging_data.side_effect = Exception("429 Rate limit exceeded - Anthropic API")
        mock_parser.close = AsyncMock()
        return mock_parser
    
    @pytest.fixture
    def mock_parser_llm_quota_exceeded(self):
        """Mock parser that raises LLM API quota exceeded errors."""
        mock_parser = AsyncMock(spec=UniversalParser)
        mock_parser.parse_flight_data.side_effect = Exception("Quota exceeded - Anthropic API")
        mock_parser.parse_lodging_data.side_effect = Exception("Quota exceeded - Anthropic API")
        mock_parser.close = AsyncMock()
        return mock_parser
    
    @pytest.fixture
    def mock_parser_llm_invalid_key(self):
        """Mock parser that raises invalid API key errors."""
        mock_parser = AsyncMock(spec=UniversalParser)
        mock_parser.parse_flight_data.side_effect = Exception("Invalid API key - Anthropic API")
        mock_parser.parse_lodging_data.side_effect = Exception("Invalid API key - Anthropic API")
        mock_parser.close = AsyncMock()
        return mock_parser
    
    @pytest.fixture
    def mock_parser_llm_service_unavailable(self):
        """Mock parser that raises service unavailable errors."""
        mock_parser = AsyncMock(spec=UniversalParser)
        mock_parser.parse_flight_data.side_effect = Exception("503 Service unavailable - Anthropic API")
        mock_parser.parse_lodging_data.side_effect = Exception("503 Service unavailable - Anthropic API")
        mock_parser.close = AsyncMock()
        return mock_parser
    
    def test_llm_rate_limit_error(self, client, mock_parser_llm_rate_limit):
        """Test LLM API rate limit error handling."""
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser_llm_rate_limit
        try:
            response = client.post(
                "/parse-flight",
                json={"link": "https://flights.google.com/flights?test=rate_limit"}
            )
        finally:
            app.dependency_overrides.clear()
        
        assert response.status_code == 429
        data = response.json()
        assert "error" in data
        assert "RATE_LIMITED" in data["message"]
    
    def test_llm_quota_exceeded_error(self, client, mock_parser_llm_quota_exceeded):
        """Test LLM API quota exceeded error handling."""
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser_llm_quota_exceeded
        try:
            response = client.post(
                "/parse-lodging",
                json={"link": "https://www.airbnb.com/rooms/quota_test"}
            )
        finally:
            app.dependency_overrides.clear()
        
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "LLM_API_ERROR" in data["message"]
    
    def test_llm_invalid_key_error(self, client, mock_parser_llm_invalid_key):
        """Test LLM API invalid key error handling."""
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser_llm_invalid_key
        try:
            response = client.post(
                "/parse-flight",
                json={"link": "https://flights.google.com/flights?test=invalid_key"}
            )
        finally:
            app.dependency_overrides.clear()
        
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "LLM_API_ERROR" in data["message"]
    
    def test_llm_service_unavailable_error(self, client, mock_parser_llm_service_unavailable):
        """Test LLM API service unavailable error handling."""
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser_llm_service_unavailable
        try:
            response = client.post(
                "/parse-lodging",
                json={"link": "https://www.booking.com/hotel/service_unavailable"}
            )
        finally:
            app.dependency_overrides.clear()
        
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "LLM_API_ERROR" in data["message"]
    
    @pytest.mark.asyncio
    async def test_llm_api_error_with_fallback(self):
        """Test LLM API error handling with fallback mechanisms."""
        from app.services.llm_data_extractor import LLMDataExtractor
        
        with patch('anthropic.Anthropic') as mock_anthropic:
            # Mock Anthropic client to raise API error
            mock_client = mock_anthropic.return_value
            mock_client.messages.create.side_effect = Exception("API Error")
            
            extractor = LLMDataExtractor(api_key="test-key")
            
            # Should raise ValueError with descriptive message
            with pytest.raises(ValueError, match="Failed to extract flight data"):
                await extractor.extract_flight_data("test content")
    
    def test_llm_malformed_response_handling(self, client):
        """Test handling of malformed LLM responses."""
        mock_parser = AsyncMock(spec=UniversalParser)
        
        # Mock parser to return malformed data
        mock_parser.parse_flight_data.side_effect = ValueError("Failed to extract flight data: Invalid JSON response")
        mock_parser.close = AsyncMock()
        
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser
        try:
            response = client.post(
                "/parse-flight",
                json={"link": "https://flights.google.com/flights?test=malformed"}
            )
        finally:
            app.dependency_overrides.clear()
        
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "PARSING_FAILED" in data["message"]


class TestParsingFailures:
    """Test parsing failure scenarios."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_parser_no_content(self):
        """Mock parser that finds no meaningful content."""
        mock_parser = AsyncMock(spec=UniversalParser)
        mock_parser.parse_flight_data.side_effect = ValueError("Parsing failed: No meaningful text content found")
        mock_parser.parse_lodging_data.side_effect = ValueError("Parsing failed: No meaningful text content found")
        mock_parser.close = AsyncMock()
        return mock_parser
    
    @pytest.fixture
    def mock_parser_invalid_data(self):
        """Mock parser that extracts invalid data."""
        mock_parser = AsyncMock(spec=UniversalParser)
        mock_parser.parse_flight_data.side_effect = ValueError("Parsing failed: Invalid data format")
        mock_parser.parse_lodging_data.side_effect = ValueError("Parsing failed: Invalid data format")
        mock_parser.close = AsyncMock()
        return mock_parser
    
    @pytest.fixture
    def mock_parser_missing_fields(self):
        """Mock parser that returns data with missing required fields."""
        mock_parser = AsyncMock(spec=UniversalParser)
        
        # Return incomplete data that should fail validation
        mock_parser.parse_flight_data.return_value = {
            "origin_airport": "JFK"
            # Missing other required fields
        }
        mock_parser.parse_lodging_data.return_value = {
            "name": "Test Hotel"
            # Missing other required fields
        }
        mock_parser.close = AsyncMock()
        return mock_parser
    
    def test_no_content_parsing_failure(self, client, mock_parser_no_content):
        """Test parsing failure when no meaningful content is found."""
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser_no_content
        try:
            response = client.post(
                "/parse-flight",
                json={"link": "https://flights.google.com/flights?test=no_content"}
            )
        finally:
            app.dependency_overrides.clear()
        
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "PARSING_FAILED" in data["message"]
        assert "no meaningful text content" in data["message"].lower()
    
    def test_invalid_data_parsing_failure(self, client, mock_parser_invalid_data):
        """Test parsing failure when data format is invalid."""
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser_invalid_data
        try:
            response = client.post(
                "/parse-lodging",
                json={"link": "https://www.airbnb.com/rooms/invalid_data"}
            )
        finally:
            app.dependency_overrides.clear()
        
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "PARSING_FAILED" in data["message"]
    
    def test_missing_required_fields_failure(self, client, mock_parser_missing_fields):
        """Test parsing failure when required fields are missing."""
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser_missing_fields
        try:
            response = client.post(
                "/parse-flight",
                json={"link": "https://flights.google.com/flights?test=missing_fields"}
            )
        finally:
            app.dependency_overrides.clear()
        
        # Should fail validation and return error
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "PARSING_ERROR" in data["message"]
    
    @pytest.mark.asyncio
    async def test_text_extraction_failure(self):
        """Test text extraction failure scenarios."""
        from app.services.text_extractor import TextExtractor
        
        extractor = TextExtractor()
        
        # Test with empty HTML
        empty_html = "<html><body></body></html>"
        result = extractor.extract_text(empty_html)
        assert result.strip() == ""
        
        # Test with malformed HTML
        malformed_html = "<html><body><div>Unclosed div"
        result = extractor.extract_text(malformed_html)
        assert "Unclosed div" in result
    
    def test_unsupported_platform_error(self, client):
        """Test error handling for unsupported platforms."""
        mock_parser = AsyncMock(spec=UniversalParser)
        mock_parser.parse_flight_data.side_effect = ValueError("Platform not supported")
        mock_parser.close = AsyncMock()
        
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser
        try:
            response = client.post(
                "/parse-flight",
                json={"link": "https://unsupported-platform.com/flights"}
            )
        finally:
            app.dependency_overrides.clear()
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "UNSUPPORTED_PLATFORM" in data["message"]
    
    def test_javascript_required_page_failure(self, client):
        """Test parsing failure for JavaScript-heavy pages."""
        mock_parser = AsyncMock(spec=UniversalParser)
        mock_parser.parse_flight_data.side_effect = ValueError("Parsing failed: Page requires JavaScript")
        mock_parser.close = AsyncMock()
        
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser
        try:
            response = client.post(
                "/parse-flight",
                json={"link": "https://flights.google.com/flights?js_required=1"}
            )
        finally:
            app.dependency_overrides.clear()
        
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "PARSING_FAILED" in data["message"]


class TestErrorScenarioIntegration:
    """Integration tests for comprehensive error scenarios."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_error_scenarios_from_fixtures(self, client):
        """Test error scenarios using fixture data."""
        error_scenarios = TestDataGenerator.get_error_scenarios()
        
        for scenario in error_scenarios[:10]:  # Test first 10 scenarios
            if scenario["url"] is None:
                continue  # Skip None URLs as they cause different validation errors
            
            # Create appropriate mock parser for the scenario
            mock_parser = AsyncMock(spec=UniversalParser)
            
            if scenario["type"] == "invalid_url":
                # For invalid URLs, the validation happens before parser is called
                pass
            elif scenario["type"] == "unreachable_url":
                mock_parser.parse_flight_data.side_effect = Exception("Connection error")
                mock_parser.parse_lodging_data.side_effect = Exception("Connection error")
            elif scenario["type"] == "unsupported_platform":
                mock_parser.parse_flight_data.side_effect = ValueError("Platform not supported")
                mock_parser.parse_lodging_data.side_effect = ValueError("Platform not supported")
            
            mock_parser.close = AsyncMock()
            
            app.dependency_overrides[get_universal_parser] = lambda: mock_parser
            try:
                # Test with flight endpoint
                response = client.post(
                    "/parse-flight",
                    json={"link": scenario["url"]}
                )
                
                # Verify expected error response
                if scenario["expected_status"] == 422:
                    assert response.status_code == 422
                    data = response.json()
                    assert "error" in data
                else:
                    assert response.status_code == scenario["expected_status"]
                    data = response.json()
                    assert "error" in data
                    
            finally:
                app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_cascading_error_scenarios(self):
        """Test cascading error scenarios where multiple things go wrong."""
        from app.services.universal_parser import UniversalParser
        from app.services.http_client import AsyncHttpClient
        from app.services.text_extractor import TextExtractor
        from app.services.llm_data_extractor import LLMDataExtractor
        
        # Test scenario: Network error followed by LLM error on retry
        with patch('httpx.AsyncClient') as mock_http_client:
            mock_client = AsyncMock()
            mock_http_client.return_value.__aenter__.return_value = mock_client
            
            # First call fails with network error, second succeeds but returns empty content
            mock_client.get.side_effect = [
                httpx.ConnectError("Network error"),
                Mock(status_code=200, text="<html><body></body></html>")
            ]
            
            with patch('anthropic.Anthropic') as mock_anthropic:
                mock_anthropic_client = mock_anthropic.return_value
                mock_anthropic_client.messages.create.side_effect = Exception("LLM API error")
                
                http_client = AsyncHttpClient()
                text_extractor = TextExtractor()
                llm_extractor = LLMDataExtractor(api_key="test-key")
                
                parser = UniversalParser(http_client, text_extractor, llm_extractor)
                
                # Should handle both network and LLM errors gracefully
                with pytest.raises(ValueError):
                    await parser.parse_flight_data("https://example.com/flight")
    
    def test_error_response_consistency(self, client):
        """Test that all error responses follow consistent format."""
        error_scenarios = [
            ("invalid_url", {"link": "not-a-url"}),
            ("missing_field", {}),
        ]
        
        for scenario_name, request_data in error_scenarios:
            response = client.post("/parse-flight", json=request_data)
            
            # All error responses should have consistent structure
            assert response.status_code in [400, 422, 500]
            data = response.json()
            
            # Check required error response fields
            assert "error" in data
            assert "message" in data
            assert "timestamp" in data
            
            # Verify timestamp format
            from datetime import datetime
            timestamp = data["timestamp"]
            # Should be able to parse ISO format timestamp
            datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    
    def test_error_logging_integration(self, client):
        """Test that errors are properly logged."""
        with patch('app.core.error_handler.logger') as mock_logger:
            mock_parser = AsyncMock(spec=UniversalParser)
            mock_parser.parse_flight_data.side_effect = Exception("Test error for logging")
            mock_parser.close = AsyncMock()
            
            app.dependency_overrides[get_universal_parser] = lambda: mock_parser
            try:
                response = client.post(
                    "/parse-flight",
                    json={"link": "https://flights.google.com/flights?test=logging"}
                )
            finally:
                app.dependency_overrides.clear()
            
            assert response.status_code == 500
            
            # Verify error was logged
            mock_logger.error.assert_called()
            
            # Check that log contains relevant information
            log_call_args = mock_logger.error.call_args
            log_message = str(log_call_args)
            assert "Test error for logging" in log_message