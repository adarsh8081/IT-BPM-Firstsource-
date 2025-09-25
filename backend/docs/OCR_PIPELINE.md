# OCR Pipeline Documentation

## Overview

The OCR Pipeline provides comprehensive text extraction and structured field extraction from PDFs and images using Tesseract or Google Document AI. It supports switching between providers and includes advanced features like image preprocessing, confidence scoring, and custom field patterns.

## Features

- **Dual OCR Providers**: Tesseract (free, local) and Google Document AI (cloud, high accuracy)
- **Document Type Detection**: Automatic detection of PDF and image formats
- **Structured Field Extraction**: Extract specific fields like name, address, phone, license
- **Image Preprocessing**: Enhance image quality for better OCR results
- **Confidence Scoring**: Assess extraction quality with confidence scores
- **Custom Patterns**: Add custom field extraction patterns
- **Provider Switching**: Switch between OCR providers at runtime
- **Async Processing**: Non-blocking document processing
- **Error Handling**: Comprehensive error handling and validation

## Installation

### Tesseract OCR

```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# macOS
brew install tesseract

# Windows
# Download from: https://github.com/tesseract-ocr/tesseract
```

### Python Dependencies

```bash
pip install pytesseract pillow PyMuPDF

# For Google Document AI (optional)
pip install google-cloud-documentai
```

## Usage

### Basic Text Extraction

```python
import asyncio
from pipelines.ocr import OCRPipeline, OCRProvider

async def extract_text():
    # Initialize OCR pipeline
    ocr_pipeline = OCRPipeline(provider=OCRProvider.TESSERACT)
    
    # Extract text from document
    result = await ocr_pipeline.extract_text("document.pdf")
    
    if result.success:
        print(f"Raw text: {result.raw_text}")
        print(f"Confidence: {result.confidence_score:.2f}")
        print(f"Processing time: {result.processing_time:.2f}s")
        
        # Show extracted fields
        for field in result.extracted_fields:
            print(f"{field.field_name}: {field.field_value}")
    else:
        print(f"Error: {result.error_message}")

# Run the example
asyncio.run(extract_text())
```

### Provider Switching

```python
async def switch_providers():
    # Start with Tesseract
    ocr_pipeline = OCRPipeline(provider=OCRProvider.TESSERACT)
    
    # Process with Tesseract
    result1 = await ocr_pipeline.extract_text("document.pdf")
    print(f"Tesseract confidence: {result1.confidence_score:.2f}")
    
    # Switch to Google Document AI
    ocr_pipeline.switch_provider(OCRProvider.GOOGLE_DOCUMENT_AI)
    
    # Process with Google Document AI
    result2 = await ocr_pipeline.extract_text("document.pdf")
    print(f"Google Document AI confidence: {result2.confidence_score:.2f}")

asyncio.run(switch_providers())
```

### Custom Field Patterns

```python
async def custom_patterns():
    ocr_pipeline = OCRPipeline(provider=OCRProvider.TESSERACT)
    
    # Add custom field patterns
    ocr_pipeline.add_field_pattern("npi", r"(?i)(?:npi|national provider identifier)[\s:]*([0-9]{10})")
    ocr_pipeline.add_field_pattern("dea", r"(?i)(?:dea|dea number)[\s:]*([A-Z]{2}[0-9]{7})")
    
    # Extract with custom patterns
    result = await ocr_pipeline.extract_text("provider_form.pdf")
    
    # Check for custom fields
    for field in result.extracted_fields:
        if field.field_name in ["npi", "dea"]:
            print(f"Custom field {field.field_name}: {field.field_value}")

asyncio.run(custom_patterns())
```

## API Reference

### OCRPipeline Class

#### Constructor

```python
OCRPipeline(provider: OCRProvider = OCRProvider.TESSERACT)
```

- `provider`: OCR provider to use (TESSERACT or GOOGLE_DOCUMENT_AI)

#### Methods

##### `extract_text(document_path: Union[str, Path, bytes]) -> OCRResult`

Extract text and structured fields from document.

**Parameters:**
- `document_path`: Path to document, Path object, or document bytes

**Returns:**
- `OCRResult`: Contains success status, extracted text, fields, and metadata

**Example:**
```python
result = await ocr_pipeline.extract_text("document.pdf")
```

