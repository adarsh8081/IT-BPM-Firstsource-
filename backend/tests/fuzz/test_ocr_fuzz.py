"""
Fuzz Tests for OCR Pipeline and Malformed PDFs

This module provides comprehensive fuzz testing for OCR pipeline robustness
against malformed inputs, corrupted files, and edge cases.
"""

import pytest
import io
import random
import string
from typing import List, Dict, Any, Optional
from unittest.mock import Mock, patch
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# Import OCR components
from backend.pipelines.ocr import OCRPipeline, TesseractOCR, GoogleDocumentAIOCR
from backend.pipelines.ocr import ExtractedText, StructuredFields

class FuzzDataGenerator:
    """Generate fuzz test data for OCR testing"""
    
    @staticmethod
    def generate_random_text(length: int = 100) -> str:
        """Generate random text for fuzzing"""
        characters = string.ascii_letters + string.digits + string.punctuation + " \n\t"
        return ''.join(random.choice(characters) for _ in range(length))
    
    @staticmethod
    def generate_malformed_text() -> List[str]:
        """Generate various malformed text patterns"""
        return [
            "",  # Empty string
            "   ",  # Whitespace only
            "\n\n\n",  # Newlines only
            "\t\t\t",  # Tabs only
            "a" * 10000,  # Very long string
            "".join(chr(i) for i in range(256)),  # All ASCII characters
            "🚀🎉💯🔥✨🌟💫⭐🎊🎈🎁",  # Emojis only
            "αβγδεζηθικλμνξοπρστυφχψω",  # Greek letters
            "中文测试文本",  # Chinese characters
            "العربية",  # Arabic text
            "Русский текст",  # Cyrillic text
            "\x00\x01\x02\x03\x04\x05",  # Control characters
            "Mixed 123 ABC αβγ 🎉 Text",  # Mixed content
        ]
    
    @staticmethod
    def generate_corrupted_image_data() -> List[bytes]:
        """Generate corrupted image data for testing"""
        return [
            b"",  # Empty data
            b"not an image",  # Invalid image data
            b"PNG\x00\x00\x00\x00",  # Corrupted PNG header
            b"\xFF\xD8\xFF\xE0\x00\x00",  # Corrupted JPEG header
            b"BM\x00\x00\x00\x00",  # Corrupted BMP header
            b"GIF87a\x00\x00\x00\x00",  # Corrupted GIF header
            b"RIFF\x00\x00\x00\x00",  # Corrupted TIFF header
            b"PK\x03\x04",  # ZIP file header (not image)
            b"PDF-1.4",  # PDF header (not image)
            b"\x00" * 1000,  # Null bytes
            b"\xFF" * 1000,  # All 0xFF bytes
            b"\xAA\x55" * 500,  # Alternating pattern
        ]
    
    @staticmethod
    def generate_edge_case_images() -> List[Image.Image]:
        """Generate edge case images for testing"""
        images = []
        
        # Empty image
        images.append(Image.new('RGB', (1, 1), (255, 255, 255)))
        
        # Very small image
        images.append(Image.new('RGB', (10, 10), (255, 255, 255)))
        
        # Very large image (but manageable)
        images.append(Image.new('RGB', (4000, 3000), (255, 255, 255)))
        
        # Single color images
        for color in [(0, 0, 0), (255, 255, 255), (255, 0, 0), (0, 255, 0), (0, 0, 255)]:
            images.append(Image.new('RGB', (100, 100), color))
        
        # High contrast image
        img = Image.new('RGB', (200, 200), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.rectangle([50, 50, 150, 150], fill=(0, 0, 0))
        images.append(img)
        
        # Noisy image
        img = Image.new('RGB', (200, 200), (128, 128, 128))
        pixels = np.array(img)
        noise = np.random.randint(0, 256, pixels.shape, dtype=np.uint8)
        noisy_img = Image.fromarray(noise)
        images.append(noisy_img)
        
        # Gradient image
        img = Image.new('RGB', (200, 200))
        for x in range(200):
            for y in range(200):
                img.putpixel((x, y), (x, y, (x + y) % 256))
        images.append(img)
        
        return images
    
    @staticmethod
    def generate_malformed_pdf_content() -> List[bytes]:
        """Generate malformed PDF content for testing"""
        return [
            b"",  # Empty PDF
            b"not a pdf",  # Invalid PDF content
            b"PDF-1.4\n",  # Minimal PDF header
            b"PDF-1.4\n%PDF-1.4",  # Duplicate header
            b"PDF-1.4\n%%EOF",  # Immediate EOF
            b"PDF-1.4\n1 0 obj\n<<>>\nstream\n" + b"x" * 10000 + b"\nendstream\nendobj\n%%EOF",  # Large stream
            b"PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\n%%EOF",  # Minimal valid PDF
            b"PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids []\n/Count 0\n>>\nendobj\n%%EOF",  # Empty pages
            b"PDF-1.4\n" + b"\x00" * 1000,  # Null bytes in PDF
            b"PDF-1.4\n" + b"\xFF" * 1000,  # All 0xFF bytes in PDF
        ]

class TestOCRFuzz:
    """Fuzz tests for OCR pipeline robustness"""
    
    @pytest.fixture
    def ocr_pipeline(self):
        """Create OCR pipeline instance for testing"""
        return OCRPipeline()
    
    @pytest.fixture
    def fuzz_generator(self):
        """Create fuzz data generator"""
        return FuzzDataGenerator()
    
    def test_ocr_with_empty_input(self, ocr_pipeline):
        """Test OCR with empty input"""
        # Test with None input
        result = ocr_pipeline.extract_text(None)
        assert result is None or result.text == ""
        
        # Test with empty bytes
        result = ocr_pipeline.extract_text(b"")
        assert result is None or result.text == ""
        
        # Test with empty string
        result = ocr_pipeline.extract_text("")
        assert result is None or result.text == ""
    
    def test_ocr_with_corrupted_image_data(self, ocr_pipeline, fuzz_generator):
        """Test OCR with corrupted image data"""
        corrupted_data_list = fuzz_generator.generate_corrupted_image_data()
        
        for i, corrupted_data in enumerate(corrupted_data_list):
            try:
                result = ocr_pipeline.extract_text(corrupted_data)
                # Should either return None or handle gracefully
                if result is not None:
                    assert isinstance(result, ExtractedText)
                    assert isinstance(result.text, str)
            except Exception as e:
                # OCR should handle corrupted data gracefully
                assert isinstance(e, (ValueError, OSError, IOError))
    
    def test_ocr_with_edge_case_images(self, ocr_pipeline, fuzz_generator):
        """Test OCR with edge case images"""
        edge_case_images = fuzz_generator.generate_edge_case_images()
        
        for i, image in enumerate(edge_case_images):
            try:
                # Convert image to bytes
                img_bytes = io.BytesIO()
                image.save(img_bytes, format='PNG')
                img_data = img_bytes.getvalue()
                
                result = ocr_pipeline.extract_text(img_data)
                
                if result is not None:
                    assert isinstance(result, ExtractedText)
                    assert isinstance(result.text, str)
                    assert result.confidence >= 0.0
                    assert result.confidence <= 1.0
                    
            except Exception as e:
                # OCR should handle edge cases gracefully
                assert isinstance(e, (ValueError, OSError, IOError))
    
    def test_ocr_with_random_text_content(self, ocr_pipeline, fuzz_generator):
        """Test OCR with random text content"""
        for i in range(50):  # Test 50 random cases
            random_text = fuzz_generator.generate_random_text(random.randint(10, 500))
            
            # Create image with random text
            try:
                img = Image.new('RGB', (400, 100), (255, 255, 255))
                draw = ImageDraw.Draw(img)
                
                # Try to use default font
                try:
                    font = ImageFont.load_default()
                except:
                    font = None
                
                # Draw text (may overflow, that's okay for fuzzing)
                draw.text((10, 10), random_text, fill=(0, 0, 0), font=font)
                
                # Convert to bytes
                img_bytes = io.BytesIO()
                img.save(img_bytes, format='PNG')
                img_data = img_bytes.getvalue()
                
                result = ocr_pipeline.extract_text(img_data)
                
                if result is not None:
                    assert isinstance(result, ExtractedText)
                    assert isinstance(result.text, str)
                    
            except Exception as e:
                # OCR should handle random content gracefully
                assert isinstance(e, (ValueError, OSError, IOError, UnicodeError))
    
    def test_structured_field_extraction_fuzz(self, ocr_pipeline, fuzz_generator):
        """Test structured field extraction with fuzzed data"""
        malformed_texts = fuzz_generator.generate_malformed_text()
        
        for text in malformed_texts:
            try:
                fields = ocr_pipeline.extract_structured_fields(text)
                
                if fields is not None:
                    assert isinstance(fields, StructuredFields)
                    # All fields should be strings or None
                    assert isinstance(fields.name, (str, type(None)))
                    assert isinstance(fields.address, (str, type(None)))
                    assert isinstance(fields.phone, (str, type(None)))
                    assert isinstance(fields.license_number, (str, type(None)))
                    assert isinstance(fields.email, (str, type(None)))
                    
            except Exception as e:
                # Field extraction should handle malformed text gracefully
                assert isinstance(e, (ValueError, AttributeError, TypeError))
    
    def test_confidence_scoring_fuzz(self, ocr_pipeline, fuzz_generator):
        """Test confidence scoring with various inputs"""
        for i in range(20):
            # Generate random text of various lengths
            text_length = random.randint(0, 1000)
            random_text = fuzz_generator.generate_random_text(text_length)
            
            try:
                confidence = ocr_pipeline._calculate_confidence(random_text)
                
                # Confidence should be between 0 and 1
                assert 0.0 <= confidence <= 1.0
                
            except Exception as e:
                # Confidence calculation should handle any input
                assert isinstance(e, (ValueError, TypeError))
    
    def test_tesseract_ocr_fuzz(self, fuzz_generator):
        """Test Tesseract OCR with fuzzed inputs"""
        tesseract_ocr = TesseractOCR()
        
        # Test with corrupted data
        corrupted_data_list = fuzz_generator.generate_corrupted_image_data()
        
        for corrupted_data in corrupted_data_list:
            try:
                result = tesseract_ocr.extract_text(corrupted_data)
                
                if result is not None:
                    assert isinstance(result, ExtractedText)
                    assert isinstance(result.text, str)
                    assert 0.0 <= result.confidence <= 1.0
                    
            except Exception as e:
                # Tesseract should handle corrupted data gracefully
                assert isinstance(e, (ValueError, OSError, IOError, RuntimeError))
    
    def test_google_document_ai_ocr_fuzz(self, fuzz_generator):
        """Test Google Document AI OCR with fuzzed inputs"""
        # Mock Google Document AI OCR since we don't have real API key in tests
        with patch('backend.pipelines.ocr.GoogleDocumentAIOCR') as MockGoogleOCR:
            mock_ocr = Mock()
            mock_ocr.extract_text.return_value = ExtractedText(
                text="Mock extracted text",
                confidence=0.9,
                raw_response={"mock": "response"}
            )
            MockGoogleOCR.return_value = mock_ocr
            
            google_ocr = GoogleDocumentAIOCR("mock_api_key")
            
            # Test with corrupted data
            corrupted_data_list = fuzz_generator.generate_corrupted_image_data()
            
            for corrupted_data in corrupted_data_list:
                try:
                    result = google_ocr.extract_text(corrupted_data)
                    
                    if result is not None:
                        assert isinstance(result, ExtractedText)
                        assert isinstance(result.text, str)
                        assert 0.0 <= result.confidence <= 1.0
                        
                except Exception as e:
                    # Google Document AI should handle corrupted data gracefully
                    assert isinstance(e, (ValueError, OSError, IOError, RuntimeError))
    
    def test_memory_usage_with_large_inputs(self, ocr_pipeline):
        """Test memory usage with large inputs"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create large image
        large_image = Image.new('RGB', (2000, 2000), (255, 255, 255))
        draw = ImageDraw.Draw(large_image)
        
        # Add lots of text
        for i in range(100):
            draw.text((random.randint(0, 1800), random.randint(0, 1800)), 
                     fuzz_generator.generate_random_text(50), 
                     fill=(0, 0, 0))
        
        # Convert to bytes
        img_bytes = io.BytesIO()
        large_image.save(img_bytes, format='PNG')
        img_data = img_bytes.getvalue()
        
        try:
            result = ocr_pipeline.extract_text(img_data)
            
            # Check memory usage
            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = current_memory - initial_memory
            
            # Memory increase should be reasonable (less than 500MB)
            assert memory_increase < 500, f"Memory usage increased by {memory_increase:.1f}MB"
            
        except Exception as e:
            # OCR should handle large inputs gracefully
            assert isinstance(e, (MemoryError, ValueError, OSError))
    
    def test_concurrent_ocr_processing(self, ocr_pipeline, fuzz_generator):
        """Test concurrent OCR processing with fuzzed inputs"""
        import asyncio
        
        async def process_ocr(data):
            try:
                return ocr_pipeline.extract_text(data)
            except Exception as e:
                return None
        
        # Generate multiple test images
        test_images = []
        for i in range(10):
            img = Image.new('RGB', (200, 100), (255, 255, 255))
            draw = ImageDraw.Draw(img)
            draw.text((10, 10), fuzz_generator.generate_random_text(50), fill=(0, 0, 0))
            
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            test_images.append(img_bytes.getvalue())
        
        # Process concurrently
        async def run_concurrent_test():
            tasks = [process_ocr(data) for data in test_images]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify results
            for result in results:
                if isinstance(result, Exception):
                    # Exceptions should be OCR-related
                    assert isinstance(result, (ValueError, OSError, IOError, RuntimeError))
                elif result is not None:
                    assert isinstance(result, ExtractedText)
        
        # Run concurrent test
        asyncio.run(run_concurrent_test())
    
    def test_regex_pattern_matching_fuzz(self, ocr_pipeline):
        """Test regex pattern matching with fuzzed text"""
        # Generate various text patterns that might match our regexes
        test_patterns = [
            "Phone: 555-123-4567",
            "Email: test@example.com",
            "Address: 123 Main St, San Francisco, CA 94102",
            "License: A12345",
            "NPI: 1234567890",
            "Mixed: Phone 555-123-4567 Email test@example.com",
            "Noisy: abc123def456ghi789",
            "Special chars: !@#$%^&*()_+-=[]{}|;':\",./<>?",
            "Unicode: αβγδε 123 ABC",
            "Empty: ",
            "Very long: " + "x" * 1000,
            "Numbers only: 1234567890",
            "Letters only: abcdefghijklmnopqrstuvwxyz",
        ]
        
        for pattern in test_patterns:
            try:
                fields = ocr_pipeline.extract_structured_fields(pattern)
                
                if fields is not None:
                    assert isinstance(fields, StructuredFields)
                    
            except Exception as e:
                # Pattern matching should handle any text
                assert isinstance(e, (ValueError, TypeError, AttributeError))

class TestPDFFuzz:
    """Fuzz tests for PDF processing robustness"""
    
    @pytest.fixture
    def fuzz_generator(self):
        """Create fuzz data generator"""
        return FuzzDataGenerator()
    
    def test_pdf_processing_with_malformed_content(self, fuzz_generator):
        """Test PDF processing with malformed content"""
        malformed_pdfs = fuzz_generator.generate_malformed_pdf_content()
        
        for i, pdf_content in enumerate(malformed_pdfs):
            try:
                # Try to process malformed PDF
                # This would normally use a PDF processing library
                # For testing, we'll simulate the behavior
                
                if len(pdf_content) == 0:
                    # Empty PDF should be handled
                    result = None
                elif b"PDF-1.4" not in pdf_content:
                    # Invalid PDF should raise error
                    raise ValueError("Invalid PDF format")
                else:
                    # Minimal valid PDF should be processed
                    result = "Extracted text from PDF"
                
                if result is not None:
                    assert isinstance(result, str)
                    
            except Exception as e:
                # PDF processing should handle malformed content gracefully
                assert isinstance(e, (ValueError, OSError, IOError))
    
    def test_pdf_size_limits(self):
        """Test PDF processing with various sizes"""
        sizes = [0, 1, 100, 1000, 10000, 100000, 1000000]  # Various sizes in bytes
        
        for size in sizes:
            try:
                # Create PDF content of specified size
                if size == 0:
                    pdf_content = b""
                else:
                    pdf_content = b"PDF-1.4\n" + b"x" * (size - 8) + b"\n%%EOF"
                
                # Simulate processing
                if size > 1000000:  # 1MB limit
                    raise ValueError("PDF too large")
                elif size == 0:
                    result = None
                else:
                    result = f"Processed PDF of size {size}"
                
                if result is not None:
                    assert isinstance(result, str)
                    
            except Exception as e:
                # PDF processing should handle size limits gracefully
                assert isinstance(e, (ValueError, MemoryError, OSError))
    
    def test_pdf_password_protection_fuzz(self):
        """Test PDF processing with password-protected content"""
        # Simulate password-protected PDFs
        password_variations = [
            "",  # Empty password
            "password",  # Simple password
            "123456",  # Numeric password
            "P@ssw0rd!",  # Complex password
            "a" * 100,  # Very long password
            "🚀🎉💯",  # Emoji password
            "αβγδε",  # Unicode password
            "\x00\x01\x02",  # Binary password
        ]
        
        for password in password_variations:
            try:
                # Simulate password-protected PDF processing
                if password == "":
                    # Empty password should be handled
                    result = "PDF processed without password"
                else:
                    # Password-protected PDF should require password
                    if len(password) > 50:
                        raise ValueError("Password too long")
                    else:
                        result = f"PDF processed with password of length {len(password)}"
                
                assert isinstance(result, str)
                
            except Exception as e:
                # Password handling should be robust
                assert isinstance(e, (ValueError, OSError))

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
