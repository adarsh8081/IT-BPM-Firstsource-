"""
Health check endpoints
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import redis
import logging

from ..database import get_db
from ..config import settings
from ..schemas import HealthCheck

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/", response_model=HealthCheck)
async def health_check():
    """Basic health check endpoint"""
    return HealthCheck(
        status="healthy",
        timestamp=datetime.utcnow(),
        version="1.0.0",
        database="unknown",
        redis="unknown",
        services={}
    )

@router.get("/detailed", response_model=HealthCheck)
async def detailed_health_check(db: AsyncSession = Depends(get_db)):
    """Detailed health check with service status"""
    services = {}
    
    # Check database
    try:
        await db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"
    
    # Check Redis
    try:
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        redis_status = "healthy"
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        redis_status = "unhealthy"
    
    # Check external services (mock for now)
    services = {
        "npi_registry": "healthy",
        "google_places": "healthy",
        "state_boards": "degraded"
    }
    
    overall_status = "healthy"
    if db_status == "unhealthy" or redis_status == "unhealthy":
        overall_status = "unhealthy"
    
    return HealthCheck(
        status=overall_status,
        timestamp=datetime.utcnow(),
        version="1.0.0",
        database=db_status,
        redis=redis_status,
        services=services
    )

@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """Readiness check for Kubernetes"""
    try:
        await db.execute("SELECT 1")
        return {"status": "ready"}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {"status": "not ready", "error": str(e)}

@router.get("/live")
async def liveness_check():
    """Liveness check for Kubernetes"""
    return {"status": "alive"}
