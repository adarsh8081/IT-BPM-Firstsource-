"""
JWT Authentication Handler with RBAC Support

This module provides JWT token generation, validation, and role-based access control
for the Provider Data Validation application.
"""

import jwt
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Union
from enum import Enum
from dataclasses import dataclass
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
import redis
import json

class UserRole(Enum):
    """User roles with hierarchical permissions"""
    ADMIN = "admin"           # Full system access
    REVIEWER = "reviewer"     # Provider review and validation
    AUDITOR = "auditor"       # Read-only audit access
    OPERATOR = "operator"     # Basic provider management
    VIEWER = "viewer"         # Read-only access

class Permission(Enum):
    """Granular permissions for fine-grained access control"""
    # Provider permissions
    PROVIDER_CREATE = "provider:create"
    PROVIDER_READ = "provider:read"
    PROVIDER_UPDATE = "provider:update"
    PROVIDER_DELETE = "provider:delete"
    
    # Validation permissions
    VALIDATION_RUN = "validation:run"
    VALIDATION_REVIEW = "validation:review"
    VALIDATION_APPROVE = "validation:approve"
    VALIDATION_REJECT = "validation:reject"
    
    # Audit permissions
    AUDIT_READ = "audit:read"
    AUDIT_EXPORT = "audit:export"
    
    # Admin permissions
    ADMIN_USERS = "admin:users"
    ADMIN_CONFIG = "admin:config"
    ADMIN_SYSTEM = "admin:system"
    
    # PII permissions
    PII_REVEAL = "pii:reveal"
    PII_EXPORT = "pii:export"
    
    # Export permissions
    EXPORT_CSV = "export:csv"
    EXPORT_PDF = "export:pdf"
    EXPORT_AUDIT = "export:audit"

@dataclass
class UserClaims:
    """User claims for JWT token"""
    user_id: str
    username: str
    email: str
    role: UserRole
    permissions: List[Permission]
    session_id: str
    issued_at: datetime
    expires_at: datetime
    iat: Optional[datetime] = None
    exp: Optional[datetime] = None

@dataclass
class TokenPair:
    """Access and refresh token pair"""
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "Bearer"

