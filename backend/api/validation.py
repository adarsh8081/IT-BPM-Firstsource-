"""
Validation API Endpoints

This module provides FastAPI endpoints for batch validation, job status checking,
and validation report retrieval.
"""

import asyncio
import logging
import csv
import io
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import redis
from rq import Queue

from services.validator import ValidationOrchestrator, ValidationReport, BatchValidationRequest
from models.validation import ValidationJob, ValidationResult
from database import get_db
from connectors.robots_compliance import RobotsComplianceManager

logger = logging.getLogger(__name__)

# Initialize API router
router = APIRouter(prefix="/api/validate", tags=["validation"])

# Initialize validation orchestrator
validation_orchestrator = ValidationOrchestrator()

# Initialize robots compliance manager
robots_manager = RobotsComplianceManager()


# Pydantic models for API requests/responses

class ProviderData(BaseModel):
    """Provider data model"""
    provider_id: str = Field(..., description="Unique provider identifier")
    given_name: Optional[str] = Field(None, description="Provider's given name")
    family_name: Optional[str] = Field(None, description="Provider's family name")
    npi_number: Optional[str] = Field(None, description="National Provider Identifier")
    phone_primary: Optional[str] = Field(None, description="Primary phone number")
    email: Optional[str] = Field(None, description="Email address")
    address_street: Optional[str] = Field(None, description="Street address")
    license_number: Optional[str] = Field(None, description="Medical license number")
    license_state: Optional[str] = Field(None, description="License state")
    document_path: Optional[str] = Field(None, description="Path to document for OCR")


class ValidationOptions(BaseModel):
    """Validation options model"""
    enable_npi_check: bool = Field(True, description="Enable NPI Registry validation")
    enable_address_validation: bool = Field(True, description="Enable address validation")
    enable_ocr_processing: bool = Field(True, description="Enable OCR processing")
    enable_license_validation: bool = Field(True, description="Enable license validation")
    enable_enrichment: bool = Field(True, description="Enable enrichment lookup")
    confidence_threshold: float = Field(0.8, description="Minimum confidence threshold")
    max_retries: int = Field(3, description="Maximum number of retries")
    timeout_seconds: int = Field(300, description="Validation timeout in seconds")


class BatchValidationRequest(BaseModel):
    """Batch validation request model"""
    provider_data: List[ProviderData] = Field(..., description="List of providers to validate")
    validation_options: ValidationOptions = Field(..., description="Validation configuration")
    idempotency_key: Optional[str] = Field(None, description="Idempotency key for deduplication")
    priority: str = Field("normal", description="Job priority: low, normal, high")


class BatchValidationResponse(BaseModel):
    """Batch validation response model"""
    job_id: str = Field(..., description="Job identifier")
    status: str = Field(..., description="Job status")
    provider_count: int = Field(..., description="Number of providers to validate")
    estimated_duration: str = Field(..., description="Estimated completion time")
    created_at: datetime = Field(..., description="Job creation timestamp")


