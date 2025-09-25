"""
PII (Personally Identifiable Information) Handler

This module provides comprehensive PII protection with permission-based reveal
and audit logging for all PII access.
"""

import hashlib
import re
import secrets
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union, Callable
from enum import Enum
from dataclasses import dataclass
from cryptography.fernet import Fernet
import json

class PIIFieldType(Enum):
    """PII field types for different masking strategies"""
    PHONE = "phone"
    EMAIL = "email"
    SSN = "ssn"
    NPI = "npi"
    ADDRESS = "address"
    NAME = "name"
    DATE_OF_BIRTH = "date_of_birth"
    MEDICAL_RECORD_NUMBER = "medical_record_number"
    CREDIT_CARD = "credit_card"
    BANK_ACCOUNT = "bank_account"
    GENERIC = "generic"

class PIISensitivityLevel(Enum):
    """PII sensitivity levels"""
    LOW = "low"           # Names, addresses
    MEDIUM = "medium"     # Phone numbers, emails
    HIGH = "high"         # SSN, NPI
    CRITICAL = "critical" # Medical records, financial data

class PIIDisclosureReason(Enum):
    """Reasons for PII disclosure"""
    AUDIT_REVIEW = "audit_review"
    COMPLIANCE_INVESTIGATION = "compliance_investigation"
    DATA_CORRECTION = "data_correction"
    CUSTOMER_SERVICE = "customer_service"
    LEGAL_REQUIREMENT = "legal_requirement"
    MEDICAL_EMERGENCY = "medical_emergency"
    SYSTEM_MAINTENANCE = "system_maintenance"
    OTHER = "other"

@dataclass
class PIIField:
    """PII field configuration"""
    field_name: str
    field_type: PIIFieldType
    sensitivity_level: PIISensitivityLevel
    required_permission: str
    audit_required: bool = True
    justification_required: bool = True
    max_access_frequency: Optional[int] = None  # per hour
    retention_days: Optional[int] = None

@dataclass
class PIIAccessEvent:
    """PII access event for audit logging"""
    timestamp: datetime
    user_id: str
    user_role: str
    field_name: str
    field_type: PIIFieldType
    sensitivity_level: PIISensitivityLevel
    original_value: Optional[str]
    revealed_value: Optional[str]
    access_reason: PIIDisclosureReason
    justification: Optional[str]
    ip_address: Optional[str]
    session_id: Optional[str]
    request_id: Optional[str]
    success: bool
    error_message: Optional[str]

