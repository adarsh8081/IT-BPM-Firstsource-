"""
Dashboard endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta
import logging

from ..database import get_db
from ..models import Provider, ProviderStatus, ValidationJob, ValidationJobStatus
from ..schemas import DashboardStats, ValidationResult

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    """Get dashboard statistics"""
    try:
        # Get provider counts
        total_providers_result = await db.execute(
            select(func.count(Provider.id))
        )
        total_providers = total_providers_result.scalar() or 0

        validated_providers_result = await db.execute(
            select(func.count(Provider.id)).where(
                Provider.status == ProviderStatus.VALID
            )
        )
        validated_providers = validated_providers_result.scalar() or 0

        pending_validation_result = await db.execute(
            select(func.count(Provider.id)).where(
                Provider.status == ProviderStatus.PENDING
            )
        )
        pending_validation = pending_validation_result.scalar() or 0

        validation_errors_result = await db.execute(
            select(func.count(Provider.id)).where(
                Provider.status == ProviderStatus.INVALID
            )
        )
        validation_errors = validation_errors_result.scalar() or 0

        # Get recent validations (last 10)
        recent_validations_result = await db.execute(
            select(Provider)
            .where(Provider.last_validated.isnot(None))
            .order_by(Provider.last_validated.desc())
            .limit(10)
        )
        recent_validations = []
        for provider in recent_validations_result.scalars().all():
            recent_validations.append({
                "id": str(provider.id),
                "provider_name": f"{provider.first_name} {provider.last_name}",
                "status": provider.status.value,
                "timestamp": provider.last_validated.isoformat() if provider.last_validated else None
            })

        # Get validation trends (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        validation_trends = await _get_validation_trends(db, thirty_days_ago)

        # Get queue status
        queue_status = await _get_queue_status(db)

        return DashboardStats(
            total_providers=total_providers,
            validated_providers=validated_providers,
            pending_validation=pending_validation,
            validation_errors=validation_errors,
            recent_validations=recent_validations,
            validation_trends=validation_trends,
            queue_status=queue_status
        )
    except Exception as e:
        logger.error(f"Failed to get dashboard stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def _get_validation_trends(db: AsyncSession, since: datetime):
    """Get validation trends over time"""
    try:
        # Get daily validation counts
        daily_validations_result = await db.execute(
            select(
                func.date(ValidationResult.created_at).label('date'),
                func.count(ValidationResult.id).label('count')
            )
            .where(ValidationResult.created_at >= since)
            .group_by(func.date(ValidationResult.created_at))
            .order_by('date')
        )
        
        daily_counts = {}
        for row in daily_validations_result:
            daily_counts[row.date.isoformat()] = row.count

        # Get status distribution
        status_distribution_result = await db.execute(
            select(Provider.status, func.count(Provider.id))
            .group_by(Provider.status)
        )
        
        status_distribution = {}
        for row in status_distribution_result:
            status_distribution[row.status.value] = row.count

        return {
            "daily_validations": daily_counts,
            "status_distribution": status_distribution,
            "period": "30_days"
        }
    except Exception as e:
        logger.error(f"Failed to get validation trends: {e}")
        return {"daily_validations": {}, "status_distribution": {}, "period": "30_days"}

async def _get_queue_status(db: AsyncSession):
    """Get validation queue status"""
    try:
        # Get job counts by status
        pending_jobs_result = await db.execute(
            select(func.count(ValidationJob.id)).where(
                ValidationJob.status == ValidationJobStatus.PENDING
            )
        )
        pending_jobs = pending_jobs_result.scalar() or 0

        running_jobs_result = await db.execute(
            select(func.count(ValidationJob.id)).where(
                ValidationJob.status == ValidationJobStatus.RUNNING
            )
        )
        running_jobs = running_jobs_result.scalar() or 0

        completed_jobs_result = await db.execute(
            select(func.count(ValidationJob.id)).where(
                ValidationJob.status == ValidationJobStatus.COMPLETED
            )
        )
        completed_jobs = completed_jobs_result.scalar() or 0

        failed_jobs_result = await db.execute(
            select(func.count(ValidationJob.id)).where(
                ValidationJob.status == ValidationJobStatus.FAILED
            )
        )
        failed_jobs = failed_jobs_result.scalar() or 0

        return {
            "pending": pending_jobs,
            "running": running_jobs,
            "completed": completed_jobs,
            "failed": failed_jobs,
            "total": pending_jobs + running_jobs + completed_jobs + failed_jobs
        }
    except Exception as e:
        logger.error(f"Failed to get queue status: {e}")
        return {"pending": 0, "running": 0, "completed": 0, "failed": 0, "total": 0}

@router.get("/analytics/validation-performance")
async def get_validation_performance(db: AsyncSession = Depends(get_db)):
    """Get validation performance analytics"""
    try:
        # Get average validation time
        avg_validation_time_result = await db.execute(
            select(
                func.avg(
                    func.extract('epoch', ValidationJob.completed_at - ValidationJob.started_at)
                )
            )
            .where(
                and_(
                    ValidationJob.completed_at.isnot(None),
                    ValidationJob.started_at.isnot(None)
                )
            )
        )
        avg_validation_time = avg_validation_time_result.scalar() or 0

        # Get success rate
        total_completed_result = await db.execute(
            select(func.count(ValidationJob.id)).where(
                ValidationJob.status.in_([
                    ValidationJobStatus.COMPLETED,
                    ValidationJobStatus.FAILED
                ])
            )
        )
        total_completed = total_completed_result.scalar() or 0

        successful_result = await db.execute(
            select(func.count(ValidationJob.id)).where(
                ValidationJob.status == ValidationJobStatus.COMPLETED
            )
        )
        successful = successful_result.scalar() or 0

        success_rate = (successful / total_completed * 100) if total_completed > 0 else 0

        # Get retry statistics
        retry_stats_result = await db.execute(
            select(
                ValidationJob.retry_count,
                func.count(ValidationJob.id)
            )
            .group_by(ValidationJob.retry_count)
        )
        
        retry_stats = {}
        for row in retry_stats_result:
            retry_stats[f"retry_{row.retry_count}"] = row.count

        return {
            "average_validation_time_seconds": float(avg_validation_time),
            "success_rate_percentage": float(success_rate),
            "total_completed_jobs": total_completed,
            "retry_statistics": retry_stats
        }
    except Exception as e:
        logger.error(f"Failed to get validation performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))
