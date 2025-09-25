"""
Security Middleware for FastAPI

This module provides comprehensive security middleware including rate limiting,
input sanitization, content moderation, and security headers.
"""

import time
import re
import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Callable, Union
from enum import Enum
from dataclasses import dataclass
import redis
import jwt
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import uvicorn
from urllib.parse import urlparse
import logging

class RateLimitType(Enum):
    """Rate limiting types"""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"

class SecurityEventType(Enum):
    """Security event types"""
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_INPUT = "suspicious_input"
    MALICIOUS_CONTENT = "malicious_content"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    CSRF_VIOLATION = "csrf_violation"
    XSS_ATTEMPT = "xss_attempt"
    SQL_INJECTION_ATTEMPT = "sql_injection_attempt"
    PATH_TRAVERSAL_ATTEMPT = "path_traversal_attempt"

@dataclass
class SecurityEvent:
    """Security event data"""
    event_type: SecurityEventType
    timestamp: datetime
    ip_address: str
    user_id: Optional[str]
    endpoint: str
    method: str
    user_agent: Optional[str]
    request_data: Optional[Dict[str, Any]]
    severity: str
    details: Optional[str] = None

@dataclass
class RateLimitConfig:
    """Rate limiting configuration"""
    requests_per_minute: int
    requests_per_hour: int
    requests_per_day: int
    burst_limit: int = 10
    window_size: int = 60  # seconds

