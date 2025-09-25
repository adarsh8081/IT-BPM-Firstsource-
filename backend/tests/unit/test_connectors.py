"""
Unit Tests for Connectors with Mock Responses

This module provides comprehensive unit tests for all connectors with mocked external API responses
to ensure reliability and independence from external services.
"""

import pytest
import json
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone
from typing import Dict, Any, List

# Import connectors
from backend.connectors.npi import NPIConnector, NPIResponse
from backend.connectors.google_places import GooglePlacesConnector, PlacesResponse
from backend.connectors.state_board_mock import StateBoardMockConnector, LicenseResponse
from backend.connectors.validation_rules import ValidationEngine, ValidationSource
from backend.connectors.robots_compliance import RobotsComplianceManager

class TestNPIConnector:
    """Test NPI Connector with mocked responses"""
    
    @pytest.fixture
    def npi_connector(self):
        """Create NPI connector instance for testing"""
        return NPIConnector(api_key="test_api_key")
    
    @pytest.fixture
    def mock_npi_response(self):
        """Mock NPI Registry API response"""
        return {
            "result_count": 1,
            "results": [
                {
                    "number": "1234567890",
                    "enumeration_type": "NPI-1",
                    "basic": {
                        "first_name": "JOHN",
                        "last_name": "SMITH",
                        "credential": "MD",
                        "sole_proprietor": "NO",
                        "gender": "M",
                        "enumeration_date": "2010-01-15",
                        "last_updated": "2023-01-15",
                        "certification_date": "2010-01-15",
                        "status": "A"
                    },
                    "addresses": [
                        {
                            "country_code": "US",
                            "country_name": "United States",
                            "address_1": "123 MAIN ST",
                            "city": "SAN FRANCISCO",
                            "state": "CA",
                            "postal_code": "94102",
                            "telephone_number": "555-123-4567",
                            "fax_number": "555-123-4568",
                            "address_type": "DOM",
                            "address_purpose": "LOCATION"
                        }
                    ],
                    "practiceLocations": [
                        {
                            "country_code": "US",
                            "country_name": "United States",
                            "address_1": "123 MAIN ST",
                            "city": "SAN FRANCISCO",
                            "state": "CA",
                            "postal_code": "94102",
                            "telephone_number": "555-123-4567",
                            "fax_number": "555-123-4568",
                            "address_type": "DOM",
                            "address_purpose": "LOCATION"
                        }
                    ],
                    "taxonomies": [
                        {
                            "code": "207Q00000X",
                            "desc": "Family Medicine",
                            "primary": True,
                            "state": "CA",
                            "license": "A12345"
                        }
                    ]
                }
            ]
        }
    
    @pytest.fixture
    def mock_npi_not_found_response(self):
        """Mock NPI Registry API response for not found"""
        return {
            "result_count": 0,
            "results": []
        }
    
    @pytest.fixture
    def mock_npi_error_response(self):
        """Mock NPI Registry API error response"""
        return {
            "error": "Invalid API key",
            "error_description": "The API key provided is invalid"
        }
    
    @pytest.mark.asyncio
    async def test_fetch_provider_by_npi_success(self, npi_connector, mock_npi_response):
        """Test successful provider fetch by NPI"""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_npi_response
            mock_get.return_value = mock_response
            
            result = await npi_connector.fetch_provider_by_npi("1234567890")
            
            assert result is not None
            assert result.npi_number == "1234567890"
            assert result.given_name == "JOHN"
            assert result.family_name == "SMITH"
            assert result.primary_taxonomy == "Family Medicine"
            assert result.license_number == "A12345"
            assert result.license_state == "CA"
            assert result.practice_name is not None
            assert result.overall_confidence > 0.8
    
    @pytest.mark.asyncio
    async def test_fetch_provider_by_npi_not_found(self, npi_connector, mock_npi_not_found_response):
        """Test provider fetch by NPI when not found"""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_npi_not_found_response
            mock_get.return_value = mock_response
            
            result = await npi_connector.fetch_provider_by_npi("0000000000")
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_fetch_provider_by_npi_api_error(self, npi_connector, mock_npi_error_response):
        """Test provider fetch by NPI with API error"""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.json.return_value = mock_npi_error_response
            mock_get.return_value = mock_response
            
            result = await npi_connector.fetch_provider_by_npi("1234567890")
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_fetch_provider_by_name_success(self, npi_connector, mock_npi_response):
        """Test successful provider fetch by name"""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_npi_response
            mock_get.return_value = mock_response
            
            results = await npi_connector.fetch_provider_by_name("JOHN", "SMITH")
            
            assert len(results) == 1
            assert results[0].npi_number == "1234567890"
            assert results[0].given_name == "JOHN"
            assert results[0].family_name == "SMITH"
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, npi_connector):
        """Test rate limiting functionality"""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"result_count": 0, "results": []}
            mock_get.return_value = mock_response
            
            # Make multiple rapid requests
            tasks = []
            for i in range(10):
                tasks.append(npi_connector.fetch_provider_by_npi(f"123456789{i}"))
            
            results = await asyncio.gather(*tasks)
            
            # Should respect rate limiting
            assert mock_get.call_count <= 5  # Assuming 5 requests per second limit
    
    @pytest.mark.asyncio
    async def test_exponential_backoff(self, npi_connector):
        """Test exponential backoff on failures"""
        with patch('httpx.AsyncClient.get') as mock_get:
            # First two calls fail, third succeeds
            mock_responses = [
                Mock(status_code=500, json=Mock(return_value={"error": "Server error"})),
                Mock(status_code=500, json=Mock(return_value={"error": "Server error"})),
                Mock(status_code=200, json=Mock(return_value={"result_count": 0, "results": []}))
            ]
            mock_get.side_effect = mock_responses
            
            result = await npi_connector.fetch_provider_by_npi("1234567890")
            
            # Should have retried with exponential backoff
            assert mock_get.call_count == 3

