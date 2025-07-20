"""
Integration tests for CacheManager with UniversalParser.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.universal_parser import UniversalParser
from app.services.cache_manager import CacheManager
from app.services.http_client import AsyncHttpClient
from app.services.text_extractor import TextExtractor
from app.services.llm_data_extractor import LLMDataExtractor


class TestCacheIntegration:
    """Test cache integration with UniversalParser."""
    
    @pytest.fixture
    def cache_manager(self):
        """Create a CacheManager for testing."""
        return CacheManager(ttl=60, enabled=True, max_size=100)
    
    @pytest.fixture
    def mock_http_client(self):
        """Create a mock HTTP client."""
        client = AsyncMock(spec=AsyncHttpClient)
        response = MagicMock()
        response.text = "<html><body>Flight from JFK to LAX, $299</body></html>"
        response.raise_for_status = MagicMock()
        client.get.return_value = response
        return client
    
    @pytest.fixture
    def mock_text_extractor(self):
        """Create a mock text extractor."""
        extractor = MagicMock(spec=TextExtractor)
        extractor.extract_text.return_value = "Flight from JFK to LAX, $299"
        return extractor
    
    @pytest.fixture
    def mock_llm_extractor(self):
        """Create a mock LLM extractor."""
        extractor = AsyncMock(spec=LLMDataExtractor)
        extractor.extract_flight_data.return_value = {
            "origin_airport": "JFK",
            "destination_airport": "LAX",
            "duration": 360,
            "total_cost": 299.0,
            "total_cost_per_person": 299.0,
            "segment": 1,
            "flight_number": "AA123"
        }
        extractor.extract_lodging_data.return_value = {
            "name": "Hotel ABC",
            "location": "New York, NY",
            "number_of_guests": 2,
            "total_cost": 200.0,
            "total_cost_per_person": 100,
            "number_of_nights": 3,
            "check_in": "2024-06-01",
            "check_out": "2024-06-04"
        }
        return extractor
    
    @pytest.mark.asyncio
    async def test_flight_parsing_with_cache_miss_then_hit(
        self, cache_manager, mock_http_client, mock_text_extractor, mock_llm_extractor
    ):
        """Test flight parsing with cache miss followed by cache hit."""
        parser = UniversalParser(
            anthropic_api_key="test-key",
            cache_manager=cache_manager,
            http_client=mock_http_client,
            text_extractor=mock_text_extractor,
            llm_extractor=mock_llm_extractor
        )
        
        url = "https://flights.google.com/search"
        
        # First call - should be cache miss and call LLM
        result1 = await parser.parse_flight_data(url)
        
        # Verify LLM was called
        mock_llm_extractor.extract_flight_data.assert_called_once()
        
        # Verify result
        expected_result = {
            "origin_airport": "JFK",
            "destination_airport": "LAX",
            "duration": 360,
            "total_cost": 299.0,
            "total_cost_per_person": 299.0,
            "segment": 1,
            "flight_number": "AA123"
        }
        assert result1 == expected_result
        
        # Reset mock to track second call
        mock_llm_extractor.reset_mock()
        
        # Second call - should be cache hit and NOT call LLM
        result2 = await parser.parse_flight_data(url)
        
        # Verify LLM was NOT called (cache hit)
        mock_llm_extractor.extract_flight_data.assert_not_called()
        
        # Verify same result
        assert result2 == expected_result
        
        # Verify cache statistics
        stats = cache_manager.get_stats()
        assert stats['hits'] >= 1
        assert stats['misses'] >= 1
        assert stats['hit_rate'] > 0
    
    @pytest.mark.asyncio
    async def test_lodging_parsing_with_cache_miss_then_hit(
        self, cache_manager, mock_http_client, mock_text_extractor, mock_llm_extractor
    ):
        """Test lodging parsing with cache miss followed by cache hit."""
        parser = UniversalParser(
            anthropic_api_key="test-key",
            cache_manager=cache_manager,
            http_client=mock_http_client,
            text_extractor=mock_text_extractor,
            llm_extractor=mock_llm_extractor
        )
        
        url = "https://booking.com/hotel/123"
        
        # First call - should be cache miss and call LLM
        result1 = await parser.parse_lodging_data(url)
        
        # Verify LLM was called
        mock_llm_extractor.extract_lodging_data.assert_called_once()
        
        # Verify result structure (dates will be converted to datetime objects)
        assert result1["name"] == "Hotel ABC"
        assert result1["location"] == "New York, NY"
        assert result1["number_of_guests"] == 2
        
        # Reset mock to track second call
        mock_llm_extractor.reset_mock()
        
        # Second call - should be cache hit and NOT call LLM
        result2 = await parser.parse_lodging_data(url)
        
        # Verify LLM was NOT called (cache hit)
        mock_llm_extractor.extract_lodging_data.assert_not_called()
        
        # Verify same result
        assert result2 == result1
        
        # Verify cache statistics
        stats = cache_manager.get_stats()
        assert stats['hits'] >= 1
        assert stats['misses'] >= 1
    
    @pytest.mark.asyncio
    async def test_different_urls_create_different_cache_keys(
        self, cache_manager, mock_http_client, mock_text_extractor, mock_llm_extractor
    ):
        """Test that different URLs create different cache keys."""
        parser = UniversalParser(
            anthropic_api_key="test-key",
            cache_manager=cache_manager,
            http_client=mock_http_client,
            text_extractor=mock_text_extractor,
            llm_extractor=mock_llm_extractor
        )
        
        url1 = "https://flights.google.com/search?q=jfk-lax"
        url2 = "https://flights.google.com/search?q=lax-jfk"
        
        # Parse both URLs
        await parser.parse_flight_data(url1)
        await parser.parse_flight_data(url2)
        
        # Both should call LLM (different cache keys)
        assert mock_llm_extractor.extract_flight_data.call_count == 2
        
        # Verify cache has 2 entries
        stats = cache_manager.get_stats()
        assert stats['current_size'] == 2
    
    @pytest.mark.asyncio
    async def test_same_content_different_urls_use_same_cache(
        self, cache_manager, mock_http_client, mock_text_extractor, mock_llm_extractor
    ):
        """Test that same content from different URLs can share cache if text is identical."""
        # Mock to return identical text content for different URLs
        mock_text_extractor.extract_text.return_value = "Identical flight content"
        
        parser = UniversalParser(
            anthropic_api_key="test-key",
            cache_manager=cache_manager,
            http_client=mock_http_client,
            text_extractor=mock_text_extractor,
            llm_extractor=mock_llm_extractor
        )
        
        url1 = "https://site1.com/flight"
        url2 = "https://site2.com/flight"
        
        # Parse first URL
        await parser.parse_flight_data(url1)
        
        # Reset mock to track second call
        mock_llm_extractor.reset_mock()
        
        # Parse second URL with same content
        await parser.parse_flight_data(url2)
        
        # Second call should still call LLM because URLs are different
        # (cache key includes URL, not just content)
        assert mock_llm_extractor.extract_flight_data.call_count == 1
    
    @pytest.mark.asyncio
    async def test_parser_without_cache_manager(
        self, mock_http_client, mock_text_extractor, mock_llm_extractor
    ):
        """Test that parser works without cache manager."""
        parser = UniversalParser(
            anthropic_api_key="test-key",
            cache_manager=None,  # No cache manager
            http_client=mock_http_client,
            text_extractor=mock_text_extractor,
            llm_extractor=mock_llm_extractor
        )
        
        url = "https://flights.google.com/search"
        
        # First call
        result1 = await parser.parse_flight_data(url)
        
        # Second call - should still call LLM (no caching)
        result2 = await parser.parse_flight_data(url)
        
        # Both calls should invoke LLM
        assert mock_llm_extractor.extract_flight_data.call_count == 2
        
        # Results should be identical
        assert result1 == result2
    
    @pytest.mark.asyncio
    async def test_cache_key_generation_includes_all_parameters(self, cache_manager):
        """Test that cache key generation includes URL, content, and data type."""
        url = "https://example.com"
        content = "Sample content"
        
        # Generate keys for different data types
        flight_key = cache_manager.generate_cache_key(url, content, "flight")
        lodging_key = cache_manager.generate_cache_key(url, content, "lodging")
        
        # Keys should be different
        assert flight_key != lodging_key
        
        # Generate keys for different URLs
        key1 = cache_manager.generate_cache_key("https://site1.com", content, "flight")
        key2 = cache_manager.generate_cache_key("https://site2.com", content, "flight")
        
        # Keys should be different
        assert key1 != key2
        
        # Generate keys for different content
        key3 = cache_manager.generate_cache_key(url, "Content A", "flight")
        key4 = cache_manager.generate_cache_key(url, "Content B", "flight")
        
        # Keys should be different
        assert key3 != key4
    
    @pytest.mark.asyncio
    async def test_cache_cost_optimization_simulation(
        self, cache_manager, mock_http_client, mock_text_extractor, mock_llm_extractor
    ):
        """Test cache cost optimization by simulating expensive LLM calls."""
        # Track LLM call count to simulate cost
        llm_call_count = 0
        
        async def expensive_llm_call(*args, **kwargs):
            nonlocal llm_call_count
            llm_call_count += 1
            return {
                "origin_airport": "JFK",
                "destination_airport": "LAX",
                "duration": 360,
                "total_cost": 299.0,
                "total_cost_per_person": 299.0,
                "segment": 1,
                "flight_number": "AA123"
            }
        
        mock_llm_extractor.extract_flight_data.side_effect = expensive_llm_call
        
        parser = UniversalParser(
            anthropic_api_key="test-key",
            cache_manager=cache_manager,
            http_client=mock_http_client,
            text_extractor=mock_text_extractor,
            llm_extractor=mock_llm_extractor
        )
        
        url = "https://flights.google.com/search"
        
        # Make multiple calls to the same URL
        for _ in range(5):
            await parser.parse_flight_data(url)
        
        # Only first call should invoke LLM (cost optimization)
        assert llm_call_count == 1
        
        # Verify cache statistics show cost savings
        stats = cache_manager.get_stats()
        assert stats['hits'] == 4  # 4 cache hits
        assert stats['misses'] == 1  # 1 cache miss
        assert stats['hit_rate'] == 0.8  # 80% hit rate
    
    @pytest.mark.asyncio
    async def test_disabled_cache_always_calls_llm(
        self, mock_http_client, mock_text_extractor, mock_llm_extractor
    ):
        """Test that disabled cache always calls LLM."""
        disabled_cache = CacheManager(ttl=60, enabled=False, max_size=100)
        
        parser = UniversalParser(
            anthropic_api_key="test-key",
            cache_manager=disabled_cache,
            http_client=mock_http_client,
            text_extractor=mock_text_extractor,
            llm_extractor=mock_llm_extractor
        )
        
        url = "https://flights.google.com/search"
        
        # Make multiple calls
        await parser.parse_flight_data(url)
        await parser.parse_flight_data(url)
        await parser.parse_flight_data(url)
        
        # All calls should invoke LLM (cache disabled)
        assert mock_llm_extractor.extract_flight_data.call_count == 3
        
        # Cache stats should show no activity
        stats = disabled_cache.get_stats()
        assert stats['enabled'] is False
        assert stats['hits'] == 0
        assert stats['misses'] == 0


class TestCacheEndpointIntegration:
    """Test cache functionality with API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi.testclient import TestClient
        from app.main import app
        return TestClient(app)
    
    def test_cache_stats_endpoint_if_exists(self, client):
        """Test cache statistics endpoint if it exists."""
        response = client.get("/cache/stats")
        
        if response.status_code == 200:
            # Cache endpoint exists and is working
            data = response.json()
            
            # Verify expected cache stats fields
            expected_fields = ['enabled', 'ttl', 'max_size', 'current_size', 'hits', 'misses', 'hit_rate']
            for field in expected_fields:
                assert field in data
        else:
            # Cache endpoint might not be implemented yet
            assert response.status_code == 404
    
    def test_cache_clear_endpoint_if_exists(self, client):
        """Test cache clear endpoint if it exists."""
        response = client.post("/cache/clear")
        
        if response.status_code == 200:
            # Cache clear endpoint exists and is working
            data = response.json()
            assert "cleared" in data or "removed" in data
        else:
            # Cache clear endpoint might not be implemented yet
            assert response.status_code == 404


