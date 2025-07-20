"""
Unit tests for CacheManager service.
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, patch

from app.services.cache_manager import CacheManager


class TestCacheManager:
    """Test cases for CacheManager functionality."""
    
    @pytest.fixture
    def cache_manager(self):
        """Create a CacheManager instance for testing."""
        return CacheManager(ttl=1, enabled=True, max_size=3)
    
    @pytest.fixture
    def disabled_cache_manager(self):
        """Create a disabled CacheManager instance for testing."""
        return CacheManager(ttl=1, enabled=False, max_size=3)
    
    def test_cache_manager_initialization(self):
        """Test CacheManager initialization with different parameters."""
        # Test default initialization
        cache = CacheManager()
        assert cache.ttl == 3600
        assert cache.enabled is True
        assert cache.max_size == 1000
        
        # Test custom initialization
        cache = CacheManager(ttl=300, enabled=False, max_size=100)
        assert cache.ttl == 300
        assert cache.enabled is False
        assert cache.max_size == 100
    
    def test_generate_cache_key(self, cache_manager):
        """Test cache key generation."""
        url = "https://example.com/flight"
        text_content = "Flight from NYC to LAX"
        data_type = "flight"
        
        # Generate cache key
        cache_key = cache_manager.generate_cache_key(url, text_content, data_type)
        
        # Verify key is a string and has expected length (SHA-256 hex)
        assert isinstance(cache_key, str)
        assert len(cache_key) == 64
        
        # Verify same inputs produce same key
        cache_key2 = cache_manager.generate_cache_key(url, text_content, data_type)
        assert cache_key == cache_key2
        
        # Verify different inputs produce different keys
        cache_key3 = cache_manager.generate_cache_key(url, text_content, "lodging")
        assert cache_key != cache_key3
    
    @pytest.mark.asyncio
    async def test_cache_set_and_get(self, cache_manager):
        """Test basic cache set and get operations."""
        cache_key = "test_key"
        test_data = {"origin": "NYC", "destination": "LAX"}
        
        # Initially, cache should be empty
        result = await cache_manager.get(cache_key)
        assert result is None
        
        # Set data in cache
        await cache_manager.set(cache_key, test_data)
        
        # Retrieve data from cache
        result = await cache_manager.get(cache_key)
        assert result == test_data
        assert result is not test_data  # Should be a copy
    
    @pytest.mark.asyncio
    async def test_cache_miss_statistics(self, cache_manager):
        """Test cache miss statistics."""
        initial_stats = cache_manager.get_stats()
        assert initial_stats['misses'] == 0
        
        # Cache miss
        result = await cache_manager.get("nonexistent_key")
        assert result is None
        
        stats = cache_manager.get_stats()
        assert stats['misses'] == 1
        assert stats['hits'] == 0
    
    @pytest.mark.asyncio
    async def test_cache_hit_statistics(self, cache_manager):
        """Test cache hit statistics."""
        cache_key = "test_key"
        test_data = {"test": "data"}
        
        # Set data
        await cache_manager.set(cache_key, test_data)
        
        initial_stats = cache_manager.get_stats()
        initial_hits = initial_stats['hits']
        
        # Cache hit
        result = await cache_manager.get(cache_key)
        assert result == test_data
        
        stats = cache_manager.get_stats()
        assert stats['hits'] == initial_hits + 1
    
    @pytest.mark.asyncio
    async def test_cache_ttl_expiration(self, cache_manager):
        """Test cache TTL expiration."""
        cache_key = "test_key"
        test_data = {"test": "data"}
        
        # Set data in cache
        await cache_manager.set(cache_key, test_data)
        
        # Immediately retrieve - should be available
        result = await cache_manager.get(cache_key)
        assert result == test_data
        
        # Wait for TTL to expire (cache_manager has TTL=1 second)
        await asyncio.sleep(1.1)
        
        # Should be expired now
        result = await cache_manager.get(cache_key)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_cache_invalidation(self, cache_manager):
        """Test manual cache invalidation."""
        cache_key = "test_key"
        test_data = {"test": "data"}
        
        # Set data in cache
        await cache_manager.set(cache_key, test_data)
        
        # Verify data is cached
        result = await cache_manager.get(cache_key)
        assert result == test_data
        
        # Invalidate cache entry
        invalidated = await cache_manager.invalidate(cache_key)
        assert invalidated is True
        
        # Should no longer be in cache
        result = await cache_manager.get(cache_key)
        assert result is None
        
        # Invalidating non-existent key should return False
        invalidated = await cache_manager.invalidate("nonexistent_key")
        assert invalidated is False
    
    @pytest.mark.asyncio
    async def test_cache_cleanup_expired(self, cache_manager):
        """Test cleanup of expired cache entries."""
        # Add multiple entries
        await cache_manager.set("key1", {"data": 1})
        await cache_manager.set("key2", {"data": 2})
        
        # Verify entries are cached
        initial_count = len(cache_manager._cache)
        assert initial_count == 2
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        
        # Add one more entry (should not be expired)
        await cache_manager.set("key3", {"data": 3})
        
        # Cleanup expired entries
        removed_count = await cache_manager.cleanup_expired()
        assert removed_count == initial_count  # First entries should be expired
        assert len(cache_manager._cache) == 1  # Only key3 should remain
        
        # Verify key3 is still accessible
        result = await cache_manager.get("key3")
        assert result == {"data": 3}
    
    @pytest.mark.asyncio
    async def test_cache_clear(self, cache_manager):
        """Test clearing all cache entries."""
        # Add multiple entries
        await cache_manager.set("key1", {"data": 1})
        await cache_manager.set("key2", {"data": 2})
        await cache_manager.set("key3", {"data": 3})
        
        # Verify entries are cached
        assert len(cache_manager._cache) == 3
        
        # Clear all entries
        removed_count = await cache_manager.clear()
        assert removed_count == 3
        assert len(cache_manager._cache) == 0
        
        # Verify no entries are accessible
        result = await cache_manager.get("key1")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_cache_max_size_eviction(self, cache_manager):
        """Test LRU eviction when max size is reached."""
        # Fill cache to max size (3)
        await cache_manager.set("key1", {"data": 1})
        await cache_manager.set("key2", {"data": 2})
        await cache_manager.set("key3", {"data": 3})
        
        assert len(cache_manager._cache) == 3
        
        # Access key1 to make it more recently used
        await cache_manager.get("key1")
        
        # Add another entry - should evict least recently used (key2)
        await cache_manager.set("key4", {"data": 4})
        
        assert len(cache_manager._cache) == 3
        
        # key2 should be evicted (least recently used)
        result = await cache_manager.get("key2")
        assert result is None
        
        # Other keys should still be available
        assert await cache_manager.get("key1") == {"data": 1}
        assert await cache_manager.get("key3") == {"data": 3}
        assert await cache_manager.get("key4") == {"data": 4}
        
        # Check eviction statistics
        stats = cache_manager.get_stats()
        assert stats['evictions'] >= 1
    
    @pytest.mark.asyncio
    async def test_disabled_cache_operations(self, disabled_cache_manager):
        """Test that disabled cache doesn't perform operations."""
        cache_key = "test_key"
        test_data = {"test": "data"}
        
        # Set operation should do nothing
        await disabled_cache_manager.set(cache_key, test_data)
        
        # Get operation should return None
        result = await disabled_cache_manager.get(cache_key)
        assert result is None
        
        # Invalidate should return False
        invalidated = await disabled_cache_manager.invalidate(cache_key)
        assert invalidated is False
        
        # Cleanup should return 0
        removed_count = await disabled_cache_manager.cleanup_expired()
        assert removed_count == 0
        
        # Stats should show cache is disabled
        stats = disabled_cache_manager.get_stats()
        assert stats['enabled'] is False
    
    def test_cache_statistics(self, cache_manager):
        """Test cache statistics reporting."""
        stats = cache_manager.get_stats()
        
        # Check all expected fields are present
        expected_fields = [
            'enabled', 'ttl', 'max_size', 'current_size',
            'hits', 'misses', 'hit_rate', 'evictions', 'cleanups'
        ]
        for field in expected_fields:
            assert field in stats
        
        # Check initial values
        assert stats['enabled'] is True
        assert stats['ttl'] == 1
        assert stats['max_size'] == 3
        assert stats['current_size'] == 0
        assert stats['hits'] == 0
        assert stats['misses'] == 0
        assert stats['hit_rate'] == 0.0
    
    @pytest.mark.asyncio
    async def test_cache_info_detailed(self, cache_manager):
        """Test detailed cache information."""
        # Add some entries
        await cache_manager.set("key1", {"data": 1})
        await cache_manager.set("key2", {"data": 2})
        
        # Get detailed info
        info = cache_manager.get_cache_info()
        
        # Check structure
        assert 'stats' in info
        assert 'entries' in info
        
        # Check entries information
        entries = info['entries']
        assert len(entries) == 2
        
        for entry in entries:
            assert 'key' in entry
            assert 'age_seconds' in entry
            assert 'expires_in_seconds' in entry
            assert 'access_count' in entry
            assert 'data_size' in entry
    
    @pytest.mark.asyncio
    async def test_get_cached_or_compute(self, cache_manager):
        """Test the convenience method for cache-first lookup."""
        cache_key = "test_key"
        expected_result = {"computed": "data"}
        
        # Mock compute function
        compute_func = AsyncMock(return_value=expected_result)
        
        # First call should compute and cache
        result = await cache_manager.get_cached_or_compute(
            cache_key, compute_func, "arg1", kwarg1="value1"
        )
        
        assert result == expected_result
        compute_func.assert_called_once_with("arg1", kwarg1="value1")
        
        # Reset mock
        compute_func.reset_mock()
        
        # Second call should use cache
        result = await cache_manager.get_cached_or_compute(
            cache_key, compute_func, "arg1", kwarg1="value1"
        )
        
        assert result == expected_result
        compute_func.assert_not_called()  # Should not be called due to cache hit
    
    @pytest.mark.asyncio
    async def test_cache_access_count_tracking(self, cache_manager):
        """Test that access count is properly tracked."""
        cache_key = "test_key"
        test_data = {"test": "data"}
        
        # Set data
        await cache_manager.set(cache_key, test_data)
        
        # Access multiple times
        await cache_manager.get(cache_key)
        await cache_manager.get(cache_key)
        await cache_manager.get(cache_key)
        
        # Check that access count is tracked in cache info
        info = cache_manager.get_cache_info()
        entry = info['entries'][0]
        assert entry['access_count'] >= 3  # Initial set counts as 1, plus 3 gets
    
    @pytest.mark.asyncio
    async def test_cache_key_generation_consistency(self, cache_manager):
        """Test that cache key generation is consistent and deterministic."""
        url = "https://booking.com/hotel/123"
        text_content = "Hotel ABC in New York, $200/night"
        data_type = "lodging"
        
        # Generate multiple keys with same input
        keys = []
        for _ in range(5):
            key = cache_manager.generate_cache_key(url, text_content, data_type)
            keys.append(key)
        
        # All keys should be identical
        assert all(key == keys[0] for key in keys)
        
        # Different content should produce different keys
        different_key = cache_manager.generate_cache_key(
            url, "Different hotel content", data_type
        )
        assert different_key != keys[0]
    
    @pytest.mark.asyncio
    async def test_cache_thread_safety(self, cache_manager):
        """Test cache operations under concurrent access."""
        async def set_and_get_data(key_suffix):
            cache_key = f"test_key_{key_suffix}"
            test_data = {"data": key_suffix}
            
            await cache_manager.set(cache_key, test_data)
            result = await cache_manager.get(cache_key)
            return result
        
        # Run multiple concurrent operations
        tasks = [set_and_get_data(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        
        # Verify all operations completed successfully
        for i, result in enumerate(results):
            assert result == {"data": i}
    
    def test_cache_hit_rate_calculation(self, cache_manager):
        """Test hit rate calculation in statistics."""
        # Initially no requests
        stats = cache_manager.get_stats()
        assert stats['hit_rate'] == 0.0
        
        # Simulate some hits and misses manually
        cache_manager._stats['hits'] = 7
        cache_manager._stats['misses'] = 3
        
        stats = cache_manager.get_stats()
        assert stats['hit_rate'] == 0.7  # 7/(7+3) = 0.7


class TestCacheManagerIntegration:
    """Integration tests for CacheManager with other components."""
    
    @pytest.mark.asyncio
    async def test_cache_with_real_data_structures(self):
        """Test cache with realistic flight and lodging data structures."""
        cache = CacheManager(ttl=60, enabled=True, max_size=100)
        
        # Test with flight data structure
        flight_data = {
            "origin_airport": "JFK",
            "destination_airport": "LAX",
            "duration": 360,
            "total_cost": 299.99,
            "total_cost_per_person": 299.99,
            "segment": 1,
            "flight_number": "AA123"
        }
        
        flight_key = cache.generate_cache_key(
            "https://flights.google.com/search",
            "Flight from JFK to LAX",
            "flight"
        )
        
        await cache.set(flight_key, flight_data)
        cached_flight = await cache.get(flight_key)
        assert cached_flight == flight_data
        
        # Test with lodging data structure
        from datetime import datetime
        lodging_data = {
            "name": "Hotel ABC",
            "location": "New York, NY",
            "number_of_guests": 2,
            "total_cost": 200.0,
            "total_cost_per_person": 100,
            "number_of_nights": 3,
            "check_in": datetime(2024, 6, 1),
            "check_out": datetime(2024, 6, 4)
        }
        
        lodging_key = cache.generate_cache_key(
            "https://booking.com/hotel/123",
            "Hotel ABC in New York",
            "lodging"
        )
        
        await cache.set(lodging_key, lodging_data)
        cached_lodging = await cache.get(lodging_key)
        assert cached_lodging == lodging_data
    
    @pytest.mark.asyncio
    async def test_cache_cost_optimization_scenario(self):
        """Test cache behavior in cost optimization scenarios."""
        cache = CacheManager(ttl=3600, enabled=True, max_size=1000)
        
        # Simulate expensive LLM API calls being cached
        expensive_computation_calls = 0
        
        async def expensive_llm_call(text_content):
            nonlocal expensive_computation_calls
            expensive_computation_calls += 1
            # Simulate processing time
            await asyncio.sleep(0.01)
            return {"extracted": "data", "cost": 0.01}
        
        url = "https://example.com/booking"
        text_content = "Sample booking page content"
        cache_key = cache.generate_cache_key(url, text_content, "flight")
        
        # First call - should compute
        result1 = await cache.get_cached_or_compute(
            cache_key, expensive_llm_call, text_content
        )
        assert expensive_computation_calls == 1
        
        # Second call - should use cache
        result2 = await cache.get_cached_or_compute(
            cache_key, expensive_llm_call, text_content
        )
        assert expensive_computation_calls == 1  # No additional calls
        assert result1 == result2
        
        # Verify cost savings
        stats = cache.get_stats()
        assert stats['hits'] >= 1
        assert stats['hit_rate'] > 0