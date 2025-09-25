"""
Metrics API Endpoints

This module provides REST API endpoints for accessing metrics data
in both Prometheus format and JSON format.
"""

from fastapi import APIRouter, Response, HTTPException, Depends
from fastapi.responses import PlainTextResponse, JSONResponse
from typing import Dict, Any, Optional
import logging
from datetime import datetime, timezone

from backend.monitoring.metrics import get_metrics_collector, MetricsCollector
from backend.monitoring.alerting import get_alert_manager, AlertManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/metrics", tags=["metrics"])

@router.get("/prometheus", response_class=PlainTextResponse)
async def get_prometheus_metrics():
    """
    Get metrics in Prometheus format
    
    Returns:
        Plain text response with Prometheus metrics
    """
    try:
        metrics_collector = get_metrics_collector()
        metrics_data = metrics_collector.get_metrics()
        
        return PlainTextResponse(
            content=metrics_data,
            media_type="text/plain; version=0.0.4; charset=utf-8"
        )
        
    except Exception as e:
        logger.error(f"Failed to get Prometheus metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics")

@router.get("/json")
async def get_json_metrics():
    """
    Get metrics in JSON format with additional metadata
    
    Returns:
        JSON response with metrics data and metadata
    """
    try:
        metrics_collector = get_metrics_collector()
        
        # Get basic metrics data
        metrics_data = metrics_collector.get_metrics_json()
        
        # Add metadata
        response_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": metrics_data,
            "metadata": {
                "format_version": "1.0",
                "collection_interval": "30s",
                "retention_period": "30d"
            }
        }
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        logger.error(f"Failed to get JSON metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics")

@router.get("/health")
async def get_health_metrics():
    """
    Get health check metrics
    
    Returns:
        JSON response with health status and key metrics
    """
    try:
        metrics_collector = get_metrics_collector()
        
        # Get key health metrics
        metrics_data = metrics_collector.get_metrics_json()
        
        # Calculate health score
        health_score = 1.0
        
        # Check validation success rate
        total_validations = metrics_data.get('provider_validations_total', {}).get('value', 0)
        if total_validations > 0:
            # This would need to be calculated from status-specific counters
            # For now, assume healthy if we have validations
            pass
        
        # Check queue health
        queue_length = metrics_data.get('manual_review_queue_length', {}).get('value', 0)
        if queue_length > 100:  # Threshold for queue length
            health_score -= 0.2
        
        # Check worker health
        active_workers = metrics_data.get('validation_workers_active', {}).get('value', 0)
        if active_workers == 0:
            health_score -= 0.5
        
        # Check error rate
        failed_jobs = metrics_data.get('failed_jobs_total', {}).get('value', 0)
        if failed_jobs > 10:  # Threshold for failed jobs
            health_score -= 0.3
        
        health_score = max(0.0, health_score)
        
        health_status = "healthy" if health_score > 0.7 else "degraded" if health_score > 0.4 else "unhealthy"
        
        response_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": health_status,
            "health_score": health_score,
            "key_metrics": {
                "total_validations": total_validations,
                "queue_length": queue_length,
                "active_workers": active_workers,
                "failed_jobs": failed_jobs,
                "validation_rate": metrics_data.get('provider_validations_per_second', {}).get('value', 0),
                "high_confidence_percentage": metrics_data.get('provider_high_confidence_percentage', {}).get('value', 0)
            },
            "alerts": {
                "active_count": 0,  # This would come from alert manager
                "critical_count": 0
            }
        }
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        logger.error(f"Failed to get health metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve health metrics")

