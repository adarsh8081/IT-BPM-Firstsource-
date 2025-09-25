"""
Performance Tests for Provider Validation

This module provides performance tests to ensure the validation system can
process 100 providers in under 5 minutes using parallel workers and mock connectors.
"""

import pytest
import asyncio
import time
from datetime import datetime, timezone
from typing import List, Dict, Any
from unittest.mock import patch, Mock, AsyncMock

# Import performance testing components
from backend.services.validator import ValidationOrchestrator
from backend.workers.queue_manager import QueueManager
from backend.utils.rate_limiter import RateLimiter
from backend.connectors.npi import NPIConnector
from backend.connectors.google_places import GooglePlacesConnector
from backend.connectors.state_board_mock import StateBoardMockConnector

class TestValidationPerformance:
    """Performance tests for validation operations"""
    
    @pytest.fixture
    def performance_test_providers(self) -> List[Dict[str, Any]]:
        """Generate 100 test providers for performance testing"""
        providers = []
        for i in range(100):
            providers.append({
                "provider_id": f"PERF_PROV_{i:03d}",
                "npi_number": f"{1000000000 + i}",
                "given_name": f"Provider{i}",
                "family_name": "Test",
                "phone_primary": f"+1-555-{i:03d}-{i:04d}",
                "email": f"provider{i}@example.com",
                "address_street": f"{100 + i} Performance St",
                "address_city": "Test City",
                "address_state": "CA",
                "address_zip": f"{90000 + i}",
                "license_number": f"PERF{i:05d}",
                "license_state": "CA"
            })
        return providers
    
    @pytest.fixture
    def mock_fast_responses(self):
        """Mock fast responses for performance testing"""
        return {
            "npi_response": {
                "result_count": 1,
                "results": [
                    {
                        "number": "1234567890",
                        "basic": {
                            "first_name": "PROVIDER",
                            "last_name": "TEST",
                            "credential": "MD"
                        },
                        "addresses": [
                            {
                                "address_1": "123 PERFORMANCE ST",
                                "city": "TEST CITY",
                                "state": "CA",
                                "postal_code": "90000",
                                "telephone_number": "555-123-4567"
                            }
                        ],
                        "taxonomies": [
                            {
                                "code": "207Q00000X",
                                "desc": "Family Medicine",
                                "primary": True,
                                "license": "PERF12345"
                            }
                        ]
                    }
                ]
            },
            "google_places_response": {
                "results": [
                    {
                        "formatted_address": "123 Performance St, Test City, CA 90000, USA",
                        "geometry": {
                            "location": {"lat": 37.7749, "lng": -122.4194}
                        },
                        "place_id": "ChIJd8BlQ2BZwokRAFQEcDlJRAI"
                    }
                ],
                "status": "OK"
            },
            "state_board_response": {
                "license_number": "PERF12345",
                "license_status": "ACTIVE",
                "provider_name": "PROVIDER TEST"
            }
        }
    
    @pytest.fixture
    async def performance_orchestrator(self, mock_fast_responses):
        """Create orchestrator with fast mock responses"""
        with patch('redis.Redis') as mock_redis:
            mock_redis_client = Mock()
            mock_redis.return_value = mock_redis_client
            
            orchestrator = ValidationOrchestrator(
                database_url="sqlite:///:memory:",
                redis_client=mock_redis_client
            )
            
            # Mock all external API calls with fast responses
            with patch('httpx.AsyncClient.get') as mock_get:
                def fast_api_response(url, **kwargs):
                    mock_response = Mock()
                    mock_response.status_code = 200
                    
                    if "npiregistry.cms.hhs.gov" in str(url):
                        mock_response.json.return_value = mock_fast_responses["npi_response"]
                    elif "maps.googleapis.com" in str(url):
                        mock_response.json.return_value = mock_fast_responses["google_places_response"]
                    elif "stateboard.mock" in str(url):
                        mock_response.json.return_value = mock_fast_responses["state_board_response"]
                    
                    return mock_response
                
                mock_get.side_effect = fast_api_response
                
                yield orchestrator
    
    @pytest.mark.asyncio
    async def test_parallel_validation_performance(
        self, 
        performance_orchestrator, 
        performance_test_providers,
        mock_fast_responses
    ):
        """Test that 100 providers can be validated in under 5 minutes"""
        
        # Record start time
        start_time = time.time()
        
        # Validate 100 providers in parallel
        validation_tasks = []
        for provider in performance_test_providers:
            task = performance_orchestrator.validate_single_provider(provider)
            validation_tasks.append(task)
        
        # Execute all validations in parallel
        results = await asyncio.gather(*validation_tasks, return_exceptions=True)
        
        # Record end time
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Performance assertions
        assert total_duration < 300, f"Validation took {total_duration:.2f} seconds, expected < 300 seconds (5 minutes)"
        
        # Verify all validations completed successfully
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) == 100, f"Expected 100 successful validations, got {len(successful_results)}"
        
        # Verify result quality
        for result in successful_results:
            assert result.overall_confidence > 0.8, f"Low confidence: {result.overall_confidence}"
            assert result.validation_status in ["valid", "warning"], f"Unexpected status: {result.validation_status}"
        
        print(f"Performance Test Results:")
        print(f"- Total providers validated: 100")
        print(f"- Total time: {total_duration:.2f} seconds")
        print(f"- Average time per provider: {total_duration/100:.3f} seconds")
        print(f"- Providers per minute: {100/(total_duration/60):.1f}")
        print(f"- Success rate: {len(successful_results)/100*100:.1f}%")
    
    @pytest.mark.asyncio
    async def test_batch_validation_performance(
        self, 
        performance_orchestrator, 
        performance_test_providers
    ):
        """Test batch validation performance"""
        
        start_time = time.time()
        
        # Start batch validation
        job_id = await performance_orchestrator.start_batch_validation(performance_test_providers)
        
        # Wait for batch completion
        while True:
            job_status = await performance_orchestrator.get_job_status(job_id)
            if job_status.status == "completed":
                break
            elif job_status.status == "failed":
                pytest.fail("Batch validation failed")
            await asyncio.sleep(0.1)  # Small delay to prevent busy waiting
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Performance assertions
        assert total_duration < 300, f"Batch validation took {total_duration:.2f} seconds, expected < 300 seconds"
        
        # Get validation report
        report = await performance_orchestrator.get_validation_report(job_id)
        assert len(report.results) == 100, f"Expected 100 results, got {len(report.results)}"
        
        print(f"Batch Validation Performance:")
        print(f"- Job ID: {job_id}")
        print(f"- Total time: {total_duration:.2f} seconds")
        print(f"- Average time per provider: {total_duration/100:.3f} seconds")
    
    @pytest.mark.asyncio
    async def test_worker_scalability(self, performance_test_providers):
        """Test worker scalability with different concurrency levels"""
        
        concurrency_levels = [1, 5, 10, 20]
        results = {}
        
        for concurrency in concurrency_levels:
            print(f"Testing concurrency level: {concurrency}")
            
            with patch('redis.Redis') as mock_redis:
                mock_redis_client = Mock()
                mock_redis.return_value = mock_redis_client
                
                orchestrator = ValidationOrchestrator(
                    database_url="sqlite:///:memory:",
                    redis_client=mock_redis_client
                )
                
                # Mock fast responses
                with patch('httpx.AsyncClient.get') as mock_get:
                    mock_response = Mock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = {
                        "result_count": 1,
                        "results": [{"number": "1234567890", "basic": {"first_name": "TEST"}}]
                    }
                    mock_get.return_value = mock_response
                    
                    start_time = time.time()
                    
                    # Create semaphore for concurrency control
                    semaphore = asyncio.Semaphore(concurrency)
                    
                    async def validate_with_semaphore(provider):
                        async with semaphore:
                            return await orchestrator.validate_single_provider(provider)
                    
                    # Validate subset of providers
                    subset = performance_test_providers[:20]  # Test with 20 providers
                    tasks = [validate_with_semaphore(p) for p in subset]
                    await asyncio.gather(*tasks)
                    
                    end_time = time.time()
                    duration = end_time - start_time
                    
                    results[concurrency] = {
                        "duration": duration,
                        "providers_per_second": len(subset) / duration
                    }
        
        # Analyze scalability results
        print(f"Scalability Results:")
        for concurrency, result in results.items():
            print(f"- Concurrency {concurrency}: {result['duration']:.2f}s, {result['providers_per_second']:.2f} providers/sec")
        
        # Verify that higher concurrency generally improves performance
        assert results[10]["providers_per_second"] > results[1]["providers_per_second"], \
            "Higher concurrency should improve performance"
    
    @pytest.mark.asyncio
    async def test_memory_usage_during_validation(self, performance_orchestrator, performance_test_providers):
        """Test memory usage during large batch validation"""
        
        import psutil
        import os
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Validate providers in batches to monitor memory
        batch_size = 25
        max_memory_usage = initial_memory
        
        for i in range(0, len(performance_test_providers), batch_size):
            batch = performance_test_providers[i:i + batch_size]
            
            # Validate batch
            tasks = [performance_orchestrator.validate_single_provider(p) for p in batch]
            await asyncio.gather(*tasks)
            
            # Check memory usage
            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            max_memory_usage = max(max_memory_usage, current_memory)
            
            # Verify memory usage is reasonable (less than 1GB increase)
            memory_increase = current_memory - initial_memory
            assert memory_increase < 1000, f"Memory usage increased by {memory_increase:.1f}MB, expected < 1000MB"
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        total_memory_increase = final_memory - initial_memory
        
        print(f"Memory Usage Analysis:")
        print(f"- Initial memory: {initial_memory:.1f}MB")
        print(f"- Final memory: {final_memory:.1f}MB")
        print(f"- Maximum memory: {max_memory_usage:.1f}MB")
        print(f"- Total increase: {total_memory_increase:.1f}MB")
        
        # Verify reasonable memory usage
        assert total_memory_increase < 500, f"Memory usage increased by {total_memory_increase:.1f}MB, expected < 500MB"
    
    @pytest.mark.asyncio
    async def test_rate_limiting_performance(self):
        """Test rate limiting doesn't significantly impact performance"""
        
        with patch('redis.Redis') as mock_redis:
            mock_redis_client = Mock()
            mock_redis.return_value = mock_redis_client
            
            rate_limiter = RateLimiter(mock_redis_client)
            
            # Mock Redis responses for rate limiting
            with patch.object(rate_limiter.redis, 'incr') as mock_incr:
                with patch.object(rate_limiter.redis, 'expire') as mock_expire:
                    mock_incr.return_value = 1  # Under limit
                    
                    start_time = time.time()
                    
                    # Test rate limiting overhead
                    for i in range(1000):
                        await rate_limiter.check_rate_limit(f"test_key_{i}", 100, 60)
                    
                    end_time = time.time()
                    duration = end_time - start_time
                    
                    # Rate limiting should be very fast (under 1 second for 1000 checks)
                    assert duration < 1.0, f"Rate limiting took {duration:.3f} seconds for 1000 checks"
                    
                    print(f"Rate Limiting Performance:")
                    print(f"- 1000 checks in {duration:.3f} seconds")
                    print(f"- Average time per check: {duration/1000*1000:.3f}ms")
    
    @pytest.mark.asyncio
    async def test_concurrent_api_calls_performance(self):
        """Test performance of concurrent external API calls"""
        
        # Mock external API connectors
        npi_connector = NPIConnector("test_key")
        places_connector = GooglePlacesConnector("test_key")
        state_board_connector = StateBoardMockConnector()
        
        # Mock fast API responses
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"result_count": 1, "results": [{"number": "1234567890"}]}
            mock_get.return_value = mock_response
            
            start_time = time.time()
            
            # Make concurrent API calls
            tasks = []
            for i in range(100):
                # Mix of different API calls
                if i % 3 == 0:
                    tasks.append(npi_connector.fetch_provider_by_npi(f"123456789{i}"))
                elif i % 3 == 1:
                    tasks.append(places_connector.geocode_address(
                        street=f"{i} Test St",
                        city="Test City",
                        state="CA",
                        zip_code="90000"
                    ))
                else:
                    tasks.append(state_board_connector.verify_license(f"LIC{i:05d}", "CA"))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Verify performance
            assert duration < 10, f"Concurrent API calls took {duration:.2f} seconds, expected < 10 seconds"
            
            successful_calls = [r for r in results if not isinstance(r, Exception)]
            assert len(successful_calls) >= 90, f"Expected >= 90 successful calls, got {len(successful_calls)}"
            
            print(f"Concurrent API Calls Performance:")
            print(f"- 100 concurrent calls in {duration:.2f} seconds")
            print(f"- Average time per call: {duration/100:.3f} seconds")
            print(f"- Success rate: {len(successful_calls)/100*100:.1f}%")
    
    @pytest.mark.asyncio
    async def test_database_write_performance(self, performance_test_providers):
        """Test database write performance during validation"""
        
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import sessionmaker
        
        # Create in-memory database for testing
        engine = create_engine("sqlite:///:memory:")
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # Create test table
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE test_providers (
                    id INTEGER PRIMARY KEY,
                    provider_id TEXT,
                    validation_result TEXT,
                    created_at TIMESTAMP
                )
            """))
            conn.commit()
        
        start_time = time.time()
        
        # Simulate database writes
        session = SessionLocal()
        try:
            for i, provider in enumerate(performance_test_providers):
                # Simulate validation result
                result = {
                    "provider_id": provider["provider_id"],
                    "overall_confidence": 0.85,
                    "validation_status": "valid",
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                
                # Insert into database
                conn = session.connection()
                conn.execute(text("""
                    INSERT INTO test_providers (provider_id, validation_result, created_at)
                    VALUES (:provider_id, :result, :created_at)
                """), {
                    "provider_id": provider["provider_id"],
                    "result": str(result),
                    "created_at": datetime.now(timezone.utc)
                })
                
                # Commit every 10 records for better performance
                if (i + 1) % 10 == 0:
                    session.commit()
            
            session.commit()
        
        finally:
            session.close()
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Verify database write performance
        assert duration < 5, f"Database writes took {duration:.2f} seconds, expected < 5 seconds"
        
        # Verify all records were written
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM test_providers"))
            count = result.scalar()
            assert count == 100, f"Expected 100 records, got {count}"
        
        print(f"Database Write Performance:")
        print(f"- 100 records written in {duration:.2f} seconds")
        print(f"- Average time per write: {duration/100:.3f} seconds")
        print(f"- Writes per second: {100/duration:.1f}")

class TestPerformanceBenchmarks:
    """Performance benchmarks for different scenarios"""
    
    @pytest.mark.asyncio
    async def test_validation_throughput_benchmark(self):
        """Benchmark validation throughput under different loads"""
        
        load_scenarios = [
            {"providers": 10, "expected_time": 30},   # 10 providers in 30 seconds
            {"providers": 50, "expected_time": 120},  # 50 providers in 2 minutes
            {"providers": 100, "expected_time": 300}  # 100 providers in 5 minutes
        ]
        
        for scenario in load_scenarios:
            provider_count = scenario["providers"]
            expected_time = scenario["expected_time"]
            
            # Generate test providers
            providers = []
            for i in range(provider_count):
                providers.append({
                    "provider_id": f"BENCH_{i:03d}",
                    "npi_number": f"{1000000000 + i}",
                    "given_name": f"Provider{i}",
                    "family_name": "Benchmark",
                    "phone_primary": f"+1-555-{i:03d}-{i:04d}",
                    "email": f"provider{i}@benchmark.com",
                    "address_street": f"{100 + i} Benchmark St",
                    "address_city": "Benchmark City",
                    "address_state": "CA",
                    "address_zip": f"{90000 + i}",
                    "license_number": f"BENCH{i:05d}",
                    "license_state": "CA"
                })
            
            with patch('redis.Redis') as mock_redis:
                mock_redis_client = Mock()
                mock_redis.return_value = mock_redis_client
                
                orchestrator = ValidationOrchestrator(
                    database_url="sqlite:///:memory:",
                    redis_client=mock_redis_client
                )
                
                # Mock fast responses
                with patch('httpx.AsyncClient.get') as mock_get:
                    mock_response = Mock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = {
                        "result_count": 1,
                        "results": [{"number": "1234567890", "basic": {"first_name": "BENCHMARK"}}]
                    }
                    mock_get.return_value = mock_response
                    
                    start_time = time.time()
                    
                    # Validate providers
                    tasks = [orchestrator.validate_single_provider(p) for p in providers]
                    await asyncio.gather(*tasks)
                    
                    end_time = time.time()
                    duration = end_time - start_time
                    
                    # Verify performance meets expectations
                    assert duration < expected_time, \
                        f"Scenario {provider_count} providers: took {duration:.2f}s, expected < {expected_time}s"
                    
                    throughput = provider_count / duration
                    
                    print(f"Benchmark - {provider_count} providers:")
                    print(f"- Duration: {duration:.2f} seconds")
                    print(f"- Throughput: {throughput:.2f} providers/second")
                    print(f"- Target: {provider_count/expected_time:.2f} providers/second")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
