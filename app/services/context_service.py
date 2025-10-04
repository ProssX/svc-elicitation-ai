"""
Context Service
Manages user context and integration with backend
"""
import json
import httpx
from typing import Optional, Dict
from pathlib import Path
from app.config import settings


class ContextService:
    """Service to get user context from backend or mock data"""
    
    def __init__(self):
        """Initialize the context service"""
        self.backend_url = settings.backend_php_url
        self.mock_data_path = Path(__file__).parent.parent.parent / "data" / "mock_users.json"
        
        # Load mock data
        with open(self.mock_data_path, "r", encoding="utf-8") as f:
            self.mock_data = json.load(f)
    
    async def get_user_context(self, user_id: Optional[str] = None) -> Dict:
        """
        Get user context information
        
        Args:
            user_id: User ID (optional, uses mock if not provided)
            
        Returns:
            dict: User context information
        """
        # For MVP, use mock data
        # In production, this would call the backend PHP service
        
        if not user_id:
            # Return default user
            user_id = "user-123"
        
        # Try to get from mock data
        user_data = self.mock_data.get("users", {}).get(user_id)
        
        if user_data:
            return user_data
        
        # If user not found in mock, return default
        return self.mock_data.get("users", {}).get("user-123", {
            "id": user_id,
            "name": "Usuario Desconocido",
            "role": "Usuario",
            "organization": "Organización",
            "technical_level": "unknown"
        })
    
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


