"""
Validation Rules and Criteria System

This module implements comprehensive validation rules for provider data with
field-specific validation logic, confidence weighting, and compliance checks.
"""

import asyncio
import logging
import re
import socket
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import httpx
import phonenumbers
from phonenumbers import geocoder, carrier
import Levenshtein
from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin, urlparse
import json

logger = logging.getLogger(__name__)


class ValidationStatus(Enum):
    """Validation status enumeration"""
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"
    UNKNOWN = "unknown"


class ValidationSource(Enum):
    """Validation source enumeration"""
    NPI = "npi"
    GOOGLE_PLACES = "google_places"
    HOSPITAL_WEBSITE = "hospital_website"
    STATE_BOARD = "state_board"
    MANUAL = "manual"


@dataclass
class ValidationRule:
    """Individual validation rule"""
    field_name: str
    rule_type: str
    criteria: Dict[str, Any]
    weight: float
    source: ValidationSource
    description: str


@dataclass
class ValidationResult:
    """Result of field validation"""
    field_name: str
    value: str
    status: ValidationStatus
    confidence: float
    source: ValidationSource
    criteria_met: bool
    details: Dict[str, Any]
    timestamp: datetime
    error_message: Optional[str] = None


@dataclass
class FieldValidationSummary:
    """Summary of field validation results"""
    field_name: str
    overall_confidence: float
    status: ValidationStatus
    results: List[ValidationResult]
    weighted_score: float
    validation_count: int


@dataclass
class ProviderValidationSummary:
    """Complete provider validation summary"""
    provider_id: str
    overall_confidence: float
    validation_status: ValidationStatus
    field_summaries: Dict[str, FieldValidationSummary]
    total_validations: int
    successful_validations: int
    failed_validations: int
    warning_validations: int
    validation_timestamp: datetime


