"""
Tests for Validation Orchestrator System
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
import json

from services.validator import (
    ValidationOrchestrator,
    WorkerTaskResult,
    WorkerTaskType,
    ValidationReport,
    BatchValidationRequest
)
from services.validation_report_generator import (
    ValidationReportGenerator,
    DetailedValidationReport,
    FieldAnalysis,
    ValidationInsight,
    ReportSeverity
)
from utils.rate_limiter import RateLimiter, RetryPolicy
from utils.idempotency import IdempotencyManager
from utils.csv_processor import CSVProcessor, CSVProcessingResult


class TestValidationOrchestrator:
    """Test cases for Validation Orchestrator"""

    @pytest.fixture
    def orchestrator(self):
        """Create validation orchestrator instance for testing"""
        return ValidationOrchestrator()

    @pytest.fixture
    def sample_provider_data(self):
        """Sample provider data for testing"""
        return {
            "provider_id": "12345",
            "given_name": "Dr. John Smith",
            "family_name": "Smith",
            "npi_number": "1234567890",
            "phone_primary": "(555) 123-4567",
            "email": "john.smith@example.com",
            "address_street": "123 Main Street, San Francisco, CA 94102",
            "license_number": "A123456",
            "license_state": "CA"
        }

    def test_orchestrator_initialization(self, orchestrator):
        """Test validation orchestrator initialization"""
        assert orchestrator.redis_url is not None
        assert orchestrator.npi_queue is not None
        assert orchestrator.google_places_queue is not None
        assert orchestrator.ocr_queue is not None
        assert orchestrator.state_board_queue is not None
        assert orchestrator.enrichment_queue is not None

    def test_rate_limits_configuration(self, orchestrator):
        """Test rate limits configuration"""
        rate_limits = orchestrator.rate_limits
        
        assert WorkerTaskType.NPI_CHECK in rate_limits
        assert WorkerTaskType.GOOGLE_PLACES in rate_limits
        assert WorkerTaskType.OCR_PROCESSING in rate_limits
        assert WorkerTaskType.STATE_BOARD_CHECK in rate_limits
        assert WorkerTaskType.ENRICHMENT_LOOKUP in rate_limits

    def test_retry_policy_configuration(self, orchestrator):
        """Test retry policy configuration"""
        retry_policy = orchestrator.retry_policy
        
        assert "max_retries" in retry_policy
        assert "base_delay" in retry_policy
        assert "exponential_backoff" in retry_policy
        assert "max_delay" in retry_policy

    @pytest.mark.asyncio
    async def test_validate_provider_batch(self, orchestrator, sample_provider_data):
        """Test batch provider validation"""
        with patch.object(orchestrator, '_enqueue_provider_validation') as mock_enqueue:
            mock_enqueue.return_value = None
            
            job_id = await orchestrator.validate_provider_batch(
                [sample_provider_data],
                validation_options={"enable_npi_check": True},
                idempotency_key="test_key"
            )
            
            assert job_id is not None
            assert job_id in orchestrator.active_jobs
            mock_enqueue.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_job_status(self, orchestrator):
        """Test getting job status"""
        # Mock active job
        orchestrator.active_jobs["test_job"] = {
            "job_id": "test_job",
            "status": "running",
            "provider_count": 1,
            "created_at": datetime.now(),
            "validation_options": {}
        }
        
        with patch.object(orchestrator, '_get_job_progress') as mock_progress:
            mock_progress.return_value = {"completed": 1, "failed": 0, "percentage": 100}
            
            status = await orchestrator.get_job_status("test_job")
            
            assert status["job_id"] == "test_job"
            assert status["status"] == "running"
            assert status["provider_count"] == 1

    @pytest.mark.asyncio
    async def test_get_validation_report(self, orchestrator):
        """Test getting validation report"""
        # Mock worker results
        worker_results = [
            WorkerTaskResult(
                task_type=WorkerTaskType.NPI_CHECK,
                provider_id="12345",
                success=True,
                confidence=0.9,
                normalized_fields={"npi_number": "1234567890"},
                field_confidence={"npi_number": 0.95}
            )
        ]
        
        with patch.object(orchestrator, '_get_provider_worker_results') as mock_results:
            mock_results.return_value = worker_results
            
            report = await orchestrator.get_validation_report("job_123", "provider_123")
            
            assert report is not None
            assert report.provider_id == "provider_123"
            assert report.job_id == "job_123"
            assert report.overall_confidence > 0.0

    def test_aggregate_worker_results(self, orchestrator):
        """Test worker results aggregation"""
        worker_results = [
            WorkerTaskResult(
                task_type=WorkerTaskType.NPI_CHECK,
                provider_id="12345",
                success=True,
                confidence=0.9,
                normalized_fields={"npi_number": "1234567890", "given_name": "John"},
                field_confidence={"npi_number": 0.95, "given_name": 0.90}
            ),
            WorkerTaskResult(
                task_type=WorkerTaskType.GOOGLE_PLACES,
                provider_id="12345",
                success=True,
                confidence=0.8,
                normalized_fields={"address_street": "123 Main St"},
                field_confidence={"address_street": 0.85}
            )
        ]
        
        aggregated_fields, field_confidence = orchestrator._aggregate_worker_results(worker_results)
        
        assert "npi_number" in aggregated_fields
        assert "given_name" in aggregated_fields
        assert "address_street" in aggregated_fields
        assert aggregated_fields["npi_number"] == "1234567890"
        assert field_confidence["npi_number"] > 0.0

    def test_calculate_overall_confidence(self, orchestrator):
        """Test overall confidence calculation"""
        field_confidence = {
            "npi_number": 0.95,
            "given_name": 0.90,
            "family_name": 0.90,
            "license_number": 0.85,
            "phone_primary": 0.80,
            "email": 0.75
        }
        
        overall_confidence = orchestrator._calculate_overall_confidence(field_confidence)
        
        assert overall_confidence > 0.0
        assert overall_confidence < 1.0

    def test_determine_validation_status(self, orchestrator):
        """Test validation status determination"""
        # Test valid status
        field_summaries = {
            "npi_number": MagicMock(status="valid"),
            "given_name": MagicMock(status="valid"),
            "family_name": MagicMock(status="valid")
        }
        
        status = orchestrator._determine_validation_status(field_summaries)
        assert status == "valid"
        
        # Test invalid status
        field_summaries["npi_number"] = MagicMock(status="invalid")
        
        status = orchestrator._determine_validation_status(field_summaries)
        assert status == "invalid"

    def test_generate_validation_flags(self, orchestrator):
        """Test validation flag generation"""
        worker_results = [
            WorkerTaskResult(
                task_type=WorkerTaskType.NPI_CHECK,
                provider_id="12345",
                success=False,
                confidence=0.0,
                normalized_fields={},
                field_confidence={},
                error_message="NPI not found"
            )
        ]
        
        aggregated_fields = {"given_name": "John"}
        
        flags = orchestrator._generate_validation_flags(worker_results, aggregated_fields)
        
        assert "FAILED_VALIDATIONS: 1" in flags
        assert "MISSING_NPI_NUMBER" in flags

    def test_create_field_summaries(self, orchestrator):
        """Test field summary creation"""
        worker_results = [
            WorkerTaskResult(
                task_type=WorkerTaskType.NPI_CHECK,
                provider_id="12345",
                success=True,
                confidence=0.9,
                normalized_fields={"npi_number": "1234567890"},
                field_confidence={"npi_number": 0.95}
            )
        ]
        
        summaries = orchestrator._create_field_summaries(worker_results)
        
        assert "npi_number" in summaries
        assert summaries["npi_number"]["confidence"] == 0.95
        assert summaries["npi_number"]["validation_count"] == 1


class TestValidationReportGenerator:
    """Test cases for Validation Report Generator"""

    @pytest.fixture
    def report_generator(self):
        """Create validation report generator instance for testing"""
        return ValidationReportGenerator()

    @pytest.fixture
    def sample_worker_results(self):
        """Sample worker results for testing"""
        return [
            WorkerTaskResult(
                task_type=WorkerTaskType.NPI_CHECK,
                provider_id="12345",
                success=True,
                confidence=0.9,
                normalized_fields={
                    "npi_number": "1234567890",
                    "given_name": "John",
                    "family_name": "Smith"
                },
                field_confidence={
                    "npi_number": 0.95,
                    "given_name": 0.90,
                    "family_name": 0.90
                }
            ),
            WorkerTaskResult(
                task_type=WorkerTaskType.GOOGLE_PLACES,
                provider_id="12345",
                success=True,
                confidence=0.8,
                normalized_fields={
                    "address_street": "123 Main St, San Francisco, CA 94102"
                },
                field_confidence={
                    "address_street": 0.85
                }
            ),
            WorkerTaskResult(
                task_type=WorkerTaskType.STATE_BOARD_CHECK,
                provider_id="12345",
                success=False,
                confidence=0.0,
                normalized_fields={},
                field_confidence={},
                error_message="License not found"
            )
        ]

    def test_report_generator_initialization(self, report_generator):
        """Test report generator initialization"""
        assert report_generator.critical_fields is not None
        assert report_generator.high_importance_fields is not None
        assert report_generator.confidence_thresholds is not None
        assert report_generator.validation_weights is not None

    def test_generate_validation_report(self, report_generator, sample_worker_results):
        """Test validation report generation"""
        original_data = {
            "provider_id": "12345",
            "given_name": "Dr. John Smith",
            "family_name": "Smith",
            "npi_number": "1234567890"
        }
        
        report = report_generator.generate_validation_report(
            provider_id="12345",
            job_id="job_123",
            worker_results=sample_worker_results,
            original_data=original_data,
            processing_time=5.0
        )
        
        assert report is not None
        assert report.provider_id == "12345"
        assert report.job_id == "job_123"
        assert report.summary is not None
        assert len(report.field_analyses) > 0
        assert len(report.insights) > 0

    def test_analyze_fields(self, report_generator, sample_worker_results):
        """Test field analysis"""
        original_data = {
            "given_name": "Dr. John Smith",
            "family_name": "Smith"
        }
        
        field_analyses = report_generator._analyze_fields(sample_worker_results, original_data)
        
        assert len(field_analyses) > 0
        
        # Check for NPI analysis
        npi_analysis = next((fa for fa in field_analyses if fa.field_name == "npi_number"), None)
        assert npi_analysis is not None
        assert npi_analysis.validated_value == "1234567890"
        assert npi_analysis.confidence == 0.95

    def test_generate_insights(self, report_generator, sample_worker_results):
        """Test insight generation"""
        field_analyses = [
            FieldAnalysis(
                field_name="npi_number",
                original_value="1234567890",
                validated_value="1234567890",
                confidence=0.95,
                validation_status="valid",
                validation_source="npi_check",
                validation_timestamp=datetime.now(),
                issues=[],
                suggestions=[]
            ),
            FieldAnalysis(
                field_name="license_number",
                original_value="A123456",
                validated_value=None,
                confidence=0.0,
                validation_status="invalid",
                validation_source="state_board_check",
                validation_timestamp=datetime.now(),
                issues=["License not found"],
                suggestions=["Verify license number"]
            )
        ]
        
        insights = report_generator._generate_insights(field_analyses, sample_worker_results)
        
        assert len(insights) > 0
        
        # Check for missing critical field insight
        missing_insight = next((i for i in insights if i.type == "missing_critical_fields"), None)
        assert missing_insight is not None
        assert missing_insight.severity == ReportSeverity.CRITICAL

    def test_generate_flags(self, report_generator, sample_worker_results):
        """Test flag generation"""
        field_analyses = [
            FieldAnalysis(
                field_name="npi_number",
                original_value="1234567890",
                validated_value="1234567890",
                confidence=0.95,
                validation_status="valid",
                validation_source="npi_check",
                validation_timestamp=datetime.now(),
                issues=[],
                suggestions=[]
            )
        ]
        
        flags = report_generator._generate_flags(field_analyses, sample_worker_results)
        
        assert "VALIDATION_FAILED" in [flag.value for flag in flags]

    def test_export_report_to_json(self, report_generator, sample_worker_results):
        """Test report JSON export"""
        original_data = {"given_name": "John"}
        
        report = report_generator.generate_validation_report(
            provider_id="12345",
            job_id="job_123",
            worker_results=sample_worker_results,
            original_data=original_data,
            processing_time=5.0
        )
        
        json_report = report_generator.export_report_to_json(report)
        
        assert json_report is not None
        assert len(json_report) > 0
        
        # Parse JSON to verify structure
        parsed_report = json.loads(json_report)
        assert parsed_report["provider_id"] == "12345"
        assert parsed_report["job_id"] == "job_123"


class TestRateLimiter:
    """Test cases for Rate Limiter"""

    @pytest.fixture
    def rate_limiter(self):
        """Create rate limiter instance for testing"""
        return RateLimiter()

    def test_rate_limiter_initialization(self, rate_limiter):
        """Test rate limiter initialization"""
        assert rate_limiter.redis_conn is not None
        assert rate_limiter.rate_limits is not None
        assert rate_limiter.last_requests is not None

    def test_set_rate_limit(self, rate_limiter):
        """Test setting rate limit"""
        from utils.rate_limiter import RateLimitConfig
        
        config = RateLimitConfig(
            connector_name="test_connector",
            requests_per_second=5.0,
            requests_per_minute=300
        )
        
        rate_limiter.set_rate_limit("test_connector", config)
        
        assert "test_connector" in rate_limiter.rate_limits

    @pytest.mark.asyncio
    async def test_check_rate_limit(self, rate_limiter):
        """Test rate limit checking"""
        with patch.object(rate_limiter.redis_conn, 'zremrangebyscore') as mock_zrem:
            with patch.object(rate_limiter.redis_conn, 'zcard') as mock_zcard:
                with patch.object(rate_limiter.redis_conn, 'zadd') as mock_zadd:
                    mock_zrem.return_value = 0
                    mock_zcard.return_value = 0
                    mock_zadd.return_value = 0
                    
                    is_allowed, wait_time = await rate_limiter.check_rate_limit("npi_registry")
                    
                    assert is_allowed is True
                    assert wait_time == 0.0

    def test_get_rate_limit_status(self, rate_limiter):
        """Test getting rate limit status"""
        with patch.object(rate_limiter.redis_conn, 'zremrangebyscore') as mock_zrem:
            with patch.object(rate_limiter.redis_conn, 'zcard') as mock_zcard:
                mock_zrem.return_value = 0
                mock_zcard.return_value = 5
                
                status = rate_limiter.get_rate_limit_status("npi_registry")
                
                assert status is not None
                assert "connector_name" in status
                assert "current_usage" in status
                assert "limit" in status


class TestIdempotencyManager:
    """Test cases for Idempotency Manager"""

    @pytest.fixture
    def idempotency_manager(self):
        """Create idempotency manager instance for testing"""
        return IdempotencyManager()

    def test_idempotency_manager_initialization(self, idempotency_manager):
        """Test idempotency manager initialization"""
        assert idempotency_manager.redis_conn is not None
        assert idempotency_manager.default_ttl is not None

    def test_generate_idempotency_key(self, idempotency_manager):
        """Test idempotency key generation"""
        request_data = {
            "provider_data": [{"provider_id": "12345"}],
            "validation_options": {"enable_npi_check": True}
        }
        
        key = idempotency_manager.generate_idempotency_key(request_data)
        
        assert key is not None
        assert key.startswith("validation_")
        assert len(key) > 20

    def test_generate_custom_idempotency_key(self, idempotency_manager):
        """Test custom idempotency key generation"""
        custom_data = "test_custom_data_12345"
        
        key = idempotency_manager.generate_custom_idempotency_key(custom_data)
        
        assert key is not None
        assert key.startswith("custom_")
        assert len(key) > 20

    @pytest.mark.asyncio
    async def test_create_idempotency_record(self, idempotency_manager):
        """Test creating idempotency record"""
        with patch.object(idempotency_manager.redis_conn, 'setex') as mock_setex:
            mock_setex.return_value = True
            
            request_data = {"test": "data"}
            
            record = await idempotency_manager.create_idempotency_record(
                idempotency_key="test_key",
                job_id="job_123",
                request_data=request_data
            )
            
            assert record is not None
            assert record.key == "test_key"
            assert record.job_id == "job_123"
            mock_setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_idempotency(self, idempotency_manager):
        """Test checking idempotency"""
        with patch.object(idempotency_manager.redis_conn, 'get') as mock_get:
            mock_get.return_value = None
            
            result = await idempotency_manager.check_idempotency("test_key")
            
            assert result is None
            mock_get.assert_called_once()


class TestCSVProcessor:
    """Test cases for CSV Processor"""

    @pytest.fixture
    def csv_processor(self):
        """Create CSV processor instance for testing"""
        return CSVProcessor()

    @pytest.fixture
    def sample_csv_content(self):
        """Sample CSV content for testing"""
        return """provider_id,given_name,family_name,npi_number,phone_primary,email
