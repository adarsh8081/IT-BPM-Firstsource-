"""
Generate precise provider data using the new provider model
"""

import json
import random
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any
import asyncio
from sqlalchemy.orm import Session

from models.provider import Provider
from database import get_db


# Sample data for generating realistic providers
FIRST_NAMES = [
    "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
    "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Christopher", "Karen", "Charles", "Nancy", "Daniel", "Lisa",
    "Matthew", "Betty", "Anthony", "Helen", "Mark", "Sandra", "Donald", "Donna",
    "Steven", "Carol", "Paul", "Ruth", "Andrew", "Sharon", "Joshua", "Michelle"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
    "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores"
]

MEDICAL_SPECIALTIES = {
    "207Q00000X": "Family Medicine",
    "207R00000X": "Internal Medicine",
    "207K00000X": "Allergy & Immunology",
    "207N00000X": "Dermatology",
    "207P00000X": "Emergency Medicine",
    "207T00000X": "Orthopedic Surgery",
    "207U00000X": "Urology",
    "207V00000X": "Obstetrics & Gynecology",
    "207W00000X": "Ophthalmology",
    "207X00000X": "Orthopedic Surgery",
    "207Y00000X": "Otolaryngology",
    "207Z00000X": "Pathology",
    "208000000X": "Pediatrics",
    "208100000X": "Physical Medicine & Rehabilitation",
    "208200000X": "Plastic Surgery",
    "208300000X": "Psychiatry",
    "208400000X": "Radiology",
    "208500000X": "Surgery",
    "208600000X": "Thoracic Surgery",
    "208800000X": "Urology"
}

STATES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"
]

CITIES_BY_STATE = {
    "CA": ["Los Angeles", "San Francisco", "San Diego", "San Jose", "Fresno", "Sacramento"],
    "NY": ["New York", "Buffalo", "Rochester", "Yonkers", "Syracuse", "Albany"],
    "TX": ["Houston", "San Antonio", "Dallas", "Austin", "Fort Worth", "El Paso"],
    "FL": ["Jacksonville", "Miami", "Tampa", "Orlando", "St. Petersburg", "Hialeah"],
    "IL": ["Chicago", "Aurora", "Rockford", "Joliet", "Naperville", "Springfield"],
    "PA": ["Philadelphia", "Pittsburgh", "Allentown", "Erie", "Reading", "Scranton"],
    "OH": ["Columbus", "Cleveland", "Cincinnati", "Toledo", "Akron", "Dayton"],
    "GA": ["Atlanta", "Augusta", "Columbus", "Savannah", "Athens", "Sandy Springs"],
    "NC": ["Charlotte", "Raleigh", "Greensboro", "Durham", "Winston-Salem", "Fayetteville"],
    "MI": ["Detroit", "Grand Rapids", "Warren", "Sterling Heights", "Lansing", "Ann Arbor"]
}

PRACTICE_TYPES = [
    "Family Medicine Clinic", "Internal Medicine Associates", "Pediatric Care Center",
    "Women's Health Clinic", "Orthopedic Specialists", "Cardiology Group",
    "Dermatology Associates", "Ophthalmology Center", "ENT Specialists",
    "Emergency Medicine Group", "Surgical Associates", "Mental Health Center"
]

LICENSE_STATUSES = ["active", "expired", "suspended", "revoked", "inactive", "pending"]


def generate_npi() -> str:
    """Generate a valid 10-digit NPI number"""
    # Generate first 9 digits
    first_nine = ''.join([str(random.randint(0, 9)) for _ in range(9)])
    
    # Calculate check digit using Luhn algorithm
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
    
    check_digit = (10 - luhn_checksum(first_nine)) % 10
    return first_nine + str(check_digit)


def generate_phone() -> str:
    """Generate a phone number"""
    area_code = random.randint(200, 999)
    exchange = random.randint(200, 999)
    number = random.randint(1000, 9999)
    return f"{area_code}-{exchange}-{number}"


def generate_address(state: str) -> Dict[str, str]:
    """Generate address components for a given state"""
    city = random.choice(CITIES_BY_STATE.get(state, ["Anytown"]))
    street_number = random.randint(1, 9999)
    street_names = ["Main St", "Oak Ave", "First St", "Second Ave", "Pine St", "Elm St", "Park Ave", "Broadway"]
    street = f"{street_number} {random.choice(street_names)}"
    zip_code = f"{random.randint(10000, 99999)}"
    
    return {
        "address_street": street,
        "address_city": city,
        "address_state": state,
        "address_zip": zip_code,
        "place_id": f"ChIJ{random.randint(10000000000000000000, 99999999999999999999)}"
    }


def generate_affiliations() -> List[Dict[str, str]]:
    """Generate provider affiliations"""
    hospitals = ["General Hospital", "Regional Medical Center", "Community Hospital", "University Medical Center"]
    medical_groups = ["Medical Associates", "Healthcare Partners", "Physician Group", "Medical Services"]
    
    affiliations = []
    if random.random() < 0.8:  # 80% chance of hospital affiliation
        affiliations.append({
            "organization": random.choice(hospitals),
            "role": random.choice(["Attending Physician", "Staff Physician", "Consultant"])
        })
    
    if random.random() < 0.6:  # 60% chance of medical group affiliation
        affiliations.append({
            "organization": random.choice(medical_groups),
            "role": random.choice(["Partner", "Associate", "Independent Contractor"])
        })
    
    return affiliations


