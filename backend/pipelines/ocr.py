"""
OCR Pipeline for Document Text Extraction

This module provides OCR functionality to extract text and structured fields
from PDFs and images using Tesseract or Google Document AI with the ability
to switch between providers.
"""

import asyncio
import logging
import json
import base64
import io
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import re
from pathlib import Path

# OCR libraries
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import fitz  # PyMuPDF for PDF handling

# Google Document AI
try:
    from google.cloud import documentai
    from google.api_core import exceptions as gcp_exceptions
    GOOGLE_DOCUMENT_AI_AVAILABLE = True
except ImportError:
    GOOGLE_DOCUMENT_AI_AVAILABLE = False

# HTTP client for API calls
import httpx

logger = logging.getLogger(__name__)


class OCRProvider(Enum):
    """OCR provider enumeration"""
    TESSERACT = "tesseract"
    GOOGLE_DOCUMENT_AI = "google_document_ai"


class DocumentType(Enum):
    """Document type enumeration"""
    PDF = "pdf"
    IMAGE = "image"
    UNKNOWN = "unknown"


@dataclass
class ExtractedField:
    """Extracted field from document"""
    field_name: str
    field_value: str
    confidence: float
    bounding_box: Optional[Dict[str, float]] = None
    page_number: Optional[int] = None


