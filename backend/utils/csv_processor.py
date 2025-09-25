"""
CSV Processor for Batch Validation

This module provides CSV processing functionality for batch validation
with support for various CSV formats and data validation.
"""

import asyncio
import logging
import csv
import io
import uuid
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import re

logger = logging.getLogger(__name__)


class CSVFormat(Enum):
    """CSV format types"""
    STANDARD = "standard"
    CUSTOM = "custom"
    PROVIDER_DIRECTORY = "provider_directory"


@dataclass
class CSVFieldMapping:
    """CSV field mapping configuration"""
    csv_column: str
    target_field: str
    required: bool = False
    data_type: str = "string"
    validation_pattern: Optional[str] = None


@dataclass
class CSVProcessingResult:
    """CSV processing result"""
    success: bool
    provider_count: int
    processed_providers: List[Dict[str, Any]]
    errors: List[str]
    warnings: List[str]
    field_mappings: Dict[str, str]
    processing_time: float


class CSVProcessor:
    """
    CSV Processor for Batch Validation
    
    Processes CSV files for batch provider validation with support for
    various formats, field mapping, and data validation.
    """
    
    def __init__(self):
        """Initialize CSV Processor"""
        self.default_field_mappings = {
            "provider_id": ["provider_id", "id", "provider_identifier"],
            "given_name": ["given_name", "first_name", "firstname", "fname"],
            "family_name": ["family_name", "last_name", "lastname", "lname"],
            "npi_number": ["npi_number", "npi", "national_provider_identifier"],
            "phone_primary": ["phone_primary", "phone", "telephone", "tel"],
            "email": ["email", "e_mail", "email_address"],
            "address_street": ["address_street", "address", "street_address", "addr"],
            "address_city": ["address_city", "city"],
            "address_state": ["address_state", "state", "state_code"],
            "address_zip": ["address_zip", "zip", "zip_code", "postal_code"],
            "license_number": ["license_number", "license", "license_no", "lic_no"],
            "license_state": ["license_state", "lic_state", "license_state_code"],
            "primary_taxonomy": ["primary_taxonomy", "taxonomy", "specialty", "speciality"],
            "practice_name": ["practice_name", "practice", "organization", "org_name"],
            "document_path": ["document_path", "document", "file_path", "pdf_path"]
        }
        
        self.validation_patterns = {
            "npi_number": r"^\d{10}$",
            "phone_primary": r"^\+?[\d\s\-\(\)\.]+$",
            "email": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
            "license_number": r"^[A-Za-z0-9\-]+$",
            "address_zip": r"^\d{5}(-\d{4})?$"
        }
    
    async def process_csv_file(self, 
                             csv_content: str,
                             format_type: CSVFormat = CSVFormat.STANDARD,
                             custom_mappings: Optional[Dict[str, str]] = None,
                             validation_options: Optional[Dict[str, Any]] = None) -> CSVProcessingResult:
        """
        Process CSV file for batch validation
        
        Args:
            csv_content: CSV file content
            format_type: CSV format type
            custom_mappings: Custom field mappings
            validation_options: Validation options
            
        Returns:
            CSV processing result
        """
        try:
            start_time = datetime.now()
            
            # Parse CSV content
            csv_reader = csv.DictReader(io.StringIO(csv_content))
            csv_headers = csv_reader.fieldnames or []
            
            # Determine field mappings
            field_mappings = self._determine_field_mappings(
                csv_headers, format_type, custom_mappings
            )
            
            # Process CSV rows
            processed_providers = []
            errors = []
            warnings = []
            
            for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 for header
                try:
                    provider_data = self._process_csv_row(row, field_mappings)
                    
                    # Validate provider data
                    validation_errors = self._validate_provider_data(provider_data)
                    
                    if validation_errors:
                        errors.extend([f"Row {row_num}: {error}" for error in validation_errors])
                        continue
                    
                    # Generate provider ID if missing
                    if not provider_data.get("provider_id"):
                        provider_data["provider_id"] = str(uuid.uuid4())
                    
                    processed_providers.append(provider_data)
                
                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")
                    continue
            
            # Generate warnings
            if not processed_providers:
                warnings.append("No valid provider records found in CSV")
            
            if len(processed_providers) < len(csv_reader.fieldnames or []):
                warnings.append(f"Only {len(processed_providers)} out of {len(csv_reader.fieldnames or [])} rows were processed successfully")
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return CSVProcessingResult(
                success=len(errors) == 0,
                provider_count=len(processed_providers),
                processed_providers=processed_providers,
                errors=errors,
                warnings=warnings,
                field_mappings=field_mappings,
                processing_time=processing_time
            )
        
        except Exception as e:
            logger.error(f"Failed to process CSV file: {str(e)}")
            return CSVProcessingResult(
                success=False,
                provider_count=0,
                processed_providers=[],
                errors=[f"CSV processing failed: {str(e)}"],
                warnings=[],
                field_mappings={},
                processing_time=0.0
            )
    
    def _determine_field_mappings(self, 
                                 csv_headers: List[str],
                                 format_type: CSVFormat,
                                 custom_mappings: Optional[Dict[str, str]]) -> Dict[str, str]:
        """
        Determine field mappings from CSV headers
        
        Args:
            csv_headers: CSV column headers
            format_type: CSV format type
            custom_mappings: Custom field mappings
            
        Returns:
            Field mappings dictionary
        """
        field_mappings = {}
        
        if custom_mappings:
            # Use custom mappings
            field_mappings.update(custom_mappings)
        else:
            # Auto-detect mappings based on headers
            for target_field, possible_headers in self.default_field_mappings.items():
                for header in csv_headers:
                    header_lower = header.lower().strip()
                    
                    # Check for exact match
                    if header_lower in [h.lower() for h in possible_headers]:
                        field_mappings[target_field] = header
                        break
                    
                    # Check for partial match
                    for possible_header in possible_headers:
                        if possible_header.lower() in header_lower or header_lower in possible_header.lower():
                            field_mappings[target_field] = header
                            break
        
        return field_mappings
    
    def _process_csv_row(self, row: Dict[str, str], field_mappings: Dict[str, str]) -> Dict[str, Any]:
        """
        Process a single CSV row
        
        Args:
            row: CSV row data
            field_mappings: Field mappings
            
        Returns:
            Processed provider data
        """
        provider_data = {}
        
        for target_field, csv_column in field_mappings.items():
            if csv_column in row:
                value = row[csv_column]
                
                # Clean and process value
                if value and value.strip():
                    processed_value = self._process_field_value(target_field, value.strip())
                    provider_data[target_field] = processed_value
        
        return provider_data
    
    def _process_field_value(self, field_name: str, value: str) -> Any:
        """
        Process field value based on field type
        
        Args:
            field_name: Field name
            value: Raw field value
            
        Returns:
            Processed field value
        """
        # Clean value
        value = value.strip()
        
        # Field-specific processing
        if field_name == "npi_number":
            # Remove non-numeric characters
            value = re.sub(r"[^\d]", "", value)
        
        elif field_name == "phone_primary":
            # Normalize phone number
            value = self._normalize_phone_number(value)
        
        elif field_name == "email":
            # Convert to lowercase
            value = value.lower()
        
        elif field_name == "license_number":
            # Remove extra spaces and normalize
            value = re.sub(r"\s+", " ", value).strip()
        
        elif field_name in ["address_street", "address_city", "address_state"]:
            # Normalize address fields
            value = re.sub(r"\s+", " ", value).strip()
        
        elif field_name == "address_zip":
            # Normalize ZIP code
            value = re.sub(r"[^\d\-]", "", value)
        
        elif field_name == "primary_taxonomy":
            # Normalize taxonomy/specialty
            value = re.sub(r"\s+", " ", value).strip()
        
        return value
    
    def _normalize_phone_number(self, phone: str) -> str:
        """
        Normalize phone number
        
        Args:
            phone: Raw phone number
            
        Returns:
            Normalized phone number
        """
        # Remove all non-numeric characters except +
        phone = re.sub(r"[^\d\+]", "", phone)
        
        # Handle different formats
        if phone.startswith("+1"):
            return phone
        elif phone.startswith("1") and len(phone) == 11:
            return "+" + phone
        elif len(phone) == 10:
            return "+1" + phone
        else:
            return phone
    
    def _validate_provider_data(self, provider_data: Dict[str, Any]) -> List[str]:
        """
        Validate provider data
        
        Args:
            provider_data: Provider data dictionary
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Check required fields
        required_fields = ["given_name", "family_name"]
        for field in required_fields:
            if not provider_data.get(field):
                errors.append(f"Missing required field: {field}")
        
        # Validate field formats
        for field_name, value in provider_data.items():
            if value and field_name in self.validation_patterns:
                pattern = self.validation_patterns[field_name]
                if not re.match(pattern, str(value)):
                    errors.append(f"Invalid format for {field_name}: {value}")
        
        # Validate NPI number if present
        if provider_data.get("npi_number"):
            npi = provider_data["npi_number"]
            if len(npi) != 10 or not npi.isdigit():
                errors.append(f"Invalid NPI number format: {npi}")
        
        # Validate phone number if present
        if provider_data.get("phone_primary"):
            phone = provider_data["phone_primary"]
            if not self._is_valid_phone(phone):
                errors.append(f"Invalid phone number format: {phone}")
        
        # Validate email if present
        if provider_data.get("email"):
            email = provider_data["email"]
            if not self._is_valid_email(email):
                errors.append(f"Invalid email format: {email}")
        
        return errors
    
    def _is_valid_phone(self, phone: str) -> bool:
        """
        Check if phone number is valid
        
        Args:
            phone: Phone number
            
        Returns:
            True if valid, False otherwise
        """
        # Remove non-numeric characters except +
        clean_phone = re.sub(r"[^\d\+]", "", phone)
        
        # Check various formats
        if clean_phone.startswith("+1") and len(clean_phone) == 12:
            return True
        elif clean_phone.startswith("1") and len(clean_phone) == 11:
            return True
        elif len(clean_phone) == 10:
            return True
        
        return False
    
    def _is_valid_email(self, email: str) -> bool:
        """
        Check if email is valid
        
        Args:
            email: Email address
            
        Returns:
            True if valid, False otherwise
        """
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))
    
    def generate_csv_template(self, format_type: CSVFormat = CSVFormat.STANDARD) -> str:
        """
        Generate CSV template
        
        Args:
            format_type: CSV format type
            
        Returns:
            CSV template string
        """
        if format_type == CSVFormat.STANDARD:
            headers = [
                "provider_id",
                "given_name",
                "family_name",
                "npi_number",
                "phone_primary",
                "email",
                "address_street",
                "address_city",
                "address_state",
                "address_zip",
                "license_number",
                "license_state",
                "primary_taxonomy",
                "practice_name",
                "document_path"
            ]
        elif format_type == CSVFormat.PROVIDER_DIRECTORY:
            headers = [
                "id",
                "first_name",
                "last_name",
                "npi",
                "phone",
                "email",
                "address",
                "city",
                "state",
                "zip_code",
                "license",
                "lic_state",
                "specialty",
                "organization",
                "document"
            ]
        else:
            headers = list(self.default_field_mappings.keys())
        
        # Create CSV template
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow(headers)
        
        # Write example row
        example_row = [
            "12345" if "provider_id" in headers or "id" in headers else "",
            "Dr. John" if "given_name" in headers or "first_name" in headers else "",
            "Smith" if "family_name" in headers or "last_name" in headers else "",
            "1234567890" if "npi_number" in headers or "npi" in headers else "",
            "+1-555-123-4567" if "phone_primary" in headers or "phone" in headers else "",
            "john.smith@example.com" if "email" in headers else "",
            "123 Main Street" if "address_street" in headers or "address" in headers else "",
            "San Francisco" if "address_city" in headers or "city" in headers else "",
            "CA" if "address_state" in headers or "state" in headers else "",
            "94102" if "address_zip" in headers or "zip_code" in headers else "",
            "A123456" if "license_number" in headers or "license" in headers else "",
            "CA" if "license_state" in headers or "lic_state" in headers else "",
            "Internal Medicine" if "primary_taxonomy" in headers or "specialty" in headers else "",
            "Example Medical Group" if "practice_name" in headers or "organization" in headers else "",
            "/path/to/document.pdf" if "document_path" in headers or "document" in headers else ""
        ]
        
        writer.writerow(example_row)
        
        return output.getvalue()
    
    def get_supported_formats(self) -> List[Dict[str, Any]]:
        """
        Get supported CSV formats
        
        Returns:
            List of supported formats
        """
        return [
            {
                "format": CSVFormat.STANDARD.value,
                "name": "Standard Format",
                "description": "Standard provider validation CSV format",
                "required_fields": ["given_name", "family_name"],
                "optional_fields": [
                    "provider_id", "npi_number", "phone_primary", "email",
                    "address_street", "address_city", "address_state", "address_zip",
                    "license_number", "license_state", "primary_taxonomy", "practice_name", "document_path"
                ]
            },
            {
                "format": CSVFormat.PROVIDER_DIRECTORY.value,
                "name": "Provider Directory Format",
                "description": "Provider directory export format",
                "required_fields": ["first_name", "last_name"],
                "optional_fields": [
                    "id", "npi", "phone", "email", "address", "city", "state", "zip_code",
                    "license", "lic_state", "specialty", "organization", "document"
                ]
            },
            {
                "format": CSVFormat.CUSTOM.value,
                "name": "Custom Format",
                "description": "Custom field mapping format",
                "required_fields": ["given_name", "family_name"],
                "optional_fields": ["All standard fields with custom column names"]
            }
        ]
    
    def validate_csv_structure(self, csv_content: str) -> Dict[str, Any]:
        """
        Validate CSV structure
        
        Args:
            csv_content: CSV file content
            
        Returns:
            Validation result
        """
        try:
            csv_reader = csv.DictReader(io.StringIO(csv_content))
            headers = csv_reader.fieldnames or []
            
            # Check for required headers
            required_headers = ["given_name", "family_name"]
            missing_headers = []
            
            for required in required_headers:
                if not any(required in h.lower() for h in headers):
                    missing_headers.append(required)
            
            # Check for duplicate headers
            duplicate_headers = []
            seen_headers = set()
            for header in headers:
                header_lower = header.lower()
                if header_lower in seen_headers:
                    duplicate_headers.append(header)
                else:
                    seen_headers.add(header_lower)
            
            # Count rows
            row_count = sum(1 for row in csv_reader)
            
            return {
                "valid": len(missing_headers) == 0 and len(duplicate_headers) == 0,
                "headers": headers,
                "row_count": row_count,
                "missing_headers": missing_headers,
                "duplicate_headers": duplicate_headers,
                "field_mappings": self._determine_field_mappings(headers, CSVFormat.STANDARD, None)
            }
        
        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
                "headers": [],
                "row_count": 0,
                "missing_headers": [],
                "duplicate_headers": [],
                "field_mappings": {}
            }


# Global CSV processor instance
csv_processor = CSVProcessor()


# Example usage and testing functions
async def example_csv_processor():
    """
    Example function demonstrating CSV processing
    """
    print("=" * 60)
    print("📊 CSV PROCESSOR EXAMPLE")
    print("=" * 60)
    
    # Initialize CSV processor
    processor = CSVProcessor()
    
    # Sample CSV content
    csv_content = """provider_id,given_name,family_name,npi_number,phone_primary,email,address_street,address_city,address_state,address_zip,license_number,license_state,primary_taxonomy,practice_name
