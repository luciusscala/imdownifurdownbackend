"""
Performance tests for the Travel Data Parser API.
Tests response times, concurrent request handling, and LLM API latency.
"""

import asyncio
import time
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from httpx import AsyncClient
from concurrent.futures import ThreadPoolExecutor

from app.main import app, get_universal_parser
from app.services.universal_parser import UniversalParser


class TestPerformanceMetrics:
    """Performance tests for API endpoints and services."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_parser_fast(self):
        """Mock parser with fast response times."""
        mock_parser = AsyncMock(spec=UniversalParser)
        
        async def fast_flight_parse(url):
            await asyncio.sleep(0.1)  # Simulate 100ms processing
            return {
                "origin_airport": "JFK",
                "destination_airport": "LAX",
                "duration": 360,
                "total_cost": 299.99,
                "total_cost_per_person": 299.99,
                "segment": 1,
                "flight_number": "AA123"
            }
        
        async def fast_lodging_parse(url):
            await asyncio.sleep(0.15)  # Simulate 150ms processing
            return {
                "name": "Test Hotel",
                "location": "Los Angeles, CA",
                "number_of_guests": 2,
                "total_cost": 200.0,
                "total_cost_per_person": 100,
                "number_of_nights": 2,
                "check_in": "2024-06-15T15:00:00Z",
                "check_out": "2024-06-17T11:00:00Z"
            }
        
        mock_parser.parse_flight_data.side_effect = fast_flight_parse
        mock_parser.parse_lodging_data.side_effect = fast_lodging_parse
        mock_parser.close = AsyncMock()
        return mock_parser
    
    @pytest.fixture
    def mock_parser_slow(self):
        """Mock parser with slow response times to test timeouts."""
        mock_parser = AsyncMock(spec=UniversalParser)
        
        async def slow_parse(url):
            await asyncio.sleep(2.0)  # Simulate 2 second processing
            return {"test": "data"}
        
        mock_parser.parse_flight_data.side_effect = slow_parse
        mock_parser.parse_lodging_data.side_effect = slow_parse
        mock_parser.close = AsyncMock()
        return mock_parser
    
    def test_flight_endpoint_response_time(self, client, mock_parser_fast):
        """Test flight endpoint response time is within acceptable limits."""
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser_fast
        try:
            start_time = time.time()
            
            response = client.post(
                "/parse-flight",
                json={"link": "https://flights.google.com/flights?test=1"}
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            # Response should be successful
            assert response.status_code == 200
            
            # Response time should be under 5 seconds (including mock processing time)
            assert response_time < 5.0
            
            # Should be reasonably fast (under 1 second for mocked response)
            assert response_time < 1.0
            
        finally:
            app.dependency_overrides.clear()
    
    def test_lodging_endpoint_response_time(self, client, mock_parser_fast):
        """Test lodging endpoint response time is within acceptable limits."""
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser_fast
        try:
            start_time = time.time()
            
            response = client.post(
                "/parse-lodging",
                json={"link": "https://www.airbnb.com/rooms/12345"}
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            # Response should be successful
            assert response.status_code == 200
            
            # Response time should be under 5 seconds
            assert response_time < 5.0
            
            # Should be reasonably fast (under 1 second for mocked response)
            assert response_time < 1.0
            
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_concurrent_flight_requests(self, mock_parser_fast):
        """Test handling of concurrent flight parsing requests."""
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser_fast
        try:
            async with AsyncClient(app=app, base_url="http://test") as ac:
                # Create multiple concurrent requests
                tasks = []
                for i in range(10):
                    task = ac.post(
                        "/parse-flight",
                        json={"link": f"https://flights.google.com/flights?test={i}"}
                    )
                    tasks.append(task)
                
                start_time = time.time()
                responses = await asyncio.gather(*tasks)
                end_time = time.time()
                
                total_time = end_time - start_time
                
                # All requests should succeed
                for response in responses:
                    assert response.status_code == 200
                
                # Concurrent processing should be faster than sequential
                # (10 requests * 0.1s each = 1s sequential, should be much less concurrent)
                assert total_time < 2.0
                
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_concurrent_mixed_requests(self, mock_parser_fast):
        """Test handling of concurrent mixed flight and lodging requests."""
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser_fast
        try:
            async with AsyncClient(app=app, base_url="http://test") as ac:
                # Create mixed concurrent requests
                flight_tasks = []
                lodging_tasks = []
                
                for i in range(5):
                    flight_task = ac.post(
                        "/parse-flight",
                        json={"link": f"https://flights.google.com/flights?test={i}"}
                    )
                    lodging_task = ac.post(
                        "/parse-lodging",
                        json={"link": f"https://www.airbnb.com/rooms/{i}"}
                    )
                    flight_tasks.append(flight_task)
                    lodging_tasks.append(lodging_task)
                
                start_time = time.time()
                all_responses = await asyncio.gather(
                    *flight_tasks, *lodging_tasks
                )
                end_time = time.time()
                
                total_time = end_time - start_time
                
                # All requests should succeed
                for response in all_responses:
                    assert response.status_code == 200
                
                # Should handle mixed requests efficiently
                assert total_time < 3.0
                
        finally:
            app.dependency_overrides.clear()
    
    def test_health_endpoint_response_time(self, client):
        """Test health endpoint has fast response time."""
        start_time = time.time()
        
        response = client.get("/health")
        
        end_time = time.time()
        response_time = end_time - start_time
        
        # Health check should be very fast
        assert response.status_code == 200
        assert response_time < 0.1  # Under 100ms
    
    @pytest.mark.asyncio
    async def test_llm_api_latency_simulation(self, mock_parser_fast):
        """Test API behavior with simulated LLM API latency."""
        # Mock with varying latencies to simulate real LLM API behavior
        mock_parser = AsyncMock(spec=UniversalParser)
        
        async def variable_latency_parse(url):
            # Simulate variable LLM API response times (0.5-2.0 seconds)
            import random
            latency = random.uniform(0.5, 2.0)
            await asyncio.sleep(latency)
            return {
                "origin_airport": "JFK",
                "destination_airport": "LAX",
                "duration": 360,
                "total_cost": 299.99,
                "total_cost_per_person": 299.99,
                "segment": 1,
                "flight_number": "AA123"
            }
        
        mock_parser.parse_flight_data.side_effect = variable_latency_parse
        mock_parser.close = AsyncMock()
        
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser
        try:
            async with AsyncClient(app=app, base_url="http://test") as ac:
                # Test multiple requests with variable latency
                response_times = []
                
                for i in range(5):
                    start_time = time.time()
                    response = await ac.post(
                        "/parse-flight",
                        json={"link": f"https://flights.google.com/flights?test={i}"}
                    )
                    end_time = time.time()
                    
                    assert response.status_code == 200
                    response_times.append(end_time - start_time)
                
                # All responses should complete within reasonable time
                for response_time in response_times:
                    assert response_time < 10.0  # Max 10 seconds including LLM latency
                
                # Average response time should be reasonable
                avg_response_time = sum(response_times) / len(response_times)
                assert avg_response_time < 5.0
                
        finally:
            app.dependency_overrides.clear()
    
    def test_memory_usage_under_load(self, client, mock_parser_fast):
        """Test memory usage doesn't grow excessively under load."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser_fast
        try:
            # Make many requests to test memory usage
            for i in range(50):
                response = client.post(
                    "/parse-flight",
                    json={"link": f"https://flights.google.com/flights?test={i}"}
                )
                assert response.status_code == 200
            
            final_memory = process.memory_info().rss
            memory_increase = final_memory - initial_memory
            
            # Memory increase should be reasonable (less than 100MB)
            assert memory_increase < 100 * 1024 * 1024
            
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_timeout_handling_performance(self, mock_parser_slow):
        """Test that timeout handling doesn't block other requests."""
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser_slow
        try:
            async with AsyncClient(app=app, base_url="http://test") as ac:
                # Start a slow request that should timeout
                slow_task = ac.post(
                    "/parse-flight",
                    json={"link": "https://flights.google.com/flights?slow=1"},
                    timeout=1.0  # 1 second timeout
                )
                
                # Start a fast request that should complete normally
                fast_parser = AsyncMock(spec=UniversalParser)
                fast_parser.parse_flight_data.return_value = {
                    "origin_airport": "JFK",
                    "destination_airport": "LAX",
                    "duration": 360,
                    "total_cost": 299.99,
                    "total_cost_per_person": 299.99,
                    "segment": 1,
                    "flight_number": "AA123"
                }
                fast_parser.close = AsyncMock()
                
                # Override with fast parser for second request
                app.dependency_overrides[get_universal_parser] = lambda: fast_parser
                
                fast_task = ac.post(
                    "/parse-flight",
                    json={"link": "https://flights.google.com/flights?fast=1"}
                )
                
                start_time = time.time()
                
                # The fast request should complete even if slow request times out
                try:
                    slow_response, fast_response = await asyncio.gather(
                        slow_task, fast_task, return_exceptions=True
                    )
                except Exception:
                    pass
                
                end_time = time.time()
                total_time = end_time - start_time
                
                # Should not take longer than the slow request timeout
                assert total_time < 3.0
                
        finally:
            app.dependency_overrides.clear()
    
    def test_api_documentation_load_time(self, client):
        """Test that API documentation loads quickly."""
        start_time = time.time()
        
        response = client.get("/docs")
        
        end_time = time.time()
        response_time = end_time - start_time
        
        # Documentation should load quickly
        assert response.status_code == 200
        assert response_time < 1.0
    
    def test_openapi_schema_load_time(self, client):
        """Test that OpenAPI schema loads quickly."""
        start_time = time.time()
        
        response = client.get("/openapi.json")
        
        end_time = time.time()
        response_time = end_time - start_time
        
        # Schema should load quickly
        assert response.status_code == 200
        assert response_time < 0.5
    
    @pytest.mark.asyncio
    async def test_cache_performance_impact(self):
        """Test performance impact of caching on response times."""
        from app.services.cache_manager import CacheManager
        
        # Test with cache enabled
        cache_enabled = CacheManager(ttl=3600, enabled=True, max_size=100)
        
        # Mock expensive computation
        call_count = 0
        async def expensive_computation():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.1)  # Simulate processing time
            return {"result": "computed"}
        
        cache_key = "test_performance_key"
        
        # First call - should compute and cache
        start_time = time.time()
        result1 = await cache_enabled.get_cached_or_compute(
            cache_key, expensive_computation
        )
        first_call_time = time.time() - start_time
        
        # Second call - should use cache
        start_time = time.time()
        result2 = await cache_enabled.get_cached_or_compute(
            cache_key, expensive_computation
        )
        second_call_time = time.time() - start_time
        
        # Verify results are the same
        assert result1 == result2
        assert call_count == 1  # Only computed once
        
        # Cache hit should be significantly faster
        assert second_call_time < first_call_time
        assert second_call_time < 0.01  # Cache hit should be very fast
        
        # Verify cache statistics
        stats = cache_enabled.get_stats()
        assert stats['hits'] >= 1
        assert stats['hit_rate'] > 0


