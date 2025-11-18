"""
Permission Dependencies

FastAPI dependencies for validating user permissions on protected endpoints.
Provides reusable permission validation functions following the ProssX standard.
"""
import logging
from typing import Callable
from uuid import UUID
from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.token_validator import TokenPayload
from app.middleware.auth_middleware import get_current_user
from app.models.permissions import InterviewPermission
from app.database import get_db


logger = logging.getLogger(__name__)


def _log_access_denied(
    user_id: str,
    endpoint: str,
    method: str,
    required_permission: str | list[str],
    user_permissions: list[str],
    reason: str = "insufficient_permissions"
) -> None:
    """
    Log access denied attempts with consistent format.
    
    Args:
        user_id: User ID attempting access
        endpoint: Endpoint path being accessed
        method: HTTP method (GET, POST, etc.)
        required_permission: Permission(s) required for access
        user_permissions: Permissions the user currently has
        reason: Reason for denial (default: insufficient_permissions)
    """
    logger.warning(
        f"ACCESS_DENIED | user_id={user_id} | endpoint={method} {endpoint} | "
        f"required={required_permission} | has={user_permissions} | reason={reason}"
    )


def _log_access_granted(
    user_id: str,
    endpoint: str,
    method: str,
    permission: str | list[str],
    resource_type: str = "endpoint"
) -> None:
    """
    Log successful access to sensitive resources with consistent format.
    
    Args:
        user_id: User ID accessing resource
        endpoint: Endpoint path being accessed
        method: HTTP method (GET, POST, etc.)
        permission: Permission(s) validated for access
        resource_type: Type of resource being accessed (default: endpoint)
    """
    logger.info(
        f"ACCESS_GRANTED | user_id={user_id} | endpoint={method} {endpoint} | "
        f"permission={permission} | resource_type={resource_type}"
    )


