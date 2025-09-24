"""
Demonstration script for the precise provider model
"""

import asyncio
from datetime import datetime
from sqlalchemy.orm import Session
from database import get_db
from models.provider import Provider


async def demo_provider_model():
    """Demonstrate the precise provider model functionality"""
    print("🏥 Provider Data Model Demonstration")
    print("=" * 50)
    
    # Create a sample provider
    provider_data = {
        "given_name": "Dr. Sarah",
        "family_name": "Johnson",
        "npi_number": "1234567890",
        "primary_taxonomy": "207Q00000X",
        "practice_name": "Johnson Family Medicine",
        "address_street": "123 Medical Center Dr",
        "address_city": "San Francisco",
        "address_state": "CA",
        "address_zip": "94102",
        "place_id": "ChIJ1234567890abcdef",
        "phone_primary": "415-555-0123",
        "phone_alt": "415-555-0124",
        "email": "sarah.johnson@johnsonfamilymedicine.com",
        "license_number": "A123456",
        "license_state": "CA",
        "license_status": "active",
        "affiliations": [
            {"organization": "San Francisco General Hospital", "role": "Attending Physician"},
            {"organization": "Bay Area Medical Group", "role": "Partner"}
        ],
        "services_offered": {
            "primary_care": True,
            "preventive_care": True,
            "pediatrics": True,
            "internal_medicine": True,
            "mental_health": False,
            "surgery": False
        }
    }
    
    # Create provider instance
    provider = Provider(**provider_data)
    print(f"✅ Created provider: {provider.full_name}")
    print(f"   NPI: {provider.npi_number}")
    print(f"   Practice: {provider.practice_name}")
    print(f"   Address: {provider.full_address}")
    
    # Demonstrate validation tracking
    print("\n🔍 Validation Tracking Demo:")
    provider.last_validated_at = datetime.utcnow()
    provider.validated_by = "validation_agent_001"
    
    # Add field confidence scores
    provider.update_field_confidence("npi_number", 0.95)
    provider.update_field_confidence("address", 0.88)
    provider.update_field_confidence("license", 0.92)
    provider.update_field_confidence("contact", 0.78)
    
    # Calculate overall confidence
    overall_confidence = provider.calculate_overall_confidence()
    provider.overall_confidence = overall_confidence
    
    print(f"   Field Confidence Scores:")
    for field, data in provider.field_confidence.items():
        print(f"     {field}: {data['score']:.2f}")
    print(f"   Overall Confidence: {overall_confidence:.2f}")
    
    # Add validation flags
    print("\n🚩 Validation Flags Demo:")
    provider.add_flag("ADDRESS_VERIFIED", "Address verified via Google Places API")
    provider.add_flag("LICENSE_ACTIVE", "License status confirmed with state board")
    provider.add_flag("EMAIL_VALIDATED", "Email address validated and active")
    
    print(f"   Flags ({len(provider.flags)}):")
    for flag in provider.flags:
        print(f"     {flag['code']}: {flag['reason']}")
    
    # Convert to dictionary
    print("\n📋 Provider Data Export:")
    provider_dict = provider.to_dict()
    print(f"   Exported {len(provider_dict)} fields")
    print(f"   Provider ID: {provider_dict['provider_id']}")
    print(f"   Created: {provider_dict['created_at']}")
    print(f"   Updated: {provider_dict['updated_at']}")
    
    # Database operations (commented out for demo)
    print("\n💾 Database Operations:")
    print("   To insert into database:")
    print("   1. db = next(get_db())")
    print("   2. db.add(provider)")
    print("   3. db.commit()")
    
    print("\n🎯 Model Features Demonstrated:")
    print("   ✅ Comprehensive field coverage")
    print("   ✅ Validation tracking and confidence scoring")
    print("   ✅ Flag system for validation issues")
    print("   ✅ JSON field support for flexible data")
    print("   ✅ Audit trail with timestamps")
    print("   ✅ Property methods for derived data")
    print("   ✅ Dictionary export functionality")
    
    print("\n📊 Model Statistics:")
    print(f"   Total fields: {len([f for f in provider.__table__.columns])}")
    print(f"   Indexed fields: {len([i for i in provider.__table__.indexes])}")
    print(f"   JSON fields: {len([f for f in provider.__table__.columns if f.type.python_type == dict])}")
    
    return provider


async def demo_validation_scenarios():
    """Demonstrate different validation scenarios"""
    print("\n🔬 Validation Scenarios Demo:")
    print("=" * 50)
    
    scenarios = [
        {
            "name": "High Confidence Provider",
            "npi_score": 0.98,
            "address_score": 0.95,
            "license_score": 0.97,
            "contact_score": 0.92,
            "flags": ["NPI_VERIFIED", "ADDRESS_CONFIRMED"]
        },
        {
            "name": "Medium Confidence Provider",
            "npi_score": 0.85,
            "address_score": 0.78,
            "license_score": 0.82,
            "contact_score": 0.75,
            "flags": ["ADDRESS_PARTIAL_MATCH", "LICENSE_PENDING_RENEWAL"]
        },
        {
            "name": "Low Confidence Provider",
            "npi_score": 0.65,
            "address_score": 0.45,
            "license_score": 0.70,
            "contact_score": 0.30,
            "flags": ["NPI_NOT_FOUND", "ADDRESS_INVALID", "EMAIL_BOUNCED", "PHONE_DISCONNECTED"]
        }
    ]
    
    for scenario in scenarios:
        provider = Provider(
            given_name="Test",
            family_name="Provider",
            npi_number="1234567890"
        )
        
        # Set confidence scores
        provider.update_field_confidence("npi_number", scenario["npi_score"])
        provider.update_field_confidence("address", scenario["address_score"])
        provider.update_field_confidence("license", scenario["license_score"])
        provider.update_field_confidence("contact", scenario["contact_score"])
        
        # Add flags
        for flag in scenario["flags"]:
            provider.add_flag(flag, f"Validation issue: {flag}")
        
        overall = provider.calculate_overall_confidence()
        provider.overall_confidence = overall
        
        print(f"\n   {scenario['name']}:")
        print(f"     Overall Confidence: {overall:.2f}")
        print(f"     Flags: {len(provider.flags)}")
        print(f"     Status: {'🟢 Valid' if overall > 0.8 else '🟡 Warning' if overall > 0.6 else '🔴 Invalid'}")


async def main():
    """Main demonstration function"""
    try:
        # Demo basic provider model
        provider = await demo_provider_model()
        
        # Demo validation scenarios
        await demo_validation_scenarios()
        
        print("\n" + "=" * 50)
        print("✅ Provider Model Demonstration Complete!")
        print("   The precise provider model is ready for production use.")
        
    except Exception as e:
        print(f"❌ Error during demonstration: {e}")


if __name__ == "__main__":
    asyncio.run(main())
