"""
Tests for the precise provider model
"""

import pytest
import uuid
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models.provider import Provider, Base


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def sample_provider_data():
    """Sample provider data for testing"""
    return {
        "given_name": "John",
        "family_name": "Doe",
        "npi_number": "1234567890",
        "primary_taxonomy": "207Q00000X",
        "practice_name": "Doe Family Medicine",
        "address_street": "123 Main St",
        "address_city": "Anytown",
        "address_state": "CA",
        "address_zip": "12345",
        "place_id": "ChIJ1234567890",
        "phone_primary": "555-123-4567",
        "phone_alt": "555-987-6543",
        "email": "john.doe@example.com",
        "license_number": "A123456",
        "license_state": "CA",
        "license_status": "active",
        "affiliations": [
            {"organization": "General Hospital", "role": "Attending Physician"},
            {"organization": "Medical Group", "role": "Partner"}
        ],
        "services_offered": {
            "primary_care": True,
            "pediatrics": False,
            "internal_medicine": True,
            "preventive_care": True
        }
    }


class TestProviderModel:
    """Test cases for the Provider model"""

    def test_create_provider(self, db_session, sample_provider_data):
        """Test creating a provider with all fields"""
        provider = Provider(**sample_provider_data)
        db_session.add(provider)
        db_session.commit()
        
        assert provider.provider_id is not None
        assert provider.given_name == "John"
        assert provider.family_name == "Doe"
        assert provider.npi_number == "1234567890"
        assert provider.primary_taxonomy == "207Q00000X"
        assert provider.practice_name == "Doe Family Medicine"
        assert provider.address_street == "123 Main St"
        assert provider.address_city == "Anytown"
        assert provider.address_state == "CA"
        assert provider.address_zip == "12345"
        assert provider.place_id == "ChIJ1234567890"
        assert provider.phone_primary == "555-123-4567"
        assert provider.phone_alt == "555-987-6543"
        assert provider.email == "john.doe@example.com"
        assert provider.license_number == "A123456"
        assert provider.license_state == "CA"
        assert provider.license_status == "active"
        assert len(provider.affiliations) == 2
        assert provider.services_offered["primary_care"] is True
        assert provider.services_offered["pediatrics"] is False

    def test_provider_full_name_property(self, db_session, sample_provider_data):
        """Test the full_name property"""
        provider = Provider(**sample_provider_data)
        db_session.add(provider)
        db_session.commit()
        
        assert provider.full_name == "John Doe"

    def test_provider_full_address_property(self, db_session, sample_provider_data):
        """Test the full_address property"""
        provider = Provider(**sample_provider_data)
        db_session.add(provider)
        db_session.commit()
        
        expected_address = "123 Main St, Anytown, CA, 12345"
        assert provider.full_address == expected_address

    def test_provider_full_address_with_missing_fields(self, db_session):
        """Test full_address property with missing address fields"""
        provider = Provider(
            given_name="Jane",
            family_name="Smith",
            npi_number="0987654321"
        )
        db_session.add(provider)
        db_session.commit()
        
        assert provider.full_address == ""

    def test_add_flag(self, db_session, sample_provider_data):
        """Test adding validation flags"""
        provider = Provider(**sample_provider_data)
        db_session.add(provider)
        db_session.commit()
        
        provider.add_flag("NPI_NOT_FOUND", "NPI number not found in registry")
        provider.add_flag("ADDRESS_MISMATCH", "Address doesn't match NPI registry")
        
        assert len(provider.flags) == 2
        assert provider.flags[0]["code"] == "NPI_NOT_FOUND"
        assert provider.flags[0]["reason"] == "NPI number not found in registry"
        assert provider.flags[1]["code"] == "ADDRESS_MISMATCH"
        assert provider.flags[1]["reason"] == "Address doesn't match NPI registry"

    def test_update_field_confidence(self, db_session, sample_provider_data):
        """Test updating field confidence scores"""
        provider = Provider(**sample_provider_data)
        db_session.add(provider)
        db_session.commit()
        
        provider.update_field_confidence("npi_number", 0.95)
        provider.update_field_confidence("address", 0.78)
        provider.update_field_confidence("license", 0.82)
        
        assert "npi_number" in provider.field_confidence
        assert provider.field_confidence["npi_number"]["score"] == 0.95
        assert "address" in provider.field_confidence
        assert provider.field_confidence["address"]["score"] == 0.78
        assert "license" in provider.field_confidence
        assert provider.field_confidence["license"]["score"] == 0.82

    def test_calculate_overall_confidence(self, db_session, sample_provider_data):
        """Test calculating overall confidence from field scores"""
        provider = Provider(**sample_provider_data)
        db_session.add(provider)
        db_session.commit()
        
        provider.update_field_confidence("npi_number", 0.95)
        provider.update_field_confidence("address", 0.78)
        provider.update_field_confidence("license", 0.82)
        
        overall_confidence = provider.calculate_overall_confidence()
        expected = (0.95 + 0.78 + 0.82) / 3
        assert abs(overall_confidence - expected) < 0.001

    def test_calculate_overall_confidence_no_fields(self, db_session, sample_provider_data):
        """Test calculating overall confidence with no field scores"""
        provider = Provider(**sample_provider_data)
        db_session.add(provider)
        db_session.commit()
        
        overall_confidence = provider.calculate_overall_confidence()
        assert overall_confidence == 0.0

    def test_to_dict(self, db_session, sample_provider_data):
        """Test converting provider to dictionary"""
        provider = Provider(**sample_provider_data)
        db_session.add(provider)
        db_session.commit()
        
        provider_dict = provider.to_dict()
        
        assert isinstance(provider_dict, dict)
        assert provider_dict["given_name"] == "John"
        assert provider_dict["family_name"] == "Doe"
        assert provider_dict["npi_number"] == "1234567890"
        assert "provider_id" in provider_dict
        assert "created_at" in provider_dict
        assert "updated_at" in provider_dict

    def test_npi_uniqueness(self, db_session, sample_provider_data):
        """Test that NPI numbers must be unique"""
        provider1 = Provider(**sample_provider_data)
        db_session.add(provider1)
        db_session.commit()
        
        # Create second provider with same NPI
        sample_provider_data["given_name"] = "Jane"
        sample_provider_data["family_name"] = "Smith"
        provider2 = Provider(**sample_provider_data)
        db_session.add(provider2)
        
        with pytest.raises(Exception):  # Should raise integrity error
            db_session.commit()

    def test_validation_tracking(self, db_session, sample_provider_data):
        """Test validation tracking fields"""
        provider = Provider(**sample_provider_data)
        db_session.add(provider)
        db_session.commit()
        
        # Update validation tracking
        validation_time = datetime.utcnow()
        provider.last_validated_at = validation_time
        provider.validated_by = "validation_worker_001"
        provider.overall_confidence = 0.85
        
        db_session.commit()
        
        assert provider.last_validated_at == validation_time
        assert provider.validated_by == "validation_worker_001"
        assert provider.overall_confidence == 0.85

    def test_required_fields(self, db_session):
        """Test that required fields are enforced"""
        # Test missing given_name
        with pytest.raises(Exception):
            provider = Provider(
                family_name="Doe",
                npi_number="1234567890"
            )
            db_session.add(provider)
            db_session.commit()

    def test_json_fields(self, db_session, sample_provider_data):
        """Test JSON field handling"""
        provider = Provider(**sample_provider_data)
        db_session.add(provider)
        db_session.commit()
        
        # Test affiliations JSON
        assert isinstance(provider.affiliations, list)
        assert len(provider.affiliations) == 2
        assert provider.affiliations[0]["organization"] == "General Hospital"
        
        # Test services_offered JSON
        assert isinstance(provider.services_offered, dict)
        assert provider.services_offered["primary_care"] is True
        assert provider.services_offered["pediatrics"] is False

    def test_audit_fields(self, db_session, sample_provider_data):
        """Test audit timestamp fields"""
        provider = Provider(**sample_provider_data)
        db_session.add(provider)
        db_session.commit()
        
        assert provider.created_at is not None
        assert provider.updated_at is not None
        assert isinstance(provider.created_at, datetime)
        assert isinstance(provider.updated_at, datetime)

    def test_provider_repr(self, db_session, sample_provider_data):
        """Test provider string representation"""
        provider = Provider(**sample_provider_data)
        db_session.add(provider)
        db_session.commit()
        
        repr_str = repr(provider)
        assert "Provider" in repr_str
        assert "npi=1234567890" in repr_str
        assert "name=John Doe" in repr_str
