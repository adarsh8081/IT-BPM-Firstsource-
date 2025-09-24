# Google Places Connector

## Overview

The Google Places Connector provides functionality to validate addresses using Google Places API and Google Geocoding API. It returns normalized address components, place_id, coordinates, and match confidence scores with comprehensive rate limiting and exponential backoff.

## Features

- **Address Validation**: Validate addresses using Google Geocoding API
- **Component Validation**: Validate addresses using individual components
- **Place Details**: Get detailed information using Google Places API
- **Data Normalization**: Converts Google API data to our provider schema
- **Trust Scoring**: Provides confidence scores (0-1) for each field
- **Rate Limiting**: Built-in rate limiting for Google API quotas
- **Exponential Backoff**: Automatic retry with exponential backoff
- **Error Handling**: Comprehensive error handling and validation

## Prerequisites

### Google API Setup

1. **Create Google Cloud Project**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing project

2. **Enable APIs**
   - Enable "Geocoding API"
   - Enable "Places API"
   - Enable "Maps JavaScript API" (optional)

3. **Create API Key**
   - Go to "Credentials" in Google Cloud Console
   - Create API key
   - Restrict key to specific APIs and IPs (recommended)

4. **Set Up Billing**
   - Google APIs require billing account
   - Set up usage quotas and limits

## Installation

```bash
pip install httpx  # For async HTTP requests
```

## Usage

### Basic Address Validation

```python
import asyncio
from connectors.google_places import GooglePlacesConnector

async def validate_address():
    connector = GooglePlacesConnector(api_key="YOUR_GOOGLE_API_KEY")
    
    # Validate address
    result = await connector.validate_address("1600 Amphitheatre Parkway, Mountain View, CA 94043")
    
    if result.success:
        print(f"Place ID: {result.data['place_id']}")
        print(f"Coordinates: {result.data['latitude']}, {result.data['longitude']}")
        print(f"Formatted Address: {result.data['formatted_address']}")
        print(f"Match Confidence: {result.data['match_confidence']}")
        
        # Check trust scores
        for field, trust in result.trust_scores.items():
            print(f"{field}: {trust.score:.2f} - {trust.confidence}")
    else:
        print(f"Error: {result.error}")

# Run the example
asyncio.run(validate_address())
```

### Component-based Validation

```python
async def validate_components():
    connector = GooglePlacesConnector(api_key="YOUR_GOOGLE_API_KEY")
    
    # Validate using components
    components = {
        'street': '123 Main Street',
        'city': 'San Francisco',
        'state': 'CA',
        'zip': '94102',
        'country': 'US'
    }
    
    result = await connector.validate_address_components(components)
    
    if result.success:
        print(f"Normalized Address: {result.data['formatted_address']}")
        print(f"Place ID: {result.data['place_id']}")
        print(f"Coordinates: {result.data['latitude']}, {result.data['longitude']}")
    else:
        print(f"Error: {result.error}")

asyncio.run(validate_components())
```

### Place Details Retrieval

```python
async def get_place_details():
    connector = GooglePlacesConnector(api_key="YOUR_GOOGLE_API_KEY")
    
    # Get place details
    result = await connector.get_place_details("ChIJ1234567890abcdef")
    
    if result.success:
        print(f"Name: {result.data['name']}")
        print(f"Address: {result.data['formatted_address']}")
        print(f"Types: {result.data['types']}")
        print(f"Coordinates: {result.data['latitude']}, {result.data['longitude']}")
    else:
        print(f"Error: {result.error}")

asyncio.run(get_place_details())
```

## API Reference

### GooglePlacesConnector Class

#### Constructor

```python
GooglePlacesConnector(api_key: str)
```

- `api_key`: Google API key with Geocoding API and Places API enabled

#### Methods

##### `validate_address(address: str, country_code: Optional[str] = None) -> ConnectorResponse`

Validate address using Google Geocoding API.

