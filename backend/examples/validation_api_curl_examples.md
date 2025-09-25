# Validation API cURL Examples

This document provides comprehensive cURL examples for testing the Provider Data Validation API endpoints. All examples include proper politeness headers and robots.txt compliance.

## Base Configuration

### Environment Variables
```bash
# Set your API base URL
export API_BASE_URL="http://localhost:8000"

# Set authentication token (if required)
export API_TOKEN="your-api-token-here"

# Set politeness headers
export USER_AGENT="Provider-Validation-System/1.0"
export ACCEPT_HEADER="application/json, text/html"
```

### Common Headers
All requests include politeness headers for robots.txt compliance:

```bash
# Common headers for all requests
COMMON_HEADERS=(
  -H "User-Agent: Provider-Validation-System/1.0"
  -H "Accept: application/json, text/html"
  -H "Accept-Language: en-US,en;q=0.9"
  -H "Accept-Encoding: gzip, deflate"
  -H "Connection: keep-alive"
  -H "Cache-Control: no-cache"
)

# Authentication header (if required)
AUTH_HEADER="-H \"Authorization: Bearer $API_TOKEN\""
```

## 1. Phone Validation (E.164 Normalization)

### Validate Phone Number
```bash
curl -X POST "$API_BASE_URL/api/v1/validate/phone" \
  "${COMMON_HEADERS[@]}" \
  $AUTH_HEADER \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "(555) 123-4567",
    "country_code": "US",
    "validation_options": {
      "e164_normalization": true,
      "carrier_lookup": true,
      "geolocation_check": true
    }
  }'
```

### Batch Phone Validation
```bash
curl -X POST "$API_BASE_URL/api/v1/validate/phone/batch" \
  "${COMMON_HEADERS[@]}" \
  $AUTH_HEADER \
  -H "Content-Type: application/json" \
  -d '{
    "phone_numbers": [
      "(555) 123-4567",
      "+1-555-987-6543",
      "555.123.4567",
      "invalid-phone"
    ],
    "country_code": "US"
  }'
```

### Expected Response
```json
{
  "success": true,
  "data": {
    "original_number": "(555) 123-4567",
    "e164_format": "+15551234567",
    "is_valid": true,
    "confidence": 0.95,
    "carrier": "Verizon Wireless",
    "geolocation": "San Francisco, CA",
    "validation_details": {
      "format_valid": true,
      "carrier_found": true,
      "geolocation_found": true
    }
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## 2. Address Validation (Place ID Matching)

### Validate Address
```bash
curl -X POST "$API_BASE_URL/api/v1/validate/address" \
  "${COMMON_HEADERS[@]}" \
  $AUTH_HEADER \
  -H "Content-Type: application/json" \
  -d '{
    "address": "123 Main Street, San Francisco, CA 94102",
    "validation_options": {
      "place_id_required": true,
      "geocode_distance_threshold": 100,
      "address_components_match": true
    }
  }'
```

### Address Components Validation
```bash
curl -X POST "$API_BASE_URL/api/v1/validate/address/components" \
  "${COMMON_HEADERS[@]}" \
  $AUTH_HEADER \
  -H "Content-Type: application/json" \
  -d '{
    "address_components": {
      "street": "123 Main Street",
      "city": "San Francisco",
      "state": "CA",
      "zip": "94102",
      "country": "US"
    },
    "validation_options": {
      "geocode_distance_threshold": 100
    }
  }'
