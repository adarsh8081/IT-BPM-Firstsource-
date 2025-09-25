# Security Documentation

## Overview

This document outlines the comprehensive security measures implemented in the Provider Data Validation & Directory Management application. Our security framework follows industry best practices and healthcare compliance requirements (HIPAA, SOC 2).

## Security Architecture

### 1. Data Encryption

#### Database Encryption at Rest
- **PostgreSQL**: TDE (Transparent Data Encryption) enabled
- **Backup Encryption**: All database backups encrypted with AES-256
- **Key Management**: AWS KMS or Azure Key Vault for key rotation

```yaml
# Database Configuration
database:
  encryption:
    enabled: true
    algorithm: "AES-256-GCM"
    key_rotation_days: 90
  ssl:
    enabled: true
    require_ssl: true
    verify_ca: true
```

#### Transport Security
- **HTTPS**: All endpoints require TLS 1.3
- **Certificate Management**: Automated certificate renewal via Let's Encrypt
- **HSTS**: HTTP Strict Transport Security headers enforced

### 2. Authentication & Authorization

#### JWT-Based Authentication
- **Algorithm**: RS256 (RSA with SHA-256)
- **Token Expiry**: 15 minutes access, 7 days refresh
- **Token Storage**: HttpOnly cookies with SameSite=Strict

#### Role-Based Access Control (RBAC)

```python
# User Roles
class UserRole(Enum):
    ADMIN = "admin"           # Full system access
    REVIEWER = "reviewer"     # Provider review and validation
    AUDITOR = "auditor"       # Read-only audit access
    OPERATOR = "operator"     # Basic provider management
    VIEWER = "viewer"         # Read-only access
```

#### Permission Matrix

| Role | Provider CRUD | Validation | Review | Audit | Admin | Export |
|------|---------------|------------|--------|-------|-------|--------|
| Admin | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Reviewer | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ |
| Auditor | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ |
| Operator | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ |
| Viewer | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

### 3. Audit Logging

#### Comprehensive Audit Trail
- **User Actions**: All CRUD operations logged
- **Data Changes**: Before/after values for sensitive fields
- **Access Patterns**: Login attempts, permission checks
- **System Events**: Configuration changes, security events

#### Audit Log Schema
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "user_id": "user_123",
  "user_role": "reviewer",
  "action": "provider.update",
  "resource_type": "provider",
  "resource_id": "provider_456",
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "changes": {
    "before": {"phone": "***-***-1234"},
    "after": {"phone": "+1-555-123-4567"}
  },
  "risk_level": "medium",
  "session_id": "sess_789"
}
```

### 4. PII Protection

#### Default Masking Strategy
- **Phone Numbers**: `***-***-1234` (last 4 digits)
- **Email Addresses**: `j***@example.com` (first char + domain)
- **SSN**: `***-**-****` (fully masked)
- **Addresses**: `123 *** Street` (street number + masked street)

#### Permission-Based Reveal
```python
# PII Reveal Permission Check
def can_reveal_pii(user_role: UserRole, data_type: str) -> bool:
    permissions = {
        UserRole.ADMIN: ["all"],
        UserRole.REVIEWER: ["phone", "email"],
        UserRole.AUDITOR: ["email"],  # For audit purposes only
        UserRole.OPERATOR: ["phone"]
    }
    return "all" in permissions.get(user_role, []) or data_type in permissions.get(user_role, [])
```

#### Audit Trail for PII Access
- Every PII reveal logged with timestamp and justification
- Automatic alerts for suspicious access patterns
- Regular access reviews and compliance reporting

### 5. Secrets Management

#### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/db
DATABASE_SSL_CERT_PATH=/certs/db-cert.pem

# JWT
JWT_SECRET_KEY=your-rsa-private-key
JWT_PUBLIC_KEY=your-rsa-public-key
JWT_ALGORITHM=RS256

# Encryption
ENCRYPTION_KEY=your-encryption-key-32-chars
ENCRYPTION_SALT=your-salt-16-chars

# External APIs
NPI_API_KEY=your-npi-api-key
GOOGLE_PLACES_API_KEY=your-google-api-key
STATE_BOARD_API_KEY=your-state-board-key

# Redis (for rate limiting)
REDIS_URL=redis://localhost:6379/0

# Monitoring
SENTRY_DSN=your-sentry-dsn
LOG_LEVEL=INFO
```