class TestGooglePlacesConnector:
    """Test Google Places Connector with mocked responses"""
    
    @pytest.fixture
    def places_connector(self):
        """Create Google Places connector instance for testing"""
        return GooglePlacesConnector(api_key="test_api_key")
    
    @pytest.fixture
    def mock_geocoding_response(self):
        """Mock Google Geocoding API response"""
        return {
            "results": [
                {
                    "formatted_address": "123 Main St, San Francisco, CA 94102, USA",
                    "geometry": {
                        "location": {
                            "lat": 37.7749,
                            "lng": -122.4194
                        },
                        "location_type": "ROOFTOP"
                    },
                    "place_id": "ChIJd8BlQ2BZwokRAFQEcDlJRAI",
                    "address_components": [
                        {
                            "long_name": "123",
                            "short_name": "123",
                            "types": ["street_number"]
                        },
                        {
                            "long_name": "Main Street",
                            "short_name": "Main St",
                            "types": ["route"]
                        },
                        {
                            "long_name": "San Francisco",
                            "short_name": "San Francisco",
                            "types": ["locality", "political"]
                        },
                        {
                            "long_name": "California",
                            "short_name": "CA",
                            "types": ["administrative_area_level_1", "political"]
                        },
                        {
                            "long_name": "United States",
                            "short_name": "US",
                            "types": ["country", "political"]
                        },
                        {
                            "long_name": "94102",
                            "short_name": "94102",
                            "types": ["postal_code"]
                        }
                    ]
                }
            ],
            "status": "OK"
        }
    
    @pytest.fixture
    def mock_places_response(self):
        """Mock Google Places API response"""
        return {
            "result": {
                "place_id": "ChIJd8BlQ2BZwokRAFQEcDlJRAI",
                "formatted_address": "123 Main St, San Francisco, CA 94102, USA",
                "geometry": {
                    "location": {
                        "lat": 37.7749,
                        "lng": -122.4194
                    }
                },
                "formatted_phone_number": "(555) 123-4567",
                "international_phone_number": "+1 555-123-4567",
                "website": "https://example.com",
                "business_status": "OPERATIONAL",
                "types": ["hospital", "health", "establishment"]
            },
            "status": "OK"
        }
    
    @pytest.mark.asyncio
    async def test_geocode_address_success(self, places_connector, mock_geocoding_response):
        """Test successful address geocoding"""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_geocoding_response
            mock_get.return_value = mock_response
            
            result = await places_connector.geocode_address(
                street="123 Main St",
                city="San Francisco",
                state="CA",
                zip_code="94102"
            )
            
            assert result is not None
            assert result.place_id == "ChIJd8BlQ2BZwokRAFQEcDlJRAI"
            assert result.latitude == 37.7749
            assert result.longitude == -122.4194
            assert result.confidence > 0.8
            assert result.formatted_address == "123 Main St, San Francisco, CA 94102, USA"
    
    @pytest.mark.asyncio
    async def test_get_place_details_success(self, places_connector, mock_places_response):
        """Test successful place details retrieval"""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_places_response
            mock_get.return_value = mock_response
            
            result = await places_connector.get_place_details("ChIJd8BlQ2BZwokRAFQEcDlJRAI")
            
            assert result is not None
            assert result.place_id == "ChIJd8BlQ2BZwokRAFQEcDlJRAI"
            assert result.phone_number == "+1 555-123-4567"
            assert result.website == "https://example.com"
            assert result.business_status == "OPERATIONAL"
    
    @pytest.mark.asyncio
    async def test_validate_address_match(self, places_connector, mock_geocoding_response):
        """Test address validation with exact match"""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_geocoding_response
            mock_get.return_value = mock_response
            
            result = await places_connector.validate_address(
                street="123 Main St",
                city="San Francisco",
                state="CA",
                zip_code="94102"
            )
            
            assert result.is_match is True
            assert result.confidence > 0.9
            assert result.distance_meters == 0
    
    @pytest.mark.asyncio
    async def test_validate_address_partial_match(self, places_connector):
        """Test address validation with partial match"""
        # Mock response with slightly different address
        partial_match_response = {
            "results": [
                {
                    "formatted_address": "123 Main Street, San Francisco, CA 94102, USA",
                    "geometry": {
                        "location": {
                            "lat": 37.7750,
                            "lng": -122.4195
                        }
                    },
                    "place_id": "ChIJd8BlQ2BZwokRAFQEcDlJRAI"
                }
            ],
            "status": "OK"
        }
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = partial_match_response
            mock_get.return_value = mock_response
            
            result = await places_connector.validate_address(
                street="123 Main St",
                city="San Francisco",
                state="CA",
                zip_code="94102"
            )
            
            assert result.is_match is True
            assert 0.7 < result.confidence < 0.9
            assert result.distance_meters < 100

