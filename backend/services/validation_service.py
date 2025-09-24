"""
Validation service for managing validation jobs and results
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
import logging
import asyncio

from ..models import (
    Provider, ValidationJob, ValidationResult, 
    ValidationJobStatus, ValidationJobPriority, ProviderStatus
)
from ..schemas import (
    ValidationJobCreate, ValidationJobResponse, ValidationJobListResponse,
    ValidationResultResponse
)
from ..connectors import NpiConnector, GooglePlacesConnector, StateBoardConnector

logger = logging.getLogger(__name__)

class ValidationService:
    """Service for validation operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.npi_connector = NpiConnector()
        self.google_places_connector = GooglePlacesConnector()
        self.state_board_connector = StateBoardConnector()

    async def create_validation_job(self, job_data: ValidationJobCreate) -> ValidationJobResponse:
        """Create a new validation job"""
        try:
            # Verify provider exists
            provider_result = await self.db.execute(
                select(Provider).where(Provider.id == job_data.provider_id)
            )
            provider = provider_result.scalar_one_or_none()
            if not provider:
                raise ValueError(f"Provider {job_data.provider_id} not found")
            
            # Create validation job
            job = ValidationJob(**job_data.dict())
            self.db.add(job)
            await self.db.commit()
            await self.db.refresh(job)
            
            logger.info(f"Created validation job {job.id} for provider {job_data.provider_id}")
            return ValidationJobResponse.from_orm(job)
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create validation job: {e}")
            raise

    async def get_validation_job(self, job_id: UUID) -> Optional[ValidationJobResponse]:
        """Get validation job by ID"""
        try:
            result = await self.db.execute(
                select(ValidationJob).where(ValidationJob.id == job_id)
            )
            job = result.scalar_one_or_none()
            
            if job:
                return ValidationJobResponse.from_orm(job)
            return None
        except Exception as e:
            logger.error(f"Failed to get validation job {job_id}: {e}")
            raise

    async def list_validation_jobs(
        self, 
        page: int = 1, 
        size: int = 10, 
        status: Optional[ValidationJobStatus] = None
    ) -> ValidationJobListResponse:
        """List validation jobs with pagination"""
        try:
            # Build query
            query = select(ValidationJob)
            
            if status:
                query = query.where(ValidationJob.status == status)
            
            # Get total count
            count_query = select(func.count(ValidationJob.id))
            if status:
                count_query = count_query.where(ValidationJob.status == status)
            
            total_result = await self.db.execute(count_query)
            total = total_result.scalar() or 0
            
            # Add pagination
            offset = (page - 1) * size
            query = query.offset(offset).limit(size).order_by(ValidationJob.created_at.desc())
            
            # Execute query
            result = await self.db.execute(query)
            jobs = result.scalars().all()
            
            # Convert to response format
            job_responses = [ValidationJobResponse.from_orm(j) for j in jobs]
            
            return ValidationJobListResponse(
                jobs=job_responses,
                total=total,
                page=page,
                size=size,
                pages=(total + size - 1) // size
            )
        except Exception as e:
            logger.error(f"Failed to list validation jobs: {e}")
            raise

    async def process_validation_job(self, job_id: UUID):
        """Process a validation job"""
        try:
            # Get job
            result = await self.db.execute(
                select(ValidationJob).where(ValidationJob.id == job_id)
            )
            job = result.scalar_one_or_none()
            if not job:
                logger.error(f"Validation job {job_id} not found")
                return
            
            # Get provider
            provider_result = await self.db.execute(
                select(Provider).where(Provider.id == job.provider_id)
            )
            provider = provider_result.scalar_one_or_none()
            if not provider:
                logger.error(f"Provider {job.provider_id} not found")
                return
            
            # Update job status
            job.status = ValidationJobStatus.RUNNING
            job.started_at = datetime.utcnow()
            job.progress = 0
            await self.db.commit()
            
            logger.info(f"Starting validation job {job_id} for provider {provider.npi}")
            
            # Initialize validation result
            validation_result = ValidationResult(
                provider_id=provider.id,
                job_id=job.id
            )
            
            errors = []
            warnings = []
            
            # NPI Validation
            if job.validate_npi:
                try:
                    job.progress = 25
                    await self.db.commit()
                    
                    npi_result = await self.npi_connector.validate_npi(provider.npi)
                    validation_result.npi_valid = npi_result['valid']
                    validation_result.npi_details = npi_result
                    
                    if not npi_result['valid']:
                        errors.append(f"NPI validation failed: {npi_result.get('error', 'Unknown error')}")
                    
                except Exception as e:
                    logger.error(f"NPI validation failed for {provider.npi}: {e}")
                    validation_result.npi_valid = False
                    validation_result.npi_details = {'error': str(e)}
                    errors.append(f"NPI validation error: {str(e)}")
            
            # Address Validation
            if job.validate_address:
                try:
                    job.progress = 50
                    await self.db.commit()
                    
                    address_result = await self.google_places_connector.validate_address(
                        provider.address_line1,
                        provider.city,
                        provider.state,
                        provider.zip_code
                    )
                    validation_result.address_valid = address_result['valid']
                    validation_result.address_details = address_result
                    validation_result.address_suggestions = address_result.get('suggestions', [])
                    
                    if not address_result['valid']:
                        warnings.append(f"Address validation warning: {address_result.get('message', 'Address not found')}")
                    
                except Exception as e:
                    logger.error(f"Address validation failed for {provider.npi}: {e}")
                    validation_result.address_valid = False
                    validation_result.address_details = {'error': str(e)}
                    warnings.append(f"Address validation error: {str(e)}")
            
            # License Validation
            if job.validate_license:
                try:
                    job.progress = 75
                    await self.db.commit()
                    
                    license_result = await self.state_board_connector.validate_license(
                        provider.license_number,
                        provider.license_state
                    )
                    validation_result.license_valid = license_result['valid']
                    validation_result.license_details = license_result
                    
                    if not license_result['valid']:
                        errors.append(f"License validation failed: {license_result.get('error', 'License not found')}")
                    
                except Exception as e:
                    logger.error(f"License validation failed for {provider.npi}: {e}")
                    validation_result.license_valid = False
                    validation_result.license_details = {'error': str(e)}
                    warnings.append(f"License validation error: {str(e)}")
            
            # Calculate overall score
            total_validations = sum([
                job.validate_npi,
                job.validate_address,
                job.validate_license
            ])
            
            valid_count = sum([
                validation_result.npi_valid if job.validate_npi else True,
                validation_result.address_valid if job.validate_address else True,
                validation_result.license_valid if job.validate_license else True
            ])
            
            overall_score = (valid_count / total_validations * 100) if total_validations > 0 else 0
            validation_result.overall_score = overall_score
            
            # Update provider status
            if overall_score >= 80:
                provider.status = ProviderStatus.VALID
            elif overall_score >= 60:
                provider.status = ProviderStatus.WARNING
            else:
                provider.status = ProviderStatus.INVALID
            
            provider.validation_score = overall_score
            provider.last_validated = datetime.utcnow()
            
            # Save validation result
            validation_result.errors = errors
            validation_result.warnings = warnings
            validation_result.validation_summary = {
                'total_validations': total_validations,
                'valid_count': valid_count,
                'overall_score': overall_score,
                'completed_at': datetime.utcnow().isoformat()
            }
            
            self.db.add(validation_result)
            
            # Update job
            job.status = ValidationJobStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            job.progress = 100
            
            await self.db.commit()
            
            logger.info(f"Completed validation job {job_id} with score {overall_score}")
            
        except Exception as e:
            logger.error(f"Validation job {job_id} failed: {e}")
            
            # Update job status to failed
            try:
                result = await self.db.execute(
                    select(ValidationJob).where(ValidationJob.id == job_id)
                )
                job = result.scalar_one_or_none()
                if job:
                    job.status = ValidationJobStatus.FAILED
                    job.error_message = str(e)
                    job.completed_at = datetime.utcnow()
                    await self.db.commit()
            except Exception as commit_error:
                logger.error(f"Failed to update job status after error: {commit_error}")

    async def retry_validation_job(self, job_id: UUID) -> bool:
        """Retry a failed validation job"""
        try:
            result = await self.db.execute(
                select(ValidationJob).where(ValidationJob.id == job_id)
            )
            job = result.scalar_one_or_none()
            
            if not job:
                return False
            
            if job.status != ValidationJobStatus.FAILED:
                raise ValueError("Can only retry failed jobs")
            
            # Reset job status
            job.status = ValidationJobStatus.PENDING
            job.started_at = None
            job.completed_at = None
            job.error_message = None
            job.retry_count += 1
            job.progress = 0
            
            await self.db.commit()
            
            logger.info(f"Retried validation job {job_id}")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to retry validation job {job_id}: {e}")
            raise

    async def cancel_validation_job(self, job_id: UUID) -> bool:
        """Cancel a validation job"""
        try:
            result = await self.db.execute(
                select(ValidationJob).where(ValidationJob.id == job_id)
            )
            job = result.scalar_one_or_none()
            
            if not job:
                return False
            
            if job.status in [ValidationJobStatus.COMPLETED, ValidationJobStatus.FAILED]:
                raise ValueError("Cannot cancel completed or failed jobs")
            
            job.status = ValidationJobStatus.CANCELLED
            job.completed_at = datetime.utcnow()
            
            await self.db.commit()
            
            logger.info(f"Cancelled validation job {job_id}")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to cancel validation job {job_id}: {e}")
            raise

    async def get_validation_results(self, provider_id: UUID) -> List[ValidationResultResponse]:
        """Get validation results for a provider"""
        try:
            result = await self.db.execute(
                select(ValidationResult)
                .where(ValidationResult.provider_id == provider_id)
                .order_by(ValidationResult.created_at.desc())
            )
            results = result.scalars().all()
            
            return [ValidationResultResponse.from_orm(r) for r in results]
        except Exception as e:
            logger.error(f"Failed to get validation results for {provider_id}: {e}")
            raise

    async def get_job_validation_result(self, job_id: UUID) -> Optional[ValidationResultResponse]:
        """Get validation result for a specific job"""
        try:
            result = await self.db.execute(
                select(ValidationResult).where(ValidationResult.job_id == job_id)
            )
            validation_result = result.scalar_one_or_none()
            
            if validation_result:
                return ValidationResultResponse.from_orm(validation_result)
            return None
        except Exception as e:
            logger.error(f"Failed to get validation result for job {job_id}: {e}")
            raise

    async def create_bulk_validation_jobs(
        self, 
        provider_ids: List[UUID], 
        priority: ValidationJobPriority = ValidationJobPriority.MEDIUM
    ) -> Dict[str, Any]:
        """Create validation jobs for multiple providers"""
        try:
            job_ids = []
            
            for provider_id in provider_ids:
                job_data = ValidationJobCreate(
                    provider_id=provider_id,
                    priority=priority
                )
                
                job = ValidationJob(**job_data.dict())
                self.db.add(job)
                job_ids.append(job.id)
            
            await self.db.commit()
            
            logger.info(f"Created {len(job_ids)} validation jobs")
            return {"job_ids": job_ids}
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create bulk validation jobs: {e}")
            raise

    async def get_queue_status(self) -> Dict[str, Any]:
        """Get validation queue status"""
        try:
            # Get job counts by status
            pending_result = await self.db.execute(
                select(func.count(ValidationJob.id)).where(
                    ValidationJob.status == ValidationJobStatus.PENDING
                )
            )
            pending = pending_result.scalar() or 0
            
            running_result = await self.db.execute(
                select(func.count(ValidationJob.id)).where(
                    ValidationJob.status == ValidationJobStatus.RUNNING
                )
            )
            running = running_result.scalar() or 0
            
            completed_result = await self.db.execute(
                select(func.count(ValidationJob.id)).where(
                    ValidationJob.status == ValidationJobStatus.COMPLETED
                )
            )
            completed = completed_result.scalar() or 0
            
            failed_result = await self.db.execute(
                select(func.count(ValidationJob.id)).where(
                    ValidationJob.status == ValidationJobStatus.FAILED
                )
            )
            failed = failed_result.scalar() or 0
            
            return {
                "pending": pending,
                "running": running,
                "completed": completed,
                "failed": failed,
                "total": pending + running + completed + failed
            }
        except Exception as e:
            logger.error(f"Failed to get queue status: {e}")
            raise
