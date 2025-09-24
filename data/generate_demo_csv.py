"""
Generate demo provider CSV with diverse data including error cases
"""

import csv
import random
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Sample data for generating realistic providers
FIRST_NAMES = [
    "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
    "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Christopher", "Karen", "Charles", "Nancy", "Daniel", "Lisa",
    "Matthew", "Betty", "Anthony", "Helen", "Mark", "Sandra", "Donald", "Donna",
    "Steven", "Carol", "Paul", "Ruth", "Andrew", "Sharon", "Joshua", "Michelle",
    "Dr. Sarah", "Dr. Michael", "Dr. Jennifer", "Dr. David", "Dr. Lisa", "Dr. Robert"
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

STATES = ["AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"]

CITIES_BY_STATE = {
    "CA": ["Los Angeles", "San Francisco", "San Diego", "San Jose", "Fresno", "Sacramento", "Oakland", "Long Beach"],
    "NY": ["New York", "Buffalo", "Rochester", "Yonkers", "Syracuse", "Albany", "Brooklyn", "Queens"],
    "TX": ["Houston", "San Antonio", "Dallas", "Austin", "Fort Worth", "El Paso", "Arlington", "Corpus Christi"],
    "FL": ["Jacksonville", "Miami", "Tampa", "Orlando", "St. Petersburg", "Hialeah", "Tallahassee", "Fort Lauderdale"],
    "IL": ["Chicago", "Aurora", "Rockford", "Joliet", "Naperville", "Springfield", "Peoria", "Elgin"],
    "PA": ["Philadelphia", "Pittsburgh", "Allentown", "Erie", "Reading", "Scranton", "Bethlehem", "Lancaster"],
    "OH": ["Columbus", "Cleveland", "Cincinnati", "Toledo", "Akron", "Dayton", "Parma", "Canton"],
    "GA": ["Atlanta", "Augusta", "Columbus", "Savannah", "Athens", "Sandy Springs", "Roswell", "Albany"],
    "NC": ["Charlotte", "Raleigh", "Greensboro", "Durham", "Winston-Salem", "Fayetteville", "Cary", "Wilmington"],
    "MI": ["Detroit", "Grand Rapids", "Warren", "Sterling Heights", "Lansing", "Ann Arbor", "Flint", "Dearborn"]
}

PRACTICE_TYPES = [
    "Family Medicine Clinic", "Internal Medicine Associates", "Pediatric Care Center",
    "Women's Health Clinic", "Orthopedic Specialists", "Cardiology Group",
    "Dermatology Associates", "Ophthalmology Center", "ENT Specialists",
    "Emergency Medicine Group", "Surgical Associates", "Mental Health Center",
    "Community Health Center", "Urgent Care Clinic", "Specialty Medical Group"
]

LICENSE_STATUSES = ["active", "expired", "suspended", "revoked", "inactive", "pending"]

# Error patterns for deliberate data issues
ERROR_PATTERNS = {
    "wrong_phone": [
        "555-000-0000", "123-456-7890", "000-000-0000", "999-999-9999",
        "555-123-456", "555-1234-567", "5551234567", "(555) 123-4567"
    ],
    "invalid_email": [
        "invalid-email", "test@", "@domain.com", "test@domain",
        "test..test@domain.com", "test@domain..com", "test@domain.com.",
        "test@domain@com", "test domain@domain.com"
    ],
    "expired_license": ["2019-12-31", "2020-06-15", "2021-03-01", "2018-11-30"],
    "fake_npi": ["0000000000", "1111111111", "9999999999", "123456789"],
    "moved_address": "OLD_ADDRESS"
}


def generate_valid_npi() -> str:
    """Generate a valid 10-digit NPI number with Luhn checksum"""
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
    
    first_nine = ''.join([str(random.randint(0, 9)) for _ in range(9)])
    check_digit = (10 - luhn_checksum(first_nine)) % 10
    return first_nine + str(check_digit)


def generate_phone() -> str:
    """Generate a realistic phone number"""
    area_code = random.randint(200, 999)
    exchange = random.randint(200, 999)
    number = random.randint(1000, 9999)
    return f"{area_code}-{exchange}-{number}"


def generate_address(state: str) -> Dict[str, str]:
    """Generate address components"""
    city = random.choice(CITIES_BY_STATE.get(state, ["Anytown"]))
    street_number = random.randint(1, 9999)
    street_names = [
        "Main St", "Oak Ave", "First St", "Second Ave", "Pine St", "Elm St", 
        "Park Ave", "Broadway", "Medical Center Dr", "Healthcare Blvd",
        "Professional Pkwy", "Medical Plaza", "Health Center Way"
    ]
    street = f"{street_number} {random.choice(street_names)}"
    zip_code = f"{random.randint(10000, 99999)}"
    
    return {
        "address_street": street,
        "address_city": city,
        "address_state": state,
        "address_zip": zip_code,
        "place_id": f"ChIJ{random.randint(10000000000000000000, 99999999999999999999)}"
    }


def generate_provider_with_errors(provider_id: int) -> Dict[str, Any]:
    """Generate a provider record with deliberate errors based on ID pattern"""
    
    # Determine error type based on provider ID
    error_type = provider_id % 10
    
    # Base provider data
    given_name = random.choice(FIRST_NAMES)
    family_name = random.choice(LAST_NAMES)
    state = random.choice(STATES)
    specialty_code = random.choice(list(MEDICAL_SPECIALTIES.keys()))
    
    provider_data = {
        "provider_id": str(uuid.uuid4()),
        "given_name": given_name,
        "family_name": family_name,
        "npi_number": generate_valid_npi(),
        "primary_taxonomy": specialty_code,
        "practice_name": f"{family_name} {MEDICAL_SPECIALTIES[specialty_code]}",
        "phone_primary": generate_phone(),
        "phone_alt": generate_phone() if random.random() < 0.3 else "",
        "email": f"{given_name.lower().replace(' ', '')}.{family_name.lower()}@{random.choice(['gmail.com', 'yahoo.com', 'outlook.com'])}",
        "license_number": f"{random.choice(['A', 'B', 'C'])}{random.randint(100000, 999999)}",
        "license_state": state,
        "license_status": "active",
        "last_validated_at": (datetime.now() - timedelta(days=random.randint(1, 365))).strftime("%Y-%m-%d %H:%M:%S"),
        "validated_by": f"validation_agent_{random.randint(1, 10):03d}",
        "overall_confidence": round(random.uniform(0.7, 1.0), 2),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Add address information
    address_data = generate_address(state)
    provider_data.update(address_data)
    
    # Introduce deliberate errors based on pattern
    if error_type == 0:  # Perfect provider (10%)
        pass  # No errors
    
    elif error_type == 1:  # Wrong phone number (10%)
        provider_data["phone_primary"] = random.choice(ERROR_PATTERNS["wrong_phone"])
        provider_data["overall_confidence"] = round(random.uniform(0.4, 0.7), 2)
    
    elif error_type == 2:  # Invalid email (10%)
        provider_data["email"] = random.choice(ERROR_PATTERNS["invalid_email"])
        provider_data["overall_confidence"] = round(random.uniform(0.5, 0.8), 2)
    
    elif error_type == 3:  # Expired license (10%)
        provider_data["license_status"] = "expired"
        provider_data["overall_confidence"] = round(random.uniform(0.3, 0.6), 2)
    
    elif error_type == 4:  # Fake NPI (10%)
        provider_data["npi_number"] = random.choice(ERROR_PATTERNS["fake_npi"])
        provider_data["overall_confidence"] = round(random.uniform(0.2, 0.5), 2)
    
    elif error_type == 5:  # Moved address (10%)
        old_address = generate_address(state)
        provider_data.update(old_address)
        provider_data["address_street"] = f"{old_address['address_street']} (MOVED)"
        provider_data["overall_confidence"] = round(random.uniform(0.4, 0.7), 2)
    
    elif error_type == 6:  # Missing license (10%)
        provider_data["license_number"] = ""
        provider_data["license_status"] = ""
        provider_data["overall_confidence"] = round(random.uniform(0.3, 0.6), 2)
    
    elif error_type == 7:  # Duplicate provider (10%)
        # Create a duplicate by copying another provider's data
        if provider_id > 10:
            # Copy data from a previous provider
            provider_data["npi_number"] = f"DUPLICATE_{provider_id}"
            provider_data["overall_confidence"] = round(random.uniform(0.1, 0.4), 2)
    
    elif error_type == 8:  # Suspended license (10%)
        provider_data["license_status"] = "suspended"
        provider_data["overall_confidence"] = round(random.uniform(0.2, 0.5), 2)
    
    elif error_type == 9:  # Mixed errors (10%)
        # Combine multiple error types
        if random.random() < 0.5:
            provider_data["phone_primary"] = random.choice(ERROR_PATTERNS["wrong_phone"])
        if random.random() < 0.5:
            provider_data["email"] = random.choice(ERROR_PATTERNS["invalid_email"])
        if random.random() < 0.5:
            provider_data["license_status"] = random.choice(["expired", "suspended"])
        provider_data["overall_confidence"] = round(random.uniform(0.2, 0.6), 2)
    
    return provider_data


def generate_csv_data(num_providers: int = 200) -> List[Dict[str, Any]]:
    """Generate CSV data with diverse provider records"""
    print(f"Generating {num_providers} provider records with diverse error patterns...")
    
    providers = []
    for i in range(num_providers):
        if (i + 1) % 50 == 0:
            print(f"Generated {i + 1}/{num_providers} providers...")
        
        provider = generate_provider_with_errors(i)
        providers.append(provider)
    
    return providers


def save_to_csv(providers: List[Dict[str, Any]], filename: str = "demo_providers.csv"):
    """Save providers to CSV file"""
    if not providers:
        print("No providers to save")
        return
    
    # Define CSV headers in the desired order
    headers = [
        "provider_id", "given_name", "family_name", "npi_number", "primary_taxonomy",
        "practice_name", "address_street", "address_city", "address_state", "address_zip",
        "place_id", "phone_primary", "phone_alt", "email", "license_number",
        "license_state", "license_status", "last_validated_at", "validated_by",
        "overall_confidence", "created_at", "updated_at"
    ]
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        
        for provider in providers:
            # Ensure all fields are present
            row = {header: provider.get(header, "") for header in headers}
            writer.writerow(row)
    
    print(f"Saved {len(providers)} providers to {filename}")


def main():
    """Main function to generate and save CSV data"""
    # Generate provider data
    providers = generate_csv_data(200)
    
    # Save to CSV
    save_to_csv(providers, "demo_providers.csv")
    
    # Print summary statistics
    print(f"\n📊 Generated Data Summary:")
    print(f"   Total providers: {len(providers)}")
    
    # Count error types
    error_counts = {
        "Perfect providers": 0,
        "Wrong phone": 0,
        "Invalid email": 0,
        "Expired license": 0,
        "Fake NPI": 0,
        "Moved address": 0,
        "Missing license": 0,
        "Duplicate providers": 0,
        "Suspended license": 0,
        "Mixed errors": 0
    }
    
    for i, provider in enumerate(providers):
        error_type = i % 10
        if error_type == 0:
            error_counts["Perfect providers"] += 1
        elif error_type == 1:
            error_counts["Wrong phone"] += 1
        elif error_type == 2:
            error_counts["Invalid email"] += 1
        elif error_type == 3:
            error_counts["Expired license"] += 1
        elif error_type == 4:
            error_counts["Fake NPI"] += 1
        elif error_type == 5:
            error_counts["Moved address"] += 1
        elif error_type == 6:
            error_counts["Missing license"] += 1
        elif error_type == 7:
            error_counts["Duplicate providers"] += 1
        elif error_type == 8:
            error_counts["Suspended license"] += 1
        elif error_type == 9:
            error_counts["Mixed errors"] += 1
    
    print(f"\n🔍 Error Pattern Distribution:")
    for error_type, count in error_counts.items():
        percentage = (count / len(providers)) * 100
        print(f"   {error_type}: {count} ({percentage:.1f}%)")
    
    print(f"\n✅ CSV file generated successfully!")
    print(f"   File: demo_providers.csv")
    print(f"   Location: data/demo_providers.csv")


if __name__ == "__main__":
    main()
