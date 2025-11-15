"""
Unit tests for BackendClient

Tests HTTP communication with svc-organizations-php backend including
retry logic, timeout handling, and error response parsing.
"""
import pytest
import httpx
from unittest.mock import AsyncMock, patch, Mock
from uuid import uuid4

from app.clients.backend_client import BackendClient


class TestBackendClientGetEmployee:
    """Test suite for get_employee method"""
    
    @pytest.mark.asyncio
    async def test_get_employee_success(self):
        """Test successful employee retrieval"""
        employee_id = uuid4()
        auth_token = "test-token"
        expected_response = {
            "id": str(employee_id),
            "firstName": "John",
            "lastName": "Doe",
            "isActive": True,
            "organizationId": "org-123"
        }
        
        client = BackendClient(base_url="http://test-api", timeout=5.0)
        
        # Mock httpx response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = expected_response
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            result = await client.get_employee(employee_id, auth_token)
        
        assert result == expected_response
        mock_client.request.assert_called_once_with(
            method="GET",
            url=f"http://test-api/employees/{employee_id}",
            headers={
                "Authorization": f"Bearer {auth_token}",
                "Accept": "application/json"
            },
            params=None
        )
    
    @pytest.mark.asyncio
    async def test_get_employee_not_found(self):
        """Test employee not found returns None"""
        employee_id = uuid4()
        auth_token = "test-token"
        
        client = BackendClient(base_url="http://test-api", timeout=5.0)
        
        # Mock 404 response
        mock_response = Mock()
        mock_response.status_code = 404
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            result = await client.get_employee(employee_id, auth_token)
        
        assert result is None


class TestBackendClientGetOrganization:
    """Test suite for get_organization method"""
    
    @pytest.mark.asyncio
    async def test_get_organization_success(self):
        """Test successful organization retrieval"""
        org_id = "org-123"
        auth_token = "test-token"
        expected_response = {
            "id": org_id,
            "name": "Acme Corp",
            "isActive": True
        }
        
        client = BackendClient(base_url="http://test-api", timeout=5.0)
        
        # Mock httpx response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = expected_response
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            result = await client.get_organization(org_id, auth_token)
        
        assert result == expected_response


class TestBackendClientGetOrganizationProcesses:
    """Test suite for get_organization_processes method"""
    
    @pytest.mark.asyncio
    async def test_get_organization_processes_success(self):
        """Test successful processes retrieval"""
        org_id = "org-123"
        auth_token = "test-token"
        expected_response = [
            {
                "id": str(uuid4()),
                "name": "Customer Onboarding",
                "type": "operational",
                "typeLabel": "Operational",
                "isActive": True,
                "createdAt": "2024-01-01T00:00:00Z",
                "updatedAt": "2024-01-15T00:00:00Z"
            },
            {
                "id": str(uuid4()),
                "name": "Invoice Processing",
                "type": "support",
                "typeLabel": "Support",
                "isActive": True,
                "createdAt": "2024-01-02T00:00:00Z",
                "updatedAt": "2024-01-16T00:00:00Z"
            }
        ]
        
        client = BackendClient(base_url="http://test-api", timeout=5.0)
        
        # Mock httpx response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = expected_response
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            result = await client.get_organization_processes(org_id, auth_token)
        
        assert result == expected_response
        assert len(result) == 2
    
    @pytest.mark.asyncio
    async def test_get_organization_processes_with_pagination(self):
        """Test processes retrieval with pagination parameters"""
        org_id = "org-123"
        auth_token = "test-token"
        
        client = BackendClient(base_url="http://test-api", timeout=5.0)
        
        # Mock httpx response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            await client.get_organization_processes(
                org_id, auth_token, active_only=True, limit=10, page=2
            )
        
        # Verify pagination params were passed
        call_args = mock_client.request.call_args
        assert call_args.kwargs["params"]["limit"] == 10
        assert call_args.kwargs["params"]["page"] == 2
        assert call_args.kwargs["params"]["isActive"] == "true"
    
    @pytest.mark.asyncio
    async def test_get_organization_processes_paginated_response(self):
        """Test processes retrieval with paginated response format"""
        org_id = "org-123"
        auth_token = "test-token"
        processes_data = [
            {
                "id": str(uuid4()),
                "name": "Process 1",
                "type": "operational",
                "typeLabel": "Operational",
                "isActive": True
            }
        ]
        
        # Backend might return paginated format
        paginated_response = {
            "data": processes_data,
            "meta": {
                "total": 1,
                "page": 1,
                "limit": 20
            }
        }
        
        client = BackendClient(base_url="http://test-api", timeout=5.0)
        
        # Mock httpx response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = paginated_response
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            result = await client.get_organization_processes(org_id, auth_token)
        
        # Should extract data from paginated response
        assert result == processes_data
    
    @pytest.mark.asyncio
    async def test_get_organization_processes_empty_list(self):
        """Test processes retrieval returns empty list on error"""
        org_id = "org-123"
        auth_token = "test-token"
        
        client = BackendClient(base_url="http://test-api", timeout=5.0)
        
        # Mock 500 error
        mock_response = Mock()
        mock_response.status_code = 500
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            result = await client.get_organization_processes(org_id, auth_token)
        
        assert result == []