class PIIHandler:
    """Comprehensive PII handling with encryption and audit logging"""
    
    def __init__(self, 
                 encryption_key: bytes,
                 audit_callback: Optional[Callable[[PIIAccessEvent], None]] = None):
        """
        Initialize PII handler
        
        Args:
            encryption_key: Encryption key for PII data
            audit_callback: Callback function for audit logging
        """
        self.encryption_key = encryption_key
        self.fernet = Fernet(encryption_key)
        self.audit_callback = audit_callback
        
        # PII field configurations
        self.pii_fields = {
            'phone_primary': PIIField(
                field_name='phone_primary',
                field_type=PIIFieldType.PHONE,
                sensitivity_level=PIISensitivityLevel.MEDIUM,
                required_permission='pii:reveal:phone',
                max_access_frequency=20  # per hour
            ),
            'phone_alt': PIIField(
                field_name='phone_alt',
                field_type=PIIFieldType.PHONE,
                sensitivity_level=PIISensitivityLevel.MEDIUM,
                required_permission='pii:reveal:phone',
                max_access_frequency=20  # per hour
            ),
            'email': PIIField(
                field_name='email',
                field_type=PIIFieldType.EMAIL,
                sensitivity_level=PIISensitivityLevel.MEDIUM,
                required_permission='pii:reveal:email',
                max_access_frequency=50  # per hour
            ),
            'npi_number': PIIField(
                field_name='npi_number',
                field_type=PIIFieldType.NPI,
                sensitivity_level=PIISensitivityLevel.HIGH,
                required_permission='pii:reveal:npi',
                max_access_frequency=10  # per hour
            ),
            'ssn': PIIField(
                field_name='ssn',
                field_type=PIIFieldType.SSN,
                sensitivity_level=PIISensitivityLevel.CRITICAL,
                required_permission='pii:reveal:ssn',
                max_access_frequency=5  # per hour
            ),
            'address_street': PIIField(
                field_name='address_street',
                field_type=PIIFieldType.ADDRESS,
                sensitivity_level=PIISensitivityLevel.LOW,
                required_permission='pii:reveal:address',
                max_access_frequency=100  # per hour
            ),
            'given_name': PIIField(
                field_name='given_name',
                field_type=PIIFieldType.NAME,
                sensitivity_level=PIISensitivityLevel.LOW,
                required_permission='pii:reveal:name',
                max_access_frequency=200  # per hour
            ),
            'family_name': PIIField(
                field_name='family_name',
                field_type=PIIFieldType.NAME,
                sensitivity_level=PIISensitivityLevel.LOW,
                required_permission='pii:reveal:name',
                max_access_frequency=200  # per hour
            ),
            'date_of_birth': PIIField(
                field_name='date_of_birth',
                field_type=PIIFieldType.DATE_OF_BIRTH,
                sensitivity_level=PIISensitivityLevel.MEDIUM,
                required_permission='pii:reveal:dob',
                max_access_frequency=10  # per hour
            ),
            'medical_record_number': PIIField(
                field_name='medical_record_number',
                field_type=PIIFieldType.MEDICAL_RECORD_NUMBER,
                sensitivity_level=PIISensitivityLevel.CRITICAL,
                required_permission='pii:reveal:mrn',
                max_access_frequency=5  # per hour
            )
        }
        
        # Masking patterns
        self.masking_patterns = {
            PIIFieldType.PHONE: self._mask_phone,
            PIIFieldType.EMAIL: self._mask_email,
            PIIFieldType.SSN: self._mask_ssn,
            PIIFieldType.NPI: self._mask_npi,
            PIIFieldType.ADDRESS: self._mask_address,
            PIIFieldType.NAME: self._mask_name,
            PIIFieldType.DATE_OF_BIRTH: self._mask_date_of_birth,
            PIIFieldType.MEDICAL_RECORD_NUMBER: self._mask_medical_record_number,
            PIIFieldType.GENERIC: self._mask_generic
        }
    
    def mask_pii_field(self, 
                      field_name: str, 
                      value: str, 
                      user_permissions: List[str],
                      is_privileged: bool = False) -> str:
        """
        Mask PII field based on user permissions
        
        Args:
            field_name: Name of the PII field
            value: Original value to mask
            user_permissions: User's permissions
            is_privileged: Whether user has privileged access
            
        Returns:
            Masked value
        """
        if not value:
            return value
        
        # Check if field is configured as PII
        if field_name not in self.pii_fields:
            return value
        
        pii_field = self.pii_fields[field_name]
        
        # Check if user has permission to reveal
        if self._has_pii_permission(user_permissions, pii_field, is_privileged):
            return value  # Return unmasked value
        
        # Apply masking
        mask_func = self.masking_patterns.get(pii_field.field_type, self._mask_generic)
        return mask_func(value)
    
    def reveal_pii_field(self,
                        field_name: str,
                        value: str,
                        user_id: str,
                        user_role: str,
                        user_permissions: List[str],
                        access_reason: PIIDisclosureReason,
                        justification: Optional[str] = None,
                        ip_address: Optional[str] = None,
                        session_id: Optional[str] = None,
                        request_id: Optional[str] = None) -> Optional[str]:
        """
        Reveal PII field with proper authorization and audit logging
        
        Args:
            field_name: Name of the PII field
            value: Encrypted or masked value
            user_id: User ID requesting access
            user_role: User's role
            user_permissions: User's permissions
            access_reason: Reason for PII disclosure
            justification: Justification for access
            ip_address: Client IP address
            session_id: Session ID
            request_id: Request ID
            
        Returns:
            Revealed value if authorized, None otherwise
        """
        if not value:
            return value
        
        # Check if field is configured as PII
        if field_name not in self.pii_fields:
            return value
        
        pii_field = self.pii_fields[field_name]
        
        # Check authorization
        if not self._has_pii_permission(user_permissions, pii_field, False):
            self._log_pii_access(
                field_name=field_name,
                field_type=pii_field.field_type,
                sensitivity_level=pii_field.sensitivity_level,
                user_id=user_id,
                user_role=user_role,
                original_value=None,
                revealed_value=None,
                access_reason=access_reason,
                justification=justification,
                ip_address=ip_address,
                session_id=session_id,
                request_id=request_id,
                success=False,
                error_message="Insufficient permissions"
            )
            return None
        
        # Check access frequency limits
        if not self._check_access_frequency(user_id, field_name, pii_field):
            self._log_pii_access(
                field_name=field_name,
                field_type=pii_field.field_type,
                sensitivity_level=pii_field.sensitivity_level,
                user_id=user_id,
                user_role=user_role,
                original_value=None,
                revealed_value=None,
                access_reason=access_reason,
                justification=justification,
                ip_address=ip_address,
                session_id=session_id,
                request_id=request_id,
                success=False,
                error_message="Access frequency limit exceeded"
            )
            return None
        
        # Decrypt if encrypted
        try:
            revealed_value = self._decrypt_value(value)
        except Exception:
            revealed_value = value  # Assume already decrypted
        
        # Log successful access
        self._log_pii_access(
            field_name=field_name,
            field_type=pii_field.field_type,
            sensitivity_level=pii_field.sensitivity_level,
            user_id=user_id,
            user_role=user_role,
            original_value=value,
            revealed_value=revealed_value,
            access_reason=access_reason,
            justification=justification,
            ip_address=ip_address,
            session_id=session_id,
            request_id=request_id,
            success=True
        )
        
        return revealed_value
    
    def encrypt_pii_value(self, value: str) -> str:
        """
        Encrypt PII value for storage
        
        Args:
            value: Value to encrypt
            
        Returns:
            Encrypted value
        """
        if not value:
            return value
        
        try:
            encrypted_bytes = self.fernet.encrypt(value.encode('utf-8'))
            return encrypted_bytes.decode('utf-8')
        except Exception as e:
            raise ValueError(f"Failed to encrypt PII value: {str(e)}")
    
    def _decrypt_value(self, encrypted_value: str) -> str:
        """
        Decrypt PII value
        
        Args:
            encrypted_value: Encrypted value
            
        Returns:
            Decrypted value
        """
        try:
            decrypted_bytes = self.fernet.decrypt(encrypted_value.encode('utf-8'))
            return decrypted_bytes.decode('utf-8')
        except Exception:
            # If decryption fails, assume value is not encrypted
            return encrypted_value
    
    def _has_pii_permission(self, 
                           user_permissions: List[str], 
                           pii_field: PIIField, 
                           is_privileged: bool) -> bool:
        """Check if user has permission to access PII field"""
        if is_privileged:
            return True
        
        return pii_field.required_permission in user_permissions
    
    def _check_access_frequency(self, 
                               user_id: str, 
                               field_name: str, 
                               pii_field: PIIField) -> bool:
        """Check if user has exceeded access frequency limits"""
        if not pii_field.max_access_frequency:
            return True
        
        # This would typically check against a rate limiting store (Redis)
        # For now, return True (implement based on your rate limiting system)
        return True
    
    def _log_pii_access(self,
                       field_name: str,
                       field_type: PIIFieldType,
                       sensitivity_level: PIISensitivityLevel,
                       user_id: str,
                       user_role: str,
                       original_value: Optional[str],
                       revealed_value: Optional[str],
                       access_reason: PIIDisclosureReason,
                       justification: Optional[str],
                       ip_address: Optional[str],
                       session_id: Optional[str],
                       request_id: Optional[str],
                       success: bool,
                       error_message: Optional[str] = None):
        """Log PII access event"""
        if not self.audit_callback:
            return
        
        event = PIIAccessEvent(
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            user_role=user_role,
            field_name=field_name,
            field_type=field_type,
            sensitivity_level=sensitivity_level,
            original_value=original_value,
            revealed_value=revealed_value,
            access_reason=access_reason,
            justification=justification,
            ip_address=ip_address,
            session_id=session_id,
            request_id=request_id,
            success=success,
            error_message=error_message
        )
        
        self.audit_callback(event)
    
    # Masking functions for different PII types
    def _mask_phone(self, value: str) -> str:
        """Mask phone number showing last 4 digits"""
        # Remove all non-digits
        digits = re.sub(r'\D', '', value)
        
        if len(digits) >= 4:
            return f"***-***-{digits[-4:]}"
        elif len(digits) > 0:
            return f"***-***-{digits}"
        else:
            return "***-***-****"
    
    def _mask_email(self, value: str) -> str:
        """Mask email showing first character and domain"""
        if '@' not in value:
            return "***@***.***"
        
        local, domain = value.split('@', 1)
        if len(local) > 1:
            return f"{local[0]}***@{domain}"
        else:
            return f"***@{domain}"
    
    def _mask_ssn(self, value: str) -> str:
        """Mask SSN completely"""
        return "***-**-****"
    
    def _mask_npi(self, value: str) -> str:
        """Mask NPI showing last 4 digits"""
        if len(value) >= 4:
            return f"***{value[-4:]}"
        else:
            return "**********"
    
    def _mask_address(self, value: str) -> str:
        """Mask street address showing number and masked street"""
        # Extract street number
        match = re.match(r'^(\d+)', value)
        if match:
            number = match.group(1)
            return f"{number} *** Street"
        else:
            return "*** Street"
    
    def _mask_name(self, value: str) -> str:
        """Mask name showing first character"""
        if len(value) > 1:
            return f"{value[0]}***"
        else:
            return "***"
    
    def _mask_date_of_birth(self, value: str) -> str:
        """Mask date of birth showing year only"""
        # Extract year from various date formats
        year_match = re.search(r'(\d{4})', value)
        if year_match:
            return f"****-**-** ({year_match.group(1)})"
        else:
            return "****-**-**"
    
    def _mask_medical_record_number(self, value: str) -> str:
        """Mask medical record number completely"""
        return "***-***-****"
    
    def _mask_generic(self, value: str) -> str:
        """Generic masking for unknown PII types"""
        if len(value) > 4:
            return f"{'*' * (len(value) - 4)}{value[-4:]}"
        else:
            return "*" * len(value)
    
    def mask_provider_data(self, 
                          provider_data: Dict[str, Any], 
                          user_permissions: List[str],
                          is_privileged: bool = False) -> Dict[str, Any]:
        """
        Mask PII fields in provider data
        
        Args:
            provider_data: Provider data dictionary
            user_permissions: User's permissions
            is_privileged: Whether user has privileged access
            
        Returns:
            Provider data with PII fields masked
        """
        masked_data = provider_data.copy()
        
        for field_name, value in provider_data.items():
            if field_name in self.pii_fields and value:
                masked_data[field_name] = self.mask_pii_field(
                    field_name, 
                    str(value), 
                    user_permissions, 
                    is_privileged
                )
        
        return masked_data
    
    def get_pii_field_config(self, field_name: str) -> Optional[PIIField]:
        """Get PII field configuration"""
        return self.pii_fields.get(field_name)
    
    def add_pii_field(self, pii_field: PIIField):
        """Add new PII field configuration"""
        self.pii_fields[pii_field.field_name] = pii_field
    
    def remove_pii_field(self, field_name: str):
        """Remove PII field configuration"""
        if field_name in self.pii_fields:
            del self.pii_fields[field_name]
    
    def get_pii_fields_by_sensitivity(self, sensitivity_level: PIISensitivityLevel) -> List[PIIField]:
        """Get PII fields by sensitivity level"""
        return [
            field for field in self.pii_fields.values()
            if field.sensitivity_level == sensitivity_level
        ]
    
    def validate_pii_access_policy(self, 
                                  user_role: str, 
                                  field_name: str, 
                                  access_reason: PIIDisclosureReason) -> bool:
        """
        Validate PII access policy based on role and reason
        
        Args:
            user_role: User's role
            field_name: PII field name
            access_reason: Reason for access
            
        Returns:
            True if access is allowed by policy
        """
        if field_name not in self.pii_fields:
            return True
        
        pii_field = self.pii_fields[field_name]
        
        # Define role-based access policies
        role_policies = {
            'admin': {
                'allowed_reasons': list(PIIDisclosureReason),
                'sensitivity_levels': [PIISensitivityLevel.LOW, PIISensitivityLevel.MEDIUM, 
                                     PIISensitivityLevel.HIGH, PIISensitivityLevel.CRITICAL]
            },
            'reviewer': {
                'allowed_reasons': [PIIDisclosureReason.AUDIT_REVIEW, PIIDisclosureReason.DATA_CORRECTION,
                                  PIIDisclosureReason.CUSTOMER_SERVICE, PIIDisclosureReason.OTHER],
                'sensitivity_levels': [PIISensitivityLevel.LOW, PIISensitivityLevel.MEDIUM]
            },
            'auditor': {
                'allowed_reasons': [PIIDisclosureReason.AUDIT_REVIEW, PIIDisclosureReason.COMPLIANCE_INVESTIGATION],
                'sensitivity_levels': [PIISensitivityLevel.LOW, PIISensitivityLevel.MEDIUM, PIISensitivityLevel.HIGH]
            },
            'operator': {
                'allowed_reasons': [PIIDisclosureReason.DATA_CORRECTION, PIIDisclosureReason.CUSTOMER_SERVICE],
                'sensitivity_levels': [PIISensitivityLevel.LOW]
            },
            'viewer': {
                'allowed_reasons': [],
                'sensitivity_levels': []
            }
        }
        
        policy = role_policies.get(user_role, role_policies['viewer'])
        
        # Check if reason is allowed
        if access_reason not in policy['allowed_reasons']:
            return False
        
        # Check if sensitivity level is allowed
        if pii_field.sensitivity_level not in policy['sensitivity_levels']:
            return False
        
        return True

# Global PII handler instance
pii_handler: Optional[PIIHandler] = None

def initialize_pii_handler(encryption_key: bytes, 
                          audit_callback: Optional[Callable[[PIIAccessEvent], None]] = None) -> PIIHandler:
    """Initialize global PII handler"""
    global pii_handler
    pii_handler = PIIHandler(encryption_key, audit_callback)
    return pii_handler

def get_pii_handler() -> PIIHandler:
    """Get global PII handler instance"""
    if pii_handler is None:
        raise RuntimeError("PII handler not initialized. Call initialize_pii_handler() first.")
    return pii_handler