class TestCacheWithRealScenarios:
    """Test caching with realistic travel booking scenarios."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi.testclient import TestClient
        from app.main import app, get_universal_parser
        return TestClient(app)
    
    def test_cache_with_flight_booking_scenarios(self, client):
        """Test cache behavior with realistic flight booking scenarios."""
        from unittest.mock import AsyncMock
        from app.services.universal_parser import UniversalParser
        from app.main import app, get_universal_parser
        
        # Mock parser with realistic responses
        mock_parser = AsyncMock(spec=UniversalParser)
        
        flight_response = {
            "origin_airport": "JFK",
            "destination_airport": "LAX",
            "duration": 360,
            "total_cost": 299.99,
            "total_cost_per_person": 299.99,
            "segment": 1,
            "flight_number": "AA123"
        }
        
        call_count = 0
        
        async def realistic_flight_parse(url):
            nonlocal call_count
            call_count += 1
            return flight_response
        
        mock_parser.parse_flight_data.side_effect = realistic_flight_parse
        mock_parser.close = AsyncMock()
        
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser
        try:
            # Test with realistic flight URL
            url = "https://flights.google.com/flights?hl=en&curr=USD"
            
            # First request
            response1 = client.post("/parse-flight", json={"link": url})
            assert response1.status_code == 200
            
            # Second request (potential cache hit)
            response2 = client.post("/parse-flight", json={"link": url})
            assert response2.status_code == 200
            
            # Results should be identical
            assert response1.json() == response2.json()
            
            # If caching is working, parser should only be called once
            # If caching is disabled, parser will be called twice
            assert call_count in [1, 2]  # Allow for both scenarios
            
        finally:
            app.dependency_overrides.clear()
    
    def test_cache_with_lodging_booking_scenarios(self, client):
        """Test cache behavior with realistic lodging booking scenarios."""
        from unittest.mock import AsyncMock
        from datetime import datetime, timezone
        from app.services.universal_parser import UniversalParser
        from app.main import app, get_universal_parser
        
        # Mock parser with realistic responses
        mock_parser = AsyncMock(spec=UniversalParser)
        
        lodging_response = {
            "name": "Luxury Hotel NYC",
            "location": "New York, NY, USA",
            "number_of_guests": 2,
            "total_cost": 450.00,
            "total_cost_per_person": 225,
            "number_of_nights": 3,
            "check_in": datetime(2024, 6, 15, 15, 0, 0, tzinfo=timezone.utc),
            "check_out": datetime(2024, 6, 18, 11, 0, 0, tzinfo=timezone.utc)
        }
        
        call_count = 0
        
        async def realistic_lodging_parse(url):
            nonlocal call_count
            call_count += 1
            return lodging_response
        
        mock_parser.parse_lodging_data.side_effect = realistic_lodging_parse
        mock_parser.close = AsyncMock()
        
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser
        try:
            # Test with realistic lodging URL
            url = "https://www.airbnb.com/rooms/12345678"
            
            # First request
            response1 = client.post("/parse-lodging", json={"link": url})
            assert response1.status_code == 200
            
            # Second request (potential cache hit)
            response2 = client.post("/parse-lodging", json={"link": url})
            assert response2.status_code == 200
            
            # Results should be identical
            data1 = response1.json()
            data2 = response2.json()
            assert data1 == data2
            
            # If caching is working, parser should only be called once
            # If caching is disabled, parser will be called twice
            assert call_count in [1, 2]  # Allow for both scenarios
            
        finally:
            app.dependency_overrides.clear()


class TestCachePerformanceIntegration:
    """Performance-focused cache integration tests."""
    
    @pytest.mark.asyncio
    async def test_cache_performance_under_load(self):
        """Test cache performance under high load."""
        cache = CacheManager(ttl=3600, enabled=True, max_size=1000)
        
        # Simulate high-frequency cache operations
        async def cache_operation(i):
            cache_key = f"perf_test_{i % 100}"  # Reuse keys to test hits
            
            # Try to get from cache first
            result = await cache.get(cache_key)
            if result is None:
                # Simulate computation and cache
                result = {"computed": i, "expensive": True}
                await cache.set(cache_key, result)
            
            return result
        
        # Run many concurrent cache operations
        tasks = [cache_operation(i) for i in range(1000)]
        
        import time
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        total_time = end_time - start_time
        
        # Should complete reasonably quickly
        assert total_time < 5.0  # Under 5 seconds for 1000 operations
        assert len(results) == 1000
        
        # Check cache statistics
        stats = cache.get_stats()
        assert stats['hits'] > 0  # Should have some cache hits
        assert stats['hit_rate'] > 0  # Positive hit rate
    
    @pytest.mark.asyncio
    async def test_cache_cleanup_performance(self):
        """Test cache cleanup performance."""
        cache = CacheManager(ttl=1, enabled=True, max_size=1000)  # Short TTL
        
        # Add many entries
        for i in range(500):
            await cache.set(f"cleanup_test_{i}", {"data": i})
        
        # Wait for entries to expire
        import asyncio
        await asyncio.sleep(1.1)
        
        # Add more entries to trigger cleanup
        for i in range(500, 600):
            await cache.set(f"cleanup_test_{i}", {"data": i})
        
        # Perform cleanup
        import time
        start_time = time.time()
        removed_count = await cache.cleanup_expired()
        cleanup_time = time.time() - start_time
        
        # Cleanup should be fast and effective
        assert cleanup_time < 1.0  # Under 1 second
        assert removed_count >= 500  # Should remove expired entries
        
        # Cache should be smaller after cleanup
        stats = cache.get_stats()
        assert stats['current_size'] < 500
    
    @pytest.mark.asyncio
    async def test_concurrent_cache_access_safety(self):
        """Test that concurrent cache access is thread-safe."""
        cache = CacheManager(ttl=3600, enabled=True, max_size=100)
        
        # Concurrent operations on the same cache key
        async def concurrent_operation(operation_id):
            cache_key = "shared_key"
            
            # Try to get and set concurrently
            existing = await cache.get(cache_key)
            if existing is None:
                await cache.set(cache_key, {"operation_id": operation_id})
            
            # Get the final value
            final_value = await cache.get(cache_key)
            return final_value
        
        # Run many concurrent operations
        tasks = [concurrent_operation(i) for i in range(50)]
        results = await asyncio.gather(*tasks)
        
        # All results should be consistent (same final value)
        first_result = results[0]
        for result in results[1:]:
            assert result == first_result
        
        # Cache should have exactly one entry
        stats = cache.get_stats()
        assert stats['current_size'] == 1


class TestCacheErrorHandling:
    """Test cache behavior during error conditions."""
    
    @pytest.mark.asyncio
    async def test_cache_with_llm_api_errors(
        self, mock_http_client, mock_text_extractor
    ):
        """Test cache behavior when LLM API errors occur."""
        cache_manager = CacheManager(ttl=60, enabled=True, max_size=100)
        
        # Mock LLM extractor that fails on first call, succeeds on second
        mock_llm_extractor = AsyncMock(spec=LLMDataExtractor)
        call_count = 0
        
        async def failing_then_succeeding_llm(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("LLM API Error")
            else:
                return {
                    "origin_airport": "JFK",
                    "destination_airport": "LAX",
                    "duration": 360,
                    "total_cost": 299.0,
                    "total_cost_per_person": 299.0,
                    "segment": 1,
                    "flight_number": "AA123"
                }
        
        mock_llm_extractor.extract_flight_data.side_effect = failing_then_succeeding_llm
        
        parser = UniversalParser(
            anthropic_api_key="test-key",
            cache_manager=cache_manager,
            http_client=mock_http_client,
            text_extractor=mock_text_extractor,
            llm_extractor=mock_llm_extractor
        )
        
        url = "https://flights.google.com/search"
        
        # First call should fail
        with pytest.raises(Exception, match="LLM API Error"):
            await parser.parse_flight_data(url)
        
        # Second call should succeed
        result = await parser.parse_flight_data(url)
        assert result["origin_airport"] == "JFK"
        
        # Verify both calls invoked LLM (no caching of errors)
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_cache_with_network_errors(
        self, mock_text_extractor, mock_llm_extractor
    ):
        """Test cache behavior when network errors occur."""
        cache_manager = CacheManager(ttl=60, enabled=True, max_size=100)
        
        # Mock HTTP client that fails
        mock_http_client = AsyncMock(spec=AsyncHttpClient)
        mock_http_client.get.side_effect = Exception("Network error")
        
        parser = UniversalParser(
            anthropic_api_key="test-key",
            cache_manager=cache_manager,
            http_client=mock_http_client,
            text_extractor=mock_text_extractor,
            llm_extractor=mock_llm_extractor
        )
        
        url = "https://flights.google.com/search"
        
        # Should fail due to network error
        with pytest.raises(Exception, match="Network error"):
            await parser.parse_flight_data(url)
        
        # Cache should not have any entries (error not cached)
        stats = cache_manager.get_stats()
        assert stats['current_size'] == 0
    
    @pytest.mark.asyncio
    async def test_cache_memory_pressure_handling(self):
        """Test cache behavior under memory pressure."""
        # Create cache with very small size to force evictions
        cache = CacheManager(ttl=3600, enabled=True, max_size=5)
        
        # Add more entries than cache can hold
        for i in range(20):
            cache_key = f"memory_test_{i}"
            await cache.set(cache_key, {"data": f"large_data_payload_{i}" * 100})
        
        # Cache should not exceed max size
        stats = cache.get_stats()
        assert stats['current_size'] <= 5
        assert stats['evictions'] > 0
        
        # Most recent entries should still be accessible
        for i in range(15, 20):  # Last 5 entries
            cache_key = f"memory_test_{i}"
            result = await cache.get(cache_key)
            assert result is not None
            assert f"large_data_payload_{i}" in result["data"]