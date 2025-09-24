"""
Tests for Google Places Connector
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from connectors.google_places import GooglePlacesConnector, GeocodeResult, AddressComponents


class TestGooglePlacesConnector:
    """Test cases for Google Places Connector"""

    @pytest.fixture
    def google_connector(self):
        """Create Google Places connector instance for testing"""
        return GooglePlacesConnector(api_key="test_api_key")

    @pytest.fixture
    def sample_geocode_response(self):
        """Sample Google Geocoding API response"""
        return {
            "results": [
                {
                    "place_id": "ChIJ1234567890abcdef",
                    "formatted_address": "1600 Amphitheatre Parkway, Mountain View, CA 94043, USA",
                    "geometry": {
                        "location": {
                            "lat": 37.4220656,
                            "lng": -122.0840897
                        },
                        "location_type": "ROOFTOP"
                    },
                    "address_components": [
                        {
                            "long_name": "1600",
                            "short_name": "1600",
                            "types": ["street_number"]
                        },
                        {
                            "long_name": "Amphitheatre Parkway",
                            "short_name": "Amphitheatre Pkwy",
                            "types": ["route"]
                        },
                        {
                            "long_name": "Mountain View",
                            "short_name": "Mountain View",
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
                            "long_name": "94043",
                            "short_name": "94043",
                            "types": ["postal_code"]
                        }
                    ]
                }
            ],
            "status": "OK"
        }

    @pytest.fixture
    def sample_place_details_response(self):
        """Sample Google Places API response"""
        return {
            "result": {
                "place_id": "ChIJ1234567890abcdef",
                "name": "Googleplex",
                "formatted_address": "1600 Amphitheatre Parkway, Mountain View, CA 94043, USA",
                "geometry": {
                    "location": {
                        "lat": 37.4220656,
                        "lng": -122.0840897
                    },
                    "location_type": "ROOFTOP"
                },
                "address_components": [
                    {
                        "long_name": "1600",
                        "short_name": "1600",
                        "types": ["street_number"]
                    },
                    {
                        "long_name": "Amphitheatre Parkway",
                        "short_name": "Amphitheatre Pkwy",
                        "types": ["route"]
                    }
                ],
                "types": ["establishment", "point_of_interest"]
            },
            "status": "OK"
        }

    def test_google_connector_initialization(self, google_connector):
        """Test Google Places connector initialization"""
        assert google_connector.name == "google_places"
        assert google_connector.base_url == "https://maps.googleapis.com/maps/api"
        assert google_connector.api_key == "test_api_key"
        assert google_connector.places_rate_limit == 100
        assert google_connector.geocoding_rate_limit == 50

    def test_calculate_geometry_confidence(self, google_connector):
        """Test geometry confidence calculation"""
        assert google_connector._calculate_geometry_confidence("ROOFTOP") == 0.95
        assert google_connector._calculate_geometry_confidence("RANGE_INTERPOLATED") == 0.85
        assert google_connector._calculate_geometry_confidence("GEOMETRIC_CENTER") == 0.75
        assert google_connector._calculate_geometry_confidence("APPROXIMATE") == 0.60
        assert google_connector._calculate_geometry_confidence("UNKNOWN") == 0.50

    def test_parse_address_components(self, google_connector):
        """Test address components parsing"""
        components = [
            {
                "long_name": "1600",
                "short_name": "1600",
                "types": ["street_number"]
            },
            {
                "long_name": "Amphitheatre Parkway",
                "short_name": "Amphitheatre Pkwy",
                "types": ["route"]
            },
            {
                "long_name": "Mountain View",
                "short_name": "Mountain View",
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
                "long_name": "94043",
                "short_name": "94043",
                "types": ["postal_code"]
            }
        ]
        
        parsed = google_connector._parse_address_components(components)
        
        assert parsed.street_number == "1600"
        assert parsed.route == "Amphitheatre Parkway"
        assert parsed.locality == "Mountain View"
        assert parsed.administrative_area_level_1 == "CA"
        assert parsed.country == "US"
        assert parsed.postal_code == "94043"

    def test_parse_geocode_result(self, google_connector, sample_geocode_response):
        """Test geocode result parsing"""
        result_data = sample_geocode_response["results"][0]
        geocode_result = google_connector._parse_geocode_result(result_data)
        
        assert geocode_result.place_id == "ChIJ1234567890abcdef"
        assert geocode_result.formatted_address == "1600 Amphitheatre Parkway, Mountain View, CA 94043, USA"
        assert geocode_result.latitude == 37.4220656
        assert geocode_result.longitude == -122.0840897
        assert geocode_result.match_confidence == 0.95  # ROOFTOP accuracy
        assert geocode_result.geometry_accuracy == "ROOFTOP"
        assert geocode_result.address_components is not None

    def test_normalize_address_data(self, google_connector):
        """Test address data normalization"""
        # Create a mock geocode result
        components = AddressComponents(
            street_number="1600",
            route="Amphitheatre Parkway",
            locality="Mountain View",
            administrative_area_level_1="CA",
            country="US",
            postal_code="94043"
        )
        
        geocode_result = GeocodeResult(
            place_id="ChIJ1234567890abcdef",
            formatted_address="1600 Amphitheatre Parkway, Mountain View, CA 94043, USA",
            latitude=37.4220656,
            longitude=-122.0840897,
            address_components=components,
            match_confidence=0.95,
            geometry_accuracy="ROOFTOP"
        )
        
        normalized = google_connector._normalize_address_data(geocode_result)
        
        assert normalized["place_id"] == "ChIJ1234567890abcdef"
        assert normalized["formatted_address"] == "1600 Amphitheatre Parkway, Mountain View, CA 94043, USA"
        assert normalized["latitude"] == 37.4220656
        assert normalized["longitude"] == -122.0840897
        assert normalized["address_street"] == "1600 Amphitheatre Parkway"
        assert normalized["address_city"] == "Mountain View"
        assert normalized["address_state"] == "CA"
        assert normalized["address_zip"] == "94043"
        assert normalized["country"] == "US"
        assert normalized["match_confidence"] == 0.95

    def test_calculate_trust_scores(self, google_connector):
        """Test trust score calculation"""
        components = AddressComponents(
            street_number="1600",
            route="Amphitheatre Parkway",
            locality="Mountain View",
            administrative_area_level_1="CA"
        )
        
        geocode_result = GeocodeResult(
            place_id="ChIJ1234567890abcdef",
            formatted_address="1600 Amphitheatre Parkway, Mountain View, CA 94043, USA",
            latitude=37.4220656,
            longitude=-122.0840897,
            address_components=components,
            match_confidence=0.95,
            geometry_accuracy="ROOFTOP"
        )
        
        trust_scores = google_connector._calculate_trust_scores(geocode_result, "geocoding")
        
        # Check high-trust fields
        assert trust_scores["place_id"].score == 0.95
        assert trust_scores["latitude"].score == 0.90
        assert trust_scores["longitude"].score == 0.90
        assert trust_scores["formatted_address"].score == 0.90
        
        # Check address components
        assert trust_scores["address_street"].score == 0.85
        assert trust_scores["address_city"].score == 0.88
        assert trust_scores["address_state"].score == 0.88
        assert trust_scores["address_zip"].score == 0.85
        
        # Check match confidence
        assert trust_scores["match_confidence"].score == 0.95

    def test_calculate_backoff_delay(self, google_connector):
        """Test exponential backoff delay calculation"""
        assert google_connector._calculate_backoff_delay(0) == 1.0  # base_delay
        assert google_connector._calculate_backoff_delay(1) == 2.0  # base_delay * 2
        assert google_connector._calculate_backoff_delay(2) == 4.0  # base_delay * 4
        assert google_connector._calculate_backoff_delay(10) == 60.0  # max_delay

    @pytest.mark.asyncio
    async def test_validate_address_success(self, google_connector, sample_geocode_response):
        """Test successful address validation"""
        with patch('httpx.AsyncClient.get') as mock_get:
            # Mock successful API response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = sample_geocode_response
            mock_get.return_value.__aenter__.return_value = mock_response
            
            result = await google_connector.validate_address("1600 Amphitheatre Parkway, Mountain View, CA")
            
            assert result.success == True
            assert result.data is not None
            assert result.data["place_id"] == "ChIJ1234567890abcdef"
            assert result.data["latitude"] == 37.4220656
            assert result.data["longitude"] == -122.0840897
            assert result.trust_scores is not None
            assert result.source == "google_geocoding"

    @pytest.mark.asyncio
    async def test_validate_address_zero_results(self, google_connector):
        """Test address validation with zero results"""
        with patch('httpx.AsyncClient.get') as mock_get:
            # Mock API response with zero results
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"results": [], "status": "ZERO_RESULTS"}
            mock_get.return_value.__aenter__.return_value = mock_response
            
            result = await google_connector.validate_address("Nonexistent Address")
            
            assert result.success == False
            assert "Low confidence" in result.error
            assert result.data is None

    @pytest.mark.asyncio
    async def test_validate_address_over_query_limit(self, google_connector):
        """Test address validation with rate limit exceeded"""
        with patch('httpx.AsyncClient.get') as mock_get:
            # Mock API response with rate limit error
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "OVER_QUERY_LIMIT"}
            mock_get.return_value.__aenter__.return_value = mock_response
            
            # Mock sleep to avoid actual delays in tests
            with patch('asyncio.sleep') as mock_sleep:
                result = await google_connector.validate_address("1600 Amphitheatre Parkway")
                
                # Should have attempted retries
                assert mock_sleep.called
                assert result.success == False

    @pytest.mark.asyncio
    async def test_validate_address_components(self, google_connector, sample_geocode_response):
        """Test address component validation"""
        with patch('httpx.AsyncClient.get') as mock_get:
            # Mock successful API response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = sample_geocode_response
            mock_get.return_value.__aenter__.return_value = mock_response
            
            components = {
                'street': '1600 Amphitheatre Parkway',
                'city': 'Mountain View',
                'state': 'CA',
                'zip': '94043',
                'country': 'US'
            }
            
            result = await google_connector.validate_address_components(components)
            
            assert result.success == True
            assert result.data is not None
            assert result.data["place_id"] == "ChIJ1234567890abcdef"

    @pytest.mark.asyncio
    async def test_get_place_details_success(self, google_connector, sample_place_details_response):
        """Test successful place details retrieval"""
        with patch('httpx.AsyncClient.get') as mock_get:
            # Mock successful API response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = sample_place_details_response
            mock_get.return_value.__aenter__.return_value = mock_response
            
            result = await google_connector.get_place_details("ChIJ1234567890abcdef")
            
            assert result.success == True
            assert result.data is not None
            assert result.data["place_id"] == "ChIJ1234567890abcdef"
            assert result.data["name"] == "Googleplex"
            assert result.source == "google_places"

    @pytest.mark.asyncio
    async def test_get_place_details_not_found(self, google_connector):
        """Test place details retrieval when place not found"""
        with patch('httpx.AsyncClient.get') as mock_get:
            # Mock API response with no results
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "NOT_FOUND"}
            mock_get.return_value.__aenter__.return_value = mock_response
            
            result = await google_connector.get_place_details("invalid_place_id")
            
            assert result.success == False
            assert "Place details not found" in result.error

    @pytest.mark.asyncio
    async def test_validate_address_network_error(self, google_connector):
        """Test address validation with network error"""
        with patch('httpx.AsyncClient.get') as mock_get:
            # Mock network error
            mock_get.side_effect = Exception("Network error")
            
            result = await google_connector.validate_address("1600 Amphitheatre Parkway")
            
            assert result.success == False
            assert "Address validation error" in result.error

    @pytest.mark.asyncio
    async def test_validate_address_timeout(self, google_connector):
        """Test address validation with timeout"""
        with patch('httpx.AsyncClient.get') as mock_get:
            # Mock timeout
            mock_get.side_effect = httpx.TimeoutException("Request timeout")
            
            # Mock sleep to avoid actual delays
            with patch('asyncio.sleep') as mock_sleep:
                result = await google_connector.validate_address("1600 Amphitheatre Parkway")
                
                # Should have attempted retries
                assert mock_sleep.called
                assert result.success == False

    @pytest.mark.asyncio
    async def test_rate_limiting(self, google_connector):
        """Test rate limiting functionality"""
        start_time = datetime.now()
        
        # Mock the HTTP client to avoid actual API calls
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "OK", "results": []}
            mock_get.return_value.__aenter__.return_value = mock_response
            
            # Call rate limit multiple times
            for _ in range(3):
                await google_connector._rate_limit()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Should have waited at least some time due to rate limiting
        assert duration >= 0.1

    def test_get_headers(self, google_connector):
        """Test HTTP headers generation"""
        headers = google_connector._get_headers()
        
        assert "User-Agent" in headers
        assert "Accept" in headers
        assert headers["Accept"] == "application/json"
        assert headers["User-Agent"] == "Provider-Validation-System/1.0"


# Integration test (requires actual API access)
@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_google_places_lookup():
    """Integration test with real Google Places API"""
    # This test requires a valid Google API key
    api_key = "YOUR_GOOGLE_API_KEY"  # Replace with actual API key
    
    if api_key == "YOUR_GOOGLE_API_KEY":
        pytest.skip("Integration test requires valid Google API key")
    
    connector = GooglePlacesConnector(api_key)
    
    # Test with a known address
    result = await connector.validate_address("1600 Amphitheatre Parkway, Mountain View, CA")
    
    if result.success:
        assert result.data is not None
        assert result.trust_scores is not None
        assert result.source == "google_geocoding"
        assert result.data["latitude"] is not None
        assert result.data["longitude"] is not None
    else:
        # If API is unavailable or rate limited, we should get a proper error
        assert result.error is not None


if __name__ == "__main__":
    # Run basic tests
    pytest.main([__file__, "-v"])
