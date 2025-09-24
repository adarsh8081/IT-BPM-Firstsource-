"""
NPI Registry API connector
"""

import logging
from typing import Dict, Any, Optional
import asyncio

from .base import BaseConnector
from ..config import settings

logger = logging.getLogger(__name__)

class NpiConnector(BaseConnector):
    """Connector for NPI Registry API"""
    
    def __init__(self):
        super().__init__(rate_limit=settings.NPI_API_RATE_LIMIT)
        self.base_url = "https://npiregistry.cms.hhs.gov/api"
        self.api_key = settings.NPI_API_KEY
        
    async def validate_npi(self, npi: str) -> Dict[str, Any]:
        """Validate NPI number against NPI Registry"""
        try:
            async with self:
                # Clean NPI (remove any non-digits)
                clean_npi = ''.join(filter(str.isdigit, npi))
                
                if len(clean_npi) != 10:
                    return {
                        'valid': False,
                        'error': 'NPI must be exactly 10 digits',
                        'npi': npi,
                        'clean_npi': clean_npi
                    }
                
                # Make API request
                params = {
                    'version': '2.1',
                    'number': clean_npi,
                    'enumeration_type': 'NPI-1,NPI-2'  # Both individual and organization
                }
                
                if self.api_key:
                    params['api_key'] = self.api_key
                
                response = await self._make_request(
                    method='GET',
                    url=f"{self.base_url}/",
                    params=params
                )
                
                # Parse response
                result_count = response.get('result_count', 0)
                
                if result_count == 0:
                    return {
                        'valid': False,
                        'error': 'NPI not found in registry',
                        'npi': npi,
                        'clean_npi': clean_npi,
                        'api_response': response
                    }
                
                # Get the first result
                results = response.get('results', [])
                if not results:
                    return {
                        'valid': False,
                        'error': 'No results returned from NPI registry',
                        'npi': npi,
                        'clean_npi': clean_npi,
                        'api_response': response
                    }
                
                npi_data = results[0]
                
                # Validate basic fields
                is_valid = True
                validation_details = {
                    'npi': clean_npi,
                    'enumeration_type': npi_data.get('enumeration_type'),
                    'basic': npi_data.get('basic', {}),
                    'addresses': npi_data.get('addresses', []),
                    'taxonomies': npi_data.get('taxonomies', []),
                    'identifiers': npi_data.get('identifiers', [])
                }
                
                # Check if NPI is active
                basic = npi_data.get('basic', {})
                status = basic.get('status', '').lower()
                if status != 'a':  # Active
                    is_valid = False
                    validation_details['error'] = f'NPI status is not active: {status}'
                
                # Check enumeration type
                enum_type = npi_data.get('enumeration_type', '').lower()
                if enum_type not in ['npi-1', 'npi-2']:
                    is_valid = False
                    validation_details['error'] = f'Invalid enumeration type: {enum_type}'
                
                logger.info(f"NPI validation completed for {npi}: {'valid' if is_valid else 'invalid'}")
                
                return {
                    'valid': is_valid,
                    'npi': npi,
                    'clean_npi': clean_npi,
                    'details': validation_details,
                    'api_response': self._sanitize_log_data(response)
                }
                
        except Exception as e:
            logger.error(f"NPI validation failed for {npi}: {e}")
            return {
                'valid': False,
                'error': f'Validation failed: {str(e)}',
                'npi': npi
            }
    
    async def search_providers(
        self, 
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        taxonomy: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """Search for providers in NPI Registry"""
        try:
            async with self:
                params = {
                    'version': '2.1',
                    'limit': min(limit, 200)  # API limit
                }
                
                if first_name:
                    params['first_name'] = first_name
                if last_name:
                    params['last_name'] = last_name
                if city:
                    params['city'] = city
                if state:
                    params['state'] = state
                if taxonomy:
                    params['taxonomy_description'] = taxonomy
                
                if self.api_key:
                    params['api_key'] = self.api_key
                
                response = await self._make_request(
                    method='GET',
                    url=f"{self.base_url}/",
                    params=params
                )
                
                return {
                    'success': True,
                    'result_count': response.get('result_count', 0),
                    'results': response.get('results', []),
                    'search_params': params
                }
                
        except Exception as e:
            logger.error(f"NPI search failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'result_count': 0,
                'results': []
            }
    
    async def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Base validation method implementation"""
        npi = data.get('npi')
        if not npi:
            return {
                'valid': False,
                'error': 'NPI is required for validation'
            }
        
        return await self.validate_npi(npi)
