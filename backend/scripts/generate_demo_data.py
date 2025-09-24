"""
Script to generate demo data for the Provider Validation system
"""

import asyncio
import random
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
import uuid

from ..database import AsyncSessionLocal, init_db
from ..models import Provider, ProviderStatus
from ..schemas import ProviderCreate

# Sample data
FIRST_NAMES = [
    'Sarah', 'Michael', 'Emily', 'David', 'Lisa', 'John', 'Maria', 'Robert',
    'Jennifer', 'James', 'Patricia', 'William', 'Linda', 'Richard', 'Barbara',
    'Joseph', 'Susan', 'Thomas', 'Jessica', 'Christopher', 'Sarah', 'Charles',
    'Karen', 'Daniel', 'Nancy', 'Matthew', 'Betty', 'Anthony', 'Helen',
    'Mark', 'Sandra', 'Donald', 'Donna', 'Steven', 'Carol', 'Paul', 'Ruth',
    'Andrew', 'Sharon', 'Joshua', 'Michelle', 'Kenneth', 'Laura', 'Kevin',
    'Sarah', 'Brian', 'Kimberly', 'George', 'Deborah', 'Edward', 'Dorothy'
]

LAST_NAMES = [
    'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis',
    'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez', 'Wilson',
    'Anderson', 'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin', 'Lee',
    'Perez', 'Thompson', 'White', 'Harris', 'Sanchez', 'Clark', 'Ramirez',
    'Lewis', 'Robinson', 'Walker', 'Young', 'Allen', 'King', 'Wright',
    'Scott', 'Torres', 'Nguyen', 'Hill', 'Flores', 'Green', 'Adams',
    'Nelson', 'Baker', 'Hall', 'Rivera', 'Campbell', 'Mitchell', 'Carter',
    'Roberts', 'Gomez', 'Phillips', 'Evans', 'Turner', 'Diaz', 'Parker'
]

SPECIALTIES = [
    'Internal Medicine', 'Family Medicine', 'Cardiology', 'Pediatrics',
    'Surgery', 'Radiology', 'Neurology', 'Oncology', 'Dermatology',
    'Orthopedic Surgery', 'Emergency Medicine', 'Anesthesiology',
    'Psychiatry', 'Ophthalmology', 'Obstetrics and Gynecology',
    'Urology', 'Gastroenterology', 'Endocrinology', 'Pulmonology',
    'Rheumatology', 'Nephrology', 'Hematology', 'Infectious Disease',
    'Critical Care Medicine', 'Pain Medicine', 'Sports Medicine',
    'Geriatric Medicine', 'Occupational Medicine', 'Preventive Medicine'
]

ORGANIZATIONS = [
    'City General Hospital', 'Regional Medical Center', 'University Hospital',
    'Community Health Clinic', 'Metropolitan Medical Group', 'Valley Health System',
    'Sunshine Medical Center', 'Riverside Hospital', 'Mountain View Medical',
    'Coastal Healthcare', 'Desert Medical Center', 'Forest Hills Hospital',
    'Prairie Medical Group', 'Lakeview Health System', 'Hillside Medical Center',
    'Parkview Hospital', 'Sunrise Medical Group', 'Sunset Health Center',
    'Northside Medical', 'Southside Healthcare'
]

CITIES = [
    'New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix', 'Philadelphia',
    'San Antonio', 'San Diego', 'Dallas', 'San Jose', 'Austin', 'Jacksonville',
    'Fort Worth', 'Columbus', 'Charlotte', 'San Francisco', 'Indianapolis',
    'Seattle', 'Denver', 'Washington', 'Boston', 'El Paso', 'Nashville',
    'Detroit', 'Oklahoma City', 'Portland', 'Las Vegas', 'Memphis', 'Louisville'
]

STATES = [
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
    'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
    'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
    'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
    'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY'
]

