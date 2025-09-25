"""
OCR Pipeline Example Usage

This script demonstrates how to use the OCR pipeline to extract text and
structured fields from PDFs and images using Tesseract or Google Document AI.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from pipelines.ocr import OCRPipeline, OCRProvider, DocumentType


async def example_ocr_extraction():
    """
    Example: Extract text and fields from documents
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
        if Path(pdf_path).exists():
            result = await ocr_pipeline.extract_text(pdf_path)
            
            if result.success:
                print("✅ Document processed successfully!")
                print(f"   Document Type: {result.document_type.value}")
                print(f"   Page Count: {result.page_count}")
                print(f"   Processing Time: {result.processing_time:.2f}s")
                print(f"   Provider: {result.provider.value}")
                print(f"   Confidence Score: {result.confidence_score:.2f}")
                
                print(f"\n📄 Raw Text (first 300 characters):")
                print(f"   {result.raw_text[:300]}...")
                
                print(f"\n🔍 Extracted Fields:")
                if result.extracted_fields:
                    for field in result.extracted_fields:
                        print(f"   {field.field_name:12}: {field.field_value}")
                        print(f"   {'':12}  Confidence: {field.confidence:.2f}")
                        print(f"   {'':12}  Page: {field.page_number}")
                else:
                    print("   No structured fields extracted")
            else:
                print(f"❌ Error: {result.error_message}")
        else:
            print(f"⚠️  File not found: {pdf_path}")
    
    except Exception as e:
        print(f"❌ Error processing document: {e}")
    
    # Example 2: Process multiple documents
    print("\n📋 Example 2: Multiple Document Processing")
    print("-" * 40)
    
    pdf_images_dir = Path("data/pdf_images")
    if pdf_images_dir.exists():
        # Process first few PDF images
        pdf_files = list(pdf_images_dir.glob("*.png"))[:3]
        
        for pdf_file in pdf_files:
            print(f"\n📄 Processing: {pdf_file.name}")
            try:
                result = await ocr_pipeline.extract_text(pdf_file)
                
                if result.success:
                    print(f"   ✅ Success - Confidence: {result.confidence_score:.2f}")
                    print(f"   📊 Fields extracted: {len(result.extracted_fields)}")
                    
                    # Show extracted fields
                    for field in result.extracted_fields[:3]:  # Show first 3 fields
                        print(f"      {field.field_name}: {field.field_value[:30]}...")
                else:
                    print(f"   ❌ Error: {result.error_message}")
            
            except Exception as e:
                print(f"   ❌ Exception: {e}")
    else:
        print("⚠️  PDF images directory not found")
    
    # Example 3: Switch to Google Document AI (if available)
    print("\n📋 Example 3: Provider Switching")
    print("-" * 40)
    
    try:
        ocr_pipeline.switch_provider(OCRProvider.GOOGLE_DOCUMENT_AI)
        print("✅ Switched to Google Document AI")
        
        # Process with Google Document AI
        if Path(pdf_path).exists():
            result = await ocr_pipeline.extract_text(pdf_path)
            
            if result.success:
                print("✅ Document processed with Google Document AI!")
                print(f"   Confidence Score: {result.confidence_score:.2f}")
                print(f"   Processing Time: {result.processing_time:.2f}s")
                print(f"   Fields extracted: {len(result.extracted_fields)}")
            else:
                print(f"❌ Error: {result.error_message}")
    
    except Exception as e:
        print(f"⚠️  Google Document AI not available: {e}")
        print("   Switching back to Tesseract...")
        ocr_pipeline.switch_provider(OCRProvider.TESSERACT)


async def example_custom_field_patterns():
    """
    Example: Custom field extraction patterns
    """
    print("\n" + "=" * 60)
    print("🎯 CUSTOM FIELD PATTERNS EXAMPLE")
    print("=" * 60)
    
    # Initialize OCR pipeline
    ocr_pipeline = OCRPipeline(provider=OCRProvider.TESSERACT)
    
    # Add custom field patterns
    print("\n📋 Adding Custom Field Patterns:")
    
    # Add NPI pattern
    ocr_pipeline.add_field_pattern("npi", r"(?i)(?:npi|national provider identifier)[\s:]*([0-9]{10})")
    print("   ✅ Added NPI pattern")
    
    # Add DEA number pattern
    ocr_pipeline.add_field_pattern("dea", r"(?i)(?:dea|dea number)[\s:]*([A-Z]{2}[0-9]{7})")
    print("   ✅ Added DEA pattern")
    
    # Add hospital affiliation pattern
    ocr_pipeline.add_field_pattern("hospital", r"(?i)(?:hospital|medical center|clinic)[\s:]*([A-Za-z\s&,-]+)")
    print("   ✅ Added hospital pattern")
    
    # Show all patterns
    print("\n📋 Current Field Patterns:")
    patterns = ocr_pipeline.get_field_patterns()
    for field_name, field_patterns in patterns.items():
        print(f"   {field_name.upper()}:")
        for i, pattern in enumerate(field_patterns[:2], 1):  # Show first 2 patterns
            print(f"      {i}. {pattern}")
        if len(field_patterns) > 2:
            print(f"      ... and {len(field_patterns) - 2} more")


