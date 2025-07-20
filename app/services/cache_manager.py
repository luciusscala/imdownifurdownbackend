"""
Cache Manager service for TTL-based caching of LLM responses to reduce API costs.
"""

import asyncio
import hashlib
import json
import logging
import time
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta


class CacheManager:
    """
    TTL-based cache manager for LLM responses to optimize API costs.
    
    This cache stores LLM extraction results with configurable TTL to avoid
    repeated expensive API calls for the same content.
    """
    
    def __init__(self, ttl: int = 3600, enabled: bool = True, max_size: int = 1000):
        """
        Initialize the Cache Manager.
        
        Args:
            ttl: Time-to-live in seconds (default: 1 hour)
            enabled: Whether caching is enabled
            max_size: Maximum number of cache entries
        """
        self.ttl = ttl
        self.enabled = enabled
        self.max_size = max_size
        self.logger = logging.getLogger(__name__)
        
        # Cache storage: {cache_key: (data, timestamp, access_count)}
        self._cache: Dict[str, Tuple[Dict[str, Any], float, int]] = {}
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
        
        # Statistics
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'cleanups': 0
        }
        
        self.logger.info(f"CacheManager initialized: TTL={ttl}s, enabled={enabled}, max_size={max_size}")
    
    def generate_cache_key(self, url: str, text_content: str, data_type: str) -> str:
        """
        Generate a unique cache key based on URL and extracted text content.
        
        Args:
            url: Original URL that was scraped
            text_content: Extracted text content from the page
            data_type: Type of data being extracted ('flight' or 'lodging')
            
        Returns:
            Unique cache key string
        """
        # Create a composite string for hashing
        composite = f"{data_type}:{url}:{text_content}"
        
        # Generate SHA-256 hash for consistent key generation
        cache_key = hashlib.sha256(composite.encode('utf-8')).hexdigest()
        
        self.logger.debug(f"Generated cache key: {cache_key[:16]}... for {data_type} data from {url}")
        return cache_key
    
    async def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve data from cache if available and not expired.
        
        Args:
            cache_key: Cache key to lookup
            
        Returns:
            Cached data if available and valid, None otherwise
        """
        if not self.enabled:
            return None
        
        async with self._lock:
            if cache_key not in self._cache:
                self._stats['misses'] += 1
                self.logger.debug(f"Cache miss for key: {cache_key[:16]}...")
                return None
            
            data, timestamp, access_count = self._cache[cache_key]
            current_time = time.time()
            
            # Check if cache entry has expired
            if current_time - timestamp > self.ttl:
                self.logger.debug(f"Cache entry expired for key: {cache_key[:16]}...")
                del self._cache[cache_key]
                self._stats['misses'] += 1
                return None
            
            # Update access count and return data
            self._cache[cache_key] = (data, timestamp, access_count + 1)
            self._stats['hits'] += 1
            
            self.logger.info(f"Cache hit for key: {cache_key[:16]}... (age: {int(current_time - timestamp)}s)")
            return data.copy()  # Return a copy to prevent external modifications
    
    async def set(self, cache_key: str, data: Dict[str, Any]) -> None:
        """
        Store data in cache with current timestamp.
        
        Args:
            cache_key: Cache key to store under
            data: Data to cache
        """
        if not self.enabled:
            return
        
        async with self._lock:
            current_time = time.time()
            
            # Check if we need to evict entries due to size limit
            if len(self._cache) >= self.max_size and cache_key not in self._cache:
                await self._evict_lru()
            
            # Store data with timestamp and initial access count
            self._cache[cache_key] = (data.copy(), current_time, 1)
            
            self.logger.info(f"Cached data for key: {cache_key[:16]}... (size: {len(self._cache)})")
    
    async def invalidate(self, cache_key: str) -> bool:
        """
        Invalidate a specific cache entry.
        
        Args:
            cache_key: Cache key to invalidate
            
        Returns:
            True if entry was found and removed, False otherwise
        """
        if not self.enabled:
            return False
        
        async with self._lock:
            if cache_key in self._cache:
                del self._cache[cache_key]
                self.logger.info(f"Invalidated cache entry: {cache_key[:16]}...")
                return True
            return False
    
    async def cleanup_expired(self) -> int:
        """
        Remove all expired cache entries.
        
        Returns:
            Number of entries removed
        """
        if not self.enabled:
            return 0
        
        async with self._lock:
            current_time = time.time()
            expired_keys = []
            
            for cache_key, (data, timestamp, access_count) in self._cache.items():
                if current_time - timestamp > self.ttl:
                    expired_keys.append(cache_key)
            
            for key in expired_keys:
                del self._cache[key]
            
            removed_count = len(expired_keys)
            if removed_count > 0:
                self._stats['cleanups'] += 1
                self.logger.info(f"Cleaned up {removed_count} expired cache entries")
            
            return removed_count
    
    async def clear(self) -> int:
        """
        Clear all cache entries.
        
        Returns:
            Number of entries removed
        """
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self.logger.info(f"Cleared all cache entries ({count} removed)")
            return count
    
    async def _evict_lru(self) -> None:
        """
        Evict least recently used cache entry to make space.
        """
        if not self._cache:
            return
        
        # Find the entry with the oldest timestamp and lowest access count
        lru_key = min(
            self._cache.keys(),
            key=lambda k: (self._cache[k][2], self._cache[k][1])  # Sort by access_count, then timestamp
        )
        
        del self._cache[lru_key]
        self._stats['evictions'] += 1
        self.logger.debug(f"Evicted LRU cache entry: {lru_key[:16]}...")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary containing cache statistics
        """
        hit_rate = 0.0
        total_requests = self._stats['hits'] + self._stats['misses']
        if total_requests > 0:
            hit_rate = self._stats['hits'] / total_requests
        
        return {
            'enabled': self.enabled,
            'ttl': self.ttl,
            'max_size': self.max_size,
            'current_size': len(self._cache),
            'hits': self._stats['hits'],
            'misses': self._stats['misses'],
            'hit_rate': round(hit_rate, 3),
            'evictions': self._stats['evictions'],
            'cleanups': self._stats['cleanups']
        }
    
    def get_cache_info(self) -> Dict[str, Any]:
        """
        Get detailed cache information including entry details.
        
        Returns:
            Dictionary containing detailed cache information
        """
        current_time = time.time()
        entries = []
        
        for cache_key, (data, timestamp, access_count) in self._cache.items():
            age = int(current_time - timestamp)
            expires_in = max(0, self.ttl - age)
            
            entries.append({
                'key': cache_key[:16] + '...',
                'age_seconds': age,
                'expires_in_seconds': expires_in,
                'access_count': access_count,
                'data_size': len(str(data))
            })
        
        # Sort by age (newest first)
        entries.sort(key=lambda x: x['age_seconds'])
        
        return {
            'stats': self.get_stats(),
            'entries': entries
        }
    
    async def get_cached_or_compute(
        self, 
        cache_key: str, 
        compute_func, 
        *args, 
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get data from cache or compute it using the provided function.
        
        This is a convenience method that implements the cache-first lookup pattern.
        
        Args:
            cache_key: Cache key to lookup
            compute_func: Async function to call if cache miss
            *args: Arguments to pass to compute_func
            **kwargs: Keyword arguments to pass to compute_func
            
        Returns:
            Cached or computed data
        """
        # Try to get from cache first
        cached_data = await self.get(cache_key)
        if cached_data is not None:
            return cached_data
        
        # Cache miss - compute the data
        computed_data = await compute_func(*args, **kwargs)
        
        # Store in cache for future use
        await self.set(cache_key, computed_data)
        
        return computed_data