12345,Dr. John,Smith,1234567890,+1-555-123-4567,john.smith@example.com,123 Main Street,San Francisco,CA,94102,A123456,CA,Internal Medicine,Example Medical Group
67890,Dr. Jane,Doe,0987654321,+1-555-987-6543,jane.doe@example.com,456 Oak Avenue,Los Angeles,CA,90210,B789012,CA,Cardiology,Heart Care Associates"""
    
    print("\n📋 Processing CSV Content...")
    print(f"   CSV Length: {len(csv_content)} characters")
    
    # Process CSV
    result = await processor.process_csv_file(csv_content)
    
    print(f"\n📊 Processing Results:")
    print(f"   Success: {result.success}")
    print(f"   Provider Count: {result.provider_count}")
    print(f"   Processing Time: {result.processing_time:.2f}s")
    print(f"   Errors: {len(result.errors)}")
    print(f"   Warnings: {len(result.warnings)}")
    
    if result.errors:
        print(f"\n❌ Errors:")
        for error in result.errors:
            print(f"   • {error}")
    
    if result.warnings:
        print(f"\n⚠️  Warnings:")
        for warning in result.warnings:
            print(f"   • {warning}")
    
    print(f"\n🔗 Field Mappings:")
    for target_field, csv_column in result.field_mappings.items():
        print(f"   {target_field} -> {csv_column}")
    
    print(f"\n📋 Processed Providers:")
    for i, provider in enumerate(result.processed_providers, 1):
        print(f"   Provider {i}: {provider.get('given_name')} {provider.get('family_name')}")
        print(f"      NPI: {provider.get('npi_number')}")
        print(f"      Phone: {provider.get('phone_primary')}")
        print(f"      Email: {provider.get('email')}")
    
    # Generate CSV template
    print(f"\n📄 Generating CSV Template...")
    template = processor.generate_csv_template(CSVFormat.STANDARD)
    print(f"   Template Length: {len(template)} characters")
    
    # Get supported formats
    print(f"\n📋 Supported Formats:")
    formats = processor.get_supported_formats()
    for format_info in formats:
        print(f"   {format_info['name']}: {format_info['description']}")
        print(f"      Required: {', '.join(format_info['required_fields'])}")
    
    # Validate CSV structure
    print(f"\n🔍 Validating CSV Structure...")
    validation = processor.validate_csv_structure(csv_content)
    print(f"   Valid: {validation['valid']}")
    print(f"   Headers: {len(validation['headers'])}")
    print(f"   Row Count: {validation['row_count']}")
    print(f"   Field Mappings: {len(validation['field_mappings'])}")


if __name__ == "__main__":
    # Run examples
    print("CSV Processor - Examples")
    print("To run examples:")
    print("1. Install dependencies: pip install uuid")
    print("2. Run: python -c 'from utils.csv_processor import example_csv_processor; asyncio.run(example_csv_processor())'")
