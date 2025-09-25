"""
Validation Orchestrator Service

This module implements a master agent validation orchestrator that coordinates
multiple worker tasks for comprehensive provider data validation.
"""

import asyncio
import logging
import json
import uuid
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import redis
from rq import Queue, Worker, Connection
from rq.job import Job
import httpx
from sqlalchemy.orm import Session

from models.provider import Provider
from models.validation import ValidationJob, ValidationResult
from connectors.npi import NPIConnector
from connectors.google_places import GooglePlacesConnector
from connectors.state_board_mock import StateBoardMockConnector, ScrapingConfig
from pipelines.ocr import OCRPipeline, OCRProvider
from connectors.validation_rules import ValidationRulesEngine, ValidationSource
from connectors.robots_compliance import RobotsComplianceManager

logger = logging.getLogger(__name__)


class WorkerTaskType(Enum):
    """Types of worker tasks"""
    NPI_CHECK = "npi_check"
    GOOGLE_PLACES = "google_places"
    OCR_PROCESSING = "ocr_processing"
    STATE_BOARD_CHECK = "state_board_check"
    ENRICHMENT_LOOKUP = "enrichment_lookup"


class JobStatus(Enum):
    """Job status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkerTaskResult:
    """Result from a worker task"""
    task_type: WorkerTaskType
    provider_id: str
    success: bool
    confidence: float
    normalized_fields: Dict[str, Any]
    field_confidence: Dict[str, float]
    error_message: Optional[str] = None
    processing_time: float = 0.0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class ValidationReport:
    """Comprehensive validation report for a provider"""
    provider_id: str
    job_id: str
    overall_confidence: float
    validation_status: str
    field_summaries: Dict[str, Dict[str, Any]]
    worker_results: List[WorkerTaskResult]
    aggregated_fields: Dict[str, Any]
    flags: List[str]
    validation_timestamp: datetime
    processing_time: float
    retry_count: int = 0


@dataclass
class BatchValidationRequest:
    """Request for batch validation"""
    provider_data: List[Dict[str, Any]]
    validation_options: Dict[str, Any]
    idempotency_key: Optional[str] = None
    priority: str = "normal"


class ValidationOrchestrator:
    """
    Validation Orchestrator - Master Agent
    
    Coordinates multiple worker tasks for comprehensive provider validation:
    - NPI Registry validation
    - Google Places address validation
    - OCR processing for PDFs
    - State board license verification
    - Enrichment lookups
    """
    
    def __init__(self, 
                 redis_url: str = "redis://localhost:6379/0",
                 db_session: Optional[Session] = None):
        """
        Initialize Validation Orchestrator
        
        Args:
            redis_url: Redis connection URL for job queue
            db_session: Database session for persistence
        """
        self.redis_url = redis_url
        self.db_session = db_session
        
        # Initialize Redis connection
        self.redis_conn = redis.from_url(redis_url)
        
        # Initialize job queues
        self.npi_queue = Queue('npi_validation', connection=self.redis_conn)
        self.google_places_queue = Queue('google_places_validation', connection=self.redis_conn)
        self.ocr_queue = Queue('ocr_processing', connection=self.redis_conn)
        self.state_board_queue = Queue('state_board_validation', connection=self.redis_conn)
        self.enrichment_queue = Queue('enrichment_lookup', connection=self.redis_conn)
        
        # Initialize connectors
        self.npi_connector = NPIConnector()
        self.google_places_connector = GooglePlacesConnector(api_key="mock_key")
        self.state_board_connector = StateBoardMockConnector(
            ScrapingConfig(
                state_code="CA",
                state_name="California",
                base_url="http://127.0.0.1:8080",
                search_url="http://127.0.0.1:8080/search",
                search_method="POST"
            )
        )
        self.ocr_pipeline = OCRPipeline(provider=OCRProvider.TESSERACT)
        self.validation_engine = ValidationRulesEngine()
        self.robots_manager = RobotsComplianceManager()
        
        # Rate limiting and retry configuration
        self.rate_limits = {
            WorkerTaskType.NPI_CHECK: {"requests_per_second": 10, "burst_limit": 20},
            WorkerTaskType.GOOGLE_PLACES: {"requests_per_second": 10, "burst_limit": 20},
            WorkerTaskType.OCR_PROCESSING: {"requests_per_second": 5, "burst_limit": 10},
            WorkerTaskType.STATE_BOARD_CHECK: {"requests_per_second": 0.5, "burst_limit": 5},
            WorkerTaskType.ENRICHMENT_LOOKUP: {"requests_per_second": 2, "burst_limit": 5}
        }
        
        self.retry_policy = {
            "max_retries": 3,
            "base_delay": 1.0,
            "exponential_backoff": True,
            "max_delay": 60.0
        }
        
        # Job tracking
        self.active_jobs = {}
        self.job_results = {}
    
    async def validate_provider_batch(self, 
                                    provider_data_list: List[Dict[str, Any]],
                                    validation_options: Optional[Dict[str, Any]] = None,
                                    idempotency_key: Optional[str] = None) -> str:
        """
        Start batch validation for multiple providers
        
        Args:
            provider_data_list: List of provider data dictionaries
            validation_options: Validation configuration options
            idempotency_key: Idempotency key for deduplication
            
        Returns:
            Job ID for tracking
        """
        try:
            # Generate job ID
            job_id = str(uuid.uuid4())
            
            # Check for existing job with same idempotency key
            if idempotency_key:
                existing_job = await self._get_job_by_idempotency_key(idempotency_key)
                if existing_job:
                    logger.info(f"Found existing job {existing_job.id} for idempotency key {idempotency_key}")
                    return existing_job.id
            
            # Create validation job record
            validation_job = ValidationJob(
                id=job_id,
                idempotency_key=idempotency_key,
                status=JobStatus.PENDING.value,
                provider_count=len(provider_data_list),
                validation_options=validation_options or {},
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Save to database
            if self.db_session:
                self.db_session.add(validation_job)
                self.db_session.commit()
            
            # Store job metadata
            self.active_jobs[job_id] = {
                "job_id": job_id,
                "status": JobStatus.PENDING.value,
                "provider_count": len(provider_data_list),
                "created_at": datetime.now(),
                "validation_options": validation_options or {}
            }
            
            # Enqueue validation tasks for each provider
            for provider_data in provider_data_list:
                await self._enqueue_provider_validation(job_id, provider_data, validation_options)
            
            # Update job status to running
            await self._update_job_status(job_id, JobStatus.RUNNING.value)
            
            logger.info(f"Started batch validation job {job_id} for {len(provider_data_list)} providers")
            
            return job_id
        
        except Exception as e:
            logger.error(f"Failed to start batch validation: {str(e)}")
            raise
    
    async def _enqueue_provider_validation(self, 
                                         job_id: str,
                                         provider_data: Dict[str, Any],
                                         validation_options: Optional[Dict[str, Any]] = None):
        """
        Enqueue validation tasks for a single provider
        
        Args:
            job_id: Job ID
            provider_data: Provider data dictionary
            validation_options: Validation options
        """
        try:
            provider_id = provider_data.get("provider_id", str(uuid.uuid4()))
            
            # Enqueue NPI check
            if validation_options.get("enable_npi_check", True):
                self.npi_queue.enqueue(
                    validate_npi_worker,
                    job_id,
                    provider_id,
                    provider_data,
                    validation_options,
                    job_timeout="5m"
                )
            
            # Enqueue Google Places validation
            if validation_options.get("enable_address_validation", True):
                self.google_places_queue.enqueue(
                    validate_address_worker,
                    job_id,
                    provider_id,
                    provider_data,
                    validation_options,
                    job_timeout="5m"
                )
            
            # Enqueue OCR processing if PDF provided
            if validation_options.get("enable_ocr_processing", True) and provider_data.get("document_path"):
                self.ocr_queue.enqueue(
                    process_ocr_worker,
                    job_id,
                    provider_id,
                    provider_data,
                    validation_options,
                    job_timeout="10m"
                )
            
            # Enqueue state board check
            if validation_options.get("enable_license_validation", True):
                self.state_board_queue.enqueue(
                    validate_license_worker,
                    job_id,
                    provider_id,
                    provider_data,
                    validation_options,
                    job_timeout="5m"
                )
            
            # Enqueue enrichment lookup
            if validation_options.get("enable_enrichment", True):
                self.enrichment_queue.enqueue(
                    enrichment_lookup_worker,
                    job_id,
                    provider_id,
                    provider_data,
                    validation_options,
                    job_timeout="5m"
                )
        
        except Exception as e:
            logger.error(f"Failed to enqueue validation tasks for provider {provider_id}: {str(e)}")
            raise
    
    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get job status and progress
        
        Args:
            job_id: Job ID
            
        Returns:
            Job status information
        """
        try:
            # Check active jobs
            if job_id in self.active_jobs:
                job_info = self.active_jobs[job_id]
                
                # Get job progress from Redis
                progress = await self._get_job_progress(job_id)
                
                return {
                    "job_id": job_id,
                    "status": job_info["status"],
                    "provider_count": job_info["provider_count"],
                    "completed_count": progress.get("completed", 0),
                    "failed_count": progress.get("failed", 0),
                    "progress_percentage": progress.get("percentage", 0),
                    "created_at": job_info["created_at"].isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "validation_options": job_info["validation_options"]
                }
            
            # Check database for completed job
            if self.db_session:
                validation_job = self.db_session.query(ValidationJob).filter_by(id=job_id).first()
                if validation_job:
                    return {
                        "job_id": job_id,
                        "status": validation_job.status,
                        "provider_count": validation_job.provider_count,
                        "completed_count": validation_job.completed_count,
                        "failed_count": validation_job.failed_count,
                        "progress_percentage": 100.0 if validation_job.status == JobStatus.COMPLETED.value else 0.0,
                        "created_at": validation_job.created_at.isoformat(),
                        "updated_at": validation_job.updated_at.isoformat(),
                        "validation_options": validation_job.validation_options
                    }
            
            return {"error": "Job not found"}
        
        except Exception as e:
            logger.error(f"Failed to get job status for {job_id}: {str(e)}")
            return {"error": str(e)}
    
    async def get_validation_report(self, job_id: str, provider_id: str) -> Optional[ValidationReport]:
        """
        Get validation report for a specific provider
        
        Args:
            job_id: Job ID
            provider_id: Provider ID
            
        Returns:
            ValidationReport or None
        """
        try:
            # Get worker results from Redis
            worker_results = await self._get_provider_worker_results(job_id, provider_id)
            
            if not worker_results:
                return None
            
            # Aggregate results
            aggregated_fields, field_confidence = self._aggregate_worker_results(worker_results)
            
            # Calculate overall confidence
            overall_confidence = self._calculate_overall_confidence(field_confidence)
            
            # Determine validation status
            validation_status = self._determine_validation_status(overall_confidence, worker_results)
            
            # Generate flags
            flags = self._generate_validation_flags(worker_results, aggregated_fields)
            
            # Create validation report
            report = ValidationReport(
                provider_id=provider_id,
                job_id=job_id,
                overall_confidence=overall_confidence,
                validation_status=validation_status,
                field_summaries=self._create_field_summaries(worker_results),
                worker_results=worker_results,
                aggregated_fields=aggregated_fields,
                flags=flags,
                validation_timestamp=datetime.now(),
                processing_time=sum(r.processing_time for r in worker_results)
            )
            
            return report
        
        except Exception as e:
            logger.error(f"Failed to get validation report for {job_id}/{provider_id}: {str(e)}")
            return None
    
    def _aggregate_worker_results(self, worker_results: List[WorkerTaskResult]) -> Tuple[Dict[str, Any], Dict[str, float]]:
        """
        Aggregate worker results using weighted confidence
        
        Args:
            worker_results: List of worker task results
            
        Returns:
            Tuple of (aggregated_fields, field_confidence)
        """
        aggregated_fields = {}
        field_confidence = {}
        
        # Confidence weights for different sources
        source_weights = {
            WorkerTaskType.NPI_CHECK: 0.4,
            WorkerTaskType.GOOGLE_PLACES: 0.25,
            WorkerTaskType.STATE_BOARD_CHECK: 0.15,
            WorkerTaskType.ENRICHMENT_LOOKUP: 0.2
        }
        
        for result in worker_results:
            if not result.success:
                continue
            
            source_weight = source_weights.get(result.task_type, 0.1)
            
            for field_name, field_value in result.normalized_fields.items():
                if field_name not in aggregated_fields:
                    aggregated_fields[field_name] = field_value
                    field_confidence[field_name] = result.field_confidence.get(field_name, 0.0) * source_weight
                else:
                    # Use weighted average for confidence
                    current_confidence = field_confidence[field_name]
                    new_confidence = result.field_confidence.get(field_name, 0.0) * source_weight
                    
                    # Update field value if new confidence is higher
                    if new_confidence > current_confidence:
                        aggregated_fields[field_name] = field_value
                        field_confidence[field_name] = new_confidence
        
        return aggregated_fields, field_confidence
    
    def _calculate_overall_confidence(self, field_confidence: Dict[str, float]) -> float:
        """
        Calculate overall confidence from field confidence scores
        
        Args:
            field_confidence: Field confidence scores
            
        Returns:
            Overall confidence score
        """
        if not field_confidence:
            return 0.0
        
        # Weight fields by importance
        field_weights = {
            "npi_number": 0.25,
            "given_name": 0.20,
            "family_name": 0.20,
            "license_number": 0.15,
            "phone_primary": 0.10,
            "email": 0.10
        }
        
        total_weight = 0.0
        weighted_confidence = 0.0
        
        for field_name, confidence in field_confidence.items():
            weight = field_weights.get(field_name, 0.05)
            weighted_confidence += confidence * weight
            total_weight += weight
        
        return weighted_confidence / total_weight if total_weight > 0 else 0.0
    
    def _determine_validation_status(self, overall_confidence: float, worker_results: List[WorkerTaskResult]) -> str:
        """
        Determine validation status based on confidence and results
        
        Args:
            overall_confidence: Overall confidence score
            worker_results: List of worker results
            
        Returns:
            Validation status string
        """
        if overall_confidence >= 0.8:
            return "valid"
        elif overall_confidence >= 0.6:
            return "warning"
        else:
            return "invalid"
    
    def _generate_validation_flags(self, worker_results: List[WorkerTaskResult], aggregated_fields: Dict[str, Any]) -> List[str]:
        """
        Generate validation flags based on results
        
        Args:
            worker_results: List of worker results
            aggregated_fields: Aggregated field values
            
        Returns:
            List of validation flags
        """
        flags = []
        
        # Check for failed validations
        failed_tasks = [r for r in worker_results if not r.success]
        if failed_tasks:
            flags.append(f"FAILED_VALIDATIONS: {len(failed_tasks)}")
        
        # Check for low confidence fields
        for result in worker_results:
            if result.success:
                for field_name, confidence in result.field_confidence.items():
                    if confidence < 0.5:
                        flags.append(f"LOW_CONFIDENCE_{field_name.upper()}")
        
        # Check for missing critical fields
        critical_fields = ["npi_number", "given_name", "family_name", "license_number"]
        for field in critical_fields:
            if field not in aggregated_fields:
                flags.append(f"MISSING_{field.upper()}")
        
        return flags
    
    def _create_field_summaries(self, worker_results: List[WorkerTaskResult]) -> Dict[str, Dict[str, Any]]:
        """
        Create field summaries from worker results
        
        Args:
            worker_results: List of worker results
            
        Returns:
            Field summaries dictionary
        """
        field_summaries = {}
        
        for result in worker_results:
            if not result.success:
                continue
            
            for field_name, confidence in result.field_confidence.items():
                if field_name not in field_summaries:
                    field_summaries[field_name] = {
                        "field_name": field_name,
                        "confidence": confidence,
                        "source": result.task_type.value,
                        "value": result.normalized_fields.get(field_name),
                        "validation_count": 1
                    }
                else:
                    # Update if confidence is higher
                    if confidence > field_summaries[field_name]["confidence"]:
                        field_summaries[field_name]["confidence"] = confidence
                        field_summaries[field_name]["source"] = result.task_type.value
                        field_summaries[field_name]["value"] = result.normalized_fields.get(field_name)
                    field_summaries[field_name]["validation_count"] += 1
        
        return field_summaries
    
    async def _update_job_status(self, job_id: str, status: str):
        """Update job status in Redis and database"""
        try:
            # Update Redis
            if job_id in self.active_jobs:
                self.active_jobs[job_id]["status"] = status
                self.active_jobs[job_id]["updated_at"] = datetime.now()
            
            # Update database
            if self.db_session:
                validation_job = self.db_session.query(ValidationJob).filter_by(id=job_id).first()
                if validation_job:
                    validation_job.status = status
                    validation_job.updated_at = datetime.now()
                    self.db_session.commit()
        
        except Exception as e:
            logger.error(f"Failed to update job status for {job_id}: {str(e)}")
    
    async def _get_job_progress(self, job_id: str) -> Dict[str, Any]:
        """Get job progress from Redis"""
        try:
            progress_key = f"job_progress:{job_id}"
            progress_data = self.redis_conn.hgetall(progress_key)
            
            if progress_data:
                return {
                    "completed": int(progress_data.get(b"completed", 0)),
                    "failed": int(progress_data.get(b"failed", 0)),
                    "percentage": float(progress_data.get(b"percentage", 0))
                }
            
            return {"completed": 0, "failed": 0, "percentage": 0}
        
        except Exception as e:
            logger.error(f"Failed to get job progress for {job_id}: {str(e)}")
            return {"completed": 0, "failed": 0, "percentage": 0}
    
    async def _get_provider_worker_results(self, job_id: str, provider_id: str) -> List[WorkerTaskResult]:
        """Get worker results for a provider from Redis"""
        try:
            results_key = f"worker_results:{job_id}:{provider_id}"
            results_data = self.redis_conn.lrange(results_key, 0, -1)
            
            worker_results = []
            for result_json in results_data:
                result_data = json.loads(result_json)
                result = WorkerTaskResult(**result_data)
                worker_results.append(result)
            
            return worker_results
        
        except Exception as e:
            logger.error(f"Failed to get worker results for {job_id}/{provider_id}: {str(e)}")
            return []
    
    async def _get_job_by_idempotency_key(self, idempotency_key: str) -> Optional[ValidationJob]:
        """Get existing job by idempotency key"""
        try:
            if self.db_session:
                return self.db_session.query(ValidationJob).filter_by(idempotency_key=idempotency_key).first()
            return None
        except Exception as e:
            logger.error(f"Failed to get job by idempotency key {idempotency_key}: {str(e)}")
            return None


