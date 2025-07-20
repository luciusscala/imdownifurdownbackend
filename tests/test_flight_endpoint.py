"""
Integration tests for the flight parsing API endpoint.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.main import app, get_universal_parser
from app.services.universal_parser import UniversalParser


class TestFlightParsingEndpoint:
    """Test cases for the /parse-flight endpoint."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_parser_success(self):
        """Mock successful parser response."""
        mock_parser = AsyncMock(spec=UniversalParser)
        mock_parser.parse_flight_data.return_value = {
            "origin_airport": "JFK",
            "destination_airport": "CDG",
            "duration": 480,
            "total_cost": 1200.50,
            "total_cost_per_person": 600.25,
            "segment": 1,
            "flight_number": "AF123"
        }
        mock_parser.close = AsyncMock()
        return mock_parser
    
    @pytest.fixture
    def mock_parser_timeout(self):
        """Mock parser that times out."""
        mock_parser = AsyncMock(spec=UniversalParser)
        mock_parser.parse_flight_data.side_effect = asyncio.TimeoutError()
        mock_parser.close = AsyncMock()
        return mock_parser
    
    @pytest.fixture
    def mock_parser_invalid_url(self):
        """Mock parser that raises ValueError for invalid URL."""
        mock_parser = AsyncMock(spec=UniversalParser)
        mock_parser.parse_flight_data.side_effect = ValueError("Invalid URL format")
        mock_parser.close = AsyncMock()
        return mock_parser
    
    @pytest.fixture
    def mock_parser_parsing_failed(self):
        """Mock parser that fails parsing."""
        mock_parser = AsyncMock(spec=UniversalParser)
        mock_parser.parse_flight_data.side_effect = ValueError("Parsing failed: No meaningful text content found")
        mock_parser.close = AsyncMock()
        return mock_parser
    
    @pytest.fixture
    def mock_parser_network_error(self):
        """Mock parser that raises network error."""
        mock_parser = AsyncMock(spec=UniversalParser)
        mock_parser.parse_flight_data.side_effect = Exception("Connection error: Unable to connect")
        mock_parser.close = AsyncMock()
        return mock_parser
    
    @pytest.fixture
    def mock_parser_rate_limited(self):
        """Mock parser that raises rate limit error."""
        mock_parser = AsyncMock(spec=UniversalParser)
        mock_parser.parse_flight_data.side_effect = Exception("429 Rate limit exceeded")
        mock_parser.close = AsyncMock()
        return mock_parser
    
    @pytest.fixture
    def mock_parser_llm_error(self):
        """Mock parser that raises LLM API error."""
        mock_parser = AsyncMock(spec=UniversalParser)
        mock_parser.parse_flight_data.side_effect = Exception("Anthropic API error: Invalid request")
        mock_parser.close = AsyncMock()
        return mock_parser
    
    def test_parse_flight_success(self, client, mock_parser_success):
        """Test successful flight parsing."""
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser_success
        try:
            response = client.post(
                "/parse-flight",
                json={"link": "https://flights.google.com/flights?hl=en&curr=USD"}
            )
        finally:
            app.dependency_overrides.clear()
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "origin_airport" in data
        assert "destination_airport" in data
        assert "duration" in data
        assert "total_cost" in data
        assert "total_cost_per_person" in data
        assert "segment" in data
        assert "flight_number" in data
        
        # Verify response values
        assert data["origin_airport"] == "JFK"
        assert data["destination_airport"] == "CDG"
        assert data["duration"] == 480
        assert data["total_cost"] == 1200.50
        assert data["total_cost_per_person"] == 600.25
        assert data["segment"] == 1
        assert data["flight_number"] == "AF123"
        
        # Verify parser was called correctly
        mock_parser_success.parse_flight_data.assert_called_once_with(
            "https://flights.google.com/flights?hl=en&curr=USD"
        )
        mock_parser_success.close.assert_called_once()
    
    def test_parse_flight_invalid_url_format(self, client):
        """Test flight parsing with invalid URL format."""
        # Mock the dependency to avoid API key check for validation errors
        mock_parser = AsyncMock(spec=UniversalParser)
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser
        try:
            response = client.post(
                "/parse-flight",
                json={"link": "not-a-valid-url"}
            )
        finally:
            app.dependency_overrides.clear()
        
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
        assert "VALIDATION_ERROR" in data["error"]
    
    def test_parse_flight_missing_link(self, client):
        """Test flight parsing with missing link field."""
        # Mock the dependency to avoid API key check for validation errors
        mock_parser = AsyncMock(spec=UniversalParser)
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser
        try:
            response = client.post(
                "/parse-flight",
                json={}
            )
        finally:
            app.dependency_overrides.clear()
        
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
        assert "VALIDATION_ERROR" in data["error"]
    
    def test_parse_flight_timeout(self, client, mock_parser_timeout):
        """Test flight parsing timeout."""
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser_timeout
        try:
            response = client.post(
                "/parse-flight",
                json={"link": "https://flights.google.com/flights?hl=en&curr=USD"}
            )
        finally:
            app.dependency_overrides.clear()
        
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "timeout" in data["message"].lower()
        
        mock_parser_timeout.close.assert_called_once()
    
    def test_parse_flight_invalid_url_error(self, client, mock_parser_invalid_url):
        """Test flight parsing with invalid URL error from parser."""
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser_invalid_url
        try:
            response = client.post(
                "/parse-flight",
                json={"link": "https://invalid-site.com/flight"}
            )
        finally:
            app.dependency_overrides.clear()
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "INVALID_URL" in data["message"]
        
        mock_parser_invalid_url.close.assert_called_once()
    
    def test_parse_flight_parsing_failed(self, client, mock_parser_parsing_failed):
        """Test flight parsing failure."""
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser_parsing_failed
        try:
            response = client.post(
                "/parse-flight",
                json={"link": "https://flights.google.com/flights?hl=en&curr=USD"}
            )
        finally:
            app.dependency_overrides.clear()
        
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "PARSING_FAILED" in data["message"]
        
        mock_parser_parsing_failed.close.assert_called_once()
    
    def test_parse_flight_network_error(self, client, mock_parser_network_error):
        """Test flight parsing with network error."""
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser_network_error
        try:
            response = client.post(
                "/parse-flight",
                json={"link": "https://flights.google.com/flights?hl=en&curr=USD"}
            )
        finally:
            app.dependency_overrides.clear()
        
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "URL_UNREACHABLE" in data["message"]
        
        mock_parser_network_error.close.assert_called_once()
    
    def test_parse_flight_rate_limited(self, client, mock_parser_rate_limited):
        """Test flight parsing with rate limit error."""
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser_rate_limited
        try:
            response = client.post(
                "/parse-flight",
                json={"link": "https://flights.google.com/flights?hl=en&curr=USD"}
            )
        finally:
            app.dependency_overrides.clear()
        
        assert response.status_code == 429
        data = response.json()
        assert "error" in data
        assert "RATE_LIMITED" in data["message"]
        
        mock_parser_rate_limited.close.assert_called_once()
    
    def test_parse_flight_llm_api_error(self, client, mock_parser_llm_error):
        """Test flight parsing with LLM API error."""
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser_llm_error
        try:
            response = client.post(
                "/parse-flight",
                json={"link": "https://flights.google.com/flights?hl=en&curr=USD"}
            )
        finally:
            app.dependency_overrides.clear()
        
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "LLM_API_ERROR" in data["message"]
        
        mock_parser_llm_error.close.assert_called_once()
    
    def test_parse_flight_various_flight_urls(self, client, mock_parser_success):
        """Test flight parsing with various flight booking URLs."""
        flight_urls = [
            "https://flights.google.com/flights?hl=en&curr=USD",
            "https://www.expedia.com/Flights",
            "https://www.kayak.com/flights",
            "https://www.united.com/ual/en/us/flight-search",
            "https://www.delta.com/flight-search",
            "https://www.american.com/booking/flights",
            "https://www.lufthansa.com/us/en/flight-search"
        ]
        
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser_success
        try:
            for url in flight_urls:
                response = client.post(
                    "/parse-flight",
                    json={"link": url}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert "origin_airport" in data
                assert "destination_airport" in data
                assert "flight_number" in data
        finally:
            app.dependency_overrides.clear()
    
    def test_parse_flight_missing_anthropic_key(self, client):
        """Test flight parsing when Anthropic API key is not configured."""
        with patch('app.core.config.settings.ANTHROPIC_API_KEY', ''):
            response = client.post(
                "/parse-flight",
                json={"link": "https://flights.google.com/flights?hl=en&curr=USD"}
            )
        
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "anthropic api key not configured" in data["message"].lower()
    
    @pytest.mark.asyncio
    async def test_parse_flight_async_processing(self, mock_parser_success):
        """Test that flight parsing handles async processing correctly."""
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser_success
        try:
            async with AsyncClient(app=app, base_url="http://test") as ac:
                response = await ac.post(
                    "/parse-flight",
                    json={"link": "https://flights.google.com/flights?hl=en&curr=USD"}
                )
        finally:
            app.dependency_overrides.clear()
        
        assert response.status_code == 200
        data = response.json()
        assert "origin_airport" in data
        
        mock_parser_success.parse_flight_data.assert_called_once()
        mock_parser_success.close.assert_called_once()
    
    def test_parse_flight_response_validation(self, client):
        """Test that response validation works correctly."""
        # Mock parser that returns invalid data
        mock_parser = AsyncMock(spec=UniversalParser)
        mock_parser.parse_flight_data.return_value = {
            "origin_airport": "JFK",
            "destination_airport": "CDG",
            "duration": -100,  # Invalid negative duration
            "total_cost": 1200.50,
            "total_cost_per_person": 600.25,
            "segment": 1,
            "flight_number": "AF123"
        }
        mock_parser.close = AsyncMock()
        
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser
        try:
            response = client.post(
                "/parse-flight",
                json={"link": "https://flights.google.com/flights?hl=en&curr=USD"}
            )
        finally:
            app.dependency_overrides.clear()
        
        # Should return error due to validation failure at endpoint level
        # The endpoint validates the response from the parser
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "PARSING_ERROR" in data["message"]
        
        mock_parser.close.assert_called_once()
    
    def test_parse_flight_cors_headers(self, client):
        """Test that CORS headers are properly set."""
        response = client.options("/parse-flight")
        
        # FastAPI automatically handles CORS preflight requests
        # The actual CORS headers are set by the middleware
        assert response.status_code in [200, 405]  # 405 if OPTIONS not explicitly defined
    
    def test_parse_flight_content_type(self, client, mock_parser_success):
        """Test that response has correct content type."""
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser_success
        try:
            response = client.post(
                "/parse-flight",
                json={"link": "https://flights.google.com/flights?hl=en&curr=USD"}
            )
        finally:
            app.dependency_overrides.clear()
        
        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")
    
    def test_parse_flight_error_response_format(self, client, mock_parser_invalid_url):
        """Test that error responses follow the correct format."""
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser_invalid_url
        try:
            response = client.post(
                "/parse-flight",
                json={"link": "https://invalid-site.com/flight"}
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