12345,Dr. John,Smith,1234567890,+1-555-123-4567,john.smith@example.com
67890,Dr. Jane,Doe,0987654321,+1-555-987-6543,jane.doe@example.com"""

    def test_csv_processor_initialization(self, csv_processor):
        """Test CSV processor initialization"""
        assert csv_processor.default_field_mappings is not None
        assert csv_processor.validation_patterns is not None

    @pytest.mark.asyncio
    async def test_process_csv_file(self, csv_processor, sample_csv_content):
        """Test CSV file processing"""
        result = await csv_processor.process_csv_file(sample_csv_content)
        
        assert result is not None
        assert result.success is True
        assert result.provider_count == 2
        assert len(result.processed_providers) == 2
        assert len(result.errors) == 0

    def test_determine_field_mappings(self, csv_processor):
        """Test field mapping determination"""
        headers = ["provider_id", "first_name", "last_name", "npi", "phone"]
        
        mappings = csv_processor._determine_field_mappings(headers, "standard", None)
        
        assert "provider_id" in mappings
        assert "given_name" in mappings
        assert "family_name" in mappings
        assert "npi_number" in mappings
        assert "phone_primary" in mappings

    def test_process_field_value(self, csv_processor):
        """Test field value processing"""
        # Test NPI processing
        npi_value = csv_processor._process_field_value("npi_number", "123-456-7890")
        assert npi_value == "1234567890"
        
        # Test phone processing
        phone_value = csv_processor._process_field_value("phone_primary", "(555) 123-4567")
        assert phone_value.startswith("+1")
        
        # Test email processing
        email_value = csv_processor._process_field_value("email", "TEST@EXAMPLE.COM")
        assert email_value == "test@example.com"

    def test_validate_provider_data(self, csv_processor):
        """Test provider data validation"""
        # Valid data
        valid_data = {
            "given_name": "John",
            "family_name": "Smith",
            "npi_number": "1234567890",
            "phone_primary": "+15551234567",
            "email": "john@example.com"
        }
        
        errors = csv_processor._validate_provider_data(valid_data)
        assert len(errors) == 0
        
        # Invalid data
        invalid_data = {
            "given_name": "",
            "family_name": "Smith",
            "npi_number": "123",
            "phone_primary": "invalid",
            "email": "invalid-email"
        }
        
        errors = csv_processor._validate_provider_data(invalid_data)
        assert len(errors) > 0

    def test_generate_csv_template(self, csv_processor):
        """Test CSV template generation"""
        template = csv_processor.generate_csv_template()
        
        assert template is not None
        assert len(template) > 0
        assert "provider_id" in template
        assert "given_name" in template
        assert "family_name" in template

    def test_validate_csv_structure(self, csv_processor, sample_csv_content):
        """Test CSV structure validation"""
        validation = csv_processor.validate_csv_structure(sample_csv_content)
        
        assert validation["valid"] is True
        assert len(validation["headers"]) > 0
        assert validation["row_count"] == 2
        assert len(validation["field_mappings"]) > 0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
