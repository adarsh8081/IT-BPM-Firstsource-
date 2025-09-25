"""
Security Implementation Examples

This module provides practical examples of how to use the security components
including JWT authentication, RBAC, PII handling, and audit logging.
"""

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
import redis
import logging

# Import our security components
from backend.auth.jwt_handler import JWTHandler, UserClaims, UserRole, Permission, get_jwt_handler
from backend.auth.audit_logger import AuditLogger, AuditAction, get_audit_logger
from backend.auth.pii_handler import PIIHandler, PIIFieldType, PIIDisclosureReason, get_pii_handler
from backend.middleware.security import SecurityMiddleware, create_security_middleware
from backend.config.environment import EnvironmentManager, get_environment_manager
from backend.services.retention_manager import RetentionManager, get_retention_manager

# Initialize FastAPI app
app = FastAPI(title="Provider Validation API", version="1.0.0")

# Security scheme
security = HTTPBearer()

# Initialize Redis for rate limiting and caching
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Initialize environment manager
env_manager = EnvironmentManager()

# Initialize JWT handler
jwt_handler = JWTHandler(
    private_key=env_manager.get_jwt_config().secret_key,
    public_key=env_manager.get_jwt_config().public_key,
    redis_client=redis_client
)

# Initialize audit logger
audit_logger = AuditLogger(
    database_url=env_manager.get_database_config().url,
    redis_client=redis_client
)

# Initialize PII handler
encryption_config = env_manager.get_encryption_config()
pii_handler = PIIHandler(
    encryption_key=encryption_config.key,
    audit_callback=lambda event: audit_logger.log_event(
        action=AuditAction.PII_REVEAL,
        user_id=event.user_id,
        username=event.user_role,
        resource_type="pii",
        resource_id=event.field_name,
        success=event.success,
        error_message=event.error_message,
        metadata={
            'field_type': event.field_type.value,
            'sensitivity_level': event.sensitivity_level.value,
            'access_reason': event.access_reason.value,
            'justification': event.justification
        }
    )
)

# Initialize retention manager
retention_manager = RetentionManager(
    database_url=env_manager.get_database_config().url,
    audit_callback=lambda event: audit_logger.log_event(
        action=AuditAction.DATA_DELETE,
        resource_type="retention",
        resource_id=event.policy_type.value,
        success=event.success,
        error_message=event.error_message,
        metadata={
            'affected_records': event.affected_records,
            'affected_size_bytes': event.affected_size_bytes,
            'action': event.action.value
        }
    )
)

# Add security middleware
app.add_middleware(SecurityMiddleware, redis_client=redis_client)

# Add CORS middleware
cors_config = env_manager.get_security_config()
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_config.cors_origins,
    allow_credentials=cors_config.cors_credentials,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    max_age=cors_config.cors_max_age
)

# Dependency to get current user from JWT token
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserClaims:
    """Get current user from JWT token"""
    try:
        # Verify token
        claims = jwt_handler.verify_token(credentials.credentials)
        if not claims:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Log authentication event
        audit_logger.log_event(
            action=AuditAction.LOGIN,
            user_id=claims.user_id,
            username=claims.username,
            user_role=claims.role.value,
            session_id=claims.session_id,
            success=True
        )
        
        return claims
        
    except Exception as e:
        # Log failed authentication
        audit_logger.log_event(
            action=AuditAction.LOGIN_FAILED,
            success=False,
            error_message=str(e)
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Permission dependency
def require_permission(permission: Permission):
    """Dependency to check user permissions"""
    def permission_checker(current_user: UserClaims = Depends(get_current_user)):
        if not jwt_handler.has_permission(current_user, permission):
            # Log unauthorized access attempt
            audit_logger.log_event(
                action=AuditAction.UNAUTHORIZED_ACCESS,
                user_id=current_user.user_id,
                username=current_user.username,
                user_role=current_user.role.value,
                success=False,
                error_message=f"Missing permission: {permission.value}"
            )
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {permission.value}"
            )
        
        return current_user
    
    return permission_checker

