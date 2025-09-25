"""
Environment Configuration Management

This module provides secure environment variable management with validation,
default values, and secrets handling.
"""

import os
import base64
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import logging

class Environment(Enum):
    """Environment types"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"

@dataclass
class DatabaseConfig:
    """Database configuration"""
    url: str
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None
    ssl_root_cert_path: Optional[str] = None
    encryption_enabled: bool = True
    encryption_key_id: Optional[str] = None
    backup_encryption_key_id: Optional[str] = None
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30

@dataclass
class JWTConfig:
    """JWT configuration"""
    secret_key: str
    public_key: str
    algorithm: str = "RS256"
    access_token_expiry: int = 900  # 15 minutes
    refresh_token_expiry: int = 604800  # 7 days

@dataclass
class EncryptionConfig:
    """Encryption configuration"""
    key: bytes
    salt: bytes
    algorithm: str = "AES-256-GCM"

@dataclass
class RedisConfig:
    """Redis configuration"""
    url: str
    password: Optional[str] = None
    ssl_enabled: bool = False
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None

@dataclass
class SecurityConfig:
    """Security configuration"""
    rate_limit_enabled: bool = True
    global_requests_per_minute: int = 1000
    global_requests_per_hour: int = 10000
    global_requests_per_day: int = 100000
    cors_origins: List[str] = None
    cors_credentials: bool = True
    cors_max_age: int = 86400
    csrf_secret_key: str = ""
    csrf_token_expiry: int = 3600

@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    format: str = "json"
    file_path: Optional[str] = None
    sentry_dsn: Optional[str] = None
    sentry_environment: Optional[str] = None

@dataclass
class RetentionConfig:
    """Data retention configuration"""
    provider_data_days: int = 2555  # 7 years
    audit_log_days: int = 3650  # 10 years
    validation_result_days: int = 1825  # 5 years
    temp_file_days: int = 30
    raw_scan_days: int = 90

@dataclass
class APIConfig:
    """External API configuration"""
    npi_api_key: Optional[str] = None
    npi_api_base_url: str = "https://npiregistry.cms.hhs.gov/api/"
    google_places_api_key: Optional[str] = None
    google_geocoding_api_key: Optional[str] = None
    state_board_api_key: Optional[str] = None
    state_board_api_base_url: Optional[str] = None

class EnvironmentManager:
    """Environment configuration manager"""
    
    def __init__(self, env_file: Optional[str] = None):
        """
        Initialize environment manager
        
        Args:
            env_file: Path to .env file (optional)
        """
        self.env_file = env_file
        self.logger = logging.getLogger(__name__)
        
        # Load environment variables
        if env_file and os.path.exists(env_file):
            self._load_env_file(env_file)
        
        # Validate required environment variables
        self._validate_environment()
    
    def _load_env_file(self, env_file: str):
        """Load environment variables from .env file"""
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        # Remove quotes if present
                        value = value.strip().strip('"').strip("'")
                        os.environ[key.strip()] = value
        except Exception as e:
            self.logger.warning(f"Failed to load .env file: {e}")
    
    def _validate_environment(self):
        """Validate required environment variables"""
        required_vars = [
            'DATABASE_URL',
            'JWT_SECRET_KEY',
            'JWT_PUBLIC_KEY',
            'ENCRYPTION_KEY',
            'ENCRYPTION_SALT'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    def get_environment(self) -> Environment:
        """Get current environment"""
        env_str = os.getenv('ENVIRONMENT', 'development').lower()
        try:
            return Environment(env_str)
        except ValueError:
            self.logger.warning(f"Invalid environment '{env_str}', defaulting to development")
            return Environment.DEVELOPMENT
    
    def get_database_config(self) -> DatabaseConfig:
        """Get database configuration"""
        return DatabaseConfig(
            url=os.getenv('DATABASE_URL'),
            ssl_cert_path=os.getenv('DATABASE_SSL_CERT_PATH'),
            ssl_key_path=os.getenv('DATABASE_SSL_KEY_PATH'),
            ssl_root_cert_path=os.getenv('DATABASE_SSL_ROOT_CERT_PATH'),
            encryption_enabled=os.getenv('DATABASE_ENCRYPTION_ENABLED', 'true').lower() == 'true',
            encryption_key_id=os.getenv('DATABASE_ENCRYPTION_KEY_ID'),
            backup_encryption_key_id=os.getenv('DATABASE_BACKUP_ENCRYPTION_KEY_ID'),
            pool_size=int(os.getenv('DB_POOL_SIZE', '10')),
            max_overflow=int(os.getenv('DB_MAX_OVERFLOW', '20')),
            pool_timeout=int(os.getenv('DB_POOL_TIMEOUT', '30'))
        )
    
    def get_jwt_config(self) -> JWTConfig:
        """Get JWT configuration"""
        return JWTConfig(
            secret_key=os.getenv('JWT_SECRET_KEY'),
            public_key=os.getenv('JWT_PUBLIC_KEY'),
            algorithm=os.getenv('JWT_ALGORITHM', 'RS256'),
            access_token_expiry=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRY', '900')),
            refresh_token_expiry=int(os.getenv('JWT_REFRESH_TOKEN_EXPIRY', '604800'))
        )
    
    def get_encryption_config(self) -> EncryptionConfig:
        """Get encryption configuration"""
        encryption_key = os.getenv('ENCRYPTION_KEY')
        encryption_salt = os.getenv('ENCRYPTION_SALT')
        
        if not encryption_key or not encryption_salt:
            raise ValueError("ENCRYPTION_KEY and ENCRYPTION_SALT are required")
        
        try:
            # Decode base64 encoded keys
            key_bytes = base64.b64decode(encryption_key)
            salt_bytes = base64.b64decode(encryption_salt)
            
            if len(key_bytes) != 32:
                raise ValueError("ENCRYPTION_KEY must be 32 bytes when base64 decoded")
            
            if len(salt_bytes) != 16:
                raise ValueError("ENCRYPTION_SALT must be 16 bytes when base64 decoded")
            
            return EncryptionConfig(
                key=key_bytes,
                salt=salt_bytes,
                algorithm=os.getenv('ENCRYPTION_ALGORITHM', 'AES-256-GCM')
            )
        except Exception as e:
            raise ValueError(f"Invalid encryption configuration: {e}")
    
    def get_redis_config(self) -> RedisConfig:
        """Get Redis configuration"""
        return RedisConfig(
            url=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
            password=os.getenv('REDIS_PASSWORD'),
            ssl_enabled=os.getenv('REDIS_SSL_ENABLED', 'false').lower() == 'true',
            ssl_cert_path=os.getenv('REDIS_SSL_CERT_PATH'),
            ssl_key_path=os.getenv('REDIS_SSL_KEY_PATH')
        )
    
    def get_security_config(self) -> SecurityConfig:
        """Get security configuration"""
        cors_origins = os.getenv('CORS_ORIGINS', '')
        cors_origins_list = [origin.strip() for origin in cors_origins.split(',') if origin.strip()] if cors_origins else []
        
        return SecurityConfig(
            rate_limit_enabled=os.getenv('RATE_LIMIT_ENABLED', 'true').lower() == 'true',
            global_requests_per_minute=int(os.getenv('RATE_LIMIT_GLOBAL_REQUESTS_PER_MINUTE', '1000')),
            global_requests_per_hour=int(os.getenv('RATE_LIMIT_GLOBAL_REQUESTS_PER_HOUR', '10000')),
            global_requests_per_day=int(os.getenv('RATE_LIMIT_GLOBAL_REQUESTS_PER_DAY', '100000')),
            cors_origins=cors_origins_list,
            cors_credentials=os.getenv('CORS_CREDENTIALS', 'true').lower() == 'true',
            cors_max_age=int(os.getenv('CORS_MAX_AGE', '86400')),
            csrf_secret_key=os.getenv('CSRF_SECRET_KEY', ''),
            csrf_token_expiry=int(os.getenv('CSRF_TOKEN_EXPIRY', '3600'))
        )
    
    def get_logging_config(self) -> LoggingConfig:
        """Get logging configuration"""
        return LoggingConfig(
            level=os.getenv('LOG_LEVEL', 'INFO'),
            format=os.getenv('LOG_FORMAT', 'json'),
            file_path=os.getenv('LOG_FILE_PATH'),
            sentry_dsn=os.getenv('SENTRY_DSN'),
            sentry_environment=os.getenv('SENTRY_ENVIRONMENT')
        )
    
    def get_retention_config(self) -> RetentionConfig:
        """Get data retention configuration"""
        return RetentionConfig(
            provider_data_days=int(os.getenv('PROVIDER_DATA_RETENTION_DAYS', '2555')),
            audit_log_days=int(os.getenv('AUDIT_LOG_RETENTION_DAYS', '3650')),
            validation_result_days=int(os.getenv('VALIDATION_RESULT_RETENTION_DAYS', '1825')),
            temp_file_days=int(os.getenv('TEMP_FILE_RETENTION_DAYS', '30')),
            raw_scan_days=int(os.getenv('RAW_SCAN_RETENTION_DAYS', '90'))
        )
    
    def get_api_config(self) -> APIConfig:
        """Get external API configuration"""
        return APIConfig(
            npi_api_key=os.getenv('NPI_API_KEY'),
            npi_api_base_url=os.getenv('NPI_API_BASE_URL', 'https://npiregistry.cms.hhs.gov/api/'),
            google_places_api_key=os.getenv('GOOGLE_PLACES_API_KEY'),
            google_geocoding_api_key=os.getenv('GOOGLE_GEOCODING_API_KEY'),
            state_board_api_key=os.getenv('STATE_BOARD_API_KEY'),
            state_board_api_base_url=os.getenv('STATE_BOARD_API_BASE_URL')
        )
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get boolean environment variable"""
        value = os.getenv(key, str(default))
        return value.lower() in ('true', '1', 'yes', 'on')
    
    def get_int(self, key: str, default: int = 0) -> int:
        """Get integer environment variable"""
        try:
            return int(os.getenv(key, str(default)))
        except ValueError:
            self.logger.warning(f"Invalid integer value for {key}, using default {default}")
            return default
    
    def get_float(self, key: str, default: float = 0.0) -> float:
        """Get float environment variable"""
        try:
            return float(os.getenv(key, str(default)))
        except ValueError:
            self.logger.warning(f"Invalid float value for {key}, using default {default}")
            return default
    
    def get_list(self, key: str, separator: str = ',', default: Optional[List[str]] = None) -> List[str]:
        """Get list environment variable"""
        value = os.getenv(key)
        if not value:
            return default or []
        
        return [item.strip() for item in value.split(separator) if item.strip()]
    
    def get_secret(self, key: str, required: bool = True) -> Optional[str]:
        """
        Get secret environment variable with logging
        
        Args:
            key: Secret key name
            required: Whether the secret is required
            
        Returns:
            Secret value or None
        """
        value = os.getenv(key)
        if not value and required:
            raise ValueError(f"Required secret {key} not found")
        
        if value:
            self.logger.debug(f"Accessed secret: {key}")
        
        return value
    
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.get_environment() == Environment.PRODUCTION
    
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.get_environment() == Environment.DEVELOPMENT
    
    def get_all_config(self) -> Dict[str, Any]:
        """Get all configuration as dictionary"""
        return {
            'environment': self.get_environment().value,
            'database': self.get_database_config().__dict__,
            'jwt': self.get_jwt_config().__dict__,
            'redis': self.get_redis_config().__dict__,
            'security': self.get_security_config().__dict__,
            'logging': self.get_logging_config().__dict__,
            'retention': self.get_retention_config().__dict__,
            'api': self.get_api_config().__dict__
        }

# Global environment manager instance
env_manager: Optional[EnvironmentManager] = None

def initialize_environment_manager(env_file: Optional[str] = None) -> EnvironmentManager:
    """Initialize global environment manager"""
    global env_manager
    env_manager = EnvironmentManager(env_file)
    return env_manager

def get_environment_manager() -> EnvironmentManager:
    """Get global environment manager instance"""
    if env_manager is None:
        raise RuntimeError("Environment manager not initialized. Call initialize_environment_manager() first.")
    return env_manager
