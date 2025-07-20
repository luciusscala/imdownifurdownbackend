"""
Tests for configuration management and environment variable handling
"""

import os
import pytest
from unittest.mock import patch
from pydantic import ValidationError

from app.core.config import Settings, Environment, LogLevel, get_settings


class TestSettings:
    """Test Settings class validation and functionality"""
    
    def test_default_settings(self):
        """Test default settings values"""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test-key-12345678901234567890123456789012345678901234567890"}, clear=True):
            settings = Settings()
            
            assert settings.API_TITLE == "Travel Data Parser API"
            assert settings.API_VERSION == "1.0.0"
            assert settings.API_HOST == "0.0.0.0"
            assert settings.API_PORT == 8000
            assert settings.CORS_ORIGINS == ["http://localhost:3000"]
            assert settings.REQUEST_TIMEOUT == 60
            assert settings.RATE_LIMIT_PER_MINUTE == 100
            assert settings.CACHE_TTL == 3600
            assert settings.ENABLE_CACHE is True
            assert settings.CACHE_MAX_SIZE == 1000
            assert settings.LOG_LEVEL == LogLevel.INFO
            assert settings.ENABLE_SELENIUM is False
            assert settings.USER_AGENT_ROTATION is True
            assert settings.ENVIRONMENT == Environment.DEVELOPMENT
    
    def test_environment_variable_override(self):
        """Test that environment variables override defaults"""
        env_vars = {
            "API_TITLE": "Custom API Title",
            "API_PORT": "9000",
            "REQUEST_TIMEOUT": "120",
            "RATE_LIMIT_PER_MINUTE": "200",
            "CACHE_TTL": "7200",
            "ENABLE_CACHE": "false",
            "LOG_LEVEL": "DEBUG",
            "ENVIRONMENT": "production",
            "ANTHROPIC_API_KEY": "sk-ant-test-key-12345678901234567890123456789012345678901234567890"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()
            
            assert settings.API_TITLE == "Custom API Title"
            assert settings.API_PORT == 9000
            assert settings.REQUEST_TIMEOUT == 120
            assert settings.RATE_LIMIT_PER_MINUTE == 200
            assert settings.CACHE_TTL == 7200
            assert settings.ENABLE_CACHE is False
            assert settings.LOG_LEVEL == LogLevel.DEBUG
            assert settings.ENVIRONMENT == Environment.PRODUCTION
    
    def test_anthropic_api_key_validation_missing(self):
        """Test that missing Anthropic API key raises validation error"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            
            assert "ANTHROPIC_API_KEY is required" in str(exc_info.value)
    
    def test_anthropic_api_key_validation_invalid_format(self):
        """Test that invalid Anthropic API key format raises validation error"""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "invalid-key"}, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            
            assert "must start with 'sk-ant-'" in str(exc_info.value)
    
    def test_anthropic_api_key_validation_too_short(self):
        """Test that too short Anthropic API key raises validation error"""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-short"}, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            
            assert "too short" in str(exc_info.value)
    
    def test_anthropic_api_key_validation_valid(self):
        """Test that valid Anthropic API key passes validation"""
        valid_key = "sk-ant-test-key-12345678901234567890123456789012345678901234567890"
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": valid_key}, clear=True):
            settings = Settings()
            assert settings.ANTHROPIC_API_KEY == valid_key
    
    def test_cors_origins_string_parsing(self):
        """Test CORS origins parsing from comma-separated string"""
        cors_string = "http://localhost:3000,https://example.com,https://app.example.com"
        with patch.dict(os.environ, {
            "CORS_ORIGINS": cors_string,
            "ANTHROPIC_API_KEY": "sk-ant-test-key-12345678901234567890123456789012345678901234567890"
        }, clear=True):
            settings = Settings()
            
            expected = ["http://localhost:3000", "https://example.com", "https://app.example.com"]
            assert settings.CORS_ORIGINS == expected
    
    def test_cors_origins_with_spaces(self):
        """Test CORS origins parsing with spaces"""
        cors_string = " http://localhost:3000 , https://example.com , https://app.example.com "
        with patch.dict(os.environ, {
            "CORS_ORIGINS": cors_string,
            "ANTHROPIC_API_KEY": "sk-ant-test-key-12345678901234567890123456789012345678901234567890"
        }, clear=True):
            settings = Settings()
            
            expected = ["http://localhost:3000", "https://example.com", "https://app.example.com"]
            assert settings.CORS_ORIGINS == expected
    
    def test_log_level_case_insensitive(self):
        """Test that log level is case insensitive"""
        with patch.dict(os.environ, {
            "LOG_LEVEL": "debug",
            "ANTHROPIC_API_KEY": "sk-ant-test-key-12345678901234567890123456789012345678901234567890"
        }, clear=True):
            settings = Settings()
            assert settings.LOG_LEVEL == LogLevel.DEBUG
    
    def test_port_validation_bounds(self):
        """Test API port validation bounds"""
        # Test lower bound
        with patch.dict(os.environ, {
            "API_PORT": "0",
            "ANTHROPIC_API_KEY": "sk-ant-test-key-12345678901234567890123456789012345678901234567890"
        }, clear=True):
            with pytest.raises(ValidationError):
                Settings()
        
        # Test upper bound
        with patch.dict(os.environ, {
            "API_PORT": "65536",
            "ANTHROPIC_API_KEY": "sk-ant-test-key-12345678901234567890123456789012345678901234567890"
        }, clear=True):
            with pytest.raises(ValidationError):
                Settings()
        
        # Test valid port
        with patch.dict(os.environ, {
            "API_PORT": "8080",
            "ANTHROPIC_API_KEY": "sk-ant-test-key-12345678901234567890123456789012345678901234567890"
        }, clear=True):
            settings = Settings()
            assert settings.API_PORT == 8080
    
    def test_timeout_validation_bounds(self):
        """Test request timeout validation bounds"""
        # Test lower bound
        with patch.dict(os.environ, {
            "REQUEST_TIMEOUT": "5",
            "ANTHROPIC_API_KEY": "sk-ant-test-key-12345678901234567890123456789012345678901234567890"
        }, clear=True):
            with pytest.raises(ValidationError):
                Settings()
        
        # Test upper bound
        with patch.dict(os.environ, {
            "REQUEST_TIMEOUT": "400",
            "ANTHROPIC_API_KEY": "sk-ant-test-key-12345678901234567890123456789012345678901234567890"
        }, clear=True):
            with pytest.raises(ValidationError):
                Settings()
    
    def test_cache_ttl_validation_bounds(self):
        """Test cache TTL validation bounds"""
        # Test lower bound
        with patch.dict(os.environ, {
            "CACHE_TTL": "30",
            "ANTHROPIC_API_KEY": "sk-ant-test-key-12345678901234567890123456789012345678901234567890"
        }, clear=True):
            with pytest.raises(ValidationError):
                Settings()
        
        # Test upper bound
        with patch.dict(os.environ, {
            "CACHE_TTL": "90000",
            "ANTHROPIC_API_KEY": "sk-ant-test-key-12345678901234567890123456789012345678901234567890"
        }, clear=True):
            with pytest.raises(ValidationError):
                Settings()


class TestEnvironmentSpecificSettings:
    """Test environment-specific configuration behavior"""
    
    def test_development_environment_config(self):
        """Test development environment configuration"""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "development",
            "ANTHROPIC_API_KEY": "sk-ant-test-key-12345678901234567890123456789012345678901234567890"
        }, clear=True):
            settings = Settings()
            config = settings.get_environment_config()
            
            assert config['environment'] == Environment.DEVELOPMENT
            assert config['debug'] is True
            assert config['testing'] is False
            assert config['enable_docs'] is True
            assert config['enable_redoc'] is True
    
    def test_staging_environment_config(self):
        """Test staging environment configuration"""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "staging",
            "ANTHROPIC_API_KEY": "sk-ant-test-key-12345678901234567890123456789012345678901234567890"
        }, clear=True):
            settings = Settings()
            config = settings.get_environment_config()
            
            assert config['environment'] == Environment.STAGING
            assert config['debug'] is False
            assert config['testing'] is True
            assert config['enable_docs'] is True
            assert config['enable_redoc'] is True
    
    def test_production_environment_config(self):
        """Test production environment configuration"""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "ANTHROPIC_API_KEY": "sk-ant-test-key-12345678901234567890123456789012345678901234567890"
        }, clear=True):
            settings = Settings()
            config = settings.get_environment_config()
            
            assert config['environment'] == Environment.PRODUCTION
            assert config['debug'] is False
            assert config['testing'] is False
            assert config['enable_docs'] is False
            assert config['enable_redoc'] is False
            assert config['log_level'] == LogLevel.INFO
    
    @patch('logging.warning')
    def test_production_localhost_cors_warning(self, mock_warning):
        """Test warning for localhost CORS in production"""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "CORS_ORIGINS": "http://localhost:3000,https://example.com",
            "ANTHROPIC_API_KEY": "sk-ant-test-key-12345678901234567890123456789012345678901234567890"
        }, clear=True):
            Settings()
            
            mock_warning.assert_called_once()
            assert "localhost CORS origins" in mock_warning.call_args[0][0]
    
    @patch('logging.warning')
    def test_production_debug_log_level_warning(self, mock_warning):
        """Test warning for DEBUG log level in production"""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "LOG_LEVEL": "DEBUG",
            "ANTHROPIC_API_KEY": "sk-ant-test-key-12345678901234567890123456789012345678901234567890"
        }, clear=True):
            Settings()
            
            mock_warning.assert_called()
            warning_calls = [call[0][0] for call in mock_warning.call_args_list]
            assert any("DEBUG log level" in call for call in warning_calls)


class TestConfigurationMethods:
    """Test configuration helper methods"""
    
    def test_get_cache_config(self):
        """Test cache configuration method"""
        with patch.dict(os.environ, {
            "ENABLE_CACHE": "true",
            "CACHE_TTL": "1800",
            "CACHE_MAX_SIZE": "500",
            "ANTHROPIC_API_KEY": "sk-ant-test-key-12345678901234567890123456789012345678901234567890"
        }, clear=True):
            settings = Settings()
            cache_config = settings.get_cache_config()
            
            assert cache_config == {
                'enabled': True,
                'ttl': 1800,
                'max_size': 500,
            }
    
    def test_get_rate_limit_config(self):
        """Test rate limit configuration method"""
        with patch.dict(os.environ, {
            "RATE_LIMIT_PER_MINUTE": "150",
            "REQUEST_TIMEOUT": "90",
            "ANTHROPIC_API_KEY": "sk-ant-test-key-12345678901234567890123456789012345678901234567890"
        }, clear=True):
            settings = Settings()
            rate_config = settings.get_rate_limit_config()
            
            assert rate_config == {
                'requests_per_minute': 150,
                'timeout': 90,
            }
    
    def test_get_scraping_config(self):
        """Test scraping configuration method"""
        with patch.dict(os.environ, {
            "ENABLE_SELENIUM": "true",
            "USER_AGENT_ROTATION": "false",
            "REQUEST_TIMEOUT": "45",
            "ANTHROPIC_API_KEY": "sk-ant-test-key-12345678901234567890123456789012345678901234567890"
        }, clear=True):
            settings = Settings()
            scraping_config = settings.get_scraping_config()
            
            assert scraping_config == {
                'enable_selenium': True,
                'user_agent_rotation': False,
                'timeout': 45,
            }
    
    def test_mask_sensitive_data(self):
        """Test sensitive data masking"""
        api_key = "sk-ant-test-key-12345678901234567890123456789012345678901234567890"
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": api_key}, clear=True):
            settings = Settings()
            masked_config = settings.mask_sensitive_data()
            
            assert masked_config['ANTHROPIC_API_KEY'] == "sk-ant-tes***"
            assert api_key not in str(masked_config)


class TestValidationMethods:
    """Test configuration validation methods"""
    
    def test_validate_required_settings_success(self):
        """Test successful validation of required settings"""
        with patch.dict(os.environ, {
            "ANTHROPIC_API_KEY": "sk-ant-test-key-12345678901234567890123456789012345678901234567890"
        }, clear=True):
            settings = Settings()
            # Should not raise any exception
            settings.validate_required_settings()
    
    def test_validate_required_settings_missing_api_key(self):
        """Test validation failure for missing API key"""
        with patch.dict(os.environ, {}, clear=True):
            # This should fail during Settings() initialization due to validator
            with pytest.raises(ValidationError):
                Settings()
    
    def test_validate_required_settings_production_debug_warning(self):
        """Test validation warning for DEBUG in production"""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "LOG_LEVEL": "DEBUG",
            "ANTHROPIC_API_KEY": "sk-ant-test-key-12345678901234567890123456789012345678901234567890"
        }, clear=True):
            settings = Settings()
            # Should not raise exception but may log warning
            settings.validate_required_settings()


class TestGetSettings:
    """Test get_settings function"""
    
    def test_get_settings_success(self):
        """Test successful settings creation"""
        with patch.dict(os.environ, {
            "ANTHROPIC_API_KEY": "sk-ant-test-key-12345678901234567890123456789012345678901234567890"
        }, clear=True):
            settings = get_settings()
            assert isinstance(settings, Settings)
            assert settings.ANTHROPIC_API_KEY.startswith("sk-ant-")
    
    def test_get_settings_validation_failure(self):
        """Test settings creation with validation failure"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValidationError):
                get_settings()


class TestEnvironmentEnums:
    """Test environment and log level enums"""
    
    def test_environment_enum_values(self):
        """Test Environment enum values"""
        assert Environment.DEVELOPMENT == "development"
        assert Environment.STAGING == "staging"
        assert Environment.PRODUCTION == "production"
    
    def test_log_level_enum_values(self):
        """Test LogLevel enum values"""
        assert LogLevel.DEBUG == "DEBUG"
        assert LogLevel.INFO == "INFO"
        assert LogLevel.WARNING == "WARNING"
        assert LogLevel.ERROR == "ERROR"
        assert LogLevel.CRITICAL == "CRITICAL"