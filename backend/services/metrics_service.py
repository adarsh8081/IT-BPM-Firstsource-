"""
Metrics Collection Service

This service periodically collects and updates metrics from various
system components and triggers alerts when thresholds are breached.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import json

from backend.monitoring.metrics import get_metrics_collector, MetricsCollector
from backend.monitoring.alerting import get_alert_manager, AlertManager
from backend.models.provider import Provider
from backend.models.validation import ValidationJob, ValidationResult
from backend.services.validator import ValidationOrchestrator
from backend.workers.queue_manager import QueueManager
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

logger = logging.getLogger(__name__)

class MetricsCollectionService:
    """Service for collecting and updating system metrics"""
    
    def __init__(self, db_session: Session, orchestrator: ValidationOrchestrator, queue_manager: QueueManager):
        """Initialize metrics collection service"""
        self.db_session = db_session
        self.orchestrator = orchestrator
        self.queue_manager = queue_manager
        self.metrics_collector = get_metrics_collector()
        self.alert_manager = get_alert_manager()
        
        # Collection intervals (in seconds)
        self.metrics_collection_interval = 30
        self.alert_check_interval = 60
        
        # Running state
        self.is_running = False
        self.collection_task: Optional[asyncio.Task] = None
        self.alert_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start metrics collection service"""
        if self.is_running:
            logger.warning("Metrics collection service is already running")
            return
        
        self.is_running = True
        
        # Start metrics collection task
        self.collection_task = asyncio.create_task(self._metrics_collection_loop())
        
        # Start alert checking task
        self.alert_task = asyncio.create_task(self._alert_checking_loop())
        
        logger.info("Metrics collection service started")
    
    async def stop(self):
        """Stop metrics collection service"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Cancel tasks
        if self.collection_task:
            self.collection_task.cancel()
        if self.alert_task:
            self.alert_task.cancel()
        
        # Wait for tasks to complete
        if self.collection_task:
            try:
                await self.collection_task
            except asyncio.CancelledError:
                pass
        
        if self.alert_task:
            try:
                await self.alert_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Metrics collection service stopped")
    
    async def _metrics_collection_loop(self):
        """Main metrics collection loop"""
        while self.is_running:
            try:
                await self._collect_all_metrics()
                await asyncio.sleep(self.metrics_collection_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {e}")
                await asyncio.sleep(self.metrics_collection_interval)
    
    async def _alert_checking_loop(self):
        """Main alert checking loop"""
        while self.is_running:
            try:
                await self._check_all_alerts()
                await asyncio.sleep(self.alert_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in alert checking loop: {e}")
                await asyncio.sleep(self.alert_check_interval)
    
    async def _collect_all_metrics(self):
        """Collect all system metrics"""
        try:
            # Collect validation metrics
            await self._collect_validation_metrics()
            
            # Collect queue metrics
            await self._collect_queue_metrics()
            
            # Collect worker metrics
            await self._collect_worker_metrics()
            
            # Collect performance metrics
            await self._collect_performance_metrics()
            
            # Collect data quality metrics
            await self._collect_data_quality_metrics()
            
            # Collect system health metrics
            await self._collect_system_health_metrics()
            
            logger.debug("Metrics collection completed")
            
        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")
    
    async def _collect_validation_metrics(self):
        """Collect validation-related metrics"""
        try:
            # Get validation statistics from database
            now = datetime.now(timezone.utc)
            one_hour_ago = now - timedelta(hours=1)
            one_day_ago = now - timedelta(days=1)
            
            # Total validations
            total_validations = self.db_session.query(func.count(ValidationResult.id)).scalar() or 0
            
            # Validations in last hour
            recent_validations = self.db_session.query(func.count(ValidationResult.id)).filter(
                ValidationResult.created_at >= one_hour_ago
            ).scalar() or 0
            
            # Calculate validation rate (validations per second)
            validation_rate = recent_validations / 3600.0 if recent_validations > 0 else 0.0
            self.metrics_collector.update_validation_rate(validation_rate)
            
            # High confidence percentage
            high_confidence_count = self.db_session.query(func.count(ValidationResult.id)).filter(
                ValidationResult.overall_confidence >= 0.8
            ).scalar() or 0
            
            high_confidence_percentage = (high_confidence_count / total_validations * 100) if total_validations > 0 else 0
            self.metrics_collector.update_high_confidence_percentage(high_confidence_percentage)
            
            # Validation status distribution
            status_counts = self.db_session.query(
                ValidationResult.validation_status,
                func.count(ValidationResult.id)
            ).group_by(ValidationResult.validation_status).all()
            
            for status, count in status_counts:
                confidence_level = self.metrics_collector._get_confidence_level(0.8)  # Default to good
                self.metrics_collector.validations_total.labels(
                    status=status,
                    confidence_level=confidence_level
                )._value._value = count
            
        except Exception as e:
            logger.error(f"Failed to collect validation metrics: {e}")
    
    async def _collect_queue_metrics(self):
        """Collect queue-related metrics"""
        try:
            # Get manual review queue length
            manual_review_count = self.db_session.query(func.count(ValidationResult.id)).filter(
                and_(
                    ValidationResult.validation_status == "warning",
                    ValidationResult.created_at >= datetime.now(timezone.utc) - timedelta(days=7)
                )
            ).scalar() or 0
            
            self.metrics_collector.update_queue_length("manual_review", manual_review_count)
            
            # Get job queue size from queue manager
            if hasattr(self.queue_manager, 'get_queue_size'):
                job_queue_size = await self.queue_manager.get_queue_size()
                self.metrics_collector.job_queue_size.labels(queue_name="validation").set(job_queue_size)
            
        except Exception as e:
            logger.error(f"Failed to collect queue metrics: {e}")
    
    async def _collect_worker_metrics(self):
        """Collect worker-related metrics"""
        try:
            # Get active worker count from queue manager
            if hasattr(self.queue_manager, 'get_worker_count'):
                worker_count = await self.queue_manager.get_worker_count()
                self.metrics_collector.update_worker_count("validation", worker_count)
            
            # Get failed job count
            failed_jobs = self.db_session.query(func.count(ValidationJob.id)).filter(
                ValidationJob.status == "failed"
            ).scalar() or 0
            
            self.metrics_collector.failed_jobs_total.labels(
                job_type="validation",
                error_type="unknown"
            )._value._value = failed_jobs
            
        except Exception as e:
            logger.error(f"Failed to collect worker metrics: {e}")
    
    async def _collect_performance_metrics(self):
        """Collect performance-related metrics"""
        try:
            # Calculate average validation duration
            avg_duration_result = self.db_session.query(
                func.avg(ValidationResult.created_at - ValidationResult.created_at)
            ).scalar()
            
            if avg_duration_result:
                avg_duration = avg_duration_result.total_seconds()
                self.metrics_collector.validation_duration.labels(
                    provider_type="standard",
                    validation_type="full"
                )._sum._value = avg_duration
            
            # Cache hit rate (if cache is available)
            # This would need to be implemented based on your caching solution
            
        except Exception as e:
            logger.error(f"Failed to collect performance metrics: {e}")
    
    async def _collect_data_quality_metrics(self):
        """Collect data quality metrics"""
        try:
            # Calculate overall data quality score
            # This is a simplified calculation - you might want to make it more sophisticated
            
            total_providers = self.db_session.query(func.count(Provider.id)).scalar() or 0
            
            if total_providers > 0:
                # Calculate quality score based on validation results
                high_quality_count = self.db_session.query(func.count(ValidationResult.id)).filter(
                    ValidationResult.overall_confidence >= 0.8
                ).scalar() or 0
                
                quality_score = high_quality_count / total_providers
                self.metrics_collector.data_quality_score.set(quality_score)
            
            # Compliance violations (simplified)
            compliance_violations = self.db_session.query(func.count(ValidationResult.id)).filter(
                ValidationResult.flags.contains('COMPLIANCE_VIOLATION')
            ).scalar() or 0
            
            self.metrics_collector.compliance_violations.labels(
                violation_type="general",
                severity="medium"
            )._value._value = compliance_violations
            
        except Exception as e:
            logger.error(f"Failed to collect data quality metrics: {e}")
    
    async def _collect_system_health_metrics(self):
        """Collect system health metrics"""
        try:
            # Database connections (simplified)
            # In a real implementation, you'd get this from your database connection pool
            self.metrics_collector.database_connections.set(1)  # Assuming at least one connection
            
            # Security events (simplified)
            # This would come from your security monitoring system
            security_events = 0  # Placeholder
            
            if security_events > 0:
                self.metrics_collector.security_events_total.labels(
                    event_type="general",
                    severity="medium"
                )._value._value = security_events
            
        except Exception as e:
            logger.error(f"Failed to collect system health metrics: {e}")
    
    async def _check_all_alerts(self):
        """Check all alert conditions"""
        try:
            # Get current metrics data
            metrics_data = self.metrics_collector.get_metrics_json()
            
            # Check alerts
            await self.alert_manager.check_alerts(metrics_data)
            
            logger.debug("Alert checking completed")
            
        except Exception as e:
            logger.error(f"Failed to check alerts: {e}")
    
    async def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of current metrics"""
        try:
            metrics_data = self.metrics_collector.get_metrics_json()
            
            summary = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "key_metrics": {
                    "validations_per_second": metrics_data.get('provider_validations_per_second', {}).get('value', 0),
                    "avg_validation_latency": self._calculate_avg_latency(metrics_data),
                    "high_confidence_percentage": metrics_data.get('provider_high_confidence_percentage', {}).get('value', 0),
                    "manual_review_queue_length": metrics_data.get('manual_review_queue_length', {}).get('value', 0),
                    "active_workers": metrics_data.get('validation_workers_active', {}).get('value', 0),
                    "failed_jobs": metrics_data.get('failed_jobs_total', {}).get('value', 0)
                },
                "system_health": {
                    "database_connections": metrics_data.get('database_connections_active', {}).get('value', 0),
                    "security_events": metrics_data.get('security_events_total', {}).get('value', 0),
                    "external_api_errors": metrics_data.get('external_api_errors_total', {}).get('value', 0)
                },
                "data_quality": {
                    "overall_score": metrics_data.get('data_quality_score', {}).get('value', 0),
                    "compliance_violations": metrics_data.get('compliance_violations_total', {}).get('value', 0)
                }
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get metrics summary: {e}")
            return {}
    
    def _calculate_avg_latency(self, metrics_data: Dict[str, Any]) -> float:
        """Calculate average validation latency"""
        validation_metrics = metrics_data.get('provider_validation_duration_seconds', {})
        count = validation_metrics.get('count', 0)
        total = validation_metrics.get('sum', 0)
        
        if count == 0:
            return 0.0
        
        return total / count
