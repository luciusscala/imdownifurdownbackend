"""Request models for the Travel Data Parser API."""

from pydantic import BaseModel, HttpUrl, ConfigDict


class FlightParseRequest(BaseModel):
    """Request model for flight parsing endpoint."""
    
    model_config = ConfigDict(
        json_encoders={HttpUrl: str},
        json_schema_extra={
            "example": {
                "link": "https://flights.google.com/flights?hl=en&curr=USD"
            }
        }
    )
    
    link: HttpUrl


class LodgingParseRequest(BaseModel):
    """Request model for lodging parsing endpoint."""
    
    model_config = ConfigDict(
        json_encoders={HttpUrl: str},
        json_schema_extra={
            "example": {
                "link": "https://www.airbnb.com/rooms/12345"
            }
        }
    )
    
    link: HttpUrl