# Role dependency
def require_role(role: UserRole):
    """Dependency to check user role"""
    def role_checker(current_user: UserClaims = Depends(get_current_user)):
        if not jwt_handler.has_role(current_user, role):
            # Log unauthorized access attempt
            audit_logger.log_event(
                action=AuditAction.UNAUTHORIZED_ACCESS,
                user_id=current_user.user_id,
                username=current_user.username,
                user_role=current_user.role.value,
                success=False,
                error_message=f"Insufficient role. Required: {role.value}"
            )
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient role. Required: {role.value}"
            )
        
        return current_user
    
    return role_checker

# PII reveal dependency
def require_pii_reveal(field_name: str, reason: PIIDisclosureReason):
    """Dependency to handle PII reveal with proper authorization"""
    def pii_checker(current_user: UserClaims = Depends(get_current_user)):
        # Check if user has permission to reveal PII
        if not pii_handler.has_permission(current_user.permissions, pii_handler.get_pii_field_config(field_name), False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions to reveal PII field: {field_name}"
            )
        
        return current_user
    
    return pii_checker

# Example API endpoints with security

@app.post("/api/auth/login")
async def login(credentials: dict):
    """Login endpoint with rate limiting"""
    # This would validate credentials and return JWT tokens
    # Rate limiting is handled by middleware
    
    # Log login attempt
    audit_logger.log_event(
        action=AuditAction.LOGIN,
        username=credentials.get('username'),
        success=True,
        metadata={'login_method': 'password'}
    )
    
    return {"access_token": "jwt_token_here", "token_type": "bearer"}

@app.get("/api/providers")
async def get_providers(
    current_user: UserClaims = Depends(require_permission(Permission.PROVIDER_READ)),
    request: Request = None
):
    """Get providers with PII masking based on user permissions"""
    
    # Log data access
    audit_logger.log_event(
        action=AuditAction.PROVIDER_READ,
        user_id=current_user.user_id,
        username=current_user.username,
        user_role=current_user.role.value,
        session_id=current_user.session_id,
        resource_type="provider",
        success=True
    )
    
    # Mock provider data
    provider_data = {
        "provider_id": "PROV001",
        "given_name": "Dr. John",
        "family_name": "Smith",
        "phone_primary": "+1-555-123-4567",
        "email": "john.smith@example.com",
        "npi_number": "1234567890",
        "address_street": "123 Main Street"
    }
    
    # Apply PII masking based on user permissions
    masked_data = pii_handler.mask_provider_data(
        provider_data,
        [p.value for p in current_user.permissions],
        is_privileged=False
    )
    
    return {"providers": [masked_data]}

@app.get("/api/providers/{provider_id}/pii")
async def reveal_provider_pii(
    provider_id: str,
    field_name: str,
    reason: PIIDisclosureReason,
    justification: str,
    current_user: UserClaims = Depends(require_permission(Permission.PII_REVEAL)),
    request: Request = None
):
    """Reveal specific PII field with proper authorization and audit logging"""
    
    # Mock encrypted PII data
    encrypted_phone = pii_handler.encrypt_pii_value("+1-555-123-4567")
    
    # Reveal PII with audit logging
    revealed_value = pii_handler.reveal_pii_field(
        field_name=field_name,
        value=encrypted_phone,
        user_id=current_user.user_id,
        user_role=current_user.role.value,
        user_permissions=[p.value for p in current_user.permissions],
        access_reason=reason,
        justification=justification,
        ip_address=request.client.host if request else None,
        session_id=current_user.session_id
    )
    
    if not revealed_value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unable to reveal PII field"
        )
    
    return {
        "field_name": field_name,
        "revealed_value": revealed_value,
        "access_reason": reason.value,
        "justification": justification
    }

@app.post("/api/providers")
async def create_provider(
    provider_data: dict,
    current_user: UserClaims = Depends(require_permission(Permission.PROVIDER_CREATE)),
    request: Request = None
):
    """Create provider with audit logging"""
    
    # Log data creation
    audit_logger.log_event(
        action=AuditAction.PROVIDER_CREATE,
        user_id=current_user.user_id,
        username=current_user.username,
        user_role=current_user.role.value,
        session_id=current_user.session_id,
        resource_type="provider",
        changes={"before": None, "after": provider_data},
        success=True
    )
    
    # Encrypt PII fields before storage
    encrypted_data = provider_data.copy()
    for field_name, value in provider_data.items():
        if pii_handler.get_pii_field_config(field_name):
            encrypted_data[field_name] = pii_handler.encrypt_pii_value(str(value))
    
    # Store provider data (mock)
    provider_id = "PROV002"
    
    return {"provider_id": provider_id, "status": "created"}