class JWTHandler:
    """JWT token handler with RBAC support"""
    
    def __init__(self, 
                 private_key: str,
                 public_key: str,
                 algorithm: str = "RS256",
                 access_token_expiry: int = 900,  # 15 minutes
                 refresh_token_expiry: int = 604800,  # 7 days
                 redis_client: Optional[redis.Redis] = None):
        """
        Initialize JWT handler
        
        Args:
            private_key: RSA private key for signing tokens
            public_key: RSA public key for verifying tokens
            algorithm: JWT algorithm (RS256 recommended)
            access_token_expiry: Access token expiry in seconds
            refresh_token_expiry: Refresh token expiry in seconds
            redis_client: Redis client for token blacklisting
        """
        self.private_key = private_key
        self.public_key = public_key
        self.algorithm = algorithm
        self.access_token_expiry = access_token_expiry
        self.refresh_token_expiry = refresh_token_expiry
        self.redis_client = redis_client
        
        # Role to permission mapping
        self.role_permissions = {
            UserRole.ADMIN: [
                Permission.PROVIDER_CREATE, Permission.PROVIDER_READ, Permission.PROVIDER_UPDATE, Permission.PROVIDER_DELETE,
                Permission.VALIDATION_RUN, Permission.VALIDATION_REVIEW, Permission.VALIDATION_APPROVE, Permission.VALIDATION_REJECT,
                Permission.AUDIT_READ, Permission.AUDIT_EXPORT,
                Permission.ADMIN_USERS, Permission.ADMIN_CONFIG, Permission.ADMIN_SYSTEM,
                Permission.PII_REVEAL, Permission.PII_EXPORT,
                Permission.EXPORT_CSV, Permission.EXPORT_PDF, Permission.EXPORT_AUDIT
            ],
            UserRole.REVIEWER: [
                Permission.PROVIDER_CREATE, Permission.PROVIDER_READ, Permission.PROVIDER_UPDATE,
                Permission.VALIDATION_RUN, Permission.VALIDATION_REVIEW, Permission.VALIDATION_APPROVE, Permission.VALIDATION_REJECT,
                Permission.AUDIT_READ,
                Permission.PII_REVEAL,
                Permission.EXPORT_CSV, Permission.EXPORT_PDF
            ],
            UserRole.AUDITOR: [
                Permission.PROVIDER_READ,
                Permission.AUDIT_READ, Permission.AUDIT_EXPORT,
                Permission.EXPORT_CSV, Permission.EXPORT_PDF, Permission.EXPORT_AUDIT
            ],
            UserRole.OPERATOR: [
                Permission.PROVIDER_CREATE, Permission.PROVIDER_READ, Permission.PROVIDER_UPDATE,
                Permission.VALIDATION_RUN,
                Permission.EXPORT_CSV
            ],
            UserRole.VIEWER: [
                Permission.PROVIDER_READ
            ]
        }
    
    def generate_keypair(self) -> tuple[str, str]:
        """Generate RSA key pair for JWT signing"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        public_key = private_key.public_key()
        
        # Serialize keys
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')
        
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
        
        return private_pem, public_pem
    
    def create_tokens(self, 
                     user_id: str, 
                     username: str, 
                     email: str, 
                     role: UserRole) -> TokenPair:
        """
        Create access and refresh token pair
        
        Args:
            user_id: Unique user identifier
            username: User's username
            email: User's email address
            role: User's role
            
        Returns:
            TokenPair with access and refresh tokens
        """
        now = datetime.now(timezone.utc)
        session_id = secrets.token_urlsafe(32)
        permissions = self.role_permissions.get(role, [])
        
        # Access token claims
        access_claims = {
            "user_id": user_id,
            "username": username,
            "email": email,
            "role": role.value,
            "permissions": [p.value for p in permissions],
            "session_id": session_id,
            "iat": now,
            "exp": now + timedelta(seconds=self.access_token_expiry),
            "type": "access"
        }
        
        # Refresh token claims
        refresh_claims = {
            "user_id": user_id,
            "session_id": session_id,
            "iat": now,
            "exp": now + timedelta(seconds=self.refresh_token_expiry),
            "type": "refresh"
        }
        
        # Generate tokens
        access_token = jwt.encode(access_claims, self.private_key, algorithm=self.algorithm)
        refresh_token = jwt.encode(refresh_claims, self.private_key, algorithm=self.algorithm)
        
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.access_token_expiry
        )
    
    def verify_token(self, token: str, token_type: str = "access") -> Optional[UserClaims]:
        """
        Verify and decode JWT token
        
        Args:
            token: JWT token to verify
            token_type: Expected token type (access/refresh)
            
        Returns:
            UserClaims if valid, None if invalid
        """
        try:
            # Check if token is blacklisted
            if self.redis_client and self._is_token_blacklisted(token):
                return None
            
            # Decode token
            payload = jwt.decode(token, self.public_key, algorithms=[self.algorithm])
            
            # Validate token type
            if payload.get("type") != token_type:
                return None
            
            # Check expiry
            exp = payload.get("exp")
            if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
                return None
            
            # Build UserClaims
            return UserClaims(
                user_id=payload["user_id"],
                username=payload["username"],
                email=payload["email"],
                role=UserRole(payload["role"]),
                permissions=[Permission(p) for p in payload.get("permissions", [])],
                session_id=payload["session_id"],
                issued_at=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
                expires_at=datetime.fromtimestamp(exp, tz=timezone.utc) if exp else None
            )
            
        except jwt.InvalidTokenError:
            return None
        except Exception:
            return None
    
    def refresh_access_token(self, refresh_token: str) -> Optional[TokenPair]:
        """
        Generate new access token using refresh token
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            New TokenPair if valid, None if invalid
        """
        claims = self.verify_token(refresh_token, "refresh")
        if not claims:
            return None
        
        # Generate new access token
        now = datetime.now(timezone.utc)
        permissions = self.role_permissions.get(claims.role, [])
        
        access_claims = {
            "user_id": claims.user_id,
            "username": claims.username,
            "email": claims.email,
            "role": claims.role.value,
            "permissions": [p.value for p in permissions],
            "session_id": claims.session_id,
            "iat": now,
            "exp": now + timedelta(seconds=self.access_token_expiry),
            "type": "access"
        }
        
        access_token = jwt.encode(access_claims, self.private_key, algorithm=self.algorithm)
        
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,  # Keep same refresh token
            expires_in=self.access_token_expiry
        )
    
    def revoke_token(self, token: str) -> bool:
        """
        Revoke token by adding to blacklist
        
        Args:
            token: Token to revoke
            
        Returns:
            True if successful, False otherwise
        """
        if not self.redis_client:
            return False
        
        try:
            # Decode token to get expiry
            payload = jwt.decode(token, self.public_key, algorithms=[self.algorithm], options={"verify_exp": False})
            exp = payload.get("exp")
            
            if exp:
                # Calculate TTL (time to live)
                exp_time = datetime.fromtimestamp(exp, tz=timezone.utc)
                ttl = int((exp_time - datetime.now(timezone.utc)).total_seconds())
                
                if ttl > 0:
                    # Add to blacklist with TTL
                    self.redis_client.setex(f"blacklist:{token}", ttl, "1")
                    return True
            
            return False
            
        except jwt.InvalidTokenError:
            return False
    
    def revoke_user_session(self, user_id: str, session_id: str) -> bool:
        """
        Revoke all tokens for a specific user session
        
        Args:
            user_id: User ID
            session_id: Session ID
            
        Returns:
            True if successful, False otherwise
        """
        if not self.redis_client:
            return False
        
        try:
            # Store session revocation
            self.redis_client.setex(f"revoked_session:{user_id}:{session_id}", 
                                  self.refresh_token_expiry, "1")
            return True
        except Exception:
            return False
    
    def _is_token_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted"""
        if not self.redis_client:
            return False
        
        return self.redis_client.exists(f"blacklist:{token}") > 0
    
    def has_permission(self, user_claims: UserClaims, permission: Permission) -> bool:
        """
        Check if user has specific permission
        
        Args:
            user_claims: User's claims from JWT
            permission: Permission to check
            
        Returns:
            True if user has permission, False otherwise
        """
        return permission in user_claims.permissions
    
    def has_role(self, user_claims: UserClaims, role: UserRole) -> bool:
        """
        Check if user has specific role
        
        Args:
            user_claims: User's claims from JWT
            role: Role to check
            
        Returns:
            True if user has role, False otherwise
        """
        return user_claims.role == role
    
    def get_user_permissions(self, role: UserRole) -> List[Permission]:
        """
        Get permissions for a specific role
        
        Args:
            role: User role
            
        Returns:
            List of permissions for the role
        """
        return self.role_permissions.get(role, [])
    
    def validate_permission_hierarchy(self, user_role: UserRole, required_permission: Permission) -> bool:
        """
        Validate if user role has required permission based on hierarchy
        
        Args:
            user_role: User's role
            required_permission: Required permission
            
        Returns:
            True if user has permission, False otherwise
        """
        user_permissions = self.role_permissions.get(user_role, [])
        return required_permission in user_permissions

# Global JWT handler instance
jwt_handler: Optional[JWTHandler] = None

def initialize_jwt_handler(private_key: str, public_key: str, redis_client: Optional[redis.Redis] = None) -> JWTHandler:
    """Initialize global JWT handler"""
    global jwt_handler
    jwt_handler = JWTHandler(private_key, public_key, redis_client=redis_client)
    return jwt_handler

def get_jwt_handler() -> JWTHandler:
    """Get global JWT handler instance"""
    if jwt_handler is None:
        raise RuntimeError("JWT handler not initialized. Call initialize_jwt_handler() first.")
    return jwt_handler
