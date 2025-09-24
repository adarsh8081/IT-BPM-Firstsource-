"""
Provider service for managing provider data
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Dict, Any
from uuid import UUID
import logging
import csv
import io

from ..models import Provider, ProviderStatus
from ..schemas import ProviderCreate, ProviderUpdate, ProviderResponse, ProviderListResponse

logger = logging.getLogger(__name__)

class ProviderService:
    """Service for provider operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_provider(self, provider_data: ProviderCreate) -> ProviderResponse:
        """Create a new provider"""
        try:
            # Check if provider with NPI already exists
            existing_provider = await self.get_provider_by_npi(provider_data.npi)
            if existing_provider:
                raise ValueError(f"Provider with NPI {provider_data.npi} already exists")
            
            # Create provider instance
            provider = Provider(**provider_data.dict())
            self.db.add(provider)
            await self.db.commit()
            await self.db.refresh(provider)
            
            logger.info(f"Created provider {provider.id} with NPI {provider.npi}")
            return ProviderResponse.from_orm(provider)
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create provider: {e}")
            raise

    async def get_provider(self, provider_id: UUID) -> Optional[ProviderResponse]:
        """Get provider by ID"""
        try:
            result = await self.db.execute(
                select(Provider).where(Provider.id == provider_id)
            )
            provider = result.scalar_one_or_none()
            
            if provider:
                return ProviderResponse.from_orm(provider)
            return None
        except Exception as e:
            logger.error(f"Failed to get provider {provider_id}: {e}")
            raise

    async def get_provider_by_npi(self, npi: str) -> Optional[ProviderResponse]:
        """Get provider by NPI"""
        try:
            result = await self.db.execute(
                select(Provider).where(Provider.npi == npi)
            )
            provider = result.scalar_one_or_none()
            
            if provider:
                return ProviderResponse.from_orm(provider)
            return None
        except Exception as e:
            logger.error(f"Failed to get provider by NPI {npi}: {e}")
            raise

    async def update_provider(self, provider_id: UUID, provider_data: ProviderUpdate) -> Optional[ProviderResponse]:
        """Update provider"""
        try:
            result = await self.db.execute(
                select(Provider).where(Provider.id == provider_id)
            )
            provider = result.scalar_one_or_none()
            
            if not provider:
                return None
            
            # Update fields
            update_data = provider_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(provider, field, value)
            
            await self.db.commit()
            await self.db.refresh(provider)
            
            logger.info(f"Updated provider {provider_id}")
            return ProviderResponse.from_orm(provider)
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update provider {provider_id}: {e}")
            raise

    async def delete_provider(self, provider_id: UUID) -> bool:
        """Delete provider"""
        try:
            result = await self.db.execute(
                select(Provider).where(Provider.id == provider_id)
            )
            provider = result.scalar_one_or_none()
            
            if not provider:
                return False
            
            await self.db.delete(provider)
            await self.db.commit()
            
            logger.info(f"Deleted provider {provider_id}")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to delete provider {provider_id}: {e}")
            raise

    async def list_providers(
        self, 
        page: int = 1, 
        size: int = 10, 
        search: Optional[str] = None,
        status: Optional[ProviderStatus] = None
    ) -> ProviderListResponse:
        """List providers with pagination and filtering"""
        try:
            # Build query
            query = select(Provider)
            
            # Add filters
            filters = []
            if search:
                search_filter = or_(
                    Provider.first_name.ilike(f"%{search}%"),
                    Provider.last_name.ilike(f"%{search}%"),
                    Provider.npi.ilike(f"%{search}%"),
                    Provider.specialty.ilike(f"%{search}%"),
                    Provider.organization.ilike(f"%{search}%")
                )
                filters.append(search_filter)
            
            if status:
                filters.append(Provider.status == status)
            
            if filters:
                query = query.where(and_(*filters))
            
            # Get total count
            count_query = select(func.count(Provider.id))
            if filters:
                count_query = count_query.where(and_(*filters))
            
            total_result = await self.db.execute(count_query)
            total = total_result.scalar() or 0
            
            # Add pagination
            offset = (page - 1) * size
            query = query.offset(offset).limit(size).order_by(Provider.created_at.desc())
            
            # Execute query
            result = await self.db.execute(query)
            providers = result.scalars().all()
            
            # Convert to response format
            provider_responses = [ProviderResponse.from_orm(p) for p in providers]
            
            return ProviderListResponse(
                providers=provider_responses,
                total=total,
                page=page,
                size=size,
                pages=(total + size - 1) // size
            )
        except Exception as e:
            logger.error(f"Failed to list providers: {e}")
            raise

    async def create_bulk_providers(self, providers_data: List[ProviderCreate]) -> Dict[str, Any]:
        """Create multiple providers in bulk"""
        try:
            created = 0
            failed = 0
            errors = []
            
            for provider_data in providers_data:
                try:
                    # Check if provider already exists
                    existing = await self.get_provider_by_npi(provider_data.npi)
                    if existing:
                        failed += 1
                        errors.append(f"Provider with NPI {provider_data.npi} already exists")
                        continue
                    
                    # Create provider
                    provider = Provider(**provider_data.dict())
                    self.db.add(provider)
                    created += 1
                    
                except Exception as e:
                    failed += 1
                    errors.append(f"NPI {provider_data.npi}: {str(e)}")
            
            # Commit all changes
            await self.db.commit()
            
            logger.info(f"Bulk created {created} providers, {failed} failed")
            return {
                "created": created,
                "failed": failed,
                "errors": errors
            }
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create bulk providers: {e}")
            raise

    async def export_providers_csv(self, status: Optional[ProviderStatus] = None) -> str:
        """Export providers to CSV format"""
        try:
            # Build query
            query = select(Provider)
            if status:
                query = query.where(Provider.status == status)
            
            result = await self.db.execute(query)
            providers = result.scalars().all()
            
            # Create CSV
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                'ID', 'NPI', 'First Name', 'Last Name', 'Middle Name', 'Suffix',
                'Specialty', 'Organization', 'Organization NPI', 'Email', 'Phone',
                'Address Line 1', 'Address Line 2', 'City', 'State', 'ZIP Code',
                'Country', 'License Number', 'License State', 'License Expiry',
                'Status', 'Validation Score', 'Last Validated', 'Created At', 'Updated At'
            ])
            
            # Write data
            for provider in providers:
                writer.writerow([
                    str(provider.id),
                    provider.npi,
                    provider.first_name,
                    provider.last_name,
                    provider.middle_name,
                    provider.suffix,
                    provider.specialty,
                    provider.organization,
                    provider.organization_npi,
                    provider.email,
                    provider.phone,
                    provider.address_line1,
                    provider.address_line2,
                    provider.city,
                    provider.state,
                    provider.zip_code,
                    provider.country,
                    provider.license_number,
                    provider.license_state,
                    provider.license_expiry.isoformat() if provider.license_expiry else None,
                    provider.status.value,
                    provider.validation_score,
                    provider.last_validated.isoformat() if provider.last_validated else None,
                    provider.created_at.isoformat(),
                    provider.updated_at.isoformat()
                ])
            
            return output.getvalue()
        except Exception as e:
            logger.error(f"Failed to export providers CSV: {e}")
            raise