##### `switch_provider(new_provider: OCRProvider) -> None`

Switch OCR provider at runtime.

**Parameters:**
- `new_provider`: New OCR provider to use

**Example:**
```python
ocr_pipeline.switch_provider(OCRProvider.GOOGLE_DOCUMENT_AI)
```

##### `add_field_pattern(field_name: str, pattern: str) -> None`

Add custom field extraction pattern.

**Parameters:**
- `field_name`: Name of the field to extract
- `pattern`: Regex pattern for field extraction

**Example:**
```python
ocr_pipeline.add_field_pattern("npi", r"(?i)npi[\s:]*([0-9]{10})")
```

##### `get_supported_formats() -> List[str]`

Get list of supported document formats.

**Returns:**
- List of supported file extensions

**Example:**
```python
formats = ocr_pipeline.get_supported_formats()
# Returns: ['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.gif']
```

##### `get_field_patterns() -> Dict[str, List[str]]`

Get current field extraction patterns.

**Returns:**
- Dictionary of field names and their regex patterns

**Example:**
```python
patterns = ocr_pipeline.get_field_patterns()
# Returns: {'name': [r'(?i)(?:name|physician)[\s:]*([A-Za-z\s.,]+)', ...], ...}
```

### OCRResult Class

#### Properties

```python
@dataclass
class OCRResult:
    success: bool                                    # Whether extraction was successful
    raw_text: str                                   # Extracted raw text
    extracted_fields: List[ExtractedField]          # Structured fields
    document_type: DocumentType                     # Document type (PDF/IMAGE)
    page_count: int                                 # Number of pages
    processing_time: float                          # Processing time in seconds
    provider: OCRProvider                          # OCR provider used
    confidence_score: float                        # Overall confidence score
    error_message: Optional[str] = None            # Error message if failed
    metadata: Optional[Dict[str, Any]] = None      # Additional metadata
```

### ExtractedField Class

#### Properties

```python
@dataclass
class ExtractedField:
    field_name: str                                # Name of the field
    field_value: str                               # Extracted value
    confidence: float                              # Field confidence score
    bounding_box: Optional[Dict[str, float]] = None # Bounding box coordinates
    page_number: Optional[int] = None              # Page number where field was found
```

## Supported Document Formats

| Format | Extension | Description |
|--------|-----------|-------------|
| PDF | `.pdf` | Portable Document Format |
| JPEG | `.jpg`, `.jpeg` | JPEG Image |
| PNG | `.png` | Portable Network Graphics |
| TIFF | `.tiff` | Tagged Image File Format |
| BMP | `.bmp` | Bitmap Image |
| GIF | `.gif` | Graphics Interchange Format |

## Field Extraction Patterns

### Built-in Fields

The pipeline includes built-in patterns for common healthcare provider fields:

#### Name Patterns
```python
name_patterns = [
    r"(?i)(?:name|physician|doctor|provider)[\s:]*([A-Za-z\s.,]+)",
    r"(?i)^([A-Za-z\s.,]+)(?:\s*MD|\s*DO|\s*Dr\.?)",
    r"(?i)Dr\.?\s*([A-Za-z\s.,]+)"
]
```

#### Phone Patterns
```python
phone_patterns = [
    r"(?i)(?:phone|telephone|tel)[\s:]*([0-9\-\(\)\s\+\.]+)",
    r"(\([0-9]{3}\)\s*[0-9]{3}-[0-9]{4})",
    r"([0-9]{3}-[0-9]{3}-[0-9]{4})",
    r"([0-9]{3}\.[0-9]{3}\.[0-9]{4})"
]
```

#### License Patterns
```python
license_patterns = [
    r"(?i)(?:license|lic\.?|license number)[\s:]*([A-Z0-9\-]+)",
    r"(?i)(?:medical license|physician license)[\s:]*([A-Z0-9\-]+)",
    r"(?i)(?:npi|national provider identifier)[\s:]*([0-9]{10})"
]
```

#### Email Patterns
```python
email_patterns = [
    r"(?i)(?:email|e-mail)[\s:]*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
    r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"
]
```

#### Address Patterns
```python
address_patterns = [
    r"(?i)(?:address|location)[\s:]*([0-9]+\s+[A-Za-z0-9\s.,-]+)",
    r"([0-9]+\s+[A-Za-z0-9\s.,-]+(?:\s+St|Street|Ave|Avenue|Rd|Road|Blvd|Boulevard|Dr|Drive))"
]
```

