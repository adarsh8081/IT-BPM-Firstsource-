"""
Integration Tests for Full Validation Pipeline

This module provides comprehensive integration tests that run the full validation
pipeline on a small subset of providers with known outcomes.
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Any, List
from unittest.mock import patch, Mock, AsyncMock

# Import integration components
from backend.services.validator import ValidationOrchestrator
from backend.services.validation_report_generator import ValidationReportGenerator
from backend.connectors.npi import NPIConnector
from backend.connectors.google_places import GooglePlacesConnector
from backend.connectors.state_board_mock import StateBoardMockConnector
from backend.models.provider import Provider
from backend.models.validation import ValidationJob, ValidationResult
from backend.auth.audit_logger import AuditLogger

class TestValidationIntegration:
    """Integration tests for full validation pipeline"""
    
    @pytest.fixture
    def test_providers(self):
        """Test providers with known expected outcomes"""
        return [
            {
                "provider_id": "PROV_VALID_001",
                "npi_number": "1234567890",
                "given_name": "John",
                "family_name": "Smith",
                "phone_primary": "+1-555-123-4567",
                "email": "john.smith@example.com",
                "address_street": "123 Main St",
                "address_city": "San Francisco",
                "address_state": "CA",
                "address_zip": "94102",
                "license_number": "A12345",
                "license_state": "CA",
                "expected_confidence": 0.85,
                "expected_status": "valid",
                "expected_flags": []
            },
            {
                "provider_id": "PROV_WARNING_001",
                "npi_number": "2345678901",
                "given_name": "Jane",
                "family_name": "Doe",
                "phone_primary": "+1-555-234-5678",
                "email": "jane.doe@invalid-domain.com",  # Invalid email
                "address_street": "456 Oak Ave",
                "address_city": "Los Angeles",
                "address_state": "CA",
                "address_zip": "90210",
                "license_number": "B67890",
                "license_state": "CA",
                "expected_confidence": 0.65,
                "expected_status": "warning",
                "expected_flags": ["LOW_CONFIDENCE_EMAIL"]
            },
            {
                "provider_id": "PROV_INVALID_001",
                "npi_number": "0000000000",  # Invalid NPI
                "given_name": "Invalid",
                "family_name": "Provider",
                "phone_primary": "invalid-phone",
                "email": "invalid@nonexistent.com",
                "address_street": "999 Fake St",
                "address_city": "Nowhere",
                "address_state": "XX",
                "address_zip": "00000",
                "license_number": "C99999",
                "license_state": "CA",
                "expected_confidence": 0.2,
                "expected_status": "invalid",
                "expected_flags": ["INVALID_NPI", "INVALID_ADDRESS", "INVALID_LICENSE"]
            },
            {
                "provider_id": "PROV_SUSPENDED_001",
                "npi_number": "3456789012",
                "given_name": "Suspended",
                "family_name": "Doctor",
                "phone_primary": "+1-555-345-6789",
                "email": "suspended@example.com",
                "address_street": "789 Pine St",
                "address_city": "San Diego",
                "address_state": "CA",
                "address_zip": "92101",
                "license_number": "D11111",
                "license_state": "CA",
                "expected_confidence": 0.4,
                "expected_status": "invalid",
                "expected_flags": ["SUSPENDED_LICENSE"]
            },
            {
                "provider_id": "PROV_PARTIAL_001",
                "npi_number": "4567890123",
                "given_name": "Partial",
                "family_name": "Match",
                "phone_primary": "+1-555-456-7890",
                "email": "partial@example.com",
                "address_street": "321 Elm St",
                "address_city": "San Francisco",
                "address_state": "CA",
                "address_zip": "94103",
                "license_number": "E22222",
                "license_state": "CA",
                "expected_confidence": 0.75,
                "expected_status": "warning",
                "expected_flags": ["LOW_CONFIDENCE_ADDRESS"]
            }
        ]
    
    @pytest.fixture
    def mock_external_apis(self):
        """Mock external API responses"""
        return {
            "npi_valid": {
                "result_count": 1,
                "results": [
                    {
                        "number": "1234567890",
                        "basic": {
                            "first_name": "JOHN",
                            "last_name": "SMITH",
                            "credential": "MD"
                        },
                        "addresses": [
                            {
                                "address_1": "123 MAIN ST",
                                "city": "SAN FRANCISCO",
                                "state": "CA",
                                "postal_code": "94102",
                                "telephone_number": "555-123-4567"
                            }
                        ],
                        "taxonomies": [
                            {
                                "code": "207Q00000X",
                                "desc": "Family Medicine",
                                "primary": True,
                                "license": "A12345"
                            }
                        ]
                    }
                ]
            },
            "npi_not_found": {
                "result_count": 0,
                "results": []
            },
            "google_places_valid": {
                "results": [
                    {
                        "formatted_address": "123 Main St, San Francisco, CA 94102, USA",
                        "geometry": {
                            "location": {"lat": 37.7749, "lng": -122.4194}
                        },
                        "place_id": "ChIJd8BlQ2BZwokRAFQEcDlJRAI"
                    }
                ],
                "status": "OK"
            },
            "google_places_partial": {
                "results": [
                    {
                        "formatted_address": "321 Elm Street, San Francisco, CA 94103, USA",
                        "geometry": {
                            "location": {"lat": 37.7750, "lng": -122.4195}
                        },
                        "place_id": "ChIJd8BlQ2BZwokRAFQEcDlJRAI"
                    }
                ],
                "status": "OK"
            },
            "google_places_not_found": {
                "results": [],
                "status": "ZERO_RESULTS"
            },
            "state_board_active": {
                "license_number": "A12345",
                "license_status": "ACTIVE",
                "provider_name": "JOHN SMITH"
            },
            "state_board_suspended": {
                "license_number": "D11111",
                "license_status": "SUSPENDED",
                "provider_name": "SUSPENDED DOCTOR",
                "disciplinary_actions": [
                    {
                        "action_date": "2023-06-15",
                        "action_type": "SUSPENSION",
                        "reason": "Professional misconduct"
                    }
                ]
            },
            "state_board_not_found": {
                "error": "License not found"
            }
        }
    
    @pytest.fixture
    async def orchestrator_with_mocks(self, mock_external_apis):
        """Create orchestrator with mocked external APIs"""
        with patch('redis.Redis') as mock_redis:
            mock_redis_client = Mock()
            mock_redis.return_value = mock_redis_client
            
            orchestrator = ValidationOrchestrator(
                database_url="sqlite:///:memory:",
                redis_client=mock_redis_client
            )
            
            # Mock external API calls
            with patch('httpx.AsyncClient.get') as mock_get:
                def mock_api_response(url, **kwargs):
                    mock_response = Mock()
                    
                    if "npiregistry.cms.hhs.gov" in str(url):
                        if "1234567890" in str(url):
                            mock_response.json.return_value = mock_external_apis["npi_valid"]
                        elif "3456789012" in str(url):
                            mock_response.json.return_value = mock_external_apis["npi_valid"]
                        elif "4567890123" in str(url):
                            mock_response.json.return_value = mock_external_apis["npi_valid"]
                        else:
                            mock_response.json.return_value = mock_external_apis["npi_not_found"]
                    
                    elif "maps.googleapis.com" in str(url):
                        if "123 Main St" in str(url):
                            mock_response.json.return_value = mock_external_apis["google_places_valid"]
                        elif "321 Elm St" in str(url):
                            mock_response.json.return_value = mock_external_apis["google_places_partial"]
                        else:
                            mock_response.json.return_value = mock_external_apis["google_places_not_found"]
                    
                    elif "stateboard.mock" in str(url):
                        if "A12345" in str(url):
                            mock_response.json.return_value = mock_external_apis["state_board_active"]
                        elif "D11111" in str(url):
                            mock_response.json.return_value = mock_external_apis["state_board_suspended"]
                        else:
                            mock_response.json.return_value = mock_external_apis["state_board_not_found"]
                    
                    mock_response.status_code = 200
                    return mock_response
                
                mock_get.side_effect = mock_api_response
                
                yield orchestrator
    
    @pytest.mark.asyncio
    async def test_valid_provider_integration(self, orchestrator_with_mocks, test_providers):
        """Test integration for valid provider with high confidence"""
        valid_provider = test_providers[0]
        
        result = await orchestrator_with_mocks.validate_single_provider(valid_provider)
        
        # Assertions for valid provider
        assert result is not None
        assert result.provider_id == valid_provider["provider_id"]
        assert result.overall_confidence >= valid_provider["expected_confidence"]
        assert result.validation_status == valid_provider["expected_status"]
        assert len(result.flags) == 0
        
        # Check field confidence scores
        assert result.field_confidence["npi_number"] > 0.8
        assert result.field_confidence["address"] > 0.8
        assert result.field_confidence["license"] > 0.8
        assert result.field_confidence["email"] > 0.7
        assert result.field_confidence["phone"] > 0.7
    
    @pytest.mark.asyncio
    async def test_warning_provider_integration(self, orchestrator_with_mocks, test_providers):
        """Test integration for provider with warnings"""
        warning_provider = test_providers[1]
        
        result = await orchestrator_with_mocks.validate_single_provider(warning_provider)
        
        # Assertions for warning provider
        assert result is not None
        assert result.provider_id == warning_provider["provider_id"]
        assert result.overall_confidence >= warning_provider["expected_confidence"]
        assert result.validation_status == warning_provider["expected_status"]
        assert "LOW_CONFIDENCE_EMAIL" in result.flags
        
        # Check field confidence scores
        assert result.field_confidence["npi_number"] > 0.8
        assert result.field_confidence["address"] > 0.8
        assert result.field_confidence["license"] > 0.8
        assert result.field_confidence["email"] < 0.5  # Invalid email domain
        assert result.field_confidence["phone"] > 0.7
    
    @pytest.mark.asyncio
    async def test_invalid_provider_integration(self, orchestrator_with_mocks, test_providers):
        """Test integration for invalid provider"""
        invalid_provider = test_providers[2]
        
        result = await orchestrator_with_mocks.validate_single_provider(invalid_provider)
        
        # Assertions for invalid provider
        assert result is not None
        assert result.provider_id == invalid_provider["provider_id"]
        assert result.overall_confidence <= invalid_provider["expected_confidence"]
        assert result.validation_status == invalid_provider["expected_status"]
        assert "INVALID_NPI" in result.flags
        assert "INVALID_ADDRESS" in result.flags
        assert "INVALID_LICENSE" in result.flags
        
        # Check field confidence scores
        assert result.field_confidence["npi_number"] < 0.3
        assert result.field_confidence["address"] < 0.3
        assert result.field_confidence["license"] < 0.3
        assert result.field_confidence["email"] < 0.3
        assert result.field_confidence["phone"] < 0.3
    
    @pytest.mark.asyncio
    async def test_suspended_license_integration(self, orchestrator_with_mocks, test_providers):
        """Test integration for provider with suspended license"""
        suspended_provider = test_providers[3]
        
        result = await orchestrator_with_mocks.validate_single_provider(suspended_provider)
        
        # Assertions for suspended provider
        assert result is not None
        assert result.provider_id == suspended_provider["provider_id"]
        assert result.overall_confidence <= suspended_provider["expected_confidence"]
        assert result.validation_status == suspended_provider["expected_status"]
        assert "SUSPENDED_LICENSE" in result.flags
        
        # Check field confidence scores
        assert result.field_confidence["npi_number"] > 0.8
        assert result.field_confidence["address"] > 0.8
        assert result.field_confidence["license"] < 0.5  # Suspended license
        assert result.field_confidence["email"] > 0.7
        assert result.field_confidence["phone"] > 0.7
    
    @pytest.mark.asyncio
    async def test_partial_match_integration(self, orchestrator_with_mocks, test_providers):
        """Test integration for provider with partial address match"""
        partial_provider = test_providers[4]
        
        result = await orchestrator_with_mocks.validate_single_provider(partial_provider)
        
        # Assertions for partial match provider
        assert result is not None
        assert result.provider_id == partial_provider["provider_id"]
        assert result.overall_confidence >= partial_provider["expected_confidence"]
        assert result.validation_status == partial_provider["expected_status"]
        assert "LOW_CONFIDENCE_ADDRESS" in result.flags
        
        # Check field confidence scores
        assert result.field_confidence["npi_number"] > 0.8
        assert result.field_confidence["address"] < 0.8  # Partial match
        assert result.field_confidence["license"] > 0.8
        assert result.field_confidence["email"] > 0.7
        assert result.field_confidence["phone"] > 0.7
    
    @pytest.mark.asyncio
    async def test_batch_validation_integration(self, orchestrator_with_mocks, test_providers):
        """Test batch validation integration with multiple providers"""
        # Start batch validation
        job_id = await orchestrator_with_mocks.start_batch_validation(test_providers)
        
        assert job_id is not None
        assert len(job_id) > 0
        
        # Wait for batch completion (in real scenario, this would be async)
        # For testing, we'll simulate the batch completion
        await asyncio.sleep(0.1)  # Simulate processing time
        
        # Check job status
        job_status = await orchestrator_with_mocks.get_job_status(job_id)
        
        assert job_status is not None
        assert job_status.job_id == job_id
        assert job_status.status in ["completed", "processing"]
        
        if job_status.status == "completed":
            # Get validation report
            report = await orchestrator_with_mocks.get_validation_report(job_id)
            
            assert report is not None
            assert len(report.results) == len(test_providers)
            
            # Verify each provider result
            for i, provider in enumerate(test_providers):
                result = report.results[i]
                assert result.provider_id == provider["provider_id"]
                assert result.overall_confidence >= provider["expected_confidence"] * 0.8  # Allow some variance
                assert result.validation_status == provider["expected_status"]
    
    @pytest.mark.asyncio
    async def test_database_writes_integration(self, orchestrator_with_mocks, test_providers):
        """Test that validation results are properly written to database"""
        valid_provider = test_providers[0]
        
        result = await orchestrator_with_mocks.validate_single_provider(valid_provider)
        
        # Verify result is saved to database
        assert result.id is not None
        assert result.created_at is not None
        
        # In a real integration test, we would query the database to verify
        # the record was saved with correct data
    
    @pytest.mark.asyncio
    async def test_confidence_threshold_assertions(self, orchestrator_with_mocks, test_providers):
        """Test that confidence thresholds are met for known outcomes"""
        for provider in test_providers:
            result = await orchestrator_with_mocks.validate_single_provider(provider)
            
            # Assert confidence is within expected range
            expected_min = provider["expected_confidence"] * 0.8
            expected_max = provider["expected_confidence"] * 1.2
            
            assert expected_min <= result.overall_confidence <= expected_max, \
                f"Provider {provider['provider_id']} confidence {result.overall_confidence} not in expected range [{expected_min}, {expected_max}]"
            
            # Assert status matches expected
            assert result.validation_status == provider["expected_status"], \
                f"Provider {provider['provider_id']} status {result.validation_status} does not match expected {provider['expected_status']}"
            
            # Assert flags match expected
            for expected_flag in provider["expected_flags"]:
                assert expected_flag in result.flags, \
                    f"Provider {provider['provider_id']} missing expected flag: {expected_flag}"
    
    @pytest.mark.asyncio
    async def test_validation_report_generation_integration(self, orchestrator_with_mocks, test_providers):
        """Test validation report generation integration"""
        valid_provider = test_providers[0]
        
        result = await orchestrator_with_mocks.validate_single_provider(valid_provider)
        
        # Generate validation report
        report_generator = ValidationReportGenerator()
        report = report_generator.generate_report(result)
        
        assert report is not None
        assert report.provider_id == valid_provider["provider_id"]
        assert report.overall_confidence == result.overall_confidence
        assert report.validation_status == result.validation_status
        
        # Check report structure
        assert len(report.field_analysis) > 0
        assert len(report.insights) > 0
        assert len(report.recommendations) > 0
        
        # Verify field analysis
        assert "npi_number" in report.field_analysis
        assert "address" in report.field_analysis
        assert "license" in report.field_analysis
        assert "email" in report.field_analysis
        assert "phone" in report.field_analysis
    
    @pytest.mark.asyncio
    async def test_audit_logging_integration(self, orchestrator_with_mocks, test_providers):
        """Test that audit logging works correctly during validation"""
        valid_provider = test_providers[0]
        
        # Mock audit logger
        with patch('backend.auth.audit_logger.get_audit_logger') as mock_audit:
            mock_audit_instance = Mock()
            mock_audit.return_value = mock_audit_instance
            
            result = await orchestrator_with_mocks.validate_single_provider(valid_provider)
            
            # Verify audit logging was called
            assert mock_audit_instance.log_event.called
            
            # Check audit log calls
            audit_calls = mock_audit_instance.log_event.call_args_list
            
            # Should have logged validation start and completion
            assert len(audit_calls) >= 2
            
            # Check for validation start log
            start_call = audit_calls[0]
            assert start_call[1]["action"] == AuditAction.VALIDATION_RUN
            
            # Check for validation completion log
            completion_call = audit_calls[-1]
            assert completion_call[1]["success"] is True

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
