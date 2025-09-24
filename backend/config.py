"""
Configuration management for the Provider Validation API
"""

from pydantic_settings import BaseSettings
from typing import List, Optional
import os

class Settings(BaseSettings):
    """Application settings"""
    
    # Database
    DATABASE_URL: str = "postgresql://username:password@localhost:5432/provider_validation"
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # API Keys
    NPI_API_KEY: Optional[str] = None
    GOOGLE_PLACES_API_KEY: Optional[str] = None
    GOOGLE_MAPS_API_KEY: Optional[str] = None
    
    # Application
    SECRET_KEY: str = "your-secret-key-change-in-production"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    
    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]
    
    # Rate Limiting
    NPI_API_RATE_LIMIT: int = 100
    GOOGLE_API_RATE_LIMIT: int = 1000
    STATE_BOARD_RATE_LIMIT: int = 10
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    # File Storage
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 10485760  # 10MB
    
    # Validation Settings
    AUTO_VALIDATION: bool = True
    VALIDATION_INTERVAL: int = 24  # hours
    MAX_RETRIES: int = 3
    TIMEOUT_SECONDS: int = 30
    
    # Security
    ALLOWED_HOSTS: List[str] = ["*"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Create settings instance
settings = Settings()

# Ensure upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