#### Secrets Rotation
- **Automatic Rotation**: Keys rotated every 90 days
- **Zero-Downtime**: Rolling key updates
- **Backup Recovery**: Secure key backup and recovery procedures

### 6. Security Middleware

#### Rate Limiting
```python
# Rate Limiting Configuration
RATE_LIMITS = {
    "login": "5/minute",
    "api": "100/minute",
    "validation": "10/minute",
    "export": "5/hour",
    "pii_reveal": "20/hour"
}
```

#### Input Sanitization
- **SQL Injection**: Parameterized queries only
- **XSS Protection**: Input validation and output encoding
- **CSRF Protection**: Token-based CSRF prevention
- **File Upload**: Restricted file types and size limits

#### Content Security Policy (CSP)
```http
Content-Security-Policy: default-src 'self'; 
  script-src 'self' 'unsafe-inline'; 
  style-src 'self' 'unsafe-inline'; 
  img-src 'self' data: https:; 
  connect-src 'self' https://api.npiregistry.cms.hhs.gov;
```

### 7. Data Retention Policy

#### Retention Windows
- **Provider Data**: 7 years (healthcare requirement)
- **Audit Logs**: 10 years (compliance requirement)
- **Validation Results**: 5 years
- **Temporary Files**: 30 days
- **Raw Scans**: 90 days (maximum)

#### Automated Cleanup
```python
# Retention Policy Implementation
RETENTION_POLICIES = {
    "provider_data": timedelta(days=2555),  # 7 years
    "audit_logs": timedelta(days=3650),     # 10 years
    "validation_results": timedelta(days=1825),  # 5 years
    "temp_files": timedelta(days=30),
    "raw_scans": timedelta(days=90)
}
```

### 8. Monitoring & Alerting

#### Security Monitoring
- **Failed Login Attempts**: Alert after 5 failures
- **Unusual Access Patterns**: ML-based anomaly detection
- **PII Access**: Real-time monitoring and alerting
- **API Abuse**: Rate limit violations and suspicious requests

#### Compliance Reporting
- **Access Reports**: Monthly user access summaries
- **Audit Trail**: Quarterly audit log reviews
- **Data Retention**: Annual retention policy compliance
- **Security Incidents**: Immediate incident response procedures

### 9. Incident Response

#### Security Incident Classification
- **Critical**: Data breach, unauthorized access
- **High**: Multiple failed logins, suspicious activity
- **Medium**: Rate limit violations, policy violations
- **Low**: Configuration changes, system updates

#### Response Procedures
1. **Immediate**: Contain and assess impact
2. **Short-term**: Investigate and remediate
3. **Long-term**: Review and improve security measures
4. **Documentation**: Complete incident report

### 10. Compliance Requirements

#### HIPAA Compliance
- **Administrative Safeguards**: Role-based access, audit logs
- **Physical Safeguards**: Secure hosting, access controls
- **Technical Safeguards**: Encryption, access controls, audit logs

#### SOC 2 Type II
- **Security**: Access controls, encryption, monitoring
- **Availability**: System uptime, backup procedures
- **Processing Integrity**: Data validation, error handling
- **Confidentiality**: Data protection, access controls
- **Privacy**: PII handling, consent management

## Security Checklist

### Development
- [ ] All secrets in environment variables
- [ ] Input validation on all endpoints
- [ ] Output encoding for XSS prevention
- [ ] Parameterized queries for SQL injection prevention
- [ ] HTTPS enforced on all endpoints
- [ ] Security headers implemented
- [ ] Rate limiting configured
- [ ] Audit logging implemented

### Deployment
- [ ] Database encryption enabled
- [ ] SSL certificates configured
- [ ] Security headers deployed
- [ ] Monitoring and alerting active
- [ ] Backup encryption verified
- [ ] Access controls tested
- [ ] Incident response procedures documented

### Maintenance
- [ ] Regular security updates
- [ ] Key rotation scheduled
- [ ] Access reviews conducted
- [ ] Audit logs reviewed
- [ ] Penetration testing performed
- [ ] Compliance audits completed

## Security Contacts

- **Security Officer**: security@company.com
- **Incident Response**: incident@company.com
- **Compliance**: compliance@company.com

## Version History

- **v1.0** (2024-01-15): Initial security documentation
- **v1.1** (2024-01-20): Added retention policies and incident response
- **v1.2** (2024-01-25): Enhanced PII protection and audit logging