class TestBackendClientGetEmployeeRoles:
    """Test suite for get_employee_roles method"""
    
    @pytest.mark.asyncio
    async def test_get_employee_roles_success(self):
        """Test successful roles retrieval"""
        org_id = "org-123"
        employee_id = uuid4()
        auth_token = "test-token"
        expected_response = [
            {
                "id": str(uuid4()),
                "name": "Software Engineer",
                "description": "Develops software applications"
            },
            {
                "id": str(uuid4()),
                "name": "Team Lead",
                "description": "Leads development team"
            }
        ]
        
        client = BackendClient(base_url="http://test-api", timeout=5.0)
        
        # Mock httpx response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = expected_response
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            result = await client.get_employee_roles(org_id, employee_id, auth_token)
        
        assert result == expected_response
        assert len(result) == 2
    
    @pytest.mark.asyncio
    async def test_get_employee_roles_wrapped_response(self):
        """Test roles retrieval with wrapped response format"""
        org_id = "org-123"
        employee_id = uuid4()
        auth_token = "test-token"
        roles_data = [
            {
                "id": str(uuid4()),
                "name": "Developer",
                "description": "Software developer"
            }
        ]
        
        # Backend might return wrapped format
        wrapped_response = {
            "data": roles_data
        }
        
        client = BackendClient(base_url="http://test-api", timeout=5.0)
        
        # Mock httpx response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = wrapped_response
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            result = await client.get_employee_roles(org_id, employee_id, auth_token)
        
        # Should extract data from wrapped response
        assert result == roles_data