@router.get("/dashboard")
async def get_dashboard_metrics():
    """
    Get metrics formatted for dashboard display
    
    Returns:
        JSON response with dashboard-formatted metrics
    """
    try:
        metrics_collector = get_metrics_collector()
        metrics_data = metrics_collector.get_metrics_json()
        
        # Format metrics for dashboard
        dashboard_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "kpis": {
                "validations_per_second": {
                    "value": metrics_data.get('provider_validations_per_second', {}).get('value', 0),
                    "unit": "validations/sec",
                    "trend": "stable"  # This would be calculated from historical data
                },
                "avg_validation_latency": {
                    "value": metrics_data.get('provider_validation_duration_seconds', {}).get('sum', 0) / 
                            max(metrics_data.get('provider_validation_duration_seconds', {}).get('count', 1), 1),
                    "unit": "seconds",
                    "trend": "stable"
                },
                "high_confidence_percentage": {
                    "value": metrics_data.get('provider_high_confidence_percentage', {}).get('value', 0),
                    "unit": "%",
                    "trend": "stable"
                },
                "manual_review_queue_length": {
                    "value": metrics_data.get('manual_review_queue_length', {}).get('value', 0),
                    "unit": "providers",
                    "trend": "stable"
                }
            },
            "system_health": {
                "active_workers": metrics_data.get('validation_workers_active', {}).get('value', 0),
                "failed_jobs": metrics_data.get('failed_jobs_total', {}).get('value', 0),
                "api_requests_total": metrics_data.get('api_requests_total', {}).get('value', 0),
                "external_api_errors": metrics_data.get('external_api_errors_total', {}).get('value', 0)
            },
            "data_quality": {
                "overall_score": metrics_data.get('data_quality_score', {}).get('value', 0),
                "compliance_violations": metrics_data.get('compliance_violations_total', {}).get('value', 0),
                "pii_access_events": metrics_data.get('pii_access_total', {}).get('value', 0)
            },
            "performance": {
                "cache_hit_rate": _calculate_cache_hit_rate(metrics_data),
                "database_query_avg_duration": _calculate_db_query_avg_duration(metrics_data),
                "external_api_avg_duration": _calculate_external_api_avg_duration(metrics_data)
            }
        }
        
        return JSONResponse(content=dashboard_data)
        
    except Exception as e:
        logger.error(f"Failed to get dashboard metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve dashboard metrics")

@router.get("/alerts")
async def get_active_alerts():
    """
    Get active alerts and their status
    
    Returns:
        JSON response with active alerts
    """
    try:
        alert_manager = get_alert_manager()
        alerts = await alert_manager.get_active_alerts()
        
        response_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "active_alerts": alerts,
            "summary": {
                "total": len(alerts),
                "critical": len([a for a in alerts if a.get('severity') == 'critical']),
                "warning": len([a for a in alerts if a.get('severity') == 'warning']),
                "info": len([a for a in alerts if a.get('severity') == 'info'])
            }
        }
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        logger.error(f"Failed to get active alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve alerts")

@router.post("/alerts/test")
async def test_alert_system():
    """
    Test the alert system by triggering a test alert
    
    Returns:
        JSON response confirming test alert was sent
    """
    try:
        alert_manager = get_alert_manager()
        
        # Send test alert
        await alert_manager.send_test_alert()
        
        return JSONResponse(content={
            "message": "Test alert sent successfully",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to send test alert: {e}")
        raise HTTPException(status_code=500, detail="Failed to send test alert")

def _calculate_cache_hit_rate(metrics_data: Dict[str, Any]) -> float:
    """Calculate cache hit rate"""
    hits = metrics_data.get('cache_hits_total', {}).get('value', 0)
    misses = metrics_data.get('cache_misses_total', {}).get('value', 0)
    total = hits + misses
    
    if total == 0:
        return 0.0
    
    return (hits / total) * 100

def _calculate_db_query_avg_duration(metrics_data: Dict[str, Any]) -> float:
    """Calculate average database query duration"""
    query_metrics = metrics_data.get('database_query_duration_seconds', {})
    count = query_metrics.get('count', 0)
    total = query_metrics.get('sum', 0)
    
    if count == 0:
        return 0.0
    
    return total / count

def _calculate_external_api_avg_duration(metrics_data: Dict[str, Any]) -> float:
    """Calculate average external API duration"""
    api_metrics = metrics_data.get('external_api_duration_seconds', {})
    count = api_metrics.get('count', 0)
    total = api_metrics.get('sum', 0)
    
    if count == 0:
        return 0.0
    
    return total / count
