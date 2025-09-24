"""
Provider Data Validation & Directory Management API
FastAPI backend for healthcare provider validation system
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import uvicorn
import logging
from typing import List, Optional

from .config import settings
from .database import init_db
from .models import Provider, ValidationJob, ValidationResult
from .schemas import (
    ProviderCreate, ProviderUpdate, ProviderResponse,
    ValidationJobCreate, ValidationJobResponse,
    ValidationResultResponse, DashboardStats
)
from .services import ProviderService, ValidationService
from .middleware import SecurityHeadersMiddleware, LoggingMiddleware
from .routers import providers, validation, dashboard, health

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format=settings.LOG_FORMAT
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting Provider Validation API...")
    await init_db()
    logger.info("Database initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Provider Validation API...")

# Create FastAPI application
app = FastAPI(
    title="Provider Validation API",
    description="Healthcare Provider Data Validation & Directory Management System",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(LoggingMiddleware)

# Include routers
app.include_router(health.router, prefix="/api/health", tags=["health"])
app.include_router(providers.router, prefix="/api/providers", tags=["providers"])
app.include_router(validation.router, prefix="/api/validation", tags=["validation"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Provider Validation API",
        "version": "1.0.0",
        "status": "healthy"
    }

@app.get("/api/status")
async def status():
    """API status endpoint"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
