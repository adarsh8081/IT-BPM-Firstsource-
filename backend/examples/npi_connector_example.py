"""
NPI Connector Example Usage

This script demonstrates how to use the NPI Registry connector to fetch
provider data and shows example API calls and responses.
"""

import asyncio
import json
from datetime import datetime
from connectors.npi import NPIConnector


async def example_npi_lookup():
    """
    Example: Search for provider by NPI number
    """
    print("=" * 60)
    print("🏥 NPI REGISTRY CONNECTOR EXAMPLE")
    print("=" * 60)
    
    # Initialize connector
    connector = NPIConnector()
    
    # Example 1: Search by NPI number (using a test NPI)
    print("\n📋 Example 1: Search by NPI Number")
    print("-" * 40)
    
    npi_number = "1234567893"  # This is a test NPI number
    print(f"Searching for NPI: {npi_number}")
    
    result = await connector.search_provider_by_npi(npi_number)
    
    if result.success:
        print("✅ Provider Found!")
        print(f"   Name: {result.data['given_name']} {result.data['family_name']}")
        print(f"   NPI: {result.data['npi_number']}")
        print(f"   Practice: {result.data['practice_name']}")
        print(f"   Specialty: {result.data['primary_taxonomy']}")
        print(f"   Address: {result.data['address_street']}")
        print(f"   City: {result.data['address_city']}, {result.data['address_state']} {result.data['address_zip']}")
        print(f"   Phone: {result.data['phone_primary']}")
        
        print("\n📊 Trust Scores:")
        for field, trust in result.trust_scores.items():
            print(f"   {field:20}: {trust.score:.2f} - {trust.confidence}")
            print(f"   {'':20}   {trust.reason}")
        
        print("\n🔍 Raw API Response:")
        print(json.dumps(result.data, indent=2, default=str))
        
    else:
        print(f"❌ Error: {result.error}")
        print("   This is expected for test NPI numbers that don't exist in the registry")


async def example_name_search():
    """
    Example: Search for providers by name
    """
    print("\n" + "=" * 60)
    print("📋 Example 2: Search by Provider Name")
    print("=" * 60)
    
    connector = NPIConnector()
    
    # Example 2: Search by name
    first_name = "John"
    last_name = "Smith"
    state = "CA"
    
    print(f"Searching for: {first_name} {last_name} in {state}")
    
    result = await connector.search_provider_by_name(first_name, last_name, state)
    
    if result.success:
        print(f"✅ Found {len(result.data)} providers")
        
        for i, provider in enumerate(result.data[:3], 1):  # Show first 3 results
            print(f"\n   Provider {i}:")
            print(f"   Name: {provider['given_name']} {provider['family_name']}")
            print(f"   NPI: {provider['npi_number']}")
            print(f"   Practice: {provider['practice_name']}")
            print(f"   Specialty: {provider['primary_taxonomy']}")
            print(f"   Location: {provider['address_city']}, {provider['address_state']}")
            
            # Show trust scores for first provider
            if i == 1:
                print(f"\n   📊 Trust Scores for Provider {i}:")
                provider_trust = result.trust_scores[f"provider_{i-1}"]
                for field, trust in provider_trust.items():
                    if trust.score > 0:
                        print(f"      {field:15}: {trust.score:.2f}")
    else:
        print(f"❌ Error: {result.error}")


async def example_error_handling():
    """
    Example: Error handling scenarios
    """
    print("\n" + "=" * 60)
    print("⚠️  Example 3: Error Handling")
    print("=" * 60)
    
    connector = NPIConnector()
    
    # Test invalid NPI format
    print("\n🔍 Testing Invalid NPI Format:")
    result = await connector.search_provider_by_npi("123")  # Too short
    print(f"   Result: {result.success} - {result.error}")
    
    # Test non-existent NPI
    print("\n🔍 Testing Non-existent NPI:")
    result = await connector.search_provider_by_npi("9999999999")  # Invalid checksum
    print(f"   Result: {result.success} - {result.error}")
    
    # Test name search with no results
    print("\n🔍 Testing Name Search with No Results:")
    result = await connector.search_provider_by_name("NonExistent", "Provider")
    print(f"   Result: {result.success} - {result.error}")


