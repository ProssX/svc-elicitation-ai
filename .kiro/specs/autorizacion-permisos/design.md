# Documento de Diseño - Autorización y Control de Permisos

## Overview

Este documento describe el diseño técnico para implementar un sistema de autorización basado en permisos en el microservicio `svc-elicitation-ai`. La solución sigue el mismo patrón establecido en `svc-organizations-php`, utilizando permisos granulares en formato `resource:action` que vienen en el JWT.

**Objetivos principales:**
- Implementar control de acceso basado en permisos (PBAC)
- Extraer permisos del JWT automáticamente
- Proteger todos los endpoints con validación de permisos
- Diferenciar entre acceso a recursos propios vs organizacionales
- Mantener consistencia con el patrón de `svc-organizations-php`

**Tecnologías utilizadas:**
- **FastAPI Dependencies**: Para inyección de validación de permisos
- **Pydantic**: Para validación de permisos en JWT
- **Python Enum**: Para definir permisos disponibles con type safety
- **Decoradores**: Para aplicar validación de permisos a endpoints

## Architecture

### Diagrama de Flujo de Autorización

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React)                         │
│  - Usuario hace login                                       │
│  - Recibe JWT con permisos                                  │
└────────────────┬────────────────────────────────────────────┘
                 │ HTTP Request + JWT
                 │ Authorization: Bearer <token>
                 │
┌────────────────▼────────────────────────────────────────────┐
│           FastAPI Middleware (Auth)                         │
│  1. Valida JWT signature                                    │
│  2. Decodifica payload                                      │
│  3. Extrae: user_id, organization_id, permissions[]         │
│  4. Crea TokenPayload con permisos                          │
└────────────────┬────────────────────────────────────────────┘
                 │ TokenPayload
                 │
┌────────────────▼────────────────────────────────────────────┐
│           Endpoint con Dependency                           │
│  @router.post("/start")                                     │
│  async def start_interview(                                 │
│      current_user: TokenPayload = Depends(get_current_user),│
│      _: None = Depends(require_permission("interviews:create"))│
│  )                                                          │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ├─ ✅ Tiene permiso → Ejecuta endpoint
                 │
                 └─ ❌ No tiene permiso → HTTP 403
                      {
                        "status": "error",
                        "code": 403,
                        "message": "Insufficient permissions",
                        "errors": [{
                          "field": "permissions",
                          "error": "Required: interviews:create, Has: []"
                        }]
                      }
```

### Componentes del Sistema

```
app/
├── models/
│   └── permissions.py (NEW)          # Enum de permisos
├── middleware/
│   └── auth_middleware.py (UPDATE)   # Extraer permisos del JWT
├── dependencies/
│   └── permissions.py (NEW)          # Dependencies de validación
├── routers/
│   └── interviews.py (UPDATE)        # Agregar dependencies a endpoints
└── services/
    └── token_validator.py (UPDATE)   # TokenPayload con permisos
```

## Components and Interfaces

### 1. Enum de Permisos (app/models/permissions.py - NEW)

```python
"""
Interview Permissions Enum
Defines all available permissions for interview operations
"""
from enum import Enum


class InterviewPermission(str, Enum):
    """
    Permission definitions for interview operations
    
    Format: resource:action
    - resource: The entity being accessed (interviews)
    - action: The operation being performed (create, read, update, delete, export)
    
    Special permissions:
    - interviews:read_all: Allows reading interviews from all users in the organization
      (for managers/admins). Regular users with only interviews:read can only see their own.
    """
    
    # Core CRUD permissions
    CREATE = "interviews:create"      # Create new interviews and continue existing ones
    READ = "interviews:read"          # Read own interviews
    READ_ALL = "interviews:read_all"  # Read all interviews in organization (admin/manager)
    UPDATE = "interviews:update"      # Update interview status
    DELETE = "interviews:delete"      # Delete own interviews (soft delete - future)
    
    # Special operations
    EXPORT = "interviews:export"      # Export interviews to documents
    
    @classmethod
    def values(cls) -> list[str]:
        """Get all permission values as a list of strings"""
        return [permission.value for permission in cls]
    
    @classmethod
    def is_valid(cls, permission: str) -> bool:
        """Check if a string is a valid permission"""
        return permission in cls.values()
    
    def __str__(self) -> str:
        return self.value
```

### 2. TokenPayload Actualizado (app/services/token_validator.py - UPDATE)

```python
from pydantic import BaseModel, Field
from typing import List, Optional


