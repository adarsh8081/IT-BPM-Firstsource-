"""
Comprehensive Audit Logging System

This module provides audit logging for all user actions, data changes, and system events
with support for compliance requirements (HIPAA, SOC 2).
"""

import json
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from dataclasses import dataclass, asdict
from sqlalchemy import create_engine, Column, String, DateTime, Text, Integer, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import redis
import logging

class AuditAction(Enum):
    """Audit action types"""
    # Authentication actions
    LOGIN = "auth.login"
    LOGOUT = "auth.logout"
    LOGIN_FAILED = "auth.login_failed"
    PASSWORD_CHANGE = "auth.password_change"
    TOKEN_REFRESH = "auth.token_refresh"
    TOKEN_REVOKE = "auth.token_revoke"
    
    # Provider actions
    PROVIDER_CREATE = "provider.create"
    PROVIDER_READ = "provider.read"
    PROVIDER_UPDATE = "provider.update"
    PROVIDER_DELETE = "provider.delete"
    PROVIDER_EXPORT = "provider.export"
    
    # Validation actions
    VALIDATION_RUN = "validation.run"
    VALIDATION_REVIEW = "validation.review"
    VALIDATION_APPROVE = "validation.approve"
    VALIDATION_REJECT = "validation.reject"
    VALIDATION_REVALIDATE = "validation.revalidate"
    
    # PII actions
    PII_REVEAL = "pii.reveal"
    PII_MASK = "pii.mask"
    PII_EXPORT = "pii.export"
    
    # Admin actions
    USER_CREATE = "admin.user_create"
    USER_UPDATE = "admin.user_update"
    USER_DELETE = "admin.user_delete"
    ROLE_CHANGE = "admin.role_change"
    PERMISSION_CHANGE = "admin.permission_change"
    CONFIG_CHANGE = "admin.config_change"
    
    # System actions
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_ERROR = "system.error"
    SYSTEM_WARNING = "system.warning"
    
    # Data actions
    DATA_EXPORT = "data.export"
    DATA_IMPORT = "data.import"
    DATA_BACKUP = "data.backup"
    DATA_RESTORE = "data.restore"
    DATA_DELETE = "data.delete"
    
    # External API actions
    API_CALL = "api.call"
    API_ERROR = "api.error"
    API_RATE_LIMIT = "api.rate_limit"

