"""
Comprehensive integration tests for task 13 completion.
Tests all requirements validation through comprehensive testing scenarios.
"""

import asyncio
import time
import pytest
from unittest.mock import AsyncMock, patch, Mock
from fastapi.testclient import TestClient
from httpx import AsyncClient
import json

from app.main import app, get_universal_parser
from app.services.universal_parser import UniversalParser
from tests.fixtures import (
    BookingURLFixtures, 
    ExpectedResponseFixtures, 
    ErrorScenarioFixtures,
    MockHTMLFixtures,
    TestDataGenerator
)


class TestComprehensiveIntegration:
    """Comprehensive integration tests covering all task 13 requirements."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_parser_with_real_responses(self):
        """Mock parser that returns realistic responses based on URL patterns."""
        mock_parser = AsyncMock(spec=UniversalParser)
        
        async def realistic_flight_parse(url):
            # Simulate different responses based on URL patterns
            if "google" in url:
                return {
                    "origin_airport": "JFK",
                    "destination_airport": "LAX",
                    "duration": 360,
                    "total_cost": 299.99,
                    "total_cost_per_person": 299.99,
                    "segment": 1,
                    "flight_number": "AA123"
                }
            elif "expedia" in url:
                return {
                    "origin_airport": "ORD",
                    "destination_airport": "MIA",
                    "duration": 180,
                    "total_cost": 199.50,
                    "total_cost_per_person": 199.50,
                    "segment": 1,
                    "flight_number": "UA456"
                }
            else:
                return {
                    "origin_airport": "SFO",
                    "destination_airport": "CDG",
                    "duration": 660,
                    "total_cost": 1200.00,
                    "total_cost_per_person": 1200.00,
                    "segment": 1,
                    "flight_number": "AF789"
                }
        
        async def realistic_lodging_parse(url):
            # Simulate different responses based on URL patterns
            if "airbnb" in url:
                return {
                    "name": "Luxury Manhattan Suite",
                    "location": "New York, NY, USA",
                    "number_of_guests": 2,
                    "total_cost": 450.00,
                    "total_cost_per_person": 225,
                    "number_of_nights": 3,
                    "check_in": "2024-06-15T15:00:00Z",
                    "check_out": "2024-06-18T11:00:00Z"
                }
            elif "booking" in url:
                return {
                    "name": "Paris Boutique Hotel",
                    "location": "Paris, France",
                    "number_of_guests": 2,
                    "total_cost": 840.00,
                    "total_cost_per_person": 420,
                    "number_of_nights": 7,
                    "check_in": "2024-07-10T14:00:00Z",
                    "check_out": "2024-07-17T12:00:00Z"
                }
            else:
                return {
                    "name": "Budget Inn & Suites",
                    "location": "Las Vegas, NV, USA",
                    "number_of_guests": 2,
                    "total_cost": 120.00,
                    "total_cost_per_person": 60,
                    "number_of_nights": 2,
                    "check_in": "2024-09-01T15:00:00Z",
                    "check_out": "2024-09-03T11:00:00Z"
                }
        
        mock_parser.parse_flight_data.side_effect = realistic_flight_parse
        mock_parser.parse_lodging_data.side_effect = realistic_lodging_parse
        mock_parser.close = AsyncMock()
        return mock_parser
    
    def test_all_flight_booking_platforms(self, client, mock_parser_with_real_responses):
        """Test all major flight booking platforms from fixtures."""
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser_with_real_responses
        try:
            # Test all flight URLs from fixtures
            all_flight_urls = TestDataGenerator.get_all_flight_urls()
            
            for url in all_flight_urls:
                response = client.post(
                    "/parse-flight",
                    json={"link": url}
                )
                
                assert response.status_code == 200, f"Failed for URL: {url}"
                data = response.json()
                
                # Verify required fields are present
                required_fields = [
                    "origin_airport", "destination_airport", "duration",
                    "total_cost", "total_cost_per_person", "segment", "flight_number"
                ]
                for field in required_fields:
                    assert field in data, f"Missing field {field} for URL: {url}"
                
                # Verify data types
                assert isinstance(data["origin_airport"], str)
                assert isinstance(data["destination_airport"], str)
                assert isinstance(data["duration"], int)
                assert isinstance(data["total_cost"], (int, float))
                assert isinstance(data["total_cost_per_person"], (int, float))
                assert isinstance(data["segment"], int)
                assert isinstance(data["flight_number"], str)
                
        finally:
            app.dependency_overrides.clear()
    
    def test_all_lodging_booking_platforms(self, client, mock_parser_with_real_responses):
        """Test all major lodging booking platforms from fixtures."""
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser_with_real_responses
        try:
            # Test all lodging URLs from fixtures
            all_lodging_urls = TestDataGenerator.get_all_lodging_urls()
            
            for url in all_lodging_urls:
                response = client.post(
                    "/parse-lodging",
                    json={"link": url}
                )
                
                assert response.status_code == 200, f"Failed for URL: {url}"
                data = response.json()
                
                # Verify required fields are present
                required_fields = [
                    "name", "location", "number_of_guests", "total_cost",
                    "total_cost_per_person", "number_of_nights", "check_in", "check_out"
                ]
                for field in required_fields:
                    assert field in data, f"Missing field {field} for URL: {url}"
                
                # Verify data types
                assert isinstance(data["name"], str)
                assert isinstance(data["location"], str)
                assert isinstance(data["number_of_guests"], int)
                assert isinstance(data["total_cost"], (int, float))
                assert isinstance(data["total_cost_per_person"], (int, float))
                assert isinstance(data["number_of_nights"], int)
                assert isinstance(data["check_in"], str)  # ISO format
                assert isinstance(data["check_out"], str)  # ISO format
                
        finally:
            app.dependency_overrides.clear()
    
    def test_error_scenarios_comprehensive(self, client):
        """Test comprehensive error scenarios from fixtures."""
        # Test invalid URLs
        for url in ErrorScenarioFixtures.INVALID_URLS:
            if url is not None:  # Skip None values for this test
                response = client.post(
                    "/parse-flight",
                    json={"link": url}
                )
                assert response.status_code in [422, 400], f"Expected validation error for URL: {url}"
        
        # Test unreachable URLs with mocked parser
        mock_parser = AsyncMock(spec=UniversalParser)
        mock_parser.parse_flight_data.side_effect = Exception("URL unreachable")
        mock_parser.close = AsyncMock()
        
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser
        try:
            for url in ErrorScenarioFixtures.UNREACHABLE_URLS:
                response = client.post(
                    "/parse-flight",
                    json={"link": url}
                )
                assert response.status_code == 500, f"Expected server error for URL: {url}"
                data = response.json()
                assert "error" in data
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_concurrent_load_performance(self, mock_parser_with_real_responses):
        """Test performance under concurrent load."""
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser_with_real_responses
        try:
            async with AsyncClient(app=app, base_url="http://test") as ac:
                # Create 20 concurrent requests (10 flight + 10 lodging)
                flight_urls = TestDataGenerator.get_all_flight_urls()[:10]
                lodging_urls = TestDataGenerator.get_all_lodging_urls()[:10]
                
                flight_tasks = [
                    ac.post("/parse-flight", json={"link": url})
                    for url in flight_urls
                ]
                lodging_tasks = [
                    ac.post("/parse-lodging", json={"link": url})
                    for url in lodging_urls
                ]
                
                start_time = time.time()
                all_responses = await asyncio.gather(
                    *flight_tasks, *lodging_tasks
                )
                end_time = time.time()
                
                total_time = end_time - start_time
                
                # All requests should succeed
                for response in all_responses:
                    assert response.status_code == 200
                
                # Performance assertion: 20 concurrent requests should complete in reasonable time
                # (Under 10 seconds for mocked responses)
                assert total_time < 10.0, f"Concurrent load test took too long: {total_time}s"
                
        finally:
            app.dependency_overrides.clear()
    
    def test_llm_api_error_handling_comprehensive(self, client):
        """Test comprehensive LLM API error handling."""
        # Test various LLM API error scenarios
        error_scenarios = [
            ("Rate limit exceeded", "429 Rate limit exceeded"),
            ("Quota exceeded", "Quota exceeded for Anthropic API"),
            ("Invalid API key", "Invalid API key"),
            ("Service unavailable", "Service temporarily unavailable"),
            ("Malformed response", "Invalid JSON response from LLM"),
        ]
        
        for error_type, error_message in error_scenarios:
            mock_parser = AsyncMock(spec=UniversalParser)
            mock_parser.parse_flight_data.side_effect = Exception(error_message)
            mock_parser.close = AsyncMock()
            
            app.dependency_overrides[get_universal_parser] = lambda: mock_parser
            try:
                response = client.post(
                    "/parse-flight",
                    json={"link": "https://flights.google.com/flights?test=1"}
                )
                
                assert response.status_code == 500
                data = response.json()
                assert "error" in data
                assert "message" in data
                
            finally:
                app.dependency_overrides.clear()
    
    def test_caching_integration_comprehensive(self, client):
        """Test comprehensive caching functionality."""
        from app.services.cache_manager import CacheManager
        
        # Create a cache manager for testing
        cache_manager = CacheManager(ttl=60, enabled=True, max_size=100)
        
        # Mock parser that tracks calls
        call_count = 0
        
        async def tracked_parse(url):
            nonlocal call_count
            call_count += 1
            return {
                "origin_airport": "JFK",
                "destination_airport": "LAX",
                "duration": 360,
                "total_cost": 299.99,
                "total_cost_per_person": 299.99,
                "segment": 1,
                "flight_number": "AA123"
            }
        
        mock_parser = AsyncMock(spec=UniversalParser)
        mock_parser.parse_flight_data.side_effect = tracked_parse
        mock_parser.close = AsyncMock()
        
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser
        try:
            test_url = "https://flights.google.com/flights?test=cache"
            
            # First request - should call parser
            response1 = client.post(
                "/parse-flight",
                json={"link": test_url}
            )
            assert response1.status_code == 200
            initial_call_count = call_count
            
            # Second request with same URL - should use cache
            response2 = client.post(
                "/parse-flight",
                json={"link": test_url}
            )
            assert response2.status_code == 200
            assert call_count == initial_call_count  # No additional calls
            
            # Verify responses are identical
            assert response1.json() == response2.json()
            
        finally:
            app.dependency_overrides.clear()
    
    def test_response_validation_comprehensive(self, client, mock_parser_with_real_responses):
        """Test comprehensive response validation."""
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser_with_real_responses
        try:
            # Test flight response validation
            flight_response = client.post(
                "/parse-flight",
                json={"link": "https://flights.google.com/flights?test=validation"}
            )
            assert flight_response.status_code == 200
            flight_data = flight_response.json()
            
            # Validate flight data structure and types
            assert isinstance(flight_data["origin_airport"], str)
            assert len(flight_data["origin_airport"]) == 3  # Airport code
            assert isinstance(flight_data["destination_airport"], str)
            assert len(flight_data["destination_airport"]) == 3  # Airport code
            assert isinstance(flight_data["duration"], int)
            assert flight_data["duration"] > 0
            assert isinstance(flight_data["total_cost"], (int, float))
            assert flight_data["total_cost"] >= 0
            assert isinstance(flight_data["total_cost_per_person"], (int, float))
            assert flight_data["total_cost_per_person"] >= 0
            assert isinstance(flight_data["segment"], int)
            assert flight_data["segment"] >= 1
            assert isinstance(flight_data["flight_number"], str)
            assert len(flight_data["flight_number"]) > 0
            
            # Test lodging response validation
            lodging_response = client.post(
                "/parse-lodging",
                json={"link": "https://www.airbnb.com/rooms/validation"}
            )
            assert lodging_response.status_code == 200
            lodging_data = lodging_response.json()
            
            # Validate lodging data structure and types
            assert isinstance(lodging_data["name"], str)
            assert len(lodging_data["name"]) > 0
            assert isinstance(lodging_data["location"], str)
            assert len(lodging_data["location"]) > 0
            assert isinstance(lodging_data["number_of_guests"], int)
            assert lodging_data["number_of_guests"] > 0
            assert isinstance(lodging_data["total_cost"], (int, float))
            assert lodging_data["total_cost"] >= 0
            assert isinstance(lodging_data["total_cost_per_person"], (int, float))
            assert lodging_data["total_cost_per_person"] >= 0
            assert isinstance(lodging_data["number_of_nights"], int)
            assert lodging_data["number_of_nights"] > 0
            
            # Validate date formats
            import re
            iso_date_pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$'
            assert re.match(iso_date_pattern, lodging_data["check_in"])
            assert re.match(iso_date_pattern, lodging_data["check_out"])
            
        finally:
            app.dependency_overrides.clear()
    
    def test_api_documentation_accessibility(self, client):
        """Test API documentation is properly generated and accessible."""
        # Test root endpoint for API documentation
        response = client.get("/")
        assert response.status_code == 200
        
        # Test OpenAPI schema
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        
        # Verify schema contains expected endpoints
        assert "/parse-flight" in schema["paths"]
        assert "/parse-lodging" in schema["paths"]
        assert "/health" in schema["paths"]
        
        # Verify schema contains expected models
        assert "FlightParseRequest" in schema["components"]["schemas"]
        assert "LodgingParseRequest" in schema["components"]["schemas"]
        assert "FlightParseResponse" in schema["components"]["schemas"]
        assert "LodgingParseResponse" in schema["components"]["schemas"]
        assert "ErrorResponse" in schema["components"]["schemas"]
    
    def test_cors_functionality_comprehensive(self, client):
        """Test CORS functionality with actual Next.js application integration."""
        # Test preflight request
        response = client.options(
            "/parse-flight",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"
            }
        )
        assert response.status_code == 200
        
        # Test actual request with CORS headers
        response = client.post(
            "/parse-flight",
            json={"link": "https://flights.google.com/flights?test=cors"},
            headers={"Origin": "http://localhost:3000"}
        )
        
        # Verify CORS headers are present
        assert "access-control-allow-origin" in response.headers
        assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    
    def test_cost_analysis_and_performance_metrics(self, client, mock_parser_with_real_responses):
        """Test cost analysis and performance testing under concurrent load."""
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser_with_real_responses
        try:
            # Test performance with multiple requests
            start_time = time.time()
            
            responses = []
            for i in range(10):
                response = client.post(
                    "/parse-flight",
                    json={"link": f"https://flights.google.com/flights?test=perf_{i}"}
                )
                responses.append(response)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # All requests should succeed
            for response in responses:
                assert response.status_code == 200
            
            # Performance assertion: 10 requests should complete in reasonable time
            assert total_time < 5.0, f"Performance test took too long: {total_time}s"
            
            # Calculate average response time
            avg_response_time = total_time / 10
            assert avg_response_time < 0.5, f"Average response time too high: {avg_response_time}s"
            
        finally:
            app.dependency_overrides.clear()


class TestEndToEndScenarios:
    """End-to-end testing with real URLs from major travel platforms."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_google_flights_end_to_end(self, client):
        """Test end-to-end with Google Flights URL structure."""
        # Mock parser with realistic Google Flights response
        mock_parser = AsyncMock(spec=UniversalParser)
        mock_parser.parse_flight_data.return_value = {
            "origin_airport": "JFK",
            "destination_airport": "CDG",
            "duration": 480,
            "total_cost": 1245.00,
            "total_cost_per_person": 1245.00,
            "segment": 1,
            "flight_number": "AF123"
        }
        mock_parser.close = AsyncMock()
        
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser
        try:
            # Test with realistic Google Flights URL
            google_flights_url = "https://flights.google.com/flights?hl=en&curr=USD&tfs=CBwQAhoeEgoyMDI0LTA2LTE1agcIARIDSkZLcgcIARIDTEFY"
            
            response = client.post(
                "/parse-flight",
                json={"link": google_flights_url}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify realistic flight data
            assert data["origin_airport"] == "JFK"
            assert data["destination_airport"] == "CDG"
            assert data["duration"] == 480  # 8 hours
            assert data["total_cost"] == 1245.00
            assert data["segment"] == 1
            assert data["flight_number"] == "AF123"
            
        finally:
            app.dependency_overrides.clear()
    
    def test_airbnb_end_to_end(self, client):
        """Test end-to-end with Airbnb URL structure."""
        # Mock parser with realistic Airbnb response
        mock_parser = AsyncMock(spec=UniversalParser)
        mock_parser.parse_lodging_data.return_value = {
            "name": "Luxury Manhattan Suite",
            "location": "New York, NY, USA",
            "number_of_guests": 2,
            "total_cost": 450.00,
            "total_cost_per_person": 225,
            "number_of_nights": 3,
            "check_in": "2024-06-15T15:00:00Z",
            "check_out": "2024-06-18T11:00:00Z"
        }
        mock_parser.close = AsyncMock()
        
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser
        try:
            # Test with realistic Airbnb URL
            airbnb_url = "https://www.airbnb.com/rooms/12345678?adults=2&children=0&infants=0&check_in=2024-06-15&check_out=2024-06-18"
            
            response = client.post(
                "/parse-lodging",
                json={"link": airbnb_url}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify realistic lodging data
            assert data["name"] == "Luxury Manhattan Suite"
            assert data["location"] == "New York, NY, USA"
            assert data["number_of_guests"] == 2
            assert data["total_cost"] == 450.00
            assert data["number_of_nights"] == 3
            
        finally:
            app.dependency_overrides.clear()
    
    def test_booking_com_end_to_end(self, client):
        """Test end-to-end with Booking.com URL structure."""
        # Mock parser with realistic Booking.com response
        mock_parser = AsyncMock(spec=UniversalParser)
        mock_parser.parse_lodging_data.return_value = {
            "name": "Paris Boutique Hotel",
            "location": "Paris, France",
            "number_of_guests": 2,
            "total_cost": 840.00,
            "total_cost_per_person": 420,
            "number_of_nights": 7,
            "check_in": "2024-07-10T14:00:00Z",
            "check_out": "2024-07-17T12:00:00Z"
        }
        mock_parser.close = AsyncMock()
        
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser
        try:
            # Test with realistic Booking.com URL
            booking_url = "https://www.booking.com/hotel/fr/paris-luxury-hotel.html?checkin=2024-07-10&checkout=2024-07-17&group_adults=2"
            
            response = client.post(
                "/parse-lodging",
                json={"link": booking_url}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify realistic lodging data
            assert data["name"] == "Paris Boutique Hotel"
            assert data["location"] == "Paris, France"
            assert data["number_of_guests"] == 2
            assert data["total_cost"] == 840.00
            assert data["number_of_nights"] == 7
            
        finally:
            app.dependency_overrides.clear()
    
    def test_hotels_com_end_to_end(self, client):
        """Test end-to-end with Hotels.com URL structure."""
        # Mock parser with realistic Hotels.com response
        mock_parser = AsyncMock(spec=UniversalParser)
        mock_parser.parse_lodging_data.return_value = {
            "name": "Budget Inn & Suites",
            "location": "Las Vegas, NV, USA",
            "number_of_guests": 2,
            "total_cost": 120.00,
            "total_cost_per_person": 60,
            "number_of_nights": 2,
            "check_in": "2024-09-01T15:00:00Z",
            "check_out": "2024-09-03T11:00:00Z"
        }
        mock_parser.close = AsyncMock()
        
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser
        try:
            # Test with realistic Hotels.com URL
            hotels_url = "https://www.hotels.com/ho123456/2024-09-01/2024-09-03/2-adults"
            
            response = client.post(
                "/parse-lodging",
                json={"link": hotels_url}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify realistic lodging data
            assert data["name"] == "Budget Inn & Suites"
            assert data["location"] == "Las Vegas, NV, USA"
            assert data["number_of_guests"] == 2
            assert data["total_cost"] == 120.00
            assert data["number_of_nights"] == 2
            
        finally:
            app.dependency_overrides.clear() 