class TestStateBoardMockConnector:
    """Test State Board Mock Connector with mocked responses"""
    
    @pytest.fixture
    def state_board_connector(self):
        """Create State Board mock connector instance for testing"""
        return StateBoardMockConnector()
    
    @pytest.fixture
    def mock_license_response(self):
        """Mock state board license response"""
        return {
            "license_number": "A12345",
            "license_state": "CA",
            "provider_name": "JOHN SMITH",
            "license_status": "ACTIVE",
            "issue_date": "2010-01-15",
            "expiration_date": "2025-01-15",
            "specialty": "Family Medicine",
            "disciplinary_actions": [],
            "last_updated": "2023-01-15"
        }
    
    @pytest.fixture
    def mock_license_suspended_response(self):
        """Mock state board license response for suspended license"""
        return {
            "license_number": "B67890",
            "license_state": "CA",
            "provider_name": "JANE DOE",
            "license_status": "SUSPENDED",
            "issue_date": "2015-01-15",
            "expiration_date": "2025-01-15",
            "specialty": "Internal Medicine",
            "disciplinary_actions": [
                {
                    "action_date": "2023-06-15",
                    "action_type": "SUSPENSION",
                    "reason": "Professional misconduct"
                }
            ],
            "last_updated": "2023-06-15"
        }
    
    @pytest.mark.asyncio
    async def test_verify_license_success(self, state_board_connector, mock_license_response):
        """Test successful license verification"""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_license_response
            mock_get.return_value = mock_response
            
            result = await state_board_connector.verify_license("A12345", "CA")
            
            assert result is not None
            assert result.license_number == "A12345"
            assert result.license_state == "CA"
            assert result.license_status == "ACTIVE"
            assert result.provider_name == "JOHN SMITH"
            assert result.confidence > 0.8
    
    @pytest.mark.asyncio
    async def test_verify_license_suspended(self, state_board_connector, mock_license_suspended_response):
        """Test license verification for suspended license"""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_license_suspended_response
            mock_get.return_value = mock_response
            
            result = await state_board_connector.verify_license("B67890", "CA")
            
            assert result is not None
            assert result.license_status == "SUSPENDED"
            assert len(result.disciplinary_actions) > 0
            assert result.confidence < 0.5
    
    @pytest.mark.asyncio
    async def test_verify_license_not_found(self, state_board_connector):
        """Test license verification for non-existent license"""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.json.return_value = {"error": "License not found"}
            mock_get.return_value = mock_response
            
            result = await state_board_connector.verify_license("C99999", "CA")
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_robots_compliance(self, state_board_connector):
        """Test robots.txt compliance"""
        with patch('httpx.AsyncClient.get') as mock_get:
            # Mock robots.txt response
            robots_response = Mock()
            robots_response.status_code = 200
            robots_response.text = "User-agent: *\nDisallow: /api/\nCrawl-delay: 1"
            
            # Mock license response
            license_response = Mock()
            license_response.status_code = 200
            license_response.json.return_value = {
                "license_number": "A12345",
                "license_status": "ACTIVE"
            }
            
            mock_get.side_effect = [robots_response, license_response]
            
            result = await state_board_connector.verify_license("A12345", "CA")
            
            # Should respect robots.txt and crawl delay
            assert mock_get.call_count == 2
            assert result is not None

