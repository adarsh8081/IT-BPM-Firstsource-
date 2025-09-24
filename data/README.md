# Demo Dataset for Provider Data Validation System

This directory contains comprehensive demo data for testing and demonstrating the Provider Data Validation & Directory Management System.

## 📁 Dataset Contents

### 1. Provider CSV Data (`demo_providers.csv`)
- **File**: `demo_providers.csv`
- **Records**: 200 provider profiles
- **Format**: CSV with UTF-8 encoding
- **Purpose**: Comprehensive test dataset with deliberate error patterns

### 2. Synthetic PDF Images (`pdf_images/`)
- **Directory**: `pdf_images/`
- **Files**: 20 PNG images simulating scanned provider application forms
- **Format**: PNG (800x1000 pixels)
- **Purpose**: Test document processing and OCR capabilities

### 3. Generation Scripts
- **CSV Generator**: `generate_demo_csv.py`
- **PDF Generator**: `generate_pdf_images.py`
- **Purpose**: Reproducible data generation for testing

## 📊 Provider CSV Data Schema

### Field Descriptions

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `provider_id` | UUID | Unique provider identifier | `550e8400-e29b-41d4-a716-446655440000` |
| `given_name` | String | Provider's first name | `Dr. Sarah` |
| `family_name` | String | Provider's last name | `Johnson` |
| `npi_number` | String | 10-digit National Provider Identifier | `1234567890` |
| `primary_taxonomy` | String | Medical specialty taxonomy code | `207Q00000X` |
| `practice_name` | String | Name of practice/organization | `Johnson Family Medicine` |
| `address_street` | String | Street address | `123 Medical Center Dr` |
| `address_city` | String | City name | `San Francisco` |
| `address_state` | String | 2-letter state code | `CA` |
| `address_zip` | String | ZIP/postal code | `94102` |
| `place_id` | String | Google Places API place ID | `ChIJ1234567890abcdef` |
| `phone_primary` | String | Primary phone number | `415-555-0123` |
| `phone_alt` | String | Alternative phone number | `415-555-0124` |
| `email` | String | Primary email address | `sarah.johnson@example.com` |
| `license_number` | String | Medical license number | `A123456` |
| `license_state` | String | State where license issued | `CA` |
| `license_status` | String | License status | `active` |
| `last_validated_at` | DateTime | Last validation timestamp | `2024-01-15 10:30:00` |
| `validated_by` | String | Validation agent ID | `validation_agent_001` |
| `overall_confidence` | Float | Overall confidence score (0-1) | `0.85` |
| `created_at` | DateTime | Record creation timestamp | `2024-01-15 08:00:00` |
| `updated_at` | DateTime | Last update timestamp | `2024-01-15 10:30:00` |

## 🚨 Deliberate Error Patterns

The dataset includes 10 distinct error patterns, each representing 10% of the data (20 records each):

### 1. Perfect Providers (20 records - 10%)
- **Pattern**: No errors, high confidence scores
- **Use Case**: Testing successful validation scenarios
- **Characteristics**:
  - Valid NPI numbers with proper checksum
  - Realistic phone numbers and email addresses
  - Active licenses with proper formatting
  - High confidence scores (0.7-1.0)

### 2. Wrong Phone Numbers (20 records - 10%)
- **Pattern**: Invalid or placeholder phone numbers
- **Examples**: `555-000-0000`, `123-456-7890`, `000-000-0000`
- **Use Case**: Testing phone validation logic
- **Characteristics**:
  - Invalid phone number formats
  - Placeholder/test numbers
  - Confidence scores: 0.4-0.7

### 3. Invalid Email Addresses (20 records - 10%)
- **Pattern**: Malformed email addresses
- **Examples**: `invalid-email`, `test@`, `@domain.com`, `test@domain`
- **Use Case**: Testing email validation logic
- **Characteristics**:
  - Missing @ symbols or domains
  - Invalid characters or formatting
  - Confidence scores: 0.5-0.8