async def generate_provider_data(count: int = 200) -> List[ProviderCreate]:
    """Generate synthetic provider data"""
    providers = []
    
    for i in range(count):
        # Generate NPI (10 digits)
        npi = ''.join([str(random.randint(0, 9)) for _ in range(10)])
        
        # Generate name
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        middle_name = random.choice(FIRST_NAMES) if random.random() < 0.3 else None
        suffix = random.choice(['Jr.', 'Sr.', 'II', 'III', 'MD', 'DO']) if random.random() < 0.1 else None
        
        # Generate specialty and organization
        specialty = random.choice(SPECIALTIES)
        organization = random.choice(ORGANIZATIONS)
        
        # Generate organization NPI (10 digits)
        org_npi = ''.join([str(random.randint(0, 9)) for _ in range(10)]) if random.random() < 0.7 else None
        
        # Generate contact information
        email = f"{first_name.lower()}.{last_name.lower()}@{organization.lower().replace(' ', '')}.com"
        phone = f"({random.randint(200, 999)}) {random.randint(200, 999)}-{random.randint(1000, 9999)}"
        
        # Generate address
        city = random.choice(CITIES)
        state = random.choice(STATES)
        zip_code = f"{random.randint(10000, 99999)}"
        
        # Generate address line 1
        street_numbers = [str(random.randint(100, 9999))]
        street_names = [
            'Main St', 'Oak Ave', 'Pine St', 'Elm St', 'Cedar Ave', 'Maple St',
            'Washington Ave', 'Lincoln St', 'Jefferson Ave', 'Madison St',
            'Park Ave', 'Broadway', 'First St', 'Second Ave', 'Third St'
        ]
        address_line1 = f"{random.choice(street_numbers)} {random.choice(street_names)}"
        address_line2 = f"Suite {random.randint(100, 999)}" if random.random() < 0.4 else None
        
        # Generate license information
        license_state = state
        license_number = f"{state}{random.randint(100000, 999999)}"
        
        # Generate license expiry (some expired, some current)
        if random.random() < 0.1:  # 10% expired
            license_expiry = datetime.now() - timedelta(days=random.randint(1, 365))
        else:  # 90% current or future
            license_expiry = datetime.now() + timedelta(days=random.randint(1, 1095))
        
        provider_data = ProviderCreate(
            npi=npi,
            first_name=first_name,
            last_name=last_name,
            middle_name=middle_name,
            suffix=suffix,
            specialty=specialty,
            organization=organization,
            organization_npi=org_npi,
            email=email,
            phone=phone,
            address_line1=address_line1,
            address_line2=address_line2,
            city=city,
            state=state,
            zip_code=zip_code,
            country='US',
            license_number=license_number,
            license_state=license_state,
            license_expiry=license_expiry
        )
        
        providers.append(provider_data)
    
    return providers

async def save_providers_to_database(providers: List[ProviderCreate]):
    """Save providers to database"""
    async with AsyncSessionLocal() as db:
        try:
            saved_count = 0
            failed_count = 0
            
            for provider_data in providers:
                try:
                    # Create provider instance
                    provider = Provider(**provider_data.dict())
                    
                    # Set random status and validation score
                    status_weights = [0.7, 0.15, 0.1, 0.05]  # valid, pending, invalid, warning
                    provider.status = random.choices(
                        [ProviderStatus.VALID, ProviderStatus.PENDING, 
                         ProviderStatus.INVALID, ProviderStatus.WARNING],
                        weights=status_weights
                    )[0]
                    
                    provider.validation_score = random.uniform(0, 100)
                    
                    # Set last validated date (some never validated)
                    if provider.status != ProviderStatus.PENDING and random.random() < 0.8:
                        provider.last_validated = datetime.now() - timedelta(
                            days=random.randint(1, 365)
                        )
                    
                    db.add(provider)
                    saved_count += 1
                    
                except Exception as e:
                    print(f"Failed to save provider {provider_data.npi}: {e}")
                    failed_count += 1
            
            await db.commit()
            print(f"Successfully saved {saved_count} providers, {failed_count} failed")
            
        except Exception as e:
            await db.rollback()
            print(f"Database error: {e}")
            raise

async def generate_demo_data():
    """Generate and save demo data"""
    print("Generating demo data...")
    
    # Initialize database
    await init_db()
    
    # Generate providers
    print("Generating 200 provider profiles...")
    providers = await generate_provider_data(200)
    
    # Save to database
    print("Saving providers to database...")
    await save_providers_to_database(providers)
    
    # Generate summary
    print("\nDemo data generation complete!")
    print(f"Generated {len(providers)} provider profiles")
    print("Provider data includes:")
    print("- Personal information (names, contact details)")
    print("- Professional information (specialty, organization)")
    print("- Address information (with realistic addresses)")
    print("- License information (with realistic expiry dates)")
    print("- Validation status and scores")
    
    # Save to JSON file for reference
    providers_dict = [provider.dict() for provider in providers]
    with open('demo_providers.json', 'w') as f:
        json.dump(providers_dict, f, indent=2, default=str)
    
    print("Provider data also saved to demo_providers.json")

if __name__ == "__main__":
    asyncio.run(generate_demo_data())
