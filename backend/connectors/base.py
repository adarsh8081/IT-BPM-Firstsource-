"""
Base connector class with common functionality
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
import httpx
import time
from datetime import datetime, timedelta

from ..config import settings

logger = logging.getLogger(__name__)

class BaseConnector(ABC):
    """Base class for external API connectors"""
    
    def __init__(self, rate_limit: int = 100, timeout: int = 30):
        self.rate_limit = rate_limit
        self.timeout = timeout
        self.request_times = []
        self.session = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = httpx.AsyncClient(timeout=self.timeout)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.aclose()
    
    async def _rate_limit_check(self):
        """Check and enforce rate limiting"""
        now = time.time()
        
        # Remove requests older than 1 hour
        self.request_times = [t for t in self.request_times if now - t < 3600]
        
        # Check if we're at the rate limit
        if len(self.request_times) >= self.rate_limit:
            # Calculate sleep time until the oldest request expires
            oldest_request = min(self.request_times)
            sleep_time = 3600 - (now - oldest_request) + 1
            
            logger.warning(f"Rate limit reached, sleeping for {sleep_time:.2f} seconds")
            await asyncio.sleep(sleep_time)
        
        # Record this request
        self.request_times.append(now)
    
    async def _make_request(
        self, 
        method: str, 
        url: str, 
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """Make HTTP request with rate limiting and retry logic"""
        
        # Rate limiting
        await self._rate_limit_check()
        
        # Default headers
        if headers is None:
            headers = {
                'User-Agent': 'ProviderValidation/1.0',
                'Accept': 'application/json'
            }
        
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                logger.debug(f"Making {method} request to {url} (attempt {attempt + 1})")
                
                response = await self.session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=json_data
                )
                
                response.raise_for_status()
                
                # Try to parse JSON
                try:
                    return response.json()
                except Exception:
                    return {"raw_response": response.text}
                    
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:  # Rate limited
                    retry_after = int(e.response.headers.get('Retry-After', 60))
                    logger.warning(f"Rate limited, retrying after {retry_after} seconds")
                    await asyncio.sleep(retry_after)
                    continue
                elif e.response.status_code >= 500:  # Server error
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt  # Exponential backoff
                        logger.warning(f"Server error, retrying in {wait_time} seconds")
                        await asyncio.sleep(wait_time)
                        continue
                
                last_exception = e
                break
                
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Request failed, retrying in {wait_time} seconds: {e}")
                    await asyncio.sleep(wait_time)
                    continue
                
                last_exception = e
                break
        
        # If we get here, all retries failed
        error_msg = f"Request failed after {max_retries} attempts"
        if last_exception:
            error_msg += f": {last_exception}"
        
        logger.error(error_msg)
        raise Exception(error_msg)
    
    def _sanitize_log_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive data from logs"""
        sanitized = data.copy()
        
        # Remove sensitive fields
        sensitive_fields = ['api_key', 'password', 'token', 'secret']
        for field in sensitive_fields:
            if field in sanitized:
                sanitized[field] = '***REDACTED***'
        
        return sanitized
    
    @abstractmethod
    async def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Abstract method for validation logic"""
        pass
