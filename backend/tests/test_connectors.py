"""
Tests for API connectors
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch

from backend.connectors.npi_connector import NpiConnector
from backend.connectors.google_places_connector import GooglePlacesConnector
from backend.connectors.state_board_connector import StateBoardConnector

class TestNpiConnector:
    """Test NPI Registry connector"""
    
    @pytest.mark.asyncio
    async def test_validate_npi_valid(self):
        """Test validating a valid NPI"""
        connector = NpiConnector()
        
        # Mock the API response
        mock_response = {
            "result_count": 1,
            "results": [{
                "enumeration_type": "NPI-1",
                "basic": {
                    "status": "A",
                    "credential": "MD",
                    "first_name": "JOHN",
                    "last_name": "DOE"
                },
                "addresses": [{
                    "address_1": "123 MAIN ST",
                    "city": "TEST CITY",
                    "state": "CA",
                    "postal_code": "12345"
                }],
                "taxonomies": [{
                    "desc": "Internal Medicine",
                    "primary": True
                }]
            }]
        }
        
        with patch.object(connector, '_make_request', return_value=mock_response):
            result = await connector.validate_npi("1234567890")
            
            assert result["valid"] is True
            assert result["npi"] == "1234567890"
            assert "details" in result
    
    @pytest.mark.asyncio
    async def test_validate_npi_invalid(self):
        """Test validating an invalid NPI"""
        connector = NpiConnector()
        
        # Mock the API response
        mock_response = {
            "result_count": 0,
            "results": []
        }
        
        with patch.object(connector, '_make_request', return_value=mock_response):
            result = await connector.validate_npi("9999999999")
            
            assert result["valid"] is False
            assert "not found" in result["error"].lower()
    
    @pytest.mark.asyncio
    async def test_validate_npi_invalid_format(self):
        """Test validating NPI with invalid format"""
        connector = NpiConnector()
        
        result = await connector.validate_npi("123")
        
        assert result["valid"] is False
        assert "10 digits" in result["error"]
    
    @pytest.mark.asyncio
    async def test_search_providers(self):
        """Test searching for providers"""
        connector = NpiConnector()
        
        # Mock the API response
        mock_response = {
            "result_count": 2,
            "results": [
                {
                    "enumeration_type": "NPI-1",
                    "basic": {
                        "first_name": "JOHN",
                        "last_name": "DOE"
                    }
                },
                {
                    "enumeration_type": "NPI-1", 
                    "basic": {
                        "first_name": "JANE",
                        "last_name": "SMITH"
                    }
                }
            ]
        }
        
        with patch.object(connector, '_make_request', return_value=mock_response):
            result = await connector.search_providers(
                first_name="John",
                last_name="Doe",
                city="Test City"
            )
            
            assert result["success"] is True
            assert result["result_count"] == 2
            assert len(result["results"]) == 2

class TestGooglePlacesConnector:
    """Test Google Places connector"""
    
    @pytest.mark.asyncio
    async def test_validate_address_valid(self):
        """Test validating a valid address"""
        connector = GooglePlacesConnector()
        
        # Mock the API response
        mock_response = {
            "status": "OK",
            "results": [{
                "formatted_address": "123 Main St, Test City, CA 12345, USA",
                "place_id": "test_place_id",
                "types": ["street_address"],
                "geometry": {
                    "location": {
                        "lat": 37.7749,
                        "lng": -122.4194
                    }
                }
            }]
        }
        
        with patch.object(connector, '_make_request', return_value=mock_response):
            result = await connector.validate_address(
                address_line1="123 Main St",
                city="Test City",
                state="CA",
                zip_code="12345"
            )
            
            assert result["valid"] is True
            assert "123 Main St" in result["formatted_address"]
            assert result["place_id"] == "test_place_id"
    
    @pytest.mark.asyncio
    async def test_validate_address_not_found(self):
        """Test validating an address not found"""
        connector = GooglePlacesConnector()
        
        # Mock the API response
        mock_response = {
            "status": "ZERO_RESULTS",
            "results": []
        }
        
        with patch.object(connector, '_make_request', return_value=mock_response):
            result = await connector.validate_address(
                address_line1="999 Fake St",
                city="Nowhere",
                state="XX",
                zip_code="99999"
            )
            
            assert result["valid"] is False
            assert "not found" in result["error"].lower()
    
    @pytest.mark.asyncio
    async def test_validate_address_mock_mode(self):
        """Test address validation in mock mode (no API key)"""
        connector = GooglePlacesConnector()
        connector.api_key = None  # Simulate no API key
        
        result = await connector.validate_address(
            address_line1="123 Main St",
            city="Test City",
            state="CA",
            zip_code="12345"
        )
        
        assert "mock" in result
        assert result["mock"] is True
        assert "API key not configured" in result["message"]
    
    @pytest.mark.asyncio
    async def test_geocode_address(self):
        """Test geocoding an address"""
        connector = GooglePlacesConnector()
        
        # Mock the API response
        mock_response = {
            "status": "OK",
            "results": [{
                "formatted_address": "123 Main St, Test City, CA 12345, USA",
                "geometry": {
                    "location": {
                        "lat": 37.7749,
                        "lng": -122.4194
                    }
                },
                "place_id": "test_place_id",
                "types": ["street_address"]
            }]
        }
        
        with patch.object(connector, '_make_request', return_value=mock_response):
            result = await connector.geocode_address("123 Main St, Test City, CA")
            
            assert result["success"] is True
            assert result["latitude"] == 37.7749
            assert result["longitude"] == -122.4194
            assert result["place_id"] == "test_place_id"

class TestStateBoardConnector:
    """Test State Medical Board connector"""
    
    @pytest.mark.asyncio
    async def test_validate_license_valid(self):
        """Test validating a valid license"""
        connector = StateBoardConnector()
        
        # Use a known valid license from mock data
        result = await connector.validate_license("A12345", "CA")
        
        assert result["valid"] is True
        assert result["license_number"] == "A12345"
        assert result["state"] == "CA"
        assert result["status"] == "active"
        assert "details" in result
    
    @pytest.mark.asyncio
    async def test_validate_license_expired(self):
        """Test validating an expired license"""
        connector = StateBoardConnector()
        
        # Use a known expired license from mock data
        result = await connector.validate_license("F44444", "CA")
        
        assert result["valid"] is False
        assert "expired" in result["error"].lower()
        assert result["status"] == "expired"
    
    @pytest.mark.asyncio
    async def test_validate_license_invalid(self):
        """Test validating an invalid license"""
        connector = StateBoardConnector()
        
        # Use a known invalid license from mock data
        result = await connector.validate_license("H66666", "CA")
        
        assert result["valid"] is False
        assert "not found" in result["error"].lower()
    
    @pytest.mark.asyncio
    async def test_validate_license_unsupported_state(self):
        """Test validating license for unsupported state"""
        connector = StateBoardConnector()
        
        result = await connector.validate_license("123456", "XX")
        
        assert result["valid"] is False
        assert "not supported" in result["error"].lower()
    
    @pytest.mark.asyncio
    async def test_search_licenses(self):
        """Test searching for licenses"""
        connector = StateBoardConnector()
        
        result = await connector.search_licenses(
            first_name="John",
            last_name="Doe",
            state="CA"
        )
        
        assert result["success"] is True
        assert result["result_count"] >= 0
        assert "results" in result
        assert result["mock"] is True
    
    @pytest.mark.asyncio
    async def test_get_disciplinary_actions(self):
        """Test getting disciplinary actions"""
        connector = StateBoardConnector()
        
        result = await connector.get_disciplinary_actions("A12345", "CA")
        
        assert result["success"] is True
        assert "disciplinary_actions" in result
        assert result["mock"] is True
