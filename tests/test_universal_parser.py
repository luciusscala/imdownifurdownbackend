"""
Integration tests for UniversalParser service.
Tests the combination of web scraping and LLM extraction.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime

from app.services.universal_parser import UniversalParser
from app.services.http_client import AsyncHttpClient
from app.services.text_extractor import TextExtractor
from app.services.llm_data_extractor import LLMDataExtractor


class TestUniversalParser:
    """Test suite for UniversalParser service."""
    
    @pytest.fixture
    def mock_http_client(self):
        """Mock HTTP client for testing."""
        client = AsyncMock(spec=AsyncHttpClient)
        return client
    
    @pytest.fixture
    def mock_text_extractor(self):
        """Mock text extractor for testing."""
        extractor = Mock(spec=TextExtractor)
        return extractor
    
    @pytest.fixture
    def mock_llm_extractor(self):
        """Mock LLM data extractor for testing."""
        extractor = AsyncMock(spec=LLMDataExtractor)
        return extractor
    
    @pytest.fixture
    def universal_parser(self, mock_http_client, mock_text_extractor, mock_llm_extractor):
        """Create UniversalParser instance with mocked dependencies."""
        return UniversalParser(
            anthropic_api_key="test-api-key",
            http_client=mock_http_client,
            text_extractor=mock_text_extractor,
            llm_extractor=mock_llm_extractor
        )
    
    @pytest.mark.asyncio
    async def test_scrape_and_extract_text_success(self, universal_parser, mock_http_client, mock_text_extractor):
        """Test successful text extraction from URL."""
        # Arrange
        url = "https://flights.google.com/test-flight"
        html_content = "<html><body>Flight from JFK to CDG</body></html>"
        clean_text = "Flight from JFK to CDG"
        
        mock_response = Mock()
        mock_response.text = html_content
        mock_response.raise_for_status = Mock()
        mock_http_client.get.return_value = mock_response
        mock_text_extractor.extract_text.return_value = clean_text
        
        # Act
        result = await universal_parser.scrape_and_extract_text(url)
        
        # Assert
        assert result == clean_text
        mock_http_client.get.assert_called_once_with(url)
        mock_text_extractor.extract_text.assert_called_once_with(html_content, url)
    
    @pytest.mark.asyncio
    async def test_scrape_and_extract_text_invalid_url(self, universal_parser):
        """Test text extraction with invalid URL."""
        # Arrange
        invalid_url = "not-a-valid-url"
        
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid URL format"):
            await universal_parser.scrape_and_extract_text(invalid_url)
    
    @pytest.mark.asyncio
    async def test_scrape_and_extract_text_empty_content(self, universal_parser, mock_http_client, mock_text_extractor):
        """Test text extraction with empty content."""
        # Arrange
        url = "https://example.com/empty"
        
        mock_response = Mock()
        mock_response.text = "<html></html>"
        mock_response.raise_for_status = Mock()
        mock_http_client.get.return_value = mock_response
        mock_text_extractor.extract_text.return_value = ""
        
        # Act & Assert
        with pytest.raises(ValueError, match="No meaningful text content found"):
            await universal_parser.scrape_and_extract_text(url)
    
    @pytest.mark.asyncio
    async def test_parse_flight_data_success(self, universal_parser, mock_http_client, mock_text_extractor, mock_llm_extractor):
        """Test successful flight data parsing."""
        # Arrange
        url = "https://flights.google.com/test-flight"
        clean_text = "Flight JFK to CDG, 8 hours, $1200"
        flight_data = {
            "origin_airport": "JFK",
            "destination_airport": "CDG",
            "duration": 480,
            "total_cost": 1200.0,
            "total_cost_per_person": 1200.0,
            "segment": 1,
            "flight_number": "AF123"
        }
        
        mock_response = Mock()
        mock_response.text = "<html><body>Flight data</body></html>"
        mock_response.raise_for_status = Mock()
        mock_http_client.get.return_value = mock_response
        mock_text_extractor.extract_text.return_value = clean_text
        mock_llm_extractor.extract_flight_data.return_value = flight_data
        
        # Act
        result = await universal_parser.parse_flight_data(url)
        
        # Assert
        assert result == flight_data
        mock_llm_extractor.extract_flight_data.assert_called_once_with(clean_text)
    
    @pytest.mark.asyncio
    async def test_parse_flight_data_validation_error(self, universal_parser, mock_http_client, mock_text_extractor, mock_llm_extractor):
        """Test flight data parsing with validation error handling."""
        # Arrange
        url = "https://flights.google.com/test-flight"
        clean_text = "Flight data"
        invalid_flight_data = {
            "origin_airport": "JFK",
            "destination_airport": "CDG",
            "duration": -100,  # Invalid negative duration
            "total_cost": "invalid",  # Invalid cost type
            "segment": 1,
            "flight_number": "AF123"
        }
        
        mock_response = Mock()
        mock_response.text = "<html><body>Flight data</body></html>"
        mock_response.raise_for_status = Mock()
        mock_http_client.get.return_value = mock_response
        mock_text_extractor.extract_text.return_value = clean_text
        mock_llm_extractor.extract_flight_data.return_value = invalid_flight_data
        
        # Act
        result = await universal_parser.parse_flight_data(url)
        
        # Assert - Should return fallback values
        assert result["origin_airport"] == "JFK"
        assert result["destination_airport"] == "CDG"
        assert result["duration"] == 0  # Fallback for negative value
        assert result["total_cost"] == 0.0  # Fallback for invalid type
        assert result["segment"] == 1
        assert result["flight_number"] == "AF123"
    
    @pytest.mark.asyncio
    async def test_parse_lodging_data_success(self, universal_parser, mock_http_client, mock_text_extractor, mock_llm_extractor):
        """Test successful lodging data parsing."""
        # Arrange
        url = "https://airbnb.com/test-listing"
        clean_text = "Luxury Hotel Paris, 2 guests, 3 nights, $450"
        lodging_data = {
            "name": "Luxury Hotel Paris",
            "location": "Paris, France",
            "number_of_guests": 2,
            "total_cost": 450.0,
            "total_cost_per_person": 225,
            "number_of_nights": 3,
            "check_in": datetime.fromisoformat("2024-06-15T15:00:00+02:00"),
            "check_out": datetime.fromisoformat("2024-06-18T11:00:00+02:00")
        }
        
        mock_response = Mock()
        mock_response.text = "<html><body>Hotel data</body></html>"
        mock_response.raise_for_status = Mock()
        mock_http_client.get.return_value = mock_response
        mock_text_extractor.extract_text.return_value = clean_text
        mock_llm_extractor.extract_lodging_data.return_value = lodging_data
        
        # Act
        result = await universal_parser.parse_lodging_data(url)
        
        # Assert
        assert result == lodging_data
        mock_llm_extractor.extract_lodging_data.assert_called_once_with(clean_text)
    
    @pytest.mark.asyncio
    async def test_parse_lodging_data_validation_error(self, universal_parser, mock_http_client, mock_text_extractor, mock_llm_extractor):
        """Test lodging data parsing with validation error handling."""
        # Arrange
        url = "https://booking.com/test-hotel"
        clean_text = "Hotel data"
        invalid_lodging_data = {
            "name": "Test Hotel",
            "location": "Test City",
            "number_of_guests": 0,  # Invalid - must be >= 1
            "total_cost": -100.0,  # Invalid negative cost
            "total_cost_per_person": "invalid",  # Invalid type
            "number_of_nights": 0,  # Invalid - must be >= 1
            "check_in": "invalid-date",
            "check_out": "invalid-date"
        }
        
        mock_response = Mock()
        mock_response.text = "<html><body>Hotel data</body></html>"
        mock_response.raise_for_status = Mock()
        mock_http_client.get.return_value = mock_response
        mock_text_extractor.extract_text.return_value = clean_text
        mock_llm_extractor.extract_lodging_data.return_value = invalid_lodging_data
        
        # Act
        result = await universal_parser.parse_lodging_data(url)
        
        # Assert - Should return fallback values
        assert result["name"] == "Test Hotel"
        assert result["location"] == "Test City"
        assert result["number_of_guests"] == 1  # Fallback for invalid value
        assert result["total_cost"] == 0.0  # Fallback for negative value
        assert result["total_cost_per_person"] == 0  # Fallback for invalid type
        assert result["number_of_nights"] == 1  # Fallback for invalid value
        assert result["check_in"] == datetime.fromisoformat("1970-01-01")  # Fallback
        assert result["check_out"] == datetime.fromisoformat("1970-01-02")  # Fallback
    
    def test_get_domain(self, universal_parser):
        """Test domain extraction from URLs."""
        # Test cases
        test_cases = [
            ("https://www.google.com/flights", "google.com"),
            ("https://airbnb.com/listing/123", "airbnb.com"),
            ("http://booking.com", "booking.com"),
            ("https://www.hotels.com/search", "hotels.com"),
        ]
        
        for url, expected_domain in test_cases:
            assert universal_parser._get_domain(url) == expected_domain
    
    def test_is_flight_platform(self, universal_parser):
        """Test flight platform detection."""
        # Flight platforms
        flight_domains = [
            "google.com", "flights.google.com", "expedia.com",
            "united.com", "delta.com", "american.com"
        ]
        
        for domain in flight_domains:
            assert universal_parser._is_flight_platform(domain) is True
        
        # Non-flight platforms
        non_flight_domains = ["airbnb.com", "booking.com", "hotels.com"]
        for domain in non_flight_domains:
            assert universal_parser._is_flight_platform(domain) is False
    
    def test_is_lodging_platform(self, universal_parser):
        """Test lodging platform detection."""
        # Lodging platforms
        lodging_domains = [
            "airbnb.com", "booking.com", "hotels.com",
            "marriott.com", "hilton.com", "vrbo.com"
        ]
        
        for domain in lodging_domains:
            assert universal_parser._is_lodging_platform(domain) is True
        
        # Non-lodging platforms
        non_lodging_domains = ["google.com", "united.com", "delta.com"]
        for domain in non_lodging_domains:
            assert universal_parser._is_lodging_platform(domain) is False
    
    @pytest.mark.asyncio
    async def test_http_client_error_handling(self, universal_parser, mock_http_client, mock_text_extractor):
        """Test HTTP client error handling."""
        # Arrange
        url = "https://example.com/test"
        mock_http_client.get.side_effect = Exception("Network error")
        
        # Act & Assert
        with pytest.raises(Exception, match="Network error"):
            await universal_parser.scrape_and_extract_text(url)
    
    @pytest.mark.asyncio
    async def test_llm_extraction_error_handling(self, universal_parser, mock_http_client, mock_text_extractor, mock_llm_extractor):
        """Test LLM extraction error handling."""
        # Arrange
        url = "https://flights.google.com/test"
        clean_text = "Flight data"
        
        mock_response = Mock()
        mock_response.text = "<html><body>Flight data</body></html>"
        mock_response.raise_for_status = Mock()
        mock_http_client.get.return_value = mock_response
        mock_text_extractor.extract_text.return_value = clean_text
        mock_llm_extractor.extract_flight_data.side_effect = ValueError("LLM extraction failed")
        
        # Act & Assert
        with pytest.raises(ValueError, match="Flight parsing failed"):
            await universal_parser.parse_flight_data(url)
    
    @pytest.mark.asyncio
    async def test_context_manager(self, mock_http_client, mock_text_extractor, mock_llm_extractor):
        """Test async context manager functionality."""
        # Arrange
        parser = UniversalParser(
            anthropic_api_key="test-key",
            http_client=mock_http_client,
            text_extractor=mock_text_extractor,
            llm_extractor=mock_llm_extractor
        )
        
        # Act & Assert
        async with parser as p:
            assert p is parser
        
        # Verify close was called
        mock_http_client.close.assert_called_once()


class TestUniversalParserIntegration:
    """Integration tests with real travel booking URLs (mocked responses)."""
    
    @pytest.fixture
    def parser_with_real_dependencies(self):
        """Create parser with real dependencies but mocked HTTP responses."""
        return UniversalParser(anthropic_api_key="test-api-key")
    
    @pytest.mark.asyncio
    async def test_google_flights_integration(self, parser_with_real_dependencies):
        """Test integration with Google Flights URL structure."""
        # Mock the HTTP response with realistic Google Flights HTML
        google_flights_html = """
        <html>
        <body>
            <div class="gws-flights__booking-card">
                <div>JFK → CDG</div>
                <div>8h 30m</div>
                <div>$1,245</div>
                <div>Air France AF123</div>
                <div>Direct flight</div>
            </div>
        </body>
        </html>
        """
        
        with patch.object(parser_with_real_dependencies.http_client, 'get') as mock_get:
            mock_response = Mock()
            mock_response.text = google_flights_html
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            with patch.object(parser_with_real_dependencies.llm_extractor, 'extract_flight_data') as mock_extract:
                mock_extract.return_value = {
                    "origin_airport": "JFK",
                    "destination_airport": "CDG",
                    "duration": 510,
                    "total_cost": 1245.0,
                    "total_cost_per_person": 1245.0,
                    "segment": 1,
                    "flight_number": "AF123"
                }
                
                # Act
                result = await parser_with_real_dependencies.parse_flight_data(
                    "https://flights.google.com/search?tfs=test"
                )
                
                # Assert
                assert result["origin_airport"] == "JFK"
                assert result["destination_airport"] == "CDG"
                assert result["duration"] == 510
                assert result["flight_number"] == "AF123"
    
    @pytest.mark.asyncio
    async def test_airbnb_integration(self, parser_with_real_dependencies):
        """Test integration with Airbnb URL structure."""
        # Mock the HTTP response with realistic Airbnb HTML
        airbnb_html = """
        <html>
        <body>
            <div data-testid="listing-details">
                <h1>Luxury Apartment in Paris</h1>
                <div>Paris, France</div>
                <div>2 guests</div>
                <div>3 nights</div>
                <div data-testid="price-breakdown">
                    <div>$150 per night</div>
                    <div>Total: $450</div>
                </div>
                <div>Check-in: Jun 15, 2024</div>
                <div>Check-out: Jun 18, 2024</div>
            </div>
        </body>
        </html>
        """
        
        with patch.object(parser_with_real_dependencies.http_client, 'get') as mock_get:
            mock_response = Mock()
            mock_response.text = airbnb_html
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            with patch.object(parser_with_real_dependencies.llm_extractor, 'extract_lodging_data') as mock_extract:
                mock_extract.return_value = {
                    "name": "Luxury Apartment in Paris",
                    "location": "Paris, France",
                    "number_of_guests": 2,
                    "total_cost": 450.0,
                    "total_cost_per_person": 225,
                    "number_of_nights": 3,
                    "check_in": datetime.fromisoformat("2024-06-15T15:00:00+02:00"),
                    "check_out": datetime.fromisoformat("2024-06-18T11:00:00+02:00")
                }
                
                # Act
                result = await parser_with_real_dependencies.parse_lodging_data(
                    "https://airbnb.com/rooms/12345"
                )
                
                # Assert
                assert result["name"] == "Luxury Apartment in Paris"
                assert result["location"] == "Paris, France"
                assert result["number_of_guests"] == 2
                assert result["total_cost"] == 450.0