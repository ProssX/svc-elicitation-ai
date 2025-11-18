"""
HTTP Client for svc-organizations-php Backend API

Handles communication with the PHP backend service for retrieving
employee, organization, role, and process data.
"""
import httpx
import asyncio
from typing import Optional, List, Dict, Any
from uuid import UUID
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class BackendClientError(Exception):
    """Base exception for backend client errors"""
    pass


class BackendClient:
    """
    HTTP client for svc-organizations-php API
    
    Implements retry logic with exponential backoff and timeout handling
    for reliable communication with the backend service.
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 5.0,
        max_retries: int = 2
    ):
        """
        Initialize backend client
        
        Args:
            base_url: Base URL for backend API (defaults to settings)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.base_url = (base_url or settings.backend_php_url).rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        auth_token: str,
        params: Optional[Dict[str, Any]] = None,
        retry_count: int = 0
    ) -> Optional[Dict[str, Any]]:
        """
        Make HTTP request with retry logic and exponential backoff
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            auth_token: JWT authentication token
            params: Query parameters
            retry_count: Current retry attempt number
            
        Returns:
            Response data as dictionary, or None if request fails
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Accept": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params
                )
                
                # Log non-2xx responses
                if response.status_code >= 400:
                    logger.warning(
                        f"[BACKEND] API error: {method} {endpoint} returned {response.status_code}",
                        extra={
                            "method": method,
                            "endpoint": endpoint,
                            "status_code": response.status_code,
                            "success": False,
                            "retry_count": retry_count
                        }
                    )
                    
                    # Don't retry on 4xx errors (client errors)
                    if 400 <= response.status_code < 500:
                        logger.error(
                            f"[BACKEND] Client error (4xx) - not retrying: {method} {endpoint}",
                            extra={
                                "method": method,
                                "endpoint": endpoint,
                                "status_code": response.status_code,
                                "error_category": "client_error"
                            }
                        )
                        return None
                    
                    # Retry on 5xx errors
                    if retry_count < self.max_retries:
                        logger.info(
                            f"[BACKEND] Server error (5xx) - retrying: {method} {endpoint}",
                            extra={
                                "method": method,
                                "endpoint": endpoint,
                                "status_code": response.status_code,
                                "retry_count": retry_count + 1,
                                "max_retries": self.max_retries
                            }
                        )
                        return await self._retry_request(
                            method, endpoint, auth_token, params, retry_count
                        )
                    return None
                
                logger.debug(
                    f"[BACKEND] API success: {method} {endpoint}",
                    extra={
                        "method": method,
                        "endpoint": endpoint,
                        "status_code": response.status_code,
                        "success": True
                    }
                )
                return response.json()
                
        except httpx.TimeoutException:
            logger.warning(
                f"[BACKEND] API timeout: {method} {endpoint} "
                f"(attempt {retry_count + 1}/{self.max_retries + 1})",
                extra={
                    "method": method,
                    "endpoint": endpoint,
                    "error_type": "timeout",
                    "retry_count": retry_count,
                    "timeout_seconds": self.timeout,
                    "success": False
                }
            )
            if retry_count < self.max_retries:
                return await self._retry_request(
                    method, endpoint, auth_token, params, retry_count
                )
            logger.error(
                f"[BACKEND] API timeout - max retries exceeded: {method} {endpoint}",
                extra={
                    "method": method,
                    "endpoint": endpoint,
                    "error_type": "timeout_max_retries",
                    "max_retries": self.max_retries
                }
            )
            return None
            
        except httpx.RequestError as e:
            logger.error(
                f"[BACKEND] API request error: {method} {endpoint} - {type(e).__name__}: {str(e)}",
                extra={
                    "method": method,
                    "endpoint": endpoint,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "retry_count": retry_count,
                    "success": False
                }
            )
            if retry_count < self.max_retries:
                return await self._retry_request(
                    method, endpoint, auth_token, params, retry_count
                )
            return None
            
        except Exception as e:
            logger.error(
                f"[BACKEND] Unexpected error: {method} {endpoint} - {type(e).__name__}: {str(e)}",
                extra={
                    "method": method,
                    "endpoint": endpoint,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "success": False
                }
            )
            return None
    
    async def _retry_request(
        self,
        method: str,
        endpoint: str,
        auth_token: str,
        params: Optional[Dict[str, Any]],
        retry_count: int
    ) -> Optional[Dict[str, Any]]:
        """
        Retry request with exponential backoff
        
        Args:
            method: HTTP method
            endpoint: API endpoint path
            auth_token: JWT authentication token
            params: Query parameters
            retry_count: Current retry attempt number
            
        Returns:
            Response data or None
        """
        # Exponential backoff: 0.5s, 1s, 2s, etc.
        wait_time = 0.5 * (2 ** retry_count)
        await asyncio.sleep(wait_time)
        
        return await self._make_request(
            method=method,
            endpoint=endpoint,
            auth_token=auth_token,
            params=params,
            retry_count=retry_count + 1
        )
    
    async def get_employee(
        self,
        employee_id: UUID,
        organization_id: str,
        auth_token: str
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch employee details from backend
        
        Args:
            employee_id: UUID of the employee
            organization_id: ID of the organization the employee belongs to
            auth_token: JWT authentication token
            
        Returns:
            Employee data dictionary or None if not found/error
            
        Example response:
            {
                "id": "uuid",
                "firstName": "John",
                "lastName": "Doe",
                "isActive": true,
                "organizationId": "org-uuid"
            }
        """
        logger.info(f"Fetching employee {employee_id} from organization {organization_id}")
        
        result = await self._make_request(
            method="GET",
            endpoint=f"/organizations/{organization_id}/employees/{employee_id}",
            auth_token=auth_token
        )
        
        if result:
            # Extract data from ProssX standard response format
            if isinstance(result, dict) and "data" in result:
                employee_data = result["data"]
                logger.info(f"Successfully fetched employee {employee_id}")
                return employee_data
            else:
                logger.info(f"Successfully fetched employee {employee_id}")
                return result
        else:
            logger.warning(f"Failed to fetch employee {employee_id}")
            return None
    
    async def get_organization(
        self,
        organization_id: str,
        auth_token: str
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch organization details from backend
        
        Args:
            organization_id: ID of the organization
            auth_token: JWT authentication token
            
        Returns:
            Organization data dictionary or None if not found/error
            
        Example response:
            {
                "id": "org-uuid",
                "businessName": "Acme Corp",
                "mission": "...",
                "vision": "...",
                "objective": "...",
                "businessType": "technology"
            }
        """
        logger.info(f"Fetching organization {organization_id} from backend")
        
        result = await self._make_request(
            method="GET",
            endpoint=f"/organizations/{organization_id}",
            auth_token=auth_token
        )
        
        if result:
            # Extract data from ProssX standard response format
            if isinstance(result, dict) and "data" in result:
                organization_data = result["data"]
                logger.info(f"Successfully fetched organization {organization_id}")
                return organization_data
            else:
                logger.info(f"Successfully fetched organization {organization_id}")
                return result
        else:
            logger.warning(f"Failed to fetch organization {organization_id}")
            
        return None
    
    async def get_role(
        self,
        role_id: str,
        organization_id: str,
        auth_token: str
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch role details from backend
        
        Args:
            role_id: UUID of the role
            organization_id: ID of the organization the role belongs to
            auth_token: JWT authentication token
            
        Returns:
            Role data dictionary or None if not found/error
            
        Example response:
            {
                "id": "role-uuid",
                "name": "Product Manager",
                "description": "Manages product development"
            }
        """
        logger.info(f"Fetching role {role_id} from organization {organization_id}")
        
        result = await self._make_request(
            method="GET",
            endpoint=f"/organizations/{organization_id}/roles/{role_id}",
            auth_token=auth_token
        )
        
        if result:
            # Extract data from ProssX standard response format
            if isinstance(result, dict) and "data" in result:
                role_data = result["data"]
                logger.info(f"Successfully fetched role {role_id}")
                return role_data
            else:
                logger.info(f"Successfully fetched role {role_id}")
                return result
        else:
            logger.warning(f"Failed to fetch role {role_id}")
            return None
    
    async def get_organization_processes(
        self,
        organization_id: str,
        auth_token: str,
        active_only: bool = True,
        limit: int = 20,
        page: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Fetch processes for an organization with pagination
        
        Args:
            organization_id: ID of the organization
            auth_token: JWT authentication token
            active_only: Filter for active processes only
            limit: Maximum number of processes to return per page
            page: Page number for pagination
            
        Returns:
            List of process data dictionaries (empty list on error)
            
        Example response item:
            {
                "id": "process-uuid",
                "name": "Customer Onboarding",
                "type": "operational",
                "typeLabel": "Operational",
                "isActive": true,
                "createdAt": "2024-01-01T00:00:00Z",
                "updatedAt": "2024-01-15T00:00:00Z"
            }
        """
        logger.info(
            f"Fetching processes for organization {organization_id} "
            f"(active_only={active_only}, limit={limit}, page={page})"
        )
        
        params = {
            "limit": limit,
            "page": page
        }
        
        if active_only:
            params["isActive"] = "true"
        
        result = await self._make_request(
            method="GET",
            endpoint=f"/organizations/{organization_id}/processes",
            auth_token=auth_token,
            params=params
        )
        
        if result:
            # Handle both paginated and non-paginated responses
            if isinstance(result, dict) and "data" in result:
                processes = result["data"]
                # Ensure processes is a list
                if not isinstance(processes, list):
                    processes = [] if processes is None else [processes]
            elif isinstance(result, list):
                processes = result
            else:
                processes = []
            
            logger.info(
                f"Successfully fetched {len(processes)} processes "
                f"for organization {organization_id}"
            )
            return processes
        else:
            logger.warning(
                f"Failed to fetch processes for organization {organization_id}"
            )
            return []
    
    async def get_role(
        self,
        organization_id: str,
        role_id: str,
        auth_token: str
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch role details by ID
        
        Args:
            organization_id: ID of the organization
            role_id: UUID of the role
            auth_token: JWT authentication token
            
        Returns:
            Role data dictionary or None if not found/error
            
        Example response:
            {
                "id": "role-uuid",
                "name": "Software Engineer",
                "description": "Develops and maintains software applications"
            }
        """
        logger.debug(f"Fetching role {role_id} from organization {organization_id}")
        
        result = await self._make_request(
            method="GET",
            endpoint=f"/organizations/{organization_id}/roles/{role_id}",
            auth_token=auth_token
        )
        
        if result:
            # Extract data from wrapped response
            if isinstance(result, dict) and "data" in result:
                role_data = result["data"]
                logger.debug(f"Successfully fetched role {role_id}")
                return role_data
            else:
                logger.debug(f"Successfully fetched role {role_id}")
                return result
        else:
            logger.warning(f"Failed to fetch role {role_id}")
            return None
    
    async def create_process(
        self,
        organization_id: str,
        auth_token: str,
        process_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new process in the backend
        
        Args:
            organization_id: ID of the organization
            auth_token: JWT authentication token
            process_data: Dictionary containing process details (name, description, type)
            
        Returns:
            Created process data dictionary or None if error
            
        Example process_data:
            {
                "name": "Customer Onboarding",
                "description": "Process for onboarding new customers",
                "type": "S"  # Must be 'S' (Soporte), 'E' (Estratégico), or 'C' (Crítico)
            }
            
        Example response:
            {
                "id": "process-uuid",
                "name": "Customer Onboarding",
                "type": "S",
                "isActive": true,
                "createdAt": "2024-01-01T00:00:00Z"
            }
        """
        logger.info(
            f"Creating process '{process_data.get('name')}' for organization {organization_id}"
        )
        
        # Validate and normalize process type
        VALID_TYPES = {'S', 'E', 'C'}  # Soporte, Estratégico, Crítico
        process_type = process_data.get("type", "C").upper()
        
        if process_type not in VALID_TYPES:
            logger.warning(
                f"Invalid process type '{process_type}', defaulting to 'C' (Crítico)",
                extra={
                    "invalid_type": process_type,
                    "valid_types": list(VALID_TYPES),
                    "process_name": process_data.get("name")
                }
            )
            process_type = "C"
        
        # Prepare payload for backend API
        payload = {
            "name": process_data.get("name"),
            "description": process_data.get("description", ""),
            "type": process_type
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                url = f"{self.base_url}/organizations/{organization_id}/processes"
                headers = {
                    "Authorization": f"Bearer {auth_token}",
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                }
                
                response = await client.post(
                    url=url,
                    headers=headers,
                    json=payload
                )
                
                if response.status_code >= 400:
                    logger.error(
                        f"Failed to create process: {response.status_code}",
                        extra={
                            "status_code": response.status_code,
                            "process_name": payload.get("name"),
                            "response_text": response.text
                        }
                    )
                    return None
                
                result = response.json()
                
                # Extract data from wrapped response
                if isinstance(result, dict) and "data" in result:
                    created_process = result["data"]
                    logger.info(
                        f"Successfully created process '{created_process.get('name')}'",
                        extra={"process_id": created_process.get("id")}
                    )
                    return created_process
                else:
                    logger.info(
                        f"Successfully created process '{payload.get('name')}'",
                        extra={"result": result}
                    )
                    return result
                    
        except Exception as e:
            logger.error(
                f"Error creating process: {type(e).__name__}: {str(e)}",
                extra={
                    "process_name": payload.get("name"),
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }
            )
            return None