@app.put("/api/providers/{provider_id}")
async def update_provider(
    provider_id: str,
    provider_data: dict,
    current_user: UserClaims = Depends(require_permission(Permission.PROVIDER_UPDATE)),
    request: Request = None
):
    """Update provider with change tracking"""
    
    # Mock existing data
    existing_data = {
        "provider_id": provider_id,
        "phone_primary": "+1-555-123-4567",
        "email": "john.smith@example.com"
    }
    
    # Log data update with before/after changes
    audit_logger.log_event(
        action=AuditAction.PROVIDER_UPDATE,
        user_id=current_user.user_id,
        username=current_user.username,
        user_role=current_user.role.value,
        session_id=current_user.session_id,
        resource_type="provider",
        resource_id=provider_id,
        changes={"before": existing_data, "after": provider_data},
        success=True
    )
    
    # Encrypt PII fields before storage
    encrypted_data = provider_data.copy()
    for field_name, value in provider_data.items():
        if pii_handler.get_pii_field_config(field_name):
            encrypted_data[field_name] = pii_handler.encrypt_pii_value(str(value))
    
    return {"provider_id": provider_id, "status": "updated"}

@app.delete("/api/providers/{provider_id}")
async def delete_provider(
    provider_id: str,
    current_user: UserClaims = Depends(require_permission(Permission.PROVIDER_DELETE)),
    request: Request = None
):
    """Delete provider with audit logging"""
    
    # Log data deletion
    audit_logger.log_event(
        action=AuditAction.PROVIDER_DELETE,
        user_id=current_user.user_id,
        username=current_user.username,
        user_role=current_user.role.value,
        session_id=current_user.session_id,
        resource_type="provider",
        resource_id=provider_id,
        success=True
    )
    
    return {"provider_id": provider_id, "status": "deleted"}

@app.post("/api/validate/batch")
async def validate_providers_batch(
    validation_request: dict,
    current_user: UserClaims = Depends(require_permission(Permission.VALIDATION_RUN)),
    request: Request = None
):
    """Run batch validation with audit logging"""
    
    # Log validation run
    audit_logger.log_event(
        action=AuditAction.VALIDATION_RUN,
        user_id=current_user.user_id,
        username=current_user.username,
        user_role=current_user.role.value,
        session_id=current_user.session_id,
        resource_type="validation",
        metadata={
            'provider_count': len(validation_request.get('provider_ids', [])),
            'validation_type': 'batch'
        },
        success=True
    )
    
    # Mock validation job
    job_id = "JOB001"
    
    return {"job_id": job_id, "status": "started"}

@app.get("/api/audit/logs")
async def get_audit_logs(
    current_user: UserClaims = Depends(require_permission(Permission.AUDIT_READ)),
    request: Request = None
):
    """Get audit logs with proper authorization"""
    
    # Log audit log access
    audit_logger.log_event(
        action=AuditAction.AUDIT_READ,
        user_id=current_user.user_id,
        username=current_user.username,
        user_role=current_user.role.value,
        session_id=current_user.session_id,
        resource_type="audit",
        success=True
    )
    
    # Get audit logs
    logs = audit_logger.get_audit_logs(
        user_id=current_user.user_id,
        limit=100
    )
    
    return {"logs": logs}

@app.post("/api/admin/retention/execute")
async def execute_retention_policy(
    policy_type: str,
    dry_run: bool = False,
    current_user: UserClaims = Depends(require_role(UserRole.ADMIN)),
    request: Request = None
):
    """Execute retention policy (admin only)"""
    
    # Log retention policy execution
    audit_logger.log_event(
        action=AuditAction.ADMIN_CONFIG,
        user_id=current_user.user_id,
        username=current_user.username,
        user_role=current_user.role.value,
        session_id=current_user.session_id,
        resource_type="retention",
        resource_id=policy_type,
        metadata={'dry_run': dry_run},
        success=True
    )
    
    # Execute retention policy
    from backend.services.retention_manager import RetentionPolicyType
    
    try:
        policy_type_enum = RetentionPolicyType(policy_type)
        event = retention_manager.execute_retention_policy(policy_type_enum, dry_run)
        
        return {
            "policy_type": policy_type,
            "dry_run": dry_run,
            "affected_records": event.affected_records,
            "affected_size_bytes": event.affected_size_bytes,
            "success": event.success,
            "error_message": event.error_message
        }
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid policy type: {policy_type}"
        )