def require_permission(permission: str) -> Callable:
    """
    Dependency factory to require a specific permission.
    
    Creates a FastAPI dependency that validates the user has the required permission.
    Returns HTTP 403 with ProssX standard error format if permission is missing.
    
    Usage:
        @router.post("/interviews/start")
        async def start_interview(
            current_user: TokenPayload = Depends(get_current_user),
            _: None = Depends(require_permission(InterviewPermission.CREATE))
        ):
            # User has interviews:create permission
            ...
    
    Args:
        permission: Required permission string (use InterviewPermission enum)
        
    Returns:
        Callable: Dependency function that validates the permission
        
    Raises:
        HTTPException(403): If user doesn't have the required permission
    """
    async def permission_checker(
        request: Request,
        current_user: TokenPayload = Depends(get_current_user)
    ) -> None:
        """
        Check if current user has the required permission.
        
        Args:
            request: FastAPI request object (for endpoint logging)
            current_user: Authenticated user from JWT token
            
        Raises:
            HTTPException(403): If permission check fails
        """
        endpoint = request.url.path
        method = request.method
        
        if not current_user.has_permission(permission):
            _log_access_denied(
                user_id=current_user.user_id,
                endpoint=endpoint,
                method=method,
                required_permission=permission,
                user_permissions=current_user.permissions
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
        
        _log_access_granted(
            user_id=current_user.user_id,
            endpoint=endpoint,
            method=method,
            permission=permission
        )
    
    return permission_checker


def require_any_permission(permissions: list[str]) -> Callable:
    """
    Dependency factory to require ANY of the specified permissions (OR logic).
    
    Creates a FastAPI dependency that validates the user has at least one of the
    required permissions. Useful for endpoints that can be accessed by users with
    different permission levels.
    
    Usage:
        @router.get("/interviews/{id}")
        async def get_interview(
            _: None = Depends(require_any_permission([
                InterviewPermission.READ,
                InterviewPermission.READ_ALL
            ]))
        ):
            # User has either interviews:read OR interviews:read_all
            ...
    
    Args:
        permissions: List of acceptable permissions (user needs at least one)
        
    Returns:
        Callable: Dependency function that validates at least one permission exists
        
    Raises:
        HTTPException(403): If user doesn't have any of the required permissions
    """
    async def permission_checker(
        request: Request,
        current_user: TokenPayload = Depends(get_current_user)
    ) -> None:
        """
        Check if current user has any of the required permissions.
        
        Args:
            request: FastAPI request object (for endpoint logging)
            current_user: Authenticated user from JWT token
            
        Raises:
            HTTPException(403): If permission check fails
        """
        endpoint = request.url.path
        method = request.method
        
        if not current_user.has_any_permission(permissions):
            _log_access_denied(
                user_id=current_user.user_id,
                endpoint=endpoint,
                method=method,
                required_permission=f"ANY of [{', '.join(permissions)}]",
                user_permissions=current_user.permissions
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
        
        _log_access_granted(
            user_id=current_user.user_id,
            endpoint=endpoint,
            method=method,
            permission=f"ANY of [{', '.join(permissions)}]"
        )
    
    return permission_checker


def require_all_permissions(permissions: list[str]) -> Callable:
    """
    Dependency factory to require ALL of the specified permissions (AND logic).
    
    Creates a FastAPI dependency that validates the user has all of the required
    permissions. Useful for endpoints that require multiple permission levels.
    
    Usage:
        @router.post("/admin-action")
        async def admin_action(
            _: None = Depends(require_all_permissions([
                InterviewPermission.READ_ALL,
                InterviewPermission.UPDATE
            ]))
        ):
            # User has BOTH interviews:read_all AND interviews:update
            ...
    
    Args:
        permissions: List of required permissions (user needs all of them)
        
    Returns:
        Callable: Dependency function that validates all permissions exist
        
    Raises:
        HTTPException(403): If user is missing any of the required permissions
    """
    async def permission_checker(
        request: Request,
        current_user: TokenPayload = Depends(get_current_user)
    ) -> None:
        """
        Check if current user has all of the required permissions.
        
        Args:
            request: FastAPI request object (for endpoint logging)
            current_user: Authenticated user from JWT token
            
        Raises:
            HTTPException(403): If permission check fails
        """
        endpoint = request.url.path
        method = request.method
        
        if not current_user.has_all_permissions(permissions):
            missing = set(permissions) - set(current_user.permissions)
            _log_access_denied(
                user_id=current_user.user_id,
                endpoint=endpoint,
                method=method,
                required_permission=f"ALL of [{', '.join(permissions)}]",
                user_permissions=current_user.permissions,
                reason=f"missing_{len(missing)}_permissions"
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
        
        _log_access_granted(
            user_id=current_user.user_id,
            endpoint=endpoint,
            method=method,
            permission=f"ALL of [{', '.join(permissions)}]"
        )
    
    return permission_checker


async def require_interview_ownership(
    interview_id: str,
    request: Request,
    current_user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> bool:
    """
    Dependency to validate interview ownership or admin access.
    
    Validates that the current user either:
    1. Owns the interview (employee_id matches user_id), OR
    2. Has interviews:read_all permission (admin/manager access)
    
    This dependency should be used in combination with permission checks to ensure
    users can only access their own interviews unless they have elevated permissions.
    
    Usage:
        @router.get("/interviews/{interview_id}")
        async def get_interview(
            interview_id: str,
            current_user: TokenPayload = Depends(get_current_user),
            _: None = Depends(require_permission(InterviewPermission.READ)),
            has_access: bool = Depends(require_interview_ownership)
        ):
            if not has_access:
                raise HTTPException(status_code=403, detail="Access denied")
            ...
    
    Args:
        interview_id: Interview UUID as string
        request: FastAPI request object (for endpoint logging)
        current_user: Authenticated user from JWT token
        db: Database session
        
    Returns:
        bool: True if user has access to the interview, False otherwise
        
    Raises:
        HTTPException(404): If interview doesn't exist
        HTTPException(403): If user doesn't have access to the interview
    """
    from app.repositories.interview_repository import InterviewRepository
    
    endpoint = request.url.path
    method = request.method
    
    try:
        interview_uuid = UUID(interview_id)
        user_uuid = UUID(current_user.user_id)
    except ValueError as e:
        logger.error(f"Invalid UUID format: {e}")
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "code": 400,
                "message": "Invalid ID format",
                "errors": [
                    {
                        "field": "interview_id",
                        "error": "Invalid UUID format"
                    }
                ]
            }
        )
    
    # Admins with read_all can access any interview in their organization
    if current_user.has_permission(InterviewPermission.READ_ALL):
        _log_access_granted(
            user_id=current_user.user_id,
            endpoint=endpoint,
            method=method,
            permission=InterviewPermission.READ_ALL,
            resource_type=f"interview:{interview_id}"
        )
        return True
    
    # Check if interview belongs to user
    interview_repo = InterviewRepository(db)
    interview = await interview_repo.get_by_id(interview_uuid, user_uuid)
    
    if interview is None:
        # Interview either doesn't exist or doesn't belong to user
        # Check if interview exists at all (for proper error message)
        from sqlalchemy import select
        from app.models.db_models import Interview
        
        stmt = select(Interview).where(Interview.id_interview == interview_uuid)
        result = await db.execute(stmt)
        exists = result.scalar_one_or_none() is not None
        
        if not exists:
            logger.warning(
                f"RESOURCE_NOT_FOUND | user_id={current_user.user_id} | "
                f"endpoint={method} {endpoint} | resource=interview:{interview_id}"
            )
            raise HTTPException(
                status_code=404,
                detail={
                    "status": "error",
                    "code": 404,
                    "message": "Interview not found",
                    "errors": [
                        {
                            "field": "interview_id",
                            "error": "Interview does not exist"
                        }
                    ]
                }
            )
        else:
            _log_access_denied(
                user_id=current_user.user_id,
                endpoint=endpoint,
                method=method,
                required_permission="ownership or interviews:read_all",
                user_permissions=current_user.permissions,
                reason="not_owner"
            )
            raise HTTPException(
                status_code=403,
                detail={
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
            )
    
    _log_access_granted(
        user_id=current_user.user_id,
        endpoint=endpoint,
        method=method,
        permission="ownership",
        resource_type=f"interview:{interview_id}"
    )
    return True