class TestValidationEngine:
    """Test Validation Engine with mocked responses"""
    
    @pytest.fixture
    def validation_engine(self):
        """Create validation engine instance for testing"""
        return ValidationEngine()
    
    @pytest.fixture
    def mock_provider_data(self):
        """Mock provider data for validation"""
        return {
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
            "license_state": "CA"
        }
    
    @pytest.mark.asyncio
    async def test_validate_phone_number_valid(self, validation_engine, mock_provider_data):
        """Test phone number validation with valid number"""
        with patch('phonenumbers.parse') as mock_parse:
            mock_phone = Mock()
            mock_phone.is_valid = True
            mock_phone.national_number = 5551234567
            mock_phone.country_code = 1
            mock_parse.return_value = mock_phone
            
            result = await validation_engine.validate_phone_number(mock_provider_data["phone_primary"])
            
            assert result.is_valid is True
            assert result.confidence > 0.8
            assert result.normalized_number == "+15551234567"
    
    @pytest.mark.asyncio
    async def test_validate_phone_number_invalid(self, validation_engine):
        """Test phone number validation with invalid number"""
        with patch('phonenumbers.parse') as mock_parse:
            mock_phone = Mock()
            mock_phone.is_valid = False
            mock_parse.return_value = mock_phone
            
            result = await validation_engine.validate_phone_number("123-456-789")
            
            assert result.is_valid is False
            assert result.confidence < 0.5
    
    @pytest.mark.asyncio
    async def test_validate_email_valid(self, validation_engine):
        """Test email validation with valid email"""
        with patch('dns.resolver.resolve') as mock_resolve:
            mock_resolve.return_value = [Mock()]
            
            result = await validation_engine.validate_email("john.smith@example.com")
            
            assert result.is_valid is True
            assert result.confidence > 0.8
    
    @pytest.mark.asyncio
    async def test_validate_email_invalid_domain(self, validation_engine):
        """Test email validation with invalid domain"""
        with patch('dns.resolver.resolve') as mock_resolve:
            mock_resolve.side_effect = Exception("No MX record found")
            
            result = await validation_engine.validate_email("john@nonexistent.com")
            
            assert result.is_valid is False
            assert result.confidence < 0.5
    
    @pytest.mark.asyncio
    async def test_validate_address_with_google_places(self, validation_engine, mock_provider_data):
        """Test address validation using Google Places"""
        with patch('backend.connectors.google_places.GooglePlacesConnector.validate_address') as mock_validate:
            mock_validate.return_value = Mock(
                is_match=True,
                confidence=0.9,
                distance_meters=10,
                place_id="test_place_id"
            )
            
            result = await validation_engine.validate_address(
                street=mock_provider_data["address_street"],
                city=mock_provider_data["address_city"],
                state=mock_provider_data["address_state"],
                zip_code=mock_provider_data["address_zip"]
            )
            
            assert result.is_valid is True
            assert result.confidence > 0.8
            assert result.place_id == "test_place_id"
    
    @pytest.mark.asyncio
    async def test_validate_license_with_state_board(self, validation_engine, mock_provider_data):
        """Test license validation using state board"""
        with patch('backend.connectors.state_board_mock.StateBoardMockConnector.verify_license') as mock_verify:
            mock_verify.return_value = Mock(
                license_number="A12345",
                license_status="ACTIVE",
                confidence=0.9
            )
            
            result = await validation_engine.validate_license(
                license_number=mock_provider_data["license_number"],
                license_state=mock_provider_data["license_state"]
            )
            
            assert result.is_valid is True
            assert result.confidence > 0.8
            assert result.license_status == "ACTIVE"
    
    @pytest.mark.asyncio
    async def test_validate_name_fuzzy_match(self, validation_engine):
        """Test name validation with fuzzy matching"""
        with patch('backend.connectors.npi.NPIConnector.fetch_provider_by_npi') as mock_fetch:
            mock_fetch.return_value = Mock(
                given_name="JOHN",
                family_name="SMITH",
                confidence=0.9
            )
            
            result = await validation_engine.validate_name(
                given_name="John",
                family_name="Smith",
                npi_number="1234567890"
            )
            
            assert result.is_valid is True
            assert result.confidence > 0.8
    
    @pytest.mark.asyncio
    async def test_aggregate_confidence_scores(self, validation_engine):
        """Test confidence score aggregation"""
        validation_results = {
            "npi": Mock(confidence=0.9, source=ValidationSource.NPI),
            "google_places": Mock(confidence=0.8, source=ValidationSource.GOOGLE_PLACES),
            "state_board": Mock(confidence=0.85, source=ValidationSource.STATE_BOARD),
            "email": Mock(confidence=0.7, source=ValidationSource.INTERNAL)
        }
        
        aggregated = validation_engine.aggregate_confidence_scores(validation_results)
        
        # Should weight NPI higher (0.4), Google Places (0.25), State Board (0.15), Internal (0.2)
        expected_confidence = (0.9 * 0.4) + (0.8 * 0.25) + (0.85 * 0.15) + (0.7 * 0.2)
        
        assert abs(aggregated - expected_confidence) < 0.01
        assert aggregated > 0.8