async def example_confidence_analysis():
    """
    Example: Confidence score analysis
    """
    print("\n" + "=" * 60)
    print("📊 CONFIDENCE ANALYSIS EXAMPLE")
    print("=" * 60)
    
    # Initialize OCR pipeline
    ocr_pipeline = OCRPipeline(provider=OCRProvider.TESSERACT)
    
    # Test different confidence scenarios
    print("\n📋 Confidence Score Analysis:")
    
    # High confidence scenario
    high_confidence_text = """
    Dr. John Smith
    123 Main Street
    San Francisco, CA 94102
    (555) 123-4567
    john.smith@example.com
    License: A123456
    """
    
    fields = ocr_pipeline._extract_fields(high_confidence_text, 1)
    confidence = ocr_pipeline._calculate_confidence_score([high_confidence_text], fields)
    
    print(f"   📄 High Quality Text:")
    print(f"      Confidence: {confidence:.2f}")
    print(f"      Fields extracted: {len(fields)}")
    for field in fields:
        print(f"         {field.field_name}: {field.confidence:.2f}")
    
    # Medium confidence scenario
    medium_confidence_text = """
    Dr. J. Smith
    123 Main St
    SF, CA
    (555) 123-4567
    License: A123
    """
    
    fields = ocr_pipeline._extract_fields(medium_confidence_text, 1)
    confidence = ocr_pipeline._calculate_confidence_score([medium_confidence_text], fields)
    
    print(f"\n   📄 Medium Quality Text:")
    print(f"      Confidence: {confidence:.2f}")
    print(f"      Fields extracted: {len(fields)}")
    for field in fields:
        print(f"         {field.field_name}: {field.confidence:.2f}")
    
    # Low confidence scenario
    low_confidence_text = """
    Dr. Smith
    123 Main
    (555) 123
    """
    
    fields = ocr_pipeline._extract_fields(low_confidence_text, 1)
    confidence = ocr_pipeline._calculate_confidence_score([low_confidence_text], fields)
    
    print(f"\n   📄 Low Quality Text:")
    print(f"      Confidence: {confidence:.2f}")
    print(f"      Fields extracted: {len(fields)}")
    for field in fields:
        print(f"         {field.field_name}: {field.confidence:.2f}")


def show_supported_formats():
    """
    Show supported document formats
    """
    print("\n" + "=" * 60)
    print("📄 SUPPORTED DOCUMENT FORMATS")
    print("=" * 60)
    
    ocr_pipeline = OCRPipeline(provider=OCRProvider.TESSERACT)
    formats = ocr_pipeline.get_supported_formats()
    
    print("📋 Supported formats:")
    for format_ext in formats:
        print(f"   • {format_ext}")
    
    print("\n📋 Format descriptions:")
    format_descriptions = {
        '.pdf': 'Portable Document Format',
        '.jpg': 'JPEG Image',
        '.jpeg': 'JPEG Image',
        '.png': 'Portable Network Graphics',
        '.tiff': 'Tagged Image File Format',
        '.bmp': 'Bitmap Image',
        '.gif': 'Graphics Interchange Format'
    }
    
    for format_ext, description in format_descriptions.items():
        if format_ext in formats:
            print(f"   {format_ext:8}: {description}")


def show_field_extraction_patterns():
    """
    Show field extraction patterns
    """
    print("\n" + "=" * 60)
    print("🎯 FIELD EXTRACTION PATTERNS")
    print("=" * 60)
    
    ocr_pipeline = OCRPipeline(provider=OCRProvider.TESSERACT)
    patterns = ocr_pipeline.get_field_patterns()
    
    for field_name, field_patterns in patterns.items():
        print(f"\n📋 {field_name.upper()}:")
        for i, pattern in enumerate(field_patterns, 1):
            print(f"   {i}. {pattern}")
        
        # Show example matches
        if field_name == "name":
            examples = ["Dr. John Smith", "Physician: Jane Doe", "Doctor: Robert Johnson"]
        elif field_name == "phone":
            examples = ["(555) 123-4567", "555-123-4567", "555.123.4567"]
        elif field_name == "email":
            examples = ["john@example.com", "jane.doe@hospital.org"]
        elif field_name == "license":
            examples = ["License: A123456", "NPI: 1234567890"]
        elif field_name == "address":
            examples = ["123 Main Street", "456 Oak Avenue, Suite 100"]
        elif field_name == "specialty":
            examples = ["Internal Medicine", "Family Practice", "Cardiology"]
        else:
            examples = []
        
        if examples:
            print(f"   Examples: {', '.join(examples)}")