class ValidationRulesEngine:
    """
    Validation Rules Engine
    
    Implements comprehensive validation rules for provider data with
    field-specific validation logic, confidence weighting, and compliance checks.
    """
    
    def __init__(self):
        """Initialize validation rules engine"""
        self.rules = self._initialize_validation_rules()
        self.confidence_weights = {
            ValidationSource.NPI: 0.4,
            ValidationSource.GOOGLE_PLACES: 0.25,
            ValidationSource.HOSPITAL_WEBSITE: 0.2,
            ValidationSource.STATE_BOARD: 0.15
        }
        
        # Robots.txt compliance
        self.robots_cache = {}
        self.politeness_headers = {
            "User-Agent": "Provider-Validation-System/1.0",
            "Accept": "application/json, text/html",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache"
        }
        
        # Rate limiting
        self.request_delays = {
            ValidationSource.NPI: 0.1,  # 10 requests per second
            ValidationSource.GOOGLE_PLACES: 0.1,  # 10 requests per second
            ValidationSource.HOSPITAL_WEBSITE: 2.0,  # 30 requests per minute
            ValidationSource.STATE_BOARD: 2.0  # 30 requests per minute
        }
        
        self.last_requests = {}
    
    def _initialize_validation_rules(self) -> List[ValidationRule]:
        """Initialize validation rules for all fields"""
        rules = [
            # Phone validation rules
            ValidationRule(
                field_name="phone_primary",
                rule_type="e164_normalization",
                criteria={
                    "format": "E.164",
                    "lookup_enabled": True,
                    "carrier_check": True,
                    "geolocation_check": True
                },
                weight=0.4,
                source=ValidationSource.NPI,
                description="E.164 phone normalization with carrier lookup"
            ),
            
            # Address validation rules
            ValidationRule(
                field_name="address_street",
                rule_type="place_id_matching",
                criteria={
                    "geocode_distance_threshold": 100,  # meters
                    "place_id_required": True,
                    "address_components_match": True
                },
                weight=0.25,
                source=ValidationSource.GOOGLE_PLACES,
                description="Address validation with place_id matching and geocode distance"
            ),
            
            # License validation rules
            ValidationRule(
                field_name="license_number",
                rule_type="state_board_verification",
                criteria={
                    "license_status_required": "ACTIVE",
                    "state_board_check": True,
                    "expiry_date_check": True
                },
                weight=0.15,
                source=ValidationSource.STATE_BOARD,
                description="License verification with state board and ACTIVE status requirement"
            ),
            
            # Email validation rules
            ValidationRule(
                field_name="email",
                rule_type="mx_record_check",
                criteria={
                    "mx_record_required": True,
                    "syntax_validation": True,
                    "domain_validation": True
                },
                weight=0.2,
                source=ValidationSource.HOSPITAL_WEBSITE,
                description="Email validation with MX record check"
            ),
            
            # Name validation rules
            ValidationRule(
                field_name="given_name",
                rule_type="fuzzy_matching",
                criteria={
                    "levenshtein_threshold": 0.85,
                    "npi_name_comparison": True,
                    "case_insensitive": True
                },
                weight=0.4,
                source=ValidationSource.NPI,
                description="Name fuzzy matching with Levenshtein distance > 0.85"
            ),
            
            ValidationRule(
                field_name="family_name",
                rule_type="fuzzy_matching",
                criteria={
                    "levenshtein_threshold": 0.85,
                    "npi_name_comparison": True,
                    "case_insensitive": True
                },
                weight=0.4,
                source=ValidationSource.NPI,
                description="Family name fuzzy matching with Levenshtein distance > 0.85"
            )
        ]
        
        return rules
    
    async def validate_provider(self, provider_data: Dict[str, Any]) -> ProviderValidationSummary:
        """
        Validate complete provider data
        
        Args:
            provider_data: Provider data dictionary
            
        Returns:
            ProviderValidationSummary with complete validation results
        """
        start_time = datetime.now()
        
        # Validate each field
        field_results = {}
        total_validations = 0
        successful_validations = 0
        failed_validations = 0
        warning_validations = 0
        
        for rule in self.rules:
            if rule.field_name in provider_data:
                field_value = provider_data[rule.field_name]
                
                # Apply field-specific validation
                validation_result = await self._validate_field(rule, field_value, provider_data)
                
                if rule.field_name not in field_results:
                    field_results[rule.field_name] = []
                
                field_results[rule.field_name].append(validation_result)
                total_validations += 1
                
                if validation_result.status == ValidationStatus.VALID:
                    successful_validations += 1
                elif validation_result.status == ValidationStatus.INVALID:
                    failed_validations += 1
                elif validation_result.status == ValidationStatus.WARNING:
                    warning_validations += 1
        
        # Calculate field summaries
        field_summaries = {}
        for field_name, results in field_results.items():
            field_summary = self._calculate_field_summary(field_name, results)
            field_summaries[field_name] = field_summary
        
        # Calculate overall confidence
        overall_confidence = self._calculate_overall_confidence(field_summaries)
        
        # Determine overall validation status
        validation_status = self._determine_overall_status(field_summaries)
        
        return ProviderValidationSummary(
            provider_id=provider_data.get("provider_id", "unknown"),
            overall_confidence=overall_confidence,
            validation_status=validation_status,
            field_summaries=field_summaries,
            total_validations=total_validations,
            successful_validations=successful_validations,
            failed_validations=failed_validations,
            warning_validations=warning_validations,
            validation_timestamp=datetime.now()
        )
    
    async def _validate_field(self, rule: ValidationRule, field_value: str, provider_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate individual field based on rule
        
        Args:
            rule: Validation rule to apply
            field_value: Field value to validate
            provider_data: Complete provider data for context
            
        Returns:
            ValidationResult for the field
        """
        try:
            # Apply rate limiting
            await self._apply_rate_limiting(rule.source)
            
            # Check robots.txt compliance
            if not await self._check_robots_compliance(rule.source):
                return ValidationResult(
                    field_name=rule.field_name,
                    value=field_value,
                    status=ValidationStatus.WARNING,
                    confidence=0.0,
                    source=rule.source,
                    criteria_met=False,
                    details={"robots_blocked": True},
                    timestamp=datetime.now(),
                    error_message="Robots.txt compliance blocked validation"
                )
            
            # Apply field-specific validation
            if rule.rule_type == "e164_normalization":
                return await self._validate_phone_e164(rule, field_value)
            elif rule.rule_type == "place_id_matching":
                return await self._validate_address_place_id(rule, field_value, provider_data)
            elif rule.rule_type == "state_board_verification":
                return await self._validate_license_state_board(rule, field_value, provider_data)
            elif rule.rule_type == "mx_record_check":
                return await self._validate_email_mx(rule, field_value)
            elif rule.rule_type == "fuzzy_matching":
                return await self._validate_name_fuzzy(rule, field_value, provider_data)
            else:
                return ValidationResult(
                    field_name=rule.field_name,
                    value=field_value,
                    status=ValidationStatus.UNKNOWN,
                    confidence=0.0,
                    source=rule.source,
                    criteria_met=False,
                    details={"rule_type": rule.rule_type},
                    timestamp=datetime.now(),
                    error_message=f"Unknown rule type: {rule.rule_type}"
                )
        
        except Exception as e:
            logger.error(f"Validation error for {rule.field_name}: {str(e)}")
            return ValidationResult(
                field_name=rule.field_name,
                value=field_value,
                status=ValidationStatus.INVALID,
                confidence=0.0,
                source=rule.source,
                criteria_met=False,
                details={"error": str(e)},
                timestamp=datetime.now(),
                error_message=str(e)
            )
    
    async def _validate_phone_e164(self, rule: ValidationRule, phone_value: str) -> ValidationResult:
        """
        Validate phone number with E.164 normalization and lookup
        
        Args:
            rule: Phone validation rule
            phone_value: Phone number to validate
            
        Returns:
            ValidationResult for phone validation
        """
        try:
            # Parse phone number
            parsed_number = phonenumbers.parse(phone_value, "US")
            
            # Check if valid
            is_valid = phonenumbers.is_valid_number(parsed_number)
            if not is_valid:
                return ValidationResult(
                    field_name=rule.field_name,
                    value=phone_value,
                    status=ValidationStatus.INVALID,
                    confidence=0.0,
                    source=rule.source,
                    criteria_met=False,
                    details={"valid_number": False},
                    timestamp=datetime.now(),
                    error_message="Invalid phone number format"
                )
            
            # Get E.164 format
            e164_format = phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
            
            # Get carrier information
            carrier_info = carrier.name_for_number(parsed_number, "en")
            
            # Get geolocation
            geolocation = geocoder.description_for_number(parsed_number, "en")
            
            # Check if number is possible (not just valid)
            is_possible = phonenumbers.is_possible_number(parsed_number)
            
            # Calculate confidence based on validation results
            confidence = 0.8 if is_valid else 0.0
            if carrier_info:
                confidence += 0.1
            if geolocation:
                confidence += 0.05
            if is_possible:
                confidence += 0.05
            
            confidence = min(1.0, confidence)
            
            return ValidationResult(
                field_name=rule.field_name,
                value=e164_format,
                status=ValidationStatus.VALID if confidence > 0.8 else ValidationStatus.WARNING,
                confidence=confidence,
                source=rule.source,
                criteria_met=True,
                details={
                    "e164_format": e164_format,
                    "carrier": carrier_info,
                    "geolocation": geolocation,
                    "is_possible": is_possible,
                    "original_format": phone_value
                },
                timestamp=datetime.now()
            )
        
        except Exception as e:
            return ValidationResult(
                field_name=rule.field_name,
                value=phone_value,
                status=ValidationStatus.INVALID,
                confidence=0.0,
                source=rule.source,
                criteria_met=False,
                details={"error": str(e)},
                timestamp=datetime.now(),
                error_message=f"Phone validation error: {str(e)}"
            )
    
    async def _validate_address_place_id(self, rule: ValidationRule, address_value: str, provider_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate address with place_id matching and geocode distance
        
        Args:
            rule: Address validation rule
            address_value: Address to validate
            provider_data: Complete provider data for context
            
        Returns:
            ValidationResult for address validation
        """
        try:
            # Use Google Places API for validation
            from .google_places import GooglePlacesConnector
            
            # Initialize Google Places connector (mock for now)
            # In production, this would use actual API key
            connector = GooglePlacesConnector(api_key="mock_key")
            
            # Validate address
            result = await connector.validate_address(address_value)
            
            if result.success:
                # Check if we have place_id
                place_id = result.data.get("place_id")
                if not place_id:
                    return ValidationResult(
                        field_name=rule.field_name,
                        value=address_value,
                        status=ValidationStatus.WARNING,
                        confidence=0.6,
                        source=rule.source,
                        criteria_met=False,
                        details={"place_id_missing": True},
                        timestamp=datetime.now(),
                        error_message="No place_id found for address"
                    )
                
                # Check geocode distance (mock calculation)
                # In production, this would calculate actual distance
                geocode_distance = 50  # Mock distance in meters
                distance_threshold = rule.criteria["geocode_distance_threshold"]
                
                if geocode_distance <= distance_threshold:
                    confidence = 0.9
                    status = ValidationStatus.VALID
                else:
                    confidence = 0.5
                    status = ValidationStatus.WARNING
                
                return ValidationResult(
                    field_name=rule.field_name,
                    value=address_value,
                    status=status,
                    confidence=confidence,
                    source=rule.source,
                    criteria_met=(geocode_distance <= distance_threshold),
                    details={
                        "place_id": place_id,
                        "geocode_distance": geocode_distance,
                        "distance_threshold": distance_threshold,
                        "formatted_address": result.data.get("formatted_address"),
                        "latitude": result.data.get("latitude"),
                        "longitude": result.data.get("longitude")
                    },
                    timestamp=datetime.now()
                )
            else:
                return ValidationResult(
                    field_name=rule.field_name,
                    value=address_value,
                    status=ValidationStatus.INVALID,
                    confidence=0.0,
                    source=rule.source,
                    criteria_met=False,
                    details={"validation_failed": True},
                    timestamp=datetime.now(),
                    error_message="Address validation failed"
                )
        
        except Exception as e:
            return ValidationResult(
                field_name=rule.field_name,
                value=address_value,
                status=ValidationStatus.INVALID,
                confidence=0.0,
                source=rule.source,
                criteria_met=False,
                details={"error": str(e)},
                timestamp=datetime.now(),
                error_message=f"Address validation error: {str(e)}"
            )
    
    async def _validate_license_state_board(self, rule: ValidationRule, license_value: str, provider_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate license with state board verification and ACTIVE status requirement
        
        Args:
            rule: License validation rule
            license_value: License number to validate
            provider_data: Complete provider data for context
            
        Returns:
            ValidationResult for license validation
        """
        try:
            # Use State Board connector for validation
            from .state_board_mock import StateBoardMockConnector, ScrapingConfig
            
            # Get license state from provider data
            license_state = provider_data.get("license_state", "CA")
            
            # Create scraping configuration
            config = ScrapingConfig(
                state_code=license_state,
                state_name="California",  # Mock state name
                base_url="http://127.0.0.1:8080",
                search_url="http://127.0.0.1:8080/search",
                search_method="POST"
            )
            
            # Initialize connector
            connector = StateBoardMockConnector(config)
            
            # Validate license
            result = await connector.verify_license(license_value)
            
            if result.success:
                # Check license status
                license_status = result.data.get("license_status", "").upper()
                required_status = rule.criteria["license_status_required"]
                
                if license_status == required_status:
                    confidence = 0.95
                    status = ValidationStatus.VALID
                elif license_status in ["SUSPENDED", "REVOKED"]:
                    confidence = 0.1
                    status = ValidationStatus.INVALID
                else:
                    confidence = 0.5
                    status = ValidationStatus.WARNING
                
                return ValidationResult(
                    field_name=rule.field_name,
                    value=license_value,
                    status=status,
                    confidence=confidence,
                    source=rule.source,
                    criteria_met=(license_status == required_status),
                    details={
                        "license_status": license_status,
                        "required_status": required_status,
                        "provider_name": result.data.get("provider_name"),
                        "issue_date": result.data.get("issue_date"),
                        "expiry_date": result.data.get("expiry_date"),
                        "board_actions": result.data.get("board_actions", [])
                    },
                    timestamp=datetime.now()
                )
            else:
                return ValidationResult(
                    field_name=rule.field_name,
                    value=license_value,
                    status=ValidationStatus.INVALID,
                    confidence=0.0,
                    source=rule.source,
                    criteria_met=False,
                    details={"validation_failed": True},
                    timestamp=datetime.now(),
                    error_message="License validation failed"
                )
        
        except Exception as e:
            return ValidationResult(
                field_name=rule.field_name,
                value=license_value,
                status=ValidationStatus.INVALID,
                confidence=0.0,
                source=rule.source,
                criteria_met=False,
                details={"error": str(e)},
                timestamp=datetime.now(),
                error_message=f"License validation error: {str(e)}"
            )
    
    async def _validate_email_mx(self, rule: ValidationRule, email_value: str) -> ValidationResult:
        """
        Validate email with MX record check
        
        Args:
            rule: Email validation rule
            email_value: Email address to validate
            
        Returns:
            ValidationResult for email validation
        """
        try:
            # Basic email format validation
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email_value):
                return ValidationResult(
                    field_name=rule.field_name,
                    value=email_value,
                    status=ValidationStatus.INVALID,
                    confidence=0.0,
                    source=rule.source,
                    criteria_met=False,
                    details={"invalid_format": True},
                    timestamp=datetime.now(),
                    error_message="Invalid email format"
                )
            
            # Extract domain
            domain = email_value.split('@')[1]
            
            # Check MX record
            try:
                mx_records = socket.getaddrinfo(domain, None, socket.AF_INET)
                mx_exists = len(mx_records) > 0
            except (socket.gaierror, socket.herror):
                mx_exists = False
            
            # Calculate confidence
            confidence = 0.8 if mx_exists else 0.3
            
            return ValidationResult(
                field_name=rule.field_name,
                value=email_value,
                status=ValidationStatus.VALID if mx_exists else ValidationStatus.WARNING,
                confidence=confidence,
                source=rule.source,
                criteria_met=mx_exists,
                details={
                    "domain": domain,
                    "mx_record_exists": mx_exists,
                    "mx_records": len(mx_records) if mx_exists else 0
                },
                timestamp=datetime.now()
            )
        
        except Exception as e:
            return ValidationResult(
                field_name=rule.field_name,
                value=email_value,
                status=ValidationStatus.INVALID,
                confidence=0.0,
                source=rule.source,
                criteria_met=False,
                details={"error": str(e)},
                timestamp=datetime.now(),
                error_message=f"Email validation error: {str(e)}"
            )
    
    async def _validate_name_fuzzy(self, rule: ValidationRule, name_value: str, provider_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate name with fuzzy matching using Levenshtein distance
        
        Args:
            rule: Name validation rule
            name_value: Name to validate
            provider_data: Complete provider data for context
            
        Returns:
            ValidationResult for name validation
        """
        try:
            # Get NPI name for comparison (mock for now)
            # In production, this would fetch from NPI registry
            npi_name = "Dr. John Smith"  # Mock NPI name
            
            # Calculate Levenshtein distance
            if rule.criteria.get("case_insensitive", True):
                name_lower = name_value.lower()
                npi_name_lower = npi_name.lower()
            else:
                name_lower = name_value
                npi_name_lower = npi_name
            
            # Calculate similarity ratio
            distance = Levenshtein.distance(name_lower, npi_name_lower)
            max_length = max(len(name_lower), len(npi_name_lower))
            similarity_ratio = 1 - (distance / max_length) if max_length > 0 else 0
            
            # Check threshold
            threshold = rule.criteria["levenshtein_threshold"]
            meets_threshold = similarity_ratio >= threshold
            
            # Calculate confidence
            confidence = similarity_ratio
            
            # Determine status
            if meets_threshold:
                status = ValidationStatus.VALID
            elif similarity_ratio >= 0.7:
                status = ValidationStatus.WARNING
            else:
                status = ValidationStatus.INVALID
            
            return ValidationResult(
                field_name=rule.field_name,
                value=name_value,
                status=status,
                confidence=confidence,
                source=rule.source,
                criteria_met=meets_threshold,
                details={
                    "npi_name": npi_name,
                    "similarity_ratio": similarity_ratio,
                    "levenshtein_distance": distance,
                    "threshold": threshold,
                    "case_insensitive": rule.criteria.get("case_insensitive", True)
                },
                timestamp=datetime.now()
            )
        
        except Exception as e:
            return ValidationResult(
                field_name=rule.field_name,
                value=name_value,
                status=ValidationStatus.INVALID,
                confidence=0.0,
                source=rule.source,
                criteria_met=False,
                details={"error": str(e)},
                timestamp=datetime.now(),
                error_message=f"Name validation error: {str(e)}"
            )
    
    def _calculate_field_summary(self, field_name: str, results: List[ValidationResult]) -> FieldValidationSummary:
        """
        Calculate field validation summary
        
        Args:
            field_name: Name of the field
            results: List of validation results for the field
            
        Returns:
            FieldValidationSummary for the field
        """
        if not results:
            return FieldValidationSummary(
                field_name=field_name,
                overall_confidence=0.0,
                status=ValidationStatus.UNKNOWN,
                results=[],
                weighted_score=0.0,
                validation_count=0
            )
        
        # Calculate weighted confidence
        total_weight = 0.0
        weighted_confidence = 0.0
        
        for result in results:
            weight = self.confidence_weights.get(result.source, 0.1)
            weighted_confidence += result.confidence * weight
            total_weight += weight
        
        overall_confidence = weighted_confidence / total_weight if total_weight > 0 else 0.0
        
        # Determine overall status
        valid_count = sum(1 for r in results if r.status == ValidationStatus.VALID)
        invalid_count = sum(1 for r in results if r.status == ValidationStatus.INVALID)
        warning_count = sum(1 for r in results if r.status == ValidationStatus.WARNING)
        
        if valid_count > 0 and invalid_count == 0:
            status = ValidationStatus.VALID
        elif invalid_count > 0:
            status = ValidationStatus.INVALID
        elif warning_count > 0:
            status = ValidationStatus.WARNING
        else:
            status = ValidationStatus.UNKNOWN
        
        return FieldValidationSummary(
            field_name=field_name,
            overall_confidence=overall_confidence,
            status=status,
            results=results,
            weighted_score=weighted_confidence,
            validation_count=len(results)
        )
    
    def _calculate_overall_confidence(self, field_summaries: Dict[str, FieldValidationSummary]) -> float:
        """
        Calculate overall confidence for provider validation
        
        Args:
            field_summaries: Dictionary of field validation summaries
            
        Returns:
            Overall confidence score
        """
        if not field_summaries:
            return 0.0
        
        # Weight fields by importance
        field_weights = {
            "license_number": 0.25,
            "given_name": 0.20,
            "family_name": 0.20,
            "phone_primary": 0.15,
            "email": 0.10,
            "address_street": 0.10
        }
        
        total_weight = 0.0
        weighted_confidence = 0.0
        
        for field_name, summary in field_summaries.items():
            weight = field_weights.get(field_name, 0.05)
            weighted_confidence += summary.overall_confidence * weight
            total_weight += weight
        
        return weighted_confidence / total_weight if total_weight > 0 else 0.0
    
    def _determine_overall_status(self, field_summaries: Dict[str, FieldValidationSummary]) -> ValidationStatus:
        """
        Determine overall validation status
        
        Args:
            field_summaries: Dictionary of field validation summaries
            
        Returns:
            Overall validation status
        """
        if not field_summaries:
            return ValidationStatus.UNKNOWN
        
        # Count statuses
        valid_count = sum(1 for s in field_summaries.values() if s.status == ValidationStatus.VALID)
        invalid_count = sum(1 for s in field_summaries.values() if s.status == ValidationStatus.INVALID)
        warning_count = sum(1 for s in field_summaries.values() if s.status == ValidationStatus.WARNING)
        
        total_count = len(field_summaries)
        
        # Determine overall status
        if invalid_count > 0:
            return ValidationStatus.INVALID
        elif warning_count > total_count * 0.5:  # More than 50% warnings
            return ValidationStatus.WARNING
        elif valid_count > total_count * 0.8:  # More than 80% valid
            return ValidationStatus.VALID
        else:
            return ValidationStatus.WARNING
    
    async def _apply_rate_limiting(self, source: ValidationSource):
        """Apply rate limiting based on source"""
        if source in self.request_delays:
            delay = self.request_delays[source]
            current_time = datetime.now()
            
            if source in self.last_requests:
                time_since_last = (current_time - self.last_requests[source]).total_seconds()
                if time_since_last < delay:
                    await asyncio.sleep(delay - time_since_last)
            
            self.last_requests[source] = datetime.now()
    
    async def _check_robots_compliance(self, source: ValidationSource) -> bool:
        """
        Check robots.txt compliance for validation source
        
        Args:
            source: Validation source to check
            
        Returns:
            True if compliant, False if blocked
        """
        try:
            # Define base URLs for each source
            base_urls = {
                ValidationSource.NPI: "https://npiregistry.cms.hhs.gov/",
                ValidationSource.GOOGLE_PLACES: "https://maps.googleapis.com/",
                ValidationSource.HOSPITAL_WEBSITE: "https://example-hospital.com/",
                ValidationSource.STATE_BOARD: "https://example-medical-board.com/"
            }
            
            if source not in base_urls:
                return True  # Allow if no URL defined
            
            base_url = base_urls[source]
            
            # Check cache first
            if base_url in self.robots_cache:
                return self.robots_cache[base_url]
            
            # Parse robots.txt
            rp = RobotFileParser()
            robots_url = urljoin(base_url, "/robots.txt")
            rp.set_url(robots_url)
            
            try:
                rp.read()
                
                # Check if our user agent is allowed
                user_agent = self.politeness_headers.get("User-Agent", "Provider-Validation-System/1.0")
                is_allowed = rp.can_fetch(user_agent, base_url)
                
                # Cache result
                self.robots_cache[base_url] = is_allowed
                
                return is_allowed
            
            except Exception as e:
                logger.warning(f"Could not read robots.txt for {base_url}: {e}")
                # Default to allowing if robots.txt cannot be read
                self.robots_cache[base_url] = True
                return True
        
        except Exception as e:
            logger.error(f"Robots.txt compliance check failed: {e}")
            return True  # Default to allowing if check fails


# Example usage and testing functions
async def example_validation():
    """
    Example function demonstrating validation rules
    """
    print("=" * 60)
    print("🔍 VALIDATION RULES ENGINE EXAMPLE")
    print("=" * 60)
    
    # Initialize validation engine
    engine = ValidationRulesEngine()
    
    # Sample provider data
    provider_data = {
        "provider_id": "12345",
        "given_name": "Dr. John Smith",
        "family_name": "Smith",
        "phone_primary": "(555) 123-4567",
        "email": "john.smith@example.com",
        "address_street": "123 Main Street, San Francisco, CA 94102",
        "license_number": "A123456",
        "license_state": "CA"
    }
    
    print("\n📋 Provider Data:")
    for key, value in provider_data.items():
        print(f"   {key}: {value}")
    
    # Validate provider
    print("\n🔍 Running Validation...")
    validation_summary = await engine.validate_provider(provider_data)
    
    print(f"\n✅ Validation Complete!")
    print(f"   Overall Confidence: {validation_summary.overall_confidence:.2f}")
    print(f"   Validation Status: {validation_summary.validation_status.value}")
    print(f"   Total Validations: {validation_summary.total_validations}")
    print(f"   Successful: {validation_summary.successful_validations}")
    print(f"   Failed: {validation_summary.failed_validations}")
    print(f"   Warnings: {validation_summary.warning_validations}")
    
    print(f"\n📊 Field Validation Results:")
    for field_name, field_summary in validation_summary.field_summaries.items():
        print(f"   {field_name}:")
        print(f"      Confidence: {field_summary.overall_confidence:.2f}")
        print(f"      Status: {field_summary.status.value}")
        print(f"      Validations: {field_summary.validation_count}")
        
        for result in field_summary.results:
            print(f"         {result.source.value}: {result.status.value} ({result.confidence:.2f})")
            if result.error_message:
                print(f"            Error: {result.error_message}")


def show_validation_rules():
    """
    Show all validation rules
    """
    print("\n" + "=" * 60)
    print("📋 VALIDATION RULES")
    print("=" * 60)
    
    engine = ValidationRulesEngine()
    
    for rule in engine.rules:
        print(f"\n📋 {rule.field_name.upper()}:")
        print(f"   Rule Type: {rule.rule_type}")
        print(f"   Weight: {rule.weight}")
        print(f"   Source: {rule.source.value}")
        print(f"   Description: {rule.description}")
        print(f"   Criteria: {rule.criteria}")


def show_confidence_weights():
    """
    Show confidence weighting system
    """
    print("\n" + "=" * 60)
    print("⚖️  CONFIDENCE WEIGHTING SYSTEM")
    print("=" * 60)
    
    engine = ValidationRulesEngine()
    
    print("📋 Source Weights:")
    for source, weight in engine.confidence_weights.items():
        print(f"   {source.value}: {weight}")
    
    total_weight = sum(engine.confidence_weights.values())
    print(f"\n   Total Weight: {total_weight}")


if __name__ == "__main__":
    # Run examples
    print("Validation Rules Engine - Examples")
    print("To run examples:")
    print("1. Install dependencies: pip install phonenumbers python-Levenshtein")
    print("2. Run: python -c 'from connectors.validation_rules import example_validation; asyncio.run(example_validation())'")