@app.get("/api/admin/retention/summary")
async def get_retention_summary(
    current_user: UserClaims = Depends(require_role(UserRole.ADMIN))
):
    """Get retention policy summary (admin only)"""
    
    summary = retention_manager.get_retention_summary()
    
    return {"retention_policies": summary}

# Example of middleware configuration
def create_app_with_security():
    """Create FastAPI app with comprehensive security"""
    
    # Create security middleware
    security_middleware = create_security_middleware(
        app=app,
        redis_client=redis_client,
        security_callback=lambda event: audit_logger.log_event(
            action=AuditAction.SYSTEM_WARNING,
            metadata={
                'security_event_type': event.event_type.value,
                'severity': event.severity,
                'details': event.details
            }
        )
    )
    
    return app

# Example of role-based access patterns
class ProviderService:
    """Example service with role-based access control"""
    
    def __init__(self, jwt_handler: JWTHandler, audit_logger: AuditLogger):
        self.jwt_handler = jwt_handler
        self.audit_logger = audit_logger
    
    def get_providers(self, user_claims: UserClaims, filters: dict = None):
        """Get providers based on user role and permissions"""
        
        # Check permissions
        if not self.jwt_handler.has_permission(user_claims, Permission.PROVIDER_READ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to read providers"
            )
        
        # Role-based data filtering
        if user_claims.role == UserRole.VIEWER:
            # Viewers can only see basic provider information
            return self._get_basic_provider_info(filters)
        elif user_claims.role == UserRole.OPERATOR:
            # Operators can see full provider information
            return self._get_full_provider_info(filters)
        elif user_claims.role in [UserRole.REVIEWER, UserRole.AUDITOR]:
            # Reviewers and auditors can see all information including PII
            return self._get_complete_provider_info(filters, user_claims)
        elif user_claims.role == UserRole.ADMIN:
            # Admins can see everything
            return self._get_admin_provider_info(filters)
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid user role"
            )
    
    def _get_basic_provider_info(self, filters):
        """Get basic provider information (no PII)"""
        return {"providers": [], "note": "Basic information only"}
    
    def _get_full_provider_info(self, filters):
        """Get full provider information (with masked PII)"""
        return {"providers": [], "note": "Full information with masked PII"}
    
    def _get_complete_provider_info(self, filters, user_claims):
        """Get complete provider information (with PII based on permissions)"""
        return {"providers": [], "note": "Complete information with PII"}
    
    def _get_admin_provider_info(self, filters):
        """Get admin-level provider information"""
        return {"providers": [], "note": "Admin-level information"}

# Example of PII handling patterns
class PIIExample:
    """Example of PII handling patterns"""
    
    def __init__(self, pii_handler: PIIHandler):
        self.pii_handler = pii_handler
    
    def process_provider_data(self, user_claims: UserClaims, provider_data: dict):
        """Process provider data with appropriate PII handling"""
        
        # Check if user can reveal PII
        can_reveal_pii = any(
            permission.value.startswith('pii:reveal') 
            for permission in user_claims.permissions
        )
        
        if can_reveal_pii:
            # User can see PII, return unmasked data
            return provider_data
        else:
            # User cannot see PII, return masked data
            return self.pii_handler.mask_provider_data(
                provider_data,
                [p.value for p in user_claims.permissions],
                is_privileged=False
            )
    
    def reveal_specific_field(self, user_claims: UserClaims, field_name: str, 
                             encrypted_value: str, reason: PIIDisclosureReason,
                             justification: str):
        """Reveal specific PII field with proper authorization"""
        
        return self.pii_handler.reveal_pii_field(
            field_name=field_name,
            value=encrypted_value,
            user_id=user_claims.user_id,
            user_role=user_claims.role.value,
            user_permissions=[p.value for p in user_claims.permissions],
            access_reason=reason,
            justification=justification
        )

if __name__ == "__main__":
    import uvicorn
    
    # Run the application with security middleware
    uvicorn.run(
        "security_examples:app",
        host="0.0.0.0",
        port=8000,
        ssl_keyfile="path/to/ssl-key.pem",
        ssl_certfile="path/to/ssl-cert.pem"
    )
