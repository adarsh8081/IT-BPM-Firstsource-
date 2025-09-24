"""
Validation endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
import logging

from ..database import get_db
from ..models import ValidationJobStatus, ValidationJobPriority
from ..schemas import (
    ValidationJobCreate, ValidationJobResponse, ValidationJobListResponse,
    ValidationResultResponse, SuccessResponse
)
from ..services import ValidationService

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/jobs", response_model=ValidationJobResponse)
async def create_validation_job(
    job_data: ValidationJobCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Create a new validation job"""
    try:
        validation_service = ValidationService(db)
        job = await validation_service.create_validation_job(job_data)
        
        # Start validation in background
        background_tasks.add_task(
            validation_service.process_validation_job,
            job.id
        )
        
        return job
    except Exception as e:
        logger.error(f"Failed to create validation job: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/jobs", response_model=ValidationJobListResponse)
async def list_validation_jobs(
    page: int = 1,
    size: int = 10,
    status: Optional[ValidationJobStatus] = None,
    db: AsyncSession = Depends(get_db)
):
    """List validation jobs"""
    try:
        validation_service = ValidationService(db)
        result = await validation_service.list_validation_jobs(
            page=page, size=size, status=status
        )
        return result
    except Exception as e:
        logger.error(f"Failed to list validation jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/jobs/{job_id}", response_model=ValidationJobResponse)
async def get_validation_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific validation job"""
    try:
        validation_service = ValidationService(db)
        job = await validation_service.get_validation_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Validation job not found")
        return job
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get validation job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/jobs/{job_id}/retry", response_model=SuccessResponse)
async def retry_validation_job(
    job_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Retry a failed validation job"""
    try:
        validation_service = ValidationService(db)
        success = await validation_service.retry_validation_job(job_id)
        if not success:
            raise HTTPException(status_code=404, detail="Validation job not found")
        
        # Restart validation in background
        background_tasks.add_task(
            validation_service.process_validation_job,
            job_id
        )
        
        return SuccessResponse(success=True, message="Validation job restarted")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retry validation job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/jobs/{job_id}/cancel", response_model=SuccessResponse)
async def cancel_validation_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Cancel a validation job"""
    try:
        validation_service = ValidationService(db)
        success = await validation_service.cancel_validation_job(job_id)
        if not success:
            raise HTTPException(status_code=404, detail="Validation job not found")
        return SuccessResponse(success=True, message="Validation job cancelled")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel validation job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/results/{provider_id}", response_model=List[ValidationResultResponse])
async def get_validation_results(
    provider_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get validation results for a provider"""
    try:
        validation_service = ValidationService(db)
        results = await validation_service.get_validation_results(provider_id)
        return results
    except Exception as e:
        logger.error(f"Failed to get validation results for {provider_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/results/job/{job_id}", response_model=ValidationResultResponse)
async def get_job_validation_result(
    job_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get validation result for a specific job"""
    try:
        validation_service = ValidationService(db)
        result = await validation_service.get_job_validation_result(job_id)
        if not result:
            raise HTTPException(status_code=404, detail="Validation result not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get validation result for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/bulk", response_model=SuccessResponse)
async def create_bulk_validation_jobs(
    provider_ids: List[UUID],
    priority: ValidationJobPriority = ValidationJobPriority.MEDIUM,
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db)
):
    """Create validation jobs for multiple providers"""
    try:
        validation_service = ValidationService(db)
        result = await validation_service.create_bulk_validation_jobs(
            provider_ids, priority
        )
        
        # Start all validations in background
        for job_id in result['job_ids']:
            background_tasks.add_task(
                validation_service.process_validation_job,
                job_id
            )
        
        return SuccessResponse(
            success=True,
            message=f"Created {len(result['job_ids'])} validation jobs",
            data=result
        )
    except Exception as e:
        logger.error(f"Failed to create bulk validation jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/queue/status")
async def get_queue_status(db: AsyncSession = Depends(get_db)):
    """Get validation queue status"""
    try:
        validation_service = ValidationService(db)
        status = await validation_service.get_queue_status()
        return status
    except Exception as e:
        logger.error(f"Failed to get queue status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
