# Precise Provider Data Model

## Overview

The precise provider data model is a comprehensive PostgreSQL schema designed for healthcare provider data validation and directory management. It includes all essential fields for provider identification, contact information, professional credentials, and validation tracking.

## Database Schema

### Provider Table

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `provider_id` | UUID | Unique provider identifier | Primary Key, Auto-generated |
| `given_name` | VARCHAR(100) | Provider's given (first) name | NOT NULL |
| `family_name` | VARCHAR(100) | Provider's family (last) name | NOT NULL |
| `npi_number` | VARCHAR(10) | 10-digit National Provider Identifier | UNIQUE, NOT NULL, CHECK format |
| `primary_taxonomy` | VARCHAR(200) | Primary medical specialty/taxonomy code | NULLABLE |
| `practice_name` | VARCHAR(200) | Name of practice or organization | NULLABLE |
| `address_street` | VARCHAR(255) | Street address line | NULLABLE |
| `address_city` | VARCHAR(100) | City name | NULLABLE |
| `address_state` | VARCHAR(2) | State abbreviation (2 characters) | CHECK uppercase |
| `address_zip` | VARCHAR(10) | ZIP/postal code | NULLABLE |
| `place_id` | VARCHAR(255) | Google Places API place ID | NULLABLE |
| `phone_primary` | VARCHAR(20) | Primary phone number | NULLABLE |
| `phone_alt` | VARCHAR(20) | Alternative phone number | NULLABLE |
| `email` | VARCHAR(255) | Primary email address | NULLABLE |
| `license_number` | VARCHAR(50) | Medical license number | NULLABLE |
| `license_state` | VARCHAR(2) | State where license is issued | CHECK uppercase |
| `license_status` | VARCHAR(20) | License status | NULLABLE |
| `affiliations` | JSON | Array of organization affiliations | NULLABLE |
| `services_offered` | JSON | Object of services offered | NULLABLE |
| `last_validated_at` | TIMESTAMP | Last validation timestamp | NULLABLE |
| `validated_by` | VARCHAR(100) | Agent/system that performed validation | NULLABLE |
| `overall_confidence` | FLOAT | Overall confidence score (0.0-1.0) | CHECK range |
| `field_confidence` | JSON | Per-field confidence scores | NULLABLE |
| `flags` | JSON | Validation flags and reason codes | NULLABLE |
| `created_at` | TIMESTAMP | Record creation timestamp | NOT NULL |
| `updated_at` | TIMESTAMP | Last update timestamp | NOT NULL |

## Indexes

The following indexes are created for optimal query performance:

- `idx_provider_npi` - Unique index on NPI number
- `idx_provider_name` - Composite index on family_name, given_name
- `idx_provider_state` - Index on address_state
- `idx_provider_taxonomy` - Index on primary_taxonomy
- `idx_provider_license` - Composite index on license_number, license_state
- `idx_provider_validated` - Index on last_validated_at
- `idx_provider_confidence` - Index on overall_confidence

## Constraints

### Check Constraints

1. **NPI Format**: `npi_number ~ '^[0-9]{10}$'`
2. **State Format**: `address_state IS NULL OR address_state ~ '^[A-Z]{2}$'`
3. **Confidence Range**: `overall_confidence >= 0.0 AND overall_confidence <= 1.0`

## JSON Field Structures

### Affiliations

```json
[
  {
    "organization": "General Hospital",
    "role": "Attending Physician",
    "start_date": "2020-01-01",
    "end_date": null
  }
]
```

### Services Offered

```json
{
  "primary_care": true,
  "preventive_care": true,
  "pediatrics": false,
  "internal_medicine": true,
  "surgery": false,
  "mental_health": false
}
```

### Field Confidence

```json
{
  "npi_number": {
    "score": 0.95,
    "updated_at": "2024-01-15T10:30:00Z"
  },
  "address": {
    "score": 0.88,
    "updated_at": "2024-01-15T10:30:00Z"
  }
}
```

### Validation Flags

