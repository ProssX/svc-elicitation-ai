"""
Interview Permissions Enum

Defines all available permissions for interview operations following the
resource:action pattern consistent with svc-organizations-php.
"""
from enum import Enum


class InterviewPermission(str, Enum):
    """
    Permission definitions for interview operations.
    
    Format: resource:action
    - resource: The entity being accessed (interviews)
    - action: The operation being performed (create, read, update, delete, export)
    
    Permissions:
    - CREATE: Allows creating new interviews and continuing existing ones
    - READ: Allows reading own interviews only
    - READ_ALL: Allows reading all interviews in the organization (admin/manager)
    - UPDATE: Allows updating interview status (own interviews only)
    - DELETE: Allows deleting own interviews (soft delete - future implementation)
    - EXPORT: Allows exporting interviews to documents (own interviews only)
    
    Special permissions:
    - interviews:read_all: This is a special permission that grants access to all
      interviews in the organization, not just the user's own interviews. Users with
      only interviews:read can only see their own interviews.
    """
    
    # Core CRUD permissions
    CREATE = "interviews:create"
    """Create new interviews and continue existing ones"""
    
    READ = "interviews:read"
    """Read own interviews"""
    
    READ_ALL = "interviews:read_all"
    """Read all interviews in organization (admin/manager only)"""
    
    UPDATE = "interviews:update"
    """Update interview status (own interviews only)"""
    
    DELETE = "interviews:delete"
    """Delete own interviews (soft delete - future implementation)"""
    
    # Special operations
    EXPORT = "interviews:export"
    """Export interviews to documents (own interviews only)"""
    
    @classmethod
    def values(cls) -> list[str]:
        """
        Get all permission values as a list of strings.
        
        Returns:
            list[str]: List of all permission string values
            
        Example:
            >>> InterviewPermission.values()
            ['interviews:create', 'interviews:read', 'interviews:read_all', ...]
        """
        return [permission.value for permission in cls]
    
    @classmethod
    def is_valid(cls, permission: str) -> bool:
        """
        Check if a string is a valid permission.
        
        Args:
            permission: Permission string to validate
            
        Returns:
            bool: True if the permission is valid, False otherwise
            
        Example:
            >>> InterviewPermission.is_valid("interviews:create")
            True
            >>> InterviewPermission.is_valid("invalid:permission")
            False
        """
        return permission in cls.values()
    
    def __str__(self) -> str:
        """Return the string value of the permission"""
        return self.value
