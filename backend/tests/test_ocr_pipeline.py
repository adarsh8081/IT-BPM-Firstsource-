"""
Tests for OCR Pipeline
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
import io
from PIL import Image
import json

from pipelines.ocr import (
    OCRPipeline, 
    OCRProvider, 
    DocumentType, 
    ExtractedField, 
    OCRResult
)


class TestOCRPipeline:
    """Test cases for OCR Pipeline"""

    @pytest.fixture
    def ocr_pipeline(self):
        """Create OCR pipeline instance for testing"""
        return OCRPipeline(provider=OCRProvider.TESSERACT)

    @pytest.fixture
    def sample_image_bytes(self):
        """Create sample image bytes for testing"""
        # Create a simple test image
        image = Image.new('RGB', (100, 100), color='white')
        img_bytes = io.BytesIO()
        image.save(img_bytes, format='PNG')
        return img_bytes.getvalue()

    @pytest.fixture
    def sample_pdf_bytes(self):
        """Create sample PDF bytes for testing"""
        # Create a simple PDF-like bytes (not a real PDF)
        return b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n'

    @pytest.fixture
    def sample_text(self):
        """Sample text for field extraction testing"""
        return """
        Dr. John Smith
        123 Main Street, Suite 100
        San Francisco, CA 94102
        (555) 123-4567
        john.smith@example.com
        License: A123456
        Specialty: Internal Medicine
        """

    def test_ocr_pipeline_initialization(self, ocr_pipeline):
        """Test OCR pipeline initialization"""
        assert ocr_pipeline.provider == OCRProvider.TESSERACT
        assert ocr_pipeline.field_patterns is not None
        assert "name" in ocr_pipeline.field_patterns
        assert "phone" in ocr_pipeline.field_patterns
        assert "license" in ocr_pipeline.field_patterns

    def test_detect_document_type_bytes(self, ocr_pipeline, sample_image_bytes, sample_pdf_bytes):
        """Test document type detection from bytes"""
        # Test PDF detection
        pdf_type = ocr_pipeline._detect_document_type(sample_pdf_bytes)
        assert pdf_type == DocumentType.PDF
        
        # Test image detection
        image_type = ocr_pipeline._detect_document_type(sample_image_bytes)
        assert image_type == DocumentType.IMAGE
        
        # Test unknown type
        unknown_bytes = b"unknown content"
        unknown_type = ocr_pipeline._detect_document_type(unknown_bytes)
        assert unknown_type == DocumentType.UNKNOWN

    def test_detect_document_type_path(self, ocr_pipeline):
        """Test document type detection from file path"""
        # Test PDF path
        pdf_type = ocr_pipeline._detect_document_type("test.pdf")
        assert pdf_type == DocumentType.PDF
        
        # Test image paths
        jpg_type = ocr_pipeline._detect_document_type("test.jpg")
        assert jpg_type == DocumentType.IMAGE
        
        png_type = ocr_pipeline._detect_document_type("test.png")
        assert png_type == DocumentType.IMAGE
        
        # Test unknown extension
        unknown_type = ocr_pipeline._detect_document_type("test.xyz")
        assert unknown_type == DocumentType.UNKNOWN

    def test_clean_text(self, ocr_pipeline):
        """Test text cleaning functionality"""
        dirty_text = "  This   is   a    test   text  with  \n\n\n  extra  spaces  "
        cleaned = ocr_pipeline._clean_text(dirty_text)
        assert cleaned == "This is a test text with extra spaces"
        
        # Test OCR error correction
        ocr_text = "Dr. |ohn Sm|th"
        cleaned = ocr_pipeline._clean_text(ocr_text)
        assert "I" in cleaned  # | should be replaced with I

    def test_clean_field_value(self, ocr_pipeline):
        """Test field value cleaning"""
        dirty_value = "  Dr. John Smith!!!  "
        cleaned = ocr_pipeline._clean_field_value(dirty_value)
        assert cleaned == "Dr. John Smith"
        
        # Test with special characters
        special_value = "john@example.com#$%"
        cleaned = ocr_pipeline._clean_field_value(special_value)
        assert cleaned == "john@example.com"

    def test_calculate_field_confidence(self, ocr_pipeline):
        """Test field confidence calculation"""
        # Test phone number confidence
        phone_confidence = ocr_pipeline._calculate_field_confidence(
            "phone", "(555) 123-4567", r"(\([0-9]{3}\)\s*[0-9]{3}-[0-9]{4})"
        )
        assert phone_confidence > 0.9
        
        # Test email confidence
        email_confidence = ocr_pipeline._calculate_field_confidence(
            "email", "john@example.com", r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"
        )
        assert email_confidence > 0.9
        
        # Test license confidence
        license_confidence = ocr_pipeline._calculate_field_confidence(
            "license", "A123456", r"([A-Z0-9\-]+)"
        )
        assert license_confidence > 0.8
        
        # Test name confidence
        name_confidence = ocr_pipeline._calculate_field_confidence(
            "name", "Dr. John Smith", r"([A-Za-z\s.,]+)"
        )
        assert name_confidence > 0.8

    def test_extract_fields(self, ocr_pipeline, sample_text):
        """Test field extraction from text"""
        fields = ocr_pipeline._extract_fields(sample_text, 1)
        
        # Check that fields were extracted
        field_names = [field.field_name for field in fields]
        assert "name" in field_names
        assert "phone" in field_names
        assert "license" in field_names
        assert "email" in field_names
        
        # Check specific field values
        name_field = next((f for f in fields if f.field_name == "name"), None)
        assert name_field is not None
        assert "John Smith" in name_field.field_value
        
        phone_field = next((f for f in fields if f.field_name == "phone"), None)
        assert phone_field is not None
        assert "555" in phone_field.field_value

    def test_calculate_confidence_score(self, ocr_pipeline):
        """Test overall confidence score calculation"""
        # Test with good text and fields
        good_text = ["This is a long text with good content"]
        good_fields = [
            ExtractedField("name", "Dr. John Smith", 0.9),
            ExtractedField("phone", "(555) 123-4567", 0.95)
        ]
        
        confidence = ocr_pipeline._calculate_confidence_score(good_text, good_fields)
        assert confidence > 0.8
        
        # Test with poor text and fields
        poor_text = ["Short"]
        poor_fields = [
            ExtractedField("name", "X", 0.5)
        ]
        
        confidence = ocr_pipeline._calculate_confidence_score(poor_text, poor_fields)
        assert confidence < 0.8

    def test_preprocess_image(self, ocr_pipeline):
        """Test image preprocessing"""
        # Create a test image
        image = Image.new('RGB', (100, 100), color='white')
        
        # Test preprocessing
        processed = ocr_pipeline._preprocess_image(image)
        
        # Should be grayscale after preprocessing
        assert processed.mode == 'L'
        assert processed.size == (100, 100)

    def test_get_supported_formats(self, ocr_pipeline):
        """Test supported formats list"""
        formats = ocr_pipeline.get_supported_formats()
        
        assert '.pdf' in formats
        assert '.jpg' in formats
        assert '.png' in formats
        assert '.tiff' in formats

    def test_get_field_patterns(self, ocr_pipeline):
        """Test field patterns retrieval"""
        patterns = ocr_pipeline.get_field_patterns()
        
        assert "name" in patterns
        assert "phone" in patterns
        assert "license" in patterns
        assert "email" in patterns
        assert "address" in patterns
        assert "specialty" in patterns

    def test_add_field_pattern(self, ocr_pipeline):
        """Test adding custom field patterns"""
        # Add custom pattern
        ocr_pipeline.add_field_pattern("custom_field", r"custom\s+pattern")
        
        # Check that pattern was added
        patterns = ocr_pipeline.get_field_patterns()
        assert "custom_field" in patterns
        assert r"custom\s+pattern" in patterns["custom_field"]

    def test_switch_provider(self, ocr_pipeline):
        """Test provider switching"""
        # Test switching to Google Document AI (mock)
        with patch.object(ocr_pipeline, '_initialize_provider'):
            ocr_pipeline.switch_provider(OCRProvider.GOOGLE_DOCUMENT_AI)
            assert ocr_pipeline.provider == OCRProvider.GOOGLE_DOCUMENT_AI

    @pytest.mark.asyncio
    async def test_extract_text_success(self, ocr_pipeline, sample_image_bytes):
        """Test successful text extraction"""
        with patch.object(ocr_pipeline, '_process_image') as mock_process:
            mock_result = OCRResult(
                success=True,
                raw_text="Sample text",
                extracted_fields=[],
                document_type=DocumentType.IMAGE,
                page_count=1,
                processing_time=1.0,
                provider=OCRProvider.TESSERACT,
                confidence_score=0.8
            )
            mock_process.return_value = mock_result
            
            result = await ocr_pipeline.extract_text(sample_image_bytes)
            
            assert result.success == True
            assert result.raw_text == "Sample text"
            assert result.document_type == DocumentType.IMAGE

    @pytest.mark.asyncio
    async def test_extract_text_failure(self, ocr_pipeline):
        """Test text extraction failure"""
        with patch.object(ocr_pipeline, '_detect_document_type', return_value=DocumentType.UNKNOWN):
            result = await ocr_pipeline.extract_text("invalid.xyz")
            
            assert result.success == False
            assert "Unsupported document type" in result.error_message

    @pytest.mark.asyncio
    async def test_extract_text_exception(self, ocr_pipeline, sample_image_bytes):
        """Test text extraction with exception"""
        with patch.object(ocr_pipeline, '_process_image', side_effect=Exception("Processing error")):
            result = await ocr_pipeline.extract_text(sample_image_bytes)
            
            assert result.success == False
            assert "Processing error" in result.error_message

    @pytest.mark.asyncio
    async def test_process_image_tesseract(self, ocr_pipeline, sample_image_bytes):
        """Test image processing with Tesseract"""
        with patch('pytesseract.image_to_string', return_value="Sample text"):
            with patch.object(ocr_pipeline, '_preprocess_image') as mock_preprocess:
                mock_image = Image.new('RGB', (100, 100), color='white')
                mock_preprocess.return_value = mock_image
                
                result = await ocr_pipeline._process_image_tesseract(sample_image_bytes, datetime.now())
                
                assert result.success == True
                assert result.raw_text == "Sample text"
                assert result.document_type == DocumentType.IMAGE

    @pytest.mark.asyncio
    async def test_process_image_tesseract_failure(self, ocr_pipeline, sample_image_bytes):
        """Test image processing failure with Tesseract"""
        with patch('pytesseract.image_to_string', side_effect=Exception("Tesseract error")):
            result = await ocr_pipeline._process_image_tesseract(sample_image_bytes, datetime.now())
            
            assert result.success == False
            assert "Tesseract error" in result.error_message

    @pytest.mark.asyncio
    async def test_extract_text_tesseract(self, ocr_pipeline):
        """Test text extraction with Tesseract"""
        with patch('pytesseract.image_to_string', return_value="Sample text"):
            image = Image.new('RGB', (100, 100), color='white')
            text = await ocr_pipeline._extract_text_tesseract(image)
            
            assert text == "Sample text"

    @pytest.mark.asyncio
    async def test_extract_text_tesseract_failure(self, ocr_pipeline):
        """Test text extraction failure with Tesseract"""
        with patch('pytesseract.image_to_string', side_effect=Exception("Tesseract error")):
            image = Image.new('RGB', (100, 100), color='white')
            text = await ocr_pipeline._extract_text_tesseract(image)
            
            assert text == ""

    def test_extract_fields_google(self, ocr_pipeline):
        """Test field extraction from Google Document AI result"""
        # Mock Google Document AI document
        mock_document = MagicMock()
        mock_document.text = "Dr. John Smith (555) 123-4567 john@example.com"
        mock_document.entities = []
        
        fields = ocr_pipeline._extract_fields_google(mock_document)
        
        # Should extract fields using regex patterns
        field_names = [field.field_name for field in fields]
        assert "name" in field_names
        assert "phone" in field_names
        assert "email" in field_names

    @pytest.mark.asyncio
    async def test_process_pdf_google(self, ocr_pipeline, sample_pdf_bytes):
        """Test PDF processing with Google Document AI"""
        # Mock Google Document AI client and response
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_document = MagicMock()
        mock_document.text = "Sample PDF text"
        mock_document.pages = [MagicMock(), MagicMock()]  # 2 pages
        mock_result.document = mock_document
        
        with patch('pipelines.ocr.documentai.DocumentProcessorServiceClient', return_value=mock_client):
            with patch.object(mock_client, 'process_document', return_value=mock_result):
                result = await ocr_pipeline._process_pdf_google(sample_pdf_bytes, datetime.now())
                
                assert result.success == True
                assert result.raw_text == "Sample PDF text"
                assert result.page_count == 2

    @pytest.mark.asyncio
    async def test_process_image_google(self, ocr_pipeline, sample_image_bytes):
        """Test image processing with Google Document AI"""
        # Mock Google Document AI client and response
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_document = MagicMock()
        mock_document.text = "Sample image text"
        mock_document.pages = [MagicMock()]  # 1 page
        mock_result.document = mock_document
        
        with patch('pipelines.ocr.documentai.DocumentProcessorServiceClient', return_value=mock_client):
            with patch.object(mock_client, 'process_document', return_value=mock_result):
                result = await ocr_pipeline._process_image_google(sample_image_bytes, datetime.now())
                
                assert result.success == True
                assert result.raw_text == "Sample image text"
                assert result.page_count == 1

    def test_google_document_ai_initialization(self):
        """Test Google Document AI initialization"""
        with patch('pipelines.ocr.GOOGLE_DOCUMENT_AI_AVAILABLE', True):
            with patch('pipelines.ocr.documentai'):
                pipeline = OCRPipeline(provider=OCRProvider.GOOGLE_DOCUMENT_AI)
                assert pipeline.provider == OCRProvider.GOOGLE_DOCUMENT_AI

    def test_google_document_ai_not_available(self):
        """Test Google Document AI not available"""
        with patch('pipelines.ocr.GOOGLE_DOCUMENT_AI_AVAILABLE', False):
            with pytest.raises(RuntimeError, match="Google Document AI not available"):
                OCRPipeline(provider=OCRProvider.GOOGLE_DOCUMENT_AI)

    def test_tesseract_not_available(self):
        """Test Tesseract not available"""
        with patch('pytesseract.get_tesseract_version', side_effect=Exception("Tesseract not found")):
            with pytest.raises(RuntimeError, match="Tesseract OCR not available"):
                OCRPipeline(provider=OCRProvider.TESSERACT)

    def test_unsupported_provider(self, ocr_pipeline, sample_image_bytes):
        """Test unsupported provider"""
        ocr_pipeline.provider = "unsupported_provider"
        
        with pytest.raises(ValueError, match="Unsupported provider"):
            asyncio.run(ocr_pipeline._process_image(sample_image_bytes, datetime.now()))

    def test_field_extraction_edge_cases(self, ocr_pipeline):
        """Test field extraction edge cases"""
        # Test empty text
        fields = ocr_pipeline._extract_fields("", 1)
        assert len(fields) == 0
        
        # Test text with no matches
        fields = ocr_pipeline._extract_fields("No relevant information here", 1)
        assert len(fields) == 0
        
        # Test text with multiple matches (should take first)
        text_with_multiple = """
        Name: Dr. John Smith
        Physician: Dr. Jane Doe
        """
        fields = ocr_pipeline._extract_fields(text_with_multiple, 1)
        name_fields = [f for f in fields if f.field_name == "name"]
        assert len(name_fields) == 1  # Should only take first match

    def test_confidence_score_edge_cases(self, ocr_pipeline):
        """Test confidence score edge cases"""
        # Test with empty inputs
        confidence = ocr_pipeline._calculate_confidence_score([], [])
        assert confidence == 0.0
        
        # Test with only text
        confidence = ocr_pipeline._calculate_confidence_score(["Some text"], [])
        assert confidence > 0.0
        
        # Test with only fields
        confidence = ocr_pipeline._calculate_confidence_score([], [
            ExtractedField("name", "Dr. John Smith", 0.9)
        ])
        assert confidence > 0.0

    def test_ocr_result_serialization(self):
        """Test OCR result serialization"""
        result = OCRResult(
            success=True,
            raw_text="Sample text",
            extracted_fields=[
                ExtractedField("name", "Dr. John Smith", 0.9, page_number=1)
            ],
            document_type=DocumentType.IMAGE,
            page_count=1,
            processing_time=1.5,
            provider=OCRProvider.TESSERACT,
            confidence_score=0.85
        )
        
        # Test that result can be converted to dict
        result_dict = {
            "success": result.success,
            "raw_text": result.raw_text,
            "extracted_fields": [
                {
                    "field_name": field.field_name,
                    "field_value": field.field_value,
                    "confidence": field.confidence,
                    "page_number": field.page_number
                }
                for field in result.extracted_fields
            ],
            "document_type": result.document_type.value,
            "page_count": result.page_count,
            "processing_time": result.processing_time,
            "provider": result.provider.value,
            "confidence_score": result.confidence_score
        }
        
        # Test JSON serialization
        json_str = json.dumps(result_dict)
        assert "Dr. John Smith" in json_str
        assert "tesseract" in json_str


if __name__ == "__main__":
    # Run basic tests
    pytest.main([__file__, "-v"])
