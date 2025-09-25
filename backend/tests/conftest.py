"""
Pytest Configuration and Fixtures

This module provides shared fixtures and configuration for all tests.
"""

import pytest
import asyncio
import tempfile
import os
from typing import Dict, Any, List
from unittest.mock import Mock, patch
import redis
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Import test models
from backend.models import Base
from backend.models.provider import Provider
from backend.models.validation import ValidationJob, ValidationResult

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    # Create in-memory SQLite database
    engine = create_engine(
        "sqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False}
    )
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    # Create session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def mock_redis():
    """Create a mock Redis client for testing."""
    with patch('redis.Redis') as mock_redis_class:
        mock_redis_client = Mock()
        mock_redis_class.return_value = mock_redis_client
        
        # Mock common Redis operations
        mock_redis_client.incr.return_value = 1
        mock_redis_client.expire.return_value = True
        mock_redis_client.get.return_value = None
        mock_redis_client.set.return_value = True
        mock_redis_client.setex.return_value = True
        mock_redis_client.exists.return_value = False
        mock_redis_client.publish.return_value = 1
        
        yield mock_redis_client

@pytest.fixture
def mock_httpx():
    """Create a mock httpx client for testing."""
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Mock common HTTP operations
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_response.text = ""
        
        mock_client.get.return_value = mock_response
        mock_client.post.return_value = mock_response
        mock_client.put.return_value = mock_response
        mock_client.delete.return_value = mock_response
        
        yield mock_client

@pytest.fixture
def sample_provider_data():
    """Sample provider data for testing."""
    return {
        "provider_id": "TEST_PROV_001",
        "npi_number": "1234567890",
        "given_name": "John",
        "family_name": "Smith",
        "phone_primary": "+1-555-123-4567",
        "email": "john.smith@example.com",
        "address_street": "123 Main St",
        "address_city": "San Francisco",
        "address_state": "CA",
        "address_zip": "94102",
        "license_number": "A12345",
        "license_state": "CA",
        "primary_taxonomy": "Family Medicine",
        "practice_name": "Smith Family Practice",
        "phone_alt": "+1-555-123-4568",
        "affiliations": ["Hospital A", "Clinic B"],
        "services_offered": {
            "primary_care": True,
            "preventive_care": True,
            "chronic_disease_management": True
        }
    }

@pytest.fixture
def sample_validation_result():
    """Sample validation result for testing."""
    return {
        "provider_id": "TEST_PROV_001",
        "overall_confidence": 0.85,
        "validation_status": "valid",
        "field_confidence": {
            "npi_number": 0.9,
            "address": 0.8,
            "license": 0.95,
            "email": 0.7,
            "phone": 0.75
        },
        "flags": [],
        "sources": ["npi", "google_places", "state_board"],
        "created_at": "2024-01-15T10:30:00Z"
    }

@pytest.fixture
def mock_external_api_responses():
    """Mock responses from external APIs."""
    return {
        "npi_success": {
            "result_count": 1,
            "results": [
                {
                    "number": "1234567890",
                    "basic": {
                        "first_name": "JOHN",
                        "last_name": "SMITH",
                        "credential": "MD"
                    },
                    "addresses": [
                        {
                            "address_1": "123 MAIN ST",
                            "city": "SAN FRANCISCO",
                            "state": "CA",
                            "postal_code": "94102",
                            "telephone_number": "555-123-4567"
                        }
                    ],
                    "taxonomies": [
                        {
                            "code": "207Q00000X",
                            "desc": "Family Medicine",
                            "primary": True,
                            "license": "A12345"
                        }
                    ]
                }
            ]
        },
        "google_places_success": {
            "results": [
                {
                    "formatted_address": "123 Main St, San Francisco, CA 94102, USA",
                    "geometry": {
                        "location": {"lat": 37.7749, "lng": -122.4194}
                    },
                    "place_id": "ChIJd8BlQ2BZwokRAFQEcDlJRAI"
                }
            ],
            "status": "OK"
        },
        "state_board_success": {
            "license_number": "A12345",
            "license_status": "ACTIVE",
            "provider_name": "JOHN SMITH"
        }
    }

@pytest.fixture
def mock_jwt_tokens():
    """Mock JWT tokens for testing."""
    return {
        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.test.access.token",
        "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.test.refresh.token",
        "expires_in": 900
    }

@pytest.fixture
def mock_user_claims():
    """Mock user claims for testing."""
    return {
        "user_id": "user_123",
        "username": "test_user",
        "email": "test@example.com",
        "role": "reviewer",
        "permissions": [
            "provider:read",
            "provider:update",
            "validation:review",
            "pii:reveal"
        ],
        "session_id": "session_123",
        "issued_at": "2024-01-15T10:00:00Z",
        "expires_at": "2024-01-15T10:15:00Z"
    }

