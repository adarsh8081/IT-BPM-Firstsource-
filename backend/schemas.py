"""
Pydantic schemas for request/response validation
"""

from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from enum import Enum

from .models import ProviderStatus, ValidationJobStatus, ValidationJobPriority

class ProviderBase(BaseModel):
    """Base provider schema"""
    npi: str = Field(..., min_length=10, max_length=10, description="10-digit NPI number")
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    suffix: Optional[str] = Field(None, max_length=10)
    specialty: Optional[str] = Field(None, max_length=200)
    organization: Optional[str] = Field(None, max_length=200)
    organization_npi: Optional[str] = Field(None, min_length=10, max_length=10)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, min_length=2, max_length=2)
    zip_code: Optional[str] = Field(None, max_length=10)
    country: str = Field("US", min_length=2, max_length=2)
    license_number: Optional[str] = Field(None, max_length=50)
    license_state: Optional[str] = Field(None, min_length=2, max_length=2)
    license_expiry: Optional[datetime] = None

    @validator('npi')
    def validate_npi(cls, v):
        if not v.isdigit():
            raise ValueError('NPI must contain only digits')
        return v

    @validator('organization_npi')
    def validate_org_npi(cls, v):
        if v and not v.isdigit():
            raise ValueError('Organization NPI must contain only digits')
        return v

class ProviderCreate(ProviderBase):
    """Schema for creating a provider"""
    pass

class ProviderUpdate(BaseModel):
    """Schema for updating a provider"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    suffix: Optional[str] = Field(None, max_length=10)
    specialty: Optional[str] = Field(None, max_length=200)
    organization: Optional[str] = Field(None, max_length=200)
    organization_npi: Optional[str] = Field(None, min_length=10, max_length=10)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, min_length=2, max_length=2)
    zip_code: Optional[str] = Field(None, max_length=10)
    country: Optional[str] = Field(None, min_length=2, max_length=2)
    license_number: Optional[str] = Field(None, max_length=50)
    license_state: Optional[str] = Field(None, min_length=2, max_length=2)
    license_expiry: Optional[datetime] = None

class ProviderResponse(ProviderBase):
    """Schema for provider response"""
    id: UUID
    status: ProviderStatus
    validation_score: float
    last_validated: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ProviderListResponse(BaseModel):
    """Schema for paginated provider list"""
    providers: List[ProviderResponse]
    total: int
    page: int
    size: int
    pages: int

class ValidationJobBase(BaseModel):
    """Base validation job schema"""
    provider_id: UUID
    priority: ValidationJobPriority = ValidationJobPriority.MEDIUM
    validate_npi: bool = True
    validate_address: bool = True
    validate_license: bool = True

class ValidationJobCreate(ValidationJobBase):
    """Schema for creating a validation job"""
    pass

class ValidationJobResponse(ValidationJobBase):
    """Schema for validation job response"""
    id: UUID
    status: ValidationJobStatus
    progress: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    retry_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ValidationJobListResponse(BaseModel):
    """Schema for paginated validation job list"""
    jobs: List[ValidationJobResponse]
    total: int
    page: int
    size: int
    pages: int

class ValidationResultResponse(BaseModel):
    """Schema for validation result response"""
    id: UUID
    provider_id: UUID
    job_id: Optional[UUID]
    npi_valid: Optional[bool]
    npi_details: Optional[Dict[str, Any]]
    address_valid: Optional[bool]
    address_details: Optional[Dict[str, Any]]
    address_suggestions: Optional[List[Dict[str, Any]]]
    license_valid: Optional[bool]
    license_details: Optional[Dict[str, Any]]
    overall_score: Optional[float]
    validation_summary: Optional[Dict[str, Any]]
    errors: Optional[List[str]]
    warnings: Optional[List[str]]
    created_at: datetime

    class Config:
        from_attributes = True

class DashboardStats(BaseModel):
    """Schema for dashboard statistics"""
    total_providers: int
    validated_providers: int
    pending_validation: int
    validation_errors: int
    recent_validations: List[Dict[str, Any]]
    validation_trends: Dict[str, Any]
    queue_status: Dict[str, Any]

class HealthCheck(BaseModel):
    """Schema for health check response"""
    status: str
    timestamp: datetime
    version: str
    database: str
    redis: str
    services: Dict[str, str]

class ErrorResponse(BaseModel):
    """Schema for error response"""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None

class SuccessResponse(BaseModel):
    """Schema for success response"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