```json
[
  {
    "code": "ADDRESS_MISMATCH",
    "reason": "Address doesn't match NPI registry",
    "timestamp": "2024-01-15T10:30:00Z"
  }
]
```

## ORM Model Features

### Properties

- `full_name` - Combines given_name and family_name
- `full_address` - Combines all address components

### Methods

- `add_flag(code, reason)` - Add validation flag
- `update_field_confidence(field, score)` - Update field confidence
- `calculate_overall_confidence()` - Calculate average confidence
- `to_dict()` - Export to dictionary format

## Validation Tracking

### Confidence Scoring

The model supports granular confidence scoring:

- **Field-level**: Individual confidence scores for each field
- **Overall**: Calculated average of all field scores
- **Range**: 0.0 (no confidence) to 1.0 (full confidence)

### Flag System

Validation flags capture issues and warnings:

- **Code**: Machine-readable identifier
- **Reason**: Human-readable description
- **Timestamp**: When the flag was added

Common flag codes:
- `NPI_NOT_FOUND` - NPI not found in registry
- `ADDRESS_MISMATCH` - Address doesn't match registry
- `LICENSE_EXPIRED` - License has expired
- `EMAIL_INVALID` - Email format is invalid
- `PHONE_UNREACHABLE` - Phone number not reachable

## Usage Examples

### Creating a Provider

```python
from models.provider import Provider

provider = Provider(
    given_name="Dr. Sarah",
    family_name="Johnson",
    npi_number="1234567890",
    primary_taxonomy="207Q00000X",
    practice_name="Johnson Family Medicine",
    address_street="123 Medical Center Dr",
    address_city="San Francisco",
    address_state="CA",
    address_zip="94102",
    phone_primary="415-555-0123",
    email="sarah.johnson@example.com",
    license_number="A123456",
    license_state="CA",
    license_status="active"
)
```

### Adding Validation Data

```python
# Add confidence scores
provider.update_field_confidence("npi_number", 0.95)
provider.update_field_confidence("address", 0.88)
provider.update_field_confidence("license", 0.92)

# Calculate overall confidence
overall_confidence = provider.calculate_overall_confidence()
provider.overall_confidence = overall_confidence

# Add validation flags
provider.add_flag("ADDRESS_VERIFIED", "Address verified via Google Places API")
provider.add_flag("LICENSE_ACTIVE", "License status confirmed with state board")
```

### Querying Providers

```python
from sqlalchemy.orm import Session

# Find by NPI
provider = db.query(Provider).filter(Provider.npi_number == "1234567890").first()

# Find by name
providers = db.query(Provider).filter(
    Provider.family_name == "Johnson",
    Provider.given_name == "Sarah"
).all()

# Find by state and specialty
providers = db.query(Provider).filter(
    Provider.address_state == "CA",
    Provider.primary_taxonomy == "207Q00000X"
).all()

# Find by confidence score
high_confidence_providers = db.query(Provider).filter(
    Provider.overall_confidence >= 0.9
).all()
```

## Migration

The provider model is created through database migrations:

```bash
# Run migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "Add provider model"
```

## Testing

Comprehensive tests are available in `tests/test_provider_model.py`:

```bash
# Run provider model tests
pytest tests/test_provider_model.py -v

# Run with coverage
pytest tests/test_provider_model.py --cov=models.provider
```

## Performance Considerations

1. **Indexes**: All frequently queried fields are indexed
2. **JSON Fields**: Use JSONB in production for better performance
3. **Batch Operations**: Use bulk insert/update for large datasets
4. **Connection Pooling**: Configure appropriate connection pool size

## Security Considerations

1. **PII Protection**: Sensitive data should be encrypted at rest
2. **Access Control**: Implement row-level security for multi-tenant scenarios
3. **Audit Trail**: All changes are tracked with timestamps
4. **Data Validation**: Input validation at both API and database levels

## Future Enhancements

1. **Soft Deletes**: Add deleted_at field for soft deletion
2. **Versioning**: Track field-level changes over time
3. **Search**: Full-text search capabilities
4. **Geospatial**: PostGIS integration for location-based queries
5. **Caching**: Redis integration for frequently accessed data
