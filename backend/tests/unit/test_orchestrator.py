"""
Unit Tests for Validation Orchestrator and Confidence Calculations

This module provides comprehensive unit tests for the validation orchestrator,
confidence aggregation logic, and worker coordination.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone
from typing import Dict, Any, List

# Import orchestrator components
from backend.services.validator import ValidationOrchestrator, ValidationWorker, ValidationResult
from backend.services.validation_report_generator import ValidationReportGenerator
from backend.utils.rate_limiter import RateLimiter
from backend.utils.idempotency import IdempotencyManager
from backend.utils.csv_processor import CSVProcessor
from backend.auth.audit_logger import AuditAction

class TestValidationOrchestrator:
    """Test Validation Orchestrator with mocked dependencies"""
    
    @pytest.fixture
    def orchestrator(self):
        """Create validation orchestrator instance for testing"""
        with patch('redis.Redis') as mock_redis:
            mock_redis_client = Mock()
            mock_redis.return_value = mock_redis_client
            
            return ValidationOrchestrator(
                database_url="sqlite:///:memory:",
                redis_client=mock_redis_client
            )
    
    @pytest.fixture
    def mock_provider_data(self):
        """Mock provider data for validation"""
        return {
            "provider_id": "PROV001",
            "npi_number": "1234567890",
            "given_name": "John",
            "family_name": "Smith",
            "phone_primary": "+1-555-123-4567",
            "email": "john.smith@example.com",
            "address_street": "123 Main St",
            "address_city": "San Francisco",
            "address_state": "CA",
            "address_zip": "94102",
            "license_number": "A12345",
            "license_state": "CA"
        }
    
    @pytest.fixture
    def mock_worker_results(self):
        """Mock worker validation results"""
        return {
            "npi": ValidationResult(
                source="npi",
                confidence=0.9,
                is_valid=True,
                normalized_data={
                    "npi_number": "1234567890",
                    "given_name": "JOHN",
                    "family_name": "SMITH",
                    "primary_taxonomy": "Family Medicine"
                },
                metadata={"verified": True}
            ),
            "google_places": ValidationResult(
                source="google_places",
                confidence=0.85,
                is_valid=True,
                normalized_data={
                    "place_id": "ChIJd8BlQ2BZwokRAFQEcDlJRAI",
                    "formatted_address": "123 Main St, San Francisco, CA 94102, USA",
                    "latitude": 37.7749,
                    "longitude": -122.4194
                },
                metadata={"distance_meters": 10}
            ),
            "state_board": ValidationResult(
                source="state_board",
                confidence=0.95,
                is_valid=True,
                normalized_data={
                    "license_number": "A12345",
                    "license_status": "ACTIVE",
                    "license_state": "CA"
                },
                metadata={"disciplinary_actions": []}
            ),
            "email": ValidationResult(
                source="internal",
                confidence=0.8,
                is_valid=True,
                normalized_data={
                    "email": "john.smith@example.com"
                },
                metadata={"mx_record_found": True}
            ),
            "phone": ValidationResult(
                source="internal",
                confidence=0.75,
                is_valid=True,
                normalized_data={
                    "phone_primary": "+15551234567"
                },
                metadata={"normalized": True}
            )
        }
    
    @pytest.mark.asyncio
    async def test_validate_single_provider_success(self, orchestrator, mock_provider_data, mock_worker_results):
        """Test successful validation of single provider"""
        with patch.object(orchestrator, '_run_validation_workers') as mock_workers:
            mock_workers.return_value = mock_worker_results
            
            result = await orchestrator.validate_single_provider(mock_provider_data)
            
            assert result is not None
            assert result.provider_id == "PROV001"
            assert result.overall_confidence > 0.8
            assert result.validation_status == "valid"
            assert len(result.field_confidence) > 0
            assert len(result.flags) == 0
    
    @pytest.mark.asyncio
    async def test_validate_single_provider_with_warnings(self, orchestrator, mock_provider_data):
        """Test validation with warnings"""
        # Mock worker results with some low confidence scores
        warning_worker_results = {
            "npi": ValidationResult(
                source="npi",
                confidence=0.9,
                is_valid=True,
                normalized_data={"npi_number": "1234567890"},
                metadata={}
            ),
            "google_places": ValidationResult(
                source="google_places",
                confidence=0.6,  # Low confidence
                is_valid=True,
                normalized_data={"place_id": "test"},
                metadata={}
            ),
            "state_board": ValidationResult(
                source="state_board",
                confidence=0.95,
                is_valid=True,
                normalized_data={"license_status": "ACTIVE"},
                metadata={}
            ),
            "email": ValidationResult(
                source="internal",
                confidence=0.4,  # Low confidence
                is_valid=False,
                normalized_data={"email": "invalid@nonexistent.com"},
                metadata={}
            ),
            "phone": ValidationResult(
                source="internal",
                confidence=0.75,
                is_valid=True,
                normalized_data={"phone_primary": "+15551234567"},
                metadata={}
            )
        }
        
        with patch.object(orchestrator, '_run_validation_workers') as mock_workers:
            mock_workers.return_value = warning_worker_results
            
            result = await orchestrator.validate_single_provider(mock_provider_data)
            
            assert result is not None
            assert result.validation_status == "warning"
            assert "LOW_CONFIDENCE_EMAIL" in result.flags
            assert "LOW_CONFIDENCE_ADDRESS" in result.flags
            assert result.overall_confidence < 0.8
    
    @pytest.mark.asyncio
    async def test_validate_single_provider_invalid(self, orchestrator, mock_provider_data):
        """Test validation with invalid results"""
        # Mock worker results with invalid data
        invalid_worker_results = {
            "npi": ValidationResult(
                source="npi",
                confidence=0.3,  # Very low confidence
                is_valid=False,
                normalized_data={"npi_number": "1234567890"},
                metadata={"error": "NPI not found"}
            ),
            "google_places": ValidationResult(
                source="google_places",
                confidence=0.2,  # Very low confidence
                is_valid=False,
                normalized_data={},
                metadata={"error": "Address not found"}
            ),
            "state_board": ValidationResult(
                source="state_board",
                confidence=0.1,  # Very low confidence
                is_valid=False,
                normalized_data={},
                metadata={"error": "License not found"}
            ),
            "email": ValidationResult(
                source="internal",
                confidence=0.0,
                is_valid=False,
                normalized_data={},
                metadata={"error": "Invalid email"}
            ),
            "phone": ValidationResult(
                source="internal",
                confidence=0.0,
                is_valid=False,
                normalized_data={},
                metadata={"error": "Invalid phone"}
            )
        }
        
        with patch.object(orchestrator, '_run_validation_workers') as mock_workers:
            mock_workers.return_value = invalid_worker_results
            
            result = await orchestrator.validate_single_provider(mock_provider_data)
            
            assert result is not None
            assert result.validation_status == "invalid"
            assert "INVALID_NPI" in result.flags
            assert "INVALID_ADDRESS" in result.flags
            assert "INVALID_LICENSE" in result.flags
            assert result.overall_confidence < 0.5
    
    @pytest.mark.asyncio
    async def test_batch_validation_success(self, orchestrator, mock_provider_data):
        """Test successful batch validation"""
        batch_data = [mock_provider_data.copy() for _ in range(3)]
        
        with patch.object(orchestrator, 'validate_single_provider') as mock_validate:
            # Mock successful validation for all providers
            mock_result = Mock()
            mock_result.provider_id = "PROV001"
            mock_result.overall_confidence = 0.9
            mock_result.validation_status = "valid"
            mock_validate.return_value = mock_result
            
            job_id = await orchestrator.start_batch_validation(batch_data)
            
            assert job_id is not None
            assert len(job_id) > 0
    
    @pytest.mark.asyncio
    async def test_confidence_aggregation_weights(self, orchestrator, mock_worker_results):
        """Test confidence aggregation with proper weights"""
        # Test the confidence weighting formula
        # NPI(0.4), Google Places(0.25), State Board(0.15), Internal(0.2)
        
        aggregated = orchestrator._aggregate_confidence_scores(mock_worker_results)
        
        # Calculate expected weighted average
        expected = (
            0.9 * 0.4 +    # NPI
            0.85 * 0.25 +  # Google Places
            0.95 * 0.15 +  # State Board
            (0.8 + 0.75) / 2 * 0.2  # Internal (email + phone average)
        )
        
        assert abs(aggregated - expected) < 0.01
        assert aggregated > 0.85
    
    @pytest.mark.asyncio
    async def test_field_confidence_calculation(self, orchestrator, mock_worker_results):
        """Test individual field confidence calculation"""
        field_confidence = orchestrator._calculate_field_confidence(mock_worker_results)
        
        assert "npi_number" in field_confidence
        assert "address" in field_confidence
        assert "license" in field_confidence
        assert "email" in field_confidence
        assert "phone" in field_confidence
        
        # NPI should have high confidence
        assert field_confidence["npi_number"] > 0.8
        
        # Address should have high confidence
        assert field_confidence["address"] > 0.8
        
        # License should have high confidence
        assert field_confidence["license"] > 0.9
    
    @pytest.mark.asyncio
    async def test_flag_generation(self, orchestrator, mock_worker_results):
        """Test flag generation based on validation results"""
        # Test with mixed results
        mixed_results = mock_worker_results.copy()
        mixed_results["email"] = ValidationResult(
            source="internal",
            confidence=0.3,  # Low confidence
            is_valid=False,
            normalized_data={"email": "invalid@example.com"},
            metadata={}
        )
        
        flags = orchestrator._generate_flags(mixed_results)
        
        assert "LOW_CONFIDENCE_EMAIL" in flags
        assert "INVALID_EMAIL" in flags
    
    @pytest.mark.asyncio
    async def test_worker_coordination(self, orchestrator, mock_provider_data):
        """Test coordination of multiple validation workers"""
        with patch.object(orchestrator, '_run_npi_validation') as mock_npi:
            with patch.object(orchestrator, '_run_address_validation') as mock_address:
                with patch.object(orchestrator, '_run_license_validation') as mock_license:
                    with patch.object(orchestrator, '_run_email_validation') as mock_email:
                        with patch.object(orchestrator, '_run_phone_validation') as mock_phone:
                            
                            # Mock worker results
                            mock_npi.return_value = ValidationResult(
                                source="npi", confidence=0.9, is_valid=True,
                                normalized_data={}, metadata={}
                            )
                            mock_address.return_value = ValidationResult(
                                source="google_places", confidence=0.85, is_valid=True,
                                normalized_data={}, metadata={}
                            )
                            mock_license.return_value = ValidationResult(
                                source="state_board", confidence=0.95, is_valid=True,
                                normalized_data={}, metadata={}
                            )
                            mock_email.return_value = ValidationResult(
                                source="internal", confidence=0.8, is_valid=True,
                                normalized_data={}, metadata={}
                            )
                            mock_phone.return_value = ValidationResult(
                                source="internal", confidence=0.75, is_valid=True,
                                normalized_data={}, metadata={}
                            )
                            
                            results = await orchestrator._run_validation_workers(mock_provider_data)
                            
                            assert len(results) == 5
                            assert "npi" in results
                            assert "google_places" in results
                            assert "state_board" in results
                            assert "email" in results
                            assert "phone" in results
                            
                            # Verify all workers were called
                            mock_npi.assert_called_once()
                            mock_address.assert_called_once()
                            mock_license.assert_called_once()
                            mock_email.assert_called_once()
                            mock_phone.assert_called_once()

class TestValidationReportGenerator:
    """Test Validation Report Generator"""
    
    @pytest.fixture
    def report_generator(self):
        """Create validation report generator instance for testing"""
        return ValidationReportGenerator()
    
    @pytest.fixture
    def mock_validation_result(self):
        """Mock validation result for report generation"""
        return Mock(
            provider_id="PROV001",
            overall_confidence=0.85,
            validation_status="warning",
            field_confidence={
                "npi_number": 0.9,
                "address": 0.8,
                "license": 0.95,
                "email": 0.6,
                "phone": 0.75
            },
            flags=["LOW_CONFIDENCE_EMAIL"],
            created_at=datetime.now(timezone.utc)
        )
    
    def test_generate_validation_report(self, report_generator, mock_validation_result):
        """Test validation report generation"""
        report = report_generator.generate_report(mock_validation_result)
        
        assert report is not None
        assert report.provider_id == "PROV001"
        assert report.overall_confidence == 0.85
        assert report.validation_status == "warning"
        assert len(report.field_analysis) > 0
        assert len(report.insights) > 0
        assert len(report.flags) > 0
    
    def test_field_analysis_generation(self, report_generator, mock_validation_result):
        """Test field analysis generation"""
        analysis = report_generator._generate_field_analysis(mock_validation_result)
        
        assert "npi_number" in analysis
        assert "address" in analysis
        assert "license" in analysis
        assert "email" in analysis
        assert "phone" in analysis
        
        # Check analysis structure
        npi_analysis = analysis["npi_number"]
        assert "confidence" in npi_analysis
        assert "status" in npi_analysis
        assert "sources" in npi_analysis
    
    def test_insights_generation(self, report_generator, mock_validation_result):
        """Test insights generation"""
        insights = report_generator._generate_insights(mock_validation_result)
        
        assert len(insights) > 0
        
        # Should include insights about low confidence fields
        insight_text = " ".join(insights)
        assert "email" in insight_text.lower()
    
    def test_recommendations_generation(self, report_generator, mock_validation_result):
        """Test recommendations generation"""
        recommendations = report_generator._generate_recommendations(mock_validation_result)
        
        assert len(recommendations) > 0
        
        # Should include recommendations for flagged fields
        recommendation_text = " ".join(recommendations)
        assert "email" in recommendation_text.lower()

class TestRateLimiter:
    """Test Rate Limiter"""
    
    @pytest.fixture
    def rate_limiter(self):
        """Create rate limiter instance for testing"""
        with patch('redis.Redis') as mock_redis:
            mock_redis_client = Mock()
            mock_redis.return_value = mock_redis_client
            
            return RateLimiter(mock_redis_client)
    
    @pytest.mark.asyncio
    async def test_rate_limit_check_under_limit(self, rate_limiter):
        """Test rate limit check when under limit"""
        with patch.object(rate_limiter.redis, 'incr') as mock_incr:
            with patch.object(rate_limiter.redis, 'expire') as mock_expire:
                mock_incr.return_value = 5  # Under limit
                
                result = await rate_limiter.check_rate_limit("test_key", 10, 60)
                
                assert result.allowed is True
                assert result.remaining == 5
                assert result.reset_time is not None
    
    @pytest.mark.asyncio
    async def test_rate_limit_check_over_limit(self, rate_limiter):
        """Test rate limit check when over limit"""
        with patch.object(rate_limiter.redis, 'incr') as mock_incr:
            with patch.object(rate_limiter.redis, 'expire') as mock_expire:
                mock_incr.return_value = 15  # Over limit
                
                result = await rate_limiter.check_rate_limit("test_key", 10, 60)
                
                assert result.allowed is False
                assert result.remaining == 0
                assert result.reset_time is not None

class TestIdempotencyManager:
    """Test Idempotency Manager"""
    
    @pytest.fixture
    def idempotency_manager(self):
        """Create idempotency manager instance for testing"""
        with patch('redis.Redis') as mock_redis:
            mock_redis_client = Mock()
            mock_redis.return_value = mock_redis_client
            
            return IdempotencyManager(mock_redis_client)
    
    def test_generate_idempotency_key(self, idempotency_manager):
        """Test idempotency key generation"""
        data = {"provider_id": "PROV001", "action": "validate"}
        
        key1 = idempotency_manager.generate_key(data)
        key2 = idempotency_manager.generate_key(data)
        
        # Same data should generate same key
        assert key1 == key2
        
        # Different data should generate different key
        data2 = {"provider_id": "PROV002", "action": "validate"}
        key3 = idempotency_manager.generate_key(data2)
        assert key1 != key3
    
    @pytest.mark.asyncio
    async def test_check_idempotency_new_request(self, idempotency_manager):
        """Test idempotency check for new request"""
        with patch.object(idempotency_manager.redis, 'get') as mock_get:
            mock_get.return_value = None  # No existing key
            
            result = await idempotency_manager.check_idempotency("test_key")
            
            assert result.is_duplicate is False
            assert result.cached_response is None
    
    @pytest.mark.asyncio
    async def test_check_idempotency_duplicate_request(self, idempotency_manager):
        """Test idempotency check for duplicate request"""
        cached_response = {"status": "completed", "result": "test"}
        
        with patch.object(idempotency_manager.redis, 'get') as mock_get:
            mock_get.return_value = json.dumps(cached_response)
            
            result = await idempotency_manager.check_idempotency("test_key")
            
            assert result.is_duplicate is True
            assert result.cached_response == cached_response

class TestCSVProcessor:
    """Test CSV Processor"""
    
    @pytest.fixture
    def csv_processor(self):
        """Create CSV processor instance for testing"""
        return CSVProcessor()
    
    def test_parse_csv_valid_format(self, csv_processor):
        """Test parsing valid CSV format"""
        csv_content = """provider_id,npi_number,given_name,family_name,phone_primary,email