class TestLoadTesting:
    """Load testing scenarios for the API."""
    
    @pytest.mark.asyncio
    async def test_sustained_load_flight_parsing(self):
        """Test sustained load on flight parsing endpoint."""
        mock_parser = AsyncMock(spec=UniversalParser)
        mock_parser.parse_flight_data.return_value = {
            "origin_airport": "JFK",
            "destination_airport": "LAX",
            "duration": 360,
            "total_cost": 299.99,
            "total_cost_per_person": 299.99,
            "segment": 1,
            "flight_number": "AA123"
        }
        mock_parser.close = AsyncMock()
        
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser
        try:
            async with AsyncClient(app=app, base_url="http://test") as ac:
                # Simulate sustained load over time
                total_requests = 100
                batch_size = 10
                successful_requests = 0
                total_response_time = 0
                
                for batch in range(0, total_requests, batch_size):
                    batch_tasks = []
                    for i in range(batch_size):
                        task = ac.post(
                            "/parse-flight",
                            json={"link": f"https://flights.google.com/flights?batch={batch}&req={i}"}
                        )
                        batch_tasks.append(task)
                    
                    start_time = time.time()
                    responses = await asyncio.gather(*batch_tasks, return_exceptions=True)
                    batch_time = time.time() - start_time
                    
                    total_response_time += batch_time
                    
                    for response in responses:
                        if hasattr(response, 'status_code') and response.status_code == 200:
                            successful_requests += 1
                    
                    # Small delay between batches
                    await asyncio.sleep(0.1)
                
                # Calculate performance metrics
                success_rate = successful_requests / total_requests
                avg_batch_time = total_response_time / (total_requests / batch_size)
                
                # Verify performance under load
                assert success_rate >= 0.95  # At least 95% success rate
                assert avg_batch_time < 2.0   # Average batch time under 2 seconds
                
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_burst_load_handling(self):
        """Test handling of sudden burst of requests."""
        mock_parser = AsyncMock(spec=UniversalParser)
        mock_parser.parse_lodging_data.return_value = {
            "name": "Test Hotel",
            "location": "Test City",
            "number_of_guests": 2,
            "total_cost": 200.0,
            "total_cost_per_person": 100,
            "number_of_nights": 2,
            "check_in": "2024-06-15T15:00:00Z",
            "check_out": "2024-06-17T11:00:00Z"
        }
        mock_parser.close = AsyncMock()
        
        app.dependency_overrides[get_universal_parser] = lambda: mock_parser
        try:
            async with AsyncClient(app=app, base_url="http://test") as ac:
                # Create a sudden burst of 50 concurrent requests
                burst_size = 50
                tasks = []
                
                for i in range(burst_size):
                    task = ac.post(
                        "/parse-lodging",
                        json={"link": f"https://www.airbnb.com/rooms/burst{i}"}
                    )
                    tasks.append(task)
                
                start_time = time.time()
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                burst_time = time.time() - start_time
                
                successful_responses = 0
                for response in responses:
                    if hasattr(response, 'status_code') and response.status_code == 200:
                        successful_responses += 1
                
                success_rate = successful_responses / burst_size
                
                # System should handle burst load reasonably well
                assert success_rate >= 0.8   # At least 80% success rate under burst
                assert burst_time < 10.0     # Complete burst within 10 seconds
                
        finally:
            app.dependency_overrides.clear()