class TokenPayload(BaseModel):
    """
    JWT Token Payload
    
    Represents the decoded JWT token with user information and permissions.
    """
    user_id: str = Field(description="User ID from JWT sub claim")
    email: str = Field(description="User email")
    organization_id: str = Field(description="Organization ID")
    roles: List[str] = Field(default_factory=list, description="User roles")
    permissions: List[str] = Field(default_factory=list, description="User permissions")  # NEW
    
    # Additional claims
    exp: Optional[int] = Field(default=None, description="Expiration timestamp")
    iat: Optional[int] = Field(default=None, description="Issued at timestamp")
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission"""
        return permission in self.permissions
    
    def has_any_permission(self, permissions: List[str]) -> bool:
        """Check if user has any of the specified permissions"""
        return any(perm in self.permissions for perm in permissions)
    
    def has_all_permissions(self, permissions: List[str]) -> bool:
        """Check if user has all of the specified permissions"""
        return all(perm in self.permissions for perm in permissions)
```

### 3. Extracción de Permisos en Auth Middleware (app/middleware/auth_middleware.py - UPDATE)

```python
# En la función que decodifica el JWT:

async def get_current_user(
    authorization: str = Header(None)
) -> TokenPayload:
    """
    Dependency to get current authenticated user from JWT
    
    Extracts user information and permissions from JWT token
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid authorization header"
        )
    
    token = authorization.replace("Bearer ", "")
    
    try:
        # Decode JWT
        payload = decode_jwt(token)  # Your existing JWT decode logic
        
        # Extract permissions from JWT (NEW)
        permissions = payload.get("permissions", [])
        
        # Validate permissions format
        if not isinstance(permissions, list):
            logger.warning(f"Invalid permissions format in JWT for user {payload.get('sub')}: {type(permissions)}")
            permissions = []
        
        # Filter out invalid permissions
        valid_permissions = [
            perm for perm in permissions 
            if isinstance(perm, str) and InterviewPermission.is_valid(perm)
        ]
        
        if len(valid_permissions) < len(permissions):
            logger.warning(
                f"JWT contains invalid permissions for user {payload.get('sub')}: "
                f"Valid: {valid_permissions}, Invalid: {set(permissions) - set(valid_permissions)}"
            )
        
        return TokenPayload(
            user_id=payload.get("sub"),
            email=payload.get("email"),
            organization_id=payload.get("organization_id"),
            roles=payload.get("roles", []),
            permissions=valid_permissions,  # NEW
            exp=payload.get("exp"),
            iat=payload.get("iat")
        )
        
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
```

### 4. Permission Dependencies (app/dependencies/permissions.py - NEW)

```python
"""
Permission Dependencies
FastAPI dependencies for validating user permissions
"""
from fastapi import Depends, HTTPException
from typing import List, Callable
from app.services.token_validator import TokenPayload, get_current_user
from app.models.permissions import InterviewPermission
import logging

logger = logging.getLogger(__name__)


def require_permission(permission: str) -> Callable:
    """
    Dependency factory to require a specific permission
    
    Usage:
        @router.post("/start")
        async def start_interview(
            current_user: TokenPayload = Depends(get_current_user),
            _: None = Depends(require_permission(InterviewPermission.CREATE))
        ):
            ...
    
    Args:
        permission: Required permission (use InterviewPermission enum)
        
    Returns:
        Dependency function that validates the permission
        
    Raises:
        HTTPException 403: If user doesn't have the required permission
    """
    async def permission_checker(
        current_user: TokenPayload = Depends(get_current_user)
    ) -> None:
        if not current_user.has_permission(permission):
            logger.warning(
                f"Permission denied for user {current_user.user_id}: "
                f"Required '{permission}', Has {current_user.permissions}"
            )
            raise HTTPException(
                status_code=403,
                detail={
                    "status": "error",
                    "code": 403,
                    "message": "Insufficient permissions",
                    "errors": [
                        {
                            "field": "permissions",
                            "error": f"Required permission: {permission}",
                            "user_permissions": current_user.permissions
                        }
                    ]
                }
            )
    
    return permission_checker


def require_any_permission(permissions: List[str]) -> Callable:
    """
    Dependency factory to require ANY of the specified permissions (OR logic)
    
    Usage:
        @router.get("/{id}")
        async def get_interview(
            _: None = Depends(require_any_permission([
                InterviewPermission.READ,
                InterviewPermission.READ_ALL
            ]))
        ):
            ...
    
    Args:
        permissions: List of acceptable permissions
        
    Returns:
        Dependency function that validates at least one permission exists
    """
    async def permission_checker(
        current_user: TokenPayload = Depends(get_current_user)
    ) -> None:
        if not current_user.has_any_permission(permissions):
            logger.warning(
                f"Permission denied for user {current_user.user_id}: "
                f"Required ANY of {permissions}, Has {current_user.permissions}"
            )
            raise HTTPException(
                status_code=403,
                detail={
                    "status": "error",
                    "code": 403,
                    "message": "Insufficient permissions",
                    "errors": [
                        {
                            "field": "permissions",
                            "error": f"Required any of: {', '.join(permissions)}",
                            "user_permissions": current_user.permissions
                        }
                    ]
                }
            )
    
    return permission_checker


