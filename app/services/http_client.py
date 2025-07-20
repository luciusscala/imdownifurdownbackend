"""
Async HTTP client with rate limiting, retry logic, and user-agent rotation
for web scraping travel booking sites.
"""

import asyncio
import random
import time
from collections import defaultdict
from typing import Dict, List, Optional
import httpx
import logging

logger = logging.getLogger(__name__)


class UserAgentRotator:
    """Rotates User-Agent headers to avoid detection"""
    
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0"
    ]
    
    def get_random_user_agent(self) -> str:
        """Get a random User-Agent string"""
        return random.choice(self.USER_AGENTS)


class RateLimiter:
    """Rate limiter to prevent IP blocking from external sites"""
    
    def __init__(self, requests_per_minute: int = 30):
        self.requests_per_minute = requests_per_minute
        self.request_times: Dict[str, List[float]] = defaultdict(list)
        self._lock = asyncio.Lock()
    
    async def acquire(self, domain: str) -> None:
        """Acquire rate limit permission for a domain"""
        async with self._lock:
            current_time = time.time()
            domain_requests = self.request_times[domain]
            
            # Remove requests older than 1 minute
            cutoff_time = current_time - 60
            self.request_times[domain] = [
                req_time for req_time in domain_requests 
                if req_time > cutoff_time
            ]
            
            # Check if we're at the rate limit
            if len(self.request_times[domain]) >= self.requests_per_minute:
                # Calculate wait time until oldest request expires
                oldest_request = min(self.request_times[domain])
                wait_time = 60 - (current_time - oldest_request)
                
                if wait_time > 0:
                    logger.info(f"Rate limit reached for {domain}, waiting {wait_time:.2f} seconds")
                    await asyncio.sleep(wait_time)
            
            # Record this request
            self.request_times[domain].append(current_time)


class AsyncHttpClient:
    """
    Async HTTP client with rate limiting, retry logic, and user-agent rotation
    for scraping travel booking sites.
    """
    
    def __init__(
        self,
        timeout: int = 60,
        max_retries: int = 3,
        requests_per_minute: int = 30
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.user_agent_rotator = UserAgentRotator()
        self.rate_limiter = RateLimiter(requests_per_minute)
        
        # Configure httpx client
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            follow_redirects=True,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
        )
    
    def _get_domain(self, url: str) -> str:
        """Extract domain from URL for rate limiting"""
        try:
            parsed = httpx.URL(url)
            return parsed.host or "unknown"
        except Exception:
            return "unknown"
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers with rotated User-Agent"""
        return {
            "User-Agent": self.user_agent_rotator.get_random_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
    
    async def _make_request_with_retry(
        self, 
        method: str, 
        url: str, 
        **kwargs
    ) -> httpx.Response:
        """Make HTTP request with exponential backoff retry logic"""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                # Apply rate limiting
                domain = self._get_domain(url)
                await self.rate_limiter.acquire(domain)
                
                # Add headers if not provided
                if "headers" not in kwargs:
                    kwargs["headers"] = self._get_headers()
                else:
                    # Merge with default headers, keeping user-provided ones
                    default_headers = self._get_headers()
                    default_headers.update(kwargs["headers"])
                    kwargs["headers"] = default_headers
                
                logger.debug(f"Making {method} request to {url} (attempt {attempt + 1})")
                
                response = await self.client.request(method, url, **kwargs)
                
                # Check for successful response
                if response.status_code < 400:
                    logger.debug(f"Successful {method} request to {url}")
                    return response
                
                # Handle client errors (4xx) - don't retry
                if 400 <= response.status_code < 500:
                    logger.warning(f"Client error {response.status_code} for {url}")
                    response.raise_for_status()
                
                # Handle server errors (5xx) - retry
                logger.warning(f"Server error {response.status_code} for {url}, attempt {attempt + 1}")
                last_exception = httpx.HTTPStatusError(
                    f"HTTP {response.status_code}", 
                    request=response.request, 
                    response=response
                )
                
            except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError) as e:
                logger.warning(f"Network error for {url}, attempt {attempt + 1}: {e}")
                last_exception = e
            
            except httpx.HTTPStatusError as e:
                # Don't retry client errors
                if 400 <= e.response.status_code < 500:
                    raise e
                logger.warning(f"HTTP error for {url}, attempt {attempt + 1}: {e}")
                last_exception = e
            
            # Calculate exponential backoff delay
            if attempt < self.max_retries:
                delay = (2 ** attempt) + random.uniform(0, 1)
                logger.info(f"Retrying {url} in {delay:.2f} seconds")
                await asyncio.sleep(delay)
        
        # All retries exhausted
        logger.error(f"All retries exhausted for {url}")
        if last_exception:
            raise last_exception
        else:
            raise httpx.RequestError(f"Failed to complete request to {url}")
    
    async def get(self, url: str, **kwargs) -> httpx.Response:
        """Make async GET request with retry logic and rate limiting"""
        return await self._make_request_with_retry("GET", url, **kwargs)
    
    async def post(self, url: str, **kwargs) -> httpx.Response:
        """Make async POST request with retry logic and rate limiting"""
        return await self._make_request_with_retry("POST", url, **kwargs)
    
    async def close(self) -> None:
        """Close the HTTP client"""
        await self.client.aclose()
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()