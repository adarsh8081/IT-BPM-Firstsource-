# State Board Mock Connector

## Overview

The State Board Mock Connector provides a modular scraper for state medical board websites with configurable XPaths/CSS selectors, built-in robot detection, and retry logic. It includes a mock HTTP server for testing license verification responses.

## Features

- **Modular Scraping**: Configurable selectors for different state medical board websites
- **Robot Detection**: Built-in robot detection and handling
- **Rate Limiting**: Configurable rate limiting and exponential backoff
- **License Verification**: Extract license status, provider info, and board actions
- **Data Normalization**: Converts scraped data to standardized format
- **Trust Scoring**: Provides confidence scores (0-1) for each field
- **Mock Server**: Built-in mock HTTP server for testing
- **Error Handling**: Comprehensive error handling and validation

## Installation

```bash
pip install httpx beautifulsoup4 lxml  # For HTTP requests and HTML parsing
```

## Usage

### Basic License Verification

```python
import asyncio
from connectors.state_board_mock import StateBoardMockConnector, ScrapingConfig

async def verify_license():
    # Create scraping configuration
    config = ScrapingConfig(
        state_code="CA",
        state_name="California",
        base_url="https://www.mbc.ca.gov",
        search_url="https://www.mbc.ca.gov/breeze/license_lookup.php",
        search_method="POST",
        selectors={
            "provider_name": ".physician-name",
            "license_status": ".license-status",
            "issue_date": ".date-issued",
            "expiry_date": ".date-expires"
        }
    )
    
    # Initialize connector
    connector = StateBoardMockConnector(config)
    
    try:
        # Verify license
        result = await connector.verify_license("A123456", "Dr. John Smith")
        
        if result.success:
            print(f"License: {result.data['license_number']}")
            print(f"Provider: {result.data['provider_name']}")
            print(f"Status: {result.data['license_status']}")
            print(f"Confidence: {result.data['confidence_score']:.2f}")
            
            # Check trust scores
            for field, trust in result.trust_scores.items():
                print(f"{field}: {trust.score:.2f} - {trust.confidence}")
        else:
            print(f"Error: {result.error}")
    
    finally:
        await connector.close()

# Run the example
asyncio.run(verify_license())
```

### Mock Server for Testing

```python
import asyncio
from connectors.state_board_mock import MockStateBoardServer

async def run_mock_server():
    # Start mock server
    mock_server = MockStateBoardServer(port=8080)
    
    print("Starting mock server on http://127.0.0.1:8080")
    print("Available test licenses:")
    print("  • A123456 - Dr. John Smith (Active)")
    print("  • B789012 - Dr. Jane Doe (Suspended)")
    print("  • C345678 - Dr. Robert Johnson (Expired)")
    
    try:
        await mock_server.start_server()
    except KeyboardInterrupt:
        print("Stopping mock server...")
        await mock_server.stop_server()

# Run the mock server
asyncio.run(run_mock_server())
```

## API Reference

### StateBoardMockConnector Class

#### Constructor

```python
StateBoardMockConnector(config: ScrapingConfig)
```

- `config`: Scraping configuration for the state medical board

#### Methods

##### `verify_license(license_number: str, provider_name: Optional[str] = None) -> ConnectorResponse`

Verify medical license with state medical board.

**Parameters:**
- `license_number` (str): Medical license number
- `provider_name` (str, optional): Provider name for additional verification

**Returns:**
- `ConnectorResponse`: Contains success status, normalized data, and trust scores

**Example:**
```python
result = await connector.verify_license("A123456", "Dr. John Smith")
```

##### `close() -> None`

Close the HTTP session and cleanup resources.

**Example:**
```python
await connector.close()
```

### ScrapingConfig Class

#### Constructor

```python
ScrapingConfig(
    state_code: str,
    state_name: str,
    base_url: str,
    search_url: str,
    search_method: str = "POST",
    search_params: Dict[str, str] = None,
    selectors: Dict[str, str] = None,
    robot_check_selectors: List[str] = None,
    rate_limit_delay: float = 2.0,
    max_retries: int = 3,
    timeout: int = 30,
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
)
```

