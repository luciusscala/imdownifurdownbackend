"""
Tests for cache management endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app


class TestCacheEndpoints:
    """Test cache management endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_cache_stats_endpoint(self, client):
        """Test cache statistics endpoint."""
        response = client.get("/cache/stats")
        assert response.status_code == 200
        
        data = response.json()
        
        # Check expected fields
        expected_fields = [
            'enabled', 'ttl', 'max_size', 'current_size',
            'hits', 'misses', 'hit_rate', 'evictions', 'cleanups'
        ]
        for field in expected_fields:
            assert field in data
        
        # Check data types
        assert isinstance(data['enabled'], bool)
        assert isinstance(data['ttl'], int)
        assert isinstance(data['max_size'], int)
        assert isinstance(data['current_size'], int)
        assert isinstance(data['hits'], int)
        assert isinstance(data['misses'], int)
        assert isinstance(data['hit_rate'], float)
        assert isinstance(data['evictions'], int)
        assert isinstance(data['cleanups'], int)
    
    def test_cache_info_endpoint(self, client):
        """Test cache detailed information endpoint."""
        response = client.get("/cache/info")
        assert response.status_code == 200
        
        data = response.json()
        
        # Check structure
        assert 'stats' in data
        assert 'entries' in data
        assert isinstance(data['entries'], list)
    
    def test_cache_cleanup_endpoint(self, client):
        """Test cache cleanup endpoint."""
        response = client.post("/cache/cleanup")
        assert response.status_code == 200
        
        data = response.json()
        assert 'message' in data
        assert 'cleaned up' in data['message'].lower()
    
    def test_cache_clear_endpoint(self, client):
        """Test cache clear endpoint."""
        response = client.delete("/cache/clear")
        assert response.status_code == 200
        
        data = response.json()
        assert 'message' in data
        assert 'cleared' in data['message'].lower()
    
    def test_cache_endpoints_cors_headers(self, client):
        """Test that cache endpoints include CORS headers."""
        # Test preflight request
        response = client.options(
            "/cache/stats",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET"
            }
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
    
    def test_cache_endpoints_with_disabled_cache(self, client):
        """Test cache endpoints when cache is disabled."""
        with patch('app.main.cache_manager.enabled', False):
            # Stats should still work
            response = client.get("/cache/stats")
            assert response.status_code == 200
            data = response.json()
            assert data['enabled'] is False
            
            # Cleanup should return 0
            response = client.post("/cache/cleanup")
            assert response.status_code == 200
            data = response.json()
            assert "0" in data['message']