**Parameters:**
- `address` (str): Address string to validate
- `country_code` (str, optional): Country code bias (e.g., 'US', 'CA')

**Returns:**
- `ConnectorResponse`: Contains success status, normalized data, and trust scores

**Example:**
```python
result = await connector.validate_address("1600 Amphitheatre Parkway, Mountain View, CA")
```

##### `validate_address_components(address_components: Dict[str, str]) -> ConnectorResponse`

Validate address using individual components.

**Parameters:**
- `address_components` (dict): Dictionary with keys like 'street', 'city', 'state', 'zip', 'country'

**Returns:**
- `ConnectorResponse`: Contains success status, validated data, and trust scores

**Example:**
```python
components = {'street': '123 Main St', 'city': 'San Francisco', 'state': 'CA'}
result = await connector.validate_address_components(components)
```

##### `get_place_details(place_id: str) -> ConnectorResponse`

Get detailed information for a place using place_id.

**Parameters:**
- `place_id` (str): Google Places place_id

**Returns:**
- `ConnectorResponse`: Contains success status, place details, and trust scores

**Example:**
```python
result = await connector.get_place_details("ChIJ1234567890abcdef")
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

### Normalized Address Data

```python
{
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
}
```

### Trust Scores

```python
{
    "place_id": TrustScore(score=0.95, reason="Google Places unique identifier", confidence="high"),
    "latitude": TrustScore(score=0.90, reason="Google Maps coordinate data", confidence="high"),
    "longitude": TrustScore(score=0.90, reason="Google Maps coordinate data", confidence="high"),
    "formatted_address": TrustScore(score=0.90, reason="Google formatted address", confidence="high"),
    "address_street": TrustScore(score=0.85, reason="Google street address data", confidence="high"),
    "address_city": TrustScore(score=0.88, reason="Google locality data", confidence="high"),
    "address_state": TrustScore(score=0.88, reason="Google administrative area data", confidence="high"),
    "address_zip": TrustScore(score=0.85, reason="Google postal code data", confidence="high"),
    "match_confidence": TrustScore(score=0.95, reason="Google geometry accuracy assessment", confidence="high")
}
```

## Geometry Accuracy Types

Google provides different accuracy levels for geocoded addresses:

| Accuracy Type | Description | Confidence Score |
|---------------|-------------|------------------|
| `ROOFTOP` | Precise location at building level | 0.95 |
| `RANGE_INTERPOLATED` | Interpolated between address ranges | 0.85 |
| `GEOMETRIC_CENTER` | Center of geometry (polygon) | 0.75 |
| `APPROXIMATE` | Approximate location | 0.60 |

## Rate Limiting & Backoff

### Rate Limits

The connector implements multiple rate limiting strategies:

- **Geocoding API**: 50 requests per second
- **Places API**: 100 requests per 100 seconds
- **Base Rate Limit**: 10 requests per second (configurable)

### Exponential Backoff

Automatic retry with exponential backoff for:
- `OVER_QUERY_LIMIT` responses
- Network timeouts
- Server errors (5xx)

**Backoff Configuration:**
- Base delay: 1.0 seconds
- Maximum delay: 60.0 seconds
- Multiplier: 2.0

## Error Handling

### Common Error Scenarios

1. **Invalid Address**
   ```python
   result = await connector.validate_address("Nonexistent Address")
   # result.success = False
   # result.error = "Address validation failed: Low confidence (0.00)"
   ```

2. **Rate Limit Exceeded**
   ```python
   # Automatic retry with exponential backoff
   # Will retry up to max_retries times
   ```

3. **Invalid Place ID**
   ```python
   result = await connector.get_place_details("invalid_place_id")
   # result.success = False
   # result.error = "Place details not found"
   ```

4. **API Errors**
   ```python
   # Network timeout, server errors, etc.
   # result.success = False
   # result.error = "Address validation error: [specific error message]"
   ```

### Error Response Codes

| Status | Description | Action |
|--------|-------------|---------|
| `OK` | Request successful | Process results |
| `ZERO_RESULTS` | No results found | Return low confidence |
| `OVER_QUERY_LIMIT` | Rate limit exceeded | Retry with backoff |
| `REQUEST_DENIED` | API key invalid/restricted | Check API key |
| `INVALID_REQUEST` | Invalid parameters | Check input format |
| `UNKNOWN_ERROR` | Server error | Retry with backoff |

## Testing

Run the test suite:

```bash
# Run all Google Places connector tests
pytest backend/tests/test_google_places_connector.py -v

