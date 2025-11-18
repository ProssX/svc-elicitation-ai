# Interview Permissions Documentation

**Service:** `svc-elicitation-ai`  
**Version:** 1.0  
**Last Updated:** 2025-01-26  
**Target Audience:** Auth Team (`svc-users-python`)

---

## Overview

This document describes the permission system for the Interview Service (`svc-elicitation-ai`). The service implements **Permission-Based Access Control (PBAC)** following the same pattern as `svc-organizations-php`.

**Key Points:**
- Permissions follow the `resource:action` format
- Permissions are included in the JWT token as a `permissions` array
- The Interview Service validates permissions on every request
- No database queries are needed for permission checks (stateless)

---

## Permission Format

All permissions follow the pattern: `resource:action`

- **resource**: The entity being accessed (e.g., `interviews`)
- **action**: The operation being performed (e.g., `create`, `read`, `update`)

**Example:** `interviews:create`

This format is consistent with `svc-organizations-php` for cross-service compatibility.

---

## Available Permissions

### Core Permissions

| Permission | Description | Scope |
|------------|-------------|-------|
| `interviews:create` | Create new interviews and continue existing ones | Own interviews only |
| `interviews:read` | Read and list interviews | Own interviews only |
| `interviews:read_all` | Read and list all interviews in the organization | Organization-wide |
| `interviews:update` | Update interview status and metadata | Own interviews only |
| `interviews:delete` | Delete interviews (soft delete) | Own interviews only (future) |
| `interviews:export` | Export interviews to documents | Own interviews only |

### Permission Details

#### `interviews:create`
- **Allows:** Starting new interviews, continuing existing interviews
- **Endpoints:** `POST /api/v1/interviews/start`, `POST /api/v1/interviews/continue`
- **Ownership:** User can only continue their own interviews (validated by `employee_id`)
- **Use Case:** All users who need to conduct interviews

#### `interviews:read`
- **Allows:** Viewing and listing own interviews
- **Endpoints:** `GET /api/v1/interviews`, `GET /api/v1/interviews/{id}`
- **Ownership:** User can only see interviews where `employee_id` matches their `user_id`
- **Use Case:** Regular users viewing their own work

#### `interviews:read_all`
- **Allows:** Viewing and listing ALL interviews in the organization
- **Endpoints:** `GET /api/v1/interviews`, `GET /api/v1/interviews/{id}`
- **Ownership:** Can access any interview in the organization (bypasses ownership check)
- **Use Case:** Managers, admins, supervisors who need to review team interviews
- **Note:** This is a **special permission** that grants elevated access

#### `interviews:update`
- **Allows:** Updating interview status, metadata
- **Endpoints:** `PATCH /api/v1/interviews/{id}`
- **Ownership:** User can only update their own interviews (unless they have `read_all`)
- **Use Case:** Users who need to mark interviews as complete, archived, etc.

#### `interviews:delete`
- **Allows:** Soft-deleting interviews
- **Endpoints:** `DELETE /api/v1/interviews/{id}` (future implementation)
- **Ownership:** User can only delete their own interviews
- **Use Case:** Users who need to remove interviews (future feature)

#### `interviews:export`
- **Allows:** Exporting interviews to documents (PDF, Word, etc.)
- **Endpoints:** `POST /api/v1/interviews/export`
- **Ownership:** User can only export their own interviews (unless they have `read_all`)
- **Use Case:** Users who need to generate reports or documentation

---

## Permission Hierarchy

```
interviews:read_all (Admin/Manager)
    ↓ includes access to
interviews:read (Regular User)
    ↓ requires
interviews:create (Can create interviews)
```

**Important:** `interviews:read_all` does NOT automatically grant other permissions. It only provides organization-wide read access. Users with `read_all` still need `update`, `export`, etc. for those operations.

---

## Suggested Role-to-Permission Mapping

Here are recommended permission sets for common roles:

### Admin Role
**Permissions:**
```json
[
  "interviews:create",
  "interviews:read",
  "interviews:read_all",
  "interviews:update",
  "interviews:export"
]
```
**Can:** Create, view all, update, and export any interview in the organization

