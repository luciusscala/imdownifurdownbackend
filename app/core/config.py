"""
Configuration settings for the Travel Data Parser API
"""

import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # API Configuration
    API_TITLE: str = "Travel Data Parser API"
    API_VERSION: str = "1.0.0"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # CORS Configuration
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    
    # Request Configuration
    REQUEST_TIMEOUT: int = 60
    RATE_LIMIT_PER_MINUTE: int = 100
    
    # Cache Configuration
    CACHE_TTL: int = 3600  # Cache TTL in seconds (1 hour default)
    ENABLE_CACHE: bool = True  # Enable/disable caching
    CACHE_MAX_SIZE: int = 1000  # Maximum number of cache entries
    
    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    
    # External API Keys
    ANTHROPIC_API_KEY: str = ""
    
    # Web Scraping Configuration
    ENABLE_SELENIUM: bool = False
    USER_AGENT_ROTATION: bool = True
    
    # Environment
    ENVIRONMENT: str = "development"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()