#### Parameters

- `state_code` (str): Two-letter state code (e.g., "CA", "TX")
- `state_name` (str): Full state name (e.g., "California", "Texas")
- `base_url` (str): Base URL of the medical board website
- `search_url` (str): URL for license search functionality
- `search_method` (str): HTTP method for search ("GET" or "POST")
- `search_params` (dict): Parameter mapping for search requests
- `selectors` (dict): CSS selectors or XPath expressions for data extraction
- `robot_check_selectors` (list): Selectors to detect robot detection
- `rate_limit_delay` (float): Delay between requests in seconds
- `max_retries` (int): Maximum number of retry attempts
- `timeout` (int): Request timeout in seconds
- `user_agent` (str): User agent string for requests

## Configuration Examples

### California Medical Board

```python
ca_config = ScrapingConfig(
    state_code="CA",
    state_name="California",
    base_url="https://www.mbc.ca.gov",
    search_url="https://www.mbc.ca.gov/breeze/license_lookup.php",
    search_method="POST",
    search_params={
        "license_number": "license_number",
        "provider_name": "provider_name"
    },
    selectors={
        "provider_name": ".physician-name",
        "license_status": ".license-status",
        "issue_date": ".date-issued",
        "expiry_date": ".date-expires",
        "specialty": ".specialty",
        "board_actions": ".board-actions"
    },
    rate_limit_delay=2.0,
    max_retries=3
)
```

### Texas Medical Board

```python
tx_config = ScrapingConfig(
    state_code="TX",
    state_name="Texas",
    base_url="https://www.tmb.state.tx.us",
    search_url="https://www.tmb.state.tx.us/page/physician-profile-search",
    search_method="GET",
    search_params={
        "license_number": "lic",
        "provider_name": "name"
    },
    selectors={
        "provider_name": ".physician-name",
        "license_status": ".license-status",
        "issue_date": ".date-issued",
        "expiry_date": ".date-expires",
        "specialty": ".specialty",
        "board_actions": ".disciplinary-actions"
    },
    rate_limit_delay=1.5,
    max_retries=2
)
```

### New York Medical Board

```python
ny_config = ScrapingConfig(
    state_code="NY",
    state_name="New York",
    base_url="https://www.op.nysed.gov",
    search_url="https://www.op.nysed.gov/prof/med/medlic.htm",
    search_method="POST",
    search_params={
        "license_number": "licensenum",
        "provider_name": "name"
    },
    selectors={
        "provider_name": ".name",
        "license_status": ".status",
        "issue_date": ".issued",
        "expiry_date": ".expires",
        "specialty": ".specialization",
        "board_actions": ".actions"
    },
    rate_limit_delay=2.0,
    max_retries=3
)
```

## Selector Types

### CSS Selectors

```python
selectors = {
    "provider_name": ".physician-name",
    "license_status": "#license-status",
    "issue_date": "div.date-issued",
    "expiry_date": "span.expiry-date",
    "specialty": ".specialty-list li:first-child",
    "board_actions": ".actions table tr"
}
```

### XPath Selectors

```python
selectors = {
    "provider_name": "//div[@class='physician-name']",
    "license_status": "//span[@id='license-status']",
    "issue_date": "//td[contains(text(), 'Issued')]/following-sibling::td",
    "expiry_date": "//td[contains(text(), 'Expires')]/following-sibling::td",
    "specialty": "//div[@class='specialty']//text()",
    "board_actions": "//table[@class='actions']//tr"
}
```

### Attribute Selectors

