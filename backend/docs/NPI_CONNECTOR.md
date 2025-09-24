# NPI Registry Connector

## Overview

The NPI Registry Connector provides functionality to fetch provider data from the official NPI Registry API (https://npiregistry.cms.hhs.gov/api/) and normalize it to match our provider schema with per-field trust scores.

## Features

- **NPI Number Lookup**: Search for providers by exact NPI number
- **Name-based Search**: Search for providers by name and optional state
- **Data Normalization**: Converts NPI Registry data to our provider schema
- **Trust Scoring**: Provides confidence scores (0-1) for each field
- **Rate Limiting**: Built-in rate limiting to respect API limits
- **Error Handling**: Comprehensive error handling and validation
- **NPI Validation**: Validates NPI format using Luhn algorithm

## Installation

```bash
pip install httpx  # For async HTTP requests
```

## Usage

### Basic NPI Lookup

```python
import asyncio
from connectors.npi import NPIConnector

async def lookup_provider():
    connector = NPIConnector()
    
    # Search by NPI number
    result = await connector.search_provider_by_npi("1234567890")
    
    if result.success:
        print(f"Provider: {result.data['given_name']} {result.data['family_name']}")
        print(f"NPI: {result.data['npi_number']}")
        print(f"Practice: {result.data['practice_name']}")
        print(f"Specialty: {result.data['primary_taxonomy']}")
        print(f"Address: {result.data['address_street']}, {result.data['address_city']}, {result.data['address_state']}")
        
        # Check trust scores
        for field, trust in result.trust_scores.items():
            print(f"{field}: {trust.score:.2f} - {trust.confidence}")
    else:
        print(f"Error: {result.error}")

# Run the example
asyncio.run(lookup_provider())
```

### Name-based Search

```python
async def search_by_name():
    connector = NPIConnector()
    
    # Search by name and state
    result = await connector.search_provider_by_name(
        first_name="John",
        last_name="Smith",
        state="CA"
    )
    
    if result.success:
        print(f"Found {len(result.data)} providers")
        
        for i, provider in enumerate(result.data):
            print(f"Provider {i+1}: {provider['given_name']} {provider['family_name']}")
            print(f"  NPI: {provider['npi_number']}")
            print(f"  Practice: {provider['practice_name']}")
            print(f"  Location: {provider['address_city']}, {provider['address_state']}")
    else:
        print(f"Error: {result.error}")

asyncio.run(search_by_name())
```

## API Reference

### NPIConnector Class

#### Constructor

```python
NPIConnector(api_key: Optional[str] = None)
```

- `api_key`: Optional API key (NPI Registry doesn't require authentication)

#### Methods

##### `search_provider_by_npi(npi_number: str) -> ConnectorResponse`

Search for a provider by NPI number.

**Parameters:**
- `npi_number` (str): 10-digit NPI number

**Returns:**
- `ConnectorResponse`: Contains success status, normalized data, and trust scores

**Example:**
```python
result = await connector.search_provider_by_npi("1234567890")
```

##### `search_provider_by_name(first_name: str, last_name: str, state: Optional[str] = None) -> ConnectorResponse`

Search for providers by name.

**Parameters:**
- `first_name` (str): Provider's first name
- `last_name` (str): Provider's last name
- `state` (str, optional): 2-letter state abbreviation

**Returns:**
- `ConnectorResponse`: Contains success status, list of providers, and trust scores

**Example:**
```python
result = await connector.search_provider_by_name("John", "Smith", "CA")
```

## Response Format

### ConnectorResponse

```python
@dataclass
class ConnectorResponse:
    success: bool
    data: Optional[Dict[str, Any]]
    trust_scores: Optional[Dict[str, TrustScore]]
    source: str
    timestamp: datetime
    error: Optional[str] = None
```

### Normalized Provider Data

```python
{
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
}
```

### Trust Scores

```python
{
    "npi_number": TrustScore(score=0.98, reason="Official NPI Registry data", confidence="high"),
    "given_name": TrustScore(score=0.95, reason="Official registry name data", confidence="high"),
    "family_name": TrustScore(score=0.95, reason="Official registry name data", confidence="high"),
    "primary_taxonomy": TrustScore(score=0.92, reason="Official taxonomy classification", confidence="high"),
    "practice_name": TrustScore(score=0.80, reason="Organization name from registry", confidence="medium"),
    "address_street": TrustScore(score=0.85, reason="Primary address from registry", confidence="medium"),
    "phone_primary": TrustScore(score=0.70, reason="Phone from registry (may be outdated)", confidence="medium"),
    "email": TrustScore(score=0.0, reason="No email in registry", confidence="none"),
    "license_number": TrustScore(score=0.0, reason="NPI Registry doesn't provide license information", confidence="none"),
    "license_state": TrustScore(score=0.0, reason="NPI Registry doesn't provide license information", confidence="none"),
    "license_status": TrustScore(score=0.0, reason="NPI Registry doesn't provide license information", confidence="none")
}
```

## Trust Score Guidelines

### High Confidence (0.8-1.0)
- **NPI Number**: Official registry identifier
- **Names**: Official registry name data
- **Taxonomy**: Official specialty classification

### Medium Confidence (0.5-0.8)
- **Practice Name**: Organization name from registry
- **Address**: Primary address from registry
- **Phone**: May be outdated or incorrect

### Low Confidence (0.1-0.5)
- **Email**: Often missing or outdated in registry

### No Confidence (0.0)
- **License Information**: Not provided by NPI Registry

## Error Handling

### Common Error Scenarios

1. **Invalid NPI Format**
   ```python
   result = await connector.search_provider_by_npi("123")
   # result.success = False
   # result.error = "Invalid NPI format. Must be 10 digits."
   ```

2. **NPI Not Found**
   ```python
   result = await connector.search_provider_by_npi("9999999999")
   # result.success = False
   # result.error = "NPI 9999999999 not found in registry"
   ```

3. **No Name Matches**
   ```python
   result = await connector.search_provider_by_name("NonExistent", "Provider")
   # result.success = False
   # result.error = "No providers found for NonExistent Provider"
   ```

4. **API Errors**
   ```python
   # Network timeout, server errors, etc.
   # result.success = False
   # result.error = "API error: [specific error message]"
   ```

## Rate Limiting

The connector implements built-in rate limiting:
- **Delay**: 0.1 seconds between requests (10 requests/second)
- **Automatic**: Applied to all API calls
- **Configurable**: Can be adjusted in constructor

## NPI Validation

The connector validates NPI numbers using:
1. **Format Check**: Must be exactly 10 digits
2. **Luhn Algorithm**: Validates the checksum digit
3. **Range Check**: Rejects common invalid patterns (all zeros, etc.)

## Testing

Run the test suite:

```bash
# Run all NPI connector tests
pytest backend/tests/test_npi_connector.py -v

# Run with coverage
pytest backend/tests/test_npi_connector.py --cov=connectors.npi

# Run integration tests (requires API access)
pytest backend/tests/test_npi_connector.py -m integration
```

## Example Output

### Successful NPI Lookup

```
✅ Provider Found!
   Name: JOHN SMITH
   NPI: 1234567890
   Practice: JOHN SMITH MEDICAL PRACTICE
   Specialty: 207Q00000X
   Address: 123 MAIN ST
   City: SAN FRANCISCO, CA 94102
   Phone: 415-555-0123

📊 Trust Scores:
   npi_number         : 0.98 - high
   given_name         : 0.95 - high
   family_name        : 0.95 - high
   primary_taxonomy   : 0.92 - high
   practice_name      : 0.80 - medium
   address_street     : 0.85 - medium
   phone_primary      : 0.70 - medium
   email              : 0.00 - none
```

### Name Search Results

```
✅ Found 2 providers

   Provider 1:
   Name: JOHN SMITH
   NPI: 1234567890
   Practice: JOHN SMITH MEDICAL PRACTICE
   Specialty: 207Q00000X
   Location: SAN FRANCISCO, CA

   Provider 2:
   Name: JOHN SMITH
   NPI: 0987654321
   Practice: SMITH CARDIOLOGY GROUP
   Specialty: 207RC0000X
   Location: LOS ANGELES, CA
```

## Best Practices

1. **Always check success status** before accessing data
2. **Use trust scores** to determine data reliability
3. **Handle errors gracefully** with appropriate fallbacks
4. **Respect rate limits** to avoid API throttling
5. **Validate NPI numbers** before making API calls
6. **Cache results** when possible to reduce API calls

## Limitations

1. **No License Information**: NPI Registry doesn't provide license numbers or status
2. **Outdated Contact Info**: Phone numbers and addresses may be outdated
3. **Limited Email Data**: Email addresses are often missing
4. **Rate Limits**: API has built-in rate limiting
5. **Data Quality**: Some providers may have incomplete or incorrect data

## Related Documentation

- [Base Connector Documentation](BASE_CONNECTOR.md)
- [Provider Model Documentation](PROVIDER_MODEL.md)
- [API Testing Guide](API_TESTING.md)