@dataclass
class OCRResult:
    """OCR extraction result"""
    success: bool
    raw_text: str
    extracted_fields: List[ExtractedField]
    document_type: DocumentType
    page_count: int
    processing_time: float
    provider: OCRProvider
    confidence_score: float
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class OCRPipeline:
    """
    OCR Pipeline for document text extraction
    
    Supports both Tesseract and Google Document AI with the ability
    to switch between providers and extract structured fields.
    """
    
    def __init__(self, provider: OCRProvider = OCRProvider.TESSERACT):
        """
        Initialize OCR Pipeline
        
        Args:
            provider: OCR provider to use (TESSERACT or GOOGLE_DOCUMENT_AI)
        """
        self.provider = provider
        self.google_project_id = None
        self.google_location = None
        self.google_processor_id = None
        
        # Field extraction patterns
        self.field_patterns = {
            "name": [
                r"(?i)(?:name|physician|doctor|provider)[\s:]*([A-Za-z\s.,]+)",
                r"(?i)^([A-Za-z\s.,]+)(?:\s*MD|\s*DO|\s*Dr\.?)",
                r"(?i)Dr\.?\s*([A-Za-z\s.,]+)"
            ],
            "address": [
                r"(?i)(?:address|location)[\s:]*([0-9]+\s+[A-Za-z0-9\s.,-]+)",
                r"([0-9]+\s+[A-Za-z0-9\s.,-]+(?:\s+St|Street|Ave|Avenue|Rd|Road|Blvd|Boulevard|Dr|Drive))"
            ],
            "phone": [
                r"(?i)(?:phone|telephone|tel)[\s:]*([0-9\-\(\)\s\+\.]+)",
                r"(\([0-9]{3}\)\s*[0-9]{3}-[0-9]{4})",
                r"([0-9]{3}-[0-9]{3}-[0-9]{4})",
                r"([0-9]{3}\.[0-9]{3}\.[0-9]{4})"
            ],
            "license": [
                r"(?i)(?:license|lic\.?|license number)[\s:]*([A-Z0-9\-]+)",
                r"(?i)(?:medical license|physician license)[\s:]*([A-Z0-9\-]+)",
                r"(?i)(?:npi|national provider identifier)[\s:]*([0-9]{10})"
            ],
            "email": [
                r"(?i)(?:email|e-mail)[\s:]*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
                r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"
            ],
            "specialty": [
                r"(?i)(?:specialty|specialization|practice area)[\s:]*([A-Za-z\s&,-]+)",
                r"(?i)(?:board certified|certification)[\s:]*([A-Za-z\s&,-]+)"
            ]
        }
        
        # Initialize provider-specific settings
        self._initialize_provider()
    
    def _initialize_provider(self):
        """Initialize provider-specific settings"""
        if self.provider == OCRProvider.TESSERACT:
            try:
                # Test Tesseract installation
                pytesseract.get_tesseract_version()
                logger.info("Tesseract OCR initialized successfully")
            except Exception as e:
                logger.error(f"Tesseract initialization failed: {e}")
                raise RuntimeError(f"Tesseract OCR not available: {e}")
        
        elif self.provider == OCRProvider.GOOGLE_DOCUMENT_AI:
            if not GOOGLE_DOCUMENT_AI_AVAILABLE:
                raise RuntimeError("Google Document AI not available. Install google-cloud-documentai")
            
            # These should be set via environment variables or configuration
            self.google_project_id = "your-project-id"
            self.google_location = "us"
            self.google_processor_id = "your-processor-id"
            
            logger.info("Google Document AI initialized successfully")
    
    async def extract_text(self, document_path: Union[str, Path, bytes]) -> OCRResult:
        """
        Extract text and structured fields from document
        
        Args:
            document_path: Path to document or document bytes
            
        Returns:
            OCRResult with extracted text and fields
        """
        start_time = datetime.now()
        
        try:
            # Determine document type
            document_type = self._detect_document_type(document_path)
            
            if document_type == DocumentType.PDF:
                return await self._process_pdf(document_path, start_time)
            elif document_type == DocumentType.IMAGE:
                return await self._process_image(document_path, start_time)
            else:
                return OCRResult(
                    success=False,
                    raw_text="",
                    extracted_fields=[],
                    document_type=document_type,
                    page_count=0,
                    processing_time=0.0,
                    provider=self.provider,
                    confidence_score=0.0,
                    error_message="Unsupported document type"
                )
        
        except Exception as e:
            logger.error(f"OCR extraction failed: {str(e)}")
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return OCRResult(
                success=False,
                raw_text="",
                extracted_fields=[],
                document_type=DocumentType.UNKNOWN,
                page_count=0,
                processing_time=processing_time,
                provider=self.provider,
                confidence_score=0.0,
                error_message=str(e)
            )
    
    def _detect_document_type(self, document_path: Union[str, Path, bytes]) -> DocumentType:
        """Detect document type from path or content"""
        if isinstance(document_path, bytes):
            # Check magic bytes
            if document_path.startswith(b'%PDF'):
                return DocumentType.PDF
            elif document_path.startswith(b'\xff\xd8\xff'):  # JPEG
                return DocumentType.IMAGE
            elif document_path.startswith(b'\x89PNG'):  # PNG
                return DocumentType.IMAGE
            else:
                return DocumentType.UNKNOWN
        
        path = Path(document_path)
        extension = path.suffix.lower()
        
        if extension == '.pdf':
            return DocumentType.PDF
        elif extension in ['.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.gif']:
            return DocumentType.IMAGE
        else:
            return DocumentType.UNKNOWN
    
    async def _process_pdf(self, document_path: Union[str, Path, bytes], start_time: datetime) -> OCRResult:
        """Process PDF document"""
        try:
            if self.provider == OCRProvider.TESSERACT:
                return await self._process_pdf_tesseract(document_path, start_time)
            elif self.provider == OCRProvider.GOOGLE_DOCUMENT_AI:
                return await self._process_pdf_google(document_path, start_time)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
        
        except Exception as e:
            logger.error(f"PDF processing failed: {str(e)}")
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return OCRResult(
                success=False,
                raw_text="",
                extracted_fields=[],
                document_type=DocumentType.PDF,
                page_count=0,
                processing_time=processing_time,
                provider=self.provider,
                confidence_score=0.0,
                error_message=str(e)
            )
    
    async def _process_image(self, document_path: Union[str, Path, bytes], start_time: datetime) -> OCRResult:
        """Process image document"""
        try:
            if self.provider == OCRProvider.TESSERACT:
                return await self._process_image_tesseract(document_path, start_time)
            elif self.provider == OCRProvider.GOOGLE_DOCUMENT_AI:
                return await self._process_image_google(document_path, start_time)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
        
        except Exception as e:
            logger.error(f"Image processing failed: {str(e)}")
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return OCRResult(
                success=False,
                raw_text="",
                extracted_fields=[],
                document_type=DocumentType.IMAGE,
                page_count=1,
                processing_time=processing_time,
                provider=self.provider,
                confidence_score=0.0,
                error_message=str(e)
            )
    
    async def _process_pdf_tesseract(self, document_path: Union[str, Path, bytes], start_time: datetime) -> OCRResult:
        """Process PDF using Tesseract"""
        try:
            # Open PDF with PyMuPDF
            if isinstance(document_path, bytes):
                doc = fitz.open(stream=document_path, filetype="pdf")
            else:
                doc = fitz.open(str(document_path))
            
            all_text = []
            all_fields = []
            page_count = len(doc)
            
            for page_num in range(page_count):
                page = doc[page_num]
                
                # Convert page to image
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better quality
                img_data = pix.tobytes("png")
                
                # Process image with Tesseract
                image = Image.open(io.BytesIO(img_data))
                page_text = await self._extract_text_tesseract(image)
                all_text.append(page_text)
                
                # Extract fields from this page
                page_fields = self._extract_fields(page_text, page_num + 1)
                all_fields.extend(page_fields)
            
            doc.close()
            
            # Combine all text
            combined_text = "\n\n".join(all_text)
            
            # Calculate overall confidence
            confidence_score = self._calculate_confidence_score(all_text, all_fields)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return OCRResult(
                success=True,
                raw_text=combined_text,
                extracted_fields=all_fields,
                document_type=DocumentType.PDF,
                page_count=page_count,
                processing_time=processing_time,
                provider=self.provider,
                confidence_score=confidence_score
            )
        
        except Exception as e:
            logger.error(f"Tesseract PDF processing failed: {str(e)}")
            raise
    
    async def _process_image_tesseract(self, document_path: Union[str, Path, bytes], start_time: datetime) -> OCRResult:
        """Process image using Tesseract"""
        try:
            # Load image
            if isinstance(document_path, bytes):
                image = Image.open(io.BytesIO(document_path))
            else:
                image = Image.open(str(document_path))
            
            # Preprocess image for better OCR
            processed_image = self._preprocess_image(image)
            
            # Extract text
            raw_text = await self._extract_text_tesseract(processed_image)
            
            # Extract fields
            extracted_fields = self._extract_fields(raw_text, 1)
            
            # Calculate confidence
            confidence_score = self._calculate_confidence_score([raw_text], extracted_fields)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return OCRResult(
                success=True,
                raw_text=raw_text,
                extracted_fields=extracted_fields,
                document_type=DocumentType.IMAGE,
                page_count=1,
                processing_time=processing_time,
                provider=self.provider,
                confidence_score=confidence_score
            )
        
        except Exception as e:
            logger.error(f"Tesseract image processing failed: {str(e)}")
            raise
    
    async def _extract_text_tesseract(self, image: Image.Image) -> str:
        """Extract text from image using Tesseract"""
        try:
            # Configure Tesseract for better accuracy
            config = '--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,()[]{}:;!?@#$%^&*+-=/\\|"\'<>~`_ '
            
            # Extract text
            text = pytesseract.image_to_string(image, config=config)
            
            # Clean up text
            text = self._clean_text(text)
            
            return text
        
        except Exception as e:
            logger.error(f"Tesseract text extraction failed: {str(e)}")
            return ""
    
    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """Preprocess image for better OCR results"""
        try:
            # Convert to grayscale if needed
            if image.mode != 'L':
                image = image.convert('L')
            
            # Enhance contrast
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(2.0)
            
            # Enhance sharpness
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(2.0)
            
            # Apply noise reduction
            image = image.filter(ImageFilter.MedianFilter(size=3))
            
            return image
        
        except Exception as e:
            logger.error(f"Image preprocessing failed: {str(e)}")
            return image
    
    def _extract_fields(self, text: str, page_number: int) -> List[ExtractedField]:
        """Extract structured fields from text"""
        extracted_fields = []
        
        for field_name, patterns in self.field_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE)
                
                for match in matches:
                    field_value = match.group(1).strip()
                    
                    # Clean up field value
                    field_value = self._clean_field_value(field_value)
                    
                    if field_value and len(field_value) > 1:
                        # Calculate confidence based on pattern match quality
                        confidence = self._calculate_field_confidence(field_name, field_value, pattern)
                        
                        extracted_fields.append(ExtractedField(
                            field_name=field_name,
                            field_value=field_value,
                            confidence=confidence,
                            page_number=page_number
                        ))
                        
                        # Only take the first good match for each field
                        break
        
        return extracted_fields
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove control characters
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        
        # Fix common OCR errors
        text = text.replace('|', 'I')  # Common OCR error
        text = text.replace('0', 'O')  # In names
        text = text.replace('5', 'S')  # In names
        
        return text.strip()
    
    def _clean_field_value(self, value: str) -> str:
        """Clean extracted field value"""
        # Remove common OCR artifacts
        value = re.sub(r'[^\w\s@.-]', '', value)
        value = re.sub(r'\s+', ' ', value)
        
        return value.strip()
    
    def _calculate_field_confidence(self, field_name: str, field_value: str, pattern: str) -> float:
        """Calculate confidence score for extracted field"""
        base_confidence = 0.8
        
        # Adjust based on field type
        if field_name == "phone":
            # Validate phone number format
            if re.match(r'^\([0-9]{3}\)\s*[0-9]{3}-[0-9]{4}$', field_value):
                base_confidence = 0.95
            elif re.match(r'^[0-9]{3}-[0-9]{3}-[0-9]{4}$', field_value):
                base_confidence = 0.90
            else:
                base_confidence = 0.70
        
        elif field_name == "email":
            # Validate email format
            if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', field_value):
                base_confidence = 0.95
            else:
                base_confidence = 0.70
        
        elif field_name == "license":
            # Validate license format
            if re.match(r'^[A-Z0-9\-]+$', field_value) and len(field_value) >= 3:
                base_confidence = 0.90
            else:
                base_confidence = 0.75
        
        elif field_name == "name":
            # Validate name format
            if re.match(r'^[A-Za-z\s.,]+$', field_value) and len(field_value) >= 3:
                base_confidence = 0.85
            else:
                base_confidence = 0.70
        
        # Adjust based on pattern complexity
        if '^' in pattern or '$' in pattern:
            base_confidence += 0.05  # More specific pattern
        
        return min(1.0, base_confidence)
    
    def _calculate_confidence_score(self, text_parts: List[str], fields: List[ExtractedField]) -> float:
        """Calculate overall confidence score"""
        if not text_parts and not fields:
            return 0.0
        
        # Calculate text confidence based on length and quality
        text_confidence = 0.0
        if text_parts:
            total_length = sum(len(text) for text in text_parts)
            if total_length > 100:
                text_confidence = 0.8
            elif total_length > 50:
                text_confidence = 0.6
            else:
                text_confidence = 0.4
        
        # Calculate field confidence
        field_confidence = 0.0
        if fields:
            field_confidence = sum(field.confidence for field in fields) / len(fields)
        
        # Combine confidences
        if text_confidence > 0 and field_confidence > 0:
            return (text_confidence + field_confidence) / 2
        elif field_confidence > 0:
            return field_confidence
        else:
            return text_confidence
    
    async def _process_pdf_google(self, document_path: Union[str, Path, bytes], start_time: datetime) -> OCRResult:
        """Process PDF using Google Document AI"""
        try:
            # Initialize Document AI client
            client = documentai.DocumentProcessorServiceClient()
            
            # Prepare document
            if isinstance(document_path, bytes):
                document_content = document_path
            else:
                with open(document_path, 'rb') as f:
                    document_content = f.read()
            
            # Create document
            raw_document = documentai.RawDocument(
                content=document_content,
                mime_type="application/pdf"
            )
            
            # Process document
            request = documentai.ProcessRequest(
                name=f"projects/{self.google_project_id}/locations/{self.google_location}/processors/{self.google_processor_id}",
                raw_document=raw_document
            )
            
            result = client.process_document(request=request)
            document = result.document
            
            # Extract text
            raw_text = document.text
            
            # Extract fields
            extracted_fields = self._extract_fields_google(document)
            
            # Calculate confidence
            confidence_score = self._calculate_confidence_score([raw_text], extracted_fields)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return OCRResult(
                success=True,
                raw_text=raw_text,
                extracted_fields=extracted_fields,
                document_type=DocumentType.PDF,
                page_count=len(document.pages),
                processing_time=processing_time,
                provider=self.provider,
                confidence_score=confidence_score
            )
        
        except Exception as e:
            logger.error(f"Google Document AI PDF processing failed: {str(e)}")
            raise
    
    async def _process_image_google(self, document_path: Union[str, Path, bytes], start_time: datetime) -> OCRResult:
        """Process image using Google Document AI"""
        try:
            # Initialize Document AI client
            client = documentai.DocumentProcessorServiceClient()
            
            # Prepare document
            if isinstance(document_path, bytes):
                document_content = document_path
            else:
                with open(document_path, 'rb') as f:
                    document_content = f.read()
            
            # Determine MIME type
            if isinstance(document_path, bytes):
                mime_type = "image/png"  # Default
            else:
                extension = Path(document_path).suffix.lower()
                if extension in ['.jpg', '.jpeg']:
                    mime_type = "image/jpeg"
                elif extension == '.png':
                    mime_type = "image/png"
                elif extension == '.tiff':
                    mime_type = "image/tiff"
                else:
                    mime_type = "image/png"
            
            # Create document
            raw_document = documentai.RawDocument(
                content=document_content,
                mime_type=mime_type
            )
            
            # Process document
            request = documentai.ProcessRequest(
                name=f"projects/{self.google_project_id}/locations/{self.google_location}/processors/{self.google_processor_id}",
                raw_document=raw_document
            )
            
            result = client.process_document(request=request)
            document = result.document
            
            # Extract text
            raw_text = document.text
            
            # Extract fields
            extracted_fields = self._extract_fields_google(document)
            
            # Calculate confidence
            confidence_score = self._calculate_confidence_score([raw_text], extracted_fields)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return OCRResult(
                success=True,
                raw_text=raw_text,
                extracted_fields=extracted_fields,
                document_type=DocumentType.IMAGE,
                page_count=1,
                processing_time=processing_time,
                provider=self.provider,
                confidence_score=confidence_score
            )
        
        except Exception as e:
            logger.error(f"Google Document AI image processing failed: {str(e)}")
            raise
    
    def _extract_fields_google(self, document: Any) -> List[ExtractedField]:
        """Extract fields from Google Document AI result"""
        extracted_fields = []
        
        # Extract entities (if available)
        if hasattr(document, 'entities'):
            for entity in document.entities:
                field_name = entity.type_.lower()
                field_value = entity.mention_text
                confidence = entity.confidence
                
                # Map Google entity types to our field names
                field_mapping = {
                    'person': 'name',
                    'address': 'address',
                    'phone_number': 'phone',
                    'email_address': 'email'
                }
                
                if field_name in field_mapping:
                    extracted_fields.append(ExtractedField(
                        field_name=field_mapping[field_name],
                        field_value=field_value,
                        confidence=confidence,
                        page_number=1  # Google Document AI doesn't provide page info for entities
                    ))
        
        # Also extract using regex patterns on the full text
        text_fields = self._extract_fields(document.text, 1)
        extracted_fields.extend(text_fields)
        
        return extracted_fields
    
    def switch_provider(self, new_provider: OCRProvider):
        """Switch OCR provider"""
        self.provider = new_provider
        self._initialize_provider()
        logger.info(f"Switched to OCR provider: {new_provider.value}")
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported document formats"""
        return ['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.gif']
    
    def get_field_patterns(self) -> Dict[str, List[str]]:
        """Get current field extraction patterns"""
        return self.field_patterns.copy()
    
    def add_field_pattern(self, field_name: str, pattern: str):
        """Add custom field extraction pattern"""
        if field_name not in self.field_patterns:
            self.field_patterns[field_name] = []
        
        self.field_patterns[field_name].append(pattern)
        logger.info(f"Added pattern for field '{field_name}': {pattern}")


# Example usage and testing functions
async def example_ocr_extraction():
    """
    Example function demonstrating OCR extraction
    """
    print("=" * 60)
    print("🔍 OCR PIPELINE EXAMPLE")
    print("=" * 60)
    
    # Initialize OCR pipeline with Tesseract
    ocr_pipeline = OCRPipeline(provider=OCRProvider.TESSERACT)
    
    # Example 1: Process a PDF document
    print("\n📋 Example 1: PDF Document Processing")
    print("-" * 40)
    
    # Use one of our generated PDF images
    pdf_path = "data/pdf_images/provider_form_001.png"  # This is actually a PNG image
    
    try:
        result = await ocr_pipeline.extract_text(pdf_path)
        
        if result.success:
            print("✅ Document processed successfully!")
            print(f"   Document Type: {result.document_type.value}")
            print(f"   Page Count: {result.page_count}")
            print(f"   Processing Time: {result.processing_time:.2f}s")
            print(f"   Provider: {result.provider.value}")
            print(f"   Confidence Score: {result.confidence_score:.2f}")
            
            print(f"\n📄 Raw Text (first 200 characters):")
            print(f"   {result.raw_text[:200]}...")
            
            print(f"\n🔍 Extracted Fields:")
            for field in result.extracted_fields:
                print(f"   {field.field_name:12}: {field.field_value}")
                print(f"   {'':12}  Confidence: {field.confidence:.2f}")
        else:
            print(f"❌ Error: {result.error_message}")
    
    except Exception as e:
        print(f"❌ Error processing document: {e}")
    
    # Example 2: Switch to Google Document AI (if available)
    print("\n📋 Example 2: Provider Switching")
    print("-" * 40)
    
    if GOOGLE_DOCUMENT_AI_AVAILABLE:
        try:
            ocr_pipeline.switch_provider(OCRProvider.GOOGLE_DOCUMENT_AI)
            print("✅ Switched to Google Document AI")
            
            # Process with Google Document AI
            result = await ocr_pipeline.extract_text(pdf_path)
            
            if result.success:
                print("✅ Document processed with Google Document AI!")
                print(f"   Confidence Score: {result.confidence_score:.2f}")
                print(f"   Processing Time: {result.processing_time:.2f}s")
            else:
                print(f"❌ Error: {result.error_message}")
        
        except Exception as e:
            print(f"❌ Google Document AI error: {e}")
    else:
        print("⚠️  Google Document AI not available (requires google-cloud-documentai)")


def show_extraction_patterns():
    """
    Show field extraction patterns
    """
    print("\n" + "=" * 60)
    print("🎯 FIELD EXTRACTION PATTERNS")
    print("=" * 60)
    
    ocr_pipeline = OCRPipeline()
    patterns = ocr_pipeline.get_field_patterns()
    
    for field_name, field_patterns in patterns.items():
        print(f"\n📋 {field_name.upper()}:")
        for i, pattern in enumerate(field_patterns, 1):
            print(f"   {i}. {pattern}")


def show_supported_formats():
    """
    Show supported document formats
    """
    print("\n" + "=" * 60)
    print("📄 SUPPORTED DOCUMENT FORMATS")
    print("=" * 60)
    
    ocr_pipeline = OCRPipeline()
    formats = ocr_pipeline.get_supported_formats()
    
    print("📋 Supported formats:")
    for format_ext in formats:
        print(f"   • {format_ext}")


def show_sample_extraction_json():
    """
    Show sample extracted JSON structure
    """
    print("\n" + "=" * 60)
    print("📄 SAMPLE EXTRACTED JSON")
    print("=" * 60)
    
    # Sample OCR result
    sample_result = OCRResult(
        success=True,
        raw_text="Dr. John Smith\n123 Main Street, Suite 100\nSan Francisco, CA 94102\n(555) 123-4567\njohn.smith@example.com\nLicense: A123456\nSpecialty: Internal Medicine",
        extracted_fields=[
            ExtractedField(
                field_name="name",
                field_value="Dr. John Smith",
                confidence=0.95,
                page_number=1
            ),
            ExtractedField(
                field_name="address",
                field_value="123 Main Street, Suite 100 San Francisco, CA 94102",
                confidence=0.90,
                page_number=1
            ),
            ExtractedField(
                field_name="phone",
                field_value="(555) 123-4567",
                confidence=0.95,
                page_number=1
            ),
            ExtractedField(
                field_name="email",
                field_value="john.smith@example.com",
                confidence=0.95,
                page_number=1
            ),
            ExtractedField(
                field_name="license",
                field_value="A123456",
                confidence=0.90,
                page_number=1
            ),
            ExtractedField(
                field_name="specialty",
                field_value="Internal Medicine",
                confidence=0.85,
                page_number=1
            )
        ],
        document_type=DocumentType.IMAGE,
        page_count=1,
        processing_time=2.5,
        provider=OCRProvider.TESSERACT,
        confidence_score=0.92
    )
    
    # Convert to JSON-serializable format
    result_dict = {
        "success": sample_result.success,
        "raw_text": sample_result.raw_text,
        "extracted_fields": [
            {
                "field_name": field.field_name,
                "field_value": field.field_value,
                "confidence": field.confidence,
                "page_number": field.page_number
            }
            for field in sample_result.extracted_fields
        ],
        "document_type": sample_result.document_type.value,
        "page_count": sample_result.page_count,
        "processing_time": sample_result.processing_time,
        "provider": sample_result.provider.value,
        "confidence_score": sample_result.confidence_score
    }
    
    print(json.dumps(result_dict, indent=2))


async def main():
    """
    Main function to run all examples
    """
    try:
        # Run examples
        await example_ocr_extraction()
        show_extraction_patterns()
        show_supported_formats()
        show_sample_extraction_json()
        
        print("\n" + "=" * 60)
        print("✅ OCR Pipeline Examples Complete!")
        print("=" * 60)
        print("\n📝 Key Features Demonstrated:")
        print("   ✅ Document type detection (PDF/Image)")
        print("   ✅ Text extraction with Tesseract")
        print("   ✅ Google Document AI integration")
        print("   ✅ Structured field extraction")
        print("   ✅ Provider switching capability")
        print("   ✅ Confidence scoring")
        print("   ✅ Image preprocessing")
        print("   ✅ Pattern-based field extraction")
        
        print("\n🔧 Configuration Options:")
        print("   • OCR provider selection (Tesseract/Google Document AI)")
        print("   • Custom field extraction patterns")
        print("   • Image preprocessing settings")
        print("   • Confidence scoring thresholds")
        print("   • Document format support")
        
        print("\n⚠️  Important Notes:")
        print("   • Tesseract requires system installation")
        print("   • Google Document AI requires GCP setup")
        print("   • Field extraction uses regex patterns")
        print("   • Confidence scores help assess quality")
        print("   • Image preprocessing improves accuracy")
        
    except Exception as e:
        print(f"❌ Error running examples: {e}")


if __name__ == "__main__":
    # Run examples
    print("OCR Pipeline - Examples")
    print("To run examples:")
    print("1. Install Tesseract: https://github.com/tesseract-ocr/tesseract")
    print("2. Install dependencies: pip install pytesseract pillow PyMuPDF")
    print("3. Run: python -c 'from pipelines.ocr import main; asyncio.run(main())'")
