"""
Universal Parser service that combines web scraping and LLM extraction
for travel booking data from any supported platform.
"""

import logging
from typing import Dict, Any, Optional, Union
from urllib.parse import urlparse
from pydantic import ValidationError

from app.services.http_client import AsyncHttpClient
from app.services.text_extractor import TextExtractor
from app.services.llm_data_extractor import LLMDataExtractor
from app.models.responses import FlightParseResponse, LodgingParseResponse


class UniversalParser:
    """
    Universal parser that combines web scraping and LLM extraction
    to parse travel booking data from any supported platform.
    """
    
    def __init__(
        self, 
        anthropic_api_key: str,
        http_client: Optional[AsyncHttpClient] = None,
        text_extractor: Optional[TextExtractor] = None,
        llm_extractor: Optional[LLMDataExtractor] = None
    ):
        """
        Initialize the Universal Parser.
        
        Args:
            anthropic_api_key: API key for Anthropic Claude
            http_client: Optional HTTP client instance
            text_extractor: Optional text extractor instance
            llm_extractor: Optional LLM data extractor instance
        """
        self.logger = logging.getLogger(__name__)
        
        # Initialize services
        self.http_client = http_client or AsyncHttpClient()
        self.text_extractor = text_extractor or TextExtractor()
        self.llm_extractor = llm_extractor or LLMDataExtractor(anthropic_api_key)
        
        # Supported platforms for flight parsing
        self.flight_platforms = {
            'google.com', 'flights.google.com',
            'expedia.com', 'kayak.com', 'priceline.com',
            'united.com', 'delta.com', 'american.com', 'jetblue.com',
            'lufthansa.com', 'airfrance.com', 'klm.com', 'british-airways.com'
        }
        
        # Supported platforms for lodging parsing
        self.lodging_platforms = {
            'airbnb.com', 'booking.com', 'hotels.com', 'expedia.com',
            'marriott.com', 'hilton.com', 'hyatt.com', 'ihg.com',
            'vrbo.com', 'homeaway.com', 'agoda.com', 'trivago.com'
        }
    
    async def scrape_and_extract_text(self, url: str) -> str:
        """
        Scrape any travel booking URL and extract clean text.
        
        Args:
            url: Travel booking URL to scrape
            
        Returns:
            Clean text extracted from the page
            
        Raises:
            ValueError: If URL is invalid or scraping fails
            Exception: If HTTP request fails
        """
        try:
            self.logger.info(f"Scraping URL: {url}")
            
            # Validate URL format
            parsed_url = urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                raise ValueError(f"Invalid URL format: {url}")
            
            # Make HTTP request to fetch page content
            response = await self.http_client.get(url)
            response.raise_for_status()
            
            # Extract clean text from HTML
            html_content = response.text
            clean_text = self.text_extractor.extract_text(html_content, url)
            
            if not clean_text.strip():
                raise ValueError("No meaningful text content found on the page")
            
            self.logger.info(f"Successfully extracted {len(clean_text)} characters of text")
            return clean_text
            
        except Exception as e:
            self.logger.error(f"Failed to scrape and extract text from {url}: {str(e)}")
            raise
    
    async def parse_flight_data(self, url: str) -> Dict[str, Any]:
        """
        Parse flight booking URL and extract structured flight data.
        
        Args:
            url: Flight booking URL
            
        Returns:
            Dictionary containing structured flight data
            
        Raises:
            ValueError: If URL is not supported or parsing fails
        """
        try:
            # Check if URL is from a supported flight platform
            domain = self._get_domain(url)
            if not self._is_flight_platform(domain):
                self.logger.warning(f"Domain {domain} may not be a supported flight platform")
            
            # Scrape and extract text
            text_content = await self.scrape_and_extract_text(url)
            
            # Use LLM to extract structured flight data
            flight_data = await self.llm_extractor.extract_flight_data(text_content)
            
            # Validate data against Pydantic model
            validated_data = self._validate_flight_data(flight_data)
            
            self.logger.info(f"Successfully parsed flight data from {url}")
            return validated_data
            
        except Exception as e:
            self.logger.error(f"Failed to parse flight data from {url}: {str(e)}")
            raise ValueError(f"Flight parsing failed: {str(e)}")
    
    async def parse_lodging_data(self, url: str) -> Dict[str, Any]:
        """
        Parse lodging booking URL and extract structured accommodation data.
        
        Args:
            url: Lodging booking URL
            
        Returns:
            Dictionary containing structured lodging data
            
        Raises:
            ValueError: If URL is not supported or parsing fails
        """
        try:
            # Check if URL is from a supported lodging platform
            domain = self._get_domain(url)
            if not self._is_lodging_platform(domain):
                self.logger.warning(f"Domain {domain} may not be a supported lodging platform")
            
            # Scrape and extract text
            text_content = await self.scrape_and_extract_text(url)
            
            # Use LLM to extract structured lodging data
            lodging_data = await self.llm_extractor.extract_lodging_data(text_content)
            
            # Validate data against Pydantic model
            validated_data = self._validate_lodging_data(lodging_data)
            
            self.logger.info(f"Successfully parsed lodging data from {url}")
            return validated_data
            
        except Exception as e:
            self.logger.error(f"Failed to parse lodging data from {url}: {str(e)}")
            raise ValueError(f"Lodging parsing failed: {str(e)}")
    
    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            # Remove www. prefix if present
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except Exception:
            return ""
    
    def _is_flight_platform(self, domain: str) -> bool:
        """Check if domain is a supported flight platform."""
        return any(platform in domain for platform in self.flight_platforms)
    
    def _is_lodging_platform(self, domain: str) -> bool:
        """Check if domain is a supported lodging platform."""
        return any(platform in domain for platform in self.lodging_platforms)
    
    def _validate_flight_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate extracted flight data against Pydantic model.
        
        Args:
            data: Raw flight data from LLM extraction
            
        Returns:
            Validated flight data
            
        Raises:
            ValueError: If data validation fails
        """
        try:
            # Create Pydantic model instance for validation
            flight_response = FlightParseResponse(**data)
            validated_data = flight_response.model_dump()
            
            self.logger.debug(f"Flight data validation successful: {validated_data}")
            return validated_data
            
        except ValidationError as e:
            self.logger.error(f"Flight data validation failed: {e}")
            
            # Handle validation errors by providing fallback values
            def safe_int(value, default=0):
                try:
                    return max(0, int(value))
                except (ValueError, TypeError):
                    return default
            
            def safe_float(value, default=0.0):
                try:
                    return max(0.0, float(value))
                except (ValueError, TypeError):
                    return default
            
            fallback_data = {
                "origin_airport": data.get("origin_airport", "Unknown"),
                "destination_airport": data.get("destination_airport", "Unknown"),
                "duration": safe_int(data.get("duration", 0)),
                "total_cost": safe_float(data.get("total_cost", 0.0)),
                "total_cost_per_person": safe_float(data.get("total_cost_per_person", 0.0)),
                "segment": safe_int(data.get("segment", 1), 1),
                "flight_number": data.get("flight_number", "Unknown")
            }
            
            try:
                # Validate fallback data
                flight_response = FlightParseResponse(**fallback_data)
                return flight_response.model_dump()
            except ValidationError:
                # If even fallback fails, raise the original error
                raise ValueError(f"Flight data validation failed: {e}")
    
    def _validate_lodging_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate extracted lodging data against Pydantic model.
        
        Args:
            data: Raw lodging data from LLM extraction
            
        Returns:
            Validated lodging data
            
        Raises:
            ValueError: If data validation fails
        """
        try:
            # Create Pydantic model instance for validation
            lodging_response = LodgingParseResponse(**data)
            validated_data = lodging_response.model_dump()
            
            self.logger.debug(f"Lodging data validation successful: {validated_data}")
            return validated_data
            
        except ValidationError as e:
            self.logger.error(f"Lodging data validation failed: {e}")
            
            # Handle validation errors by providing fallback values
            from datetime import datetime
            
            def safe_int(value, default=1):
                try:
                    return max(1, int(value))
                except (ValueError, TypeError):
                    return default
            
            def safe_float(value, default=0.0):
                try:
                    return max(0.0, float(value))
                except (ValueError, TypeError):
                    return default
            
            def safe_datetime(value, default_str="1970-01-01"):
                if isinstance(value, datetime):
                    return value
                try:
                    return datetime.fromisoformat(str(value))
                except (ValueError, TypeError):
                    return datetime.fromisoformat(default_str)
            
            fallback_data = {
                "name": data.get("name", "Unknown"),
                "location": data.get("location", "Unknown"),
                "number_of_guests": safe_int(data.get("number_of_guests", 1)),
                "total_cost": safe_float(data.get("total_cost", 0.0)),
                "total_cost_per_person": safe_int(data.get("total_cost_per_person", 0), 0),
                "number_of_nights": safe_int(data.get("number_of_nights", 1)),
                "check_in": safe_datetime(data.get("check_in"), "1970-01-01"),
                "check_out": safe_datetime(data.get("check_out"), "1970-01-02")
            }
            
            try:
                # Validate fallback data
                lodging_response = LodgingParseResponse(**fallback_data)
                return lodging_response.model_dump()
            except ValidationError:
                # If even fallback fails, raise the original error
                raise ValueError(f"Lodging data validation failed: {e}")
    
    async def close(self):
        """Close HTTP client connection."""
        if self.http_client:
            await self.http_client.close()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()