def require_all_permissions(permissions: List[str]) -> Callable:
    """
    Dependency factory to require ALL of the specified permissions (AND logic)
    
    Usage:
        @router.post("/admin-action")
        async def admin_action(
            _: None = Depends(require_all_permissions([
                InterviewPermission.READ_ALL,
                InterviewPermission.UPDATE
            ]))
        ):
            ...
    
    Args:
        permissions: List of required permissions
        
    Returns:
        Dependency function that validates all permissions exist
    """
    async def permission_checker(
        current_user: TokenPayload = Depends(get_current_user)
    ) -> None:
        if not current_user.has_all_permissions(permissions):
            missing = set(permissions) - set(current_user.permissions)
            logger.warning(
                f"Permission denied for user {current_user.user_id}: "
                f"Required ALL of {permissions}, Missing {missing}"
            )
            raise HTTPException(
                status_code=403,
                detail={
                    "status": "error",
                    "code": 403,
                    "message": "Insufficient permissions",
                    "errors": [
                        {
                            "field": "permissions",
                            "error": f"Required all of: {', '.join(permissions)}",
                            "missing_permissions": list(missing),
                            "user_permissions": current_user.permissions
                        }
                    ]
                }
            )
    
    return permission_checker
```

### 5. Validación de Ownership (app/dependencies/permissions.py - ADD)

```python
async def require_interview_ownership(
    interview_id: str,
    current_user: TokenPayload,
    db: AsyncSession
) -> bool:
    """
    Helper function to validate interview ownership
    
    Returns True if:
    - User owns the interview (employee_id matches user_id), OR
    - User has interviews:read_all permission (admin/manager)
    
    Args:
        interview_id: Interview UUID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        bool: True if user has access, False otherwise
    """
    from app.repositories.interview_repository import InterviewRepository
    from uuid import UUID
    
    # Admins with read_all can access any interview
    if current_user.has_permission(InterviewPermission.READ_ALL):
        return True
    
    # Check if interview belongs to user
    interview_repo = InterviewRepository(db)
    interview = await interview_repo.get_by_id(
        UUID(interview_id),
        UUID(current_user.user_id)
    )
    
    return interview is not None
```

## Data Models

### Permission Mapping Table

| Endpoint | HTTP Method | Required Permission | Ownership Check |
|----------|-------------|---------------------|-----------------|
| `/interviews/start` | POST | `interviews:create` | N/A (creates new) |
| `/interviews/continue` | POST | `interviews:create` | ✅ Yes (must own interview) |
| `/interviews` | GET | `interviews:read` | ✅ Auto-filter by user |
| `/interviews` | GET | `interviews:read_all` | ❌ No (sees all in org) |
| `/interviews/{id}` | GET | `interviews:read` | ✅ Yes (must own) |
| `/interviews/{id}` | GET | `interviews:read_all` | ❌ No (can see any) |
| `/interviews/{id}` | PATCH | `interviews:update` | ✅ Yes (must own) |
| `/interviews/export` | POST | `interviews:export` | ✅ Yes (must own) |

### Permission Hierarchy

```
interviews:read_all  (Admin/Manager)
    ↓ includes
interviews:read      (Regular User)
    ↓ requires
interviews:create    (Can create interviews)
```

**Note:** `interviews:read_all` implicitly grants access to all `interviews:read` operations.

## Error Handling

### Permission Denied Response (403)

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

### Interview Access Denied (403)

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

### No Permissions in JWT (403)

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

## Testing Strategy

### 1. Unit Tests

**Test Permission Dependencies:**
```python
# tests/unit/dependencies/test_permissions.py

async def test_require_permission_with_valid_permission():
    """Test that user with correct permission can access"""
    user = TokenPayload(
        user_id="123",
        email="test@example.com",
        organization_id="org-1",
        permissions=["interviews:create"]
    )
    
    checker = require_permission(InterviewPermission.CREATE)
    result = await checker(current_user=user)
    assert result is None  # No exception raised

async def test_require_permission_without_permission():
    """Test that user without permission gets 403"""
    user = TokenPayload(
        user_id="123",
        email="test@example.com",
        organization_id="org-1",
        permissions=[]
    )
    
    checker = require_permission(InterviewPermission.CREATE)
    with pytest.raises(HTTPException) as exc_info:
        await checker(current_user=user)
    
    assert exc_info.value.status_code == 403
