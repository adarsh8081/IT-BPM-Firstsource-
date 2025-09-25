"""
Data Retention Manager

This module implements comprehensive data retention policies with automated cleanup,
compliance reporting, and audit logging for all data deletion activities.
"""

import os
import shutil
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import logging
import json
import hashlib

class RetentionPolicyType(Enum):
    """Retention policy types"""
    PROVIDER_DATA = "provider_data"
    AUDIT_LOGS = "audit_logs"
    VALIDATION_RESULTS = "validation_results"
    TEMP_FILES = "temp_files"
    RAW_SCANS = "raw_scans"
    BACKUP_FILES = "backup_files"
    CACHE_DATA = "cache_data"
    SESSION_DATA = "session_data"
    LOG_FILES = "log_files"

class RetentionAction(Enum):
    """Retention actions"""
    DELETE = "delete"
    ARCHIVE = "archive"
    ANONYMIZE = "anonymize"
    COMPRESS = "compress"
    MOVE_TO_COLD_STORAGE = "move_to_cold_storage"

@dataclass
class RetentionPolicy:
    """Data retention policy configuration"""
    policy_type: RetentionPolicyType
    retention_days: int
    action: RetentionAction
    description: str
    compliance_requirement: Optional[str] = None
    auto_cleanup_enabled: bool = True
    cleanup_schedule: Optional[str] = None  # Cron expression
    archive_location: Optional[str] = None
    anonymization_rules: Optional[Dict[str, str]] = None
    notification_enabled: bool = True
    dry_run: bool = False

