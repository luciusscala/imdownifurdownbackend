"""Unit tests for Pydantic models."""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError
from app.models import (
    FlightParseRequest,
    LodgingParseRequest,
    FlightParseResponse,
    LodgingParseResponse,
    ErrorResponse
)


class TestFlightParseRequest:
    """Test cases for FlightParseRequest model."""
    
    def test_valid_flight_request(self):
        """Test valid flight parse request."""
        request = FlightParseRequest(link="https://flights.google.com/flights?hl=en")
        assert str(request.link) == "https://flights.google.com/flights?hl=en"
    
    def test_invalid_url_format(self):
        """Test invalid URL format raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            FlightParseRequest(link="not-a-valid-url")
        
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "url_parsing"
        assert "link" in errors[0]["loc"]
    
    def test_missing_link_field(self):
        """Test missing link field raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            FlightParseRequest()
        
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "missing"
        assert "link" in errors[0]["loc"]
    
    def test_various_valid_urls(self):
        """Test various valid URL formats."""
        valid_urls = [
            "https://flights.google.com/flights",
            "https://www.united.com/booking",
            "http://example.com/flight",
            "https://www.delta.com/flight/search"
        ]
        
        for url in valid_urls:
            request = FlightParseRequest(link=url)
            assert str(request.link) == url


class TestLodgingParseRequest:
    """Test cases for LodgingParseRequest model."""
    
    def test_valid_lodging_request(self):
        """Test valid lodging parse request."""
        request = LodgingParseRequest(link="https://www.airbnb.com/rooms/12345")
        assert str(request.link) == "https://www.airbnb.com/rooms/12345"
    
    def test_invalid_url_format(self):
        """Test invalid URL format raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            LodgingParseRequest(link="invalid-url")
        
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "url_parsing"
        assert "link" in errors[0]["loc"]
    
    def test_missing_link_field(self):
        """Test missing link field raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            LodgingParseRequest()
        
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "missing"
        assert "link" in errors[0]["loc"]
    
    def test_various_valid_urls(self):
        """Test various valid URL formats."""
        valid_urls = [
            "https://www.airbnb.com/rooms/12345",
            "https://www.booking.com/hotel/us/example.html",
            "https://www.hotels.com/ho123456",
            "http://example-hotel.com/booking"
        ]
        
        for url in valid_urls:
            request = LodgingParseRequest(link=url)
            assert str(request.link) == url