def show_sample_extraction_json():
    """
    Show sample extracted JSON structure
    """
    print("\n" + "=" * 60)
    print("📄 SAMPLE EXTRACTED JSON")
    print("=" * 60)
    
    # Sample OCR result
    sample_result = {
        "success": True,
        "raw_text": "Dr. John Smith\n123 Main Street, Suite 100\nSan Francisco, CA 94102\n(555) 123-4567\njohn.smith@example.com\nLicense: A123456\nSpecialty: Internal Medicine",
        "extracted_fields": [
            {
                "field_name": "name",
                "field_value": "Dr. John Smith",
                "confidence": 0.95,
                "page_number": 1
            },
            {
                "field_name": "address",
                "field_value": "123 Main Street, Suite 100 San Francisco, CA 94102",
                "confidence": 0.90,
                "page_number": 1
            },
            {
                "field_name": "phone",
                "field_value": "(555) 123-4567",
                "confidence": 0.95,
                "page_number": 1
            },
            {
                "field_name": "email",
                "field_value": "john.smith@example.com",
                "confidence": 0.95,
                "page_number": 1
            },
            {
                "field_name": "license",
                "field_value": "A123456",
                "confidence": 0.90,
                "page_number": 1
            },
            {
                "field_name": "specialty",
                "field_value": "Internal Medicine",
                "confidence": 0.85,
                "page_number": 1
            }
        ],
        "document_type": "image",
        "page_count": 1,
        "processing_time": 2.5,
        "provider": "tesseract",
        "confidence_score": 0.92
    }
    
    print("📋 Sample OCR Result JSON:")
    print(json.dumps(sample_result, indent=2))


def show_provider_comparison():
    """
    Show OCR provider comparison
    """
    print("\n" + "=" * 60)
    print("⚖️  OCR PROVIDER COMPARISON")
    print("=" * 60)
    
    print("📋 Tesseract OCR:")
    print("   ✅ Free and open source")
    print("   ✅ Local processing (no internet required)")
    print("   ✅ Supports multiple languages")
    print("   ✅ Good for basic text extraction")
    print("   ⚠️  Requires system installation")
    print("   ⚠️  Accuracy depends on image quality")
    print("   ⚠️  Limited structured field extraction")
    
    print("\n📋 Google Document AI:")
    print("   ✅ High accuracy for structured documents")
    print("   ✅ Excellent field extraction capabilities")
    print("   ✅ Handles complex layouts")
    print("   ✅ Built-in document understanding")
    print("   ⚠️  Requires Google Cloud setup")
    print("   ⚠️  Internet connection required")
    print("   ⚠️  Pay-per-use pricing")
    print("   ⚠️  Data sent to Google servers")
    
    print("\n📋 Recommendation:")
    print("   • Use Tesseract for: Simple text extraction, offline processing")
    print("   • Use Google Document AI for: Complex documents, high accuracy needs")


async def main():
    """
    Main function to run all examples
    """
    try:
        # Run examples
        await example_ocr_extraction()
        await example_custom_field_patterns()
        await example_confidence_analysis()
        show_supported_formats()
        show_field_extraction_patterns()
        show_sample_extraction_json()
        show_provider_comparison()
        
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
        print("   ✅ Custom field patterns")
        print("   ✅ Multiple document processing")
        
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
        
        print("\n📊 Performance Tips:")
        print("   • Use high-quality images for better OCR")
        print("   • Preprocess images to improve contrast")
        print("   • Adjust field patterns for your documents")
        print("   • Monitor confidence scores for quality")
        print("   • Use appropriate provider for your needs")
        
    except Exception as e:
        print(f"❌ Error running examples: {e}")


if __name__ == "__main__":
    # Run examples
    print("OCR Pipeline - Examples")
    print("To run examples:")
    print("1. Install Tesseract: https://github.com/tesseract-ocr/tesseract")
    print("2. Install dependencies: pip install pytesseract pillow PyMuPDF")
    print("3. Run: python -c 'from examples.ocr_pipeline_example import main; asyncio.run(main())'")
