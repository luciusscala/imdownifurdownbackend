"""Response models for the Travel Data Parser API."""

from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class FlightParseResponse(BaseModel):
    """Response model for flight parsing endpoint."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "origin_airport": "JFK",
                "destination_airport": "CDG",
                "duration": 480,
                "total_cost": 1200.50,
                "total_cost_per_person": 600.25,
                "segment": 1,
                "flight_number": "AF123"
            }
        }
    )
    
    origin_airport: str = Field(..., description="Origin airport code (IATA preferred)")
    destination_airport: str = Field(..., description="Destination airport code (IATA preferred)")
    duration: int = Field(..., description="Total flight time in minutes", ge=0)
    total_cost: float = Field(..., description="Total cost as decimal", ge=0)
    total_cost_per_person: float = Field(..., description="Cost per person as decimal", ge=0)
    segment: int = Field(..., description="Number of flight segments/stops", ge=0)
    flight_number: str = Field(..., description="Primary flight number")


class LodgingParseResponse(BaseModel):
    """Response model for lodging parsing endpoint."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Luxury Hotel Paris",
                "location": "Paris, France",
                "number_of_guests": 2,
                "total_cost": 450.00,
                "total_cost_per_person": 225,
                "number_of_nights": 3,
                "check_in": "2024-06-15T15:00:00+02:00",
                "check_out": "2024-06-18T11:00:00+02:00"
            }
        }
    )
    
    name: str = Field(..., description="Hotel/property name")
    location: str = Field(..., description="City, country or full address")
    number_of_guests: int = Field(..., description="Number of guests", ge=1)
    total_cost: float = Field(..., description="Total cost as decimal", ge=0)
    total_cost_per_person: int = Field(..., description="Cost per person as integer", ge=0)
    number_of_nights: int = Field(..., description="Number of nights", ge=1)
    check_in: datetime = Field(..., description="Check-in date in ISO format with timezone")
    check_out: datetime = Field(..., description="Check-out date in ISO format with timezone")


class ErrorResponse(BaseModel):
    """Error response model for consistent error handling."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": "INVALID_URL",
                "message": "Invalid or malformed URL provided",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }
    )
    
    error: str = Field(..., description="Error code or type")
    message: str = Field(..., description="Human-readable error message")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), 
        description="Error timestamp"
    )