```python
selectors = {
    "provider_name": "input[name='physician_name']",
    "license_status": "span[data-status='current']",
    "issue_date": "div[data-field='issue_date']",
    "expiry_date": "div[data-field='expiry_date']",
    "specialty": "select[name='specialty'] option[selected]",
    "board_actions": "div[class*='action']"
}
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

### Normalized License Data

```python
{
    "license_number": "A123456",
    "provider_name": "Dr. John Smith",
    "license_status": "active",
    "issue_date": "2020-01-15",
    "expiry_date": "2025-01-15",
    "specialty": "Internal Medicine",
    "board_actions": [
        {
            "description": "Suspension for 6 months due to violation of medical standards",
            "date": "2023-12-01",
            "type": "suspension"
        }
    ],
    "verification_date": "2024-01-15T10:30:00Z",
    "source_url": "https://www.mbc.ca.gov/breeze/license_lookup.php",
    "confidence_score": 0.95,
    "state_code": "CA",
    "state_name": "California"
}
```

### Trust Scores

```python
{
    "license_number": TrustScore(score=0.95, reason="Direct license number match", confidence="high"),
    "license_status": TrustScore(score=0.80, reason="Official state medical board status", confidence="high"),
    "provider_name": TrustScore(score=0.75, reason="Provider name from state board", confidence="medium"),
    "issue_date": TrustScore(score=0.70, reason="Issue date from state board", confidence="medium"),
    "expiry_date": TrustScore(score=0.70, reason="Expiry date from state board", confidence="medium"),
    "specialty": TrustScore(score=0.65, reason="Specialty information from state board", confidence="medium"),
    "board_actions": TrustScore(score=0.90, reason="Official board disciplinary actions", confidence="high"),
    "confidence_score": TrustScore(score=0.95, reason="Overall verification confidence", confidence="high")
}
```

## License Status Types

| Status | Description | Text Variations |
|--------|-------------|-----------------|
| `ACTIVE` | License is currently valid and active | "Active", "Current", "Valid", "Good Standing" |
| `EXPIRED` | License has expired and is no longer valid | "Expired", "Expire", "Invalid", "Lapsed" |
| `SUSPENDED` | License is temporarily suspended | "Suspended", "Suspend", "Temporary Suspension" |
| `REVOKED` | License has been permanently revoked | "Revoked", "Revoke", "Cancelled", "Terminated" |
| `PENDING` | License application or renewal is pending | "Pending", "Pending Review", "Under Review" |
| `PROBATION` | License is on probationary status | "Probation", "Probationary", "On Probation" |
| `INACTIVE` | License status is unclear or inactive | Default for unrecognized statuses |

## Board Action Types

| Type | Description | Keywords |
|------|-------------|----------|
| `suspension` | License suspension | "suspension", "suspend" |
| `revocation` | License revocation | "revocation", "revoke" |
| `probation` | Probationary status | "probation", "probationary" |
| `fine` | Financial penalty | "fine", "penalty" |
| `warning` | Warning or reprimand | "warning", "reprimand" |
| `other` | Other disciplinary action | Default for unrecognized actions |

## Robot Detection

### Built-in Robot Detection

The connector automatically checks for common robot detection indicators:

```python
robot_check_selectors = [
    "input[name='captcha']",
    ".captcha",
    "#captcha",
    "input[name='robot']",
    ".robot-check",
    "input[name='verification']"
]
```

### Robot Detection Text

The connector also checks for robot detection text:

```python
robot_text_indicators = [
    "robot", "captcha", "verification", "security check",
    "access denied", "blocked", "suspicious activity"
]
```

### Handling Robot Detection

When robot detection is triggered:

1. The connector returns an error response
2. No scraping is attempted
3. The user should implement alternative verification methods

## Rate Limiting & Backoff

### Rate Limiting

- **Default Delay**: 2.0 seconds between requests
- **Configurable**: Can be adjusted per state
- **Respectful**: Follows website-specific requirements

### Exponential Backoff

- **Base Delay**: Configurable (default 2.0 seconds)
- **Maximum Delay**: 30.0 seconds
- **Multiplier**: 2.0
- **Retry Logic**: Automatic retry for failures

### Retry Scenarios

- Network timeouts
- HTTP errors (5xx)
- Parsing errors
- No results found

## Error Handling

### Common Error Scenarios

1. **Robot Detection**
   ```python
   result = await connector.verify_license("A123456")
   # result.success = False
   # result.error = "Robot detection triggered - cannot proceed with scraping"
   ```

2. **No Results Found**
   ```python
   result = await connector.verify_license("X999999")
   # result.success = False
   # result.error = "License verification failed: Low confidence (0.00)"
   ```

3. **Network Errors**
   ```python
   # Automatic retry with exponential backoff
   # Will retry up to max_retries times
   ```

4. **Parsing Errors**
   ```python
   # result.success = False
   # result.error = "License verification error: [specific error message]"
   ```

### Error Response Codes

| Scenario | Description | Action |
|----------|-------------|---------|
| Robot Detection | CAPTCHA or security check detected | Return error, no retry |
| No Results | License not found in database | Return low confidence |
| Network Error | Connection timeout or failure | Retry with backoff |
| Parsing Error | HTML parsing failed | Retry with backoff |
| HTTP Error | Server error (5xx) | Retry with backoff |

## Testing

### Mock Server

The connector includes a built-in mock server for testing:

```python
from connectors.state_board_mock import MockStateBoardServer

