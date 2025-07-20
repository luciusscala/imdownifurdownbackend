"""
Unit tests for LLMDataExtractor service.
"""

import json
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from app.services.llm_data_extractor import LLMDataExtractor


class TestLLMDataExtractor:
    """Test cases for LLMDataExtractor class."""
    
    @pytest.fixture
    def mock_anthropic_client(self):
        """Mock Anthropic client for testing."""
        with patch('app.services.llm_data_extractor.anthropic.Anthropic') as mock_client:
            yield mock_client
    
    @pytest.fixture
    def extractor(self, mock_anthropic_client):
        """Create LLMDataExtractor instance for testing."""
        return LLMDataExtractor(api_key="test-api-key")
    
    @pytest.mark.asyncio
    async def test_extract_flight_data_success(self, extractor, mock_anthropic_client):
        """Test successful flight data extraction."""
        # Mock Claude API response
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = json.dumps({
            "origin_airport": "JFK",
            "destination_airport": "CDG",
            "duration": 480,
            "total_cost": 1200.50,
            "total_cost_per_person": 1200.50,
            "segment": 1,
            "flight_number": "AF123"
        })
        
        mock_client_instance = mock_anthropic_client.return_value
        mock_client_instance.messages.create.return_value = mock_response
        
        # Test extraction
        text_content = "Flight from JFK to CDG, Air France AF123, 8 hours, $1200.50"
        result = await extractor.extract_flight_data(text_content)
        
        # Verify result
        assert result["origin_airport"] == "JFK"
        assert result["destination_airport"] == "CDG"
        assert result["duration"] == 480
        assert result["total_cost"] == 1200.50
        assert result["total_cost_per_person"] == 1200.50
        assert result["segment"] == 1
        assert result["flight_number"] == "AF123"
        
        # Verify API call
        mock_client_instance.messages.create.assert_called_once()
        call_args = mock_client_instance.messages.create.call_args
        assert call_args[1]["model"] == "claude-3-5-sonnet-20241022"
        assert call_args[1]["temperature"] == 0.1
        assert text_content in call_args[1]["messages"][0]["content"]
    
    @pytest.mark.asyncio
    async def test_extract_flight_data_with_missing_fields(self, extractor, mock_anthropic_client):
        """Test flight data extraction with missing fields."""
        # Mock Claude API response with missing fields
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = json.dumps({
            "origin_airport": "JFK",
            "destination_airport": "CDG"
            # Missing other fields
        })
        
        mock_client_instance = mock_anthropic_client.return_value
        mock_client_instance.messages.create.return_value = mock_response
        
        # Test extraction - should use default values for missing fields
        text_content = "Flight from JFK to CDG"
        result = await extractor.extract_flight_data(text_content)
        
        # Verify defaults are used for missing fields
        assert result["origin_airport"] == "JFK"
        assert result["destination_airport"] == "CDG"
        assert result["duration"] == 0  # Default
        assert result["total_cost"] == 0.0  # Default
        assert result["total_cost_per_person"] == 0.0  # Default
        assert result["segment"] == 1  # Default
        assert result["flight_number"] == "Unknown"  # Default
    
    @pytest.mark.asyncio
    async def test_extract_flight_data_invalid_json(self, extractor, mock_anthropic_client):
        """Test flight data extraction with invalid JSON response."""
        # Mock Claude API response with invalid JSON
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = "This is not valid JSON"
        
        mock_client_instance = mock_anthropic_client.return_value
        mock_client_instance.messages.create.return_value = mock_response
        
        # Test extraction - should raise ValueError
        text_content = "Flight information"
        with pytest.raises(ValueError, match="Failed to extract flight data"):
            await extractor.extract_flight_data(text_content)
    
    @pytest.mark.asyncio
    async def test_extract_flight_data_api_error(self, extractor, mock_anthropic_client):
        """Test flight data extraction with API error."""
        # Mock Claude API to raise exception
        mock_client_instance = mock_anthropic_client.return_value
        mock_client_instance.messages.create.side_effect = Exception("API Error")
        
        # Test extraction - should raise ValueError
        text_content = "Flight information"
        with pytest.raises(ValueError, match="Failed to extract flight data"):
            await extractor.extract_flight_data(text_content)
    
    @pytest.mark.asyncio
    async def test_extract_lodging_data_success(self, extractor, mock_anthropic_client):
        """Test successful lodging data extraction."""
        # Mock Claude API response
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = json.dumps({
            "name": "Luxury Hotel Paris",
            "location": "Paris, France",
            "number_of_guests": 2,
            "total_cost": 450.00,
            "total_cost_per_person": 225,
            "number_of_nights": 3,
            "check_in": "2024-06-15",
            "check_out": "2024-06-18"
        })
        
        mock_client_instance = mock_anthropic_client.return_value
        mock_client_instance.messages.create.return_value = mock_response
        
        # Test extraction
        text_content = "Luxury Hotel Paris, 2 guests, 3 nights, $450 total"
        result = await extractor.extract_lodging_data(text_content)
        
        # Verify result
        assert result["name"] == "Luxury Hotel Paris"
        assert result["location"] == "Paris, France"
        assert result["number_of_guests"] == 2
        assert result["total_cost"] == 450.00
        assert result["total_cost_per_person"] == 225
        assert result["number_of_nights"] == 3
        assert isinstance(result["check_in"], datetime)
        assert isinstance(result["check_out"], datetime)
        
        # Verify API call
        mock_client_instance.messages.create.assert_called_once()
        call_args = mock_client_instance.messages.create.call_args
        assert text_content in call_args[1]["messages"][0]["content"]
    
    @pytest.mark.asyncio
    async def test_extract_lodging_data_with_invalid_dates(self, extractor, mock_anthropic_client):
        """Test lodging data extraction with invalid date formats."""
        # Mock Claude API response with invalid dates
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = json.dumps({
            "name": "Test Hotel",
            "location": "Test City",
            "number_of_guests": 1,
            "total_cost": 100.0,
            "total_cost_per_person": 100,
            "number_of_nights": 1,
            "check_in": "invalid-date",
            "check_out": "also-invalid"
        })
        
        mock_client_instance = mock_anthropic_client.return_value
        mock_client_instance.messages.create.return_value = mock_response
        
        # Test extraction - should use default dates for invalid formats
        text_content = "Test Hotel booking"
        result = await extractor.extract_lodging_data(text_content)
        
        # Verify default dates are used
        assert result["check_in"] == datetime.fromisoformat("1970-01-01")
        assert result["check_out"] == datetime.fromisoformat("1970-01-02")
    
    @pytest.mark.asyncio
    async def test_extract_lodging_data_validation_failure(self, extractor, mock_anthropic_client):
        """Test lodging data extraction with validation failure."""
        # Mock Claude API response with invalid data types
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = json.dumps({
            "name": "Test Hotel",
            "location": "Test City",
            "number_of_guests": "invalid",  # Should be integer
            "total_cost": "invalid",  # Should be float
            "total_cost_per_person": "invalid",  # Should be integer
            "number_of_nights": "invalid",  # Should be integer
            "check_in": "2024-01-01",
            "check_out": "2024-01-02"
        })
        
        mock_client_instance = mock_anthropic_client.return_value
        mock_client_instance.messages.create.return_value = mock_response
        
        # Test extraction - should return default values due to validation failure
        text_content = "Test Hotel booking"
        result = await extractor.extract_lodging_data(text_content)
        
        # Verify default values are returned
        assert result["name"] == "Unknown"
        assert result["location"] == "Unknown"
        assert result["number_of_guests"] == 1
        assert result["total_cost"] == 0.0
        assert result["total_cost_per_person"] == 0
        assert result["number_of_nights"] == 1
    
    def test_parse_json_response_success(self, extractor):
        """Test successful JSON parsing from Claude response."""
        response_text = '{"key": "value", "number": 123}'
        result = extractor._parse_json_response(response_text)
        
        assert result == {"key": "value", "number": 123}
    
    def test_parse_json_response_with_extra_text(self, extractor):
        """Test JSON parsing with extra text around JSON."""
        response_text = 'Here is the data: {"key": "value"} and some more text'
        result = extractor._parse_json_response(response_text)
        
        assert result == {"key": "value"}
    
    def test_parse_json_response_no_json(self, extractor):
        """Test JSON parsing with no JSON in response."""
        response_text = 'This response contains no JSON'
        
        with pytest.raises(ValueError, match="No JSON object found in response"):
            extractor._parse_json_response(response_text)
    
    def test_parse_json_response_invalid_json(self, extractor):
        """Test JSON parsing with invalid JSON."""
        response_text = '{"invalid": json}'
        
        with pytest.raises(ValueError, match="Invalid JSON response"):
            extractor._parse_json_response(response_text)
    
    def test_validate_flight_data_success(self, extractor):
        """Test successful flight data validation."""
        data = {
            "origin_airport": "JFK",
            "destination_airport": "CDG",
            "duration": 480,
            "total_cost": 1200.50,
            "total_cost_per_person": 1200.50,
            "segment": 1,
            "flight_number": "AF123"
        }
        
        result = extractor._validate_flight_data(data)
        assert result == data
    
    def test_validate_flight_data_failure(self, extractor):
        """Test flight data validation failure returns defaults."""
        data = {
            "origin_airport": "JFK",
            "duration": "invalid",  # Should be integer
            "total_cost": "invalid"  # Should be float
        }
        
        result = extractor._validate_flight_data(data)
        
        # Should return default values
        expected = {
            "origin_airport": "Unknown",
            "destination_airport": "Unknown",
            "duration": 0,
            "total_cost": 0.0,
            "total_cost_per_person": 0.0,
            "segment": 1,
            "flight_number": "Unknown"
        }
        assert result == expected
    
    def test_validate_lodging_data_success(self, extractor):
        """Test successful lodging data validation."""
        data = {
            "name": "Test Hotel",
            "location": "Test City",
            "number_of_guests": 2,
            "total_cost": 200.0,
            "total_cost_per_person": 100,
            "number_of_nights": 2,
            "check_in": "2024-01-01",
            "check_out": "2024-01-03"
        }
        
        result = extractor._validate_lodging_data(data)
        
        # Verify dates were converted to datetime objects
        assert result["name"] == "Test Hotel"
        assert result["location"] == "Test City"
        assert isinstance(result["check_in"], datetime)
        assert isinstance(result["check_out"], datetime)
    
    def test_build_flight_extraction_prompt(self, extractor):
        """Test flight extraction prompt building."""
        text_content = "Sample flight text"
        prompt = extractor._build_flight_extraction_prompt(text_content)
        
        # Verify prompt contains required elements
        assert "flight booking information" in prompt
        assert "origin_airport" in prompt
        assert "destination_airport" in prompt
        assert "duration" in prompt
        assert "total_cost" in prompt
        assert "segment" in prompt
        assert "flight_number" in prompt
        assert text_content in prompt
    
    def test_build_lodging_extraction_prompt(self, extractor):
        """Test lodging extraction prompt building."""
        text_content = "Sample lodging text"
        prompt = extractor._build_lodging_extraction_prompt(text_content)
        
        # Verify prompt contains required elements
        assert "lodging booking information" in prompt
        assert "name" in prompt
        assert "location" in prompt
        assert "number_of_guests" in prompt
        assert "total_cost" in prompt
        assert "number_of_nights" in prompt
        assert "check_in" in prompt
        assert "check_out" in prompt
        assert text_content in prompt
    
    def test_extractor_initialization(self):
        """Test LLMDataExtractor initialization."""
        api_key = "test-api-key"
        model = "claude-3-haiku-20240307"
        
        extractor = LLMDataExtractor(api_key=api_key, model=model)
        
        assert extractor.model == model
        assert extractor.logger.name == "app.services.llm_data_extractor"
    
    def test_extractor_default_model(self):
        """Test LLMDataExtractor with default model."""
        extractor = LLMDataExtractor(api_key="test-api-key")
        
        assert extractor.model == "claude-3-5-sonnet-20241022"