### 4. Expired Licenses (20 records - 10%)
- **Pattern**: License status marked as expired
- **Use Case**: Testing license status validation
- **Characteristics**:
  - `license_status` = "expired"
  - Confidence scores: 0.3-0.6
  - Valid license numbers but expired status

### 5. Fake NPI Numbers (20 records - 10%)
- **Pattern**: Invalid NPI numbers
- **Examples**: `0000000000`, `1111111111`, `9999999999`
- **Use Case**: Testing NPI validation against registry
- **Characteristics**:
  - Invalid NPI formats or checksums
  - Confidence scores: 0.2-0.5
  - Will fail NPI Registry API validation

### 6. Moved Addresses (20 records - 10%)
- **Pattern**: Addresses marked as moved
- **Use Case**: Testing address validation and change detection
- **Characteristics**:
  - Address street includes "(MOVED)" indicator
  - Confidence scores: 0.4-0.7
  - Valid addresses but marked as outdated

### 7. Missing License Information (20 records - 10%)
- **Pattern**: Empty license fields
- **Use Case**: Testing required field validation
- **Characteristics**:
  - Empty `license_number` and `license_status`
  - Confidence scores: 0.3-0.6
  - Missing critical credentialing information

### 8. Duplicate Providers (20 records - 10%)
- **Pattern**: Duplicate NPI numbers
- **Use Case**: Testing duplicate detection logic
- **Characteristics**:
  - NPI numbers prefixed with "DUPLICATE_"
  - Confidence scores: 0.1-0.4
  - Will trigger duplicate detection alerts

### 9. Suspended Licenses (20 records - 10%)
- **Pattern**: License status marked as suspended
- **Use Case**: Testing license status validation
- **Characteristics**:
  - `license_status` = "suspended"
  - Confidence scores: 0.2-0.5
  - Valid license numbers but suspended status

### 10. Mixed Errors (20 records - 10%)
- **Pattern**: Combination of multiple error types
- **Use Case**: Testing complex validation scenarios
- **Characteristics**:
  - Multiple validation issues per provider
  - Confidence scores: 0.2-0.6
  - Real-world complexity simulation

## 📄 Synthetic PDF Images

### Image Specifications
- **Count**: 20 images
- **Format**: PNG (800x1000 pixels)
- **Directory**: `pdf_images/`
- **Metadata**: `pdf_images/metadata.json`

### Form Templates
The images represent 5 different form types:
1. **Provider Application Form v1** - Basic provider enrollment
2. **Medical License Application v2** - License application process
3. **Credentialing Application v3** - Healthcare credentialing
4. **Provider Enrollment Form v4** - Insurance enrollment
5. **Physician Registration Form v5** - Medical board registration

### Realistic Features
Each image includes:
- **Handwriting Simulation**: Text with slight variations and imperfections
- **Scanning Artifacts**: Noise, spots, and scanning imperfections
- **Age Marks**: Coffee stains, creases, and wear patterns
- **Form Layouts**: Diverse field arrangements and templates
- **Sample Data**: Realistic provider information filled in fields

### Field Types
Forms contain various field types:
- **Text Fields**: Names, addresses, specialties
- **Date Fields**: Birth dates, license dates
- **Contact Fields**: Phone numbers, email addresses
- **Signature Fields**: Provider signatures
- **Checkboxes**: Yes/no selections
- **Long Text**: Descriptions, comments

## 🔧 Usage Examples

### Loading CSV Data
```python
import pandas as pd

# Load provider data
providers_df = pd.read_csv('demo_providers.csv')

# Filter by error type
perfect_providers = providers_df[providers_df['overall_confidence'] > 0.8]
error_providers = providers_df[providers_df['overall_confidence'] < 0.5]

# Analyze error patterns
error_counts = providers_df.groupby('license_status').size()
```