```

### 2. Integration Tests

**Test Endpoint Protection:**
```python
# tests/integration/test_interview_authorization.py

async def test_start_interview_without_permission(client, jwt_token_no_permissions):
    """Test that starting interview without permission fails"""
    response = await client.post(
        "/api/v1/interviews/start",
        headers={"Authorization": f"Bearer {jwt_token_no_permissions}"},
        json={"language": "es"}
    )
    
    assert response.status_code == 403
    assert "Insufficient permissions" in response.json()["message"]

async def test_list_interviews_with_read_all_permission(client, jwt_token_admin):
    """Test that admin with read_all can see all interviews"""
    response = await client.get(
        "/api/v1/interviews",
        headers={"Authorization": f"Bearer {jwt_token_admin}"}
    )
    
    assert response.status_code == 200
    # Should see interviews from multiple users
```

### 3. Functional Tests (E2E)

**Test Complete Authorization Flow:**
```python
async def test_complete_interview_flow_with_permissions():
    """Test full interview lifecycle with proper permissions"""
    # 1. User with interviews:create starts interview
    # 2. User continues interview (ownership validated)
    # 3. User lists their interviews (only sees own)
    # 4. Admin lists interviews (sees all in organization)
    # 5. User exports their interview
    # 6. User tries to access another user's interview (denied)
```

## Configuration

### Environment Variables

No new environment variables required. Permissions come from JWT.

### JWT Payload Structure

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

## Migration Plan

### Phase 1: Setup (No Breaking Changes)

1. Create `app/models/permissions.py` with enum
2. Update `TokenPayload` to include permissions field
3. Update auth middleware to extract permissions from JWT
4. Create `app/dependencies/permissions.py` with validation functions

### Phase 2: Protect Endpoints (Breaking Change)

1. Add permission dependencies to all interview endpoints
2. Update OpenAPI documentation
3. Test with mock JWTs containing permissions

### Phase 3: Coordinate with Auth Service

1. Share permission list with `svc-users-python` team
2. Auth service adds permissions to JWT based on user roles
3. Test end-to-end with real JWTs

### Phase 4: Rollout

1. Deploy to staging with feature flag
2. Test with real users
3. Deploy to production
4. Monitor logs for permission denials

## Design Decisions

### 1. ¿Por qué usar Dependencies en lugar de decoradores?

**Decisión:** Usar FastAPI Dependencies (`Depends()`)

**Razones:**
- ✅ Idiomático en FastAPI
- ✅ Se integra con OpenAPI/Swagger automáticamente
- ✅ Permite composición de dependencies
- ✅ Type-safe con IDE support

**Alternativa descartada:** Decoradores custom
- ❌ No se integran con OpenAPI
- ❌ Más difícil de testear
- ❌ No es el patrón estándar de FastAPI

### 2. ¿Por qué `interviews:read_all` en lugar de roles?

**Decisión:** Usar permisos granulares, no roles

**Razones:**
- ✅ Más flexible (un usuario puede tener permisos específicos)
- ✅ Consistente con `svc-organizations-php`
- ✅ Permite control fino (ej: puede leer todo pero no exportar)
- ✅ Roles se mapean a permisos en el auth service

**Ejemplo:**
```
Role: Manager → Permissions: [interviews:read_all, interviews:export]
Role: User → Permissions: [interviews:create, interviews:read]
```

### 3. ¿Por qué validar ownership en el service layer?

**Decisión:** Validar ownership tanto en dependency como en service

**Razones:**
- ✅ Defense in depth (doble validación)
- ✅ Dependency valida permiso general
- ✅ Service valida ownership específico
- ✅ Más seguro si alguien olvida agregar dependency

### 4. ¿Por qué no usar RBAC (Role-Based Access Control)?

**Decisión:** Usar PBAC (Permission-Based Access Control)

**Razones:**
- ✅ Más granular que roles
- ✅ Consistente con backend PHP
- ✅ Roles se convierten en permisos en el JWT
- ✅ Más fácil de auditar (sabes exactamente qué puede hacer)

## Summary

Este diseño implementa autorización basada en permisos siguiendo el patrón de `svc-organizations-php`:

**✅ Consistente con el ecosistema:**
- Mismo formato de permisos (`resource:action`)
- Permisos vienen en el JWT
- Validación en cada endpoint

**✅ Seguro:**
- Validación de permisos en dependencies
- Validación de ownership en service layer
- Logs de todos los intentos de acceso denegado

**✅ Mantenible:**
- Enum para permisos (type-safe)
- Dependencies reutilizables
- Fácil de testear

**✅ Escalable:**
- Fácil agregar nuevos permisos
- Fácil agregar nuevos endpoints protegidos
- No requiere cambios en base de datos