class TestFlightParseResponse:
    """Test cases for FlightParseResponse model."""
    
    def test_valid_flight_response(self):
        """Test valid flight parse response."""
        response_data = {
            "origin_airport": "JFK",
            "destination_airport": "CDG", 
            "duration": 480,
            "total_cost": 1200.50,
            "total_cost_per_person": 600.25,
            "segment": 1,
            "flight_number": "AF123"
        }
        
        response = FlightParseResponse(**response_data)
        assert response.origin_airport == "JFK"
        assert response.destination_airport == "CDG"
        assert response.duration == 480
        assert response.total_cost == 1200.50
        assert response.total_cost_per_person == 600.25
        assert response.segment == 1
        assert response.flight_number == "AF123"
    
    def test_missing_required_fields(self):
        """Test missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            FlightParseResponse()
        
        errors = exc_info.value.errors()
        required_fields = {
            "origin_airport", "destination_airport", "duration",
            "total_cost", "total_cost_per_person", "segment", "flight_number"
        }
        error_fields = {error["loc"][0] for error in errors}
        assert required_fields == error_fields
    
    def test_negative_duration_validation(self):
        """Test negative duration raises ValidationError."""
        response_data = {
            "origin_airport": "JFK",
            "destination_airport": "CDG",
            "duration": -10,  # Invalid negative duration
            "total_cost": 1200.50,
            "total_cost_per_person": 600.25,
            "segment": 1,
            "flight_number": "AF123"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            FlightParseResponse(**response_data)
        
        errors = exc_info.value.errors()
        duration_error = next(e for e in errors if e["loc"][0] == "duration")
        assert duration_error["type"] == "greater_than_equal"
    
    def test_negative_cost_validation(self):
        """Test negative costs raise ValidationError."""
        response_data = {
            "origin_airport": "JFK",
            "destination_airport": "CDG",
            "duration": 480,
            "total_cost": -100.0,  # Invalid negative cost
            "total_cost_per_person": 600.25,
            "segment": 1,
            "flight_number": "AF123"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            FlightParseResponse(**response_data)
        
        errors = exc_info.value.errors()
        cost_error = next(e for e in errors if e["loc"][0] == "total_cost")
        assert cost_error["type"] == "greater_than_equal"
    
    def test_negative_segment_validation(self):
        """Test negative segment raises ValidationError."""
        response_data = {
            "origin_airport": "JFK",
            "destination_airport": "CDG",
            "duration": 480,
            "total_cost": 1200.50,
            "total_cost_per_person": 600.25,
            "segment": -1,  # Invalid negative segment
            "flight_number": "AF123"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            FlightParseResponse(**response_data)
        
        errors = exc_info.value.errors()
        segment_error = next(e for e in errors if e["loc"][0] == "segment")
        assert segment_error["type"] == "greater_than_equal"
    
    def test_type_validation(self):
        """Test field type validation."""
        response_data = {
            "origin_airport": "JFK",
            "destination_airport": "CDG",
            "duration": "480",  # String instead of int - should be coerced
            "total_cost": "1200.50",  # String instead of float - should be coerced
            "total_cost_per_person": "600.25",  # String instead of float - should be coerced
            "segment": "1",  # String instead of int - should be coerced
            "flight_number": "AF123"
        }
        
        response = FlightParseResponse(**response_data)
        assert isinstance(response.duration, int)
        assert isinstance(response.total_cost, float)
        assert isinstance(response.total_cost_per_person, float)
        assert isinstance(response.segment, int)


class TestLodgingParseResponse:
    """Test cases for LodgingParseResponse model."""
    
    def test_valid_lodging_response(self):
        """Test valid lodging parse response."""
        check_in = datetime(2024, 6, 15, 15, 0, 0, tzinfo=timezone.utc)
        check_out = datetime(2024, 6, 18, 11, 0, 0, tzinfo=timezone.utc)
        
        response_data = {
            "name": "Luxury Hotel Paris",
            "location": "Paris, France",
            "number_of_guests": 2,
            "total_cost": 450.00,
            "total_cost_per_person": 225,
            "number_of_nights": 3,
            "check_in": check_in,
            "check_out": check_out
        }
        
        response = LodgingParseResponse(**response_data)
        assert response.name == "Luxury Hotel Paris"
        assert response.location == "Paris, France"
        assert response.number_of_guests == 2
        assert response.total_cost == 450.00
        assert response.total_cost_per_person == 225
        assert response.number_of_nights == 3
        assert response.check_in == check_in
        assert response.check_out == check_out
    
    def test_missing_required_fields(self):
        """Test missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            LodgingParseResponse()
        
        errors = exc_info.value.errors()
        required_fields = {
            "name", "location", "number_of_guests", "total_cost",
            "total_cost_per_person", "number_of_nights", "check_in", "check_out"
        }
        error_fields = {error["loc"][0] for error in errors}
        assert required_fields == error_fields
    
    def test_negative_guests_validation(self):
        """Test negative number of guests raises ValidationError."""
        check_in = datetime(2024, 6, 15, 15, 0, 0, tzinfo=timezone.utc)
        check_out = datetime(2024, 6, 18, 11, 0, 0, tzinfo=timezone.utc)
        
        response_data = {
            "name": "Hotel",
            "location": "Paris",
            "number_of_guests": 0,  # Invalid - must be >= 1
            "total_cost": 450.00,
            "total_cost_per_person": 225,
            "number_of_nights": 3,
            "check_in": check_in,
            "check_out": check_out
        }
        
        with pytest.raises(ValidationError) as exc_info:
            LodgingParseResponse(**response_data)
        
        errors = exc_info.value.errors()
        guests_error = next(e for e in errors if e["loc"][0] == "number_of_guests")
        assert guests_error["type"] == "greater_than_equal"
    
    def test_negative_nights_validation(self):
        """Test negative number of nights raises ValidationError."""
        check_in = datetime(2024, 6, 15, 15, 0, 0, tzinfo=timezone.utc)
        check_out = datetime(2024, 6, 18, 11, 0, 0, tzinfo=timezone.utc)
        
        response_data = {
            "name": "Hotel",
            "location": "Paris",
            "number_of_guests": 2,
            "total_cost": 450.00,
            "total_cost_per_person": 225,
            "number_of_nights": 0,  # Invalid - must be >= 1
            "check_in": check_in,
            "check_out": check_out
        }
        
        with pytest.raises(ValidationError) as exc_info:
            LodgingParseResponse(**response_data)
        
        errors = exc_info.value.errors()
        nights_error = next(e for e in errors if e["loc"][0] == "number_of_nights")
        assert nights_error["type"] == "greater_than_equal"
    
    def test_negative_cost_validation(self):
        """Test negative costs raise ValidationError."""
        check_in = datetime(2024, 6, 15, 15, 0, 0, tzinfo=timezone.utc)
        check_out = datetime(2024, 6, 18, 11, 0, 0, tzinfo=timezone.utc)
        
        response_data = {
            "name": "Hotel",
            "location": "Paris",
            "number_of_guests": 2,
            "total_cost": -100.0,  # Invalid negative cost
            "total_cost_per_person": 225,
            "number_of_nights": 3,
            "check_in": check_in,
            "check_out": check_out
        }
        
        with pytest.raises(ValidationError) as exc_info:
            LodgingParseResponse(**response_data)
        
        errors = exc_info.value.errors()
        cost_error = next(e for e in errors if e["loc"][0] == "total_cost")
        assert cost_error["type"] == "greater_than_equal"
    
    def test_datetime_validation(self):
        """Test datetime field validation."""
        response_data = {
            "name": "Hotel",
            "location": "Paris",
            "number_of_guests": 2,
            "total_cost": 450.00,
            "total_cost_per_person": 225,
            "number_of_nights": 3,
            "check_in": "2024-06-15T15:00:00+02:00",  # ISO string - should be parsed
            "check_out": "2024-06-18T11:00:00+02:00"   # ISO string - should be parsed
        }
        
        response = LodgingParseResponse(**response_data)
        assert isinstance(response.check_in, datetime)
        assert isinstance(response.check_out, datetime)
    
    def test_type_validation(self):
        """Test field type validation."""
        check_in = datetime(2024, 6, 15, 15, 0, 0, tzinfo=timezone.utc)
        check_out = datetime(2024, 6, 18, 11, 0, 0, tzinfo=timezone.utc)
        
        response_data = {
            "name": "Hotel",
            "location": "Paris",
            "number_of_guests": "2",  # String instead of int - should be coerced
            "total_cost": "450.00",   # String instead of float - should be coerced
            "total_cost_per_person": "225",  # String instead of int - should be coerced
            "number_of_nights": "3",  # String instead of int - should be coerced
            "check_in": check_in,
            "check_out": check_out
        }
        
        response = LodgingParseResponse(**response_data)
        assert isinstance(response.number_of_guests, int)
        assert isinstance(response.total_cost, float)
        assert isinstance(response.total_cost_per_person, int)
        assert isinstance(response.number_of_nights, int)


