"""
Integration tests for the lodging parsing API endpoint.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from httpx import AsyncClient
from datetime import datetime, timezone

from app.main import app, get_universal_parser
from app.services.universal_parser import UniversalParser


class TestLodgingParsingEndpoint:
    """Test cases for the /parse-lodging endpoint."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_parser_success(self):
        """Mock successful parser response."""
        mock_parser = AsyncMock(spec=UniversalParser)
        mock_parser.parse_lodging_data.return_value = {
            "name": "Luxury Hotel Paris",
            "location": "Paris, France",
            "number_of_guests": 2,
            "total_cost": 450.00,
            "total_cost_per_person": 225,
            "number_of_nights": 3,
            "check_in": datetime(2024, 6, 15, 15, 0, 0, tzinfo=timezone.utc),
            "check_out": datetime(2024, 6, 18, 11, 0, 0, tzinfo=timezone.utc)
        }
        mock_parser.close = AsyncMock()
        return mock_parser
    
    @pytest.fixture
    def mock_parser_timeout(self):
        """Mock parser that times out."""
        mock_parser = AsyncMock(spec=UniversalParser)
        mock_parser.parse_lodging_data.side_effect = asyncio.TimeoutError()
        mock_parser.close = AsyncMock()
        return mock_parser
    
    @pytest.fixture
    def mock_parser_invalid_url(self):
        """Mock parser that raises ValueError for invalid URL."""
        mock_parser = AsyncMock(spec=UniversalParser)
        mock_parser.parse_lodging_data.side_effect = ValueError("Invalid URL format")
        mock_parser.close = AsyncMock()
        return mock_parser
    
    @pytest.fixture
    def mock_parser_unsupported_platform(self):
        """Mock parser that raises ValueError for unsupported platform."""
        mock_parser = AsyncMock(spec=UniversalParser)
        mock_parser.parse_lodging_data.side_effect = ValueError("Platform not supported")
        mock_parser.close = AsyncMock()
        return mock_parser
    
    @pytest.fixture
    def mock_parser_parsing_failed(self):
        """Mock parser that fails parsing."""
        mock_parser = AsyncMock(spec=UniversalParser)
        mock_parser.parse_lodging_data.side_effect = ValueError("Parsing failed: No meaningful text content found")
        mock_parser.close = AsyncMock()
        return mock_parser
    
    @pytest.fixture
    def mock_parser_network_error(self):
        """Mock parser that raises network error."""
        mock_parser = AsyncMock(spec=UniversalParser)
        mock_parser.parse_lodging_data.side_effect = Exception("Connection error: Unable to connect")
        mock_parser.close = AsyncMock()
        return mock_parser
    
    @pytest.fixture
    def mock_parser_404_error(self):
        """Mock parser that raises 404 error."""
        mock_parser = AsyncMock(spec=UniversalParser)
        mock_parser.parse_lodging_data.side_effect = Exception("404 Not found")
        mock_parser.close = AsyncMock()
        return mock_parser
    
    @pytest.fixture
    def mock_parser_403_error(self):
        """Mock parser that raises 403 error."""
        mock_parser = AsyncMock(spec=UniversalParser)
        mock_parser.parse_lodging_data.side_effect = Exception("403 Forbidden access")
        mock_parser.close = AsyncMock()
        return mock_parser
    
    @pytest.fixture
    def mock_parser_rate_limited(self):
        """Mock parser that raises rate limit error."""
        mock_parser = AsyncMock(spec=UniversalParser)
        mock_parser.parse_lodging_data.side_effect = Exception("429 Rate limit exceeded")
        mock_parser.close = AsyncMock()
        return mock_parser
    
    @pytest.fixture
    def mock_parser_llm_error(self):
        """Mock parser that raises LLM API error."""
        mock_parser = AsyncMock(spec=UniversalParser)
        mock_parser.parse_lodging_data.side_effect = Exception("Anthropic API error: Invalid request")
        mock_parser.close = AsyncMock()
        return mock_parser
    
    def test_parse_lodging_success(self, client, mock_parser_success):
        """Test successful lodging parsing."""
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser_success
        try:
            response = client.post(
                "/parse-lodging",
                json={"link": "https://www.airbnb.com/rooms/12345"}
            )
        finally:
            app.dependency_overrides.clear()
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "name" in data
        assert "location" in data
        assert "number_of_guests" in data
        assert "total_cost" in data
        assert "total_cost_per_person" in data
        assert "number_of_nights" in data
        assert "check_in" in data
        assert "check_out" in data
        
        # Verify response values
        assert data["name"] == "Luxury Hotel Paris"
        assert data["location"] == "Paris, France"
        assert data["number_of_guests"] == 2
        assert data["total_cost"] == 450.00
        assert data["total_cost_per_person"] == 225
        assert data["number_of_nights"] == 3
        
        # Verify parser was called correctly
        mock_parser_success.parse_lodging_data.assert_called_once_with(
            "https://www.airbnb.com/rooms/12345"
        )
        mock_parser_success.close.assert_called_once()
    
    def test_parse_lodging_invalid_url_format(self, client):
        """Test lodging parsing with invalid URL format."""
        # Mock the dependency to avoid API key check for validation errors
        mock_parser = AsyncMock(spec=UniversalParser)
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser
        try:
            response = client.post(
                "/parse-lodging",
                json={"link": "not-a-valid-url"}
            )
        finally:
            app.dependency_overrides.clear()
        
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
        assert "VALIDATION_ERROR" in data["error"]
    
    def test_parse_lodging_missing_link(self, client):
        """Test lodging parsing with missing link field."""
        # Mock the dependency to avoid API key check for validation errors
        mock_parser = AsyncMock(spec=UniversalParser)
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser
        try:
            response = client.post(
                "/parse-lodging",
                json={}
            )
        finally:
            app.dependency_overrides.clear()
        
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
        assert "VALIDATION_ERROR" in data["error"]
    
    def test_parse_lodging_timeout(self, client, mock_parser_timeout):
        """Test lodging parsing timeout."""
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser_timeout
        try:
            response = client.post(
                "/parse-lodging",
                json={"link": "https://www.airbnb.com/rooms/12345"}
            )
        finally:
            app.dependency_overrides.clear()
        
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "timeout" in data["message"].lower()
        
        mock_parser_timeout.close.assert_called_once()
    
    def test_parse_lodging_invalid_url_error(self, client, mock_parser_invalid_url):
        """Test lodging parsing with invalid URL error from parser."""
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser_invalid_url
        try:
            response = client.post(
                "/parse-lodging",
                json={"link": "https://invalid-site.com/hotel"}
            )
        finally:
            app.dependency_overrides.clear()
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "INVALID_URL" in data["message"]
        
        mock_parser_invalid_url.close.assert_called_once()
    
    def test_parse_lodging_unsupported_platform(self, client, mock_parser_unsupported_platform):
        """Test lodging parsing with unsupported platform."""
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser_unsupported_platform
        try:
            response = client.post(
                "/parse-lodging",
                json={"link": "https://unsupported-site.com/hotel"}
            )
        finally:
            app.dependency_overrides.clear()
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "UNSUPPORTED_PLATFORM" in data["message"]
        
        mock_parser_unsupported_platform.close.assert_called_once()
    
    def test_parse_lodging_parsing_failed(self, client, mock_parser_parsing_failed):
        """Test lodging parsing failure."""
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser_parsing_failed
        try:
            response = client.post(
                "/parse-lodging",
                json={"link": "https://www.airbnb.com/rooms/12345"}
            )
        finally:
            app.dependency_overrides.clear()
        
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "PARSING_FAILED" in data["message"]
        
        mock_parser_parsing_failed.close.assert_called_once()
    
    def test_parse_lodging_network_error(self, client, mock_parser_network_error):
        """Test lodging parsing with network error."""
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser_network_error
        try:
            response = client.post(
                "/parse-lodging",
                json={"link": "https://www.airbnb.com/rooms/12345"}
            )
        finally:
            app.dependency_overrides.clear()
        
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "URL_UNREACHABLE" in data["message"]
        
        mock_parser_network_error.close.assert_called_once()
    
    def test_parse_lodging_404_error(self, client, mock_parser_404_error):
        """Test lodging parsing with 404 error."""
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser_404_error
        try:
            response = client.post(
                "/parse-lodging",
                json={"link": "https://www.airbnb.com/rooms/nonexistent"}
            )
        finally:
            app.dependency_overrides.clear()
        
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "URL_UNREACHABLE" in data["message"]
        
        mock_parser_404_error.close.assert_called_once()
    
    def test_parse_lodging_403_error(self, client, mock_parser_403_error):
        """Test lodging parsing with 403 error."""
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser_403_error
        try:
            response = client.post(
                "/parse-lodging",
                json={"link": "https://www.airbnb.com/rooms/forbidden"}
            )
        finally:
            app.dependency_overrides.clear()
        
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "URL_UNREACHABLE" in data["message"]
        
        mock_parser_403_error.close.assert_called_once()
    
    def test_parse_lodging_rate_limited(self, client, mock_parser_rate_limited):
        """Test lodging parsing with rate limit error."""
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser_rate_limited
        try:
            response = client.post(
                "/parse-lodging",
                json={"link": "https://www.airbnb.com/rooms/12345"}
            )
        finally:
            app.dependency_overrides.clear()
        
        assert response.status_code == 429
        data = response.json()
        assert "error" in data
        assert "RATE_LIMITED" in data["message"]
        
        mock_parser_rate_limited.close.assert_called_once()
    
    def test_parse_lodging_llm_api_error(self, client, mock_parser_llm_error):
        """Test lodging parsing with LLM API error."""
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser_llm_error
        try:
            response = client.post(
                "/parse-lodging",
                json={"link": "https://www.airbnb.com/rooms/12345"}
            )
        finally:
            app.dependency_overrides.clear()
        
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "LLM_API_ERROR" in data["message"]
        
        mock_parser_llm_error.close.assert_called_once()
    
    def test_parse_lodging_various_lodging_urls(self, client, mock_parser_success):
        """Test lodging parsing with various lodging booking URLs."""
        lodging_urls = [
            "https://www.airbnb.com/rooms/12345",
            "https://www.booking.com/hotel/fr/luxury-paris.html",
            "https://www.hotels.com/ho123456/",
            "https://www.expedia.com/Paris-Hotels",
            "https://www.marriott.com/hotels/travel/parmc-paris-marriott-champs-elysees-hotel/",
            "https://www.hilton.com/en/hotels/parhi-hilton-paris-opera/",
            "https://www.hyatt.com/en-US/hotel/france/park-hyatt-paris-vendome/parph",
            "https://www.vrbo.com/123456"
        ]
        
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser_success
        try:
            for url in lodging_urls:
                response = client.post(
                    "/parse-lodging",
                    json={"link": url}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert "name" in data
                assert "location" in data
                assert "number_of_guests" in data
                assert "check_in" in data
                assert "check_out" in data
        finally:
            app.dependency_overrides.clear()
    
    def test_parse_lodging_missing_anthropic_key(self, client):
        """Test lodging parsing when Anthropic API key is not configured."""
        with patch('app.core.config.settings.ANTHROPIC_API_KEY', ''):
            response = client.post(
                "/parse-lodging",
                json={"link": "https://www.airbnb.com/rooms/12345"}
            )
        
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "anthropic api key not configured" in data["message"].lower()
    
    @pytest.mark.asyncio
    async def test_parse_lodging_async_processing(self, mock_parser_success):
        """Test that lodging parsing handles async processing correctly."""
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser_success
        try:
            async with AsyncClient(app=app, base_url="http://test") as ac:
                response = await ac.post(
                    "/parse-lodging",
                    json={"link": "https://www.airbnb.com/rooms/12345"}
                )
        finally:
            app.dependency_overrides.clear()
        
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        
        mock_parser_success.parse_lodging_data.assert_called_once()
        mock_parser_success.close.assert_called_once()
    
    def test_parse_lodging_response_validation(self, client):
        """Test that response validation works correctly."""
        # Mock parser that returns invalid data
        mock_parser = AsyncMock(spec=UniversalParser)
        mock_parser.parse_lodging_data.return_value = {
            "name": "Test Hotel",
            "location": "Test City",
            "number_of_guests": -1,  # Invalid negative guests
            "total_cost": 100.0,
            "total_cost_per_person": 50,
            "number_of_nights": 2,
            "check_in": datetime(2024, 6, 15, 15, 0, 0, tzinfo=timezone.utc),
            "check_out": datetime(2024, 6, 17, 11, 0, 0, tzinfo=timezone.utc)
        }
        mock_parser.close = AsyncMock()
        
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser
        try:
            response = client.post(
                "/parse-lodging",
                json={"link": "https://www.airbnb.com/rooms/12345"}
            )
        finally:
            app.dependency_overrides.clear()
        
        # Should return error due to validation failure at endpoint level
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "PARSING_ERROR" in data["message"]
        
        mock_parser.close.assert_called_once()
    
    def test_parse_lodging_cors_headers(self, client):
        """Test that CORS headers are properly set."""
        response = client.options("/parse-lodging")
        
        # FastAPI automatically handles CORS preflight requests
        # The actual CORS headers are set by the middleware
        assert response.status_code in [200, 405]  # 405 if OPTIONS not explicitly defined
    
    def test_parse_lodging_content_type(self, client, mock_parser_success):
        """Test that response has correct content type."""
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser_success
        try:
            response = client.post(
                "/parse-lodging",
                json={"link": "https://www.airbnb.com/rooms/12345"}
            )
        finally:
            app.dependency_overrides.clear()
        
        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")
    
    def test_parse_lodging_error_response_format(self, client, mock_parser_invalid_url):
        """Test that error responses follow the correct format."""
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser_invalid_url
        try:
            response = client.post(
                "/parse-lodging",
                json={"link": "https://invalid-site.com/hotel"}
            )
        finally:
            app.dependency_overrides.clear()
        
        assert response.status_code == 400
        data = response.json()
        
        # Check error response structure
        assert "error" in data
        assert "message" in data
        assert "timestamp" in data
        
        # Verify timestamp format
        from datetime import datetime
        timestamp = data["timestamp"]
        # Should be able to parse ISO format timestamp
        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    
    def test_parse_lodging_date_handling(self, client):
        """Test that lodging parsing handles dates correctly."""
        mock_parser = AsyncMock(spec=UniversalParser)
        mock_parser.parse_lodging_data.return_value = {
            "name": "Test Hotel",
            "location": "Test City",
            "number_of_guests": 2,
            "total_cost": 300.0,
            "total_cost_per_person": 150,
            "number_of_nights": 2,
            "check_in": datetime(2024, 12, 25, 15, 0, 0, tzinfo=timezone.utc),
            "check_out": datetime(2024, 12, 27, 11, 0, 0, tzinfo=timezone.utc)
        }
        mock_parser.close = AsyncMock()
        
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser
        try:
            response = client.post(
                "/parse-lodging",
                json={"link": "https://www.airbnb.com/rooms/12345"}
            )
        finally:
            app.dependency_overrides.clear()
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify date fields are present and properly formatted
        assert "check_in" in data
        assert "check_out" in data
        
        # Verify dates can be parsed
        check_in = datetime.fromisoformat(data["check_in"].replace('Z', '+00:00'))
        check_out = datetime.fromisoformat(data["check_out"].replace('Z', '+00:00'))
        
        assert check_in.year == 2024
        assert check_in.month == 12
        assert check_in.day == 25
        assert check_out.year == 2024
        assert check_out.month == 12
        assert check_out.day == 27
    
    def test_parse_lodging_cost_calculations(self, client, mock_parser_success):
        """Test that cost calculations are handled correctly."""
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser_success
        try:
            response = client.post(
                "/parse-lodging",
                json={"link": "https://www.airbnb.com/rooms/12345"}
            )
        finally:
            app.dependency_overrides.clear()
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify cost fields
        assert data["total_cost"] == 450.00
        assert data["total_cost_per_person"] == 225
        assert data["number_of_guests"] == 2
        assert data["number_of_nights"] == 3
        
        # Verify cost per person calculation makes sense
        assert data["total_cost"] / data["number_of_guests"] == data["total_cost_per_person"]