"""
Idempotency Management

This module provides idempotency key management for job retries and deduplication
in the validation system.
"""

import asyncio
import logging
import hashlib
import json
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import redis
import uuid

logger = logging.getLogger(__name__)


class IdempotencyStatus(Enum):
    """Idempotency status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass
class IdempotencyRecord:
    """Idempotency record structure"""
    key: str
    status: IdempotencyStatus
    job_id: str
    request_data: Dict[str, Any]
    response_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime = None
    updated_at: datetime = None
    expires_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
        if self.expires_at is None:
            self.expires_at = datetime.now() + timedelta(hours=24)


class IdempotencyManager:
    """
    Idempotency Manager
    
    Manages idempotency keys for job retries and deduplication to ensure
    that duplicate requests are handled gracefully.
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        """
        Initialize Idempotency Manager
        
        Args:
            redis_url: Redis connection URL
        """
        self.redis_conn = redis.from_url(redis_url)
        self.default_ttl = 86400  # 24 hours
        self.cleanup_interval = 3600  # 1 hour
    
    def generate_idempotency_key(self, 
                                request_data: Dict[str, Any],
                                prefix: str = "validation") -> str:
        """
        Generate idempotency key from request data
        
        Args:
            request_data: Request data dictionary
            prefix: Key prefix
            
        Returns:
            Generated idempotency key
        """
        try:
            # Sort keys for consistent hashing
            sorted_data = json.dumps(request_data, sort_keys=True, default=str)
            
            # Generate hash
            data_hash = hashlib.md5(sorted_data.encode()).hexdigest()
            
            # Create idempotency key
            idempotency_key = f"{prefix}_{data_hash}"
            
            logger.debug(f"Generated idempotency key: {idempotency_key}")
            return idempotency_key
        
        except Exception as e:
            logger.error(f"Failed to generate idempotency key: {str(e)}")
            # Fallback to UUID
            return f"{prefix}_{uuid.uuid4().hex}"
    
    def generate_custom_idempotency_key(self, 
                                      custom_data: str,
                                      prefix: str = "custom") -> str:
        """
        Generate idempotency key from custom data
        
        Args:
            custom_data: Custom data string
            prefix: Key prefix
            
        Returns:
            Generated idempotency key
        """
        try:
            # Generate hash from custom data
            data_hash = hashlib.md5(custom_data.encode()).hexdigest()
            
            # Create idempotency key
            idempotency_key = f"{prefix}_{data_hash}"
            
            logger.debug(f"Generated custom idempotency key: {idempotency_key}")
            return idempotency_key
        
        except Exception as e:
            logger.error(f"Failed to generate custom idempotency key: {str(e)}")
            # Fallback to UUID
            return f"{prefix}_{uuid.uuid4().hex}"
    
    async def check_idempotency(self, idempotency_key: str) -> Optional[IdempotencyRecord]:
        """
        Check if idempotency key exists and return record
        
        Args:
            idempotency_key: Idempotency key to check
            
        Returns:
            IdempotencyRecord if exists, None otherwise
        """
        try:
            key = f"idempotency:{idempotency_key}"
            data = self.redis_conn.get(key)
            
            if not data:
                return None
            
            # Deserialize record
            record_data = json.loads(data)
            record = IdempotencyRecord(**record_data)
            
            # Check if expired
            if record.expires_at and datetime.now() > record.expires_at:
                logger.info(f"Idempotency key {idempotency_key} has expired")
                await self.delete_idempotency_record(idempotency_key)
                return None
            
            logger.debug(f"Found idempotency record for key: {idempotency_key}")
            return record
        
        except Exception as e:
            logger.error(f"Failed to check idempotency for {idempotency_key}: {str(e)}")
            return None
    
    async def create_idempotency_record(self, 
                                      idempotency_key: str,
                                      job_id: str,
                                      request_data: Dict[str, Any],
                                      ttl: Optional[int] = None) -> IdempotencyRecord:
        """
        Create new idempotency record
        
        Args:
            idempotency_key: Idempotency key
            job_id: Associated job ID
            request_data: Request data
            ttl: Time to live in seconds
            
        Returns:
            Created IdempotencyRecord
        """
        try:
            # Check if key already exists
            existing_record = await self.check_idempotency(idempotency_key)
            if existing_record:
                logger.warning(f"Idempotency key {idempotency_key} already exists")
                return existing_record
            
            # Create new record
            expires_at = datetime.now() + timedelta(seconds=ttl or self.default_ttl)
            
            record = IdempotencyRecord(
                key=idempotency_key,
                status=IdempotencyStatus.PENDING,
                job_id=job_id,
                request_data=request_data,
                expires_at=expires_at
            )
            
            # Store in Redis
            key = f"idempotency:{idempotency_key}"
            record_data = asdict(record)
            record_data['created_at'] = record.created_at.isoformat()
            record_data['updated_at'] = record.updated_at.isoformat()
            record_data['expires_at'] = record.expires_at.isoformat()
            record_data['status'] = record.status.value
            
            self.redis_conn.setex(
                key,
                ttl or self.default_ttl,
                json.dumps(record_data)
            )
            
            logger.info(f"Created idempotency record for key: {idempotency_key}")
            return record
        
        except Exception as e:
            logger.error(f"Failed to create idempotency record for {idempotency_key}: {str(e)}")
            raise
    
    async def update_idempotency_record(self, 
                                      idempotency_key: str,
                                      status: IdempotencyStatus,
                                      response_data: Optional[Dict[str, Any]] = None,
                                      error_message: Optional[str] = None) -> bool:
        """
        Update idempotency record
        
        Args:
            idempotency_key: Idempotency key
            status: New status
            response_data: Response data (for completed requests)
            error_message: Error message (for failed requests)
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            key = f"idempotency:{idempotency_key}"
            data = self.redis_conn.get(key)
            
            if not data:
                logger.warning(f"Idempotency record not found for key: {idempotency_key}")
                return False
            
            # Deserialize and update record
            record_data = json.loads(data)
            record_data['status'] = status.value
            record_data['updated_at'] = datetime.now().isoformat()
            
            if response_data:
                record_data['response_data'] = response_data
            
            if error_message:
                record_data['error_message'] = error_message
            
            # Store updated record
            self.redis_conn.setex(key, self.default_ttl, json.dumps(record_data))
            
            logger.info(f"Updated idempotency record for key: {idempotency_key} to status: {status.value}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to update idempotency record for {idempotency_key}: {str(e)}")
            return False
    
    async def delete_idempotency_record(self, idempotency_key: str) -> bool:
        """
        Delete idempotency record
        
        Args:
            idempotency_key: Idempotency key
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            key = f"idempotency:{idempotency_key}"
            result = self.redis_conn.delete(key)
            
            if result:
                logger.info(f"Deleted idempotency record for key: {idempotency_key}")
                return True
            else:
                logger.warning(f"Idempotency record not found for key: {idempotency_key}")
                return False
        
        except Exception as e:
            logger.error(f"Failed to delete idempotency record for {idempotency_key}: {str(e)}")
            return False
    
    async def get_idempotency_status(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        """
        Get idempotency status information
        
        Args:
            idempotency_key: Idempotency key
            
        Returns:
            Status information dictionary
        """
        try:
            record = await self.check_idempotency(idempotency_key)
            
            if not record:
                return None
            
            return {
                "key": record.key,
                "status": record.status.value,
                "job_id": record.job_id,
                "created_at": record.created_at.isoformat(),
                "updated_at": record.updated_at.isoformat(),
                "expires_at": record.expires_at.isoformat(),
                "has_response": record.response_data is not None,
                "has_error": record.error_message is not None
            }
        
        except Exception as e:
            logger.error(f"Failed to get idempotency status for {idempotency_key}: {str(e)}")
            return None
    
    async def list_idempotency_records(self, 
                                     status_filter: Optional[IdempotencyStatus] = None,
                                     limit: int = 100) -> List[Dict[str, Any]]:
        """
        List idempotency records
        
        Args:
            status_filter: Filter by status
            limit: Maximum number of records to return
            
        Returns:
            List of idempotency record information
        """
        try:
            pattern = "idempotency:*"
            keys = self.redis_conn.keys(pattern)
            
            records = []
            for key in keys[:limit]:
                try:
                    data = self.redis_conn.get(key)
                    if data:
                        record_data = json.loads(data)
                        record = IdempotencyRecord(**record_data)
                        
                        # Apply status filter
                        if status_filter and record.status != status_filter:
                            continue
                        
                        records.append({
                            "key": record.key,
                            "status": record.status.value,
                            "job_id": record.job_id,
                            "created_at": record.created_at.isoformat(),
                            "updated_at": record.updated_at.isoformat(),
                            "expires_at": record.expires_at.isoformat()
                        })
                
                except Exception as e:
                    logger.error(f"Failed to process idempotency record {key}: {str(e)}")
                    continue
            
            # Sort by created_at descending
            records.sort(key=lambda x: x['created_at'], reverse=True)
            
            return records
        
        except Exception as e:
            logger.error(f"Failed to list idempotency records: {str(e)}")
            return []
    
    async def cleanup_expired_records(self) -> int:
        """
        Clean up expired idempotency records
        
        Returns:
            Number of records cleaned up
        """
        try:
            pattern = "idempotency:*"
            keys = self.redis_conn.keys(pattern)
            
            cleaned_count = 0
            current_time = datetime.now()
            
            for key in keys:
                try:
                    data = self.redis_conn.get(key)
                    if data:
                        record_data = json.loads(data)
                        expires_at = datetime.fromisoformat(record_data['expires_at'])
                        
                        if current_time > expires_at:
                            self.redis_conn.delete(key)
                            cleaned_count += 1
                
                except Exception as e:
                    logger.error(f"Failed to cleanup record {key}: {str(e)}")
                    continue
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} expired idempotency records")
            
            return cleaned_count
        
        except Exception as e:
            logger.error(f"Failed to cleanup expired idempotency records: {str(e)}")
            return 0
    
    async def get_idempotency_metrics(self) -> Dict[str, Any]:
        """
        Get idempotency metrics
        
        Returns:
            Metrics dictionary
        """
        try:
            pattern = "idempotency:*"
            keys = self.redis_conn.keys(pattern)
            
            total_records = len(keys)
            status_counts = {
                "pending": 0,
                "processing": 0,
                "completed": 0,
                "failed": 0,
                "expired": 0
            }
            
            current_time = datetime.now()
            
            for key in keys:
                try:
                    data = self.redis_conn.get(key)
                    if data:
                        record_data = json.loads(data)
                        status = record_data.get('status', 'pending')
                        
                        # Check if expired
                        expires_at = datetime.fromisoformat(record_data['expires_at'])
                        if current_time > expires_at:
                            status = 'expired'
                        
                        status_counts[status] += 1
                
                except Exception as e:
                    logger.error(f"Failed to process record {key} for metrics: {str(e)}")
                    continue
            
            return {
                "total_records": total_records,
                "status_counts": status_counts,
                "cleanup_interval": self.cleanup_interval,
                "default_ttl": self.default_ttl,
                "timestamp": current_time.isoformat()
            }
        
        except Exception as e:
            logger.error(f"Failed to get idempotency metrics: {str(e)}")
            return {"error": str(e)}
    
    async def handle_duplicate_request(self, 
                                     idempotency_key: str,
                                     request_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Handle duplicate request based on idempotency key
        
        Args:
            idempotency_key: Idempotency key
            request_data: Request data
            
        Returns:
            Response data if request was already processed, None otherwise
        """
        try:
            # Check if request already exists
            existing_record = await self.check_idempotency(idempotency_key)
            
            if not existing_record:
                # New request
                return None
            
            # Handle based on status
            if existing_record.status == IdempotencyStatus.COMPLETED:
                # Return cached response
                logger.info(f"Returning cached response for idempotency key: {idempotency_key}")
                return existing_record.response_data
            
            elif existing_record.status == IdempotencyStatus.FAILED:
                # Allow retry
                logger.info(f"Previous request failed, allowing retry for idempotency key: {idempotency_key}")
                return None
            
            elif existing_record.status in [IdempotencyStatus.PENDING, IdempotencyStatus.PROCESSING]:
                # Request is already being processed
                logger.info(f"Request already being processed for idempotency key: {idempotency_key}")
                return {
                    "job_id": existing_record.job_id,
                    "status": existing_record.status.value,
                    "message": "Request is already being processed"
                }
            
            else:
                # Unknown status
                logger.warning(f"Unknown status for idempotency key: {idempotency_key}")
                return None
        
        except Exception as e:
            logger.error(f"Failed to handle duplicate request for {idempotency_key}: {str(e)}")
            return None


# Global idempotency manager instance
idempotency_manager = IdempotencyManager()


# Example usage and testing functions
async def example_idempotency():
    """
    Example function demonstrating idempotency management
    """
    print("=" * 60)
    print("🔄 IDEMPOTENCY MANAGEMENT EXAMPLE")
    print("=" * 60)
    
    # Initialize idempotency manager
    manager = IdempotencyManager()
    
    # Sample request data
    request_data = {
        "provider_data": [
            {
                "provider_id": "12345",
                "given_name": "Dr. John Smith",
                "npi_number": "1234567890"
            }
        ],
        "validation_options": {
            "enable_npi_check": True,
            "enable_address_validation": True
        }
    }
    
    # Generate idempotency key
    idempotency_key = manager.generate_idempotency_key(request_data)
    print(f"\n📋 Generated Idempotency Key: {idempotency_key}")
    
    # Create idempotency record
    job_id = "job_12345"
    record = await manager.create_idempotency_record(
        idempotency_key=idempotency_key,
        job_id=job_id,
        request_data=request_data
    )
    
    print(f"   Created Record: {record.status.value}")
    print(f"   Job ID: {record.job_id}")
    print(f"   Expires At: {record.expires_at}")
    
    # Check idempotency
    existing_record = await manager.check_idempotency(idempotency_key)
    print(f"\n🔍 Checking Idempotency:")
    print(f"   Found: {existing_record is not None}")
    if existing_record:
        print(f"   Status: {existing_record.status.value}")
        print(f"   Job ID: {existing_record.job_id}")
    
    # Update record status
    await manager.update_idempotency_record(
        idempotency_key=idempotency_key,
        status=IdempotencyStatus.PROCESSING
    )
    
    print(f"\n📝 Updated Status to PROCESSING")
    
    # Complete the request
    response_data = {
        "job_id": job_id,
        "status": "completed",
        "provider_count": 1,
        "overall_confidence": 0.95
    }
    
    await manager.update_idempotency_record(
        idempotency_key=idempotency_key,
        status=IdempotencyStatus.COMPLETED,
        response_data=response_data
    )
    
    print(f"   Updated Status to COMPLETED")
    
    # Handle duplicate request
    duplicate_response = await manager.handle_duplicate_request(
        idempotency_key=idempotency_key,
        request_data=request_data
    )
    
    print(f"\n🔄 Handling Duplicate Request:")
    print(f"   Response: {duplicate_response}")
    
    # Get metrics
    metrics = await manager.get_idempotency_metrics()
    print(f"\n📊 Idempotency Metrics:")
    print(f"   Total Records: {metrics['total_records']}")
    print(f"   Status Counts: {metrics['status_counts']}")


if __name__ == "__main__":
    # Run examples
    print("Idempotency Management - Examples")
    print("To run examples:")
    print("1. Install dependencies: pip install redis")
    print("2. Start Redis server: redis-server")
    print("3. Run: python -c 'from utils.idempotency import example_idempotency; asyncio.run(example_idempotency())'")
