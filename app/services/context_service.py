"""
Context Service
Manages user context and integration with backend
"""
import httpx
from typing import Optional, Dict
from app.config import settings


class ContextService:
    """Service to get user context from backend"""
    
    def __init__(self):
        """Initialize the context service"""
        self.backend_url = settings.backend_php_url
    
    async def get_user_context(self, user_id: str) -> Dict:
        """
        Get user context information from backend service
        
        Args:
            user_id: User ID from JWT token
            
        Returns:
            dict: User context information with name, role, organization, technical_level
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.backend_url}/users/{user_id}",
                    timeout=5.0
                )
                if response.status_code == 200:
                    user_data = response.json()
                    # Return user data in expected format
                    return {
                        "id": user_data.get("id", user_id),
                        "name": user_data.get("name", "Usuario"),
                        "email": user_data.get("email", ""),
                        "role": user_data.get("role", "Empleado"),
                        "organization": user_data.get("organization", "Organización"),
                        "organization_id": user_data.get("organization_id", ""),
                        "technical_level": user_data.get("technical_level", "unknown")
                    }
        except Exception as e:
            print(f"Error fetching user context: {e}")
        
        # Fallback to minimal context if backend unavailable
        return {
            "id": user_id,
            "name": "Usuario",
            "role": "Empleado",
            "organization": "Organización",
            "technical_level": "unknown"
        }
    
    async def get_organization_info(self, organization_id: str) -> Optional[Dict]:
        """
        Get organization information from backend
        
        Args:
            organization_id: Organization UUID
            
        Returns:
            dict: Organization info or None if error
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.backend_url}/organizations/{organization_id}",
                    timeout=5.0
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            print(f"Error fetching organization: {e}")
        
        return None
    
    async def get_role_info(self, organization_id: str, role_id: str) -> Optional[Dict]:
        """
        Get role information from backend
        
        Args:
            organization_id: Organization UUID
            role_id: Role UUID
            
        Returns:
            dict: Role info or None if error
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.backend_url}/organizations/{organization_id}/roles/{role_id}",
                    timeout=5.0
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            print(f"Error fetching role: {e}")
        
        return None


# Global context service instance
_context_service = None


def get_context_service() -> ContextService:
    """Get or create the global context service instance"""
    global _context_service
    if _context_service is None:
        _context_service = ContextService()
    return _context_service


