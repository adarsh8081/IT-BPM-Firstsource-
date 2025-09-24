"""
Google Places API connector for address validation
"""

import logging
from typing import Dict, Any, Optional, List
import asyncio

from .base import BaseConnector
from ..config import settings

logger = logging.getLogger(__name__)

class GooglePlacesConnector(BaseConnector):
    """Connector for Google Places API"""
    
    def __init__(self):
        super().__init__(rate_limit=settings.GOOGLE_API_RATE_LIMIT)
        self.api_key = settings.GOOGLE_PLACES_API_KEY
        self.maps_api_key = settings.GOOGLE_MAPS_API_KEY
        
    async def validate_address(
        self, 
        address_line1: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        zip_code: Optional[str] = None,
        country: str = "US"
    ) -> Dict[str, Any]:
        """Validate address using Google Places API"""
        try:
            if not self.api_key:
                logger.warning("Google Places API key not configured, using mock validation")
                return await self._mock_address_validation(
                    address_line1, city, state, zip_code, country
                )
            
            async with self:
                # Build address string
                address_parts = []
                if address_line1:
                    address_parts.append(address_line1)
                if city:
                    address_parts.append(city)
                if state:
                    address_parts.append(state)
                if zip_code:
                    address_parts.append(zip_code)
                if country:
                    address_parts.append(country)
                
                address_string = ', '.join(address_parts)
                
                if not address_string.strip():
                    return {
                        'valid': False,
                        'error': 'No address components provided',
                        'address': address_string
                    }
                
                # Use Places API Text Search
                params = {
                    'query': address_string,
                    'key': self.api_key,
                    'fields': 'formatted_address,geometry,place_id,name,types'
                }
                
                response = await self._make_request(
                    method='GET',
                    url='https://maps.googleapis.com/maps/api/place/textsearch/json',
                    params=params
                )
                
                status = response.get('status')
                results = response.get('results', [])
                
                if status != 'OK' or not results:
                    return {
                        'valid': False,
                        'error': f'Address not found: {status}',
                        'address': address_string,
                        'api_status': status
                    }
                
                # Get the best match (first result)
                best_match = results[0]
                
                # Extract components
                formatted_address = best_match.get('formatted_address', '')
                place_id = best_match.get('place_id', '')
                types = best_match.get('types', [])
                
                # Check if it's a valid address type
                valid_types = ['street_address', 'premise', 'subpremise', 'route']
                is_valid_address = any(t in valid_types for t in types)
                
                # Get place details for more information
                place_details = await self._get_place_details(place_id)
                
                validation_result = {
                    'valid': is_valid_address,
                    'address': address_string,
                    'formatted_address': formatted_address,
                    'place_id': place_id,
                    'types': types,
                    'geometry': best_match.get('geometry', {}),
                    'details': place_details,
                    'confidence': self._calculate_confidence(best_match, address_string)
                }
                
                # Add suggestions if confidence is low
                if validation_result['confidence'] < 0.8 and len(results) > 1:
                    validation_result['suggestions'] = [
                        {
                            'formatted_address': r.get('formatted_address', ''),
                            'place_id': r.get('place_id', ''),
                            'confidence': self._calculate_confidence(r, address_string)
                        }
                        for r in results[1:6]  # Top 5 suggestions
                    ]
                
                logger.info(f"Address validation completed for {address_string}: {'valid' if is_valid_address else 'invalid'}")
                
                return validation_result
                
        except Exception as e:
            logger.error(f"Address validation failed: {e}")
            return {
                'valid': False,
                'error': f'Validation failed: {str(e)}',
                'address': f"{address_line1}, {city}, {state} {zip_code}, {country}"
            }
    
    async def _get_place_details(self, place_id: str) -> Dict[str, Any]:
        """Get detailed information about a place"""
        try:
            params = {
                'place_id': place_id,
                'key': self.api_key,
                'fields': 'address_components,formatted_address,geometry,name,types'
            }
            
            response = await self._make_request(
                method='GET',
                url='https://maps.googleapis.com/maps/api/place/details/json',
                params=params
            )
            
            result = response.get('result', {})
            
            # Parse address components
            address_components = result.get('address_components', [])
            parsed_components = {}
            
            for component in address_components:
                types = component.get('types', [])
                if 'street_number' in types:
                    parsed_components['street_number'] = component.get('long_name', '')
                elif 'route' in types:
                    parsed_components['route'] = component.get('long_name', '')
                elif 'locality' in types:
                    parsed_components['city'] = component.get('long_name', '')
                elif 'administrative_area_level_1' in types:
                    parsed_components['state'] = component.get('short_name', '')
                elif 'postal_code' in types:
                    parsed_components['zip_code'] = component.get('long_name', '')
                elif 'country' in types:
                    parsed_components['country'] = component.get('short_name', '')
            
            return {
                'address_components': parsed_components,
                'formatted_address': result.get('formatted_address', ''),
                'types': result.get('types', []),
                'geometry': result.get('geometry', {})
            }
            
        except Exception as e:
            logger.error(f"Failed to get place details for {place_id}: {e}")
            return {}
    
    def _calculate_confidence(self, result: Dict[str, Any], original_address: str) -> float:
        """Calculate confidence score for address match"""
        try:
            confidence = 0.5  # Base confidence
            
            # Check types
            types = result.get('types', [])
            if any(t in types for t in ['street_address', 'premise']):
                confidence += 0.3
            elif 'route' in types:
                confidence += 0.2
            
            # Check if formatted address contains original components
            formatted_address = result.get('formatted_address', '').lower()
            original_lower = original_address.lower()
            
            # Simple word matching
            original_words = set(original_lower.split())
            formatted_words = set(formatted_address.split())
            
            if original_words and formatted_words:
                word_overlap = len(original_words.intersection(formatted_words))
                word_confidence = word_overlap / len(original_words)
                confidence += word_confidence * 0.2
            
            return min(confidence, 1.0)
            
        except Exception:
            return 0.5
    
    async def _mock_address_validation(
        self, 
        address_line1: Optional[str],
        city: Optional[str],
        state: Optional[str],
        zip_code: Optional[str],
        country: str
    ) -> Dict[str, Any]:
        """Mock address validation when API key is not available"""
        
        # Simple validation logic
        is_valid = bool(address_line1 and city and state and zip_code)
        
        return {
            'valid': is_valid,
            'address': f"{address_line1}, {city}, {state} {zip_code}, {country}",
            'formatted_address': f"{address_line1}, {city}, {state} {zip_code}, {country}",
            'place_id': 'mock_place_id',
            'types': ['street_address'] if is_valid else [],
            'confidence': 0.8 if is_valid else 0.3,
            'mock': True,
            'message': 'Using mock validation (API key not configured)'
        }
    
    async def geocode_address(self, address: str) -> Dict[str, Any]:
        """Geocode an address to get coordinates"""
        try:
            if not self.maps_api_key:
                logger.warning("Google Maps API key not configured")
                return {
                    'success': False,
                    'error': 'Maps API key not configured'
                }
            
            async with self:
                params = {
                    'address': address,
                    'key': self.maps_api_key
                }
                
                response = await self._make_request(
                    method='GET',
                    url='https://maps.googleapis.com/maps/api/geocode/json',
                    params=params
                )
                
                status = response.get('status')
                results = response.get('results', [])
                
                if status != 'OK' or not results:
                    return {
                        'success': False,
                        'error': f'Geocoding failed: {status}',
                        'status': status
                    }
                
                result = results[0]
                geometry = result.get('geometry', {})
                location = geometry.get('location', {})
                
                return {
                    'success': True,
                    'address': result.get('formatted_address', ''),
                    'latitude': location.get('lat'),
                    'longitude': location.get('lng'),
                    'place_id': result.get('place_id', ''),
                    'types': result.get('types', [])
                }
                
        except Exception as e:
            logger.error(f"Geocoding failed for {address}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Base validation method implementation"""
        return await self.validate_address(
            address_line1=data.get('address_line1'),
            city=data.get('city'),
            state=data.get('state'),
            zip_code=data.get('zip_code'),
            country=data.get('country', 'US')
        )