async def test_with_mock_server():
    # Start mock server
    mock_server = MockStateBoardServer(port=8080)
    await mock_server.start_server()
    
    # Test with mock server
    config = ScrapingConfig(
        state_code="TEST",
        state_name="Test State",
        base_url="http://127.0.0.1:8080",
        search_url="http://127.0.0.1:8080/search",
        search_method="POST"
    )
    
    connector = StateBoardMockConnector(config)
    result = await connector.verify_license("A123456")
    
    # Stop mock server
    await mock_server.stop_server()
```

### Test Data

The mock server provides test data for:

- **A123456**: Dr. John Smith (Active license)
- **B789012**: Dr. Jane Doe (Suspended license)
- **C345678**: Dr. Robert Johnson (Expired license)

### Running Tests

```bash
# Run all state board connector tests
pytest backend/tests/test_state_board_mock_connector.py -v

# Run with coverage
pytest backend/tests/test_state_board_mock_connector.py --cov=connectors.state_board_mock

# Run integration tests
pytest backend/tests/test_state_board_mock_connector.py -m integration
```

## Best Practices

### Configuration

1. **Respect robots.txt**: Always check and respect robots.txt files
2. **Rate Limiting**: Implement appropriate delays between requests
3. **User Agent**: Use realistic user agent strings
4. **Selectors**: Test selectors thoroughly before deployment

### Error Handling

1. **Robot Detection**: Handle gracefully without retrying
2. **Rate Limiting**: Implement exponential backoff
3. **Timeouts**: Set appropriate timeout values
4. **Retries**: Limit retry attempts to avoid overloading servers

### Data Quality

1. **Validation**: Validate scraped data before processing
2. **Confidence Scores**: Use confidence scores to assess data quality
3. **Fallbacks**: Implement fallback verification methods
4. **Monitoring**: Monitor for website changes and selector updates

### Legal Compliance

1. **Terms of Service**: Respect website terms of service
2. **Rate Limits**: Stay within acceptable usage limits
3. **Data Privacy**: Handle personal information appropriately
4. **Attribution**: Provide proper attribution for data sources

## Limitations

1. **Website Changes**: Selectors may break when websites are updated
2. **Robot Detection**: Some sites may block automated access
3. **Rate Limits**: Strict rate limiting may slow down processing
4. **Data Accuracy**: Results depend on website data quality
5. **Legal Restrictions**: Some states may restrict automated access

## Related Documentation

- [Base Connector Documentation](BASE_CONNECTOR.md)
- [Provider Model Documentation](PROVIDER_MODEL.md)
- [NPI Connector Documentation](NPI_CONNECTOR.md)
- [Google Places Connector Documentation](GOOGLE_PLACES_CONNECTOR.md)
- [API Testing Guide](API_TESTING.md)
