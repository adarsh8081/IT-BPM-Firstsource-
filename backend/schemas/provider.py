"""
Pydantic schemas for the precise provider model
"""

from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

class ProviderBase(BaseModel):
    """Base provider schema with all fields"""
    
    # Personal information
    given_name: str = Field(..., min_length=1, max_length=100, description="Provider's given (first) name")
    family_name: str = Field(..., min_length=1, max_length=100, description="Provider's family (last) name")
    
    # Professional identifiers
    npi_number: str = Field(..., min_length=10, max_length=10, description="10-digit National Provider Identifier")
    primary_taxonomy: Optional[str] = Field(None, max_length=200, description="Primary medical specialty/taxonomy code")
    practice_name: Optional[str] = Field(None, max_length=200, description="Name of practice or organization")
    
    # Address information
    address_street: Optional[str] = Field(None, max_length=255, description="Street address line")
    address_city: Optional[str] = Field(None, max_length=100, description="City name")
    address_state: Optional[str] = Field(None, min_length=2, max_length=2, description="State abbreviation (2 characters)")
    address_zip: Optional[str] = Field(None, max_length=10, description="ZIP/postal code")
    place_id: Optional[str] = Field(None, max_length=255, description="Google Places API place ID")
    
    # Contact information
    phone_primary: Optional[str] = Field(None, max_length=20, description="Primary phone number")
    phone_alt: Optional[str] = Field(None, max_length=20, description="Alternative phone number")
    email: Optional[EmailStr] = Field(None, description="Primary email address")
    
    # License information
    license_number: Optional[str] = Field(None, max_length=50, description="Medical license number")
    license_state: Optional[str] = Field(None, min_length=2, max_length=2, description="State where license is issued")
    license_status: Optional[str] = Field(None, max_length=20, description="License status")
    
    # Professional relationships
    affiliations: Optional[List[Dict[str, Any]]] = Field(None, description="JSON array of organization affiliations")
    
    # Services and capabilities
    services_offered: Optional[Dict[str, Any]] = Field(None, description="JSON object of services offered by provider")

    @validator('npi_number')
    def validate_npi_number(cls, v):
        if not v.isdigit():
            raise ValueError('NPI number must contain only digits')
        return v

    @validator('address_state')
    def validate_state(cls, v):
        if v and not v.isupper():
            raise ValueError('State must be uppercase')
        return v

    @validator('license_state')
    def validate_license_state(cls, v):
        if v and not v.isupper():
            raise ValueError('License state must be uppercase')
        return v

class ProviderCreate(ProviderBase):
    """Schema for creating a new provider"""
    pass

class ProviderUpdate(BaseModel):
    """Schema for updating a provider - all fields optional"""
    
    given_name: Optional[str] = Field(None, min_length=1, max_length=100)
    family_name: Optional[str] = Field(None, min_length=1, max_length=100)
    npi_number: Optional[str] = Field(None, min_length=10, max_length=10)
    primary_taxonomy: Optional[str] = Field(None, max_length=200)
    practice_name: Optional[str] = Field(None, max_length=200)
    address_street: Optional[str] = Field(None, max_length=255)
    address_city: Optional[str] = Field(None, max_length=100)
    address_state: Optional[str] = Field(None, min_length=2, max_length=2)
    address_zip: Optional[str] = Field(None, max_length=10)
    place_id: Optional[str] = Field(None, max_length=255)
    phone_primary: Optional[str] = Field(None, max_length=20)
    phone_alt: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    license_number: Optional[str] = Field(None, max_length=50)
    license_state: Optional[str] = Field(None, min_length=2, max_length=2)
    license_status: Optional[str] = Field(None, max_length=20)
    affiliations: Optional[List[Dict[str, Any]]] = None
    services_offered: Optional[Dict[str, Any]] = None

class ProviderResponse(ProviderBase):
    """Schema for provider response with all fields"""
    
    provider_id: UUID
    last_validated_at: Optional[datetime]
    validated_by: Optional[str]
    overall_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    field_confidence: Optional[Dict[str, Any]]
    flags: Optional[List[Dict[str, Any]]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ProviderListResponse(BaseModel):
    """Schema for paginated provider list response"""
    
    providers: List[ProviderResponse]
    total: int
    page: int
    size: int
    pages: int

class ValidationFlag(BaseModel):
    """Schema for validation flags"""
    
    code: str = Field(..., description="Flag code identifier")
    reason: Optional[str] = Field(None, description="Human-readable reason")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class FieldConfidence(BaseModel):
    """Schema for field-level confidence scores"""
    
    score: float = Field(..., ge=0.0, le=1.0, description="Confidence score for the field")
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ProviderValidationUpdate(BaseModel):
    """Schema for updating provider validation data"""
    
    validated_by: Optional[str] = None
    overall_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    field_confidence: Optional[Dict[str, FieldConfidence]] = None
    flags: Optional[List[ValidationFlag]] = None

class ProviderSearchFilters(BaseModel):
    """Schema for provider search filters"""
    
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    npi_number: Optional[str] = None
    primary_taxonomy: Optional[str] = None
    practice_name: Optional[str] = None
    address_state: Optional[str] = None
    license_state: Optional[str] = None
    license_status: Optional[str] = None
    min_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    validated_since: Optional[datetime] = None

class ProviderBulkCreate(BaseModel):
    """Schema for bulk provider creation"""
    
    providers: List[ProviderCreate] = Field(..., min_items=1, max_items=1000)

class ProviderBulkUpdate(BaseModel):
    """Schema for bulk provider updates"""
    
    provider_ids: List[UUID] = Field(..., min_items=1, max_items=1000)
    updates: ProviderUpdate

class ProviderStats(BaseModel):
    """Schema for provider statistics"""
    
    total_providers: int
    validated_providers: int
    providers_by_state: Dict[str, int]
    providers_by_taxonomy: Dict[str, int]
    average_confidence: float
    validation_status_counts: Dict[str, int]