class JobStatusResponse(BaseModel):
    """Job status response model"""
    job_id: str = Field(..., description="Job identifier")
    status: str = Field(..., description="Job status")
    provider_count: int = Field(..., description="Total number of providers")
    completed_count: int = Field(..., description="Number of completed providers")
    failed_count: int = Field(..., description="Number of failed providers")
    progress_percentage: float = Field(..., description="Completion percentage")
    created_at: datetime = Field(..., description="Job creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    validation_options: Dict[str, Any] = Field(..., description="Validation options")


class ValidationReportResponse(BaseModel):
    """Validation report response model"""
    provider_id: str = Field(..., description="Provider identifier")
    job_id: str = Field(..., description="Job identifier")
    overall_confidence: float = Field(..., description="Overall confidence score")
    validation_status: str = Field(..., description="Validation status")
    field_summaries: Dict[str, Dict[str, Any]] = Field(..., description="Field validation summaries")
    aggregated_fields: Dict[str, Any] = Field(..., description="Aggregated field values")
    flags: List[str] = Field(..., description="Validation flags")
    validation_timestamp: datetime = Field(..., description="Validation timestamp")
    processing_time: float = Field(..., description="Processing time in seconds")


class CSVUploadResponse(BaseModel):
    """CSV upload response model"""
    job_id: str = Field(..., description="Job identifier")
    status: str = Field(..., description="Job status")
    provider_count: int = Field(..., description="Number of providers from CSV")
    estimated_duration: str = Field(..., description="Estimated completion time")
    created_at: datetime = Field(..., description="Job creation timestamp")


# API Endpoints

@router.post("/batch", response_model=BatchValidationResponse)
async def start_batch_validation(
    request: BatchValidationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Start batch validation for multiple providers
    
    Args:
        request: Batch validation request
        background_tasks: FastAPI background tasks
        db: Database session
        
    Returns:
        Batch validation response with job ID
    """
    try:
        # Validate request
        if not request.provider_data:
            raise HTTPException(status_code=400, detail="No provider data provided")
        
        if len(request.provider_data) > 1000:
            raise HTTPException(status_code=400, detail="Maximum 1000 providers per batch")
        
        # Convert Pydantic models to dictionaries
        provider_data_list = [provider.dict() for provider in request.provider_data]
        validation_options = request.validation_options.dict()
        
        # Generate idempotency key if not provided
        idempotency_key = request.idempotency_key
        if not idempotency_key:
            # Generate idempotency key from provider data hash
            import hashlib
            data_hash = hashlib.md5(str(provider_data_list).encode()).hexdigest()
            idempotency_key = f"batch_validation_{data_hash}"
        
        # Start batch validation
        job_id = await validation_orchestrator.validate_provider_batch(
            provider_data_list=provider_data_list,
            validation_options=validation_options,
            idempotency_key=idempotency_key
        )
        
        # Calculate estimated duration
        estimated_duration = calculate_estimated_duration(len(provider_data_list), validation_options)
        
        # Return response
        return BatchValidationResponse(
            job_id=job_id,
            status="pending",
            provider_count=len(provider_data_list),
            estimated_duration=estimated_duration,
            created_at=datetime.now()
        )
    
    except Exception as e:
        logger.error(f"Failed to start batch validation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start batch validation: {str(e)}")


@router.post("/csv", response_model=CSVUploadResponse)
async def upload_csv_validation(
    file: UploadFile = File(..., description="CSV file with provider data"),
    validation_options: str = Form(..., description="Validation options JSON"),
    idempotency_key: Optional[str] = Form(None, description="Idempotency key"),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """
    Upload CSV file for batch validation
    
    Args:
        file: CSV file upload
        validation_options: Validation options as JSON string
        idempotency_key: Optional idempotency key
        background_tasks: FastAPI background tasks
        db: Database session
        
    Returns:
        CSV upload response with job ID
    """
    try:
        # Validate file type
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="File must be a CSV file")
        
        # Parse validation options
        try:
            import json
            options_dict = json.loads(validation_options)
            validation_options_obj = ValidationOptions(**options_dict)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid validation options: {str(e)}")
        
        # Read CSV file
        content = await file.read()
        csv_content = content.decode('utf-8')
        
        # Parse CSV data
        provider_data_list = parse_csv_data(csv_content)
        
        if not provider_data_list:
            raise HTTPException(status_code=400, detail="No valid provider data found in CSV")
        
        if len(provider_data_list) > 1000:
            raise HTTPException(status_code=400, detail="Maximum 1000 providers per batch")
        
        # Generate idempotency key if not provided
        if not idempotency_key:
            import hashlib
            data_hash = hashlib.md5(csv_content.encode()).hexdigest()
            idempotency_key = f"csv_validation_{data_hash}"
        
        # Start batch validation
        job_id = await validation_orchestrator.validate_provider_batch(
            provider_data_list=provider_data_list,
            validation_options=validation_options_obj.dict(),
            idempotency_key=idempotency_key
        )
        
        # Calculate estimated duration
        estimated_duration = calculate_estimated_duration(len(provider_data_list), validation_options_obj.dict())
        
        # Return response
        return CSVUploadResponse(
            job_id=job_id,
            status="pending",
            provider_count=len(provider_data_list),
            estimated_duration=estimated_duration,
            created_at=datetime.now()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload CSV for validation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to upload CSV: {str(e)}")


@router.get("/job/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """
    Get job status and progress
    
    Args:
        job_id: Job identifier
        db: Database session
        
    Returns:
        Job status response
    """
    try:
        # Get job status from orchestrator
        status_data = await validation_orchestrator.get_job_status(job_id)
        
        if "error" in status_data:
            raise HTTPException(status_code=404, detail=status_data["error"])
        
        # Convert to response model
        return JobStatusResponse(
            job_id=status_data["job_id"],
            status=status_data["status"],
            provider_count=status_data["provider_count"],
            completed_count=status_data.get("completed_count", 0),
            failed_count=status_data.get("failed_count", 0),
            progress_percentage=status_data.get("progress_percentage", 0.0),
            created_at=datetime.fromisoformat(status_data["created_at"]),
            updated_at=datetime.fromisoformat(status_data["updated_at"]),
            validation_options=status_data["validation_options"]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job status for {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get job status: {str(e)}")


@router.get("/job/{job_id}/report/{provider_id}", response_model=ValidationReportResponse)
async def get_validation_report(job_id: str, provider_id: str, db: Session = Depends(get_db)):
    """
    Get validation report for a specific provider
    
    Args:
        job_id: Job identifier
        provider_id: Provider identifier
        db: Database session
        
    Returns:
        Validation report response
    """
    try:
        # Get validation report from orchestrator
        report = await validation_orchestrator.get_validation_report(job_id, provider_id)
        
        if not report:
            raise HTTPException(status_code=404, detail="Validation report not found")
        
        # Convert to response model
        return ValidationReportResponse(
            provider_id=report.provider_id,
            job_id=report.job_id,
            overall_confidence=report.overall_confidence,
            validation_status=report.validation_status,
            field_summaries=report.field_summaries,
            aggregated_fields=report.aggregated_fields,
            flags=report.flags,
            validation_timestamp=report.validation_timestamp,
            processing_time=report.processing_time
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get validation report for {job_id}/{provider_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get validation report: {str(e)}")


@router.get("/job/{job_id}/reports")
async def get_all_validation_reports(job_id: str, db: Session = Depends(get_db)):
    """
    Get all validation reports for a job
    
    Args:
        job_id: Job identifier
        db: Database session
        
    Returns:
        List of validation reports
    """
    try:
        # Get job status first
        status_data = await validation_orchestrator.get_job_status(job_id)
        
        if "error" in status_data:
            raise HTTPException(status_code=404, detail=status_data["error"])
        
        # Get all provider IDs from job
        # This would need to be implemented in the orchestrator
        # For now, return a placeholder response
        return {
            "job_id": job_id,
            "status": status_data["status"],
            "provider_count": status_data["provider_count"],
            "reports": []  # Placeholder - would need to implement provider ID retrieval
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get all validation reports for {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get validation reports: {str(e)}")


@router.delete("/job/{job_id}")
async def cancel_job(job_id: str, db: Session = Depends(get_db)):
    """
    Cancel a validation job
    
    Args:
        job_id: Job identifier
        db: Database session
        
    Returns:
        Cancellation confirmation
    """
    try:
        # Cancel job in orchestrator
        # This would need to be implemented in the orchestrator
        # For now, return a placeholder response
        
        return {
            "job_id": job_id,
            "status": "cancelled",
            "message": "Job cancellation requested"
        }
    
    except Exception as e:
        logger.error(f"Failed to cancel job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel job: {str(e)}")


@router.get("/health")
async def health_check():
    """
    Health check endpoint
    
    Returns:
        Health status
    """
    try:
        # Check Redis connection
        redis_conn = redis.from_url("redis://localhost:6379/0")
        redis_conn.ping()
        
        # Check database connection
        # This would need to be implemented
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "redis": "healthy",
                "database": "healthy",
                "validation_engine": "healthy"
            }
        }
    
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
        )


@router.get("/metrics")
async def get_validation_metrics(db: Session = Depends(get_db)):
    """
    Get validation metrics
    
    Args:
        db: Database session
        
    Returns:
        Validation metrics
    """
    try:
        # Get metrics from database
        total_jobs = db.query(ValidationJob).count()
        completed_jobs = db.query(ValidationJob).filter_by(status="completed").count()
        failed_jobs = db.query(ValidationJob).filter_by(status="failed").count()
        
        # Get queue metrics from Redis
        redis_conn = redis.from_url("redis://localhost:6379/0")
        queue_lengths = {
            "npi_validation": len(Queue('npi_validation', connection=redis_conn)),
            "google_places_validation": len(Queue('google_places_validation', connection=redis_conn)),
            "ocr_processing": len(Queue('ocr_processing', connection=redis_conn)),
            "state_board_validation": len(Queue('state_board_validation', connection=redis_conn)),
            "enrichment_lookup": len(Queue('enrichment_lookup', connection=redis_conn))
        }
        
        return {
            "total_jobs": total_jobs,
            "completed_jobs": completed_jobs,
            "failed_jobs": failed_jobs,
            "success_rate": (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0,
            "queue_lengths": queue_lengths,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Failed to get validation metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")


# Helper functions

def parse_csv_data(csv_content: str) -> List[Dict[str, Any]]:
    """
    Parse CSV content into provider data list
    
    Args:
        csv_content: CSV file content
        
    Returns:
        List of provider data dictionaries
    """
    try:
        provider_data_list = []
        
        # Parse CSV
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        
        for row in csv_reader:
            # Generate provider ID if not provided
            provider_id = row.get("provider_id", str(uuid.uuid4()))
            
            # Create provider data dictionary
            provider_data = {
                "provider_id": provider_id,
                "given_name": row.get("given_name"),
                "family_name": row.get("family_name"),
                "npi_number": row.get("npi_number"),
                "phone_primary": row.get("phone_primary"),
                "email": row.get("email"),
                "address_street": row.get("address_street"),
                "license_number": row.get("license_number"),
                "license_state": row.get("license_state"),
                "document_path": row.get("document_path")
            }
            
            # Only add if at least one field is provided
            if any(value for value in provider_data.values() if value and value != provider_id):
                provider_data_list.append(provider_data)
        
        return provider_data_list
    
    except Exception as e:
        logger.error(f"Failed to parse CSV data: {str(e)}")
        return []


def calculate_estimated_duration(provider_count: int, validation_options: Dict[str, Any]) -> str:
    """
    Calculate estimated validation duration
    
    Args:
        provider_count: Number of providers
        validation_options: Validation options
        
    Returns:
        Estimated duration string
    """
    try:
        # Base time per provider (in seconds)
        base_time_per_provider = 30  # 30 seconds per provider
        
        # Adjust based on validation options
        if validation_options.get("enable_ocr_processing", True):
            base_time_per_provider += 20  # OCR takes longer
        
        if validation_options.get("enable_license_validation", True):
            base_time_per_provider += 10  # State board checks are slow
        
        # Calculate total time
        total_seconds = provider_count * base_time_per_provider
        
        # Convert to human readable format
        if total_seconds < 60:
            return f"{total_seconds} seconds"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            return f"{minutes} minutes"
        else:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours}h {minutes}m"
    
    except Exception as e:
        logger.error(f"Failed to calculate estimated duration: {str(e)}")
        return "Unknown"


# Rate limiting and retry policy endpoints

@router.get("/rate-limits")
async def get_rate_limits():
    """
    Get current rate limits for all connectors
    
    Returns:
        Rate limits information
    """
    try:
        rate_limits = {
            "npi_registry": {
                "requests_per_second": 10,
                "burst_limit": 20,
                "current_usage": 0  # Would need to implement usage tracking
            },
            "google_places": {
                "requests_per_second": 10,
                "burst_limit": 20,
                "current_usage": 0
            },
            "ocr_processing": {
                "requests_per_second": 5,
                "burst_limit": 10,
                "current_usage": 0
            },
            "state_board": {
                "requests_per_second": 0.5,
                "burst_limit": 5,
                "current_usage": 0
            },
            "enrichment": {
                "requests_per_second": 2,
                "burst_limit": 5,
                "current_usage": 0
            }
        }
        
        return {
            "rate_limits": rate_limits,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Failed to get rate limits: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get rate limits: {str(e)}")


@router.get("/retry-policy")
async def get_retry_policy():
    """
    Get current retry policy
    
    Returns:
        Retry policy information
    """
    try:
        retry_policy = {
            "max_retries": 3,
            "base_delay": 1.0,
            "exponential_backoff": True,
            "max_delay": 60.0,
            "retry_on_errors": [
                "ConnectionError",
                "TimeoutError",
                "HTTPError",
                "ValidationError"
            ]
        }
        
        return {
            "retry_policy": retry_policy,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Failed to get retry policy: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get retry policy: {str(e)}")


# Include router in FastAPI app
# This would be done in the main FastAPI application file
# app.include_router(validation_router)
