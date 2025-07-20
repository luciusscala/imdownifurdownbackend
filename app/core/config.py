"""
Configuration settings for the Travel Data Parser API
"""

import os
import logging
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings


class Environment(str, Enum):
    """Supported environment types"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    """Supported log levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    """Application settings loaded from environment variables with validation"""
    
    # API Configuration
    API_TITLE: str = Field(default="Travel Data Parser API", description="API title")
    API_VERSION: str = Field(default="1.0.0", description="API version")
    API_HOST: str = Field(default="0.0.0.0", description="API host")
    API_PORT: int = Field(default=8000, ge=1, le=65535, description="API port")
    
    # CORS Configuration (stored as string, parsed to list)
    CORS_ORIGINS_STR: str = Field(
        default="http://localhost:3000", 
        description="Allowed CORS origins (comma-separated)",
        alias="CORS_ORIGINS"
    )
    
    # Request Configuration
    REQUEST_TIMEOUT: int = Field(
        default=60, 
        ge=10, 
        le=300, 
        description="Request timeout in seconds"
    )
    RATE_LIMIT_PER_MINUTE: int = Field(
        default=100, 
        ge=1, 
        le=10000, 
        description="Rate limit per minute per IP"
    )
    
    # Cache Configuration
    CACHE_TTL: int = Field(
        default=3600, 
        ge=60, 
        le=86400, 
        description="Cache TTL in seconds"
    )
    ENABLE_CACHE: bool = Field(
        default=True, 
        description="Enable/disable caching for cost optimization"
    )
    CACHE_MAX_SIZE: int = Field(
        default=1000, 
        ge=10, 
        le=100000, 
        description="Maximum number of cache entries"
    )
    
    # Logging Configuration
    LOG_LEVEL: LogLevel = Field(
        default=LogLevel.INFO, 
        description="Logging level"
    )
    
    # External API Keys
    ANTHROPIC_API_KEY: str = Field(
        default="", 
        description="Anthropic Claude API key for LLM data extraction"
    )
    
    # Web Scraping Configuration
    ENABLE_SELENIUM: bool = Field(
        default=False, 
        description="Enable Selenium for JavaScript-heavy sites"
    )
    USER_AGENT_ROTATION: bool = Field(
        default=True, 
        description="Enable User-Agent rotation for web scraping"
    )
    
    # Environment Configuration
    ENVIRONMENT: Environment = Field(
        default=Environment.DEVELOPMENT, 
        description="Application environment"
    )
    
    # Security Configuration
    API_KEY_MIN_LENGTH: int = Field(
        default=20, 
        description="Minimum required length for API keys"
    )
    
    ENABLE_PLAYWRIGHT: bool = Field(
        default=False,
        description="Enable Playwright for JS-heavy site extraction"
    )
    
    @property
    def CORS_ORIGINS(self) -> List[str]:
        """Get CORS origins as a list"""
        return [origin.strip() for origin in self.CORS_ORIGINS_STR.split(',') if origin.strip()]
    
    @field_validator('ANTHROPIC_API_KEY')
    @classmethod
    def validate_anthropic_api_key(cls, v: str) -> str:
        """Validate Anthropic API key format and presence"""
        if not v:
            raise ValueError("ANTHROPIC_API_KEY is required and cannot be empty")
        
        if not v.startswith('sk-ant-'):
            raise ValueError("ANTHROPIC_API_KEY must start with 'sk-ant-'")
        
        if len(v) < 50:  # Anthropic keys are typically much longer
            raise ValueError("ANTHROPIC_API_KEY appears to be invalid (too short)")
        
        return v
    
    @field_validator('LOG_LEVEL', mode='before')
    @classmethod
    def validate_log_level(cls, v) -> str:
        """Validate and normalize log level"""
        if isinstance(v, str):
            return v.upper()
        return v
    
    @model_validator(mode='after')
    def validate_environment_specific_settings(self) -> 'Settings':
        """Validate environment-specific configuration"""
        # Production-specific validations
        if self.ENVIRONMENT == Environment.PRODUCTION:
            # Ensure secure CORS origins in production
            if any('localhost' in origin for origin in self.CORS_ORIGINS):
                logging.warning(
                    "Production environment detected with localhost CORS origins. "
                    "Consider updating CORS_ORIGINS for production."
                )
            
            # Ensure appropriate log level for production
            if self.LOG_LEVEL == LogLevel.DEBUG:
                logging.warning(
                    "DEBUG log level detected in production environment. "
                    "Consider using INFO or WARNING for production."
                )
        
        return self
    
    def get_environment_config(self) -> Dict[str, Any]:
        """Get environment-specific configuration"""
        base_config = {
            'api_title': self.API_TITLE,
            'api_version': self.API_VERSION,
            'environment': self.ENVIRONMENT,
            'debug': self.ENVIRONMENT == Environment.DEVELOPMENT,
            'testing': self.ENVIRONMENT == Environment.STAGING,
        }
        
        if self.ENVIRONMENT == Environment.PRODUCTION:
            base_config.update({
                'log_level': LogLevel.INFO,
                'enable_docs': False,  # Disable API docs in production
                'enable_redoc': False,
            })
        else:
            base_config.update({
                'log_level': self.LOG_LEVEL,
                'enable_docs': True,
                'enable_redoc': True,
            })
        
        return base_config
    
    def validate_required_settings(self) -> None:
        """Validate that all required settings are present and valid"""
        errors = []
        
        # Check required API key
        if not self.ANTHROPIC_API_KEY:
            errors.append("ANTHROPIC_API_KEY is required")
        
        # Check environment-specific requirements (warnings only, not errors)
        if self.ENVIRONMENT == Environment.PRODUCTION:
            if self.LOG_LEVEL == LogLevel.DEBUG:
                logging.warning("DEBUG log level not recommended for production")
        
        if errors:
            raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")
    
    def get_cache_config(self) -> Dict[str, Any]:
        """Get cache-specific configuration"""
        return {
            'enabled': self.ENABLE_CACHE,
            'ttl': self.CACHE_TTL,
            'max_size': self.CACHE_MAX_SIZE,
        }
    
    def get_rate_limit_config(self) -> Dict[str, Any]:
        """Get rate limiting configuration"""
        return {
            'requests_per_minute': self.RATE_LIMIT_PER_MINUTE,
            'timeout': self.REQUEST_TIMEOUT,
        }
    
    def get_scraping_config(self) -> Dict[str, Any]:
        """Get web scraping configuration"""
        return {
            'enable_selenium': self.ENABLE_SELENIUM,
            'user_agent_rotation': self.USER_AGENT_ROTATION,
            'timeout': self.REQUEST_TIMEOUT,
        }
    
    def mask_sensitive_data(self) -> Dict[str, Any]:
        """Get configuration with sensitive data masked for logging"""
        config = self.model_dump()
        
        # Mask API keys
        if config.get('ANTHROPIC_API_KEY'):
            config['ANTHROPIC_API_KEY'] = f"{config['ANTHROPIC_API_KEY'][:10]}***"
        
        return config
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "validate_assignment": True,
        "use_enum_values": True,
        "env_parse_none_str": "None",
    }
    



def get_settings() -> Settings:
    """Get validated settings instance"""
    settings = Settings()
    settings.validate_required_settings()
    return settings


# Global settings instance - will be initialized when first accessed
settings: Optional[Settings] = None


def get_global_settings() -> Settings:
    """Get or create global settings instance"""
    global settings
    if settings is None:
        settings = get_settings()
    return settings