@pytest.fixture
def temp_file():
    """Create a temporary file for testing."""
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"test content")
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    try:
        os.unlink(temp_path)
    except OSError:
        pass

@pytest.fixture
def temp_directory():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir

@pytest.fixture
def mock_audit_logger():
    """Mock audit logger for testing."""
    with patch('backend.auth.audit_logger.get_audit_logger') as mock_audit:
        mock_logger = Mock()
        mock_audit.return_value = mock_logger
        yield mock_logger

@pytest.fixture
def mock_rate_limiter():
    """Mock rate limiter for testing."""
    with patch('backend.utils.rate_limiter.RateLimiter') as mock_limiter:
        mock_instance = Mock()
        mock_instance.check_rate_limit.return_value = Mock(
            allowed=True,
            remaining=100,
            reset_time=1234567890
        )
        mock_limiter.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def mock_pii_handler():
    """Mock PII handler for testing."""
    with patch('backend.auth.pii_handler.get_pii_handler') as mock_pii:
        mock_instance = Mock()
        mock_instance.mask_pii_field.return_value = "***-***-4567"
        mock_instance.reveal_pii_field.return_value = "+1-555-123-4567"
        mock_instance.encrypt_pii_value.return_value = "encrypted_value"
        mock_pii.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def mock_ocr_pipeline():
    """Mock OCR pipeline for testing."""
    with patch('backend.pipelines.ocr.OCRPipeline') as mock_ocr:
        mock_instance = Mock()
        mock_instance.extract_text.return_value = Mock(
            text="Extracted text from document",
            confidence=0.9,
            raw_response={"mock": "response"}
        )
        mock_instance.extract_structured_fields.return_value = Mock(
            name="John Smith",
            address="123 Main St",
            phone="555-123-4567",
            license_number="A12345",
            email="john@example.com"
        )
        mock_ocr.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def mock_validation_workers():
    """Mock validation workers for testing."""
    with patch('backend.services.validator.ValidationOrchestrator._run_validation_workers') as mock_workers:
        mock_workers.return_value = {
            "npi": Mock(
                source="npi",
                confidence=0.9,
                is_valid=True,
                normalized_data={"npi_number": "1234567890"},
                metadata={}
            ),
            "google_places": Mock(
                source="google_places",
                confidence=0.85,
                is_valid=True,
                normalized_data={"place_id": "test_place_id"},
                metadata={}
            ),
            "state_board": Mock(
                source="state_board",
                confidence=0.95,
                is_valid=True,
                normalized_data={"license_status": "ACTIVE"},
                metadata={}
            ),
            "email": Mock(
                source="internal",
                confidence=0.8,
                is_valid=True,
                normalized_data={"email": "john@example.com"},
                metadata={}
            ),
            "phone": Mock(
                source="internal",
                confidence=0.75,
                is_valid=True,
                normalized_data={"phone": "+15551234567"},
                metadata={}
            )
        }
        yield mock_workers

@pytest.fixture
def mock_queue_manager():
    """Mock queue manager for testing."""
    with patch('backend.workers.queue_manager.QueueManager') as mock_queue:
        mock_instance = Mock()
        mock_instance.start_worker.return_value = True
        mock_instance.stop_worker.return_value = True
        mock_instance.get_queue_status.return_value = {
            "status": "running",
            "worker_count": 4,
            "pending_jobs": 0,
            "completed_jobs": 100
        }
        mock_queue.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def performance_test_data():
    """Generate test data for performance testing."""
    providers = []
    for i in range(100):
        providers.append({
            "provider_id": f"PERF_{i:03d}",
            "npi_number": f"{1000000000 + i}",
            "given_name": f"Provider{i}",
            "family_name": "Test",
            "phone_primary": f"+1-555-{i:03d}-{i:04d}",
            "email": f"provider{i}@example.com",
            "address_street": f"{100 + i} Test St",
            "address_city": "Test City",
            "address_state": "CA",
            "address_zip": f"{90000 + i}",
            "license_number": f"TEST{i:05d}",
            "license_state": "CA"
        })
    return providers

# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom settings."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as an end-to-end test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as a performance test"
    )
    config.addinivalue_line(
        "markers", "fuzz: mark test as a fuzz test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )

def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test location."""
    for item in items:
        # Add markers based on test file location
        if "unit" in item.nodeid:
            item.add_marker(pytest.mark.unit)
        elif "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        elif "e2e" in item.nodeid:
            item.add_marker(pytest.mark.e2e)
        elif "performance" in item.nodeid:
            item.add_marker(pytest.mark.performance)
        elif "fuzz" in item.nodeid:
            item.add_marker(pytest.mark.fuzz)
        
        # Mark slow tests
        if "performance" in item.nodeid or "integration" in item.nodeid:
            item.add_marker(pytest.mark.slow)