"""
NPI Registry API Connector

This module provides functionality to fetch provider data from the NPI Registry API
(https://npiregistry.cms.hhs.gov/api/) and normalize it to match our provider schema.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import httpx
from dataclasses import dataclass

from .base import BaseConnector, ConnectorResponse, TrustScore

logger = logging.getLogger(__name__)


@dataclass
class NPISearchParams:
    """Parameters for NPI Registry API search"""
    number: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    taxonomy_description: Optional[str] = None
    limit: int = 200


class NPIConnector(BaseConnector):
    """
    NPI Registry API Connector
    
    Fetches provider data from the official NPI Registry API and normalizes
    it to match our provider schema with per-field trust scores.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize NPI Connector
        
        Args:
            api_key: Optional API key (NPI Registry doesn't require authentication)
        """
        super().__init__(
            name="npi_registry",
            base_url="https://npiregistry.cms.hhs.gov/api",
            api_key=api_key,
            rate_limit_delay=0.1,  # 10 requests per second
            max_retries=3
        )
    
    async def search_provider_by_npi(self, npi_number: str) -> ConnectorResponse:
        """
        Search for provider by NPI number
        
        Args:
            npi_number: 10-digit NPI number
            
        Returns:
            ConnectorResponse with normalized provider data
        """
        try:
            # Validate NPI format
            if not self._validate_npi_format(npi_number):
                return ConnectorResponse(
                    success=False,
                    error="Invalid NPI format. Must be 10 digits.",
                    data=None,
                    trust_scores=None
                )
            
            params = NPISearchParams(number=npi_number)
            response = await self._search_npi(params)
            
            if response.success and response.data:
                # NPI search should return exactly one result
                provider_data = response.data[0] if isinstance(response.data, list) else response.data
                normalized_data = self._normalize_provider_data(provider_data)
                trust_scores = self._calculate_trust_scores(provider_data, "npi_search")
                
                return ConnectorResponse(
                    success=True,
                    data=normalized_data,
                    trust_scores=trust_scores,
                    source="npi_registry",
                    timestamp=datetime.utcnow()
                )
            else:
                return ConnectorResponse(
                    success=False,
                    error=f"NPI {npi_number} not found in registry",
                    data=None,
                    trust_scores=None
                )
                
        except Exception as e:
            logger.error(f"Error searching NPI {npi_number}: {str(e)}")
            return ConnectorResponse(
                success=False,
                error=f"API error: {str(e)}",
                data=None,
                trust_scores=None
            )
    
    async def search_provider_by_name(self, first_name: str, last_name: str, 
                                    state: Optional[str] = None) -> ConnectorResponse:
        """
        Search for providers by name
        
        Args:
            first_name: Provider's first name
            last_name: Provider's last name
            state: Optional state abbreviation (2 letters)
            
        Returns:
            ConnectorResponse with list of matching providers
        """
        try:
            params = NPISearchParams(
                first_name=first_name,
                last_name=last_name,
                state=state,
                limit=50
            )
            
            response = await self._search_npi(params)
            
            if response.success and response.data:
                # Normalize all results
                normalized_providers = []
                all_trust_scores = {}
                
                for i, provider_data in enumerate(response.data):
                    normalized_data = self._normalize_provider_data(provider_data)
                    trust_scores = self._calculate_trust_scores(provider_data, "name_search")
                    
                    normalized_providers.append(normalized_data)
                    all_trust_scores[f"provider_{i}"] = trust_scores
                
                return ConnectorResponse(
                    success=True,
                    data=normalized_providers,
                    trust_scores=all_trust_scores,
                    source="npi_registry",
                    timestamp=datetime.utcnow()
                )
            else:
                return ConnectorResponse(
                    success=False,
                    error=f"No providers found for {first_name} {last_name}",
                    data=None,
                    trust_scores=None
                )
                
        except Exception as e:
            logger.error(f"Error searching by name {first_name} {last_name}: {str(e)}")
            return ConnectorResponse(
                success=False,
                error=f"API error: {str(e)}",
                data=None,
                trust_scores=None
            )
    
    async def _search_npi(self, params: NPISearchParams) -> ConnectorResponse:
        """
        Perform NPI Registry API search
        
        Args:
            params: Search parameters
            
        Returns:
            Raw API response
        """
        try:
            await self._rate_limit()
            
            # Build query parameters
            query_params = {}
            if params.number:
                query_params["number"] = params.number
            if params.first_name:
                query_params["first_name"] = params.first_name
            if params.last_name:
                query_params["last_name"] = params.last_name
            if params.city:
                query_params["city"] = params.city
            if params.state:
                query_params["state"] = params.state
            if params.taxonomy_description:
                query_params["taxonomy_description"] = params.taxonomy_description
            if params.limit:
                query_params["limit"] = params.limit
            
            # Make API request
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}",
                    params=query_params,
                    headers=self._get_headers()
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get("result_count", 0) > 0:
                        return ConnectorResponse(
                            success=True,
                            data=data.get("results", []),
                            trust_scores=None,
                            source="npi_registry",
                            timestamp=datetime.utcnow()
                        )
                    else:
                        return ConnectorResponse(
                            success=False,
                            error="No results found",
                            data=None,
                            trust_scores=None
                        )
                else:
                    return ConnectorResponse(
                        success=False,
                        error=f"API returned status {response.status_code}",
                        data=None,
                        trust_scores=None
                    )
                    
        except httpx.TimeoutException:
            return ConnectorResponse(
                success=False,
                error="Request timeout",
                data=None,
                trust_scores=None
            )
        except Exception as e:
            return ConnectorResponse(
                success=False,
                error=f"Request failed: {str(e)}",
                data=None,
                trust_scores=None
            )
    
    def _normalize_provider_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize NPI Registry data to our provider schema
        
        Args:
            raw_data: Raw data from NPI Registry API
            
        Returns:
            Normalized provider data
        """
        # Extract basic provider information
        basic_info = raw_data.get("basic", {})
        addresses = raw_data.get("addresses", [])
        taxonomies = raw_data.get("taxonomies", [])
        
        # Get primary address (usually the first one)
        primary_address = addresses[0] if addresses else {}
        
        # Get primary taxonomy
        primary_taxonomy = None
        primary_taxonomy_desc = None
        if taxonomies:
            # Find primary taxonomy (usually the first one or one marked as primary)
            primary_tax = taxonomies[0]
            primary_taxonomy = primary_tax.get("code", "")
            primary_taxonomy_desc = primary_tax.get("desc", "")
        
        normalized = {
            "npi_number": raw_data.get("number", ""),
            "given_name": basic_info.get("first_name", ""),
            "family_name": basic_info.get("last_name", ""),
            "primary_taxonomy": primary_taxonomy,
            "practice_name": basic_info.get("organization_name", ""),
            "address_street": primary_address.get("address_1", ""),
            "address_city": primary_address.get("city", ""),
            "address_state": primary_address.get("state", ""),
            "address_zip": primary_address.get("postal_code", ""),
            "phone_primary": primary_address.get("telephone_number", ""),
            "email": basic_info.get("email", ""),
            "license_number": "",  # NPI Registry doesn't provide license numbers
            "license_state": "",   # NPI Registry doesn't provide license info
            "license_status": "",  # NPI Registry doesn't provide license status
        }
        
        # Add additional metadata
        normalized["_npi_metadata"] = {
            "enumeration_type": raw_data.get("enumeration_type", ""),
            "credential": basic_info.get("credential", ""),
            "middle_name": basic_info.get("middle_name", ""),
            "name_prefix": basic_info.get("name_prefix", ""),
            "name_suffix": basic_info.get("name_suffix", ""),
            "sole_proprietor": basic_info.get("sole_proprietor", ""),
            "gender": basic_info.get("gender", ""),
            "enumeration_date": raw_data.get("enumeration_date", ""),
            "last_updated": raw_data.get("last_updated", ""),
            "certification_date": raw_data.get("certification_date", ""),
            "all_taxonomies": [tax.get("desc", "") for tax in taxonomies],
            "all_addresses": len(addresses)
        }
        
        return normalized
    
    def _calculate_trust_scores(self, raw_data: Dict[str, Any], search_type: str) -> Dict[str, TrustScore]:
        """
        Calculate trust scores for each field based on data quality and source reliability
        
        Args:
            raw_data: Raw data from NPI Registry
            search_type: Type of search performed ("npi_search" or "name_search")
            
        Returns:
            Dictionary of field trust scores
        """
        trust_scores = {}
        
        # Base trust scores for NPI Registry (high reliability)
        base_trust = 0.95 if search_type == "npi_search" else 0.85
        
        # NPI number - highest trust for direct NPI lookup
        npi_trust = 0.98 if search_type == "npi_search" else 0.90
        trust_scores["npi_number"] = TrustScore(
            score=npi_trust,
            reason="Official NPI Registry data",
            source="npi_registry",
            confidence="high"
        )
        
        # Name fields - high trust from official source
        trust_scores["given_name"] = TrustScore(
            score=base_trust,
            reason="Official registry name data",
            source="npi_registry",
            confidence="high"
        )
        
        trust_scores["family_name"] = TrustScore(
            score=base_trust,
            reason="Official registry name data",
            source="npi_registry",
            confidence="high"
        )
        
        # Taxonomy - high trust for official classifications
        trust_scores["primary_taxonomy"] = TrustScore(
            score=0.92,
            reason="Official taxonomy classification",
            source="npi_registry",
            confidence="high"
        )
        
        # Practice name - medium-high trust
        trust_scores["practice_name"] = TrustScore(
            score=0.80,
            reason="Organization name from registry",
            source="npi_registry",
            confidence="medium"
        )
        
        # Address fields - medium-high trust
        address_trust = 0.85
        trust_scores["address_street"] = TrustScore(
            score=address_trust,
            reason="Primary address from registry",
            source="npi_registry",
            confidence="medium"
        )
        
        trust_scores["address_city"] = TrustScore(
            score=address_trust,
            reason="Primary address from registry",
            source="npi_registry",
            confidence="medium"
        )
        
        trust_scores["address_state"] = TrustScore(
            score=address_trust,
            reason="Primary address from registry",
            source="npi_registry",
            confidence="medium"
        )
        
        trust_scores["address_zip"] = TrustScore(
            score=address_trust,
            reason="Primary address from registry",
            source="npi_registry",
            confidence="medium"
        )
        
        # Phone - medium trust (may be outdated)
        trust_scores["phone_primary"] = TrustScore(
            score=0.70,
            reason="Phone from registry (may be outdated)",
            source="npi_registry",
            confidence="medium"
        )
        
        # Email - lower trust (often missing or outdated)
        email_trust = 0.60 if raw_data.get("basic", {}).get("email") else 0.0
        trust_scores["email"] = TrustScore(
            score=email_trust,
            reason="Email from registry (often missing/outdated)" if email_trust > 0 else "No email in registry",
            source="npi_registry",
            confidence="low" if email_trust > 0 else "none"
        )
        
        # License fields - no trust (NPI Registry doesn't provide license info)
        trust_scores["license_number"] = TrustScore(
            score=0.0,
            reason="NPI Registry doesn't provide license information",
            source="npi_registry",
            confidence="none"
        )
        
        trust_scores["license_state"] = TrustScore(
            score=0.0,
            reason="NPI Registry doesn't provide license information",
            source="npi_registry",
            confidence="none"
        )
        
        trust_scores["license_status"] = TrustScore(
            score=0.0,
            reason="NPI Registry doesn't provide license information",
            source="npi_registry",
            confidence="none"
        )
        
        return trust_scores
    
    def _validate_npi_format(self, npi: str) -> bool:
        """
        Validate NPI number format
        
        Args:
            npi: NPI number to validate
            
        Returns:
            True if valid format, False otherwise
        """
        if not npi:
            return False
        
        # Remove any non-digit characters
        clean_npi = ''.join(filter(str.isdigit, npi))
        
        # Check if exactly 10 digits
        if len(clean_npi) != 10:
            return False
        
        # Check Luhn algorithm (NPI validation)
        def luhn_checksum(npi_string):
            def digits_of(n):
                return [int(d) for d in str(n)]
            digits = digits_of(npi_string)
            odd_digits = digits[-1::-2]
            even_digits = digits[-2::-2]
            checksum = sum(odd_digits)
            for d in even_digits:
                checksum += sum(digits_of(d*2))
            return checksum % 10
        
        return luhn_checksum(clean_npi) == 0
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for API requests"""
        headers = {
            "User-Agent": "Provider-Validation-System/1.0",
            "Accept": "application/json",
        }
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        return headers


# Example usage and testing functions
async def example_npi_lookup():
    """
    Example function demonstrating NPI lookup
    """
    connector = NPIConnector()
    
    # Example 1: Search by NPI number
    print("=== NPI Lookup Example ===")
    npi_number = "1234567890"  # Example NPI (this is a test number)
    
    result = await connector.search_provider_by_npi(npi_number)
    
    if result.success:
        print(f"✅ Found provider: {result.data['given_name']} {result.data['family_name']}")
        print(f"   NPI: {result.data['npi_number']}")
        print(f"   Practice: {result.data['practice_name']}")
        print(f"   Specialty: {result.data['primary_taxonomy']}")
        print(f"   Address: {result.data['address_street']}, {result.data['address_city']}, {result.data['address_state']}")
        
        print("\n📊 Trust Scores:")
        for field, trust in result.trust_scores.items():
            print(f"   {field}: {trust.score:.2f} - {trust.reason}")
    else:
        print(f"❌ Error: {result.error}")


async def example_name_search():
    """
    Example function demonstrating name search
    """
    connector = NPIConnector()
    
    # Example 2: Search by name
    print("\n=== Name Search Example ===")
    first_name = "John"
    last_name = "Smith"
    state = "CA"
    
    result = await connector.search_provider_by_name(first_name, last_name, state)
    
    if result.success:
        print(f"✅ Found {len(result.data)} providers matching '{first_name} {last_name}' in {state}")
        
        for i, provider in enumerate(result.data[:3]):  # Show first 3 results
            print(f"\n   Provider {i+1}:")
            print(f"   Name: {provider['given_name']} {provider['family_name']}")
            print(f"   NPI: {provider['npi_number']}")
            print(f"   Practice: {provider['practice_name']}")
            print(f"   Specialty: {provider['primary_taxonomy']}")
    else:
        print(f"❌ Error: {result.error}")


if __name__ == "__main__":
    # Run examples
    asyncio.run(example_npi_lookup())
    asyncio.run(example_name_search())
