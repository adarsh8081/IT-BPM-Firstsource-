"""
Validation job and result models
"""

from sqlalchemy import Column, String, DateTime, Float, JSON, Text, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid
import enum

from .provider import Base

class ValidationStatus(enum.Enum):
    """Validation job status enumeration"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ValidationJob(Base):
    """Validation job tracking model"""
    __tablename__ = "validation_jobs"

    job_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment="Unique job identifier")
    provider_id = Column(UUID(as_uuid=True), ForeignKey('providers.provider_id'), nullable=True, comment="Provider being validated (null for batch jobs)")
    job_type = Column(String(50), nullable=False, comment="Type of validation job (single, batch, bulk)")
    status = Column(Enum(ValidationStatus), nullable=False, default=ValidationStatus.PENDING, comment="Current job status")
    priority = Column(String(20), nullable=False, default='normal', comment="Job priority (low, normal, high, urgent)")
    
    # Job configuration
    validation_config = Column(JSON, nullable=True, comment="JSON configuration for validation rules")
    requested_validations = Column(JSON, nullable=True, comment="Array of validation types to perform")
    
    # Progress tracking
    progress_percentage = Column(Float, nullable=True, default=0.0, comment="Job progress percentage (0-100)")
    current_step = Column(String(100), nullable=True, comment="Current validation step")
    total_steps = Column(String(100), nullable=True, comment="Total number of steps")
    
    # Results and metadata
    results_summary = Column(JSON, nullable=True, comment="Summary of validation results")
    error_message = Column(Text, nullable=True, comment="Error message if job failed")
    started_at = Column(DateTime, nullable=True, comment="Job start timestamp")
    completed_at = Column(DateTime, nullable=True, comment="Job completion timestamp")
    
    # Audit fields
    created_by = Column(String(100), nullable=True, comment="User or system that created the job")
    created_at = Column(DateTime, default=func.now(), nullable=False, comment="Job creation timestamp")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False, comment="Last update timestamp")

    # Relationships
    provider = relationship("Provider", back_populates="validation_jobs")
    validation_results = relationship("ValidationResult", back_populates="job", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ValidationJob(job_id={self.job_id}, status={self.status}, provider_id={self.provider_id})>"

class ValidationResult(Base):
    """Individual validation result model"""
    __tablename__ = "validation_results"

    result_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment="Unique result identifier")
    job_id = Column(UUID(as_uuid=True), ForeignKey('validation_jobs.job_id'), nullable=False, comment="Associated validation job")
    provider_id = Column(UUID(as_uuid=True), ForeignKey('providers.provider_id'), nullable=False, comment="Provider that was validated")
    
    # Validation details
    validation_type = Column(String(50), nullable=False, comment="Type of validation performed")
    validation_source = Column(String(100), nullable=True, comment="Source of validation (NPI API, Google Places, etc.)")
    field_name = Column(String(100), nullable=True, comment="Specific field that was validated")
    
    # Results
    is_valid = Column(String(10), nullable=False, comment="Validation result (valid, invalid, warning, error)")
    confidence_score = Column(Float, nullable=True, comment="Confidence score for this validation (0-1)")
    raw_response = Column(JSON, nullable=True, comment="Raw response from validation source")
    
    # Validation details
    validation_details = Column(JSON, nullable=True, comment="Detailed validation information")
    suggested_corrections = Column(JSON, nullable=True, comment="Suggested corrections if validation failed")
    flags = Column(JSON, nullable=True, comment="Validation flags and warnings")
    
    # Timing
    validation_duration_ms = Column(Float, nullable=True, comment="Validation duration in milliseconds")
    validated_at = Column(DateTime, default=func.now(), nullable=False, comment="Validation timestamp")

    # Relationships
    job = relationship("ValidationJob", back_populates="validation_results")
    provider = relationship("Provider")

    def __repr__(self):
        return f"<ValidationResult(result_id={self.result_id}, type={self.validation_type}, is_valid={self.is_valid})>"

# Update Provider model to include relationship
from sqlalchemy.orm import relationship

# Add this to the Provider class in provider.py (we'll do it here for now)
Provider.validation_jobs = relationship("ValidationJob", back_populates="provider", cascade="all, delete-orphan")