class TestRobotsComplianceManager:
    """Test Robots Compliance Manager"""
    
    @pytest.fixture
    def robots_manager(self):
        """Create robots compliance manager instance for testing"""
        return RobotsComplianceManager()
    
    @pytest.mark.asyncio
    async def test_check_robots_txt_allowed(self, robots_manager):
        """Test robots.txt check for allowed path"""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = "User-agent: *\nDisallow: /admin/\nAllow: /api/"
            mock_get.return_value = mock_response
            
            result = await robots_manager.check_robots_txt(
                base_url="https://example.com",
                path="/api/providers"
            )
            
            assert result.is_allowed is True
            assert result.crawl_delay == 0
    
    @pytest.mark.asyncio
    async def test_check_robots_txt_disallowed(self, robots_manager):
        """Test robots.txt check for disallowed path"""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = "User-agent: *\nDisallow: /api/\nCrawl-delay: 1"
            mock_get.return_value = mock_response
            
            result = await robots_manager.check_robots_txt(
                base_url="https://example.com",
                path="/api/providers"
            )
            
            assert result.is_allowed is False
            assert result.crawl_delay == 1
    
    @pytest.mark.asyncio
    async def test_check_robots_txt_no_robots(self, robots_manager):
        """Test robots.txt check when no robots.txt exists"""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response
            
            result = await robots_manager.check_robots_txt(
                base_url="https://example.com",
                path="/api/providers"
            )
            
            assert result.is_allowed is True
            assert result.crawl_delay == 0

# Integration test fixtures
@pytest.fixture
def mock_connector_responses():
    """Comprehensive mock responses for integration testing"""
    return {
        "npi_success": {
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
        "google_places_success": {
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
        "state_board_success": {
            "license_number": "A12345",
            "license_status": "ACTIVE",
            "provider_name": "JOHN SMITH"
        }
    }

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