# Worker Functions (to be run by RQ workers)

def validate_npi_worker(job_id: str, provider_id: str, provider_data: Dict[str, Any], validation_options: Dict[str, Any]) -> Dict[str, Any]:
    """
    Worker function for NPI validation
    
    Args:
        job_id: Job ID
        provider_id: Provider ID
        provider_data: Provider data
        validation_options: Validation options
        
    Returns:
        Worker task result
    """
    try:
        start_time = datetime.now()
        
        # Initialize NPI connector
        npi_connector = NPIConnector()
        
        # Validate NPI number
        npi_number = provider_data.get("npi_number")
        if npi_number:
            result = asyncio.run(npi_connector.search_provider_by_npi(npi_number))
            
            if result.success:
                normalized_fields = {
                    "npi_number": result.data.get("npi_number"),
                    "given_name": result.data.get("given_name"),
                    "family_name": result.data.get("family_name"),
                    "primary_taxonomy": result.data.get("primary_taxonomy"),
                    "practice_name": result.data.get("practice_name")
                }
                
                field_confidence = {
                    "npi_number": 0.95,
                    "given_name": 0.90,
                    "family_name": 0.90,
                    "primary_taxonomy": 0.85,
                    "practice_name": 0.80
                }
                
                worker_result = WorkerTaskResult(
                    task_type=WorkerTaskType.NPI_CHECK,
                    provider_id=provider_id,
                    success=True,
                    confidence=0.90,
                    normalized_fields=normalized_fields,
                    field_confidence=field_confidence,
                    processing_time=(datetime.now() - start_time).total_seconds()
                )
            else:
                worker_result = WorkerTaskResult(
                    task_type=WorkerTaskType.NPI_CHECK,
                    provider_id=provider_id,
                    success=False,
                    confidence=0.0,
                    normalized_fields={},
                    field_confidence={},
                    error_message=result.error_message,
                    processing_time=(datetime.now() - start_time).total_seconds()
                )
        else:
            worker_result = WorkerTaskResult(
                task_type=WorkerTaskType.NPI_CHECK,
                provider_id=provider_id,
                success=False,
                confidence=0.0,
                normalized_fields={},
                field_confidence={},
                error_message="No NPI number provided",
                processing_time=(datetime.now() - start_time).total_seconds()
            )
        
        # Store result in Redis
        store_worker_result(job_id, provider_id, worker_result)
        
        return asdict(worker_result)
    
    except Exception as e:
        logger.error(f"NPI validation worker failed for {provider_id}: {str(e)}")
        worker_result = WorkerTaskResult(
            task_type=WorkerTaskType.NPI_CHECK,
            provider_id=provider_id,
            success=False,
            confidence=0.0,
            normalized_fields={},
            field_confidence={},
            error_message=str(e),
            processing_time=0.0
        )
        store_worker_result(job_id, provider_id, worker_result)
        return asdict(worker_result)


