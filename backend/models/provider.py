"""
Provider data model with precise field definitions
"""

from sqlalchemy import Column, String, DateTime, Float, JSON, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid

Base = declarative_base()

class Provider(Base):
    """Precise provider data model with comprehensive field coverage"""
    __tablename__ = "providers"

    # Primary identifier
    provider_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment="Unique provider identifier")
    
    # Personal information
    given_name = Column(String(100), nullable=False, comment="Provider's given (first) name")
    family_name = Column(String(100), nullable=False, comment="Provider's family (last) name")
    
    # Professional identifiers
    npi_number = Column(String(10), unique=True, nullable=False, index=True, comment="10-digit National Provider Identifier")
    primary_taxonomy = Column(String(200), nullable=True, comment="Primary medical specialty/taxonomy code")
    practice_name = Column(String(200), nullable=True, comment="Name of practice or organization")
    
    # Address information
    address_street = Column(String(255), nullable=True, comment="Street address line")
    address_city = Column(String(100), nullable=True, comment="City name")
    address_state = Column(String(2), nullable=True, comment="State abbreviation (2 characters)")
    address_zip = Column(String(10), nullable=True, comment="ZIP/postal code")
    place_id = Column(String(255), nullable=True, comment="Google Places API place ID")
    
    # Contact information
    phone_primary = Column(String(20), nullable=True, comment="Primary phone number")
    phone_alt = Column(String(20), nullable=True, comment="Alternative phone number")
    email = Column(String(255), nullable=True, comment="Primary email address")
    
    # License information
    license_number = Column(String(50), nullable=True, comment="Medical license number")
    license_state = Column(String(2), nullable=True, comment="State where license is issued")
    license_status = Column(String(20), nullable=True, comment="License status (active, expired, suspended, etc.)")
    
    # Professional relationships
    affiliations = Column(JSON, nullable=True, comment="JSON array of organization affiliations")
    
    # Services and capabilities
    services_offered = Column(JSON, nullable=True, comment="JSON object of services offered by provider")
    
    # Validation tracking
    last_validated_at = Column(DateTime, nullable=True, comment="Timestamp of last validation")
    validated_by = Column(String(100), nullable=True, comment="Agent ID or system that performed validation")
    overall_confidence = Column(Float, nullable=True, comment="Overall confidence score (0.0-1.0)")
    
    # Field-level validation scores
    field_confidence = Column(JSON, nullable=True, comment="JSON object with per-field confidence scores")
    
    # Validation flags and reason codes
    flags = Column(JSON, nullable=True, comment="JSON array of validation flags and reason codes")
    
    # Audit fields
    created_at = Column(DateTime, default=func.now(), nullable=False, comment="Record creation timestamp")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False, comment="Last update timestamp")

    # Indexes for performance
    __table_args__ = (
        Index('idx_provider_npi', 'npi_number'),
        Index('idx_provider_name', 'family_name', 'given_name'),
        Index('idx_provider_state', 'address_state'),
        Index('idx_provider_taxonomy', 'primary_taxonomy'),
        Index('idx_provider_license', 'license_number', 'license_state'),
        Index('idx_provider_validated', 'last_validated_at'),
        Index('idx_provider_confidence', 'overall_confidence'),
    )

    def __repr__(self):
        return f"<Provider(provider_id={self.provider_id}, npi={self.npi_number}, name={self.given_name} {self.family_name})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert provider to dictionary representation"""
        return {
            'provider_id': str(self.provider_id),
            'given_name': self.given_name,
            'family_name': self.family_name,
            'npi_number': self.npi_number,
            'primary_taxonomy': self.primary_taxonomy,
            'practice_name': self.practice_name,
            'address_street': self.address_street,
            'address_city': self.address_city,
            'address_state': self.address_state,
            'address_zip': self.address_zip,
            'place_id': self.place_id,
            'phone_primary': self.phone_primary,
            'phone_alt': self.phone_alt,
            'email': self.email,
            'license_number': self.license_number,
            'license_state': self.license_state,
            'license_status': self.license_status,
            'affiliations': self.affiliations,
            'services_offered': self.services_offered,
            'last_validated_at': self.last_validated_at.isoformat() if self.last_validated_at else None,
            'validated_by': self.validated_by,
            'overall_confidence': self.overall_confidence,
            'field_confidence': self.field_confidence,
            'flags': self.flags,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    @property
    def full_name(self) -> str:
        """Get provider's full name"""
        return f"{self.given_name} {self.family_name}".strip()

    @property
    def full_address(self) -> str:
        """Get provider's full address"""
        parts = [
            self.address_street,
            self.address_city,
            self.address_state,
            self.address_zip
        ]
        return ", ".join(filter(None, parts))

    def add_flag(self, flag_code: str, reason: str = None):
        """Add a validation flag with reason code"""
        if self.flags is None:
            self.flags = []
        
        flag_entry = {
            'code': flag_code,
            'reason': reason,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if flag_entry not in self.flags:
            self.flags.append(flag_entry)

    def update_field_confidence(self, field_name: str, confidence_score: float):
        """Update confidence score for a specific field"""
        if self.field_confidence is None:
            self.field_confidence = {}
        
        self.field_confidence[field_name] = {
            'score': confidence_score,
            'updated_at': datetime.utcnow().isoformat()
        }

    def calculate_overall_confidence(self) -> float:
        """Calculate overall confidence based on field scores"""
        if not self.field_confidence:
            return 0.0
        
        scores = []
        for field_data in self.field_confidence.values():
            if isinstance(field_data, dict) and 'score' in field_data:
                scores.append(field_data['score'])
            elif isinstance(field_data, (int, float)):
                scores.append(float(field_data))
        
        if not scores:
            return 0.0
        
        return sum(scores) / len(scores)