# Run with coverage
pytest backend/tests/test_google_places_connector.py --cov=connectors.google_places

# Run integration tests (requires API key)
pytest backend/tests/test_google_places_connector.py -m integration
```

## Example Output

### Successful Address Validation

```
✅ Address validated successfully!
   Place ID: ChIJ1234567890abcdef
   Formatted Address: 1600 Amphitheatre Parkway, Mountain View, CA 94043, USA
   Coordinates: 37.4220656, -122.0840897
   Street: 1600 Amphitheatre Parkway
   City: Mountain View
   State: CA
   ZIP: 94043
   Country: US
   Geometry Accuracy: ROOFTOP
   Match Confidence: 0.95

📊 Trust Scores:
   place_id            : 0.95 - high
   latitude            : 0.90 - high
   longitude           : 0.90 - high
   formatted_address   : 0.90 - high
   address_street      : 0.85 - high
   address_city        : 0.88 - high
   address_state       : 0.88 - high
   address_zip         : 0.85 - high
   match_confidence    : 0.95 - high
```

### Component Validation Results

```
✅ Components validated successfully!
   Place ID: ChIJ1234567890abcdef
   Normalized Street: 123 Main Street
   Normalized City: San Francisco
   Normalized State: CA
   Normalized ZIP: 94102
   Coordinates: 37.7749, -122.4194
   Match Confidence: 0.85
```

## Best Practices

1. **API Key Management**
   - Use environment variables for API keys
   - Restrict API keys to specific APIs and IPs
   - Monitor usage and set up billing alerts

2. **Rate Limiting**
   - Respect Google's rate limits
   - Implement caching for repeated requests
   - Use exponential backoff for retries

3. **Error Handling**
   - Always check success status before accessing data
   - Handle rate limit errors gracefully
   - Implement fallback strategies

4. **Data Quality**
   - Use trust scores to determine data reliability
   - Validate geometry accuracy levels
   - Handle low-confidence results appropriately

5. **Cost Optimization**
   - Cache results when possible
   - Use specific API endpoints for your needs
   - Monitor usage and optimize queries

## Cost Considerations

### Google API Pricing (as of 2024)

- **Geocoding API**: $5.00 per 1,000 requests
- **Places API (Place Details)**: $17.00 per 1,000 requests
- **Places API (Place Search)**: $32.00 per 1,000 requests

### Cost Optimization Tips

1. **Caching**: Cache results to avoid duplicate requests
2. **Batching**: Process multiple addresses in batches
3. **Filtering**: Only validate addresses that need validation
4. **Quotas**: Set up daily quotas to control costs
5. **Monitoring**: Monitor usage and set up billing alerts

## Limitations

1. **API Quotas**: Google APIs have daily and per-minute quotas
2. **Billing Required**: All Google APIs require billing account
3. **Rate Limits**: Built-in rate limiting may slow down processing
4. **Data Accuracy**: Results depend on Google's data quality
5. **International Coverage**: Coverage varies by country/region

## Related Documentation

- [Google Geocoding API Documentation](https://developers.google.com/maps/documentation/geocoding)
- [Google Places API Documentation](https://developers.google.com/maps/documentation/places)
- [Base Connector Documentation](BASE_CONNECTOR.md)
- [Provider Model Documentation](PROVIDER_MODEL.md)
- [API Testing Guide](API_TESTING.md)
