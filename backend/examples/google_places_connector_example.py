"""
Google Places Connector Example Usage

This script demonstrates how to use the Google Places connector to validate
addresses and shows example API calls and responses.
"""

import asyncio
import json
from datetime import datetime
from connectors.google_places import GooglePlacesConnector


async def example_address_validation():
    """
    Example: Validate address using Google Geocoding API
    """
    print("=" * 60)
    print("🏢 GOOGLE PLACES CONNECTOR EXAMPLE")
    print("=" * 60)
    
    # Initialize connector (requires valid Google API key)
    api_key = "YOUR_GOOGLE_API_KEY"  # Replace with actual API key
    connector = GooglePlacesConnector(api_key)
    
    # Example 1: Validate full address
    print("\n📋 Example 1: Full Address Validation")
    print("-" * 40)
    
    address = "1600 Amphitheatre Parkway, Mountain View, CA 94043"
    print(f"Validating address: {address}")
    
    result = await connector.validate_address(address, "US")
    
    if result.success:
        print("✅ Address validated successfully!")
        print(f"   Place ID: {result.data['place_id']}")
        print(f"   Formatted Address: {result.data['formatted_address']}")
        print(f"   Coordinates: {result.data['latitude']}, {result.data['longitude']}")
        print(f"   Street: {result.data['address_street']}")
        print(f"   City: {result.data['address_city']}")
        print(f"   State: {result.data['address_state']}")
        print(f"   ZIP: {result.data['address_zip']}")
        print(f"   Country: {result.data['country']}")
        print(f"   Geometry Accuracy: {result.data['geometry_accuracy']}")
        print(f"   Match Confidence: {result.data['match_confidence']:.2f}")
        
        print("\n📊 Trust Scores:")
        for field, trust in result.trust_scores.items():
            print(f"   {field:20}: {trust.score:.2f} - {trust.confidence}")
            print(f"   {'':20}   {trust.reason}")
        
        print("\n🔍 Raw API Response:")
        print(json.dumps(result.data, indent=2, default=str))
        
    else:
        print(f"❌ Error: {result.error}")
        print("   This may be due to invalid API key or API limits")


async def example_address_components():
    """
    Example: Validate address using individual components
    """
    print("\n" + "=" * 60)
    print("📋 Example 2: Address Components Validation")
    print("=" * 60)
    
    api_key = "YOUR_GOOGLE_API_KEY"  # Replace with actual API key
    connector = GooglePlacesConnector(api_key)
    
    # Example 2: Validate using components
    components = {
        'street': '123 Main Street',
        'city': 'San Francisco',
        'state': 'CA',
        'zip': '94102',
        'country': 'US'
    }
    
    print(f"Validating components:")
    for key, value in components.items():
        print(f"   {key}: {value}")
    
    result = await connector.validate_address_components(components)
    
    if result.success:
        print("\n✅ Components validated successfully!")
        print(f"   Place ID: {result.data['place_id']}")
        print(f"   Normalized Street: {result.data['address_street']}")
        print(f"   Normalized City: {result.data['address_city']}")
        print(f"   Normalized State: {result.data['address_state']}")
        print(f"   Normalized ZIP: {result.data['address_zip']}")
        print(f"   Coordinates: {result.data['latitude']}, {result.data['longitude']}")
        print(f"   Match Confidence: {result.data['match_confidence']:.2f}")
        
        print("\n📊 Trust Scores:")
        for field, trust in result.trust_scores.items():
            if trust.score > 0:
                print(f"   {field:15}: {trust.score:.2f} - {trust.confidence}")
    else:
        print(f"❌ Error: {result.error}")


async def example_place_details():
    """
    Example: Get detailed place information using place_id
    """
    print("\n" + "=" * 60)
    print("📋 Example 3: Place Details Retrieval")
    print("=" * 60)
    
    api_key = "YOUR_GOOGLE_API_KEY"  # Replace with actual API key
    connector = GooglePlacesConnector(api_key)
    
    # Example 3: Get place details
    place_id = "ChIJ1234567890abcdef"  # This is a test place ID
    
    print(f"Getting details for Place ID: {place_id}")
    
    result = await connector.get_place_details(place_id)
    
    if result.success:
        print("✅ Place details retrieved successfully!")
        print(f"   Name: {result.data['name']}")
        print(f"   Place ID: {result.data['place_id']}")
        print(f"   Formatted Address: {result.data['formatted_address']}")
        print(f"   Coordinates: {result.data['latitude']}, {result.data['longitude']}")
        print(f"   Types: {', '.join(result.data['types'])}")
        print(f"   Match Confidence: {result.data['match_confidence']:.2f}")
        
        print("\n📊 Trust Scores:")
        for field, trust in result.trust_scores.items():
            if trust.score > 0:
                print(f"   {field:15}: {trust.score:.2f} - {trust.confidence}")
    else:
        print(f"❌ Error: {result.error}")