#### Specialty Patterns
```python
specialty_patterns = [
    r"(?i)(?:specialty|specialization|practice area)[\s:]*([A-Za-z\s&,-]+)",
    r"(?i)(?:board certified|certification)[\s:]*([A-Za-z\s&,-]+)"
]
```

### Custom Field Patterns

Add custom patterns for specific document types:

```python
# Add NPI pattern
ocr_pipeline.add_field_pattern("npi", r"(?i)(?:npi|national provider identifier)[\s:]*([0-9]{10})")

# Add DEA number pattern
ocr_pipeline.add_field_pattern("dea", r"(?i)(?:dea|dea number)[\s:]*([A-Z]{2}[0-9]{7})")

# Add hospital affiliation pattern
ocr_pipeline.add_field_pattern("hospital", r"(?i)(?:hospital|medical center|clinic)[\s:]*([A-Za-z\s&,-]+)")
```

## OCR Providers

### Tesseract OCR

**Advantages:**
- Free and open source
- Local processing (no internet required)
- Supports multiple languages
- Good for basic text extraction

**Disadvantages:**
- Requires system installation
- Accuracy depends on image quality
- Limited structured field extraction

**Configuration:**
```python
# Tesseract configuration
config = '--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,()[]{}:;!?@#$%^&*+-=/\\|"\'<>~`_ '
```

### Google Document AI

**Advantages:**
- High accuracy for structured documents
- Excellent field extraction capabilities
- Handles complex layouts
- Built-in document understanding

**Disadvantages:**
- Requires Google Cloud setup
- Internet connection required
- Pay-per-use pricing
- Data sent to Google servers

**Configuration:**
```python
# Google Document AI configuration
project_id = "your-project-id"
location = "us"
processor_id = "your-processor-id"
```

## Image Preprocessing

The pipeline includes automatic image preprocessing to improve OCR accuracy:

### Preprocessing Steps

1. **Grayscale Conversion**: Convert to grayscale for better contrast
2. **Contrast Enhancement**: Increase contrast by 2x
3. **Sharpness Enhancement**: Increase sharpness by 2x
4. **Noise Reduction**: Apply median filter to reduce noise

### Custom Preprocessing

```python
def custom_preprocess_image(image: Image.Image) -> Image.Image:
    # Custom preprocessing logic
    image = image.convert('L')  # Grayscale
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(3.0)  # Higher contrast
    return image

# Apply custom preprocessing
processed_image = custom_preprocess_image(original_image)
```

## Confidence Scoring

### Field Confidence Calculation

Confidence scores are calculated based on:

1. **Pattern Match Quality**: How well the extracted text matches the pattern
2. **Field Type Validation**: Format validation for specific field types
3. **Pattern Complexity**: More specific patterns get higher confidence

### Confidence Score Examples

| Field Type | High Confidence | Medium Confidence | Low Confidence |
|------------|----------------|-------------------|----------------|
| Phone | `(555) 123-4567` | `555-123-4567` | `5551234567` |
| Email | `john@example.com` | `john@example` | `john@` |
| License | `A123456` | `A123` | `123` |
| Name | `Dr. John Smith` | `John Smith` | `J. Smith` |

### Overall Confidence Score

The overall confidence score combines:
- Text quality assessment
- Field extraction success rate
- Individual field confidence scores

```python
# Confidence score calculation
text_confidence = 0.8  # Based on text length and quality
field_confidence = 0.9  # Average of field confidences
overall_confidence = (text_confidence + field_confidence) / 2  # 0.85
```

## Error Handling

### Common Error Scenarios

1. **Document Type Not Supported**
   ```python
   result = await ocr_pipeline.extract_text("document.xyz")
   # result.success = False
   # result.error_message = "Unsupported document type"
   ```

2. **OCR Processing Failed**
   ```python
   result = await ocr_pipeline.extract_text("corrupted.pdf")
   # result.success = False
   # result.error_message = "OCR processing failed: [specific error]"
   ```

3. **Provider Not Available**
   ```python
   # Tesseract not installed
   OCRPipeline(provider=OCRProvider.TESSERACT)
   # Raises RuntimeError: "Tesseract OCR not available"
   ```

4. **Google Document AI Setup Required**
   ```python
   # Google Document AI not configured
   OCRPipeline(provider=OCRProvider.GOOGLE_DOCUMENT_AI)
   # Raises RuntimeError: "Google Document AI not available"
   ```

### Error Recovery

The pipeline includes automatic error recovery:

- **Retry Logic**: Automatic retry for transient failures
- **Fallback Providers**: Switch to alternative provider if available
- **Graceful Degradation**: Return partial results when possible

## Testing

### Unit Tests

```bash
# Run OCR pipeline tests
pytest backend/tests/test_ocr_pipeline.py -v