def generate_services_offered() -> Dict[str, bool]:
    """Generate services offered based on specialty"""
    base_services = {
        "primary_care": True,
        "preventive_care": True,
        "diagnostic_services": True,
        "consultation": True
    }
    
    specialty_services = {
        "pediatrics": random.choice([True, False]),
        "internal_medicine": random.choice([True, False]),
        "surgery": random.choice([True, False]),
        "emergency_care": random.choice([True, False]),
        "mental_health": random.choice([True, False])
    }
    
    base_services.update(specialty_services)
    return base_services


def generate_provider() -> Dict[str, Any]:
    """Generate a single provider record"""
    given_name = random.choice(FIRST_NAMES)
    family_name = random.choice(LAST_NAMES)
    state = random.choice(STATES)
    specialty_code = random.choice(list(MEDICAL_SPECIALTIES.keys()))
    
    provider_data = {
        "given_name": given_name,
        "family_name": family_name,
        "npi_number": generate_npi(),
        "primary_taxonomy": specialty_code,
        "practice_name": f"{family_name} {MEDICAL_SPECIALTIES[specialty_code]}",
        "phone_primary": generate_phone(),
        "phone_alt": generate_phone() if random.random() < 0.3 else None,
        "email": f"{given_name.lower()}.{family_name.lower()}@{random.choice(['gmail.com', 'yahoo.com', 'outlook.com'])}",
        "license_number": f"{random.choice(['A', 'B', 'C'])}{random.randint(100000, 999999)}",
        "license_state": state,
        "license_status": random.choice(LICENSE_STATUSES),
        "affiliations": generate_affiliations(),
        "services_offered": generate_services_offered(),
        "last_validated_at": datetime.utcnow() - timedelta(days=random.randint(1, 365)),
        "validated_by": f"validation_agent_{random.randint(1, 10):03d}",
        "overall_confidence": round(random.uniform(0.6, 1.0), 2),
        "field_confidence": {
            "npi_number": {"score": round(random.uniform(0.9, 1.0), 2), "updated_at": datetime.utcnow().isoformat()},
            "address": {"score": round(random.uniform(0.7, 1.0), 2), "updated_at": datetime.utcnow().isoformat()},
            "license": {"score": round(random.uniform(0.8, 1.0), 2), "updated_at": datetime.utcnow().isoformat()},
            "contact": {"score": round(random.uniform(0.6, 1.0), 2), "updated_at": datetime.utcnow().isoformat()}
        },
        "flags": []
    }
    
    # Add address information
    address_data = generate_address(state)
    provider_data.update(address_data)
    
    # Add some validation flags occasionally
    if random.random() < 0.1:  # 10% chance of having flags
        flags = [
            {"code": "ADDRESS_MISMATCH", "reason": "Address doesn't match NPI registry", "timestamp": datetime.utcnow().isoformat()},
            {"code": "LICENSE_EXPIRED", "reason": "License has expired", "timestamp": datetime.utcnow().isoformat()},
            {"code": "EMAIL_INVALID", "reason": "Email address format is invalid", "timestamp": datetime.utcnow().isoformat()},
            {"code": "PHONE_UNREACHABLE", "reason": "Phone number is not reachable", "timestamp": datetime.utcnow().isoformat()}
        ]
        provider_data["flags"] = random.sample(flags, random.randint(1, 2))
    
    return provider_data


async def generate_providers(count: int = 200) -> List[Dict[str, Any]]:
    """Generate multiple provider records"""
    print(f"Generating {count} provider records...")
    
    providers = []
    for i in range(count):
        if (i + 1) % 50 == 0:
            print(f"Generated {i + 1}/{count} providers...")
        providers.append(generate_provider())
    
    return providers


def save_to_json(providers: List[Dict[str, Any]], filename: str = "precise_providers.json"):
    """Save providers to JSON file"""
    # Convert datetime objects to strings for JSON serialization
    def convert_datetime(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return obj
    
    # Convert all datetime objects in the data
    json_data = json.loads(json.dumps(providers, default=convert_datetime))
    
    with open(filename, 'w') as f:
        json.dump(json_data, f, indent=2, default=str)
    
    print(f"Saved {len(providers)} providers to {filename}")


async def insert_to_database(providers: List[Dict[str, Any]]):
    """Insert providers into the database"""
    print("Inserting providers into database...")
    
    db = next(get_db())
    try:
        for i, provider_data in enumerate(providers):
            if (i + 1) % 50 == 0:
                print(f"Inserted {i + 1}/{len(providers)} providers...")
            
            provider = Provider(**provider_data)
            db.add(provider)
        
        db.commit()
        print(f"Successfully inserted {len(providers)} providers into database")
    except Exception as e:
        db.rollback()
        print(f"Error inserting providers: {e}")
        raise
    finally:
        db.close()


async def main():
    """Main function to generate and save provider data"""
    count = 200
    providers = await generate_providers(count)
    
    # Save to JSON file
    save_to_json(providers)
    
    # Optionally insert into database
    # await insert_to_database(providers)
    
    print(f"\nGenerated {len(providers)} precise provider records")
    print("Sample provider:")
    print(json.dumps(providers[0], indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
