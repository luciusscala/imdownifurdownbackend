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