def validate_address_worker(job_id: str, provider_id: str, provider_data: Dict[str, Any], validation_options: Dict[str, Any]) -> Dict[str, Any]:
    """
    Worker function for address validation using Google Places
    
    Args:
        job_id: Job ID
        provider_id: Provider ID
        provider_data: Provider data
        validation_options: Validation options
        
    Returns:
        Worker task result
    """
    try:
        start_time = datetime.now()
        
        # Initialize Google Places connector
        google_connector = GooglePlacesConnector(api_key="mock_key")
        
        # Validate address
        address = provider_data.get("address_street")
        if address:
            result = asyncio.run(google_connector.validate_address(address))
            
            if result.success:
                normalized_fields = {
                    "address_street": result.data.get("formatted_address"),
                    "place_id": result.data.get("place_id"),
                    "latitude": result.data.get("latitude"),
                    "longitude": result.data.get("longitude")
                }
                
                field_confidence = {
                    "address_street": 0.90,
                    "place_id": 0.95,
                    "latitude": 0.90,
                    "longitude": 0.90
                }
                
                worker_result = WorkerTaskResult(
                    task_type=WorkerTaskType.GOOGLE_PLACES,
                    provider_id=provider_id,
                    success=True,
                    confidence=0.90,
                    normalized_fields=normalized_fields,
                    field_confidence=field_confidence,
                    processing_time=(datetime.now() - start_time).total_seconds()
                )
            else:
                worker_result = WorkerTaskResult(
                    task_type=WorkerTaskType.GOOGLE_PLACES,
                    provider_id=provider_id,
                    success=False,
                    confidence=0.0,
                    normalized_fields={},
                    field_confidence={},
                    error_message=result.error_message,
                    processing_time=(datetime.now() - start_time).total_seconds()
                )
        else:
            worker_result = WorkerTaskResult(
                task_type=WorkerTaskType.GOOGLE_PLACES,
                provider_id=provider_id,
                success=False,
                confidence=0.0,
                normalized_fields={},
                field_confidence={},
                error_message="No address provided",
                processing_time=(datetime.now() - start_time).total_seconds()
            )
        
        # Store result in Redis
        store_worker_result(job_id, provider_id, worker_result)
        
        return asdict(worker_result)
    
    except Exception as e:
        logger.error(f"Address validation worker failed for {provider_id}: {str(e)}")
        worker_result = WorkerTaskResult(
            task_type=WorkerTaskType.GOOGLE_PLACES,
            provider_id=provider_id,
            success=False,
            confidence=0.0,
            normalized_fields={},
            field_confidence={},
            error_message=str(e),
            processing_time=0.0
        )
        store_worker_result(job_id, provider_id, worker_result)
        return asdict(worker_result)


