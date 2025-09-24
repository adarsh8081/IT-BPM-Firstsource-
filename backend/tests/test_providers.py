"""
Tests for provider endpoints
"""

import pytest
from fastapi import status
from uuid import uuid4

class TestProviderEndpoints:
    """Test provider API endpoints"""
    
    def test_create_provider(self, client, sample_provider_data):
        """Test creating a new provider"""
        response = client.post("/api/providers/", json=sample_provider_data)
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["npi"] == sample_provider_data["npi"]
        assert data["first_name"] == sample_provider_data["first_name"]
        assert data["last_name"] == sample_provider_data["last_name"]
        assert data["status"] == "pending"
        assert "id" in data
    
    def test_create_provider_invalid_npi(self, client, sample_provider_data):
        """Test creating provider with invalid NPI"""
        sample_provider_data["npi"] = "invalid"
        response = client.post("/api/providers/", json=sample_provider_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_get_provider(self, client, sample_provider_data):
        """Test getting a provider by ID"""
        # Create provider first
        create_response = client.post("/api/providers/", json=sample_provider_data)
        assert create_response.status_code == status.HTTP_200_OK
        provider_id = create_response.json()["id"]
        
        # Get provider
        response = client.get(f"/api/providers/{provider_id}")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["id"] == provider_id
        assert data["npi"] == sample_provider_data["npi"]
    
    def test_get_provider_not_found(self, client):
        """Test getting non-existent provider"""
        fake_id = str(uuid4())
        response = client.get(f"/api/providers/{fake_id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_get_provider_by_npi(self, client, sample_provider_data):
        """Test getting provider by NPI"""
        # Create provider first
        create_response = client.post("/api/providers/", json=sample_provider_data)
        assert create_response.status_code == status.HTTP_200_OK
        
        # Get provider by NPI
        response = client.get(f"/api/providers/npi/{sample_provider_data['npi']}")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["npi"] == sample_provider_data["npi"]
    
    def test_list_providers(self, client, sample_provider_data):
        """Test listing providers"""
        # Create a few providers
        for i in range(3):
            provider_data = sample_provider_data.copy()
            provider_data["npi"] = f"123456789{i}"
            provider_data["first_name"] = f"Test{i}"
            client.post("/api/providers/", json=provider_data)
        
        # List providers
        response = client.get("/api/providers/")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "providers" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert "pages" in data
        assert len(data["providers"]) >= 3
    
    def test_list_providers_with_search(self, client, sample_provider_data):
        """Test listing providers with search"""
        # Create provider
        create_response = client.post("/api/providers/", json=sample_provider_data)
        assert create_response.status_code == status.HTTP_200_OK
        
        # Search providers
        response = client.get(f"/api/providers/?search={sample_provider_data['first_name']}")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert len(data["providers"]) >= 1
        assert any(p["first_name"] == sample_provider_data["first_name"] for p in data["providers"])
    
    def test_list_providers_with_status_filter(self, client, sample_provider_data):
        """Test listing providers with status filter"""
        # Create provider
        create_response = client.post("/api/providers/", json=sample_provider_data)
        assert create_response.status_code == status.HTTP_200_OK
        
        # Filter by status
        response = client.get("/api/providers/?status=pending")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert all(p["status"] == "pending" for p in data["providers"])
    
    def test_update_provider(self, client, sample_provider_data):
        """Test updating a provider"""
        # Create provider first
        create_response = client.post("/api/providers/", json=sample_provider_data)
        assert create_response.status_code == status.HTTP_200_OK
        provider_id = create_response.json()["id"]
        
        # Update provider
        update_data = {"first_name": "Updated Name", "specialty": "Cardiology"}
        response = client.put(f"/api/providers/{provider_id}", json=update_data)
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["first_name"] == "Updated Name"
        assert data["specialty"] == "Cardiology"
        assert data["last_name"] == sample_provider_data["last_name"]  # Unchanged
    
    def test_delete_provider(self, client, sample_provider_data):
        """Test deleting a provider"""
        # Create provider first
        create_response = client.post("/api/providers/", json=sample_provider_data)
        assert create_response.status_code == status.HTTP_200_OK
        provider_id = create_response.json()["id"]
        
        # Delete provider
        response = client.delete(f"/api/providers/{provider_id}")
        assert response.status_code == status.HTTP_200_OK
        
        # Verify provider is deleted
        get_response = client.get(f"/api/providers/{provider_id}")
        assert get_response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_create_bulk_providers(self, client, sample_provider_data):
        """Test creating multiple providers in bulk"""
        # Prepare bulk data
        bulk_data = []
        for i in range(5):
            provider_data = sample_provider_data.copy()
            provider_data["npi"] = f"123456789{i}"
            provider_data["first_name"] = f"Bulk{i}"
            bulk_data.append(provider_data)
        
        # Create bulk providers
        response = client.post("/api/providers/bulk", json=bulk_data)
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["success"] is True
        assert "Created" in data["message"]
    
    def test_export_providers_csv(self, client, sample_provider_data):
        """Test exporting providers to CSV"""
        # Create provider first
        create_response = client.post("/api/providers/", json=sample_provider_data)
        assert create_response.status_code == status.HTTP_200_OK
        
        # Export CSV
        response = client.get("/api/providers/export/csv")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "csv_data" in data
        assert isinstance(data["csv_data"], str)