class TestErrorResponse:
    """Test cases for ErrorResponse model."""
    
    def test_valid_error_response(self):
        """Test valid error response."""
        timestamp = datetime.now(timezone.utc)
        response_data = {
            "error": "INVALID_URL",
            "message": "Invalid or malformed URL provided",
            "timestamp": timestamp
        }
        
        response = ErrorResponse(**response_data)
        assert response.error == "INVALID_URL"
        assert response.message == "Invalid or malformed URL provided"
        assert response.timestamp == timestamp
    
    def test_auto_timestamp_generation(self):
        """Test automatic timestamp generation."""
        response_data = {
            "error": "PARSING_FAILED",
            "message": "Failed to parse data from the URL"
        }
        
        response = ErrorResponse(**response_data)
        assert response.error == "PARSING_FAILED"
        assert response.message == "Failed to parse data from the URL"
        assert isinstance(response.timestamp, datetime)
        # Timestamp should be recent (within last minute)
        time_diff = datetime.now(timezone.utc) - response.timestamp
        assert time_diff.total_seconds() < 60
    
    def test_missing_required_fields(self):
        """Test missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ErrorResponse()
        
        errors = exc_info.value.errors()
        required_fields = {"error", "message"}
        error_fields = {error["loc"][0] for error in errors}
        assert required_fields == error_fields
    
    def test_timestamp_type_validation(self):
        """Test timestamp field type validation."""
        response_data = {
            "error": "TIMEOUT",
            "message": "Request timeout exceeded",
            "timestamp": "2024-01-15T10:30:00Z"  # ISO string - should be parsed
        }
        
        response = ErrorResponse(**response_data)
        assert isinstance(response.timestamp, datetime)
        assert response.error == "TIMEOUT"
        assert response.message == "Request timeout exceeded"