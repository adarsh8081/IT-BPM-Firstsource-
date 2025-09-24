"""
SQLAlchemy models for the Provider Validation system
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON, Float, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from enum import Enum

from .database import Base

class ProviderStatus(str, Enum):
    """Provider validation status"""
    PENDING = "pending"
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"

class ValidationJobStatus(str, Enum):
    """Validation job status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ValidationJobPriority(str, Enum):
    """Validation job priority"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class Provider(Base):
    """Provider model"""
    __tablename__ = "providers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    npi = Column(String(10), unique=True, nullable=False, index=True)
    
    # Personal Information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    middle_name = Column(String(100), nullable=True)
    suffix = Column(String(10), nullable=True)
    
    # Professional Information
    specialty = Column(String(200), nullable=True)
    organization = Column(String(200), nullable=True)
    organization_npi = Column(String(10), nullable=True)
    
    # Contact Information
    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    
    # Address Information
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(2), nullable=True)
    zip_code = Column(String(10), nullable=True)
    country = Column(String(2), default="US")
    
    # License Information
    license_number = Column(String(50), nullable=True)
    license_state = Column(String(2), nullable=True)
    license_expiry = Column(DateTime, nullable=True)
    
    # Validation Status
    status = Column(SQLEnum(ProviderStatus), default=ProviderStatus.PENDING)
    validation_score = Column(Float, default=0.0)
    last_validated = Column(DateTime, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    validation_jobs = relationship("ValidationJob", back_populates="provider")
    validation_results = relationship("ValidationResult", back_populates="provider")

    def __repr__(self):
        return f"<Provider(id={self.id}, npi={self.npi}, name={self.first_name} {self.last_name})>"

class ValidationJob(Base):
    """Validation job model"""
    __tablename__ = "validation_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Job Configuration
    priority = Column(SQLEnum(ValidationJobPriority), default=ValidationJobPriority.MEDIUM)
    status = Column(SQLEnum(ValidationJobStatus), default=ValidationJobStatus.PENDING)
    
    # Validation Settings
    validate_npi = Column(Boolean, default=True)
    validate_address = Column(Boolean, default=True)
    validate_license = Column(Boolean, default=True)
    
    # Job Tracking
    progress = Column(Integer, default=0)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    provider = relationship("Provider", back_populates="validation_jobs")
    results = relationship("ValidationResult", back_populates="job")

    def __repr__(self):
        return f"<ValidationJob(id={self.id}, provider_id={self.provider_id}, status={self.status})>"

class ValidationResult(Base):
    """Validation result model"""
    __tablename__ = "validation_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    job_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    
    # Validation Results
    npi_valid = Column(Boolean, nullable=True)
    npi_details = Column(JSON, nullable=True)
    
    address_valid = Column(Boolean, nullable=True)
    address_details = Column(JSON, nullable=True)
    address_suggestions = Column(JSON, nullable=True)
    
    license_valid = Column(Boolean, nullable=True)
    license_details = Column(JSON, nullable=True)
    
    # Overall Results
    overall_score = Column(Float, nullable=True)
    validation_summary = Column(JSON, nullable=True)
    errors = Column(JSON, nullable=True)
    warnings = Column(JSON, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    provider = relationship("Provider", back_populates="validation_results")
    job = relationship("ValidationJob", back_populates="results")

    def __repr__(self):
        return f"<ValidationResult(id={self.id}, provider_id={self.provider_id}, score={self.overall_score})>"