# Run with coverage
pytest backend/tests/test_ocr_pipeline.py --cov=pipelines.ocr

# Run specific test
pytest backend/tests/test_ocr_pipeline.py::TestOCRPipeline::test_extract_text_success -v
```

### Integration Tests

```bash
# Test with real documents
pytest backend/tests/test_ocr_pipeline.py -m integration

# Test provider switching
pytest backend/tests/test_ocr_pipeline.py -k "provider"
```

### Mock Testing

The tests include comprehensive mocking for:
- Tesseract OCR responses
- Google Document AI responses
- Image processing operations
- File I/O operations

## Performance Optimization

### Image Quality

1. **High Resolution**: Use high-resolution images (300+ DPI)
2. **Good Contrast**: Ensure good contrast between text and background
3. **Clean Images**: Remove noise and artifacts
4. **Proper Orientation**: Ensure text is right-side up

### Processing Speed

1. **Image Size**: Resize large images to reasonable dimensions
2. **Provider Selection**: Use Tesseract for simple documents, Google Document AI for complex ones
3. **Batch Processing**: Process multiple documents in parallel
4. **Caching**: Cache results for repeated processing

### Memory Usage

1. **Stream Processing**: Process large documents in chunks
2. **Image Cleanup**: Clean up image objects after processing
3. **Provider Switching**: Switch providers to balance accuracy and resource usage

## Best Practices

### Document Preparation

1. **Scan Quality**: Use high-quality scanning (300+ DPI)
2. **Format Consistency**: Use consistent document formats
3. **Field Layout**: Ensure fields are clearly labeled and positioned
4. **Handwriting**: Use printed text when possible

### Pattern Development

1. **Test Patterns**: Test patterns with sample documents
2. **Iterative Refinement**: Refine patterns based on results
3. **Documentation**: Document custom patterns for team use
4. **Validation**: Validate extracted fields for accuracy

### Error Handling

1. **Graceful Degradation**: Handle partial failures gracefully
2. **Logging**: Log errors for debugging and improvement
3. **Monitoring**: Monitor confidence scores and success rates
4. **Fallback Strategies**: Implement fallback strategies for critical fields

## Troubleshooting

### Common Issues

1. **Tesseract Not Found**
   ```bash
   # Install Tesseract
   sudo apt-get install tesseract-ocr  # Ubuntu/Debian
   brew install tesseract              # macOS
   ```

2. **Low OCR Accuracy**
   - Check image quality and resolution
   - Ensure good contrast and lighting
   - Remove noise and artifacts
   - Use appropriate preprocessing

3. **Field Extraction Issues**
   - Review and refine field patterns
   - Test patterns with sample documents
   - Consider document layout variations
   - Use custom patterns for specific fields

4. **Google Document AI Errors**
   - Verify project ID and processor ID
   - Check API credentials and permissions
   - Ensure proper billing setup
   - Monitor API quotas and limits

### Debugging Tips

1. **Enable Logging**: Set logging level to DEBUG for detailed output
2. **Test Patterns**: Use regex testing tools to validate patterns
3. **Sample Documents**: Keep sample documents for testing
4. **Confidence Monitoring**: Monitor confidence scores for quality assessment

## Related Documentation

- [Base Connector Documentation](BASE_CONNECTOR.md)
- [Provider Model Documentation](PROVIDER_MODEL.md)
- [NPI Connector Documentation](NPI_CONNECTOR.md)
- [Google Places Connector Documentation](GOOGLE_PLACES_CONNECTOR.md)
- [State Board Connector Documentation](STATE_BOARD_MOCK_CONNECTOR.md)
- [API Testing Guide](API_TESTING.md)