def process_ocr_worker(job_id: str, provider_id: str, provider_data: Dict[str, Any], validation_options: Dict[str, Any]) -> Dict[str, Any]:
    """
    Worker function for OCR processing
    
    Args:
        job_id: Job ID
        provider_id: Provider ID
        provider_data: Provider data
        validation_options: Validation options
        
    Returns:
        Worker task result
    """
    try:
        start_time = datetime.now()
        
        # Initialize OCR pipeline
        ocr_pipeline = OCRPipeline(provider=OCRProvider.TESSERACT)
        
        # Process document
        document_path = provider_data.get("document_path")
        if document_path:
            result = asyncio.run(ocr_pipeline.extract_text(document_path))
            
            if result["success"]:
                # Extract structured fields from OCR result
                extracted_fields = {}
                field_confidence = {}
                
                for field in result["extracted_fields"]:
                    field_name = field["field_name"]
                    field_value = field["field_value"]
                    confidence = field["confidence"]
                    
                    extracted_fields[field_name] = field_value
                    field_confidence[field_name] = confidence
                
                worker_result = WorkerTaskResult(
                    task_type=WorkerTaskType.OCR_PROCESSING,
                    provider_id=provider_id,
                    success=True,
                    confidence=result["confidence_score"],
                    normalized_fields=extracted_fields,
                    field_confidence=field_confidence,
                    processing_time=(datetime.now() - start_time).total_seconds()
                )
            else:
                worker_result = WorkerTaskResult(
                    task_type=WorkerTaskType.OCR_PROCESSING,
                    provider_id=provider_id,
                    success=False,
                    confidence=0.0,
                    normalized_fields={},
                    field_confidence={},
                    error_message=result.get("error", "OCR processing failed"),
                    processing_time=(datetime.now() - start_time).total_seconds()
                )
        else:
            worker_result = WorkerTaskResult(
                task_type=WorkerTaskType.OCR_PROCESSING,
                provider_id=provider_id,
                success=False,
                confidence=0.0,
                normalized_fields={},
                field_confidence={},
                error_message="No document path provided",
                processing_time=(datetime.now() - start_time).total_seconds()
            )
        
        # Store result in Redis
        store_worker_result(job_id, provider_id, worker_result)
        
        return asdict(worker_result)
    
    except Exception as e:
        logger.error(f"OCR processing worker failed for {provider_id}: {str(e)}")
        worker_result = WorkerTaskResult(
            task_type=WorkerTaskType.OCR_PROCESSING,
            provider_id=provider_id,
            success=False,
            confidence=0.0,
            normalized_fields={},
            field_confidence={},
            error_message=str(e),
            processing_time=0.0
        )
        store_worker_result(job_id, provider_id, worker_result)
        return asdict(worker_result)


