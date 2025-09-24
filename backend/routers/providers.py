"""
Provider management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import Optional, List
from uuid import UUID
import logging

from ..database import get_db
from ..models import Provider, ProviderStatus
from ..schemas import (
    ProviderCreate, ProviderUpdate, ProviderResponse, 
    ProviderListResponse, SuccessResponse
)
from ..services import ProviderService

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/", response_model=ProviderResponse)
async def create_provider(
    provider_data: ProviderCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new provider"""
    try:
        provider_service = ProviderService(db)
        provider = await provider_service.create_provider(provider_data)
        return provider
    except Exception as e:
        logger.error(f"Failed to create provider: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=ProviderListResponse)
async def list_providers(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    status: Optional[ProviderStatus] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """List providers with pagination and filtering"""
    try:
        provider_service = ProviderService(db)
        result = await provider_service.list_providers(
            page=page, size=size, search=search, status=status
        )
        return result
    except Exception as e:
        logger.error(f"Failed to list providers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{provider_id}", response_model=ProviderResponse)
async def get_provider(
    provider_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific provider by ID"""
    try:
        provider_service = ProviderService(db)
        provider = await provider_service.get_provider(provider_id)
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")
        return provider
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get provider {provider_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{provider_id}", response_model=ProviderResponse)
async def update_provider(
    provider_id: UUID,
    provider_data: ProviderUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a provider"""
    try:
        provider_service = ProviderService(db)
        provider = await provider_service.update_provider(provider_id, provider_data)
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")
        return provider
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update provider {provider_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{provider_id}", response_model=SuccessResponse)
async def delete_provider(
    provider_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a provider"""
    try:
        provider_service = ProviderService(db)
        success = await provider_service.delete_provider(provider_id)
        if not success:
            raise HTTPException(status_code=404, detail="Provider not found")
        return SuccessResponse(success=True, message="Provider deleted successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete provider {provider_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/npi/{npi}", response_model=ProviderResponse)
async def get_provider_by_npi(
    npi: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a provider by NPI number"""
    try:
        provider_service = ProviderService(db)
        provider = await provider_service.get_provider_by_npi(npi)
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")
        return provider
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get provider by NPI {npi}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/bulk", response_model=SuccessResponse)
async def create_bulk_providers(
    providers_data: List[ProviderCreate],
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Create multiple providers in bulk"""
    try:
        provider_service = ProviderService(db)
        result = await provider_service.create_bulk_providers(providers_data)
        return SuccessResponse(
            success=True, 
            message=f"Created {result['created']} providers, {result['failed']} failed",
            data=result
        )
    except Exception as e:
        logger.error(f"Failed to create bulk providers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/export/csv")
async def export_providers_csv(
    status: Optional[ProviderStatus] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Export providers to CSV"""
    try:
        provider_service = ProviderService(db)
        csv_data = await provider_service.export_providers_csv(status)
        return {"csv_data": csv_data}
    except Exception as e:
        logger.error(f"Failed to export providers: {e}")
        raise HTTPException(status_code=500, detail=str(e))
