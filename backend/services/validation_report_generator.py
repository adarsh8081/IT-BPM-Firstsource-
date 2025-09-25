"""
Validation Report Generator

This module generates comprehensive validation reports for providers with
detailed field analysis, confidence scoring, and actionable insights.
"""

import asyncio
import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

from services.validator import WorkerTaskResult, ValidationReport, WorkerTaskType
from models.provider import Provider
from models.validation import ValidationResult

logger = logging.getLogger(__name__)


class ReportSeverity(Enum):
    """Report severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationFlag(Enum):
    """Validation flag types"""
    MISSING_CRITICAL_FIELD = "missing_critical_field"
    LOW_CONFIDENCE = "low_confidence"
    VALIDATION_FAILED = "validation_failed"
    DATA_INCONSISTENCY = "data_inconsistency"
    POTENTIAL_DUPLICATE = "potential_duplicate"
    EXPIRED_LICENSE = "expired_license"
    SUSPENDED_LICENSE = "suspended_license"
    INVALID_PHONE = "invalid_phone"
    INVALID_EMAIL = "invalid_email"
    ADDRESS_NOT_FOUND = "address_not_found"
    OCR_FAILED = "ocr_failed"
    NPI_NOT_FOUND = "npi_not_found"


@dataclass
class FieldAnalysis:
    """Field analysis result"""
    field_name: str
    original_value: Optional[str]
    validated_value: Optional[str]
    confidence: float
    validation_status: str
    validation_source: str
    validation_timestamp: datetime
    issues: List[str]
    suggestions: List[str]


@dataclass
class ValidationInsight:
    """Validation insight"""
    type: str
    severity: ReportSeverity
    title: str
    description: str
    field_name: Optional[str] = None
    confidence_impact: float = 0.0
    action_required: bool = False


@dataclass
class ValidationSummary:
    """Validation summary statistics"""
    total_fields: int
    validated_fields: int
    high_confidence_fields: int
    medium_confidence_fields: int
    low_confidence_fields: int
    failed_validations: int
    overall_confidence: float
    validation_status: str
    processing_time: float


@dataclass
class DetailedValidationReport:
    """Detailed validation report"""
    report_id: str
    provider_id: str
    job_id: str
    generated_at: datetime
    summary: ValidationSummary
    field_analyses: List[FieldAnalysis]
    insights: List[ValidationInsight]
    flags: List[ValidationFlag]
    recommendations: List[str]
    metadata: Dict[str, Any]


class ValidationReportGenerator:
    """
    Validation Report Generator
    
    Generates comprehensive validation reports with detailed analysis,
    confidence scoring, and actionable insights for provider data.
    """
    
    def __init__(self):
        """Initialize Validation Report Generator"""
        self.critical_fields = [
            "npi_number",
            "given_name",
            "family_name",
            "license_number",
            "license_state"
        ]
        
        self.high_importance_fields = [
            "phone_primary",
            "email",
            "address_street",
            "primary_taxonomy"
        ]
        
        self.confidence_thresholds = {
            "high": 0.8,
            "medium": 0.6,
            "low": 0.4
        }
        
        self.validation_weights = {
            WorkerTaskType.NPI_CHECK: 0.4,
            WorkerTaskType.GOOGLE_PLACES: 0.25,
            WorkerTaskType.STATE_BOARD_CHECK: 0.15,
            WorkerTaskType.ENRICHMENT_LOOKUP: 0.2
        }
    
    def generate_validation_report(self, 
                                 provider_id: str,
                                 job_id: str,
                                 worker_results: List[WorkerTaskResult],
                                 original_data: Dict[str, Any],
                                 processing_time: float) -> DetailedValidationReport:
        """
        Generate comprehensive validation report
        
        Args:
            provider_id: Provider ID
            job_id: Job ID
            worker_results: List of worker task results
            original_data: Original provider data
            processing_time: Total processing time
            
        Returns:
            Detailed validation report
        """
        try:
            # Generate report ID
            report_id = str(uuid.uuid4())
            
            # Analyze fields
            field_analyses = self._analyze_fields(worker_results, original_data)
            
            # Generate insights
            insights = self._generate_insights(field_analyses, worker_results)
            
            # Generate flags
            flags = self._generate_flags(field_analyses, worker_results)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(insights, flags)
            
            # Create summary
            summary = self._create_summary(field_analyses, worker_results, processing_time)
            
            # Create metadata
            metadata = self._create_metadata(worker_results, original_data)
            
            # Create detailed report
            report = DetailedValidationReport(
                report_id=report_id,
                provider_id=provider_id,
                job_id=job_id,
                generated_at=datetime.now(),
                summary=summary,
                field_analyses=field_analyses,
                insights=insights,
                flags=flags,
                recommendations=recommendations,
                metadata=metadata
            )
            
            logger.info(f"Generated validation report {report_id} for provider {provider_id}")
            return report
        
        except Exception as e:
            logger.error(f"Failed to generate validation report for provider {provider_id}: {str(e)}")
            raise
    
    def _analyze_fields(self, 
                       worker_results: List[WorkerTaskResult],
                       original_data: Dict[str, Any]) -> List[FieldAnalysis]:
        """
        Analyze individual fields from worker results
        
        Args:
            worker_results: List of worker task results
            original_data: Original provider data
            
        Returns:
            List of field analyses
        """
        field_analyses = []
        field_data = {}
        
        # Collect field data from all workers
        for result in worker_results:
            if result.success:
                for field_name, field_value in result.normalized_fields.items():
                    if field_name not in field_data:
                        field_data[field_name] = {
                            'validated_value': field_value,
                            'confidence': result.field_confidence.get(field_name, 0.0),
                            'validation_source': result.task_type.value,
                            'validation_timestamp': result.timestamp
                        }
                    else:
                        # Use higher confidence value
                        current_confidence = field_data[field_name]['confidence']
                        new_confidence = result.field_confidence.get(field_name, 0.0)
                        
                        if new_confidence > current_confidence:
                            field_data[field_name].update({
                                'validated_value': field_value,
                                'confidence': new_confidence,
                                'validation_source': result.task_type.value,
                                'validation_timestamp': result.timestamp
                            })
        
        # Create field analyses
        for field_name, data in field_data.items():
            original_value = original_data.get(field_name)
            
            # Determine validation status
            if data['confidence'] >= self.confidence_thresholds['high']:
                validation_status = 'valid'
            elif data['confidence'] >= self.confidence_thresholds['medium']:
                validation_status = 'warning'
            else:
                validation_status = 'invalid'
            
            # Analyze issues and suggestions
            issues, suggestions = self._analyze_field_issues(
                field_name, original_value, data['validated_value'], data['confidence']
            )
            
            field_analysis = FieldAnalysis(
                field_name=field_name,
                original_value=original_value,
                validated_value=data['validated_value'],
                confidence=data['confidence'],
                validation_status=validation_status,
                validation_source=data['validation_source'],
                validation_timestamp=data['validation_timestamp'],
                issues=issues,
                suggestions=suggestions
            )
            
            field_analyses.append(field_analysis)
        
        return field_analyses
    
    def _analyze_field_issues(self, 
                            field_name: str,
                            original_value: Optional[str],
                            validated_value: Optional[str],
                            confidence: float) -> Tuple[List[str], List[str]]:
        """
        Analyze issues and suggestions for a field
        
        Args:
            field_name: Field name
            original_value: Original field value
            validated_value: Validated field value
            confidence: Confidence score
            
        Returns:
            Tuple of (issues, suggestions)
        """
        issues = []
        suggestions = []
        
        # Check for missing values
        if not validated_value or validated_value.strip() == "":
            issues.append(f"{field_name} is missing or empty")
            if field_name in self.critical_fields:
                suggestions.append(f"Provide {field_name} as it is required for validation")
            else:
                suggestions.append(f"Consider providing {field_name} for better validation")
        
        # Check confidence levels
        if confidence < self.confidence_thresholds['low']:
            issues.append(f"{field_name} has very low confidence ({confidence:.2f})")
            suggestions.append(f"Verify {field_name} data quality and source")
        elif confidence < self.confidence_thresholds['medium']:
            issues.append(f"{field_name} has low confidence ({confidence:.2f})")
            suggestions.append(f"Review {field_name} for accuracy")
        
        # Field-specific validations
        if field_name == "npi_number":
            if validated_value and len(validated_value) != 10:
                issues.append("NPI number should be 10 digits")
                suggestions.append("Verify NPI number format")
        
        elif field_name == "phone_primary":
            if validated_value and not validated_value.startswith("+"):
                issues.append("Phone number should be in E.164 format")
                suggestions.append("Format phone number as +1XXXXXXXXXX")
        
        elif field_name == "email":
            if validated_value and "@" not in validated_value:
                issues.append("Invalid email format")
                suggestions.append("Provide valid email address")
        
        elif field_name == "license_number":
            if validated_value and len(validated_value) < 3:
                issues.append("License number appears too short")
                suggestions.append("Verify license number format")
        
        return issues, suggestions
    
    def _generate_insights(self, 
                          field_analyses: List[FieldAnalysis],
                          worker_results: List[WorkerTaskResult]) -> List[ValidationInsight]:
        """
        Generate validation insights
        
        Args:
            field_analyses: List of field analyses
            worker_results: List of worker task results
            
        Returns:
            List of validation insights
        """
        insights = []
        
        # Analyze missing critical fields
        missing_critical_fields = [
            fa.field_name for fa in field_analyses 
            if fa.field_name in self.critical_fields and not fa.validated_value
        ]
        
        if missing_critical_fields:
            insights.append(ValidationInsight(
                type="missing_critical_fields",
                severity=ReportSeverity.CRITICAL,
                title="Missing Critical Fields",
                description=f"Critical fields are missing: {', '.join(missing_critical_fields)}",
                confidence_impact=-0.3,
                action_required=True
            ))
        
        # Analyze low confidence fields
        low_confidence_fields = [
            fa for fa in field_analyses 
            if fa.confidence < self.confidence_thresholds['medium']
        ]
        
        if low_confidence_fields:
            insights.append(ValidationInsight(
                type="low_confidence_fields",
                severity=ReportSeverity.WARNING,
                title="Low Confidence Fields",
                description=f"{len(low_confidence_fields)} fields have low confidence scores",
                confidence_impact=-0.2,
                action_required=False
            ))
        
        # Analyze failed validations
        failed_validations = [r for r in worker_results if not r.success]
        
        if failed_validations:
            insights.append(ValidationInsight(
                type="failed_validations",
                severity=ReportSeverity.ERROR,
                title="Failed Validations",
                description=f"{len(failed_validations)} validation tasks failed",
                confidence_impact=-0.4,
                action_required=True
            ))
        
        # Analyze data consistency
        consistency_issues = self._check_data_consistency(field_analyses)
        
        if consistency_issues:
            insights.append(ValidationInsight(
                type="data_inconsistency",
                severity=ReportSeverity.WARNING,
                title="Data Inconsistency",
                description=f"Found {len(consistency_issues)} data consistency issues",
                confidence_impact=-0.1,
                action_required=False
            ))
        
        # Analyze validation coverage
        validation_coverage = len(field_analyses) / len(self.critical_fields + self.high_importance_fields)
        
        if validation_coverage < 0.8:
            insights.append(ValidationInsight(
                type="low_coverage",
                severity=ReportSeverity.WARNING,
                title="Low Validation Coverage",
                description=f"Only {validation_coverage:.1%} of important fields were validated",
                confidence_impact=-0.15,
                action_required=False
            ))
        
        return insights
    
    def _check_data_consistency(self, field_analyses: List[FieldAnalysis]) -> List[str]:
        """
        Check for data consistency issues
        
        Args:
            field_analyses: List of field analyses
            
        Returns:
            List of consistency issues
        """
        issues = []
        
        # Check name consistency
        given_name_analysis = next((fa for fa in field_analyses if fa.field_name == "given_name"), None)
        family_name_analysis = next((fa for fa in field_analyses if fa.field_name == "family_name"), None)
        
        if given_name_analysis and family_name_analysis:
            if given_name_analysis.validated_value and family_name_analysis.validated_value:
                # Check if names are too similar (potential duplicate)
                if given_name_analysis.validated_value.lower() == family_name_analysis.validated_value.lower():
                    issues.append("Given name and family name are identical")
        
        # Check address consistency
        address_analysis = next((fa for fa in field_analyses if fa.field_name == "address_street"), None)
        
        if address_analysis and address_analysis.validated_value:
            # Check for common address issues
            address = address_analysis.validated_value.lower()
            if "po box" in address and "street" in address:
                issues.append("Address contains both PO Box and street information")
        
        return issues
    
    def _generate_flags(self, 
                       field_analyses: List[FieldAnalysis],
                       worker_results: List[WorkerTaskResult]) -> List[ValidationFlag]:
        """
        Generate validation flags
        
        Args:
            field_analyses: List of field analyses
            worker_results: List of worker task results
            
        Returns:
            List of validation flags
        """
        flags = []
        
        # Check for missing critical fields
        missing_critical_fields = [
            fa.field_name for fa in field_analyses 
            if fa.field_name in self.critical_fields and not fa.validated_value
        ]
        
        if missing_critical_fields:
            flags.append(ValidationFlag.MISSING_CRITICAL_FIELD)
        
        # Check for low confidence
        low_confidence_fields = [
            fa for fa in field_analyses 
            if fa.confidence < self.confidence_thresholds['medium']
        ]
        
        if len(low_confidence_fields) > len(field_analyses) * 0.5:
            flags.append(ValidationFlag.LOW_CONFIDENCE)
        
        # Check for failed validations
        failed_validations = [r for r in worker_results if not r.success]
        
        if failed_validations:
            flags.append(ValidationFlag.VALIDATION_FAILED)
        
        # Check for specific field issues
        for analysis in field_analyses:
            if analysis.field_name == "npi_number" and not analysis.validated_value:
                flags.append(ValidationFlag.NPI_NOT_FOUND)
            
            elif analysis.field_name == "phone_primary" and analysis.validation_status == "invalid":
                flags.append(ValidationFlag.INVALID_PHONE)
            
            elif analysis.field_name == "email" and analysis.validation_status == "invalid":
                flags.append(ValidationFlag.INVALID_EMAIL)
            
            elif analysis.field_name == "address_street" and not analysis.validated_value:
                flags.append(ValidationFlag.ADDRESS_NOT_FOUND)
            
            elif analysis.field_name == "license_number":
                # Check for expired or suspended license
                if analysis.validated_value:
                    # This would need to be enhanced with actual license status checking
                    pass
        
        # Check for OCR failures
        ocr_results = [r for r in worker_results if r.task_type == WorkerTaskType.OCR_PROCESSING]
        if ocr_results and not any(r.success for r in ocr_results):
            flags.append(ValidationFlag.OCR_FAILED)
        
        return flags
    
    def _generate_recommendations(self, 
                                 insights: List[ValidationInsight],
                                 flags: List[ValidationFlag]) -> List[str]:
        """
        Generate actionable recommendations
        
        Args:
            insights: List of validation insights
            flags: List of validation flags
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        # Generate recommendations based on flags
        if ValidationFlag.MISSING_CRITICAL_FIELD in flags:
            recommendations.append("Provide missing critical fields (NPI, name, license) for complete validation")
        
        if ValidationFlag.LOW_CONFIDENCE in flags:
            recommendations.append("Review and improve data quality for low-confidence fields")
        
        if ValidationFlag.VALIDATION_FAILED in flags:
            recommendations.append("Investigate and resolve failed validation tasks")
        
        if ValidationFlag.NPI_NOT_FOUND in flags:
            recommendations.append("Verify NPI number or check if provider is registered in NPI Registry")
        
        if ValidationFlag.INVALID_PHONE in flags:
            recommendations.append("Format phone number in E.164 format (+1XXXXXXXXXX)")
        
        if ValidationFlag.INVALID_EMAIL in flags:
            recommendations.append("Provide valid email address with proper format")
        
        if ValidationFlag.ADDRESS_NOT_FOUND in flags:
            recommendations.append("Verify address format and completeness")
        
        if ValidationFlag.OCR_FAILED in flags:
            recommendations.append("Improve document quality or try alternative OCR processing")
        
        # Generate recommendations based on insights
        for insight in insights:
            if insight.action_required:
                if insight.type == "missing_critical_fields":
                    recommendations.append("Complete missing critical fields to enable full validation")
                elif insight.type == "failed_validations":
                    recommendations.append("Retry failed validation tasks or check data sources")
                elif insight.type == "data_inconsistency":
                    recommendations.append("Review and correct data inconsistencies")
        
        # General recommendations
        if not recommendations:
            recommendations.append("Data validation completed successfully")
        
        return recommendations
    
    def _create_summary(self, 
                       field_analyses: List[FieldAnalysis],
                       worker_results: List[WorkerTaskResult],
                       processing_time: float) -> ValidationSummary:
        """
        Create validation summary
        
        Args:
            field_analyses: List of field analyses
            worker_results: List of worker task results
            processing_time: Total processing time
            
        Returns:
            Validation summary
        """
        total_fields = len(field_analyses)
        validated_fields = len([fa for fa in field_analyses if fa.validated_value])
        
        high_confidence_fields = len([
            fa for fa in field_analyses 
            if fa.confidence >= self.confidence_thresholds['high']
        ])
        
        medium_confidence_fields = len([
            fa for fa in field_analyses 
            if self.confidence_thresholds['medium'] <= fa.confidence < self.confidence_thresholds['high']
        ])
        
        low_confidence_fields = len([
            fa for fa in field_analyses 
            if fa.confidence < self.confidence_thresholds['medium']
        ])
        
        failed_validations = len([r for r in worker_results if not r.success])
        
        # Calculate overall confidence
        if field_analyses:
            overall_confidence = sum(fa.confidence for fa in field_analyses) / len(field_analyses)
        else:
            overall_confidence = 0.0
        
        # Determine validation status
        if overall_confidence >= self.confidence_thresholds['high']:
            validation_status = "valid"
        elif overall_confidence >= self.confidence_thresholds['medium']:
            validation_status = "warning"
        else:
            validation_status = "invalid"
        
        return ValidationSummary(
            total_fields=total_fields,
            validated_fields=validated_fields,
            high_confidence_fields=high_confidence_fields,
            medium_confidence_fields=medium_confidence_fields,
            low_confidence_fields=low_confidence_fields,
            failed_validations=failed_validations,
            overall_confidence=overall_confidence,
            validation_status=validation_status,
            processing_time=processing_time
        )
    
    def _create_metadata(self, 
                        worker_results: List[WorkerTaskResult],
                        original_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create report metadata
        
        Args:
            worker_results: List of worker task results
            original_data: Original provider data
            
        Returns:
            Metadata dictionary
        """
        return {
            "worker_results_count": len(worker_results),
            "successful_workers": len([r for r in worker_results if r.success]),
            "failed_workers": len([r for r in worker_results if not r.success]),
            "worker_types": [r.task_type.value for r in worker_results],
            "original_data_fields": list(original_data.keys()),
            "validation_weights": {k.value: v for k, v in self.validation_weights.items()},
            "confidence_thresholds": self.confidence_thresholds,
            "report_version": "1.0"
        }
    
    def export_report_to_json(self, report: DetailedValidationReport) -> str:
        """
        Export validation report to JSON
        
        Args:
            report: Validation report
            
        Returns:
            JSON string
        """
        try:
            # Convert report to dictionary
            report_dict = asdict(report)
            
            # Convert datetime objects to ISO format
            report_dict['generated_at'] = report.generated_at.isoformat()
            
            for field_analysis in report_dict['field_analyses']:
                field_analysis['validation_timestamp'] = field_analysis['validation_timestamp'].isoformat()
            
            # Convert enums to values
            report_dict['flags'] = [flag.value for flag in report.flags]
            
            for insight in report_dict['insights']:
                insight['severity'] = insight['severity'].value
            
            return json.dumps(report_dict, indent=2, default=str)
        
        except Exception as e:
            logger.error(f"Failed to export report to JSON: {str(e)}")
            raise
    
    def export_report_to_summary(self, report: DetailedValidationReport) -> Dict[str, Any]:
        """
        Export validation report summary
        
        Args:
            report: Validation report
            
        Returns:
            Summary dictionary
        """
        return {
            "report_id": report.report_id,
            "provider_id": report.provider_id,
            "job_id": report.job_id,
            "generated_at": report.generated_at.isoformat(),
            "summary": asdict(report.summary),
            "flags": [flag.value for flag in report.flags],
            "recommendations": report.recommendations,
            "critical_insights": [
                {
                    "title": insight.title,
                    "severity": insight.severity.value,
                    "action_required": insight.action_required
                }
                for insight in report.insights
                if insight.severity in [ReportSeverity.CRITICAL, ReportSeverity.ERROR]
            ]
        }


# Global validation report generator instance
validation_report_generator = ValidationReportGenerator()


# Example usage and testing functions
async def example_validation_report_generator():
    """
    Example function demonstrating validation report generation
    """
    print("=" * 60)
    print("📊 VALIDATION REPORT GENERATOR EXAMPLE")
    print("=" * 60)
    
    # Initialize report generator
    generator = ValidationReportGenerator()
    
    # Sample worker results
    worker_results = [
        WorkerTaskResult(
            task_type=WorkerTaskType.NPI_CHECK,
            provider_id="12345",
            success=True,
            confidence=0.9,
            normalized_fields={
                "npi_number": "1234567890",
                "given_name": "John",
                "family_name": "Smith"
            },
            field_confidence={
                "npi_number": 0.95,
                "given_name": 0.90,
                "family_name": 0.90
            },
            processing_time=2.5
        ),
        WorkerTaskResult(
            task_type=WorkerTaskType.GOOGLE_PLACES,
            provider_id="12345",
            success=True,
            confidence=0.8,
            normalized_fields={
                "address_street": "123 Main St, San Francisco, CA 94102",
                "place_id": "ChIJ1234567890"
            },
            field_confidence={
                "address_street": 0.85,
                "place_id": 0.95
            },
            processing_time=1.8
        ),
        WorkerTaskResult(
            task_type=WorkerTaskType.STATE_BOARD_CHECK,
            provider_id="12345",
            success=False,
            confidence=0.0,
            normalized_fields={},
            field_confidence={},
            error_message="License not found",
            processing_time=3.2
        )
    ]
    
    # Sample original data
    original_data = {
        "provider_id": "12345",
        "given_name": "Dr. John Smith",
        "family_name": "Smith",
        "npi_number": "1234567890",
        "phone_primary": "(555) 123-4567",
        "email": "john.smith@example.com",
        "address_street": "123 Main Street, San Francisco, CA",
        "license_number": "A123456",
        "license_state": "CA"
    }
    
    print("\n📋 Generating Validation Report...")
    
    # Generate report
    report = generator.generate_validation_report(
        provider_id="12345",
        job_id="job_12345",
        worker_results=worker_results,
        original_data=original_data,
        processing_time=7.5
    )
    
    print(f"   Report ID: {report.report_id}")
    print(f"   Generated At: {report.generated_at}")
    
    # Display summary
    print(f"\n📊 Validation Summary:")
    print(f"   Total Fields: {report.summary.total_fields}")
    print(f"   Validated Fields: {report.summary.validated_fields}")
    print(f"   High Confidence: {report.summary.high_confidence_fields}")
    print(f"   Medium Confidence: {report.summary.medium_confidence_fields}")
    print(f"   Low Confidence: {report.summary.low_confidence_fields}")
    print(f"   Failed Validations: {report.summary.failed_validations}")
    print(f"   Overall Confidence: {report.summary.overall_confidence:.2f}")
    print(f"   Validation Status: {report.summary.validation_status}")
    print(f"   Processing Time: {report.summary.processing_time:.2f}s")
    
    # Display insights
    print(f"\n💡 Validation Insights:")
    for insight in report.insights:
        print(f"   {insight.severity.value.upper()}: {insight.title}")
        print(f"      {insight.description}")
        print(f"      Action Required: {insight.action_required}")
    
    # Display flags
    print(f"\n🚩 Validation Flags:")
    for flag in report.flags:
        print(f"   {flag.value}")
    
    # Display recommendations
    print(f"\n💡 Recommendations:")
    for recommendation in report.recommendations:
        print(f"   • {recommendation}")
    
    # Export to JSON
    print(f"\n📄 Exporting Report to JSON...")
    json_report = generator.export_report_to_json(report)
    print(f"   JSON Length: {len(json_report)} characters")
    
    # Export summary
    print(f"\n📋 Exporting Summary...")
    summary = generator.export_report_to_summary(report)
    print(f"   Summary Keys: {list(summary.keys())}")


if __name__ == "__main__":
    # Run examples
    print("Validation Report Generator - Examples")
    print("To run examples:")
    print("1. Install dependencies: pip install uuid")
    print("2. Run: python -c 'from services.validation_report_generator import example_validation_report_generator; asyncio.run(example_validation_report_generator())'")
