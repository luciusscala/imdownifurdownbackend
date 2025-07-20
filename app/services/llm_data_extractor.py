"""
LLM Data Extractor service using Anthropic Claude API for travel data extraction.
"""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

import anthropic
from pydantic import BaseModel, ValidationError

from app.models.responses import FlightParseResponse, LodgingParseResponse


class LLMDataExtractor:
    """
    Service for extracting structured travel data using Anthropic Claude API.
    """
    
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        """
        Initialize the LLM Data Extractor.
        
        Args:
            api_key: Anthropic API key
            model: Claude model to use for extraction
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.logger = logging.getLogger(__name__)
        
    async def extract_flight_data(self, text_content: str) -> Dict[str, Any]:
        """
        Extract flight data from text content using Claude API.
        
        Args:
            text_content: Clean text extracted from flight booking page
            
        Returns:
            Dictionary containing structured flight data
            
        Raises:
            ValueError: If extraction fails or returns invalid data
        """
        prompt = self._build_flight_extraction_prompt(text_content)
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0.1,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            # Extract JSON from response
            response_text = response.content[0].text.strip()
            self.logger.info(f"Claude response: {response_text}")
            
            # Parse JSON response
            flight_data = self._parse_json_response(response_text)
            
            # Validate response structure
            validated_data = self._validate_flight_data(flight_data)
            
            return validated_data
            
        except Exception as e:
            self.logger.error(f"Flight data extraction failed: {str(e)}")
            raise ValueError(f"Failed to extract flight data: {str(e)}")
    
    async def extract_lodging_data(self, text_content: str) -> Dict[str, Any]:
        """
        Extract lodging data from text content using Claude API.
        
        Args:
            text_content: Clean text extracted from lodging booking page
            
        Returns:
            Dictionary containing structured lodging data
            
        Raises:
            ValueError: If extraction fails or returns invalid data
        """
        prompt = self._build_lodging_extraction_prompt(text_content)
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0.1,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            # Extract JSON from response
            response_text = response.content[0].text.strip()
            self.logger.info(f"Claude response: {response_text}")
            
            # Parse JSON response
            lodging_data = self._parse_json_response(response_text)
            
            # Validate response structure
            validated_data = self._validate_lodging_data(lodging_data)
            
            return validated_data
            
        except Exception as e:
            self.logger.error(f"Lodging data extraction failed: {str(e)}")
            raise ValueError(f"Failed to extract lodging data: {str(e)}")
    
    def _build_flight_extraction_prompt(self, text_content: str) -> str:
        """Build prompt for flight data extraction."""
        return f"""
You are a travel data extraction expert. Extract flight booking information from the following text and return it as a JSON object with exactly these fields:

Required JSON format:
{{
    "origin_airport": "string (IATA code preferred, e.g., 'JFK' or city name if IATA not available)",
    "destination_airport": "string (IATA code preferred, e.g., 'CDG' or city name if IATA not available)",
    "duration": "integer (total flight time in minutes, calculate from hours/minutes if needed)",
    "total_cost": "float (total cost as decimal number, extract numeric value only)",
    "total_cost_per_person": "float (cost per person as decimal, same as total_cost if single passenger)",
    "segment": "integer (number of flight segments/stops, 1 for direct flight)",
    "flight_number": "string (primary flight number, e.g., 'AF123' or 'Multiple' if multiple flights)"
}}

Instructions:
- Extract only the information that is clearly present in the text
- For missing data, use these defaults: origin_airport="Unknown", destination_airport="Unknown", duration=0, total_cost=0.0, total_cost_per_person=0.0, segment=1, flight_number="Unknown"
- Convert duration to minutes (e.g., "2h 30m" = 150 minutes)
- Extract numeric values only for costs (remove currency symbols)
- For multi-segment flights, count the number of flights/stops
- Return only valid JSON, no additional text or explanation

Text to analyze:
{text_content}
"""

    def _build_lodging_extraction_prompt(self, text_content: str) -> str:
        """Build prompt for lodging data extraction."""
        return f"""
You are a travel data extraction expert. Extract lodging booking information from the following text and return it as a JSON object with exactly these fields:

Required JSON format:
{{
    "name": "string (hotel/property name)",
    "location": "string (city, country or full address)",
    "number_of_guests": "integer (number of guests)",
    "total_cost": "float (total cost as decimal number)",
    "total_cost_per_person": "integer (cost per person as integer)",
    "number_of_nights": "integer (number of nights)",
    "check_in": "string (ISO format date: YYYY-MM-DD)",
    "check_out": "string (ISO format date: YYYY-MM-DD)"
}}

Instructions:
- Extract only the information that is clearly present in the text
- For missing data, use these defaults: name="Unknown", location="Unknown", number_of_guests=1, total_cost=0.0, total_cost_per_person=0, number_of_nights=1, check_in="1970-01-01", check_out="1970-01-02"
- Convert dates to ISO format (YYYY-MM-DD)
- Extract numeric values only for costs (remove currency symbols)
- Calculate number_of_nights from check-in/check-out dates if not explicitly stated
- Calculate total_cost_per_person by dividing total_cost by number_of_guests (round to integer)
- Return only valid JSON, no additional text or explanation

Text to analyze:
{text_content}
"""

    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse JSON response from Claude, handling potential formatting issues.
        
        Args:
            response_text: Raw response text from Claude
            
        Returns:
            Parsed JSON data
            
        Raises:
            ValueError: If JSON parsing fails
        """
        try:
            # Try to find JSON in the response (in case there's extra text)
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON object found in response")
            
            json_str = response_text[start_idx:end_idx]
            return json.loads(json_str)
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parsing failed: {e}")
            raise ValueError(f"Invalid JSON response: {e}")
    
    def _validate_flight_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and clean flight data response.
        
        Args:
            data: Raw flight data from Claude
            
        Returns:
            Validated and cleaned flight data
        """
        # Fill in missing fields with defaults before validation
        defaults = {
            "origin_airport": "Unknown",
            "destination_airport": "Unknown", 
            "duration": 0,
            "total_cost": 0.0,
            "total_cost_per_person": 0.0,
            "segment": 1,
            "flight_number": "Unknown"
        }
        
        # Merge data with defaults, keeping existing values
        complete_data = {**defaults, **data}
        
        try:
            # Create Pydantic model instance for validation
            flight_response = FlightParseResponse(**complete_data)
            return flight_response.model_dump()
            
        except ValidationError as e:
            self.logger.error(f"Flight data validation failed: {e}")
            # Return default values if validation fails
            return defaults
    
    def _validate_lodging_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and clean lodging data response.
        
        Args:
            data: Raw lodging data from Claude
            
        Returns:
            Validated and cleaned lodging data
        """
        # Fill in missing fields with defaults before validation
        defaults = {
            "name": "Unknown",
            "location": "Unknown",
            "number_of_guests": 1,
            "total_cost": 0.0,
            "total_cost_per_person": 0,
            "number_of_nights": 1,
            "check_in": datetime.fromisoformat("1970-01-01"),
            "check_out": datetime.fromisoformat("1970-01-02")
        }
        
        # Merge data with defaults, keeping existing values
        complete_data = {**defaults, **data}
        
        try:
            # Handle date conversion from string to datetime
            if 'check_in' in complete_data and isinstance(complete_data['check_in'], str):
                try:
                    # Convert ISO date string to datetime object
                    complete_data['check_in'] = datetime.fromisoformat(complete_data['check_in'])
                except ValueError:
                    complete_data['check_in'] = datetime.fromisoformat("1970-01-01")
            
            if 'check_out' in complete_data and isinstance(complete_data['check_out'], str):
                try:
                    # Convert ISO date string to datetime object
                    complete_data['check_out'] = datetime.fromisoformat(complete_data['check_out'])
                except ValueError:
                    complete_data['check_out'] = datetime.fromisoformat("1970-01-02")
            
            # Create Pydantic model instance for validation
            lodging_response = LodgingParseResponse(**complete_data)
            return lodging_response.model_dump()
            
        except ValidationError as e:
            self.logger.error(f"Lodging data validation failed: {e}")
            # Return default values if validation fails
            return defaults