```

### Expected Response
```json
{
  "success": true,
  "data": {
    "original_address": "123 Main Street, San Francisco, CA 94102",
    "formatted_address": "123 Main St, San Francisco, CA 94102, USA",
    "place_id": "ChIJ1234567890abcdef",
    "confidence": 0.90,
    "geocode_distance": 50,
    "coordinates": {
      "latitude": 37.7749,
      "longitude": -122.4194
    },
    "address_components": {
      "street_number": "123",
      "route": "Main Street",
      "locality": "San Francisco",
      "administrative_area_level_1": "CA",
      "postal_code": "94102",
      "country": "US"
    },
    "validation_details": {
      "place_id_found": true,
      "distance_within_threshold": true,
      "components_match": true
    }
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## 3. License Validation (State Board Verification)

### Validate License Number
```bash
curl -X POST "$API_BASE_URL/api/v1/validate/license" \
  "${COMMON_HEADERS[@]}" \
  $AUTH_HEADER \
  -H "Content-Type: application/json" \
  -d '{
    "license_number": "A123456",
    "license_state": "CA",
    "provider_name": "Dr. John Smith",
    "validation_options": {
      "license_status_required": "ACTIVE",
      "state_board_check": true,
      "expiry_date_check": true
    }
  }'
```

### Batch License Validation
```bash
curl -X POST "$API_BASE_URL/api/v1/validate/license/batch" \
  "${COMMON_HEADERS[@]}" \
  $AUTH_HEADER \
  -H "Content-Type: application/json" \
  -d '{
    "licenses": [
      {
        "license_number": "A123456",
        "license_state": "CA",
        "provider_name": "Dr. John Smith"
      },
      {
        "license_number": "B789012",
        "license_state": "TX",
        "provider_name": "Dr. Jane Doe"
      }
    ],
    "validation_options": {
      "license_status_required": "ACTIVE"
    }
  }'
```

### Expected Response
```json
{
  "success": true,
  "data": {
    "license_number": "A123456",
    "license_state": "CA",
    "license_status": "active",
    "confidence": 0.95,
    "provider_name": "Dr. John Smith",
    "issue_date": "2020-01-15",
    "expiry_date": "2025-01-15",
    "board_actions": [],
    "validation_details": {
      "status_active": true,
      "not_expired": true,
      "no_disciplinary_actions": true
    }
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## 4. Email Validation (MX Record Check)

### Validate Email Address
```bash
curl -X POST "$API_BASE_URL/api/v1/validate/email" \
  "${COMMON_HEADERS[@]}" \
  $AUTH_HEADER \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john.smith@example.com",
    "validation_options": {
      "mx_record_required": true,
      "syntax_validation": true,
      "domain_validation": true
    }
  }'
```

### Batch Email Validation
```bash
curl -X POST "$API_BASE_URL/api/v1/validate/email/batch" \
  "${COMMON_HEADERS[@]}" \
  $AUTH_HEADER \
  -H "Content-Type: application/json" \
  -d '{
    "emails": [
      "john.smith@example.com",
      "jane.doe@hospital.org",
      "invalid-email",
      "nonexistent@invalid-domain.com"
    ]
  }'
