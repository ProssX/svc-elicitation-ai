"""
Integration tests for unchanged endpoints
Verifies that /start, /export, GET /interviews, GET /interviews/{id}, and PATCH /interviews/{id}
still work correctly after the optimization changes and return consistent error formats.
"""
import pytest
import pytest_asyncio
import httpx
import os
from uuid import UUID
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
from fastapi import FastAPI
from app.models.db_models import Interview, InterviewMessage, InterviewStatusEnum, MessageRoleEnum, LanguageEnum
from app.services.interview_service import InterviewService
from app.main import app


# Mark all tests in this module as async
pytestmark = pytest.mark.asyncio


class TestUnchangedEndpoints:
    """Test suite for endpoints that should remain unchanged"""
    
    @pytest_asyncio.fixture
    async def client(self):
        """Create async test client"""
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    
    @pytest.fixture
    def auth_service_url(self):
        """Get auth service URL from environment"""
        import os
        
        # Check if we're running inside Docker by looking for /.dockerenv
        is_docker = os.path.exists('/.dockerenv')
        
        if is_docker:
            # Inside Docker: use container name
            return "http://svc-users-app:8001"
        else:
            # Local testing: use localhost
            return "http://localhost:8001"
    
    @pytest.fixture
    def auth_token(self, auth_service_url):
        """Get real JWT token from auth service"""
        # Login with admin user (from seed.py)
        login_url = f"{auth_service_url}/api/v1/auth/login"
        
        try:
            response = httpx.post(
                login_url,
                json={
                    "email": "admin@example.com",
                    "password": "admin123"
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                data = response.json()
                # The auth service returns "token" not "access_token"
                token = data.get("data", {}).get("token")
                if token:
                    return f"Bearer {token}"
            
            # If admin login fails, try user account
            response = httpx.post(
                login_url,
                json={
                    "email": "user@example.com",
                    "password": "user123"
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                data = response.json()
                token = data.get("data", {}).get("token")
                if token:
                    return f"Bearer {token}"
            
            pytest.skip(f"Could not authenticate with auth service: {response.status_code}")
            
        except Exception as e:
            pytest.skip(f"Auth service not available: {str(e)}")
    
    @pytest.fixture
    def mock_user_context(self):
        """Mock user context"""
        return {
            "name": "Test User",
            "role": "Test Role",
            "organization": "Test Organization",
            "technical_level": "intermediate"
        }
    
    async def test_start_endpoint_still_works(self, client, auth_token, mock_user_context):
        """Test /start endpoint still works correctly"""
        # Mock only the context service and agent (not auth)
        with patch('app.routers.interviews.get_context_service') as mock_context, \
             patch('app.routers.interviews.get_agent') as mock_agent:
            
            # Setup mocks
            mock_context_service = AsyncMock()
            mock_context_service.get_user_context = AsyncMock(return_value=mock_user_context)
            mock_context.return_value = mock_context_service
            
            mock_agent_instance = Mock()
            mock_agent_instance.start_interview = Mock(return_value=Mock(
                question="¿Cuál es tu rol en la organización?",
                question_number=1,
                is_final=False
            ))
            mock_agent.return_value = mock_agent_instance
            
            # Make request with real JWT token
            response = await client.post(
                "/api/v1/interviews/start",
                json={"language": "es"},
                headers={"Authorization": auth_token}
            )
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "interview_id" in data["data"]
            assert "question" in data["data"]
            assert data["data"]["question_number"] == 1
            assert data["data"]["is_final"] is False
    
    async def test_export_endpoint_returns_404_for_nonexistent_interview(self, client, auth_token, mock_user_context):
        """Test /export endpoint returns 404 for non-existent interview"""
        # Mock context service
        with patch('app.routers.interviews.get_context_service') as mock_context:
            mock_context_service = AsyncMock()
            mock_context_service.get_user_context = AsyncMock(return_value=mock_user_context)
            mock_context.return_value = mock_context_service
            
            # Make request with non-existent interview_id
            fake_interview_id = "018e5f8b-1234-7890-abcd-123456789abc"
            response = await client.post(
                "/api/v1/interviews/export",
                json={"interview_id": fake_interview_id},
                headers={"Authorization": auth_token}
            )
            
            # Verify response - should be 404 (interview not found)
            assert response.status_code == 404
            data = response.json()
            assert data["status"] == "error"
            assert data["code"] == 404
    
    async def test_list_interviews_endpoint_still_works(self, client, auth_token):
        """Test GET /interviews endpoint still works correctly"""
        # Make request with real JWT token
        response = await client.get(
            "/api/v1/interviews",
            headers={"Authorization": auth_token}
        )
        
        # Verify response structure (may be empty list if no interviews)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert isinstance(data["data"], list)
        assert "pagination" in data["meta"]
        assert "total_items" in data["meta"]["pagination"]
        assert "current_page" in data["meta"]["pagination"]
    
    async def test_get_interview_by_id_endpoint_returns_404(self, client, auth_token):
        """Test GET /interviews/{id} endpoint returns 404 for non-existent interview"""
        # Make request with non-existent interview_id
        fake_interview_id = "018e5f8b-1234-7890-abcd-123456789abc"
        response = await client.get(
            f"/api/v1/interviews/{fake_interview_id}",
            headers={"Authorization": auth_token}
        )
        
        # Verify response - should be 404
        assert response.status_code == 404
        data = response.json()
        assert data["status"] == "error"
        assert data["code"] == 404
        assert data["message"] == "Interview not found"
    
    async def test_update_interview_status_endpoint_returns_404(self, client, auth_token):
        """Test PATCH /interviews/{id} endpoint returns 404 for non-existent interview"""
        # Make request with non-existent interview_id
        fake_interview_id = "018e5f8b-1234-7890-abcd-123456789abc"
        response = await client.patch(
            f"/api/v1/interviews/{fake_interview_id}",
            json={"status": "completed"},
            headers={"Authorization": auth_token}
        )
        
        # Verify response - should be 404
        assert response.status_code == 404
        data = response.json()
        assert data["status"] == "error"
        assert data["code"] == 404
        assert data["message"] == "Interview not found"
    
    async def test_error_responses_match_prossx_format_validation_error(self, client, auth_token):
        """Test error responses match ProssX format across all endpoints - validation errors"""
        # Send invalid request (empty user_response) with real JWT token
        response = await client.post(
            "/api/v1/interviews/continue",
            json={
                "interview_id": "018e5f8b-1234-7890-abcd-123456789abc",
                "user_response": "",  # Invalid: empty
                "language": "es"
            },
            headers={"Authorization": auth_token}
        )
        
        # Verify ProssX error format
        assert response.status_code == 422
        data = response.json()
        assert data["status"] == "error"
        assert data["code"] == 422
        assert data["message"] == "Validation error"
        assert "errors" in data
        assert isinstance(data["errors"], list)
        assert len(data["errors"]) > 0
        
        # Check error structure
        error = data["errors"][0]
        assert "field" in error
        assert "error" in error
        assert "type" in error
        
        # Check meta information
        assert "meta" in data
        assert "endpoint" in data["meta"]
        assert "method" in data["meta"]
    
    async def test_error_responses_match_prossx_format_invalid_uuid(self, client, auth_token):
        """Test error responses match ProssX format - invalid UUID"""
        # Send request with invalid UUID and real JWT token
        response = await client.post(
            "/api/v1/interviews/continue",
            json={
                "interview_id": "invalid-uuid",  # Invalid UUID format
                "user_response": "Mi respuesta",
                "language": "es"
            },
            headers={"Authorization": auth_token}
        )
        
        # Verify ProssX error format
        assert response.status_code == 422
        data = response.json()
        assert data["status"] == "error"
        assert data["code"] == 422
        assert data["message"] == "Validation error"
        assert "errors" in data
    
    async def test_error_responses_match_prossx_format_invalid_language(self, client, auth_token):
        """Test error responses match ProssX format - invalid language pattern"""
        # Send request with invalid language and real JWT token
        response = await client.post(
            "/api/v1/interviews/continue",
            json={
                "interview_id": "018e5f8b-1234-7890-abcd-123456789abc",
                "user_response": "Mi respuesta",
                "language": "fr"  # Invalid: not in pattern
            },
            headers={"Authorization": auth_token}
        )
        
        # Verify ProssX error format
        assert response.status_code == 422
        data = response.json()
        assert data["status"] == "error"
        assert data["code"] == 422
        assert data["message"] == "Validation error"
        assert "errors" in data
        
        # Check that language field error is present
        language_errors = [e for e in data["errors"] if e["field"] == "language"]
        assert len(language_errors) > 0
