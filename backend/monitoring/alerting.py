"""
Alerting System for Provider Validation Application

This module provides comprehensive alerting capabilities for monitoring
system health, performance issues, and business rule violations.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import httpx
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

class AlertChannel(Enum):
    """Alert notification channels"""
    SLACK = "slack"
    EMAIL = "email"
    WEBHOOK = "webhook"

@dataclass
class Alert:
    """Alert data structure"""
    id: str
    title: str
    message: str
    severity: AlertSeverity
    source: str
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary"""
        data = asdict(self)
        data['severity'] = self.severity.value
        data['timestamp'] = self.timestamp.isoformat()
        if self.resolved_at:
            data['resolved_at'] = self.resolved_at.isoformat()
        return data

@dataclass
class AlertRule:
    """Alert rule configuration"""
    name: str
    condition: Callable[[Dict[str, Any]], bool]
    severity: AlertSeverity
    channels: List[AlertChannel]
    cooldown_minutes: int = 15
    enabled: bool = True
    description: str = ""

class AlertManager:
    """Manages alerting system for the validation application"""
    
    def __init__(self):
        """Initialize alert manager"""
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.alert_rules: Dict[str, AlertRule] = {}
        self.last_alert_times: Dict[str, datetime] = {}
        
        # Configuration
        self.slack_webhook_url = os.getenv('SLACK_WEBHOOK_URL')
        self.smtp_server = os.getenv('SMTP_SERVER', 'localhost')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.alert_email_from = os.getenv('ALERT_EMAIL_FROM', 'alerts@provider-validation.com')
        self.alert_email_to = os.getenv('ALERT_EMAIL_TO', 'admin@provider-validation.com')
        
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """Setup default alert rules"""
        
        # High queue length alert
        self.add_rule(AlertRule(
            name="high_manual_review_queue",
            condition=lambda metrics: metrics.get('manual_review_queue_length', 0) > 50,
            severity=AlertSeverity.WARNING,
            channels=[AlertChannel.SLACK, AlertChannel.EMAIL],
            cooldown_minutes=30,
            description="Manual review queue length exceeds 50 providers"
        ))
        
        # Critical queue length alert
        self.add_rule(AlertRule(
            name="critical_manual_review_queue",
            condition=lambda metrics: metrics.get('manual_review_queue_length', 0) > 100,
            severity=AlertSeverity.CRITICAL,
            channels=[AlertChannel.SLACK, AlertChannel.EMAIL],
            cooldown_minutes=15,
            description="Manual review queue length exceeds 100 providers"
        ))
        
        # Low validation rate alert
        self.add_rule(AlertRule(
            name="low_validation_rate",
            condition=lambda metrics: metrics.get('provider_validations_per_second', 0) < 0.1,
            severity=AlertSeverity.WARNING,
            channels=[AlertChannel.SLACK],
            cooldown_minutes=60,
            description="Validation rate below 0.1 validations per second"
        ))
        
        # High failure rate alert
        self.add_rule(AlertRule(
            name="high_failure_rate",
            condition=lambda metrics: self._calculate_failure_rate(metrics) > 0.1,
            severity=AlertSeverity.CRITICAL,
            channels=[AlertChannel.SLACK, AlertChannel.EMAIL],
            cooldown_minutes=15,
            description="Job failure rate exceeds 10%"
        ))
        
        # No active workers alert
        self.add_rule(AlertRule(
            name="no_active_workers",
            condition=lambda metrics: metrics.get('validation_workers_active', 0) == 0,
            severity=AlertSeverity.CRITICAL,
            channels=[AlertChannel.SLACK, AlertChannel.EMAIL],
            cooldown_minutes=5,
            description="No active validation workers"
        ))
        
        # Low confidence rate alert
        self.add_rule(AlertRule(
            name="low_confidence_rate",
            condition=lambda metrics: metrics.get('provider_high_confidence_percentage', 0) < 70,
            severity=AlertSeverity.WARNING,
            channels=[AlertChannel.SLACK],
            cooldown_minutes=120,
            description="High confidence rate below 70%"
        ))
        
        # External API error rate alert
        self.add_rule(AlertRule(
            name="high_external_api_errors",
            condition=lambda metrics: self._calculate_external_api_error_rate(metrics) > 0.05,
            severity=AlertSeverity.WARNING,
            channels=[AlertChannel.SLACK],
            cooldown_minutes=30,
            description="External API error rate exceeds 5%"
        ))
        
        # Security events alert
        self.add_rule(AlertRule(
            name="security_events",
            condition=lambda metrics: metrics.get('security_events_total', 0) > 0,
            severity=AlertSeverity.CRITICAL,
            channels=[AlertChannel.SLACK, AlertChannel.EMAIL],
            cooldown_minutes=5,
            description="Security events detected"
        ))
        
        # Database connection issues alert
        self.add_rule(AlertRule(
            name="database_connection_issues",
            condition=lambda metrics: metrics.get('database_connections_active', 0) == 0,
            severity=AlertSeverity.CRITICAL,
            channels=[AlertChannel.SLACK, AlertChannel.EMAIL],
            cooldown_minutes=5,
            description="No active database connections"
        ))
    
    def add_rule(self, rule: AlertRule):
        """Add alert rule"""
        self.alert_rules[rule.name] = rule
        logger.info(f"Added alert rule: {rule.name}")
    
    def remove_rule(self, rule_name: str):
        """Remove alert rule"""
        if rule_name in self.alert_rules:
            del self.alert_rules[rule_name]
            logger.info(f"Removed alert rule: {rule_name}")
    
    async def check_alerts(self, metrics: Dict[str, Any]):
        """Check all alert rules against current metrics"""
        try:
            for rule_name, rule in self.alert_rules.items():
                if not rule.enabled:
                    continue
                
                # Check cooldown
                if self._is_in_cooldown(rule_name):
                    continue
                
                # Check condition
                try:
                    if rule.condition(metrics):
                        await self._trigger_alert(rule, metrics)
                except Exception as e:
                    logger.error(f"Error checking alert rule {rule_name}: {e}")
                    
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
    
    async def _trigger_alert(self, rule: AlertRule, metrics: Dict[str, Any]):
        """Trigger an alert"""
        try:
            alert_id = f"{rule.name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
            
            alert = Alert(
                id=alert_id,
                title=f"Provider Validation Alert: {rule.name.replace('_', ' ').title()}",
                message=rule.description,
                severity=rule.severity,
                source=rule.name,
                timestamp=datetime.now(timezone.utc),
                metadata={
                    "rule_name": rule.name,
                    "metrics_snapshot": metrics,
                    "threshold_breached": True
                }
            )
            
            # Store alert
            self.active_alerts[alert_id] = alert
            self.alert_history.append(alert)
            self.last_alert_times[rule.name] = datetime.now(timezone.utc)
            
            # Send notifications
            await self._send_notifications(alert, rule.channels)
            
            logger.warning(f"Alert triggered: {rule.name} - {alert.message}")
            
        except Exception as e:
            logger.error(f"Failed to trigger alert {rule.name}: {e}")
    
    async def _send_notifications(self, alert: Alert, channels: List[AlertChannel]):
        """Send notifications through configured channels"""
        for channel in channels:
            try:
                if channel == AlertChannel.SLACK:
                    await self._send_slack_alert(alert)
                elif channel == AlertChannel.EMAIL:
                    await self._send_email_alert(alert)
                elif channel == AlertChannel.WEBHOOK:
                    await self._send_webhook_alert(alert)
            except Exception as e:
                logger.error(f"Failed to send {channel.value} notification: {e}")
    
    async def _send_slack_alert(self, alert: Alert):
        """Send Slack alert"""
        if not self.slack_webhook_url:
            logger.warning("Slack webhook URL not configured")
            return
        
        # Determine color based on severity
        color_map = {
            AlertSeverity.INFO: "#36a64f",
            AlertSeverity.WARNING: "#ff9500",
            AlertSeverity.CRITICAL: "#ff0000"
        }
        
        payload = {
            "attachments": [
                {
                    "color": color_map[alert.severity],
                    "title": alert.title,
                    "text": alert.message,
                    "fields": [
                        {
                            "title": "Severity",
                            "value": alert.severity.value.upper(),
                            "short": True
                        },
                        {
                            "title": "Source",
                            "value": alert.source,
                            "short": True
                        },
                        {
                            "title": "Timestamp",
                            "value": alert.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
                            "short": True
                        }
                    ],
                    "footer": "Provider Validation System",
                    "ts": int(alert.timestamp.timestamp())
                }
            ]
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.slack_webhook_url,
                json=payload,
                timeout=10.0
            )
            response.raise_for_status()
    
    async def _send_email_alert(self, alert: Alert):
        """Send email alert"""
        if not self.smtp_username or not self.smtp_password:
            logger.warning("SMTP credentials not configured")
            return
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.alert_email_from
            msg['To'] = self.alert_email_to
            msg['Subject'] = f"[{alert.severity.value.upper()}] {alert.title}"
            
            body = f"""
            Alert Details:
            =============
            
            Title: {alert.title}
            Message: {alert.message}
            Severity: {alert.severity.value.upper()}
            Source: {alert.source}
            Timestamp: {alert.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")}
            
            Please investigate this issue promptly.
            
            Provider Validation System
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            text = msg.as_string()
            server.sendmail(self.alert_email_from, self.alert_email_to, text)
            server.quit()
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
    
    async def _send_webhook_alert(self, alert: Alert):
        """Send webhook alert"""
        webhook_url = os.getenv('WEBHOOK_URL')
        if not webhook_url:
            logger.warning("Webhook URL not configured")
            return
        
        payload = alert.to_dict()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook_url,
                json=payload,
                timeout=10.0
            )
            response.raise_for_status()
    
    async def resolve_alert(self, alert_id: str, resolution_message: str = ""):
        """Resolve an alert"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            alert.resolved_at = datetime.now(timezone.utc)
            
            if resolution_message:
                alert.message += f"\n\nResolution: {resolution_message}"
            
            # Remove from active alerts
            del self.active_alerts[alert_id]
            
            logger.info(f"Alert resolved: {alert_id}")
    
    async def send_test_alert(self):
        """Send a test alert to verify alerting system"""
        test_alert = Alert(
            id="test_alert",
            title="Test Alert",
            message="This is a test alert to verify the alerting system is working correctly.",
            severity=AlertSeverity.INFO,
            source="test",
            timestamp=datetime.now(timezone.utc)
        )
        
        await self._send_notifications(test_alert, [AlertChannel.SLACK, AlertChannel.EMAIL])
        logger.info("Test alert sent")
    
    def _is_in_cooldown(self, rule_name: str) -> bool:
        """Check if rule is in cooldown period"""
        if rule_name not in self.last_alert_times:
            return False
        
        rule = self.alert_rules.get(rule_name)
        if not rule:
            return False
        
        last_alert_time = self.last_alert_times[rule_name]
        cooldown_duration = timedelta(minutes=rule.cooldown_minutes)
        
        return datetime.now(timezone.utc) - last_alert_time < cooldown_duration
    
    def _calculate_failure_rate(self, metrics: Dict[str, Any]) -> float:
        """Calculate job failure rate"""
        total_jobs = metrics.get('providers_processed_total', 0)
        failed_jobs = metrics.get('failed_jobs_total', 0)
        
        if total_jobs == 0:
            return 0.0
        
        return failed_jobs / total_jobs
    
    def _calculate_external_api_error_rate(self, metrics: Dict[str, Any]) -> float:
        """Calculate external API error rate"""
        total_calls = metrics.get('external_api_calls_total', 0)
        error_calls = metrics.get('external_api_errors_total', 0)
        
        if total_calls == 0:
            return 0.0
        
        return error_calls / total_calls
    
    async def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active alerts"""
        return [alert.to_dict() for alert in self.active_alerts.values()]
    
    async def get_alert_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get alert history for specified hours"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        history = [
            alert.to_dict() for alert in self.alert_history
            if alert.timestamp >= cutoff_time
        ]
        
        return sorted(history, key=lambda x: x['timestamp'], reverse=True)

# Global alert manager instance
alert_manager: Optional[AlertManager] = None

def initialize_alert_manager() -> AlertManager:
    """Initialize global alert manager"""
    global alert_manager
    alert_manager = AlertManager()
    return alert_manager

def get_alert_manager() -> AlertManager:
    """Get global alert manager instance"""
    if alert_manager is None:
        raise RuntimeError("Alert manager not initialized. Call initialize_alert_manager() first.")
    return alert_manager