PROV001,1234567890,John,Smith,+1-555-123-4567,john.smith@example.com
PROV002,0987654321,Jane,Doe,+1-555-987-6543,jane.doe@example.com"""
        
        result = csv_processor.parse_csv(csv_content)
        
        assert result.success is True
        assert len(result.providers) == 2
        assert result.providers[0]["provider_id"] == "PROV001"
        assert result.providers[1]["provider_id"] == "PROV002"
    
    def test_parse_csv_invalid_format(self, csv_processor):
        """Test parsing invalid CSV format"""
        csv_content = """invalid,csv,format
missing,required,fields"""
        
        result = csv_processor.parse_csv(csv_content)
        
        assert result.success is False
        assert len(result.errors) > 0
    
    def test_validate_provider_data(self, csv_processor):
        """Test provider data validation"""
        valid_provider = {
            "provider_id": "PROV001",
            "npi_number": "1234567890",
            "given_name": "John",
            "family_name": "Smith",
            "phone_primary": "+1-555-123-4567",
            "email": "john.smith@example.com"
        }
        
        invalid_provider = {
            "provider_id": "PROV002",
            "npi_number": "invalid",  # Invalid NPI
            "given_name": "",  # Empty name
            "family_name": "Doe",
            "phone_primary": "invalid",  # Invalid phone
            "email": "invalid-email"  # Invalid email
        }
        
        valid_result = csv_processor.validate_provider_data(valid_provider)
        invalid_result = csv_processor.validate_provider_data(invalid_provider)
        
        assert valid_result.is_valid is True
        assert len(valid_result.errors) == 0
        
        assert invalid_result.is_valid is False
        assert len(invalid_result.errors) > 0

# Performance test fixtures
@pytest.fixture
def performance_test_data():
    """Generate test data for performance testing"""
    providers = []
    for i in range(100):
        providers.append({
            "provider_id": f"PROV{i:03d}",
            "npi_number": f"{1000000000 + i}",
            "given_name": f"Provider{i}",
            "family_name": "Test",
            "phone_primary": f"+1-555-{i:03d}-{i:04d}",
            "email": f"provider{i}@example.com",
            "address_street": f"{100 + i} Test St",
            "address_city": "Test City",
            "address_state": "CA",
            "address_zip": f"{90000 + i}",
            "license_number": f"LIC{i:05d}",
            "license_state": "CA"
        })
    return providers

class TestPerformanceValidation:
    """Test performance of validation operations"""
    
    @pytest.fixture
    def performance_orchestrator(self):
        """Create orchestrator for performance testing"""
        with patch('redis.Redis') as mock_redis:
            mock_redis_client = Mock()
            mock_redis.return_value = mock_redis_client
            
            return ValidationOrchestrator(
                database_url="sqlite:///:memory:",
                redis_client=mock_redis_client
            )
    
    @pytest.mark.asyncio
    async def test_parallel_validation_performance(self, performance_orchestrator, performance_test_data):
        """Test parallel validation performance"""
        # Mock all external API calls for performance testing
        with patch.object(performance_orchestrator, '_run_validation_workers') as mock_workers:
            # Mock fast validation results
            mock_workers.return_value = {
                "npi": ValidationResult(
                    source="npi", confidence=0.9, is_valid=True,
                    normalized_data={}, metadata={}
                ),
                "google_places": ValidationResult(
                    source="google_places", confidence=0.85, is_valid=True,
                    normalized_data={}, metadata={}
                ),
                "state_board": ValidationResult(
                    source="state_board", confidence=0.95, is_valid=True,
                    normalized_data={}, metadata={}
                ),
                "email": ValidationResult(
                    source="internal", confidence=0.8, is_valid=True,
                    normalized_data={}, metadata={}
                ),
                "phone": ValidationResult(
                    source="internal", confidence=0.75, is_valid=True,
                    normalized_data={}, metadata={}
                )
            }
            
            start_time = datetime.now()
            
            # Validate 100 providers in parallel
            tasks = []
            for provider in performance_test_data:
                tasks.append(performance_orchestrator.validate_single_provider(provider))
            
            results = await asyncio.gather(*tasks)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Should complete in under 5 minutes (300 seconds)
            assert duration < 300
            assert len(results) == 100
            
            # All results should be successful
            for result in results:
                assert result is not None
                assert result.overall_confidence > 0.8

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
