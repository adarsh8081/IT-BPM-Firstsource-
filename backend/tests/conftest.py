"""
Pytest configuration and fixtures
"""

import pytest
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from httpx import AsyncClient

from backend.main import app
from backend.database import Base, get_db
from backend.config import settings

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=True,
    future=True
)

# Create test session factory
TestSessionLocal = sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def setup_test_db():
    """Set up test database"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def db_session(setup_test_db):
    """Create a test database session"""
    async with TestSessionLocal() as session:
        yield session

@pytest.fixture
def client(db_session):
    """Create a test client"""
    def override_get_db():
        return db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()

@pytest.fixture
async def async_client(db_session):
    """Create an async test client"""
    def override_get_db():
        return db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()

@pytest.fixture
def sample_provider_data():
    """Sample provider data for testing"""
    return {
        "npi": "1234567890",
        "first_name": "John",
        "last_name": "Doe",
        "middle_name": "Michael",
        "specialty": "Internal Medicine",
        "organization": "Test Hospital",
        "organization_npi": "0987654321",
        "email": "john.doe@testhospital.com",
        "phone": "(555) 123-4567",
        "address_line1": "123 Main St",
        "city": "Test City",
        "state": "CA",
        "zip_code": "12345",
        "country": "US",
        "license_number": "CA123456",
        "license_state": "CA",
        "license_expiry": "2025-12-31T00:00:00"
    }

@pytest.fixture
def sample_validation_job_data():
    """Sample validation job data for testing"""
    return {
        "provider_id": "123e4567-e89b-12d3-a456-426614174000",
        "priority": "medium",
        "validate_npi": True,
        "validate_address": True,
        "validate_license": True
    }
