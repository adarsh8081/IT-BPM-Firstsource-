"""
Main FastAPI Application with Monitoring Integration

This module sets up the FastAPI application with comprehensive monitoring,
metrics collection, and alerting capabilities.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import time
import uvicorn

# Import monitoring components
from backend.monitoring.metrics import initialize_metrics, get_metrics_collector
from backend.monitoring.alerting import initialize_alert_manager, get_alert_manager
from backend.services.metrics_service import MetricsCollectionService

# Import API routers
from backend.api.metrics import router as metrics_router
from backend.api.validation import router as validation_router

# Import database and services
from backend.models import engine, SessionLocal
from backend.services.validator import ValidationOrchestrator
from backend.workers.queue_manager import QueueManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variables for services
metrics_service: MetricsCollectionService = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global metrics_service
    
    logger.info("Starting Provider Validation Application...")
    
    try:
        # Initialize monitoring components
        logger.info("Initializing monitoring components...")
        metrics_collector = initialize_metrics()
        alert_manager = initialize_alert_manager()
        
        # Initialize services
        logger.info("Initializing services...")
        db_session = SessionLocal()
        orchestrator = ValidationOrchestrator(
            database_url="sqlite:///provider_validation.db",
            redis_client=None  # Would be initialized with real Redis client
        )
        queue_manager = QueueManager()
        
        # Initialize metrics collection service
        metrics_service = MetricsCollectionService(
            db_session=db_session,
            orchestrator=orchestrator,
            queue_manager=queue_manager
        )
        
        # Start metrics collection
        await metrics_service.start()
        logger.info("Metrics collection service started")
        
        # Add metrics service to app state
        app.state.metrics_service = metrics_service
        app.state.metrics_collector = metrics_collector
        app.state.alert_manager = alert_manager
        
        logger.info("Application startup completed successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    finally:
        # Cleanup on shutdown
        logger.info("Shutting down application...")
        
        if metrics_service:
            await metrics_service.stop()
            logger.info("Metrics collection service stopped")
        
        if 'db_session' in locals():
            db_session.close()
            logger.info("Database session closed")
        
        logger.info("Application shutdown completed")

# Create FastAPI application
app = FastAPI(
    title="Provider Data Validation & Directory Management",
    description="Healthcare provider data validation system with comprehensive monitoring",
    version="1.0.0",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time header and collect metrics"""
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    
    # Add timing header
    response.headers["X-Process-Time"] = str(process_time)
    
    # Record metrics
    try:
        metrics_collector = get_metrics_collector()
        metrics_collector.record_api_request(
            method=request.method,
            endpoint=str(request.url.path),
            status_code=response.status_code,
            duration=process_time
        )
    except Exception as e:
        logger.error(f"Failed to record API metrics: {e}")
    
    return response

# Include API routers
app.include_router(metrics_router, tags=["monitoring"])
app.include_router(validation_router, tags=["validation"])

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check database connection
        db_session = SessionLocal()
        db_session.execute("SELECT 1")
        db_session.close()
        
        # Check metrics service
        metrics_service_status = "healthy"
        if hasattr(app.state, 'metrics_service') and app.state.metrics_service:
            if not app.state.metrics_service.is_running:
                metrics_service_status = "unhealthy"
        
        return JSONResponse(content={
            "status": "healthy",
            "timestamp": time.time(),
            "services": {
                "database": "healthy",
                "metrics_collection": metrics_service_status,
                "alerting": "healthy"
            }
        })
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": time.time(),
                "error": str(e)
            }
        )

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with system information"""
    return JSONResponse(content={
        "message": "Provider Data Validation & Directory Management API",
        "version": "1.0.0",
        "docs": "/docs",
        "metrics": "/api/metrics/prometheus",
        "health": "/health",
        "monitoring": {
            "grafana": "http://localhost:3001",
            "prometheus": "http://localhost:9090",
            "alertmanager": "http://localhost:9093"
        }
    })

# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    # Record error metrics
    try:
        metrics_collector = get_metrics_collector()
        metrics_collector.record_job_failure(
            job_type="api_request",
            error_type=type(exc).__name__
        )
    except Exception as e:
        logger.error(f"Failed to record error metrics: {e}")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "timestamp": time.time()
        }
    )

# Startup event
@app.on_event("startup")
async def startup_event():
    """Additional startup tasks"""
    logger.info("Application startup event triggered")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Additional shutdown tasks"""
    logger.info("Application shutdown event triggered")

if __name__ == "__main__":
    # Run the application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )