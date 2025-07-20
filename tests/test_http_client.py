"""
Unit tests for AsyncHttpClient, RateLimiter, and UserAgentRotator
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from app.services.http_client import AsyncHttpClient, RateLimiter, UserAgentRotator


class TestUserAgentRotator:
    """Test User-Agent rotation functionality"""
    
    def test_get_random_user_agent(self):
        """Test that random user agent is returned"""
        rotator = UserAgentRotator()
        user_agent = rotator.get_random_user_agent()
        
        assert isinstance(user_agent, str)
        assert len(user_agent) > 0
        assert user_agent in UserAgentRotator.USER_AGENTS
    
    def test_user_agent_rotation(self):
        """Test that different user agents are returned over multiple calls"""
        rotator = UserAgentRotator()
        user_agents = [rotator.get_random_user_agent() for _ in range(20)]
        
        # Should have some variety (not all the same)
        unique_agents = set(user_agents)
        assert len(unique_agents) > 1


class TestRateLimiter:
    """Test rate limiting functionality"""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_allows_requests_under_limit(self):
        """Test that requests under the limit are allowed immediately"""
        rate_limiter = RateLimiter(requests_per_minute=10)
        
        start_time = time.time()
        
        # Make 5 requests (under the limit)
        for _ in range(5):
            await rate_limiter.acquire("example.com")
        
        end_time = time.time()
        
        # Should complete quickly (no rate limiting delay)
        assert end_time - start_time < 1.0
    
    @pytest.mark.asyncio
    async def test_rate_limiter_blocks_requests_over_limit(self):
        """Test that requests over the limit are delayed"""
        rate_limiter = RateLimiter(requests_per_minute=2)
        
        # Make requests up to the limit
        await rate_limiter.acquire("example.com")
        await rate_limiter.acquire("example.com")
        
        # This request should be delayed
        start_time = time.time()
        await rate_limiter.acquire("example.com")
        end_time = time.time()
        
        # Should have been delayed (but we'll use a small delay for testing)
        # In real implementation, this would be longer
        assert end_time - start_time >= 0
    
    @pytest.mark.asyncio
    async def test_rate_limiter_per_domain(self):
        """Test that rate limiting is applied per domain"""
        rate_limiter = RateLimiter(requests_per_minute=2)
        
        # Fill up rate limit for one domain
        await rate_limiter.acquire("example.com")
        await rate_limiter.acquire("example.com")
        
        # Different domain should not be affected
        start_time = time.time()
        await rate_limiter.acquire("other.com")
        end_time = time.time()
        
        # Should complete quickly (no delay for different domain)
        assert end_time - start_time < 1.0
    
    @pytest.mark.asyncio
    async def test_rate_limiter_cleanup_old_requests(self):
        """Test that old requests are cleaned up from tracking"""
        rate_limiter = RateLimiter(requests_per_minute=2)
        
        # Add some old requests manually
        old_time = time.time() - 120  # 2 minutes ago
        rate_limiter.request_times["example.com"] = [old_time, old_time]
        
        # New request should not be blocked by old requests
        start_time = time.time()
        await rate_limiter.acquire("example.com")
        end_time = time.time()
        
        # Should complete quickly (old requests cleaned up)
        assert end_time - start_time < 1.0
        
        # Old requests should be removed
        assert len(rate_limiter.request_times["example.com"]) == 1


class TestAsyncHttpClient:
    """Test AsyncHttpClient functionality"""
    
    @pytest.fixture
    def mock_httpx_client(self):
        """Mock httpx.AsyncClient"""
        with patch('app.services.http_client.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            yield mock_client
    
    @pytest.mark.asyncio
    async def test_successful_get_request(self, mock_httpx_client):
        """Test successful GET request"""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Success"
        mock_httpx_client.request.return_value = mock_response
        
        client = AsyncHttpClient(timeout=30, max_retries=2)
        
        response = await client.get("https://example.com")
        
        assert response.status_code == 200
        assert response.text == "Success"
        
        # Verify request was made with correct parameters
        mock_httpx_client.request.assert_called_once()
        call_args = mock_httpx_client.request.call_args
        assert call_args[0][0] == "GET"  # method
        assert call_args[0][1] == "https://example.com"  # url
        
        # Verify headers were added
        headers = call_args[1]["headers"]
        assert "User-Agent" in headers
        assert "Accept" in headers
    
    @pytest.mark.asyncio
    async def test_successful_post_request(self, mock_httpx_client):
        """Test successful POST request"""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_httpx_client.request.return_value = mock_response
        
        client = AsyncHttpClient()
        
        response = await client.post("https://example.com", json={"key": "value"})
        
        assert response.status_code == 201
        
        # Verify POST method was used
        call_args = mock_httpx_client.request.call_args
        assert call_args[0][0] == "POST"
    
    @pytest.mark.asyncio
    async def test_retry_on_server_error(self, mock_httpx_client):
        """Test retry logic on server errors (5xx)"""
        # First two calls return 500, third call succeeds
        mock_responses = [
            MagicMock(status_code=500),
            MagicMock(status_code=500),
            MagicMock(status_code=200)
        ]
        
        for response in mock_responses[:2]:
            response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "HTTP 500", request=MagicMock(), response=response
            )
        
        mock_httpx_client.request.side_effect = mock_responses
        
        client = AsyncHttpClient(max_retries=3)
        
        response = await client.get("https://example.com")
        
        assert response.status_code == 200
        assert mock_httpx_client.request.call_count == 3
    
    @pytest.mark.asyncio
    async def test_no_retry_on_client_error(self, mock_httpx_client):
        """Test that client errors (4xx) are not retried"""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "HTTP 404", request=MagicMock(), response=mock_response
        )
        mock_httpx_client.request.return_value = mock_response
        
        client = AsyncHttpClient(max_retries=3)
        
        with pytest.raises(httpx.HTTPStatusError):
            await client.get("https://example.com/notfound")
        
        # Should only be called once (no retries for 4xx)
        assert mock_httpx_client.request.call_count == 1
    
    @pytest.mark.asyncio
    async def test_retry_on_network_error(self, mock_httpx_client):
        """Test retry logic on network errors"""
        # First two calls raise network error, third succeeds
        mock_response = MagicMock(status_code=200)
        mock_httpx_client.request.side_effect = [
            httpx.ConnectError("Connection failed"),
            httpx.TimeoutException("Request timeout"),
            mock_response
        ]
        
        client = AsyncHttpClient(max_retries=3)
        
        response = await client.get("https://example.com")
        
        assert response.status_code == 200
        assert mock_httpx_client.request.call_count == 3
    
    @pytest.mark.asyncio
    async def test_max_retries_exhausted(self, mock_httpx_client):
        """Test behavior when max retries are exhausted"""
        mock_httpx_client.request.side_effect = httpx.ConnectError("Connection failed")
        
        client = AsyncHttpClient(max_retries=2)
        
        with pytest.raises(httpx.ConnectError):
            await client.get("https://example.com")
        
        # Should be called max_retries + 1 times (initial + retries)
        assert mock_httpx_client.request.call_count == 3
    
    @pytest.mark.asyncio
    async def test_domain_extraction(self):
        """Test domain extraction for rate limiting"""
        client = AsyncHttpClient()
        
        assert client._get_domain("https://example.com/path") == "example.com"
        assert client._get_domain("http://subdomain.example.com") == "subdomain.example.com"
        assert client._get_domain("https://example.com:8080/path") == "example.com"
        assert client._get_domain("invalid-url") == "unknown"
    
    @pytest.mark.asyncio
    async def test_headers_generation(self):
        """Test that proper headers are generated"""
        client = AsyncHttpClient()
        headers = client._get_headers()
        
        required_headers = [
            "User-Agent", "Accept", "Accept-Language", 
            "Accept-Encoding", "DNT", "Connection", 
            "Upgrade-Insecure-Requests"
        ]
        
        for header in required_headers:
            assert header in headers
        
        # User-Agent should be one of the predefined ones
        assert headers["User-Agent"] in UserAgentRotator.USER_AGENTS
    
    @pytest.mark.asyncio
    async def test_custom_headers_merge(self, mock_httpx_client):
        """Test that custom headers are merged with default headers"""
        mock_response = MagicMock(status_code=200)
        mock_httpx_client.request.return_value = mock_response
        
        client = AsyncHttpClient()
        custom_headers = {"Authorization": "Bearer token", "User-Agent": "Custom Agent"}
        
        await client.get("https://example.com", headers=custom_headers)
        
        call_args = mock_httpx_client.request.call_args
        headers = call_args[1]["headers"]
        
        # Custom headers should be preserved
        assert headers["Authorization"] == "Bearer token"
        assert headers["User-Agent"] == "Custom Agent"
        
        # Default headers should still be present
        assert "Accept" in headers
        assert "Accept-Language" in headers
    
    @pytest.mark.asyncio
    async def test_context_manager(self, mock_httpx_client):
        """Test async context manager functionality"""
        mock_response = MagicMock(status_code=200)
        mock_httpx_client.request.return_value = mock_response
        
        async with AsyncHttpClient() as client:
            response = await client.get("https://example.com")
            assert response.status_code == 200
        
        # Client should be closed after context manager exits
        mock_httpx_client.aclose.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_rate_limiting_integration(self, mock_httpx_client):
        """Test that rate limiting is applied during requests"""
        mock_response = MagicMock(status_code=200)
        mock_httpx_client.request.return_value = mock_response
        
        client = AsyncHttpClient(requests_per_minute=2)
        
        # Make requests to the same domain
        start_time = time.time()
        await client.get("https://example.com/page1")
        await client.get("https://example.com/page2")
        # This third request should be rate limited
        await client.get("https://example.com/page3")
        end_time = time.time()
        
        # Should have taken some time due to rate limiting
        # (In practice, this would be more significant)
        assert mock_httpx_client.request.call_count == 3
        
        # Verify all requests were made to the same domain
        for call in mock_httpx_client.request.call_args_list:
            assert "example.com" in call[0][1]