### Manager Role
**Permissions:**
```json
[
  "interviews:create",
  "interviews:read",
  "interviews:read_all",
  "interviews:export"
]
```
**Can:** Create, view all, and export interviews (cannot update others' interviews)

### User Role (Regular Employee)
**Permissions:**
```json
[
  "interviews:create",
  "interviews:read",
  "interviews:export"
]
```
**Can:** Create, view own, and export own interviews only

### Read-Only Role (Auditor)
**Permissions:**
```json
[
  "interviews:read_all"
]
```
**Can:** View all interviews but cannot create, update, or export

### Minimal Role (Restricted User)
**Permissions:**
```json
[
  "interviews:create",
  "interviews:read"
]
```
**Can:** Create and view own interviews (cannot export)

---

## JWT Structure

### Required JWT Claims

The Interview Service expects the following claims in the JWT:

```json
{
  "sub": "01932e5f-8b2a-7890-b123-456789abcdef",
  "email": "user@example.com",
  "organization_id": "org-123",
  "roles": ["ROLE_USER"],
  "permissions": [
    "interviews:create",
    "interviews:read",
    "interviews:export"
  ],
  "exp": 1735228800,
  "iat": 1735142400
}
```

### JWT Claims Explained

| Claim | Type | Required | Description |
|-------|------|----------|-------------|
| `sub` | string | ✅ Yes | User ID (UUID format) |
| `email` | string | ✅ Yes | User email address |
| `organization_id` | string | ✅ Yes | Organization ID (UUID format) |
| `roles` | array[string] | ❌ No | User roles (for reference, not used for authorization) |
| `permissions` | array[string] | ✅ Yes | List of permission strings |
| `exp` | number | ✅ Yes | Expiration timestamp (Unix epoch) |
| `iat` | number | ✅ Yes | Issued at timestamp (Unix epoch) |

### Permissions Array Format

- **Type:** Array of strings
- **Format:** Each string must follow `resource:action` pattern
- **Validation:** Invalid permissions are filtered out and logged
- **Empty Array:** If no permissions are provided, user will be denied access to all endpoints

**Example:**
```json
"permissions": [
  "interviews:create",
  "interviews:read",
  "interviews:read_all",
  "interviews:update",
  "interviews:export"
]
```

---

## Implementation Guide for Auth Service

### Step 1: Define Permission Constants

In `svc-users-python`, define the interview permissions:

```python
# app/models/permission.py or similar

class InterviewPermissions:
    """Interview service permissions"""
    CREATE = "interviews:create"
    READ = "interviews:read"
    READ_ALL = "interviews:read_all"
    UPDATE = "interviews:update"
    DELETE = "interviews:delete"
    EXPORT = "interviews:export"
```

### Step 2: Map Roles to Permissions

Create a mapping from roles to permissions:

```python
# app/services/permission_service.py or similar

ROLE_PERMISSIONS = {
    "ROLE_ADMIN": [
        InterviewPermissions.CREATE,
        InterviewPermissions.READ,
        InterviewPermissions.READ_ALL,
        InterviewPermissions.UPDATE,
        InterviewPermissions.EXPORT,
    ],
    "ROLE_MANAGER": [
        InterviewPermissions.CREATE,
        InterviewPermissions.READ,
        InterviewPermissions.READ_ALL,
        InterviewPermissions.EXPORT,
    ],
    "ROLE_USER": [
        InterviewPermissions.CREATE,
        InterviewPermissions.READ,
        InterviewPermissions.EXPORT,
    ],
}

def get_permissions_for_roles(roles: list[str]) -> list[str]:
    """
    Get all permissions for a list of roles.
    
    Args:
        roles: List of role names (e.g., ["ROLE_USER", "ROLE_MANAGER"])
        
    Returns:
        List of unique permissions
    """
    permissions = set()
    for role in roles:
        permissions.update(ROLE_PERMISSIONS.get(role, []))
    return list(permissions)
```

### Step 3: Include Permissions in JWT

When generating the JWT token, include the permissions:

```python
# app/services/auth_service.py or similar

def create_access_token(user: User) -> str:
    """
    Create JWT access token with user information and permissions.
    
    Args:
        user: User object with roles
        
    Returns:
        JWT token string
    """
    # Get permissions based on user roles
    permissions = get_permissions_for_roles(user.roles)
    
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "organization_id": str(user.organization_id),
        "roles": user.roles,
        "permissions": permissions,  # Add permissions here
        "exp": datetime.utcnow() + timedelta(hours=24),
        "iat": datetime.utcnow(),
    }
    
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")
```

### Step 4: Testing

Test that JWTs include the correct permissions:

```python
def test_jwt_includes_permissions():
    """Test that JWT contains permissions array"""
    user = User(
        id=uuid4(),
        email="test@example.com",
        organization_id=uuid4(),
        roles=["ROLE_USER"]
    )
    
    token = create_access_token(user)
    decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    
    assert "permissions" in decoded
    assert isinstance(decoded["permissions"], list)
    assert "interviews:create" in decoded["permissions"]
    assert "interviews:read" in decoded["permissions"]
```

---

## Endpoint Permission Requirements

### Summary Table

| Endpoint | Method | Required Permission | Ownership Check |
|----------|--------|---------------------|-----------------|
| `/api/v1/interviews/start` | POST | `interviews:create` | N/A (creates new) |
| `/api/v1/interviews/continue` | POST | `interviews:create` | ✅ Must own interview |
| `/api/v1/interviews` | GET | `interviews:read` | ✅ Auto-filtered by user |
| `/api/v1/interviews` | GET | `interviews:read_all` | ❌ Sees all in org |
| `/api/v1/interviews/{id}` | GET | `interviews:read` | ✅ Must own interview |
| `/api/v1/interviews/{id}` | GET | `interviews:read_all` | ❌ Can see any |
| `/api/v1/interviews/{id}` | PATCH | `interviews:update` | ✅ Must own interview |
| `/api/v1/interviews/export` | POST | `interviews:export` | ✅ Must own interview |

### Ownership Rules

**Ownership Check:** The service validates that `interview.employee_id == user.user_id`

**Bypass with `read_all`:** Users with `interviews:read_all` can access any interview in their organization, bypassing the ownership check.

---

## Error Responses

### 403 Forbidden - Missing Permission

When a user lacks the required permission:

```json
{
  "status": "error",
  "code": 403,
  "message": "Insufficient permissions",
  "errors": [
    {
      "field": "permissions",
      "error": "Required permission: interviews:create",
      "user_permissions": ["interviews:read"]
    }
  ]
}
```

### 403 Forbidden - Access Denied to Resource

When a user tries to access another user's interview:

```json
{
  "status": "error",
  "code": 403,
  "message": "Access denied",
  "errors": [
    {
      "field": "interview_id",
      "error": "You don't have permission to access this interview"
    }
  ]
}
```

### 403 Forbidden - No Permissions in JWT

When JWT doesn't contain any permissions:

```json
{
  "status": "error",
  "code": 403,
  "message": "Insufficient permissions",
  "errors": [
    {
      "field": "permissions",
      "error": "No permissions found in JWT. Contact administrator.",
      "user_permissions": []
    }
  ]
}
```

---

## Testing with Mock JWTs

### Creating Test JWTs

For testing purposes, you can create JWTs with specific permissions:

```python
import jwt
from datetime import datetime, timedelta

def create_test_jwt(permissions: list[str]) -> str:
    """Create a test JWT with specific permissions"""
    payload = {
        "sub": "test-user-123",
        "email": "test@example.com",
        "organization_id": "test-org-123",
        "roles": ["ROLE_USER"],
        "permissions": permissions,
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, "your-secret-key", algorithm="HS256")

# Test with different permission sets
jwt_admin = create_test_jwt([
    "interviews:create",
    "interviews:read",
    "interviews:read_all",
    "interviews:update",
    "interviews:export"
])

jwt_user = create_test_jwt([
    "interviews:create",
    "interviews:read",
    "interviews:export"
])

jwt_no_permissions = create_test_jwt([])
```

### Testing Scenarios

1. **User with full permissions** - Should access all endpoints
2. **User with read-only** - Should only access GET endpoints
3. **User with no permissions** - Should get 403 on all endpoints
4. **User trying to access another's interview** - Should get 403
5. **Admin with read_all** - Should access any interview

---

## Security Considerations

### ✅ Best Practices

1. **Permissions are signed in JWT** - Cannot be tampered with
2. **Stateless validation** - No database queries for permission checks
3. **Ownership validation** - Double-check that users own the resources they access
4. **Audit logging** - All permission denials are logged with user context
5. **Fail-safe defaults** - Missing permissions = denied access

### ⚠️ Important Notes

1. **Don't expose sensitive info in errors** - 403 responses don't reveal why access was denied
2. **Use 404 instead of 403 for non-existent resources** - Don't reveal resource existence
3. **Log all permission denials** - Monitor for potential security issues
4. **Validate permission format** - Invalid permissions are filtered out
5. **Keep permissions in sync** - Coordinate deployments between auth and interview services

---

## Deployment Checklist

Before deploying the permission system to production:

### Pre-Deployment

- [ ] Auth service updated to include `permissions` array in JWT
- [ ] Role-to-permission mapping configured in auth service
- [ ] Test JWTs generated with various permission sets
- [ ] Integration tests pass with real JWTs
- [ ] Documentation shared with all teams

### Staging Deployment

- [ ] Deploy auth service to staging
- [ ] Deploy interview service to staging
- [ ] Test end-to-end with real user accounts
- [ ] Verify permission denials work correctly
- [ ] Check audit logs for permission checks

### Production Deployment

- [ ] Deploy auth service first (backward compatible)
- [ ] Verify existing JWTs still work
- [ ] Deploy interview service
- [ ] Monitor error rates for 403 responses
- [ ] Verify users can access appropriate endpoints

### Post-Deployment

- [ ] Monitor logs for unexpected permission denials
- [ ] Verify no users are locked out
- [ ] Check that admins can access all interviews
- [ ] Validate audit trail is working

---

## Rollback Plan

If issues occur in production:

### Option 1: Revert Deployment
- Rollback interview service to previous version (no permission checks)
- Gives time to fix issues without impacting users

### Option 2: Emergency Permission Grant
- Auth service temporarily grants all permissions to all users
- Allows service to continue while investigating issues

### Option 3: Feature Flag
- Disable permission validation via environment variable
- Requires code change but allows quick toggle

---

## Support and Questions

### Contact Information

- **Team:** Interview Service Team
- **Service:** `svc-elicitation-ai`
- **Repository:** [Link to repo]
- **Slack Channel:** #interview-service

### Common Questions

**Q: What happens if JWT doesn't include permissions?**  
A: User will be denied access to all endpoints (403 Forbidden)

**Q: Can a user have multiple roles?**  
A: Yes, permissions from all roles are combined (union)

**Q: What's the difference between `read` and `read_all`?**  
A: `read` = own interviews only, `read_all` = all interviews in organization

**Q: Do permissions expire?**  
A: Permissions are in the JWT, so they expire when the JWT expires

**Q: Can permissions be revoked immediately?**  
A: No, permissions are in the JWT. To revoke, user must re-authenticate

**Q: How do I test with different permissions?**  
A: Create test JWTs with specific permission arrays (see Testing section)

---

## Appendix: Permission Validation Logic

### Pseudocode

```python
def validate_permission(required_permission: str, user: TokenPayload) -> bool:
    """
    Validate if user has required permission
    
    Args:
        required_permission: Permission string (e.g., "interviews:create")
        user: User token payload with permissions array
        
    Returns:
        True if user has permission, False otherwise
    """
    # Check if user has the exact permission
    if required_permission in user.permissions:
        return True
    
    # Special case: read_all grants read access
    if required_permission == "interviews:read" and "interviews:read_all" in user.permissions:
        return True
    
    return False

def validate_ownership(interview: Interview, user: TokenPayload) -> bool:
    """
    Validate if user owns the interview or has read_all permission
    
    Args:
        interview: Interview object
        user: User token payload
        
    Returns:
        True if user has access, False otherwise
    """
    # User owns the interview
    if interview.employee_id == user.user_id:
        return True
    
    # User has organization-wide access
    if "interviews:read_all" in user.permissions:
        return True
    
    return False
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-01-26 | Initial documentation |

---

**End of Document**
