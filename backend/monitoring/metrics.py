"""
Prometheus Metrics Collection for Provider Validation Application

This module provides comprehensive metrics collection for monitoring
validation performance, system health, and business KPIs.
"""

import time
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from dataclasses import dataclass
from prometheus_client import (
    Counter, Histogram, Gauge, Summary, Info,
    generate_latest, CONTENT_TYPE_LATEST, CollectorRegistry
)
import logging

logger = logging.getLogger(__name__)

@dataclass
class ValidationMetrics:
    """Validation metrics data structure"""
    provider_id: str
    validation_duration: float
    overall_confidence: float
    validation_status: str
    source_count: int
    error_count: int

class MetricsCollector:
    """Prometheus metrics collector for the validation system"""
    
    def __init__(self):
        """Initialize metrics collector"""
        self.registry = CollectorRegistry()
        self._setup_metrics()
    
    def _setup_metrics(self):
        """Setup Prometheus metrics"""
        
        # Validation metrics
        self.validations_total = Counter(
            'provider_validations_total',
            'Total number of provider validations',
            ['status', 'confidence_level'],
            registry=self.registry
        )
        
        self.validation_duration = Histogram(
            'provider_validation_duration_seconds',
            'Time spent on provider validation',
            ['provider_type', 'validation_type'],
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
            registry=self.registry
        )
        
        self.validations_per_second = Gauge(
            'provider_validations_per_second',
            'Current validation rate (validations per second)',
            registry=self.registry
        )
        
        # Confidence metrics
        self.confidence_distribution = Histogram(
            'provider_validation_confidence',
            'Distribution of validation confidence scores',
            ['confidence_range'],
            buckets=[0.1, 0.3, 0.5, 0.7, 0.8, 0.9, 0.95, 1.0],
            registry=self.registry
        )
        
        self.high_confidence_percentage = Gauge(
            'provider_high_confidence_percentage',
            'Percentage of providers with overall confidence > 0.8',
            registry=self.registry
        )
        
        # Queue metrics
        self.manual_review_queue_length = Gauge(
            'manual_review_queue_length',
            'Number of providers in manual review queue',
            ['queue_type'],
            registry=self.registry
        )
        
        self.queue_processing_time = Histogram(
            'queue_processing_time_seconds',
            'Time spent processing queue items',
            ['queue_type'],
            buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 300.0, 600.0, 1800.0],
            registry=self.registry
        )
        
        # API metrics
        self.api_requests_total = Counter(
            'api_requests_total',
            'Total number of API requests',
            ['method', 'endpoint', 'status_code'],
            registry=self.registry
        )
        
        self.api_request_duration = Histogram(
            'api_request_duration_seconds',
            'API request duration',
            ['method', 'endpoint'],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
            registry=self.registry
        )
        
        # External service metrics
        self.external_api_calls_total = Counter(
            'external_api_calls_total',
            'Total number of external API calls',
            ['service', 'endpoint', 'status'],
            registry=self.registry
        )
        
        self.external_api_duration = Histogram(
            'external_api_duration_seconds',
            'External API call duration',
            ['service', 'endpoint'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
            registry=self.registry
        )
        
        self.external_api_errors = Counter(
            'external_api_errors_total',
            'Total number of external API errors',
            ['service', 'error_type'],
            registry=self.registry
        )
        
        # System metrics
        self.active_workers = Gauge(
            'validation_workers_active',
            'Number of active validation workers',
            ['worker_type'],
            registry=self.registry
        )
        
        self.job_queue_size = Gauge(
            'job_queue_size',
            'Number of jobs in queue',
            ['queue_name'],
            registry=self.registry
        )
        
        self.failed_jobs_total = Counter(
            'failed_jobs_total',
            'Total number of failed jobs',
            ['job_type', 'error_type'],
            registry=self.registry
        )
        
        # Business metrics
        self.providers_processed_total = Counter(
            'providers_processed_total',
            'Total number of providers processed',
            ['status', 'source'],
            registry=self.registry
        )
        
        self.data_quality_score = Gauge(
            'data_quality_score',
            'Overall data quality score (0-1)',
            registry=self.registry
        )
        
        self.compliance_violations = Counter(
            'compliance_violations_total',
            'Total number of compliance violations',
            ['violation_type', 'severity'],
            registry=self.registry
        )
        
        # Database metrics
        self.database_connections = Gauge(
            'database_connections_active',
            'Number of active database connections',
            registry=self.registry
        )
        
        self.database_query_duration = Histogram(
            'database_query_duration_seconds',
            'Database query duration',
            ['query_type'],
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
            registry=self.registry
        )
        
        # Cache metrics
        self.cache_hits_total = Counter(
            'cache_hits_total',
            'Total number of cache hits',
            ['cache_type'],
            registry=self.registry
        )
        
        self.cache_misses_total = Counter(
            'cache_misses_total',
            'Total number of cache misses',
            ['cache_type'],
            registry=self.registry
        )
        
        # Security metrics
        self.security_events_total = Counter(
            'security_events_total',
            'Total number of security events',
            ['event_type', 'severity'],
            registry=self.registry
        )
        
        self.pii_access_total = Counter(
            'pii_access_total',
            'Total number of PII access events',
            ['data_type', 'access_type'],
            registry=self.registry
        )
        
        # Application info
        self.app_info = Info(
            'provider_validation_app_info',
            'Application information',
            registry=self.registry
        )
        
        # Set application info
        self.app_info.info({
            'version': '1.0.0',
            'environment': 'production',
            'build_date': datetime.now(timezone.utc).isoformat()
        })
    
    def record_validation(self, metrics: ValidationMetrics):
        """Record validation metrics"""
        try:
            # Determine confidence level bucket
            confidence_level = self._get_confidence_level(metrics.overall_confidence)
            
            # Record validation count
            self.validations_total.labels(
                status=metrics.validation_status,
                confidence_level=confidence_level
            ).inc()
            
            # Record validation duration
            self.validation_duration.labels(
                provider_type='standard',
                validation_type='full'
            ).observe(metrics.validation_duration)
            
            # Record confidence distribution
            self.confidence_distribution.labels(
                confidence_range=confidence_level
            ).observe(metrics.overall_confidence)
            
            # Record source and error counts
            self.providers_processed_total.labels(
                status=metrics.validation_status,
                source='validation_pipeline'
            ).inc()
            
            logger.debug(f"Recorded validation metrics for provider {metrics.provider_id}")
            
        except Exception as e:
            logger.error(f"Failed to record validation metrics: {e}")
    
    def record_api_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record API request metrics"""
        try:
            self.api_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status_code=str(status_code)
            ).inc()
            
            self.api_request_duration.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
            
        except Exception as e:
            logger.error(f"Failed to record API request metrics: {e}")
    
    def record_external_api_call(self, service: str, endpoint: str, duration: float, success: bool):
        """Record external API call metrics"""
        try:
            status = 'success' if success else 'error'
            
            self.external_api_calls_total.labels(
                service=service,
                endpoint=endpoint,
                status=status
            ).inc()
            
            self.external_api_duration.labels(
                service=service,
                endpoint=endpoint
            ).observe(duration)
            
            if not success:
                self.external_api_errors.labels(
                    service=service,
                    error_type='api_error'
                ).inc()
                
        except Exception as e:
            logger.error(f"Failed to record external API call metrics: {e}")
    
    def update_queue_length(self, queue_type: str, length: int):
        """Update queue length metrics"""
        try:
            self.manual_review_queue_length.labels(
                queue_type=queue_type
            ).set(length)
            
        except Exception as e:
            logger.error(f"Failed to update queue length metrics: {e}")
    
    def update_worker_count(self, worker_type: str, count: int):
        """Update active worker count"""
        try:
            self.active_workers.labels(
                worker_type=worker_type
            ).set(count)
            
        except Exception as e:
            logger.error(f"Failed to update worker count metrics: {e}")
    
    def update_validation_rate(self, rate: float):
        """Update validation rate (validations per second)"""
        try:
            self.validations_per_second.set(rate)
            
        except Exception as e:
            logger.error(f"Failed to update validation rate metrics: {e}")
    
    def update_high_confidence_percentage(self, percentage: float):
        """Update percentage of providers with high confidence"""
        try:
            self.high_confidence_percentage.set(percentage)
            
        except Exception as e:
            logger.error(f"Failed to update high confidence percentage metrics: {e}")
    
    def record_job_failure(self, job_type: str, error_type: str):
        """Record job failure"""
        try:
            self.failed_jobs_total.labels(
                job_type=job_type,
                error_type=error_type
            ).inc()
            
        except Exception as e:
            logger.error(f"Failed to record job failure metrics: {e}")
    
    def record_security_event(self, event_type: str, severity: str):
        """Record security event"""
        try:
            self.security_events_total.labels(
                event_type=event_type,
                severity=severity
            ).inc()
            
        except Exception as e:
            logger.error(f"Failed to record security event metrics: {e}")
    
    def record_pii_access(self, data_type: str, access_type: str):
        """Record PII access event"""
        try:
            self.pii_access_total.labels(
                data_type=data_type,
                access_type=access_type
            ).inc()
            
        except Exception as e:
            logger.error(f"Failed to record PII access metrics: {e}")
    
    def record_cache_event(self, cache_type: str, hit: bool):
        """Record cache hit/miss"""
        try:
            if hit:
                self.cache_hits_total.labels(cache_type=cache_type).inc()
            else:
                self.cache_misses_total.labels(cache_type=cache_type).inc()
                
        except Exception as e:
            logger.error(f"Failed to record cache event metrics: {e}")
    
    def record_database_query(self, query_type: str, duration: float):
        """Record database query metrics"""
        try:
            self.database_query_duration.labels(
                query_type=query_type
            ).observe(duration)
            
        except Exception as e:
            logger.error(f"Failed to record database query metrics: {e}")
    
    def _get_confidence_level(self, confidence: float) -> str:
        """Get confidence level bucket"""
        if confidence >= 0.9:
            return 'high'
        elif confidence >= 0.8:
            return 'good'
        elif confidence >= 0.6:
            return 'medium'
        elif confidence >= 0.4:
            return 'low'
        else:
            return 'very_low'
    
    def get_metrics(self) -> str:
        """Get Prometheus metrics in text format"""
        return generate_latest(self.registry).decode('utf-8')
    
    def get_metrics_json(self) -> Dict[str, Any]:
        """Get metrics in JSON format for custom endpoints"""
        metrics_data = {}
        
        try:
            # Get all metric families
            for metric_family in self.registry.collect():
                metric_name = metric_family.name
                metric_type = metric_family.type
                
                if metric_type == 'counter':
                    metrics_data[metric_name] = {
                        'type': 'counter',
                        'value': sum(sample.value for sample in metric_family.samples)
                    }
                elif metric_type == 'gauge':
                    metrics_data[metric_name] = {
                        'type': 'gauge',
                        'value': sum(sample.value for sample in metric_family.samples)
                    }
                elif metric_type == 'histogram':
                    metrics_data[metric_name] = {
                        'type': 'histogram',
                        'count': sum(sample.value for sample in metric_family.samples if sample.name.endswith('_count')),
                        'sum': sum(sample.value for sample in metric_family.samples if sample.name.endswith('_sum'))
                    }
                elif metric_type == 'summary':
                    metrics_data[metric_name] = {
                        'type': 'summary',
                        'count': sum(sample.value for sample in metric_family.samples if sample.name.endswith('_count')),
                        'sum': sum(sample.value for sample in metric_family.samples if sample.name.endswith('_sum'))
                    }
                    
        except Exception as e:
            logger.error(f"Failed to generate JSON metrics: {e}")
            
        return metrics_data

# Global metrics collector instance
metrics_collector: Optional[MetricsCollector] = None

def initialize_metrics() -> MetricsCollector:
    """Initialize global metrics collector"""
    global metrics_collector
    metrics_collector = MetricsCollector()
    return metrics_collector

def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector instance"""
    if metrics_collector is None:
        raise RuntimeError("Metrics collector not initialized. Call initialize_metrics() first.")
    return metrics_collector

# Decorator for automatic metrics collection
def track_validation_metrics(func):
    """Decorator to automatically track validation metrics"""
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = await func(*args, **kwargs)
            
            # Calculate metrics
            duration = time.time() - start_time
            
            if hasattr(result, 'provider_id'):
                metrics = ValidationMetrics(
                    provider_id=result.provider_id,
                    validation_duration=duration,
                    overall_confidence=result.overall_confidence,
                    validation_status=result.validation_status,
                    source_count=len(result.sources) if hasattr(result, 'sources') else 0,
                    error_count=len(result.flags) if hasattr(result, 'flags') else 0
                )
                
                get_metrics_collector().record_validation(metrics)
            
            return result
            
        except Exception as e:
            # Record failure
            get_metrics_collector().record_job_failure(
                job_type='validation',
                error_type=type(e).__name__
            )
            raise
    
    return wrapper

def track_api_metrics(func):
    """Decorator to automatically track API metrics"""
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            
            # Extract method and endpoint from request if available
            method = 'UNKNOWN'
            endpoint = 'UNKNOWN'
            status_code = 200
            
            if len(args) > 0 and hasattr(args[0], 'method'):
                method = args[0].method
            if len(args) > 0 and hasattr(args[0], 'url'):
                endpoint = str(args[0].url.path)
            
            get_metrics_collector().record_api_request(method, endpoint, status_code, duration)
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            get_metrics_collector().record_api_request('UNKNOWN', 'UNKNOWN', 500, duration)
            raise
    
    return wrapper