def show_json_response_example():
    """
    Show example JSON response structure
    """
    print("\n" + "=" * 60)
    print("📄 Example JSON Response Structure")
    print("=" * 60)
    
    example_response = {
        "success": True,
        "data": {
            "npi_number": "1234567890",
            "given_name": "JOHN",
            "family_name": "SMITH",
            "primary_taxonomy": "207Q00000X",
            "practice_name": "JOHN SMITH MEDICAL PRACTICE",
            "address_street": "123 MAIN ST",
            "address_city": "SAN FRANCISCO",
            "address_state": "CA",
            "address_zip": "94102",
            "phone_primary": "415-555-0123",
            "email": "",
            "license_number": "",
            "license_state": "",
            "license_status": "",
            "_npi_metadata": {
                "enumeration_type": "NPI-1",
                "credential": "MD",
                "middle_name": "MICHAEL",
                "gender": "M",
                "enumeration_date": "2005-06-13",
                "last_updated": "2023-01-15",
                "all_taxonomies": ["Family Medicine"],
                "all_addresses": 1
            }
        },
        "trust_scores": {
            "npi_number": {
                "score": 0.98,
                "reason": "Official NPI Registry data",
                "source": "npi_registry",
                "confidence": "high"
            },
            "given_name": {
                "score": 0.95,
                "reason": "Official registry name data",
                "source": "npi_registry",
                "confidence": "high"
            },
            "family_name": {
                "score": 0.95,
                "reason": "Official registry name data",
                "source": "npi_registry",
                "confidence": "high"
            },
            "primary_taxonomy": {
                "score": 0.92,
                "reason": "Official taxonomy classification",
                "source": "npi_registry",
                "confidence": "high"
            },
            "practice_name": {
                "score": 0.80,
                "reason": "Organization name from registry",
                "source": "npi_registry",
                "confidence": "medium"
            },
            "address_street": {
                "score": 0.85,
                "reason": "Primary address from registry",
                "source": "npi_registry",
                "confidence": "medium"
            },
            "phone_primary": {
                "score": 0.70,
                "reason": "Phone from registry (may be outdated)",
                "source": "npi_registry",
                "confidence": "medium"
            },
            "email": {
                "score": 0.0,
                "reason": "No email in registry",
                "source": "npi_registry",
                "confidence": "none"
            },
            "license_number": {
                "score": 0.0,
                "reason": "NPI Registry doesn't provide license information",
                "source": "npi_registry",
                "confidence": "none"
            }
        },
        "source": "npi_registry",
        "timestamp": "2024-01-15T10:30:00Z"
    }
    
    print(json.dumps(example_response, indent=2))


async def main():
    """
    Main function to run all examples
    """
    try:
        # Run examples
        await example_npi_lookup()
        await example_name_search()
        await example_error_handling()
        show_json_response_example()
        
        print("\n" + "=" * 60)
        print("✅ NPI Connector Examples Complete!")
        print("=" * 60)
        print("\n📝 Key Features Demonstrated:")
        print("   ✅ NPI number validation and lookup")
        print("   ✅ Provider name search with state filtering")
        print("   ✅ Data normalization to our schema")
        print("   ✅ Per-field trust score calculation")
        print("   ✅ Comprehensive error handling")
        print("   ✅ Rate limiting and API best practices")
        print("   ✅ Structured JSON responses with metadata")
        
        print("\n🔗 API Endpoints Used:")
        print("   • GET https://npiregistry.cms.hhs.gov/api")
        print("   • Parameters: number, first_name, last_name, state, etc.")
        print("   • Response: JSON with provider data and metadata")
        
    except Exception as e:
        print(f"❌ Error running examples: {e}")


if __name__ == "__main__":
    asyncio.run(main())
