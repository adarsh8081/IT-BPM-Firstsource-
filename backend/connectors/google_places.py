"""
Google Places API Connector

This module provides functionality to validate addresses using Google Places API
and Google Geocoding API, returning normalized address components, place_id,
coordinates, and match confidence scores.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import httpx
from dataclasses import dataclass
import json
import time

from .base import BaseConnector, ConnectorResponse, TrustScore

logger = logging.getLogger(__name__)


@dataclass
class AddressComponents:
    """Address components for validation"""
    street_number: Optional[str] = None
    route: Optional[str] = None
    locality: Optional[str] = None
    administrative_area_level_1: Optional[str] = None
    administrative_area_level_2: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    formatted_address: Optional[str] = None


@dataclass
class GeocodeResult:
    """Result from geocoding operation"""
    place_id: Optional[str] = None
    formatted_address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address_components: Optional[AddressComponents] = None
    match_confidence: float = 0.0
    geometry_accuracy: Optional[str] = None


class GooglePlacesConnector(BaseConnector):
    """
    Google Places API Connector
    
    Validates addresses using Google Places API and Google Geocoding API.
    Provides normalized address components, place_id, coordinates, and confidence scores.
    """
    
    def __init__(self, api_key: str):
        """
        Initialize Google Places Connector
        
        Args:
            api_key: Google API key with Places API and Geocoding API enabled
        """
        super().__init__(
            name="google_places",
            base_url="https://maps.googleapis.com/maps/api",
            api_key=api_key,
            rate_limit_delay=0.1,  # 10 requests per second
            max_retries=3
        )
        
        # Google API specific rate limits
        self.places_rate_limit = 100  # requests per 100 seconds
        self.geocoding_rate_limit = 50  # requests per second
        self.last_requests = {}  # Track request timestamps
        
        # Exponential backoff configuration
        self.base_delay = 1.0  # Base delay in seconds
        self.max_delay = 60.0  # Maximum delay in seconds
        self.backoff_multiplier = 2.0
    
    async def validate_address(self, address: str, country_code: Optional[str] = None) -> ConnectorResponse:
        """
        Validate address using Google Geocoding API
        
        Args:
            address: Address string to validate
            country_code: Optional country code (e.g., 'US', 'CA')
            
        Returns:
            ConnectorResponse with normalized address data and confidence scores
        """
        try:
            await self._rate_limit()
            
            # Geocode the address
            geocode_result = await self._geocode_address(address, country_code)
            
            if geocode_result and geocode_result.match_confidence > 0.5:
                # Normalize the result
                normalized_data = self._normalize_address_data(geocode_result)
                trust_scores = self._calculate_trust_scores(geocode_result, "geocoding")
                
                return ConnectorResponse(
                    success=True,
                    data=normalized_data,
                    trust_scores=trust_scores,
                    source="google_geocoding",
                    timestamp=datetime.utcnow()
                )
            else:
                return ConnectorResponse(
                    success=False,
                    error=f"Address validation failed: Low confidence ({geocode_result.match_confidence:.2f})",
                    data=None,
                    trust_scores=None
                )
                
        except Exception as e:
            logger.error(f"Error validating address '{address}': {str(e)}")
            return ConnectorResponse(
                success=False,
                error=f"Address validation error: {str(e)}",
                data=None,
                trust_scores=None
            )
    
    async def validate_address_components(self, address_components: Dict[str, str]) -> ConnectorResponse:
        """
        Validate address using individual components
        
        Args:
            address_components: Dict with keys like 'street', 'city', 'state', 'zip', 'country'
            
        Returns:
            ConnectorResponse with validated and normalized address data
        """
        try:
            await self._rate_limit()
            
            # Build address string from components
            address_parts = []
            if address_components.get('street'):
                address_parts.append(address_components['street'])
            if address_components.get('city'):
                address_parts.append(address_components['city'])
            if address_components.get('state'):
                address_parts.append(address_components['state'])
            if address_components.get('zip'):
                address_parts.append(address_components['zip'])
            
            address_string = ', '.join(address_parts)
            country_code = address_components.get('country', 'US')
            
            # Use geocoding to validate
            return await self.validate_address(address_string, country_code)
            
        except Exception as e:
            logger.error(f"Error validating address components: {str(e)}")
            return ConnectorResponse(
                success=False,
                error=f"Component validation error: {str(e)}",
                data=None,
                trust_scores=None
            )
    
    async def get_place_details(self, place_id: str) -> ConnectorResponse:
        """
        Get detailed information for a place using place_id
        
        Args:
            place_id: Google Places place_id
            
        Returns:
            ConnectorResponse with detailed place information
        """
        try:
            await self._rate_limit()
            
            place_details = await self._get_place_details(place_id)
            
            if place_details:
                normalized_data = self._normalize_place_data(place_details)
                trust_scores = self._calculate_trust_scores(place_details, "place_details")
                
                return ConnectorResponse(
                    success=True,
                    data=normalized_data,
                    trust_scores=trust_scores,
                    source="google_places",
                    timestamp=datetime.utcnow()
                )
            else:
                return ConnectorResponse(
                    success=False,
                    error="Place details not found",
                    data=None,
                    trust_scores=None
                )
                
        except Exception as e:
            logger.error(f"Error getting place details for {place_id}: {str(e)}")
            return ConnectorResponse(
                success=False,
                error=f"Place details error: {str(e)}",
                data=None,
                trust_scores=None
            )
    
    async def _geocode_address(self, address: str, country_code: Optional[str] = None) -> Optional[GeocodeResult]:
        """
        Geocode address using Google Geocoding API with exponential backoff
        
        Args:
            address: Address to geocode
            country_code: Optional country code restriction
            
        Returns:
            GeocodeResult or None if failed
        """
        for attempt in range(self.max_retries + 1):
            try:
                # Build request parameters
                params = {
                    'address': address,
                    'key': self.api_key,
                    'region': country_code.lower() if country_code else None
                }
                
                # Remove None values
                params = {k: v for k, v in params.items() if v is not None}
                
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(
                        f"{self.base_url}/geocode/json",
                        params=params,
                        headers=self._get_headers()
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        if data.get('status') == 'OK' and data.get('results'):
                            result = data['results'][0]  # Use first (best) result
                            return self._parse_geocode_result(result)
                        elif data.get('status') == 'ZERO_RESULTS':
                            return None
                        elif data.get('status') == 'OVER_QUERY_LIMIT':
                            # Rate limit exceeded - implement exponential backoff
                            delay = self._calculate_backoff_delay(attempt)
                            logger.warning(f"Rate limit exceeded, waiting {delay}s before retry {attempt + 1}")
                            await asyncio.sleep(delay)
                            continue
                        else:
                            logger.error(f"Geocoding API error: {data.get('status')}")
                            return None
                    else:
                        logger.error(f"HTTP error {response.status_code}: {response.text}")
                        if response.status_code >= 500:  # Server error - retry
                            delay = self._calculate_backoff_delay(attempt)
                            await asyncio.sleep(delay)
                            continue
                        return None
                        
            except httpx.TimeoutException:
                logger.warning(f"Timeout on attempt {attempt + 1}")
                if attempt < self.max_retries:
                    delay = self._calculate_backoff_delay(attempt)
                    await asyncio.sleep(delay)
                    continue
                return None
            except Exception as e:
                logger.error(f"Geocoding error on attempt {attempt + 1}: {str(e)}")
                if attempt < self.max_retries:
                    delay = self._calculate_backoff_delay(attempt)
                    await asyncio.sleep(delay)
                    continue
                return None
        
        return None
    
    async def _get_place_details(self, place_id: str) -> Optional[Dict[str, Any]]:
        """
        Get place details using Google Places API
        
        Args:
            place_id: Google Places place_id
            
        Returns:
            Place details dict or None if failed
        """
        for attempt in range(self.max_retries + 1):
            try:
                params = {
                    'place_id': place_id,
                    'key': self.api_key,
                    'fields': 'place_id,name,formatted_address,geometry,address_components,types'
                }
                
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(
                        f"{self.base_url}/place/details/json",
                        params=params,
                        headers=self._get_headers()
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        if data.get('status') == 'OK' and data.get('result'):
                            return data['result']
                        elif data.get('status') == 'OVER_QUERY_LIMIT':
                            delay = self._calculate_backoff_delay(attempt)
                            logger.warning(f"Rate limit exceeded, waiting {delay}s before retry {attempt + 1}")
                            await asyncio.sleep(delay)
                            continue
                        else:
                            logger.error(f"Places API error: {data.get('status')}")
                            return None
                    else:
                        logger.error(f"HTTP error {response.status_code}: {response.text}")
                        if response.status_code >= 500:
                            delay = self._calculate_backoff_delay(attempt)
                            await asyncio.sleep(delay)
                            continue
                        return None
                        
            except httpx.TimeoutException:
                logger.warning(f"Timeout on attempt {attempt + 1}")
                if attempt < self.max_retries:
                    delay = self._calculate_backoff_delay(attempt)
                    await asyncio.sleep(delay)
                    continue
                return None
            except Exception as e:
                logger.error(f"Places API error on attempt {attempt + 1}: {str(e)}")
                if attempt < self.max_retries:
                    delay = self._calculate_backoff_delay(attempt)
                    await asyncio.sleep(delay)
                    continue
                return None
        
        return None
    
    def _parse_geocode_result(self, result: Dict[str, Any]) -> GeocodeResult:
        """
        Parse geocoding API result into GeocodeResult
        
        Args:
            result: Raw geocoding API result
            
        Returns:
            Parsed GeocodeResult
        """
        geometry = result.get('geometry', {})
        location = geometry.get('location', {})
        address_components = result.get('address_components', [])
        
        # Parse address components
        parsed_components = self._parse_address_components(address_components)
        
        # Calculate match confidence based on geometry accuracy
        geometry_accuracy = geometry.get('location_type', '')
        match_confidence = self._calculate_geometry_confidence(geometry_accuracy)
        
        return GeocodeResult(
            place_id=result.get('place_id'),
            formatted_address=result.get('formatted_address'),
            latitude=location.get('lat'),
            longitude=location.get('lng'),
            address_components=parsed_components,
            match_confidence=match_confidence,
            geometry_accuracy=geometry_accuracy
        )
    
    def _parse_address_components(self, components: List[Dict[str, Any]]) -> AddressComponents:
        """
        Parse Google address components into our format
        
        Args:
            components: List of address components from Google API
            
        Returns:
            Parsed AddressComponents
        """
        parsed = AddressComponents()
        
        for component in components:
            types = component.get('types', [])
            long_name = component.get('long_name', '')
            short_name = component.get('short_name', '')
            
            if 'street_number' in types:
                parsed.street_number = long_name
            elif 'route' in types:
                parsed.route = long_name
            elif 'locality' in types:
                parsed.locality = long_name
            elif 'administrative_area_level_1' in types:
                parsed.administrative_area_level_1 = short_name
            elif 'administrative_area_level_2' in types:
                parsed.administrative_area_level_2 = long_name
            elif 'country' in types:
                parsed.country = short_name
            elif 'postal_code' in types:
                parsed.postal_code = long_name
        
        return parsed
    
    def _calculate_geometry_confidence(self, geometry_accuracy: str) -> float:
        """
        Calculate confidence score based on geometry accuracy
        
        Args:
            geometry_accuracy: Google's geometry accuracy indicator
            
        Returns:
            Confidence score between 0 and 1
        """
        confidence_map = {
            'ROOFTOP': 0.95,      # Precise location
            'RANGE_INTERPOLATED': 0.85,  # Interpolated between ranges
            'GEOMETRIC_CENTER': 0.75,    # Center of geometry
            'APPROXIMATE': 0.60,         # Approximate location
        }
        
        return confidence_map.get(geometry_accuracy, 0.50)
    
    def _normalize_address_data(self, geocode_result: GeocodeResult) -> Dict[str, Any]:
        """
        Normalize geocode result to our address schema
        
        Args:
            geocode_result: Parsed geocoding result
            
        Returns:
            Normalized address data
        """
        components = geocode_result.address_components
        
        # Build full street address
        street_parts = []
        if components and components.street_number:
            street_parts.append(components.street_number)
        if components and components.route:
            street_parts.append(components.route)
        full_street = ' '.join(street_parts) if street_parts else None
        
        return {
            'place_id': geocode_result.place_id,
            'formatted_address': geocode_result.formatted_address,
            'latitude': geocode_result.latitude,
            'longitude': geocode_result.longitude,
            'street_number': components.street_number if components else None,
            'route': components.route if components else None,
            'address_street': full_street,
            'address_city': components.locality if components else None,
            'address_state': components.administrative_area_level_1 if components else None,
            'address_zip': components.postal_code if components else None,
            'country': components.country if components else None,
            'geometry_accuracy': geocode_result.geometry_accuracy,
            'match_confidence': geocode_result.match_confidence
        }
    
    def _normalize_place_data(self, place_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize place details to our schema
        
        Args:
            place_data: Raw place details from Google Places API
            
        Returns:
            Normalized place data
        """
        geometry = place_data.get('geometry', {})
        location = geometry.get('location', {})
        address_components = place_data.get('address_components', [])
        
        # Parse components
        components = self._parse_address_components(address_components)
        
        # Build street address
        street_parts = []
        if components.street_number:
            street_parts.append(components.street_number)
        if components.route:
            street_parts.append(components.route)
        full_street = ' '.join(street_parts) if street_parts else None
        
        return {
            'place_id': place_data.get('place_id'),
            'name': place_data.get('name'),
            'formatted_address': place_data.get('formatted_address'),
            'latitude': location.get('lat'),
            'longitude': location.get('lng'),
            'address_street': full_street,
            'address_city': components.locality,
            'address_state': components.administrative_area_level_1,
            'address_zip': components.postal_code,
            'country': components.country,
            'types': place_data.get('types', []),
            'geometry_accuracy': geometry.get('location_type', ''),
            'match_confidence': self._calculate_geometry_confidence(geometry.get('location_type', ''))
        }
    
    def _calculate_trust_scores(self, result: Any, source_type: str) -> Dict[str, TrustScore]:
        """
        Calculate trust scores for address validation results
        
        Args:
            result: GeocodeResult or place details dict
            source_type: Type of validation ("geocoding" or "place_details")
            
        Returns:
            Dictionary of field trust scores
        """
        trust_scores = {}
        
        # Base confidence for Google APIs (high reliability)
        base_trust = 0.90
        
        # Place ID - highest trust
        trust_scores["place_id"] = TrustScore(
            score=0.95,
            reason="Google Places unique identifier",
            source="google_places",
            confidence="high"
        )
        
        # Coordinates - high trust
        trust_scores["latitude"] = TrustScore(
            score=base_trust,
            reason="Google Maps coordinate data",
            source="google_places",
            confidence="high"
        )
        
        trust_scores["longitude"] = TrustScore(
            score=base_trust,
            reason="Google Maps coordinate data",
            source="google_places",
            confidence="high"
        )
        
        # Address components - high trust
        trust_scores["formatted_address"] = TrustScore(
            score=base_trust,
            reason="Google formatted address",
            source="google_places",
            confidence="high"
        )
        
        trust_scores["address_street"] = TrustScore(
            score=0.85,
            reason="Google street address data",
            source="google_places",
            confidence="high"
        )
        
        trust_scores["address_city"] = TrustScore(
            score=0.88,
            reason="Google locality data",
            source="google_places",
            confidence="high"
        )
        
        trust_scores["address_state"] = TrustScore(
            score=0.88,
            reason="Google administrative area data",
            source="google_places",
            confidence="high"
        )
        
        trust_scores["address_zip"] = TrustScore(
            score=0.85,
            reason="Google postal code data",
            source="google_places",
            confidence="high"
        )
        
        # Match confidence - reflects validation quality
        if hasattr(result, 'match_confidence'):
            confidence_score = result.match_confidence
        elif isinstance(result, dict) and 'geometry' in result:
            confidence_score = self._calculate_geometry_confidence(
                result['geometry'].get('location_type', '')
            )
        else:
            confidence_score = 0.8
        
        trust_scores["match_confidence"] = TrustScore(
            score=confidence_score,
            reason="Google geometry accuracy assessment",
            source="google_places",
            confidence="high" if confidence_score > 0.8 else "medium"
        )
        
        return trust_scores
    
    def _calculate_backoff_delay(self, attempt: int) -> float:
        """
        Calculate exponential backoff delay
        
        Args:
            attempt: Current attempt number (0-based)
            
        Returns:
            Delay in seconds
        """
        delay = self.base_delay * (self.backoff_multiplier ** attempt)
        return min(delay, self.max_delay)
    
    async def _rate_limit(self):
        """
        Implement rate limiting for Google APIs
        """
        current_time = time.time()
        
        # Check if we need to wait
        if 'geocoding' in self.last_requests:
            time_since_last = current_time - self.last_requests['geocoding']
            if time_since_last < (1.0 / self.geocoding_rate_limit):
                sleep_time = (1.0 / self.geocoding_rate_limit) - time_since_last
                await asyncio.sleep(sleep_time)
        
        # Update last request time
        self.last_requests['geocoding'] = time.time()
        
        # Also apply base rate limiting
        await super()._rate_limit()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for API requests"""
        return {
            "User-Agent": "Provider-Validation-System/1.0",
            "Accept": "application/json",
        }


# Example usage and testing functions
async def example_address_validation():
    """
    Example function demonstrating address validation
    """
    # Note: This requires a valid Google API key
    api_key = "YOUR_GOOGLE_API_KEY"  # Replace with actual API key
    connector = GooglePlacesConnector(api_key)
    
    print("=== Address Validation Example ===")
    
    # Example 1: Validate full address
    address = "1600 Amphitheatre Parkway, Mountain View, CA 94043"
    
    result = await connector.validate_address(address, "US")
    
    if result.success:
        print(f"✅ Address validated successfully!")
        print(f"   Place ID: {result.data['place_id']}")
        print(f"   Formatted: {result.data['formatted_address']}")
        print(f"   Coordinates: {result.data['latitude']}, {result.data['longitude']}")
        print(f"   Confidence: {result.data['match_confidence']:.2f}")
        
        print("\n📊 Trust Scores:")
        for field, trust in result.trust_scores.items():
            print(f"   {field}: {trust.score:.2f} - {trust.confidence}")
    else:
        print(f"❌ Error: {result.error}")


async def example_address_components():
    """
    Example function demonstrating component-based validation
    """
    api_key = "YOUR_GOOGLE_API_KEY"  # Replace with actual API key
    connector = GooglePlacesConnector(api_key)
    
    print("\n=== Address Components Example ===")
    
    # Example 2: Validate using components
    components = {
        'street': '123 Main Street',
        'city': 'San Francisco',
        'state': 'CA',
        'zip': '94102',
        'country': 'US'
    }
    
    result = await connector.validate_address_components(components)
    
    if result.success:
        print(f"✅ Components validated successfully!")
        print(f"   Street: {result.data['address_street']}")
        print(f"   City: {result.data['address_city']}")
        print(f"   State: {result.data['address_state']}")
        print(f"   ZIP: {result.data['address_zip']}")
        print(f"   Place ID: {result.data['place_id']}")
    else:
        print(f"❌ Error: {result.error}")


if __name__ == "__main__":
    # Run examples (requires valid API key)
    # asyncio.run(example_address_validation())
    # asyncio.run(example_address_components())
    print("Google Places Connector - Examples require valid API key")
