"""
Tests for validation endpoints
"""

import pytest
from fastapi import status
from uuid import uuid4

class TestValidationEndpoints:
    """Test validation API endpoints"""
    
    def test_create_validation_job(self, client, sample_validation_job_data):
        """Test creating a validation job"""
        response = client.post("/api/validation/jobs", json=sample_validation_job_data)
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["provider_id"] == sample_validation_job_data["provider_id"]
        assert data["priority"] == sample_validation_job_data["priority"]
        assert data["status"] == "pending"
        assert "id" in data
    
    def test_get_validation_job(self, client, sample_validation_job_data):
        """Test getting a validation job"""
        # Create job first
        create_response = client.post("/api/validation/jobs", json=sample_validation_job_data)
        assert create_response.status_code == status.HTTP_200_OK
        job_id = create_response.json()["id"]
        
        # Get job
        response = client.get(f"/api/validation/jobs/{job_id}")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["id"] == job_id
        assert data["provider_id"] == sample_validation_job_data["provider_id"]
    
    def test_get_validation_job_not_found(self, client):
        """Test getting non-existent validation job"""
        fake_id = str(uuid4())
        response = client.get(f"/api/validation/jobs/{fake_id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_list_validation_jobs(self, client, sample_validation_job_data):
        """Test listing validation jobs"""
        # Create a few jobs
        for i in range(3):
            job_data = sample_validation_job_data.copy()
            job_data["provider_id"] = str(uuid4())
            client.post("/api/validation/jobs", json=job_data)
        
        # List jobs
        response = client.get("/api/validation/jobs")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "jobs" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert "pages" in data
        assert len(data["jobs"]) >= 3
    
    def test_list_validation_jobs_with_status_filter(self, client, sample_validation_job_data):
        """Test listing validation jobs with status filter"""
        # Create job
        create_response = client.post("/api/validation/jobs", json=sample_validation_job_data)
        assert create_response.status_code == status.HTTP_200_OK
        
        # Filter by status
        response = client.get("/api/validation/jobs?status=pending")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert all(j["status"] == "pending" for j in data["jobs"])
    
    def test_cancel_validation_job(self, client, sample_validation_job_data):
        """Test cancelling a validation job"""
        # Create job first
        create_response = client.post("/api/validation/jobs", json=sample_validation_job_data)
        assert create_response.status_code == status.HTTP_200_OK
        job_id = create_response.json()["id"]
        
        # Cancel job
        response = client.post(f"/api/validation/jobs/{job_id}/cancel")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["success"] is True
        assert "cancelled" in data["message"]
    
    def test_retry_validation_job(self, client, sample_validation_job_data):
        """Test retrying a validation job"""
        # Create job first
        create_response = client.post("/api/validation/jobs", json=sample_validation_job_data)
        assert create_response.status_code == status.HTTP_200_OK
        job_id = create_response.json()["id"]
        
        # Retry job
        response = client.post(f"/api/validation/jobs/{job_id}/retry")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["success"] is True
        assert "restarted" in data["message"]
    
    def test_get_validation_results(self, client, sample_validation_job_data):
        """Test getting validation results"""
        provider_id = sample_validation_job_data["provider_id"]
        
        response = client.get(f"/api/validation/results/{provider_id}")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_job_validation_result(self, client, sample_validation_job_data):
        """Test getting validation result for a specific job"""
        # Create job first
        create_response = client.post("/api/validation/jobs", json=sample_validation_job_data)
        assert create_response.status_code == status.HTTP_200_OK
        job_id = create_response.json()["id"]
        
        # Get result (may not exist yet)
        response = client.get(f"/api/validation/results/job/{job_id}")
        # This might return 404 if no result exists yet
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
    
    def test_create_bulk_validation_jobs(self, client):
        """Test creating validation jobs for multiple providers"""
        provider_ids = [str(uuid4()) for _ in range(3)]
        
        response = client.post("/api/validation/bulk", json=provider_ids)
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["success"] is True
        assert "Created" in data["message"]
    
    def test_get_queue_status(self, client):
        """Test getting queue status"""
        response = client.get("/api/validation/queue/status")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert isinstance(data, dict)