class InputSanitizer:
    """Input sanitization and validation"""
    
    def __init__(self):
        # Malicious patterns
        self.xss_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'vbscript:',
            r'onload\s*=',
            r'onerror\s*=',
            r'onclick\s*=',
            r'onmouseover\s*=',
            r'<iframe[^>]*>',
            r'<object[^>]*>',
            r'<embed[^>]*>',
            r'<link[^>]*>',
            r'<meta[^>]*>',
            r'<style[^>]*>',
            r'expression\s*\(',
            r'url\s*\(',
            r'@import',
            r'<.*?on\w+\s*=',
            r'<.*?style\s*=',
            r'<.*?href\s*=',
            r'<.*?src\s*='
        ]
        
        self.sql_injection_patterns = [
            r'union\s+select',
            r'drop\s+table',
            r'delete\s+from',
            r'insert\s+into',
            r'update\s+set',
            r'exec\s*\(',
            r'execute\s*\(',
            r'sp_',
            r'xp_',
            r'--',
            r'/\*.*?\*/',
            r';.*?--',
            r'waitfor\s+delay',
            r'benchmark\s*\(',
            r'sleep\s*\(',
            r'char\s*\(',
            r'ascii\s*\(',
            r'ord\s*\(',
            r'length\s*\(',
            r'substring\s*\(',
            r'mid\s*\(',
            r'left\s*\(',
            r'right\s*\(',
            r'concat\s*\(',
            r'group_concat\s*\(',
            r'information_schema',
            r'sys\.',
            r'master\.',
            r'@@version',
            r'@@hostname',
            r'@@datadir',
            r'@@basedir'
        ]
        
        self.path_traversal_patterns = [
            r'\.\./',
            r'\.\.\\',
            r'\.\.%2f',
            r'\.\.%5c',
            r'%2e%2e%2f',
            r'%2e%2e%5c',
            r'\.\.%252f',
            r'\.\.%255c',
            r'\.\.%c0%af',
            r'\.\.%c1%9c',
            r'\.\.%c1%pc',
            r'\.\.%e0%80%af',
            r'\.\.%f0%80%80%af'
        ]
        
        # Compile patterns for performance
        self.xss_regex = [re.compile(pattern, re.IGNORECASE | re.DOTALL) for pattern in self.xss_patterns]
        self.sql_injection_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.sql_injection_patterns]
        self.path_traversal_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.path_traversal_patterns]
    
    def sanitize_input(self, value: str, max_length: int = 1000) -> str:
        """
        Sanitize input string
        
        Args:
            value: Input string to sanitize
            max_length: Maximum allowed length
            
        Returns:
            Sanitized string
        """
        if not isinstance(value, str):
            return str(value)
        
        # Trim whitespace
        value = value.strip()
        
        # Limit length
        if len(value) > max_length:
            value = value[:max_length]
        
        # Remove null bytes
        value = value.replace('\x00', '')
        
        # Normalize unicode
        value = value.encode('utf-8', errors='ignore').decode('utf-8')
        
        return value
    
    def detect_malicious_content(self, value: str) -> List[SecurityEventType]:
        """
        Detect malicious content in input
        
        Args:
            value: Input string to check
            
        Returns:
            List of detected security event types
        """
        if not isinstance(value, str):
            return []
        
        events = []
        
        # Check for XSS
        if any(regex.search(value) for regex in self.xss_regex):
            events.append(SecurityEventType.XSS_ATTEMPT)
        
        # Check for SQL injection
        if any(regex.search(value) for regex in self.sql_injection_regex):
            events.append(SecurityEventType.SQL_INJECTION_ATTEMPT)
        
        # Check for path traversal
        if any(regex.search(value) for regex in self.path_traversal_regex):
            events.append(SecurityEventType.PATH_TRAVERSAL_ATTEMPT)
        
        return events
    
    def sanitize_dict(self, data: Dict[str, Any], max_depth: int = 10) -> Dict[str, Any]:
        """
        Recursively sanitize dictionary data
        
        Args:
            data: Dictionary to sanitize
            max_depth: Maximum recursion depth
            
        Returns:
            Sanitized dictionary
        """
        if max_depth <= 0:
            return {}
        
        sanitized = {}
        for key, value in data.items():
            # Sanitize key
            sanitized_key = self.sanitize_input(str(key), max_length=100)
            
            # Sanitize value
            if isinstance(value, str):
                sanitized_value = self.sanitize_input(value)
            elif isinstance(value, dict):
                sanitized_value = self.sanitize_dict(value, max_depth - 1)
            elif isinstance(value, list):
                sanitized_value = [
                    self.sanitize_input(str(item)) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                sanitized_value = value
            
            sanitized[sanitized_key] = sanitized_value
        
        return sanitized

class RateLimiter:
    """Rate limiting implementation using Redis"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.default_config = RateLimitConfig(
            requests_per_minute=60,
            requests_per_hour=1000,
            requests_per_day=10000,
            burst_limit=10
        )
    
    def check_rate_limit(self, 
                        identifier: str, 
                        config: Optional[RateLimitConfig] = None) -> Dict[str, Any]:
        """
        Check rate limit for identifier
        
        Args:
            identifier: Unique identifier (IP, user ID, etc.)
            config: Rate limit configuration
            
        Returns:
            Rate limit status
        """
        config = config or self.default_config
        
        now = int(time.time())
        minute_window = now // 60
        hour_window = now // 3600
        day_window = now // 86400
        
        # Check minute limit
        minute_key = f"rate_limit:{identifier}:minute:{minute_window}"
        minute_count = self.redis.incr(minute_key)
        if minute_count == 1:
            self.redis.expire(minute_key, 60)
        
        # Check hour limit
        hour_key = f"rate_limit:{identifier}:hour:{hour_window}"
        hour_count = self.redis.incr(hour_key)
        if hour_count == 1:
            self.redis.expire(hour_key, 3600)
        
        # Check day limit
        day_key = f"rate_limit:{identifier}:day:{day_window}"
        day_count = self.redis.incr(day_key)
        if day_count == 1:
            self.redis.expire(day_key, 86400)
        
        # Check burst limit (sliding window)
        burst_key = f"rate_limit:{identifier}:burst"
        burst_count = self.redis.incr(burst_key)
        if burst_count == 1:
            self.redis.expire(burst_key, 10)  # 10 second window
        
        # Determine if rate limit exceeded
        exceeded = (
            minute_count > config.requests_per_minute or
            hour_count > config.requests_per_hour or
            day_count > config.requests_per_day or
            burst_count > config.burst_limit
        )
        
        return {
            'exceeded': exceeded,
            'minute_count': minute_count,
            'hour_count': hour_count,
            'day_count': day_count,
            'burst_count': burst_count,
            'minute_limit': config.requests_per_minute,
            'hour_limit': config.requests_per_hour,
            'day_limit': config.requests_per_day,
            'burst_limit': config.burst_limit
        }

class SecurityMiddleware(BaseHTTPMiddleware):
    """Comprehensive security middleware"""
    
    def __init__(self, 
                 app: ASGIApp,
                 redis_client: Optional[redis.Redis] = None,
                 rate_limit_config: Optional[Dict[str, RateLimitConfig]] = None,
                 security_callback: Optional[Callable[[SecurityEvent], None]] = None,
                 enable_cors: bool = True,
                 enable_csrf: bool = True,
                 enable_security_headers: bool = True):
        """
        Initialize security middleware
        
        Args:
            app: FastAPI application
            redis_client: Redis client for rate limiting
            rate_limit_config: Rate limit configuration per endpoint
            security_callback: Callback for security events
            enable_cors: Enable CORS protection
            enable_csrf: Enable CSRF protection
            enable_security_headers: Enable security headers
        """
        super().__init__(app)
        self.redis_client = redis_client
        self.rate_limit_config = rate_limit_config or {}
        self.security_callback = security_callback
        self.enable_cors = enable_cors
        self.enable_csrf = enable_csrf
        self.enable_security_headers = enable_security_headers
        
        # Initialize components
        self.input_sanitizer = InputSanitizer()
        self.rate_limiter = RateLimiter(redis_client) if redis_client else None
        
        # Security headers
        self.security_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Permissions-Policy': 'geolocation=(), microphone=(), camera=()',
            'Cross-Origin-Embedder-Policy': 'require-corp',
            'Cross-Origin-Opener-Policy': 'same-origin',
            'Cross-Origin-Resource-Policy': 'same-origin'
        }
        
        # Content Security Policy
        self.csp_header = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://api.npiregistry.cms.hhs.gov; "
            "font-src 'self' data:; "
            "object-src 'none'; "
            "media-src 'self'; "
            "frame-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        
        # HSTS header
        self.hsts_header = "max-age=31536000; includeSubDomains; preload"
    
    async def dispatch(self, request: Request, call_next):
        """Process request through security middleware"""
        start_time = time.time()
        
        try:
            # Get client information
            client_ip = self._get_client_ip(request)
            user_agent = request.headers.get('user-agent', '')
            
            # Rate limiting
            if self.rate_limiter:
                rate_limit_result = await self._check_rate_limit(request, client_ip)
                if rate_limit_result['exceeded']:
                    await self._log_security_event(
                        SecurityEventType.RATE_LIMIT_EXCEEDED,
                        request, client_ip, None, severity="medium"
                    )
                    return JSONResponse(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        content={
                            "error": "Rate limit exceeded",
                            "retry_after": 60,
                            "details": rate_limit_result
                        },
                        headers={'Retry-After': '60'}
                    )
            
            # Input sanitization
            sanitization_result = await self._sanitize_request(request)
            if sanitization_result['malicious_detected']:
                await self._log_security_event(
                    SecurityEventType.SUSPICIOUS_INPUT,
                    request, client_ip, None, severity="high",
                    details=f"Malicious content detected: {sanitization_result['events']}"
                )
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "error": "Invalid input detected",
                        "details": "Request contains potentially malicious content"
                    }
                )
            
            # CSRF protection
            if self.enable_csrf and request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
                csrf_result = await self._check_csrf(request)
                if not csrf_result['valid']:
                    await self._log_security_event(
                        SecurityEventType.CSRF_VIOLATION,
                        request, client_ip, None, severity="high"
                    )
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={
                            "error": "CSRF token validation failed",
                            "details": csrf_result['reason']
                        }
                    )
            
            # Process request
            response = await call_next(request)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Add security headers
            if self.enable_security_headers:
                await self._add_security_headers(response)
            
            # Log slow requests
            if processing_time > 5.0:  # 5 seconds
                await self._log_security_event(
                    SecurityEventType.SUSPICIOUS_INPUT,
                    request, client_ip, None, severity="low",
                    details=f"Slow request: {processing_time:.2f}s"
                )
            
            return response
            
        except Exception as e:
            # Log security exception
            await self._log_security_event(
                SecurityEventType.UNAUTHORIZED_ACCESS,
                request, client_ip, None, severity="high",
                details=f"Security middleware exception: {str(e)}"
            )
            
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Internal server error",
                    "details": "Request processing failed"
                }
            )
    
    async def _check_rate_limit(self, request: Request, client_ip: str) -> Dict[str, Any]:
        """Check rate limit for request"""
        if not self.rate_limiter:
            return {'exceeded': False}
        
        # Get endpoint-specific config
        endpoint = f"{request.method}:{request.url.path}"
        config = self.rate_limit_config.get(endpoint)
        
        # Use IP as identifier (could be enhanced with user ID if available)
        identifier = client_ip
        
        return self.rate_limiter.check_rate_limit(identifier, config)
    
    async def _sanitize_request(self, request: Request) -> Dict[str, Any]:
        """Sanitize request data"""
        malicious_events = []
        
        try:
            # Check URL parameters
            for param_name, param_value in request.query_params.items():
                if isinstance(param_value, str):
                    events = self.input_sanitizer.detect_malicious_content(param_value)
                    malicious_events.extend(events)
            
            # Check headers
            for header_name, header_value in request.headers.items():
                if isinstance(header_value, str):
                    events = self.input_sanitizer.detect_malicious_content(header_value)
                    malicious_events.extend(events)
            
            # Check path
            events = self.input_sanitizer.detect_malicious_content(request.url.path)
            malicious_events.extend(events)
            
            # Check request body for POST/PUT/PATCH
            if request.method in ['POST', 'PUT', 'PATCH']:
                try:
                    body = await request.body()
                    if body:
                        body_str = body.decode('utf-8', errors='ignore')
                        events = self.input_sanitizer.detect_malicious_content(body_str)
                        malicious_events.extend(events)
                except Exception:
                    pass  # Ignore body parsing errors
            
            return {
                'malicious_detected': len(malicious_events) > 0,
                'events': malicious_events
            }
            
        except Exception:
            return {
                'malicious_detected': False,
                'events': []
            }
    
    async def _check_csrf(self, request: Request) -> Dict[str, Any]:
        """Check CSRF token"""
        try:
            # Get CSRF token from header or form data
            csrf_token = request.headers.get('X-CSRF-Token') or request.headers.get('X-CSRFToken')
            
            if not csrf_token:
                return {'valid': False, 'reason': 'CSRF token missing'}
            
            # Verify CSRF token (implement based on your CSRF strategy)
            # This is a simplified implementation
            if len(csrf_token) < 32:
                return {'valid': False, 'reason': 'Invalid CSRF token format'}
            
            return {'valid': True, 'reason': 'CSRF token valid'}
            
        except Exception:
            return {'valid': False, 'reason': 'CSRF validation error'}
    
    async def _add_security_headers(self, response: Response):
        """Add security headers to response"""
        # Add basic security headers
        for header_name, header_value in self.security_headers.items():
            response.headers[header_name] = header_value
        
        # Add CSP header
        response.headers['Content-Security-Policy'] = self.csp_header
        
        # Add HSTS header
        response.headers['Strict-Transport-Security'] = self.hsts_header
        
        # Add CORS headers if enabled
        if self.enable_cors:
            response.headers['Access-Control-Allow-Origin'] = 'https://yourdomain.com'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-CSRF-Token'
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Access-Control-Max-Age'] = '86400'
    
    async def _log_security_event(self,
                                 event_type: SecurityEventType,
                                 request: Request,
                                 ip_address: str,
                                 user_id: Optional[str],
                                 severity: str,
                                 details: Optional[str] = None):
        """Log security event"""
        if not self.security_callback:
            return
        
        try:
            # Extract request data (sanitized)
            request_data = {
                'method': request.method,
                'url': str(request.url),
                'headers': dict(request.headers),
                'query_params': dict(request.query_params)
            }
            
            event = SecurityEvent(
                event_type=event_type,
                timestamp=datetime.now(timezone.utc),
                ip_address=ip_address,
                user_id=user_id,
                endpoint=request.url.path,
                method=request.method,
                user_agent=request.headers.get('user-agent'),
                request_data=request_data,
                severity=severity,
                details=details
            )
            
            self.security_callback(event)
            
        except Exception:
            pass  # Don't let logging errors break the request
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        # Check for forwarded headers
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        # Fallback to direct connection IP
        if hasattr(request.client, 'host'):
            return request.client.host
        
        return '127.0.0.1'

def create_security_middleware(app: ASGIApp,
                              redis_client: Optional[redis.Redis] = None,
                              rate_limit_config: Optional[Dict[str, RateLimitConfig]] = None,
                              security_callback: Optional[Callable[[SecurityEvent], None]] = None) -> SecurityMiddleware:
    """Create security middleware with configuration"""
    
    # Default rate limit configurations
    default_rate_limits = {
        'POST:/api/auth/login': RateLimitConfig(5, 50, 500, 3),
        'POST:/api/validate/batch': RateLimitConfig(10, 100, 1000, 5),
        'GET:/api/providers': RateLimitConfig(60, 1000, 10000, 20),
        'POST:/api/providers': RateLimitConfig(30, 500, 5000, 10),
        'PUT:/api/providers': RateLimitConfig(30, 500, 5000, 10),
        'DELETE:/api/providers': RateLimitConfig(10, 100, 1000, 3),
        'POST:/api/export': RateLimitConfig(5, 50, 500, 2),
        'GET:/api/audit': RateLimitConfig(60, 1000, 10000, 20),
        'POST:/api/audit': RateLimitConfig(10, 100, 1000, 5),
    }
    
    # Merge with provided configuration
    if rate_limit_config:
        default_rate_limits.update(rate_limit_config)
    
    return SecurityMiddleware(
        app=app,
        redis_client=redis_client,
        rate_limit_config=default_rate_limits,
        security_callback=security_callback
    )