def validate_license_worker(job_id: str, provider_id: str, provider_data: Dict[str, Any], validation_options: Dict[str, Any]) -> Dict[str, Any]:
    """
    Worker function for license validation
    
    Args:
        job_id: Job ID
        provider_id: Provider ID
        provider_data: Provider data
        validation_options: Validation options
        
    Returns:
        Worker task result
    """
    try:
        start_time = datetime.now()
        
        # Initialize state board connector
        state_board_connector = StateBoardMockConnector(
            ScrapingConfig(
                state_code=provider_data.get("license_state", "CA"),
                state_name="California",
                base_url="http://127.0.0.1:8080",
                search_url="http://127.0.0.1:8080/search",
                search_method="POST"
            )
        )
        
        # Validate license
        license_number = provider_data.get("license_number")
        if license_number:
            result = asyncio.run(state_board_connector.verify_license(license_number))
            
            if result.success:
                normalized_fields = {
                    "license_number": result.data.get("license_number"),
                    "license_state": result.data.get("license_state"),
                    "license_status": result.data.get("license_status"),
                    "issue_date": result.data.get("issue_date"),
                    "expiry_date": result.data.get("expiry_date")
                }
                
                field_confidence = {
                    "license_number": 0.95,
                    "license_state": 0.90,
                    "license_status": 0.95,
                    "issue_date": 0.80,
                    "expiry_date": 0.80
                }
                
                worker_result = WorkerTaskResult(
                    task_type=WorkerTaskType.STATE_BOARD_CHECK,
                    provider_id=provider_id,
                    success=True,
                    confidence=0.90,
                    normalized_fields=normalized_fields,
                    field_confidence=field_confidence,
                    processing_time=(datetime.now() - start_time).total_seconds()
                )
            else:
                worker_result = WorkerTaskResult(
                    task_type=WorkerTaskType.STATE_BOARD_CHECK,
                    provider_id=provider_id,
                    success=False,
                    confidence=0.0,
                    normalized_fields={},
                    field_confidence={},
                    error_message=result.error_message,
                    processing_time=(datetime.now() - start_time).total_seconds()
                )
        else:
            worker_result = WorkerTaskResult(
                task_type=WorkerTaskType.STATE_BOARD_CHECK,
                provider_id=provider_id,
                success=False,
                confidence=0.0,
                normalized_fields={},
                field_confidence={},
                error_message="No license number provided",
                processing_time=(datetime.now() - start_time).total_seconds()
            )
        
        # Store result in Redis
        store_worker_result(job_id, provider_id, worker_result)
        
        return asdict(worker_result)
    
    except Exception as e:
        logger.error(f"License validation worker failed for {provider_id}: {str(e)}")
        worker_result = WorkerTaskResult(
            task_type=WorkerTaskType.STATE_BOARD_CHECK,
            provider_id=provider_id,
            success=False,
            confidence=0.0,
            normalized_fields={},
            field_confidence={},
            error_message=str(e),
            processing_time=0.0
        )
        store_worker_result(job_id, provider_id, worker_result)
        return asdict(worker_result)


