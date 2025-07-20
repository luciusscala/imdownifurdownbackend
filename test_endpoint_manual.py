#!/usr/bin/env python3
"""
Manual test script for the flight parsing endpoint
"""

import asyncio
import os
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock

# Set a dummy API key for testing
os.environ['ANTHROPIC_API_KEY'] = 'test-key-12345'

from app.main import app, get_universal_parser
from app.services.universal_parser import UniversalParser

def test_flight_endpoint_manually():
    """Test the flight endpoint manually with mocked parser."""
    
    # Create a mock parser with successful response
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
    
    # Override the dependency
    app.dependency_overrides[get_universal_parser] = lambda: mock_parser
    
    try:
        # Create test client
        client = TestClient(app)
        
        # Test successful request
        print("Testing successful flight parsing request...")
        response = client.post(
            "/parse-flight",
            json={"link": "https://flights.google.com/flights?hl=en&curr=USD"}
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        assert response.status_code == 200
        data = response.json()
        assert "origin_airport" in data
        assert data["origin_airport"] == "JFK"
        assert data["destination_airport"] == "CDG"
        print("✅ Successful request test passed!")
        
        # Test invalid URL format
        print("\nTesting invalid URL format...")
        response = client.post(
            "/parse-flight",
            json={"link": "not-a-valid-url"}
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        assert response.status_code == 422
        print("✅ Invalid URL format test passed!")
        
        # Test missing link field
        print("\nTesting missing link field...")
        response = client.post(
            "/parse-flight",
            json={}
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        assert response.status_code == 422
        print("✅ Missing link field test passed!")
        
        print("\n🎉 All manual tests passed!")
        
    finally:
        # Clean up dependency overrides
        app.dependency_overrides.clear()

if __name__ == "__main__":
    test_flight_endpoint_manually()