class RiskLevel(Enum):
    """Risk levels for audit events"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class AuditEvent:
    """Audit event data structure"""
    timestamp: datetime
    user_id: Optional[str]
    username: Optional[str]
    user_role: Optional[str]
    session_id: Optional[str]
    action: AuditAction
    resource_type: Optional[str]
    resource_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    request_id: Optional[str]
    changes: Optional[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]]
    risk_level: RiskLevel
    success: bool
    error_message: Optional[str]
    duration_ms: Optional[int]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['action'] = self.action.value
        data['risk_level'] = self.risk_level.value
        return data
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), default=str)

# SQLAlchemy model for audit logs
Base = declarative_base()

class AuditLog(Base):
    """Audit log database model"""
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    user_id = Column(String(255), nullable=True, index=True)
    username = Column(String(255), nullable=True, index=True)
    user_role = Column(String(50), nullable=True, index=True)
    session_id = Column(String(255), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(100), nullable=True, index=True)
    resource_id = Column(String(255), nullable=True, index=True)
    ip_address = Column(String(45), nullable=True, index=True)
    user_agent = Column(Text, nullable=True)
    request_id = Column(String(255), nullable=True, index=True)
    changes = Column(JSON, nullable=True)
    metadata = Column(JSON, nullable=True)
    risk_level = Column(String(20), nullable=False, index=True)
    success = Column(Boolean, nullable=False, default=True)
    error_message = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    
    # Computed fields for faster queries
    date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    hour = Column(Integer, nullable=False, index=True)     # 0-23
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, action={self.action}, user_id={self.user_id}, timestamp={self.timestamp})>"

class AuditLogger:
    """Comprehensive audit logging system"""
    
    def __init__(self, 
                 database_url: str,
                 redis_client: Optional[redis.Redis] = None,
                 log_level: str = "INFO",
                 enable_file_logging: bool = True,
                 log_file_path: str = "audit.log"):
        """
        Initialize audit logger
        
        Args:
            database_url: Database URL for audit log storage
            redis_client: Redis client for real-time alerts
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
            enable_file_logging: Enable file-based logging
            log_file_path: Path to audit log file
        """
        self.database_url = database_url
        self.redis_client = redis_client
        self.log_level = log_level
        self.enable_file_logging = enable_file_logging
        self.log_file_path = log_file_path
        
        # Initialize database
        self.engine = create_engine(database_url)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Initialize file logging
        if self.enable_file_logging:
            self._setup_file_logging()
        
        # Risk level mapping for actions
        self.action_risk_levels = {
            # Low risk actions
            AuditAction.PROVIDER_READ: RiskLevel.LOW,
            AuditAction.VALIDATION_REVIEW: RiskLevel.LOW,
            AuditAction.AUDIT_READ: RiskLevel.LOW,
            AuditAction.SYSTEM_STARTUP: RiskLevel.LOW,
            AuditAction.SYSTEM_SHUTDOWN: RiskLevel.LOW,
            
            # Medium risk actions
            AuditAction.LOGIN: RiskLevel.MEDIUM,
            AuditAction.LOGOUT: RiskLevel.MEDIUM,
            AuditAction.PROVIDER_CREATE: RiskLevel.MEDIUM,
            AuditAction.PROVIDER_UPDATE: RiskLevel.MEDIUM,
            AuditAction.VALIDATION_RUN: RiskLevel.MEDIUM,
            AuditAction.VALIDATION_APPROVE: RiskLevel.MEDIUM,
            AuditAction.VALIDATION_REJECT: RiskLevel.MEDIUM,
            AuditAction.DATA_EXPORT: RiskLevel.MEDIUM,
            AuditAction.API_CALL: RiskLevel.MEDIUM,
            
            # High risk actions
            AuditAction.LOGIN_FAILED: RiskLevel.HIGH,
            AuditAction.PASSWORD_CHANGE: RiskLevel.HIGH,
            AuditAction.PROVIDER_DELETE: RiskLevel.HIGH,
            AuditAction.PII_REVEAL: RiskLevel.HIGH,
            AuditAction.PII_EXPORT: RiskLevel.HIGH,
            AuditAction.USER_CREATE: RiskLevel.HIGH,
            AuditAction.USER_UPDATE: RiskLevel.HIGH,
            AuditAction.ROLE_CHANGE: RiskLevel.HIGH,
            AuditAction.PERMISSION_CHANGE: RiskLevel.HIGH,
            AuditAction.CONFIG_CHANGE: RiskLevel.HIGH,
            AuditAction.DATA_IMPORT: RiskLevel.HIGH,
            AuditAction.DATA_BACKUP: RiskLevel.HIGH,
            AuditAction.DATA_RESTORE: RiskLevel.HIGH,
            AuditAction.API_RATE_LIMIT: RiskLevel.HIGH,
            
            # Critical risk actions
            AuditAction.TOKEN_REVOKE: RiskLevel.CRITICAL,
            AuditAction.USER_DELETE: RiskLevel.CRITICAL,
            AuditAction.DATA_DELETE: RiskLevel.CRITICAL,
            AuditAction.SYSTEM_ERROR: RiskLevel.CRITICAL,
            AuditAction.API_ERROR: RiskLevel.CRITICAL,
        }
    
    def _setup_file_logging(self):
        """Setup file-based logging"""
        logging.basicConfig(
            level=getattr(logging, self.log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file_path),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('audit_logger')
    
    def log_event(self, 
                  action: AuditAction,
                  user_id: Optional[str] = None,
                  username: Optional[str] = None,
                  user_role: Optional[str] = None,
                  session_id: Optional[str] = None,
                  resource_type: Optional[str] = None,
                  resource_id: Optional[str] = None,
                  ip_address: Optional[str] = None,
                  user_agent: Optional[str] = None,
                  request_id: Optional[str] = None,
                  changes: Optional[Dict[str, Any]] = None,
                  metadata: Optional[Dict[str, Any]] = None,
                  success: bool = True,
                  error_message: Optional[str] = None,
                  duration_ms: Optional[int] = None,
                  custom_risk_level: Optional[RiskLevel] = None) -> str:
        """
        Log an audit event
        
        Args:
            action: Audit action type
            user_id: User ID (if applicable)
            username: Username (if applicable)
            user_role: User role (if applicable)
            session_id: Session ID (if applicable)
            resource_type: Type of resource being acted upon
            resource_id: ID of resource being acted upon
            ip_address: Client IP address
            user_agent: Client user agent
            request_id: Request ID for tracing
            changes: Before/after changes for data modifications
            metadata: Additional metadata
            success: Whether the action was successful
            error_message: Error message if action failed
            duration_ms: Duration of action in milliseconds
            custom_risk_level: Custom risk level override
            
        Returns:
            Audit log ID
        """
        timestamp = datetime.now(timezone.utc)
        risk_level = custom_risk_level or self.action_risk_levels.get(action, RiskLevel.MEDIUM)
        
        # Create audit event
        event = AuditEvent(
            timestamp=timestamp,
            user_id=user_id,
            username=username,
            user_role=user_role,
            session_id=session_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            changes=changes,
            metadata=metadata,
            risk_level=risk_level,
            success=success,
            error_message=error_message,
            duration_ms=duration_ms
        )
        
        # Store in database
        log_id = self._store_audit_log(event)
        
        # Log to file
        if self.enable_file_logging:
            self.logger.info(f"Audit Event: {event.to_json()}")
        
        # Send real-time alert for high-risk events
        if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            self._send_real_time_alert(event)
        
        return log_id
    
    def _store_audit_log(self, event: AuditEvent) -> str:
        """Store audit log in database"""
        try:
            session = self.SessionLocal()
            
            # Create audit log record
            audit_log = AuditLog(
                timestamp=event.timestamp,
                user_id=event.user_id,
                username=event.username,
                user_role=event.user_role,
                session_id=event.session_id,
                action=event.action.value,
                resource_type=event.resource_type,
                resource_id=event.resource_id,
                ip_address=event.ip_address,
                user_agent=event.user_agent,
                request_id=event.request_id,
                changes=event.changes,
                metadata=event.metadata,
                risk_level=event.risk_level.value,
                success=event.success,
                error_message=event.error_message,
                duration_ms=event.duration_ms,
                date=event.timestamp.strftime('%Y-%m-%d'),
                hour=event.timestamp.hour
            )
            
            session.add(audit_log)
            session.commit()
            
            log_id = str(audit_log.id)
            session.close()
            
            return log_id
            
        except Exception as e:
            if self.enable_file_logging:
                self.logger.error(f"Failed to store audit log: {str(e)}")
            raise
    
    def _send_real_time_alert(self, event: AuditEvent):
        """Send real-time alert for high-risk events"""
        if not self.redis_client:
            return
        
        try:
            alert_data = {
                'timestamp': event.timestamp.isoformat(),
                'user_id': event.user_id,
                'username': event.username,
                'action': event.action.value,
                'resource_type': event.resource_type,
                'resource_id': event.resource_id,
                'risk_level': event.risk_level.value,
                'ip_address': event.ip_address,
                'success': event.success,
                'error_message': event.error_message
            }
            
            # Publish to Redis channel for real-time monitoring
            self.redis_client.publish('audit_alerts', json.dumps(alert_data))
            
        except Exception as e:
            if self.enable_file_logging:
                self.logger.error(f"Failed to send real-time alert: {str(e)}")
    
    def get_audit_logs(self,
                      user_id: Optional[str] = None,
                      action: Optional[AuditAction] = None,
                      resource_type: Optional[str] = None,
                      resource_id: Optional[str] = None,
                      risk_level: Optional[RiskLevel] = None,
                      start_date: Optional[datetime] = None,
                      end_date: Optional[datetime] = None,
                      limit: int = 100,
                      offset: int = 0) -> List[Dict[str, Any]]:
        """
        Retrieve audit logs with filtering
        
        Args:
            user_id: Filter by user ID
            action: Filter by action type
            resource_type: Filter by resource type
            resource_id: Filter by resource ID
            risk_level: Filter by risk level
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of audit log records
        """
        try:
            session = self.SessionLocal()
            
            query = session.query(AuditLog)
            
            # Apply filters
            if user_id:
                query = query.filter(AuditLog.user_id == user_id)
            if action:
                query = query.filter(AuditLog.action == action.value)
            if resource_type:
                query = query.filter(AuditLog.resource_type == resource_type)
            if resource_id:
                query = query.filter(AuditLog.resource_id == resource_id)
            if risk_level:
                query = query.filter(AuditLog.risk_level == risk_level.value)
            if start_date:
                query = query.filter(AuditLog.timestamp >= start_date)
            if end_date:
                query = query.filter(AuditLog.timestamp <= end_date)
            
            # Apply pagination and ordering
            query = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit)
            
            logs = query.all()
            session.close()
            
            # Convert to dictionaries
            return [self._audit_log_to_dict(log) for log in logs]
            
        except Exception as e:
            if self.enable_file_logging:
                self.logger.error(f"Failed to retrieve audit logs: {str(e)}")
            raise
    
    def _audit_log_to_dict(self, log: AuditLog) -> Dict[str, Any]:
        """Convert audit log to dictionary"""
        return {
            'id': log.id,
            'timestamp': log.timestamp.isoformat(),
            'user_id': log.user_id,
            'username': log.username,
            'user_role': log.user_role,
            'session_id': log.session_id,
            'action': log.action,
            'resource_type': log.resource_type,
            'resource_id': log.resource_id,
            'ip_address': log.ip_address,
            'user_agent': log.user_agent,
            'request_id': log.request_id,
            'changes': log.changes,
            'metadata': log.metadata,
            'risk_level': log.risk_level,
            'success': log.success,
            'error_message': log.error_message,
            'duration_ms': log.duration_ms
        }
    
    def get_user_activity_summary(self, 
                                 user_id: str,
                                 days: int = 30) -> Dict[str, Any]:
        """
        Get user activity summary for compliance reporting
        
        Args:
            user_id: User ID
            days: Number of days to analyze
            
        Returns:
            User activity summary
        """
        try:
            session = self.SessionLocal()
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)
            
            # Get user logs
            logs = session.query(AuditLog).filter(
                AuditLog.user_id == user_id,
                AuditLog.timestamp >= start_date,
                AuditLog.timestamp <= end_date
            ).all()
            
            session.close()
            
            # Analyze activity
            total_actions = len(logs)
            successful_actions = sum(1 for log in logs if log.success)
            failed_actions = total_actions - successful_actions
            
            # Count actions by type
            action_counts = {}
            for log in logs:
                action_counts[log.action] = action_counts.get(log.action, 0) + 1
            
            # Count by risk level
            risk_counts = {}
            for log in logs:
                risk_counts[log.risk_level] = risk_counts.get(log.risk_level, 0) + 1
            
            # Get unique IP addresses
            unique_ips = set(log.ip_address for log in logs if log.ip_address)
            
            return {
                'user_id': user_id,
                'period_days': days,
                'total_actions': total_actions,
                'successful_actions': successful_actions,
                'failed_actions': failed_actions,
                'success_rate': successful_actions / total_actions if total_actions > 0 else 0,
                'action_counts': action_counts,
                'risk_counts': risk_counts,
                'unique_ip_addresses': list(unique_ips),
                'first_activity': min(log.timestamp for log in logs).isoformat() if logs else None,
                'last_activity': max(log.timestamp for log in logs).isoformat() if logs else None
            }
            
        except Exception as e:
            if self.enable_file_logging:
                self.logger.error(f"Failed to get user activity summary: {str(e)}")
            raise
    
    def cleanup_old_logs(self, retention_days: int = 2555) -> int:
        """
        Clean up old audit logs based on retention policy
        
        Args:
            retention_days: Number of days to retain logs (default: 7 years)
            
        Returns:
            Number of logs deleted
        """
        try:
            session = self.SessionLocal()
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
            
            # Delete old logs
            deleted_count = session.query(AuditLog).filter(
                AuditLog.timestamp < cutoff_date
            ).delete()
            
            session.commit()
            session.close()
            
            if self.enable_file_logging:
                self.logger.info(f"Cleaned up {deleted_count} old audit logs")
            
            return deleted_count
            
        except Exception as e:
            if self.enable_file_logging:
                self.logger.error(f"Failed to cleanup old logs: {str(e)}")
            raise

# Global audit logger instance
audit_logger: Optional[AuditLogger] = None

def initialize_audit_logger(database_url: str, 
                           redis_client: Optional[redis.Redis] = None,
                           log_level: str = "INFO") -> AuditLogger:
    """Initialize global audit logger"""
    global audit_logger
    audit_logger = AuditLogger(database_url, redis_client, log_level)
    return audit_logger

def get_audit_logger() -> AuditLogger:
    """Get global audit logger instance"""
    if audit_logger is None:
        raise RuntimeError("Audit logger not initialized. Call initialize_audit_logger() first.")
    return audit_logger