```

### Expected Response
```json
{
  "success": true,
  "data": {
    "email": "john.smith@example.com",
    "is_valid": true,
    "confidence": 0.85,
    "domain": "example.com",
    "mx_record_exists": true,
    "mx_records": 5,
    "validation_details": {
      "syntax_valid": true,
      "domain_valid": true,
      "mx_record_found": true
    }
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## 5. Name Validation (Fuzzy Matching)

### Validate Provider Name
```bash
curl -X POST "$API_BASE_URL/api/v1/validate/name" \
  "${COMMON_HEADERS[@]}" \
  $AUTH_HEADER \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Dr. John Smith",
    "npi_number": "1234567890",
    "validation_options": {
      "levenshtein_threshold": 0.85,
      "npi_name_comparison": true,
      "case_insensitive": true
    }
  }'
```

### Name Components Validation
```bash
curl -X POST "$API_BASE_URL/api/v1/validate/name/components" \
  "${COMMON_HEADERS[@]}" \
  $AUTH_HEADER \
  -H "Content-Type: application/json" \
  -d '{
    "name_components": {
      "given_name": "John",
      "family_name": "Smith",
      "title": "Dr."
    },
    "npi_number": "1234567890",
    "validation_options": {
      "levenshtein_threshold": 0.85
    }
  }'
```

### Expected Response
```json
{
  "success": true,
  "data": {
    "original_name": "Dr. John Smith",
    "npi_name": "Dr. John Smith",
    "similarity_ratio": 1.0,
    "confidence": 1.0,
    "levenshtein_distance": 0,
    "validation_details": {
      "exact_match": true,
      "threshold_met": true,
      "case_insensitive_match": true
    }
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## 6. Complete Provider Validation

### Validate Complete Provider Profile
```bash
curl -X POST "$API_BASE_URL/api/v1/validate/provider" \
  "${COMMON_HEADERS[@]}" \
  $AUTH_HEADER \
  -H "Content-Type: application/json" \
  -d '{
    "provider_data": {
      "provider_id": "12345",
      "given_name": "Dr. John Smith",
      "family_name": "Smith",
      "npi_number": "1234567890",
      "phone_primary": "(555) 123-4567",
      "email": "john.smith@example.com",
      "address_street": "123 Main Street, San Francisco, CA 94102",
      "license_number": "A123456",
      "license_state": "CA"
    },
    "validation_options": {
      "include_all_fields": true,
      "confidence_weighting": true,
      "robots_compliance": true
    }
  }'
```

### Expected Response
```json
{
  "success": true,
  "data": {
    "provider_id": "12345",
    "overall_confidence": 0.92,
    "validation_status": "valid",
    "field_summaries": {
      "phone_primary": {
        "field_name": "phone_primary",
        "overall_confidence": 0.95,
        "status": "valid",
        "weighted_score": 0.38,
        "validation_count": 1
      },
      "address_street": {
        "field_name": "address_street",
        "overall_confidence": 0.90,
        "status": "valid",
        "weighted_score": 0.225,
        "validation_count": 1
      },
      "license_number": {
        "field_name": "license_number",
        "overall_confidence": 0.95,
        "status": "valid",
        "weighted_score": 0.1425,
        "validation_count": 1
      },
      "email": {
        "field_name": "email",
        "overall_confidence": 0.85,
        "status": "valid",
        "weighted_score": 0.17,
        "validation_count": 1
      },
      "given_name": {
        "field_name": "given_name",
        "overall_confidence": 1.0,
        "status": "valid",
        "weighted_score": 0.4,
        "validation_count": 1
      }
    },
    "total_validations": 5,
    "successful_validations": 5,
    "failed_validations": 0,
    "warning_validations": 0
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## 7. Validation Rules Management

### Get Validation Rules
```bash
curl -X GET "$API_BASE_URL/api/v1/validation/rules" \
  "${COMMON_HEADERS[@]}" \
  $AUTH_HEADER
```

### Update Validation Rule
```bash
curl -X PUT "$API_BASE_URL/api/v1/validation/rules/phone_primary" \
  "${COMMON_HEADERS[@]}" \
  $AUTH_HEADER \
  -H "Content-Type: application/json" \
  -d '{
    "rule_type": "e164_normalization",
    "criteria": {
      "format": "E.164",
      "lookup_enabled": true,
      "carrier_check": true,
      "geolocation_check": true
    },
    "weight": 0.4,
    "source": "npi",
    "description": "E.164 phone normalization with carrier lookup"
  }'
```

### Add Custom Validation Rule
```bash
curl -X POST "$API_BASE_URL/api/v1/validation/rules" \
  "${COMMON_HEADERS[@]}" \
  $AUTH_HEADER \
  -H "Content-Type: application/json" \
  -d '{
    "field_name": "npi_number",
    "rule_type": "npi_format_check",
    "criteria": {
      "format": "10_digits",
      "checksum_validation": true,
      "registry_lookup": true
    },
    "weight": 0.4,
    "source": "npi",
    "description": "NPI number format and registry validation"
  }'
```

## 8. Health and Status Endpoints

### Health Check
```bash
curl -X GET "$API_BASE_URL/api/v1/health" \
  "${COMMON_HEADERS[@]}" \
  $AUTH_HEADER
```

### Validation Service Status
```bash
curl -X GET "$API_BASE_URL/api/v1/validation/status" \
  "${COMMON_HEADERS[@]}" \
  $AUTH_HEADER
```

### Rate Limit Status
```bash
curl -X GET "$API_BASE_URL/api/v1/validation/rate-limits" \
  "${COMMON_HEADERS[@]}" \
  $AUTH_HEADER
```

## 9. Error Handling Examples

### Invalid Request Format
```bash
curl -X POST "$API_BASE_URL/api/v1/validate/phone" \
  "${COMMON_HEADERS[@]}" \
  $AUTH_HEADER \
  -H "Content-Type: application/json" \
  -d '{
    "invalid_field": "value"
  }'
```

### Expected Error Response
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Missing required field: phone_number",
    "details": {
      "required_fields": ["phone_number"],
      "provided_fields": ["invalid_field"]
    }
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Rate Limit Exceeded
```bash
# Make multiple requests quickly to trigger rate limit
for i in {1..20}; do
  curl -X POST "$API_BASE_URL/api/v1/validate/phone" \
    "${COMMON_HEADERS[@]}" \
    $AUTH_HEADER \
    -H "Content-Type: application/json" \
    -d '{"phone_number": "(555) 123-4567"}'
  sleep 0.1
done
```

### Expected Rate Limit Response
```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded for phone validation",
    "details": {
      "limit": "10 requests per second",
      "retry_after": 1.0
    }
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## 10. Testing Scripts

### Complete Validation Test Script
```bash
#!/bin/bash

# Set configuration
API_BASE_URL="http://localhost:8000"
API_TOKEN="your-api-token"

# Common headers
COMMON_HEADERS=(
  -H "User-Agent: Provider-Validation-System/1.0"
  -H "Accept: application/json, text/html"
  -H "Accept-Language: en-US,en;q=0.9"
  -H "Accept-Encoding: gzip, deflate"
  -H "Connection: keep-alive"
  -H "Cache-Control: no-cache"
  -H "Authorization: Bearer $API_TOKEN"
)

echo "Testing Provider Validation API..."

# Test phone validation
echo "Testing phone validation..."
curl -X POST "$API_BASE_URL/api/v1/validate/phone" \
  "${COMMON_HEADERS[@]}" \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "(555) 123-4567"}' \
  | jq '.'

# Test address validation
echo "Testing address validation..."
curl -X POST "$API_BASE_URL/api/v1/validate/address" \
  "${COMMON_HEADERS[@]}" \
  -H "Content-Type: application/json" \
  -d '{"address": "123 Main Street, San Francisco, CA 94102"}' \
  | jq '.'

# Test license validation
echo "Testing license validation..."
curl -X POST "$API_BASE_URL/api/v1/validate/license" \
  "${COMMON_HEADERS[@]}" \
  -H "Content-Type: application/json" \
  -d '{"license_number": "A123456", "license_state": "CA"}' \
  | jq '.'

# Test email validation
echo "Testing email validation..."
curl -X POST "$API_BASE_URL/api/v1/validate/email" \
  "${COMMON_HEADERS[@]}" \
  -H "Content-Type: application/json" \
  -d '{"email": "john.smith@example.com"}' \
  | jq '.'

# Test name validation
echo "Testing name validation..."
curl -X POST "$API_BASE_URL/api/v1/validate/name" \
  "${COMMON_HEADERS[@]}" \
  -H "Content-Type: application/json" \
  -d '{"name": "Dr. John Smith", "npi_number": "1234567890"}' \
  | jq '.'

# Test complete provider validation
echo "Testing complete provider validation..."
curl -X POST "$API_BASE_URL/api/v1/validate/provider" \
  "${COMMON_HEADERS[@]}" \
  -H "Content-Type: application/json" \
  -d '{
    "provider_data": {
      "provider_id": "12345",
      "given_name": "Dr. John Smith",
      "family_name": "Smith",
      "npi_number": "1234567890",
      "phone_primary": "(555) 123-4567",
      "email": "john.smith@example.com",
      "address_street": "123 Main Street, San Francisco, CA 94102",
      "license_number": "A123456",
      "license_state": "CA"
    }
  }' \
  | jq '.'

echo "Testing complete!"
```

## 11. Performance Testing

### Load Testing with Apache Bench
```bash
# Test phone validation endpoint
ab -n 100 -c 10 \
  -H "User-Agent: Provider-Validation-System/1.0" \
  -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -p phone_validation.json \
  "$API_BASE_URL/api/v1/validate/phone"

# phone_validation.json content:
# {"phone_number": "(555) 123-4567"}
```

### Concurrent Validation Testing
```bash
#!/bin/bash

# Test concurrent validations
for i in {1..10}; do
  (
    curl -X POST "$API_BASE_URL/api/v1/validate/provider" \
      -H "User-Agent: Provider-Validation-System/1.0" \
      -H "Content-Type: application/json" \
      -d "{
        \"provider_data\": {
          \"provider_id\": \"$i\",
          \"given_name\": \"Dr. Test $i\",
          \"phone_primary\": \"(555) 123-$i\",
          \"email\": \"test$i@example.com\"
        }
      }" &
  )