### Processing PDF Images
```python
from PIL import Image
import os

# Load PDF images
pdf_dir = 'pdf_images/'
for filename in os.listdir(pdf_dir):
    if filename.endswith('.png'):
        image = Image.open(os.path.join(pdf_dir, filename))
        # Process image for OCR or validation
```

### Validation Testing
```python
# Test different validation scenarios
def test_phone_validation(phone):
    return phone not in ['555-000-0000', '123-456-7890', '000-000-0000']

def test_email_validation(email):
    return '@' in email and '.' in email.split('@')[1]

def test_npi_validation(npi):
    return len(npi) == 10 and npi.isdigit() and npi not in ['0000000000', '1111111111']
```

## 📈 Data Statistics

### Provider Distribution
- **Total Records**: 200
- **States Covered**: 50 US states
- **Specialties**: 20 different medical specialties
- **Confidence Range**: 0.1 - 1.0
- **Validation Status**: Mixed (valid, invalid, warnings)

### Error Pattern Distribution
| Error Type | Count | Percentage | Confidence Range |
|------------|-------|------------|------------------|
| Perfect Providers | 20 | 10.0% | 0.7 - 1.0 |
| Wrong Phone | 20 | 10.0% | 0.4 - 0.7 |
| Invalid Email | 20 | 10.0% | 0.5 - 0.8 |
| Expired License | 20 | 10.0% | 0.3 - 0.6 |
| Fake NPI | 20 | 10.0% | 0.2 - 0.5 |
| Moved Address | 20 | 10.0% | 0.4 - 0.7 |
| Missing License | 20 | 10.0% | 0.3 - 0.6 |
| Duplicate Provider | 20 | 10.0% | 0.1 - 0.4 |
| Suspended License | 20 | 10.0% | 0.2 - 0.5 |
| Mixed Errors | 20 | 10.0% | 0.2 - 0.6 |

### PDF Image Statistics
- **Total Images**: 20
- **Form Templates**: 5 different layouts
- **Average Fields per Form**: 12
- **Handwriting Styles**: 4 different simulations
- **Data Quality**: Mixed (good, fair, poor)

## 🧪 Testing Scenarios

### 1. Validation Accuracy Testing
- **High Confidence**: Test providers with confidence > 0.8
- **Low Confidence**: Test providers with confidence < 0.5
- **Edge Cases**: Test boundary conditions and edge cases

### 2. Error Detection Testing
- **Phone Validation**: Test invalid phone number detection
- **Email Validation**: Test malformed email detection
- **License Validation**: Test expired/suspended license detection
- **NPI Validation**: Test fake NPI detection
- **Duplicate Detection**: Test duplicate provider identification

### 3. Document Processing Testing
- **OCR Accuracy**: Test text extraction from PDF images
- **Form Recognition**: Test different form layout recognition
- **Handwriting Recognition**: Test handwriting-style text processing
- **Noise Handling**: Test processing of scanned documents with artifacts

### 4. Performance Testing
- **Bulk Processing**: Test processing of all 200 providers
- **Batch Validation**: Test validation job performance
- **Memory Usage**: Test memory consumption with large datasets
- **Processing Time**: Test validation speed and efficiency

## 🔄 Regenerating Data

To regenerate the demo data:

```bash
# Regenerate CSV data
python generate_demo_csv.py

# Regenerate PDF images
python generate_pdf_images.py
```

Both scripts will create fresh data with different random values while maintaining the same error patterns and distributions.

## 📝 Notes

- **PII Compliance**: All data is synthetic and contains no real personal information
- **Reproducibility**: Generation scripts use fixed seeds for consistent results
- **Extensibility**: Easy to add new error patterns or form templates
- **Realism**: Data patterns based on real-world healthcare provider validation issues
- **Coverage**: Comprehensive test coverage for all validation scenarios

This demo dataset provides a robust foundation for testing, development, and demonstration of the Provider Data Validation & Directory Management System.
