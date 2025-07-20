# Pydantic models for request/response validation

from .requests import FlightParseRequest, LodgingParseRequest
from .responses import FlightParseResponse, LodgingParseResponse, ErrorResponse

__all__ = [
    "FlightParseRequest",
    "LodgingParseRequest", 
    "FlightParseResponse",
    "LodgingParseResponse",
    "ErrorResponse"
]