@dataclass
class RetentionEvent:
    """Retention event for audit logging"""
    timestamp: datetime
    policy_type: RetentionPolicyType
    action: RetentionAction
    affected_records: int
    affected_size_bytes: int
    success: bool
    error_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class RetentionManager:
    """Comprehensive data retention management system"""
    
    def __init__(self, 
                 database_url: str,
                 audit_callback: Optional[Callable[[RetentionEvent], None]] = None,
                 notification_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None):
        """
        Initialize retention manager
        
        Args:
            database_url: Database connection URL
            audit_callback: Callback for audit logging
            notification_callback: Callback for notifications
        """
        self.database_url = database_url
        self.audit_callback = audit_callback
        self.notification_callback = notification_callback
        self.logger = logging.getLogger(__name__)
        
        # Initialize database connection
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Default retention policies
        self.policies = self._initialize_default_policies()
        
        # File system paths
        self.temp_storage_path = os.getenv('LOCAL_STORAGE_PATH', '/tmp/provider-validation')
        self.archive_storage_path = os.getenv('ARCHIVE_STORAGE_PATH', '/var/archive/provider-validation')
        
        # Ensure storage directories exist
        os.makedirs(self.temp_storage_path, exist_ok=True)
        os.makedirs(self.archive_storage_path, exist_ok=True)
    
    def _initialize_default_policies(self) -> Dict[RetentionPolicyType, RetentionPolicy]:
        """Initialize default retention policies"""
        return {
            RetentionPolicyType.PROVIDER_DATA: RetentionPolicy(
                policy_type=RetentionPolicyType.PROVIDER_DATA,
                retention_days=2555,  # 7 years (HIPAA requirement)
                action=RetentionAction.ARCHIVE,
                description="Provider data retention for HIPAA compliance",
                compliance_requirement="HIPAA",
                cleanup_schedule="0 2 * * 0",  # Weekly on Sunday at 2 AM
                archive_location=self.archive_storage_path
            ),
            RetentionPolicyType.AUDIT_LOGS: RetentionPolicy(
                policy_type=RetentionPolicyType.AUDIT_LOGS,
                retention_days=3650,  # 10 years (SOC 2 requirement)
                action=RetentionAction.ARCHIVE,
                description="Audit logs retention for SOC 2 compliance",
                compliance_requirement="SOC 2",
                cleanup_schedule="0 3 * * 0",  # Weekly on Sunday at 3 AM
                archive_location=self.archive_storage_path
            ),
            RetentionPolicyType.VALIDATION_RESULTS: RetentionPolicy(
                policy_type=RetentionPolicyType.VALIDATION_RESULTS,
                retention_days=1825,  # 5 years
                action=RetentionAction.ARCHIVE,
                description="Validation results retention",
                cleanup_schedule="0 4 * * 0",  # Weekly on Sunday at 4 AM
                archive_location=self.archive_storage_path
            ),
            RetentionPolicyType.TEMP_FILES: RetentionPolicy(
                policy_type=RetentionPolicyType.TEMP_FILES,
                retention_days=30,
                action=RetentionAction.DELETE,
                description="Temporary files cleanup",
                cleanup_schedule="0 1 * * *",  # Daily at 1 AM
                auto_cleanup_enabled=True
            ),
            RetentionPolicyType.RAW_SCANS: RetentionPolicy(
                policy_type=RetentionPolicyType.RAW_SCANS,
                retention_days=90,  # Maximum 90 days for raw scans
                action=RetentionAction.DELETE,
                description="Raw scan files cleanup (maximum 90 days)",
                compliance_requirement="Data minimization principle",
                cleanup_schedule="0 5 * * *",  # Daily at 5 AM
                auto_cleanup_enabled=True,
                notification_enabled=True
            ),
            RetentionPolicyType.BACKUP_FILES: RetentionPolicy(
                policy_type=RetentionPolicyType.BACKUP_FILES,
                retention_days=30,
                action=RetentionAction.DELETE,
                description="Backup files cleanup",
                cleanup_schedule="0 6 * * 0",  # Weekly on Sunday at 6 AM
                auto_cleanup_enabled=True
            ),
            RetentionPolicyType.CACHE_DATA: RetentionPolicy(
                policy_type=RetentionPolicyType.CACHE_DATA,
                retention_days=7,
                action=RetentionAction.DELETE,
                description="Cache data cleanup",
                cleanup_schedule="0 */6 * * *",  # Every 6 hours
                auto_cleanup_enabled=True
            ),
            RetentionPolicyType.SESSION_DATA: RetentionPolicy(
                policy_type=RetentionPolicyType.SESSION_DATA,
                retention_days=1,
                action=RetentionAction.DELETE,
                description="Session data cleanup",
                cleanup_schedule="0 */2 * * *",  # Every 2 hours
                auto_cleanup_enabled=True
            ),
            RetentionPolicyType.LOG_FILES: RetentionPolicy(
                policy_type=RetentionPolicyType.LOG_FILES,
                retention_days=90,
                action=RetentionAction.COMPRESS,
                description="Log files compression and cleanup",
                cleanup_schedule="0 7 * * 0",  # Weekly on Sunday at 7 AM
                auto_cleanup_enabled=True
            )
        }
    
    def execute_retention_policy(self, 
                                policy_type: RetentionPolicyType, 
                                dry_run: bool = False) -> RetentionEvent:
        """
        Execute retention policy for specific data type
        
        Args:
            policy_type: Type of data to process
            dry_run: If True, only simulate the action
            
        Returns:
            Retention event with results
        """
        policy = self.policies.get(policy_type)
        if not policy:
            raise ValueError(f"No retention policy found for {policy_type}")
        
        # Override dry_run if specified
        if dry_run:
            policy.dry_run = True
        
        try:
            self.logger.info(f"Executing retention policy for {policy_type.value}")
            
            # Execute based on policy type
            if policy_type == RetentionPolicyType.PROVIDER_DATA:
                result = self._cleanup_provider_data(policy)
            elif policy_type == RetentionPolicyType.AUDIT_LOGS:
                result = self._cleanup_audit_logs(policy)
            elif policy_type == RetentionPolicyType.VALIDATION_RESULTS:
                result = self._cleanup_validation_results(policy)
            elif policy_type == RetentionPolicyType.TEMP_FILES:
                result = self._cleanup_temp_files(policy)
            elif policy_type == RetentionPolicyType.RAW_SCANS:
                result = self._cleanup_raw_scans(policy)
            elif policy_type == RetentionPolicyType.BACKUP_FILES:
                result = self._cleanup_backup_files(policy)
            elif policy_type == RetentionPolicyType.CACHE_DATA:
                result = self._cleanup_cache_data(policy)
            elif policy_type == RetentionPolicyType.SESSION_DATA:
                result = self._cleanup_session_data(policy)
            elif policy_type == RetentionPolicyType.LOG_FILES:
                result = self._cleanup_log_files(policy)
            else:
                raise ValueError(f"Unsupported retention policy type: {policy_type}")
            
            # Create retention event
            event = RetentionEvent(
                timestamp=datetime.now(timezone.utc),
                policy_type=policy_type,
                action=policy.action,
                affected_records=result['affected_records'],
                affected_size_bytes=result['affected_size_bytes'],
                success=result['success'],
                error_message=result.get('error_message'),
                details=result.get('details', {})
            )
            
            # Log audit event
            if self.audit_callback:
                self.audit_callback(event)
            
            # Send notification if enabled
            if policy.notification_enabled and self.notification_callback:
                self._send_retention_notification(event)
            
            return event
            
        except Exception as e:
            self.logger.error(f"Failed to execute retention policy for {policy_type}: {e}")
            
            # Create failure event
            event = RetentionEvent(
                timestamp=datetime.now(timezone.utc),
                policy_type=policy_type,
                action=policy.action,
                affected_records=0,
                affected_size_bytes=0,
                success=False,
                error_message=str(e)
            )
            
            if self.audit_callback:
                self.audit_callback(event)
            
            raise
    
    def _cleanup_provider_data(self, policy: RetentionPolicy) -> Dict[str, Any]:
        """Cleanup provider data based on retention policy"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=policy.retention_days)
        
        session = self.SessionLocal()
        try:
            if policy.dry_run:
                # Count records that would be affected
                count_query = text("""
                    SELECT COUNT(*) as count, 
                           COALESCE(SUM(pg_column_size(providers.*)), 0) as size_bytes
                    FROM providers 
                    WHERE created_at < :cutoff_date
                """)
                result = session.execute(count_query, {'cutoff_date': cutoff_date}).fetchone()
                
                return {
                    'affected_records': result.count,
                    'affected_size_bytes': result.size_bytes,
                    'success': True,
                    'details': {'dry_run': True, 'cutoff_date': cutoff_date.isoformat()}
                }
            
            # Get records to be archived
            select_query = text("""
                SELECT provider_id, created_at, 
                       pg_column_size(providers.*) as size_bytes
                FROM providers 
                WHERE created_at < :cutoff_date
                ORDER BY created_at
            """)
            records = session.execute(select_query, {'cutoff_date': cutoff_date}).fetchall()
            
            total_records = len(records)
            total_size = sum(record.size_bytes for record in records)
            
            if total_records > 0:
                if policy.action == RetentionAction.ARCHIVE:
                    # Archive records
                    self._archive_provider_records(records, policy.archive_location)
                    
                    # Delete from main table
                    delete_query = text("DELETE FROM providers WHERE created_at < :cutoff_date")
                    session.execute(delete_query, {'cutoff_date': cutoff_date})
                    session.commit()
                
                elif policy.action == RetentionAction.ANONYMIZE:
                    # Anonymize records
                    self._anonymize_provider_records(records)
                
                elif policy.action == RetentionAction.DELETE:
                    # Delete records
                    delete_query = text("DELETE FROM providers WHERE created_at < :cutoff_date")
                    session.execute(delete_query, {'cutoff_date': cutoff_date})
                    session.commit()
            
            return {
                'affected_records': total_records,
                'affected_size_bytes': total_size,
                'success': True,
                'details': {'cutoff_date': cutoff_date.isoformat(), 'action': policy.action.value}
            }
            
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    def _cleanup_audit_logs(self, policy: RetentionPolicy) -> Dict[str, Any]:
        """Cleanup audit logs based on retention policy"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=policy.retention_days)
        
        session = self.SessionLocal()
        try:
            if policy.dry_run:
                # Count records that would be affected
                count_query = text("""
                    SELECT COUNT(*) as count, 
                           COALESCE(SUM(pg_column_size(audit_logs.*)), 0) as size_bytes
                    FROM audit_logs 
                    WHERE timestamp < :cutoff_date
                """)
                result = session.execute(count_query, {'cutoff_date': cutoff_date}).fetchone()
                
                return {
                    'affected_records': result.count,
                    'affected_size_bytes': result.size_bytes,
                    'success': True,
                    'details': {'dry_run': True, 'cutoff_date': cutoff_date.isoformat()}
                }
            
            # Get records to be archived
            select_query = text("""
                SELECT id, timestamp, 
                       pg_column_size(audit_logs.*) as size_bytes
                FROM audit_logs 
                WHERE timestamp < :cutoff_date
                ORDER BY timestamp
            """)
            records = session.execute(select_query, {'cutoff_date': cutoff_date}).fetchall()
            
            total_records = len(records)
            total_size = sum(record.size_bytes for record in records)
            
            if total_records > 0:
                if policy.action == RetentionAction.ARCHIVE:
                    # Archive records
                    self._archive_audit_logs(records, policy.archive_location)
                    
                    # Delete from main table
                    delete_query = text("DELETE FROM audit_logs WHERE timestamp < :cutoff_date")
                    session.execute(delete_query, {'cutoff_date': cutoff_date})
                    session.commit()
                
                elif policy.action == RetentionAction.DELETE:
                    # Delete records
                    delete_query = text("DELETE FROM audit_logs WHERE timestamp < :cutoff_date")
                    session.execute(delete_query, {'cutoff_date': cutoff_date})
                    session.commit()
            
            return {
                'affected_records': total_records,
                'affected_size_bytes': total_size,
                'success': True,
                'details': {'cutoff_date': cutoff_date.isoformat(), 'action': policy.action.value}
            }
            
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    def _cleanup_temp_files(self, policy: RetentionPolicy) -> Dict[str, Any]:
        """Cleanup temporary files"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=policy.retention_days)
        affected_files = 0
        total_size = 0
        
        try:
            for root, dirs, files in os.walk(self.temp_storage_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        file_stat = os.stat(file_path)
                        file_time = datetime.fromtimestamp(file_stat.st_mtime, tz=timezone.utc)
                        
                        if file_time < cutoff_date:
                            if not policy.dry_run:
                                os.remove(file_path)
                            
                            affected_files += 1
                            total_size += file_stat.st_size
                    
                    except (OSError, FileNotFoundError):
                        # File might have been deleted by another process
                        continue
            
            return {
                'affected_records': affected_files,
                'affected_size_bytes': total_size,
                'success': True,
                'details': {'cutoff_date': cutoff_date.isoformat(), 'action': policy.action.value}
            }
            
        except Exception as e:
            return {
                'affected_records': 0,
                'affected_size_bytes': 0,
                'success': False,
                'error_message': str(e)
            }
    
    def _cleanup_raw_scans(self, policy: RetentionPolicy) -> Dict[str, Any]:
        """Cleanup raw scan files (strict 90-day limit)"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=policy.retention_days)
        affected_files = 0
        total_size = 0
        
        try:
            # Define raw scan file patterns
            scan_patterns = ['*.pdf', '*.jpg', '*.jpeg', '*.png', '*.tiff', '*.bmp']
            scan_directories = [
                os.path.join(self.temp_storage_path, 'scans'),
                os.path.join(self.temp_storage_path, 'uploads'),
                os.path.join(self.temp_storage_path, 'ocr_input')
            ]
            
            for scan_dir in scan_directories:
                if not os.path.exists(scan_dir):
                    continue
                
                for root, dirs, files in os.walk(scan_dir):
                    for file in files:
                        if any(file.lower().endswith(pattern.replace('*', '')) for pattern in scan_patterns):
                            file_path = os.path.join(root, file)
                            try:
                                file_stat = os.stat(file_path)
                                file_time = datetime.fromtimestamp(file_stat.st_mtime, tz=timezone.utc)
                                
                                if file_time < cutoff_date:
                                    if not policy.dry_run:
                                        # Securely delete file
                                        self._secure_delete_file(file_path)
                                    
                                    affected_files += 1
                                    total_size += file_stat.st_size
                            
                            except (OSError, FileNotFoundError):
                                continue
            
            return {
                'affected_records': affected_files,
                'affected_size_bytes': total_size,
                'success': True,
                'details': {'cutoff_date': cutoff_date.isoformat(), 'action': policy.action.value}
            }
            
        except Exception as e:
            return {
                'affected_records': 0,
                'affected_size_bytes': 0,
                'success': False,
                'error_message': str(e)
            }
    
    def _cleanup_validation_results(self, policy: RetentionPolicy) -> Dict[str, Any]:
        """Cleanup validation results"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=policy.retention_days)
        
        session = self.SessionLocal()
        try:
            if policy.dry_run:
                count_query = text("""
                    SELECT COUNT(*) as count, 
                           COALESCE(SUM(pg_column_size(validation_results.*)), 0) as size_bytes
                    FROM validation_results 
                    WHERE created_at < :cutoff_date
                """)
                result = session.execute(count_query, {'cutoff_date': cutoff_date}).fetchone()
                
                return {
                    'affected_records': result.count,
                    'affected_size_bytes': result.size_bytes,
                    'success': True,
                    'details': {'dry_run': True, 'cutoff_date': cutoff_date.isoformat()}
                }
            
            # Get records to be processed
            select_query = text("""
                SELECT id, created_at, 
                       pg_column_size(validation_results.*) as size_bytes
                FROM validation_results 
                WHERE created_at < :cutoff_date
                ORDER BY created_at
            """)
            records = session.execute(select_query, {'cutoff_date': cutoff_date}).fetchall()
            
            total_records = len(records)
            total_size = sum(record.size_bytes for record in records)
            
            if total_records > 0:
                if policy.action == RetentionAction.ARCHIVE:
                    # Archive records
                    self._archive_validation_results(records, policy.archive_location)
                    
                    # Delete from main table
                    delete_query = text("DELETE FROM validation_results WHERE created_at < :cutoff_date")
                    session.execute(delete_query, {'cutoff_date': cutoff_date})
                    session.commit()
                
                elif policy.action == RetentionAction.DELETE:
                    # Delete records
                    delete_query = text("DELETE FROM validation_results WHERE created_at < :cutoff_date")
                    session.execute(delete_query, {'cutoff_date': cutoff_date})
                    session.commit()
            
            return {
                'affected_records': total_records,
                'affected_size_bytes': total_size,
                'success': True,
                'details': {'cutoff_date': cutoff_date.isoformat(), 'action': policy.action.value}
            }
            
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    def _cleanup_cache_data(self, policy: RetentionPolicy) -> Dict[str, Any]:
        """Cleanup cache data"""
        # This would typically clean Redis cache
        # For now, return a placeholder implementation
        return {
            'affected_records': 0,
            'affected_size_bytes': 0,
            'success': True,
            'details': {'action': 'cache_cleanup', 'note': 'Cache cleanup implemented via Redis TTL'}
        }
    
    def _cleanup_session_data(self, policy: RetentionPolicy) -> Dict[str, Any]:
        """Cleanup session data"""
        # This would typically clean session storage
        return {
            'affected_records': 0,
            'affected_size_bytes': 0,
            'success': True,
            'details': {'action': 'session_cleanup', 'note': 'Session cleanup implemented via Redis TTL'}
        }
    
    def _cleanup_backup_files(self, policy: RetentionPolicy) -> Dict[str, Any]:
        """Cleanup backup files"""
        backup_path = os.getenv('BACKUP_LOCAL_PATH', '/var/backups/provider-validation')
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=policy.retention_days)
        affected_files = 0
        total_size = 0
        
        try:
            if not os.path.exists(backup_path):
                return {
                    'affected_records': 0,
                    'affected_size_bytes': 0,
                    'success': True,
                    'details': {'backup_path': backup_path, 'note': 'Backup path does not exist'}
                }
            
            for root, dirs, files in os.walk(backup_path):
                for file in files:
                    if file.endswith(('.sql', '.dump', '.gz', '.zip')):
                        file_path = os.path.join(root, file)
                        try:
                            file_stat = os.stat(file_path)
                            file_time = datetime.fromtimestamp(file_stat.st_mtime, tz=timezone.utc)
                            
                            if file_time < cutoff_date:
                                if not policy.dry_run:
                                    os.remove(file_path)
                                
                                affected_files += 1
                                total_size += file_stat.st_size
                        
                        except (OSError, FileNotFoundError):
                            continue
            
            return {
                'affected_records': affected_files,
                'affected_size_bytes': total_size,
                'success': True,
                'details': {'cutoff_date': cutoff_date.isoformat(), 'action': policy.action.value}
            }
            
        except Exception as e:
            return {
                'affected_records': 0,
                'affected_size_bytes': 0,
                'success': False,
                'error_message': str(e)
            }
    
    def _cleanup_log_files(self, policy: RetentionPolicy) -> Dict[str, Any]:
        """Cleanup and compress log files"""
        log_path = os.getenv('LOG_FILE_PATH', '/var/log/provider-validation')
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=policy.retention_days)
        affected_files = 0
        total_size = 0
        
        try:
            if not os.path.exists(log_path):
                return {
                    'affected_records': 0,
                    'affected_size_bytes': 0,
                    'success': True,
                    'details': {'log_path': log_path, 'note': 'Log path does not exist'}
                }
            
            for root, dirs, files in os.walk(log_path):
                for file in files:
                    if file.endswith('.log') and not file.endswith('.gz'):
                        file_path = os.path.join(root, file)
                        try:
                            file_stat = os.stat(file_path)
                            file_time = datetime.fromtimestamp(file_stat.st_mtime, tz=timezone.utc)
                            
                            if file_time < cutoff_date:
                                if not policy.dry_run:
                                    if policy.action == RetentionAction.COMPRESS:
                                        # Compress the log file
                                        import gzip
                                        with open(file_path, 'rb') as f_in:
                                            with gzip.open(f"{file_path}.gz", 'wb') as f_out:
                                                shutil.copyfileobj(f_in, f_out)
                                        os.remove(file_path)
                                    elif policy.action == RetentionAction.DELETE:
                                        os.remove(file_path)
                                
                                affected_files += 1
                                total_size += file_stat.st_size
                        
                        except (OSError, FileNotFoundError):
                            continue
            
            return {
                'affected_records': affected_files,
                'affected_size_bytes': total_size,
                'success': True,
                'details': {'cutoff_date': cutoff_date.isoformat(), 'action': policy.action.value}
            }
            
        except Exception as e:
            return {
                'affected_records': 0,
                'affected_size_bytes': 0,
                'success': False,
                'error_message': str(e)
            }
    
    def _secure_delete_file(self, file_path: str):
        """Securely delete a file by overwriting it first"""
        try:
            # Get file size
            file_size = os.path.getsize(file_path)
            
            # Overwrite with random data
            with open(file_path, 'r+b') as f:
                f.write(os.urandom(file_size))
                f.flush()
                os.fsync(f.fileno())
            
            # Delete the file
            os.remove(file_path)
            
        except Exception as e:
            self.logger.error(f"Failed to securely delete file {file_path}: {e}")
            # Fallback to regular delete
            os.remove(file_path)
    
    def _archive_provider_records(self, records: List, archive_location: str):
        """Archive provider records"""
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        archive_file = os.path.join(archive_location, f"providers_archive_{timestamp}.json")
        
        archived_data = []
        for record in records:
            archived_data.append({
                'provider_id': record.provider_id,
                'created_at': record.created_at.isoformat(),
                'size_bytes': record.size_bytes
            })
        
        with open(archive_file, 'w') as f:
            json.dump(archived_data, f, indent=2)
    
    def _archive_audit_logs(self, records: List, archive_location: str):
        """Archive audit log records"""
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        archive_file = os.path.join(archive_location, f"audit_logs_archive_{timestamp}.json")
        
        archived_data = []
        for record in records:
            archived_data.append({
                'id': record.id,
                'timestamp': record.timestamp.isoformat(),
                'size_bytes': record.size_bytes
            })
        
        with open(archive_file, 'w') as f:
            json.dump(archived_data, f, indent=2)
    
    def _archive_validation_results(self, records: List, archive_location: str):
        """Archive validation result records"""
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        archive_file = os.path.join(archive_location, f"validation_results_archive_{timestamp}.json")
        
        archived_data = []
        for record in records:
            archived_data.append({
                'id': record.id,
                'created_at': record.created_at.isoformat(),
                'size_bytes': record.size_bytes
            })
        
        with open(archive_file, 'w') as f:
            json.dump(archived_data, f, indent=2)
    
    def _anonymize_provider_records(self, records: List):
        """Anonymize provider records"""
        # This would implement data anonymization
        # For now, it's a placeholder
        pass
    
    def _send_retention_notification(self, event: RetentionEvent):
        """Send retention notification"""
        if not self.notification_callback:
            return
        
        message = f"Retention Policy Executed: {event.policy_type.value}"
        details = {
            'policy_type': event.policy_type.value,
            'action': event.action.value,
            'affected_records': event.affected_records,
            'affected_size_mb': round(event.affected_size_bytes / (1024 * 1024), 2),
            'success': event.success,
            'timestamp': event.timestamp.isoformat()
        }
        
        if event.error_message:
            details['error_message'] = event.error_message
        
        self.notification_callback(message, details)
    
    def get_retention_summary(self) -> Dict[str, Any]:
        """Get summary of all retention policies"""
        summary = {}
        
        for policy_type, policy in self.policies.items():
            summary[policy_type.value] = {
                'retention_days': policy.retention_days,
                'action': policy.action.value,
                'description': policy.description,
                'compliance_requirement': policy.compliance_requirement,
                'auto_cleanup_enabled': policy.auto_cleanup_enabled,
                'cleanup_schedule': policy.cleanup_schedule,
                'notification_enabled': policy.notification_enabled
            }
        
        return summary
    
    def update_retention_policy(self, policy_type: RetentionPolicyType, policy: RetentionPolicy):
        """Update retention policy"""
        self.policies[policy_type] = policy
        self.logger.info(f"Updated retention policy for {policy_type.value}")
    
    def execute_all_retention_policies(self, dry_run: bool = False) -> List[RetentionEvent]:
        """Execute all retention policies"""
        events = []
        
        for policy_type in self.policies.keys():
            try:
                event = self.execute_retention_policy(policy_type, dry_run)
                events.append(event)
            except Exception as e:
                self.logger.error(f"Failed to execute retention policy for {policy_type.value}: {e}")
                # Create failure event
                event = RetentionEvent(
                    timestamp=datetime.now(timezone.utc),
                    policy_type=policy_type,
                    action=RetentionAction.DELETE,
                    affected_records=0,
                    affected_size_bytes=0,
                    success=False,
                    error_message=str(e)
                )
                events.append(event)
        
        return events

# Global retention manager instance
retention_manager: Optional[RetentionManager] = None

def initialize_retention_manager(database_url: str,
                                audit_callback: Optional[Callable[[RetentionEvent], None]] = None,
                                notification_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None) -> RetentionManager:
    """Initialize global retention manager"""
    global retention_manager
    retention_manager = RetentionManager(database_url, audit_callback, notification_callback)
    return retention_manager

def get_retention_manager() -> RetentionManager:
    """Get global retention manager instance"""
    if retention_manager is None:
        raise RuntimeError("Retention manager not initialized. Call initialize_retention_manager() first.")
    return retention_manager
