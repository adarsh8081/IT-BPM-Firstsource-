"""
Logging middleware for request/response logging
"""

import time
import logging
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import json

logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())
        
        # Start time
        start_time = time.time()
        
        # Log request
        await self._log_request(request, request_id)
        
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log response
        await self._log_response(response, request_id, process_time)
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response
    
    async def _log_request(self, request: Request, request_id: str):
        """Log incoming request"""
        try:
            # Get client IP
            client_ip = request.client.host if request.client else "unknown"
            
            # Get user agent
            user_agent = request.headers.get("user-agent", "unknown")
            
            # Get request body (for non-GET requests)
            body = None
            if request.method in ["POST", "PUT", "PATCH"]:
                try:
                    body_bytes = await request.body()
                    if body_bytes:
                        # Try to parse as JSON
                        try:
                            body = json.loads(body_bytes.decode())
                        except json.JSONDecodeError:
                            body = body_bytes.decode()[:500]  # Limit size
                except Exception:
                    body = None
            
            # Log request
            log_data = {
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "headers": self._sanitize_headers(dict(request.headers)),
                "client_ip": client_ip,
                "user_agent": user_agent,
                "body": body
            }
            
            logger.info(f"Request {request_id}: {request.method} {request.url.path}", 
                       extra={"request_data": log_data})
            
        except Exception as e:
            logger.error(f"Failed to log request {request_id}: {e}")
    
    async def _log_response(self, response: Response, request_id: str, process_time: float):
        """Log outgoing response"""
        try:
            # Get response body
            response_body = None
            if hasattr(response, 'body') and response.body:
                try:
                    # Try to parse as JSON
                    body_text = response.body.decode()
                    response_body = json.loads(body_text)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    response_body = str(response.body)[:500]  # Limit size
            
            # Log response
            log_data = {
                "request_id": request_id,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "process_time": round(process_time, 4),
                "body": response_body
            }
            
            # Use appropriate log level based on status code
            if response.status_code >= 500:
                logger.error(f"Response {request_id}: {response.status_code} ({process_time:.4f}s)",
                           extra={"response_data": log_data})
            elif response.status_code >= 400:
                logger.warning(f"Response {request_id}: {response.status_code} ({process_time:.4f}s)",
                             extra={"response_data": log_data})
            else:
                logger.info(f"Response {request_id}: {response.status_code} ({process_time:.4f}s)",
                          extra={"response_data": log_data})
            
        except Exception as e:
            logger.error(f"Failed to log response {request_id}: {e}")
    
    def _sanitize_headers(self, headers: dict) -> dict:
        """Remove sensitive headers from logs"""
        sensitive_headers = [
            'authorization', 'cookie', 'x-api-key', 'x-auth-token',
            'x-csrf-token', 'x-forwarded-for', 'x-real-ip'
        ]
        
        sanitized = {}
        for key, value in headers.items():
            if key.lower() in sensitive_headers:
                sanitized[key] = '***REDACTED***'
            else:
                sanitized[key] = value
        
        return sanitized
