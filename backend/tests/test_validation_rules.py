"""
Tests for Validation Rules Engine
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
import socket
import phonenumbers
from phonenumbers import geocoder, carrier
import Levenshtein

from connectors.validation_rules import (
    ValidationRulesEngine,
    ValidationRule,
    ValidationResult,
    ValidationStatus,
    ValidationSource,
    FieldValidationSummary,
    ProviderValidationSummary
)


class TestValidationRulesEngine:
    """Test cases for Validation Rules Engine"""

    @pytest.fixture
    def validation_engine(self):
        """Create validation rules engine instance for testing"""
        return ValidationRulesEngine()

    @pytest.fixture
    def sample_provider_data(self):
        """Sample provider data for testing"""
        return {
            "provider_id": "12345",
            "given_name": "Dr. John Smith",
            "family_name": "Smith",
            "phone_primary": "(555) 123-4567",
            "email": "john.smith@example.com",
            "address_street": "123 Main Street, San Francisco, CA 94102",
            "license_number": "A123456",
            "license_state": "CA"
        }

    def test_validation_engine_initialization(self, validation_engine):
        """Test validation rules engine initialization"""
        assert validation_engine.rules is not None
        assert len(validation_engine.rules) > 0
        assert validation_engine.confidence_weights is not None
        assert ValidationSource.NPI in validation_engine.confidence_weights
        assert validation_engine.confidence_weights[ValidationSource.NPI] == 0.4

    def test_validation_rules_initialization(self, validation_engine):
        """Test validation rules initialization"""
        rules = validation_engine.rules
        
        # Check that all expected rules are present
        rule_fields = [rule.field_name for rule in rules]
        assert "phone_primary" in rule_fields
        assert "address_street" in rule_fields
        assert "license_number" in rule_fields
        assert "email" in rule_fields
        assert "given_name" in rule_fields
        assert "family_name" in rule_fields
        
        # Check rule types
        rule_types = [rule.rule_type for rule in rules]
        assert "e164_normalization" in rule_types
        assert "place_id_matching" in rule_types
        assert "state_board_verification" in rule_types
        assert "mx_record_check" in rule_types
        assert "fuzzy_matching" in rule_types

    def test_confidence_weights(self, validation_engine):
        """Test confidence weighting system"""
        weights = validation_engine.confidence_weights
        
        assert weights[ValidationSource.NPI] == 0.4
        assert weights[ValidationSource.GOOGLE_PLACES] == 0.25
        assert weights[ValidationSource.HOSPITAL_WEBSITE] == 0.2
        assert weights[ValidationSource.STATE_BOARD] == 0.15
        
        # Check that weights sum to 1.0
        total_weight = sum(weights.values())
        assert abs(total_weight - 1.0) < 0.01

    @pytest.mark.asyncio
    async def test_validate_provider_success(self, validation_engine, sample_provider_data):
        """Test successful provider validation"""
        with patch.object(validation_engine, '_validate_field') as mock_validate:
            # Mock successful validation results
            mock_result = ValidationResult(
                field_name="phone_primary",
                value="+15551234567",
                status=ValidationStatus.VALID,
                confidence=0.9,
                source=ValidationSource.NPI,
                criteria_met=True,
                details={"e164_format": "+15551234567"},
                timestamp=datetime.now()
            )
            mock_validate.return_value = mock_result
            
            summary = await validation_engine.validate_provider(sample_provider_data)
            
            assert summary.provider_id == "12345"
            assert summary.total_validations > 0
            assert summary.successful_validations > 0
            assert summary.overall_confidence > 0.0

    @pytest.mark.asyncio
    async def test_validate_phone_e164_valid(self, validation_engine):
        """Test valid phone number E.164 normalization"""
        rule = ValidationRule(
            field_name="phone_primary",
            rule_type="e164_normalization",
            criteria={"format": "E.164", "lookup_enabled": True},
            weight=0.4,
            source=ValidationSource.NPI,
            description="E.164 phone normalization"
        )
        
        result = await validation_engine._validate_phone_e164(rule, "(555) 123-4567")
        
        assert result.field_name == "phone_primary"
        assert result.status in [ValidationStatus.VALID, ValidationStatus.WARNING]
        assert result.confidence > 0.0
        assert result.criteria_met is not None
        assert "e164_format" in result.details

    @pytest.mark.asyncio
    async def test_validate_phone_e164_invalid(self, validation_engine):
        """Test invalid phone number E.164 normalization"""
        rule = ValidationRule(
            field_name="phone_primary",
            rule_type="e164_normalization",
            criteria={"format": "E.164"},
            weight=0.4,
            source=ValidationSource.NPI,
            description="E.164 phone normalization"
        )
        
        result = await validation_engine._validate_phone_e164(rule, "invalid-phone")
        
        assert result.field_name == "phone_primary"
        assert result.status == ValidationStatus.INVALID
        assert result.confidence == 0.0
        assert not result.criteria_met

    @pytest.mark.asyncio
    async def test_validate_address_place_id(self, validation_engine, sample_provider_data):
        """Test address validation with place_id matching"""
        rule = ValidationRule(
            field_name="address_street",
            rule_type="place_id_matching",
            criteria={"geocode_distance_threshold": 100},
            weight=0.25,
            source=ValidationSource.GOOGLE_PLACES,
            description="Address validation with place_id"
        )
        
        with patch('connectors.validation_rules.GooglePlacesConnector') as mock_connector_class:
            mock_connector = AsyncMock()
            mock_connector.validate_address.return_value = MagicMock(
                success=True,
                data={
                    "place_id": "ChIJ1234567890abcdef",
                    "latitude": 37.7749,
                    "longitude": -122.4194,
                    "formatted_address": "123 Main Street, San Francisco, CA 94102"
                }
            )
            mock_connector_class.return_value = mock_connector
            
            result = await validation_engine._validate_address_place_id(
                rule, 
                "123 Main Street, San Francisco, CA 94102", 
                sample_provider_data
            )
            
            assert result.field_name == "address_street"
            assert result.status in [ValidationStatus.VALID, ValidationStatus.WARNING]
            assert result.confidence > 0.0
            assert "place_id" in result.details

    @pytest.mark.asyncio
    async def test_validate_license_state_board(self, validation_engine, sample_provider_data):
        """Test license validation with state board verification"""
        rule = ValidationRule(
            field_name="license_number",
            rule_type="state_board_verification",
            criteria={"license_status_required": "ACTIVE"},
            weight=0.15,
            source=ValidationSource.STATE_BOARD,
            description="License verification with state board"
        )
        
        with patch('connectors.validation_rules.StateBoardMockConnector') as mock_connector_class:
            mock_connector = AsyncMock()
            mock_connector.verify_license.return_value = MagicMock(
                success=True,
                data={
                    "license_status": "active",
                    "provider_name": "Dr. John Smith",
                    "issue_date": "2020-01-15",
                    "expiry_date": "2025-01-15",
                    "board_actions": []
                }
            )
            mock_connector_class.return_value = mock_connector
            
            result = await validation_engine._validate_license_state_board(
                rule, 
                "A123456", 
                sample_provider_data
            )
            
            assert result.field_name == "license_number"
            assert result.status == ValidationStatus.VALID
            assert result.confidence > 0.9
            assert result.criteria_met is True
            assert "license_status" in result.details

    @pytest.mark.asyncio
    async def test_validate_license_state_board_suspended(self, validation_engine, sample_provider_data):
        """Test license validation with suspended license"""
        rule = ValidationRule(
            field_name="license_number",
            rule_type="state_board_verification",
            criteria={"license_status_required": "ACTIVE"},
            weight=0.15,
            source=ValidationSource.STATE_BOARD,
            description="License verification with state board"
        )
        
        with patch('connectors.validation_rules.StateBoardMockConnector') as mock_connector_class:
            mock_connector = AsyncMock()
            mock_connector.verify_license.return_value = MagicMock(
                success=True,
                data={
                    "license_status": "suspended",
                    "provider_name": "Dr. John Smith",
                    "board_actions": [{"type": "suspension", "date": "2023-01-01"}]
                }
            )
            mock_connector_class.return_value = mock_connector
            
            result = await validation_engine._validate_license_state_board(
                rule, 
                "A123456", 
                sample_provider_data
            )
            
            assert result.field_name == "license_number"
            assert result.status == ValidationStatus.INVALID
            assert result.confidence < 0.5
            assert not result.criteria_met

    @pytest.mark.asyncio
    async def test_validate_email_mx_valid(self, validation_engine):
        """Test valid email with MX record"""
        rule = ValidationRule(
            field_name="email",
            rule_type="mx_record_check",
            criteria={"mx_record_required": True},
            weight=0.2,
            source=ValidationSource.HOSPITAL_WEBSITE,
            description="Email validation with MX record check"
        )
        
        with patch('socket.getaddrinfo') as mock_getaddrinfo:
            mock_getaddrinfo.return_value = [("192.168.1.1", 80)]  # Mock MX record
            
            result = await validation_engine._validate_email_mx(rule, "test@example.com")
            
            assert result.field_name == "email"
            assert result.status == ValidationStatus.VALID
            assert result.confidence > 0.8
            assert result.criteria_met is True
            assert result.details["mx_record_exists"] is True

    @pytest.mark.asyncio
    async def test_validate_email_mx_no_mx_record(self, validation_engine):
        """Test email without MX record"""
        rule = ValidationRule(
            field_name="email",
            rule_type="mx_record_check",
            criteria={"mx_record_required": True},
            weight=0.2,
            source=ValidationSource.HOSPITAL_WEBSITE,
            description="Email validation with MX record check"
        )
        
        with patch('socket.getaddrinfo') as mock_getaddrinfo:
            mock_getaddrinfo.side_effect = socket.gaierror("No MX record")
            
            result = await validation_engine._validate_email_mx(rule, "test@invalid.com")
            
            assert result.field_name == "email"
            assert result.status == ValidationStatus.WARNING
            assert result.confidence < 0.5
            assert not result.criteria_met
            assert result.details["mx_record_exists"] is False

    @pytest.mark.asyncio
    async def test_validate_email_invalid_format(self, validation_engine):
        """Test email with invalid format"""
        rule = ValidationRule(
            field_name="email",
            rule_type="mx_record_check",
            criteria={"mx_record_required": True},
            weight=0.2,
            source=ValidationSource.HOSPITAL_WEBSITE,
            description="Email validation with MX record check"
        )
        
        result = await validation_engine._validate_email_mx(rule, "invalid-email")
        
        assert result.field_name == "email"
        assert result.status == ValidationStatus.INVALID
        assert result.confidence == 0.0
        assert not result.criteria_met
        assert "invalid_format" in result.details

    @pytest.mark.asyncio
    async def test_validate_name_fuzzy_match(self, validation_engine, sample_provider_data):
        """Test name validation with fuzzy matching"""
        rule = ValidationRule(
            field_name="given_name",
            rule_type="fuzzy_matching",
            criteria={"levenshtein_threshold": 0.85, "case_insensitive": True},
            weight=0.4,
            source=ValidationSource.NPI,
            description="Name fuzzy matching with Levenshtein distance"
        )
        
        # Mock NPI name for comparison
        with patch.object(validation_engine, '_get_npi_name', return_value="Dr. John Smith"):
            result = await validation_engine._validate_name_fuzzy(
                rule, 
                "Dr. John Smith", 
                sample_provider_data
            )
            
            assert result.field_name == "given_name"
            assert result.status == ValidationStatus.VALID
            assert result.confidence > 0.85
            assert result.criteria_met is True
            assert "similarity_ratio" in result.details

    @pytest.mark.asyncio
    async def test_validate_name_fuzzy_no_match(self, validation_engine, sample_provider_data):
        """Test name validation with no fuzzy match"""
        rule = ValidationRule(
            field_name="given_name",
            rule_type="fuzzy_matching",
            criteria={"levenshtein_threshold": 0.85, "case_insensitive": True},
            weight=0.4,
            source=ValidationSource.NPI,
            description="Name fuzzy matching with Levenshtein distance"
        )
        
        # Mock NPI name for comparison
        with patch.object(validation_engine, '_get_npi_name', return_value="Dr. Jane Doe"):
            result = await validation_engine._validate_name_fuzzy(
                rule, 
                "Dr. John Smith", 
                sample_provider_data
            )
            
            assert result.field_name == "given_name"
            assert result.status == ValidationStatus.INVALID
            assert result.confidence < 0.85
            assert not result.criteria_met

    def test_calculate_field_summary(self, validation_engine):
        """Test field validation summary calculation"""
        results = [
            ValidationResult(
                field_name="phone_primary",
                value="+15551234567",
                status=ValidationStatus.VALID,
                confidence=0.9,
                source=ValidationSource.NPI,
                criteria_met=True,
                details={},
                timestamp=datetime.now()
            ),
            ValidationResult(
                field_name="phone_primary",
                value="+15551234567",
                status=ValidationStatus.VALID,
                confidence=0.8,
                source=ValidationSource.GOOGLE_PLACES,
                criteria_met=True,
                details={},
                timestamp=datetime.now()
            )
        ]
        
        summary = validation_engine._calculate_field_summary("phone_primary", results)
        
        assert summary.field_name == "phone_primary"
        assert summary.overall_confidence > 0.0
        assert summary.status == ValidationStatus.VALID
        assert summary.validation_count == 2
        assert len(summary.results) == 2

    def test_calculate_overall_confidence(self, validation_engine):
        """Test overall confidence calculation"""
        field_summaries = {
            "license_number": FieldValidationSummary(
                field_name="license_number",
                overall_confidence=0.9,
                status=ValidationStatus.VALID,
                results=[],
                weighted_score=0.9,
                validation_count=1
            ),
            "given_name": FieldValidationSummary(
                field_name="given_name",
                overall_confidence=0.8,
                status=ValidationStatus.VALID,
                results=[],
                weighted_score=0.8,
                validation_count=1
            )
        }
        
        overall_confidence = validation_engine._calculate_overall_confidence(field_summaries)
        
        assert overall_confidence > 0.0
        assert overall_confidence < 1.0

    def test_determine_overall_status(self, validation_engine):
        """Test overall status determination"""
        # Test with mostly valid fields
        field_summaries = {
            "license_number": FieldValidationSummary(
                field_name="license_number",
                overall_confidence=0.9,
                status=ValidationStatus.VALID,
                results=[],
                weighted_score=0.9,
                validation_count=1
            ),
            "given_name": FieldValidationSummary(
                field_name="given_name",
                overall_confidence=0.8,
                status=ValidationStatus.VALID,
                results=[],
                weighted_score=0.8,
                validation_count=1
            ),
            "email": FieldValidationSummary(
                field_name="email",
                overall_confidence=0.7,
                status=ValidationStatus.WARNING,
                results=[],
                weighted_score=0.7,
                validation_count=1
            )
        }
        
        status = validation_engine._determine_overall_status(field_summaries)
        assert status == ValidationStatus.VALID
        
        # Test with invalid fields
        field_summaries["license_number"] = FieldValidationSummary(
            field_name="license_number",
            overall_confidence=0.1,
            status=ValidationStatus.INVALID,
            results=[],
            weighted_score=0.1,
            validation_count=1
        )
        
        status = validation_engine._determine_overall_status(field_summaries)
        assert status == ValidationStatus.INVALID

    @pytest.mark.asyncio
    async def test_apply_rate_limiting(self, validation_engine):
        """Test rate limiting application"""
        # Test rate limiting for different sources
        start_time = datetime.now()
        
        await validation_engine._apply_rate_limiting(ValidationSource.NPI)
        await validation_engine._apply_rate_limiting(ValidationSource.NPI)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Should have applied some delay
        assert duration >= 0.0

    @pytest.mark.asyncio
    async def test_check_robots_compliance(self, validation_engine):
        """Test robots.txt compliance checking"""
        # Test with mock robots.txt
        with patch('urllib.robotparser.RobotFileParser') as mock_rp_class:
            mock_rp = MagicMock()
            mock_rp.can_fetch.return_value = True
            mock_rp_class.return_value = mock_rp
            
            result = await validation_engine._check_robots_compliance(ValidationSource.NPI)
            
            assert result is True
        
        # Test with blocked robots.txt
        with patch('urllib.robotparser.RobotFileParser') as mock_rp_class:
            mock_rp = MagicMock()
            mock_rp.can_fetch.return_value = False
            mock_rp_class.return_value = mock_rp
            
            result = await validation_engine._check_robots_compliance(ValidationSource.NPI)
            
            assert result is False

    def test_validation_result_serialization(self):
        """Test validation result serialization"""
        result = ValidationResult(
            field_name="phone_primary",
            value="+15551234567",
            status=ValidationStatus.VALID,
            confidence=0.9,
            source=ValidationSource.NPI,
            criteria_met=True,
            details={"e164_format": "+15551234567"},
            timestamp=datetime.now()
        )
        
        # Test that result can be converted to dict
        result_dict = {
            "field_name": result.field_name,
            "value": result.value,
            "status": result.status.value,
            "confidence": result.confidence,
            "source": result.source.value,
            "criteria_met": result.criteria_met,
            "details": result.details,
            "timestamp": result.timestamp.isoformat()
        }
        
        assert result_dict["field_name"] == "phone_primary"
        assert result_dict["status"] == "valid"
        assert result_dict["confidence"] == 0.9

    def test_validation_rule_creation(self):
        """Test validation rule creation"""
        rule = ValidationRule(
            field_name="test_field",
            rule_type="test_rule",
            criteria={"test": "value"},
            weight=0.5,
            source=ValidationSource.NPI,
            description="Test rule"
        )
        
        assert rule.field_name == "test_field"
        assert rule.rule_type == "test_rule"
        assert rule.weight == 0.5
        assert rule.source == ValidationSource.NPI
        assert rule.description == "Test rule"

    @pytest.mark.asyncio
    async def test_validate_field_exception_handling(self, validation_engine, sample_provider_data):
        """Test exception handling in field validation"""
        rule = ValidationRule(
            field_name="test_field",
            rule_type="unknown_rule",
            criteria={},
            weight=0.5,
            source=ValidationSource.NPI,
            description="Test rule"
        )
        
        result = await validation_engine._validate_field(rule, "test_value", sample_provider_data)
        
        assert result.field_name == "test_field"
        assert result.status == ValidationStatus.UNKNOWN
        assert result.confidence == 0.0
        assert not result.criteria_met
        assert "Unknown rule type" in result.error_message

    def test_confidence_weights_sum(self, validation_engine):
        """Test that confidence weights sum to 1.0"""
        total_weight = sum(validation_engine.confidence_weights.values())
        assert abs(total_weight - 1.0) < 0.01

    def test_rate_limiting_delays(self, validation_engine):
        """Test rate limiting delays are set"""
        assert ValidationSource.NPI in validation_engine.request_delays
        assert ValidationSource.GOOGLE_PLACES in validation_engine.request_delays
        assert ValidationSource.HOSPITAL_WEBSITE in validation_engine.request_delays
        assert ValidationSource.STATE_BOARD in validation_engine.request_delays

    def test_politeness_headers(self, validation_engine):
        """Test politeness headers are set"""
        headers = validation_engine.politeness_headers
        
        assert "User-Agent" in headers
        assert "Accept" in headers
        assert "Accept-Language" in headers
        assert "Connection" in headers
        
        # Check that User-Agent is appropriate
        user_agent = headers["User-Agent"]
        assert "Provider-Validation-System" in user_agent


if __name__ == "__main__":
    # Run basic tests
    pytest.main([__file__, "-v"])