done

wait
echo "All concurrent validations completed"
```

## 12. Monitoring and Debugging

### Enable Debug Mode
```bash
curl -X POST "$API_BASE_URL/api/v1/validate/phone" \
  "${COMMON_HEADERS[@]}" \
  $AUTH_HEADER \
  -H "Content-Type: application/json" \
  -H "X-Debug: true" \
  -d '{
    "phone_number": "(555) 123-4567",
    "debug_options": {
      "include_validation_steps": true,
      "include_timing": true,
      "include_source_details": true
    }
  }'
```

### Get Validation Metrics
```bash
curl -X GET "$API_BASE_URL/api/v1/validation/metrics" \
  "${COMMON_HEADERS[@]}" \
  $AUTH_HEADER
```

## Notes

1. **Rate Limiting**: All endpoints implement rate limiting. Respect the limits to avoid being blocked.

2. **Robots.txt Compliance**: All requests include proper User-Agent headers for robots.txt compliance.

3. **Politeness**: Requests include appropriate delays and politeness headers to be respectful to external services.

4. **Authentication**: Replace `$API_TOKEN` with your actual API token if authentication is required.

5. **Error Handling**: All endpoints return consistent error responses with appropriate HTTP status codes.

6. **Validation Rules**: Validation rules can be customized per field and source to meet specific requirements.

7. **Confidence Weighting**: The system uses weighted confidence scoring based on source reliability (NPI: 0.4, Google Places: 0.25, Hospital: 0.2, State Board: 0.15).