async def example_error_handling():
    """
    Example: Error handling scenarios
    """
    print("\n" + "=" * 60)
    print("⚠️  Example 4: Error Handling")
    print("=" * 60)
    
    api_key = "YOUR_GOOGLE_API_KEY"  # Replace with actual API key
    connector = GooglePlacesConnector(api_key)
    
    # Test invalid address
    print("\n🔍 Testing Invalid Address:")
    result = await connector.validate_address("Nonexistent Address 12345")
    print(f"   Result: {result.success} - {result.error}")
    
    # Test invalid place ID
    print("\n🔍 Testing Invalid Place ID:")
    result = await connector.get_place_details("invalid_place_id")
    print(f"   Result: {result.success} - {result.error}")
    
    # Test empty components
    print("\n🔍 Testing Empty Address Components:")
    result = await connector.validate_address_components({})
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
            "place_id": "ChIJ1234567890abcdef",
            "formatted_address": "1600 Amphitheatre Parkway, Mountain View, CA 94043, USA",
            "latitude": 37.4220656,
            "longitude": -122.0840897,
            "street_number": "1600",
            "route": "Amphitheatre Parkway",
            "address_street": "1600 Amphitheatre Parkway",
            "address_city": "Mountain View",
            "address_state": "CA",
            "address_zip": "94043",
            "country": "US",
            "geometry_accuracy": "ROOFTOP",
            "match_confidence": 0.95
        },
        "trust_scores": {
            "place_id": {
                "score": 0.95,
                "reason": "Google Places unique identifier",
                "source": "google_places",
                "confidence": "high"
            },
            "latitude": {
                "score": 0.90,
                "reason": "Google Maps coordinate data",
                "source": "google_places",
                "confidence": "high"
            },
            "longitude": {
                "score": 0.90,
                "reason": "Google Maps coordinate data",
                "source": "google_places",
                "confidence": "high"
            },
            "formatted_address": {
                "score": 0.90,
                "reason": "Google formatted address",
                "source": "google_places",
                "confidence": "high"
            },
            "address_street": {
                "score": 0.85,
                "reason": "Google street address data",
                "source": "google_places",
                "confidence": "high"
            },
            "match_confidence": {
                "score": 0.95,
                "reason": "Google geometry accuracy assessment",
                "source": "google_places",
                "confidence": "high"
            }
        },
        "source": "google_geocoding",
        "timestamp": "2024-01-15T10:30:00Z"
    }
    
    print(json.dumps(example_response, indent=2))


def show_api_endpoints():
    """
    Show Google API endpoints and parameters
    """
    print("\n" + "=" * 60)
    print("🔗 Google API Endpoints")
    print("=" * 60)
    
    print("\n📍 Geocoding API:")
    print("   Endpoint: https://maps.googleapis.com/maps/api/geocode/json")
    print("   Method: GET")
    print("   Parameters:")
    print("     • address: Address string to geocode")
    print("     • key: Google API key")
    print("     • region: Country code bias (optional)")
    print("   Response: JSON with geocoded results")
    
    print("\n🏢 Places API (Place Details):")
    print("   Endpoint: https://maps.googleapis.com/maps/api/place/details/json")
    print("   Method: GET")
    print("   Parameters:")
    print("     • place_id: Google Places place ID")
    print("     • key: Google API key")
    print("     • fields: Specific fields to return")
    print("   Response: JSON with place details")


async def main():
    """
    Main function to run all examples
    """
    try:
        # Run examples
        await example_address_validation()
        await example_address_components()
        await example_place_details()
        await example_error_handling()
        show_json_response_example()
        show_api_endpoints()
        
        print("\n" + "=" * 60)
        print("✅ Google Places Connector Examples Complete!")
        print("=" * 60)
        print("\n📝 Key Features Demonstrated:")
        print("   ✅ Address validation using Google Geocoding API")
        print("   ✅ Address component validation")
        print("   ✅ Place details retrieval")
        print("   ✅ Data normalization and trust scoring")
        print("   ✅ Exponential backoff and rate limiting")
        print("   ✅ Comprehensive error handling")
        print("   ✅ Coordinate extraction and geometry accuracy")
        
        print("\n🔧 Configuration Required:")
        print("   • Google API key with Geocoding API enabled")
        print("   • Google API key with Places API enabled")
        print("   • Billing account for API usage")
        print("   • Rate limiting configuration")
        
        print("\n⚠️  Important Notes:")
        print("   • Google APIs have usage quotas and billing")
        print("   • Rate limiting is built-in to prevent quota exhaustion")
        print("   • Exponential backoff handles temporary failures")
        print("   • Trust scores reflect data quality and accuracy")
        
    except Exception as e:
        print(f"❌ Error running examples: {e}")


if __name__ == "__main__":
    # Run examples (requires valid Google API key)
    # asyncio.run(main())
    print("Google Places Connector - Examples require valid Google API key")
    print("To run examples:")
    print("1. Get a Google API key from Google Cloud Console")
    print("2. Enable Geocoding API and Places API")
    print("3. Replace 'YOUR_GOOGLE_API_KEY' in the script")
    print("4. Run: python google_places_connector_example.py")