def enrichment_lookup_worker(job_id: str, provider_id: str, provider_data: Dict[str, Any], validation_options: Dict[str, Any]) -> Dict[str, Any]:
    """
    Worker function for enrichment lookup
    
    Args:
        job_id: Job ID
        provider_id: Provider ID
        provider_data: Provider data
        validation_options: Validation options
        
    Returns:
        Worker task result
    """
    try:
        start_time = datetime.now()
        
        # Mock enrichment lookup
        normalized_fields = {
            "phone_primary": provider_data.get("phone_primary"),
            "email": provider_data.get("email"),
            "affiliations": ["Example Hospital", "Medical Group"],
            "services_offered": {"primary_care": True, "specialty": False}
        }
        
        field_confidence = {
            "phone_primary": 0.85,
            "email": 0.80,
            "affiliations": 0.70,
            "services_offered": 0.65
        }
        
        worker_result = WorkerTaskResult(
            task_type=WorkerTaskType.ENRICHMENT_LOOKUP,
            provider_id=provider_id,
            success=True,
            confidence=0.75,
            normalized_fields=normalized_fields,
            field_confidence=field_confidence,
            processing_time=(datetime.now() - start_time).total_seconds()
        )
        
        # Store result in Redis
        store_worker_result(job_id, provider_id, worker_result)
        
        return asdict(worker_result)
    
    except Exception as e:
        logger.error(f"Enrichment lookup worker failed for {provider_id}: {str(e)}")
        worker_result = WorkerTaskResult(
            task_type=WorkerTaskType.ENRICHMENT_LOOKUP,
            provider_id=provider_id,
            success=False,
            confidence=0.0,
            normalized_fields={},
            field_confidence={},
            error_message=str(e),
            processing_time=0.0
        )
        store_worker_result(job_id, provider_id, worker_result)
        return asdict(worker_result)


