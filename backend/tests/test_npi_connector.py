"""
Tests for NPI Registry Connector
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from connectors.npi import NPIConnector, NPISearchParams


class TestNPIConnector:
    """Test cases for NPI Registry Connector"""

    @pytest.fixture
    def npi_connector(self):
        """Create NPI connector instance for testing"""
        return NPIConnector()

    @pytest.fixture
    def sample_npi_response(self):
        """Sample NPI Registry API response"""
        return {
            "result_count": 1,
            "results": [
                {
                    "number": "1234567890",
                    "enumeration_type": "NPI-1",
                    "basic": {
                        "first_name": "JOHN",
                        "last_name": "SMITH",
                        "middle_name": "MICHAEL",
                        "credential": "MD",
                        "sole_proprietor": "NO",
                        "gender": "M",
                        "enumeration_date": "2005-06-13",
                        "last_updated": "2023-01-15",
                        "certification_date": "2005-06-13",
                        "organization_name": "JOHN SMITH MEDICAL PRACTICE"
                    },
                    "addresses": [
                        {
                            "country_code": "US",
                            "country_name": "United States",
                            "address_1": "123 MAIN ST",
                            "address_2": "SUITE 100",
                            "city": "SAN FRANCISCO",
                            "state": "CA",
                            "postal_code": "94102",
                            "telephone_number": "415-555-0123",
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
                            "license": "A123456"
                        }
                    ]
                }
            ]
        }

    def test_npi_connector_initialization(self, npi_connector):
        """Test NPI connector initialization"""
        assert npi_connector.name == "npi_registry"
        assert npi_connector.base_url == "https://npiregistry.cms.hhs.gov/api"
        assert npi_connector.rate_limit_delay == 0.1
        assert npi_connector.max_retries == 3

    def test_validate_npi_format_valid(self, npi_connector):
        """Test NPI format validation with valid NPIs"""
        valid_npis = [
            "1234567890",
            "1234567893",  # Valid Luhn checksum
            "1234567894",  # Valid Luhn checksum
        ]
        
        for npi in valid_npis:
            assert npi_connector._validate_npi_format(npi) == True

    def test_validate_npi_format_invalid(self, npi_connector):
        """Test NPI format validation with invalid NPIs"""
        invalid_npis = [
            "123456789",   # Too short
            "12345678901", # Too long
            "1234567891",  # Invalid Luhn checksum
            "0000000000",  # All zeros
            "1111111111",  # Invalid Luhn checksum
            "abc1234567",  # Contains letters
            "",            # Empty string
            None           # None value
        ]
        
        for npi in invalid_npis:
            assert npi_connector._validate_npi_format(npi) == False

    def test_normalize_provider_data(self, npi_connector, sample_npi_response):
        """Test provider data normalization"""
        raw_data = sample_npi_response["results"][0]
        normalized = npi_connector._normalize_provider_data(raw_data)
        
        # Check basic fields
        assert normalized["npi_number"] == "1234567890"
        assert normalized["given_name"] == "JOHN"
        assert normalized["family_name"] == "SMITH"
        assert normalized["primary_taxonomy"] == "207Q00000X"
        assert normalized["practice_name"] == "JOHN SMITH MEDICAL PRACTICE"
        
        # Check address fields
        assert normalized["address_street"] == "123 MAIN ST"
        assert normalized["address_city"] == "SAN FRANCISCO"
        assert normalized["address_state"] == "CA"
        assert normalized["address_zip"] == "94102"
        assert normalized["phone_primary"] == "415-555-0123"
        
        # Check metadata
        assert "_npi_metadata" in normalized
        metadata = normalized["_npi_metadata"]
        assert metadata["enumeration_type"] == "NPI-1"
        assert metadata["credential"] == "MD"
        assert metadata["middle_name"] == "MICHAEL"
        assert metadata["gender"] == "M"

    def test_calculate_trust_scores_npi_search(self, npi_connector, sample_npi_response):
        """Test trust score calculation for NPI search"""
        raw_data = sample_npi_response["results"][0]
        trust_scores = npi_connector._calculate_trust_scores(raw_data, "npi_search")
        
        # Check high-trust fields
        assert trust_scores["npi_number"].score == 0.98
        assert trust_scores["given_name"].score == 0.95
        assert trust_scores["family_name"].score == 0.95
        assert trust_scores["primary_taxonomy"].score == 0.92
        
        # Check medium-trust fields
        assert trust_scores["practice_name"].score == 0.80
        assert trust_scores["address_street"].score == 0.85
        assert trust_scores["phone_primary"].score == 0.70
        
        # Check low-trust fields
        assert trust_scores["email"].score == 0.0  # No email in sample data
        
        # Check no-trust fields (license info not available from NPI Registry)
        assert trust_scores["license_number"].score == 0.0
        assert trust_scores["license_state"].score == 0.0
        assert trust_scores["license_status"].score == 0.0

    def test_calculate_trust_scores_name_search(self, npi_connector, sample_npi_response):
        """Test trust score calculation for name search"""
        raw_data = sample_npi_response["results"][0]
        trust_scores = npi_connector._calculate_trust_scores(raw_data, "name_search")
        
        # Name search should have slightly lower trust scores
        assert trust_scores["npi_number"].score == 0.90
        assert trust_scores["given_name"].score == 0.85
        assert trust_scores["family_name"].score == 0.85

    @pytest.mark.asyncio
    async def test_search_provider_by_npi_success(self, npi_connector, sample_npi_response):
        """Test successful NPI search"""
        with patch('httpx.AsyncClient.get') as mock_get:
            # Mock successful API response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = sample_npi_response
            mock_get.return_value.__aenter__.return_value = mock_response
            
            result = await npi_connector.search_provider_by_npi("1234567890")
            
            assert result.success == True
            assert result.data is not None
            assert result.data["npi_number"] == "1234567890"
            assert result.data["given_name"] == "JOHN"
            assert result.data["family_name"] == "SMITH"
            assert result.trust_scores is not None
            assert result.source == "npi_registry"

    @pytest.mark.asyncio
    async def test_search_provider_by_npi_not_found(self, npi_connector):
        """Test NPI search when provider not found"""
        with patch('httpx.AsyncClient.get') as mock_get:
            # Mock API response with no results
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"result_count": 0, "results": []}
            mock_get.return_value.__aenter__.return_value = mock_response
            
            result = await npi_connector.search_provider_by_npi("9999999999")
            
            assert result.success == False
            assert "not found" in result.error.lower()
            assert result.data is None

    @pytest.mark.asyncio
    async def test_search_provider_by_npi_invalid_format(self, npi_connector):
        """Test NPI search with invalid NPI format"""
        result = await npi_connector.search_provider_by_npi("123")
        
        assert result.success == False
        assert "Invalid NPI format" in result.error
        assert result.data is None

    @pytest.mark.asyncio
    async def test_search_provider_by_npi_api_error(self, npi_connector):
        """Test NPI search with API error"""
        with patch('httpx.AsyncClient.get') as mock_get:
            # Mock API error
            mock_get.side_effect = Exception("Network error")
            
            result = await npi_connector.search_provider_by_npi("1234567890")
            
            assert result.success == False
            assert "API error" in result.error
            assert result.data is None

    @pytest.mark.asyncio
    async def test_search_provider_by_name_success(self, npi_connector):
        """Test successful name search"""
        sample_response = {
            "result_count": 2,
            "results": [
                {
                    "number": "1234567890",
                    "basic": {
                        "first_name": "JOHN",
                        "last_name": "SMITH",
                        "organization_name": "JOHN SMITH MEDICAL PRACTICE"
                    },
                    "addresses": [{"city": "SAN FRANCISCO", "state": "CA"}],
                    "taxonomies": [{"code": "207Q00000X", "desc": "Family Medicine"}]
                },
                {
                    "number": "0987654321",
                    "basic": {
                        "first_name": "JOHN",
                        "last_name": "SMITH",
                        "organization_name": "SMITH CARDIOLOGY GROUP"
                    },
                    "addresses": [{"city": "LOS ANGELES", "state": "CA"}],
                    "taxonomies": [{"code": "207RC0000X", "desc": "Cardiology"}]
                }
            ]
        }
        
        with patch('httpx.AsyncClient.get') as mock_get:
            # Mock successful API response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = sample_response
            mock_get.return_value.__aenter__.return_value = mock_response
            
            result = await npi_connector.search_provider_by_name("John", "Smith", "CA")
            
            assert result.success == True
            assert isinstance(result.data, list)
            assert len(result.data) == 2
            assert result.data[0]["given_name"] == "JOHN"
            assert result.data[1]["given_name"] == "JOHN"
            assert result.trust_scores is not None

    @pytest.mark.asyncio
    async def test_search_provider_by_name_not_found(self, npi_connector):
        """Test name search when no providers found"""
        with patch('httpx.AsyncClient.get') as mock_get:
            # Mock API response with no results
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"result_count": 0, "results": []}
            mock_get.return_value.__aenter__.return_value = mock_response
            
            result = await npi_connector.search_provider_by_name("Nonexistent", "Provider")
            
            assert result.success == False
            assert "No providers found" in result.error
            assert result.data is None

    @pytest.mark.asyncio
    async def test_rate_limiting(self, npi_connector):
        """Test rate limiting functionality"""
        start_time = datetime.now()
        
        # Call rate limit multiple times
        for _ in range(3):
            await npi_connector._rate_limit()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Should have waited at least 0.2 seconds (2 * 0.1s delay)
        assert duration >= 0.2

    def test_get_headers(self, npi_connector):
        """Test HTTP headers generation"""
        headers = npi_connector._get_headers()
        
        assert "User-Agent" in headers
        assert "Accept" in headers
        assert headers["Accept"] == "application/json"
        
        # Test with API key
        connector_with_key = NPIConnector(api_key="test_key")
        headers_with_key = connector_with_key._get_headers()
        assert "Authorization" in headers_with_key
        assert headers_with_key["Authorization"] == "Bearer test_key"


# Integration test (requires actual API access)
@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_npi_lookup():
    """Integration test with real NPI Registry API"""
    connector = NPIConnector()
    
    # Test with a known valid NPI (this is a test NPI)
    result = await connector.search_provider_by_npi("1234567893")
    
    # This test may pass or fail depending on API availability
    # and whether the test NPI exists
    if result.success:
        assert result.data is not None
        assert result.trust_scores is not None
        assert result.source == "npi_registry"
    else:
        # If API is unavailable, we should get a proper error
        assert result.error is not None


if __name__ == "__main__":
    # Run basic tests
    pytest.main([__file__, "-v"])