class TestBackendClientRetryLogic:
    """Test suite for retry logic and error handling"""
    
    @pytest.mark.asyncio
    async def test_retry_on_timeout(self):
        """Test retry logic on timeout"""
        employee_id = uuid4()
        auth_token = "test-token"
        
        client = BackendClient(base_url="http://test-api", timeout=5.0, max_retries=2)
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            
            # First call times out, second succeeds
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"id": str(employee_id)}
            
            mock_client.request = AsyncMock(
                side_effect=[
                    httpx.TimeoutException("Timeout"),
                    mock_response
                ]
            )
            mock_client_class.return_value = mock_client
            
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await client.get_employee(employee_id, auth_token)
        
        assert result is not None
        assert result["id"] == str(employee_id)
        assert mock_client.request.call_count == 2
    
    @pytest.mark.asyncio
    async def test_retry_on_500_error(self):
        """Test retry logic on 5xx server errors"""
        employee_id = uuid4()
        auth_token = "test-token"
        
        client = BackendClient(base_url="http://test-api", timeout=5.0, max_retries=2)
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            
            # First call returns 500, second succeeds
            mock_error_response = Mock()
            mock_error_response.status_code = 500
            
            mock_success_response = Mock()
            mock_success_response.status_code = 200
            mock_success_response.json.return_value = {"id": str(employee_id)}
            
            mock_client.request = AsyncMock(
                side_effect=[mock_error_response, mock_success_response]
            )
            mock_client_class.return_value = mock_client
            
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await client.get_employee(employee_id, auth_token)
        
        assert result is not None
        assert mock_client.request.call_count == 2
    
    @pytest.mark.asyncio
    async def test_no_retry_on_404_error(self):
        """Test no retry on 4xx client errors"""
        employee_id = uuid4()
        auth_token = "test-token"
        
        client = BackendClient(base_url="http://test-api", timeout=5.0, max_retries=2)
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            
            # Return 404
            mock_response = Mock()
            mock_response.status_code = 404
            
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            result = await client.get_employee(employee_id, auth_token)
        
        assert result is None
        # Should not retry on 4xx errors
        assert mock_client.request.call_count == 1
    
    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test returns None after max retries exceeded"""
        employee_id = uuid4()
        auth_token = "test-token"
        
        client = BackendClient(base_url="http://test-api", timeout=5.0, max_retries=2)
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            
            # All calls timeout
            mock_client.request = AsyncMock(
                side_effect=httpx.TimeoutException("Timeout")
            )
            mock_client_class.return_value = mock_client
            
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await client.get_employee(employee_id, auth_token)
        
        assert result is None
        # Initial call + 2 retries = 3 total calls
        assert mock_client.request.call_count == 3
    
    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        """Test exponential backoff timing"""
        employee_id = uuid4()
        auth_token = "test-token"
        
        client = BackendClient(base_url="http://test-api", timeout=5.0, max_retries=2)
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            
            # All calls timeout
            mock_client.request = AsyncMock(
                side_effect=httpx.TimeoutException("Timeout")
            )
            mock_client_class.return_value = mock_client
            
            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                await client.get_employee(employee_id, auth_token)
                
                # Verify exponential backoff: 0.5s, 1s
                assert mock_sleep.call_count == 2
                sleep_times = [call.args[0] for call in mock_sleep.call_args_list]
                assert sleep_times[0] == 0.5  # First retry
                assert sleep_times[1] == 1.0  # Second retry


class TestBackendClientTimeoutHandling:
    """Test suite for timeout handling"""
    
    @pytest.mark.asyncio
    async def test_timeout_configuration(self):
        """Test timeout is properly configured"""
        client = BackendClient(base_url="http://test-api", timeout=3.0)
        
        employee_id = uuid4()
        auth_token = "test-token"
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {}
            mock_client.request = AsyncMock(return_value=mock_response)
            
            mock_client_class.return_value = mock_client
            
            await client.get_employee(employee_id, auth_token)
            
            # Verify timeout was passed to AsyncClient
            mock_client_class.assert_called_once_with(timeout=3.0)
    
    @pytest.mark.asyncio
    async def test_request_error_handling(self):
        """Test handling of general request errors"""
        employee_id = uuid4()
        auth_token = "test-token"
        
        client = BackendClient(base_url="http://test-api", timeout=5.0, max_retries=1)
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            
            # Simulate connection error
            mock_client.request = AsyncMock(
                side_effect=httpx.RequestError("Connection failed")
            )
            mock_client_class.return_value = mock_client
            
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await client.get_employee(employee_id, auth_token)
        
        assert result is None
        # Should retry once
        assert mock_client.request.call_count == 2


class TestBackendClientErrorResponseParsing:
    """Test suite for error response parsing"""
    
    @pytest.mark.asyncio
    async def test_invalid_json_response(self):
        """Test handling of invalid JSON responses"""
        employee_id = uuid4()
        auth_token = "test-token"
        
        client = BackendClient(base_url="http://test-api", timeout=5.0)
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            
            # Mock response with invalid JSON
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.side_effect = ValueError("Invalid JSON")
            
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            result = await client.get_employee(employee_id, auth_token)
        
        # Should handle gracefully and return None
        assert result is None
    
    @pytest.mark.asyncio
    async def test_base_url_trailing_slash_handling(self):
        """Test base URL trailing slash is handled correctly"""
        # Test with trailing slash
        client1 = BackendClient(base_url="http://test-api/", timeout=5.0)
        assert client1.base_url == "http://test-api"
        
        # Test without trailing slash
        client2 = BackendClient(base_url="http://test-api", timeout=5.0)
        assert client2.base_url == "http://test-api"