def store_worker_result(job_id: str, provider_id: str, worker_result: WorkerTaskResult):
    """
    Store worker result in Redis
    
    Args:
        job_id: Job ID
        provider_id: Provider ID
        worker_result: Worker task result
    """
    try:
        redis_conn = redis.from_url("redis://localhost:6379/0")
        
        # Store result
        results_key = f"worker_results:{job_id}:{provider_id}"
        result_json = json.dumps(asdict(worker_result), default=str)
        redis_conn.lpush(results_key, result_json)
        
        # Update progress
        progress_key = f"job_progress:{job_id}"
        redis_conn.hincrby(progress_key, "completed", 1)
        
        # Calculate percentage
        total_tasks = 5  # NPI, Google Places, OCR, State Board, Enrichment
        completed = int(redis_conn.hget(progress_key, "completed") or 0)
        percentage = (completed / total_tasks) * 100
        redis_conn.hset(progress_key, "percentage", percentage)
        
    except Exception as e:
        logger.error(f"Failed to store worker result: {str(e)}")


# Global orchestrator instance
validation_orchestrator = ValidationOrchestrator()


# Example usage and testing functions
async def example_validation_orchestrator():
    """
    Example function demonstrating validation orchestrator
    """
    print("=" * 60)
    print("🔍 VALIDATION ORCHESTRATOR EXAMPLE")
    print("=" * 60)
    
    # Initialize orchestrator
    orchestrator = ValidationOrchestrator()
    
    # Sample provider data
    provider_data = {
        "provider_id": "12345",
        "given_name": "Dr. John Smith",
        "family_name": "Smith",
        "npi_number": "1234567890",
        "phone_primary": "(555) 123-4567",
        "email": "john.smith@example.com",
        "address_street": "123 Main Street, San Francisco, CA 94102",
        "license_number": "A123456",
        "license_state": "CA",
        "document_path": "/path/to/provider_document.pdf"
    }
    
    print("\n📋 Provider Data:")
    for key, value in provider_data.items():
        print(f"   {key}: {value}")
    
    # Start batch validation
    print("\n🔍 Starting Batch Validation...")
    job_id = await orchestrator.validate_provider_batch(
        [provider_data],
        validation_options={
            "enable_npi_check": True,
            "enable_address_validation": True,
            "enable_ocr_processing": True,
            "enable_license_validation": True,
            "enable_enrichment": True
        },
        idempotency_key="example-validation-123"
    )
    
    print(f"   Job ID: {job_id}")
    
    # Check job status
    print("\n📊 Job Status:")
    status = await orchestrator.get_job_status(job_id)
    print(f"   Status: {status.get('status')}")
    print(f"   Provider Count: {status.get('provider_count')}")
    print(f"   Progress: {status.get('progress_percentage')}%")
    
    # Get validation report
    print("\n📋 Validation Report:")
    report = await orchestrator.get_validation_report(job_id, provider_data["provider_id"])
    if report:
        print(f"   Overall Confidence: {report.overall_confidence:.2f}")
        print(f"   Validation Status: {report.validation_status}")
        print(f"   Processing Time: {report.processing_time:.2f}s")
        print(f"   Flags: {report.flags}")
        
        print(f"\n   Aggregated Fields:")
        for field_name, field_value in report.aggregated_fields.items():
            print(f"      {field_name}: {field_value}")
        
        print(f"\n   Worker Results:")
        for result in report.worker_results:
            print(f"      {result.task_type.value}: {'✅' if result.success else '❌'} ({result.confidence:.2f})")


if __name__ == "__main__":
    # Run examples
    print("Validation Orchestrator - Examples")
    print("To run examples:")
    print("1. Install dependencies: pip install redis rq")
    print("2. Start Redis server: redis-server")
    print("3. Run: python -c 'from services.validator import example_validation_orchestrator; asyncio.run(example_validation_orchestrator())'")
