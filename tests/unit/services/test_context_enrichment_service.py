"""
Unit tests for ContextEnrichmentService

Tests context retrieval, caching integration, error handling,
and graceful degradation when backend services are unavailable.
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID
from datetime import datetime, timedelta

from app.services.context_enrichment_service import ContextEnrichmentService
from app.clients.backend_client import BackendClient
from app.services.context_cache import ContextCache
from app.models.context import (
    EmployeeContextData,
    RoleContextData,
    ProcessContextData,
    InterviewHistorySummary,
    InterviewContextData
)
from app.models.db_models import Interview, InterviewStatusEnum, LanguageEnum


@pytest.fixture
def mock_backend_client():
    """Create a mock backend client"""
    return AsyncMock(spec=BackendClient)


@pytest.fixture
def mock_cache():
    """Create a mock cache"""
    cache = MagicMock(spec=ContextCache)
    cache.get = MagicMock(return_value=None)
    cache.set = MagicMock()
    return cache


@pytest.fixture
def context_service(mock_backend_client, mock_cache):
    """Create context enrichment service with mocked dependencies"""
    return ContextEnrichmentService(
        backend_client=mock_backend_client,
        cache=mock_cache
    )


@pytest.fixture
def sample_employee_data():
    """Sample employee data from backend"""
    return {
        "id": str(uuid4()),
        "firstName": "Juan",
        "lastName": "Pérez",
        "organizationId": str(uuid4()),
        "isActive": True
    }


@pytest.fixture
def sample_organization_data():
    """Sample organization data from backend"""
    return {
        "id": str(uuid4()),
        "name": "ProssX Demo",
        "isActive": True
    }


@pytest.fixture
def sample_roles_data():
    """Sample roles data from backend"""
    return [
        {
            "id": str(uuid4()),
            "name": "Gerente de Operaciones",
            "description": "Responsable de supervisar las operaciones diarias"
        },
        {
            "id": str(uuid4()),
            "name": "Analista de Procesos",
            "description": None
        }
    ]


@pytest.fixture
def sample_processes_data():
    """Sample processes data from backend"""
    return [
        {
            "id": str(uuid4()),
            "name": "Proceso de Aprobación de Compras",
            "type": "operational",
            "typeLabel": "Operacional",
            "isActive": True,
            "createdAt": "2025-01-15T10:00:00Z",
            "updatedAt": "2025-01-20T14:30:00Z"
        },
        {
            "id": str(uuid4()),
            "name": "Gestión de Inventario",
            "type": "operational",
            "typeLabel": "Operacional",
            "isActive": True,
            "createdAt": "2025-01-10T10:00:00Z",
            "updatedAt": "2025-01-18T14:30:00Z"
        }
    ]


class TestGetEmployeeContext:
    """Test suite for get_employee_context method"""
    
    @pytest.mark.asyncio
    async def test_get_employee_context_success(
        self,
        context_service,
        mock_backend_client,
        mock_cache,
        sample_employee_data,
        sample_organization_data,
        sample_roles_data
    ):
        """Test successful employee context retrieval"""
        employee_id = UUID(sample_employee_data["id"])
        auth_token = "test-token"
        
        # Setup mocks
        mock_cache.get.return_value = None  # Cache miss
        mock_backend_client.get_employee.return_value = sample_employee_data
        mock_backend_client.get_organization.return_value = sample_organization_data
        mock_backend_client.get_employee_roles.return_value = sample_roles_data
        
        # Execute
        result = await context_service.get_employee_context(employee_id, auth_token)
        
        # Verify
        assert isinstance(result, EmployeeContextData)
        assert result.id == employee_id
        assert result.first_name == "Juan"
        assert result.last_name == "Pérez"
        assert result.full_name == "Juan Pérez"
        assert result.organization_name == "ProssX Demo"
        assert len(result.roles) == 2
        assert result.roles[0].name == "Gerente de Operaciones"
        assert result.is_active is True
        
        # Verify backend calls
        mock_backend_client.get_employee.assert_called_once_with(
            employee_id=employee_id,
            auth_token=auth_token
        )
        
        # Verify caching
        mock_cache.set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_employee_context_from_cache(
        self,
        context_service,
        mock_backend_client,
        mock_cache
    ):
        """Test employee context retrieval from cache"""
        employee_id = uuid4()
        auth_token = "test-token"
        
        cached_data = {
            "id": str(employee_id),
            "first_name": "Juan",
            "last_name": "Pérez",
            "full_name": "Juan Pérez",
            "organization_id": str(uuid4()),
            "organization_name": "ProssX Demo",
            "roles": [],
            "is_active": True
        }
        
        # Setup cache hit
        mock_cache.get.return_value = cached_data
        
        # Execute
        result = await context_service.get_employee_context(employee_id, auth_token)
        
        # Verify
        assert isinstance(result, EmployeeContextData)
        assert result.first_name == "Juan"
        
        # Verify backend was not called
        mock_backend_client.get_employee.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_employee_context_employee_not_found(
        self,
        context_service,
        mock_backend_client,
        mock_cache
    ):
        """Test error when employee not found"""
        employee_id = uuid4()
        auth_token = "test-token"
        
        # Setup mocks
        mock_cache.get.return_value = None
        mock_backend_client.get_employee.return_value = None
        
        # Execute and verify exception
        with pytest.raises(ValueError, match="not found"):
            await context_service.get_employee_context(employee_id, auth_token)
    
    @pytest.mark.asyncio
    async def test_get_employee_context_no_organization(
        self,
        context_service,
        mock_backend_client,
        mock_cache
    ):
        """Test error when employee has no organization"""
        employee_id = uuid4()
        auth_token = "test-token"
        
        employee_data = {
            "id": str(employee_id),
            "firstName": "Juan",
            "lastName": "Pérez",
            # Missing organizationId
            "isActive": True
        }
        
        # Setup mocks
        mock_cache.get.return_value = None
        mock_backend_client.get_employee.return_value = employee_data
        
        # Execute and verify exception
        with pytest.raises(ValueError, match="no organization"):
            await context_service.get_employee_context(employee_id, auth_token)
    
    @pytest.mark.asyncio
    async def test_get_employee_context_organization_fetch_fails(
        self,
        context_service,
        mock_backend_client,
        mock_cache,
        sample_employee_data,
        sample_roles_data
    ):
        """Test graceful handling when organization fetch fails"""
        employee_id = UUID(sample_employee_data["id"])
        auth_token = "test-token"
        
        # Setup mocks
        mock_cache.get.return_value = None
        mock_backend_client.get_employee.return_value = sample_employee_data
        mock_backend_client.get_organization.return_value = None  # Fails
        mock_backend_client.get_employee_roles.return_value = sample_roles_data
        
        # Execute
        result = await context_service.get_employee_context(employee_id, auth_token)
        
        # Verify - should use organization ID as name
        assert isinstance(result, EmployeeContextData)
        assert result.organization_name == sample_employee_data["organizationId"]
    
    @pytest.mark.asyncio
    async def test_get_employee_context_roles_fetch_fails(
        self,
        context_service,
        mock_backend_client,
        mock_cache,
        sample_employee_data,
        sample_organization_data
    ):
        """Test graceful handling when roles fetch fails"""
        employee_id = UUID(sample_employee_data["id"])
        auth_token = "test-token"
        
        # Setup mocks
        mock_cache.get.return_value = None
        mock_backend_client.get_employee.return_value = sample_employee_data
        mock_backend_client.get_organization.return_value = sample_organization_data
        mock_backend_client.get_employee_roles.side_effect = Exception("API error")
        
        # Execute
        result = await context_service.get_employee_context(employee_id, auth_token)
        
        # Verify - should have empty roles
        assert isinstance(result, EmployeeContextData)
        assert len(result.roles) == 0


class TestGetOrganizationProcesses:
    """Test suite for get_organization_processes method"""
    
    @pytest.mark.asyncio
    async def test_get_organization_processes_success(
        self,
        context_service,
        mock_backend_client,
        mock_cache,
        sample_processes_data
    ):
        """Test successful processes retrieval"""
        organization_id = str(uuid4())
        auth_token = "test-token"
        
        # Setup mocks
        mock_cache.get.return_value = None  # Cache miss
        mock_backend_client.get_organization_processes.return_value = sample_processes_data
        
        # Execute
        result = await context_service.get_organization_processes(
            organization_id, auth_token
        )
        
        # Verify
        assert len(result) == 2
        assert all(isinstance(p, ProcessContextData) for p in result)
        assert result[0].name == "Proceso de Aprobación de Compras"
        # Should be sorted by updated_at descending
        assert result[0].updated_at > result[1].updated_at
        
        # Verify backend call
        mock_backend_client.get_organization_processes.assert_called_once_with(
            organization_id=organization_id,
            auth_token=auth_token,
            active_only=True,
            limit=20
        )
        
        # Verify caching
        mock_cache.set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_organization_processes_from_cache(
        self,
        context_service,
        mock_backend_client,
        mock_cache
    ):
        """Test processes retrieval from cache"""
        organization_id = str(uuid4())
        auth_token = "test-token"
        
        cached_data = [
            {
                "id": str(uuid4()),
                "name": "Cached Process",
                "type": "operational",
                "type_label": "Operacional",
                "is_active": True,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
        ]
        
        # Setup cache hit
        mock_cache.get.return_value = cached_data
        
        # Execute
        result = await context_service.get_organization_processes(
            organization_id, auth_token
        )
        
        # Verify
        assert len(result) == 1
        assert result[0].name == "Cached Process"
        
        # Verify backend was not called
        mock_backend_client.get_organization_processes.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_organization_processes_empty_list(
        self,
        context_service,
        mock_backend_client,
        mock_cache
    ):
        """Test handling of no processes"""
        organization_id = str(uuid4())
        auth_token = "test-token"
        
        # Setup mocks
        mock_cache.get.return_value = None
        mock_backend_client.get_organization_processes.return_value = []
        
        # Execute
        result = await context_service.get_organization_processes(
            organization_id, auth_token
        )
        
        # Verify
        assert result == []
    
    @pytest.mark.asyncio
    async def test_get_organization_processes_backend_error(
        self,
        context_service,
        mock_backend_client,
        mock_cache
    ):
        """Test graceful handling of backend errors"""
        organization_id = str(uuid4())
        auth_token = "test-token"
        
        # Setup mocks
        mock_cache.get.return_value = None
        mock_backend_client.get_organization_processes.side_effect = Exception("API error")
        
        # Execute
        result = await context_service.get_organization_processes(
            organization_id, auth_token
        )
        
        # Verify - should return empty list, not raise exception
        assert result == []
    
    @pytest.mark.asyncio
    async def test_get_organization_processes_invalid_data(
        self,
        context_service,
        mock_backend_client,
        mock_cache
    ):
        """Test handling of invalid process data"""
        organization_id = str(uuid4())
        auth_token = "test-token"
        
        processes_data = [
            {
                "id": str(uuid4()),
                "name": "Valid Process",
                "type": "operational",
                "typeLabel": "Operacional",
                "isActive": True,
                "createdAt": "2025-01-15T10:00:00Z",
                "updatedAt": "2025-01-20T14:30:00Z"
            },
            {
                # Missing required 'id' field
                "name": "Invalid Process",
                "type": "operational"
            }
        ]
        
        # Setup mocks
        mock_cache.get.return_value = None
        mock_backend_client.get_organization_processes.return_value = processes_data
        
        # Execute
        result = await context_service.get_organization_processes(
            organization_id, auth_token
        )
        
        # Verify - should skip invalid process
        assert len(result) == 1
        assert result[0].name == "Valid Process"
    
    @pytest.mark.asyncio
    async def test_get_organization_processes_custom_limit(
        self,
        context_service,
        mock_backend_client,
        mock_cache
    ):
        """Test processes retrieval with custom limit"""
        organization_id = str(uuid4())
        auth_token = "test-token"
        
        # Setup mocks
        mock_cache.get.return_value = None
        mock_backend_client.get_organization_processes.return_value = []
        
        # Execute with custom limit
        await context_service.get_organization_processes(
            organization_id, auth_token, limit=50
        )
        
        # Verify backend call with custom limit
        mock_backend_client.get_organization_processes.assert_called_once_with(
            organization_id=organization_id,
            auth_token=auth_token,
            active_only=True,
            limit=50
        )


class TestGetInterviewHistorySummary:
    """Test suite for get_interview_history_summary method"""
    
    @pytest.mark.asyncio
    async def test_get_interview_history_with_interviews(
        self,
        context_service,
        db_session
    ):
        """Test interview history retrieval with existing interviews"""
        employee_id = uuid4()
        
        # Create test interviews
        interview1 = Interview(
            id_interview=uuid4(),
            employee_id=employee_id,
            language=LanguageEnum.es,
            status=InterviewStatusEnum.completed,
            started_at=datetime.utcnow() - timedelta(days=5),
            completed_at=datetime.utcnow() - timedelta(days=5)
        )
        interview2 = Interview(
            id_interview=uuid4(),
            employee_id=employee_id,
            language=LanguageEnum.es,
            status=InterviewStatusEnum.completed,
            started_at=datetime.utcnow() - timedelta(days=2),
            completed_at=datetime.utcnow() - timedelta(days=2)
        )
        interview3 = Interview(
            id_interview=uuid4(),
            employee_id=employee_id,
            language=LanguageEnum.es,
            status=InterviewStatusEnum.in_progress,
            started_at=datetime.utcnow() - timedelta(days=1)
        )
        
        db_session.add_all([interview1, interview2, interview3])
        await db_session.commit()
        
        # Execute
        result = await context_service.get_interview_history_summary(
            employee_id, db_session
        )
        
        # Verify
        assert isinstance(result, InterviewHistorySummary)
        assert result.total_interviews == 3
        assert result.completed_interviews == 2
        assert result.last_interview_date is not None
        assert result.topics_covered == []  # Currently empty
    
    @pytest.mark.asyncio
    async def test_get_interview_history_no_interviews(
        self,
        context_service,
        db_session
    ):
        """Test interview history retrieval with no interviews"""
        employee_id = uuid4()
        
        # Execute
        result = await context_service.get_interview_history_summary(
            employee_id, db_session
        )
        
        # Verify
        assert isinstance(result, InterviewHistorySummary)
        assert result.total_interviews == 0
        assert result.completed_interviews == 0
        assert result.last_interview_date is None
        assert result.topics_covered == []
    
    @pytest.mark.asyncio
    async def test_get_interview_history_database_error(
        self,
        context_service
    ):
        """Test graceful handling of database errors"""
        employee_id = uuid4()
        
        # Create a mock session that raises an error
        mock_db = AsyncMock()
        mock_db.execute.side_effect = Exception("Database error")
        
        # Execute
        result = await context_service.get_interview_history_summary(
            employee_id, mock_db
        )
        
        # Verify - should return empty summary
        assert isinstance(result, InterviewHistorySummary)
        assert result.total_interviews == 0


class TestGetFullInterviewContext:
    """Test suite for get_full_interview_context method"""
    
    @pytest.mark.asyncio
    async def test_get_full_context_success(
        self,
        context_service,
        mock_backend_client,
        mock_cache,
        db_session,
        sample_employee_data,
        sample_organization_data,
        sample_roles_data,
        sample_processes_data
    ):
        """Test successful full context retrieval"""
        employee_id = UUID(sample_employee_data["id"])
        auth_token = "test-token"
        
        # Setup mocks
        mock_cache.get.return_value = None
        mock_backend_client.get_employee.return_value = sample_employee_data
        mock_backend_client.get_organization.return_value = sample_organization_data
        mock_backend_client.get_employee_roles.return_value = sample_roles_data
        mock_backend_client.get_organization_processes.return_value = sample_processes_data
        
        # Execute
        result = await context_service.get_full_interview_context(
            employee_id, auth_token, db_session
        )
        
        # Verify
        assert isinstance(result, InterviewContextData)
        assert isinstance(result.employee, EmployeeContextData)
        assert result.employee.first_name == "Juan"
        assert len(result.organization_processes) == 2
        assert isinstance(result.interview_history, InterviewHistorySummary)
        assert result.context_timestamp is not None
    
    @pytest.mark.asyncio
    async def test_get_full_context_employee_fetch_fails(
        self,
        context_service,
        mock_backend_client,
        mock_cache,
        db_session
    ):
        """Test that employee fetch failure raises exception"""
        employee_id = uuid4()
        auth_token = "test-token"
        
        # Setup mocks
        mock_cache.get.return_value = None
        mock_backend_client.get_employee.return_value = None
        
        # Execute and verify exception
        with pytest.raises(ValueError):
            await context_service.get_full_interview_context(
                employee_id, auth_token, db_session
            )
    
    @pytest.mark.asyncio
    async def test_get_full_context_history_fetch_fails(
        self,
        context_service,
        mock_backend_client,
        mock_cache,
        sample_employee_data,
        sample_organization_data,
        sample_roles_data,
        sample_processes_data
    ):
        """Test graceful handling when history fetch fails"""
        employee_id = UUID(sample_employee_data["id"])
        auth_token = "test-token"
        
        # Setup mocks
        mock_cache.get.return_value = None
        mock_backend_client.get_employee.return_value = sample_employee_data
        mock_backend_client.get_organization.return_value = sample_organization_data
        mock_backend_client.get_employee_roles.return_value = sample_roles_data
        mock_backend_client.get_organization_processes.return_value = sample_processes_data
        
        # Create a mock session that raises an error
        mock_db = AsyncMock()
        mock_db.execute.side_effect = Exception("Database error")
        
        # Execute
        result = await context_service.get_full_interview_context(
            employee_id, auth_token, mock_db
        )
        
        # Verify - should have empty history but continue
        assert isinstance(result, InterviewContextData)
        assert result.interview_history.total_interviews == 0
    
    @pytest.mark.asyncio
    async def test_get_full_context_processes_fetch_fails(
        self,
        context_service,
        mock_backend_client,
        mock_cache,
        db_session,
        sample_employee_data,
        sample_organization_data,
        sample_roles_data
    ):
        """Test graceful handling when processes fetch fails"""
        employee_id = UUID(sample_employee_data["id"])
        auth_token = "test-token"
        
        # Setup mocks
        mock_cache.get.return_value = None
        mock_backend_client.get_employee.return_value = sample_employee_data
        mock_backend_client.get_organization.return_value = sample_organization_data
        mock_backend_client.get_employee_roles.return_value = sample_roles_data
        mock_backend_client.get_organization_processes.side_effect = Exception("API error")
        
        # Execute
        result = await context_service.get_full_interview_context(
            employee_id, auth_token, db_session
        )
        
        # Verify - should have empty processes but continue
        assert isinstance(result, InterviewContextData)
        assert len(result.organization_processes) == 0
    
    @pytest.mark.asyncio
    async def test_get_full_context_parallel_fetching(
        self,
        context_service,
        mock_backend_client,
        mock_cache,
        db_session,
        sample_employee_data,
        sample_organization_data,
        sample_roles_data,
        sample_processes_data
    ):
        """Test that employee and history are fetched in parallel"""
        employee_id = UUID(sample_employee_data["id"])
        auth_token = "test-token"
        
        # Setup mocks
        mock_cache.get.return_value = None
        mock_backend_client.get_employee.return_value = sample_employee_data
        mock_backend_client.get_organization.return_value = sample_organization_data
        mock_backend_client.get_employee_roles.return_value = sample_roles_data
        mock_backend_client.get_organization_processes.return_value = sample_processes_data
        
        # Execute
        start_time = datetime.utcnow()
        result = await context_service.get_full_interview_context(
            employee_id, auth_token, db_session
        )
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        
        # Verify result
        assert isinstance(result, InterviewContextData)
        
        # Verify performance - should be fast due to parallel execution
        # (This is a basic check; actual timing depends on system)
        assert elapsed < 5.0  # Should complete within 5 seconds


class TestCachingIntegration:
    """Test suite for caching integration"""
    
    @pytest.mark.asyncio
    async def test_employee_context_uses_real_cache(self):
        """Test employee context with real cache"""
        # Create service with real cache
        real_cache = ContextCache(ttl_seconds=300)
        mock_backend = AsyncMock(spec=BackendClient)
        service = ContextEnrichmentService(
            backend_client=mock_backend,
            cache=real_cache
        )
        
        employee_id = uuid4()
        auth_token = "test-token"
        
        employee_data = {
            "id": str(employee_id),
            "firstName": "Test",
            "lastName": "User",
            "organizationId": str(uuid4()),
            "isActive": True
        }
        
        org_data = {"id": employee_data["organizationId"], "name": "Test Org"}
        
        mock_backend.get_employee.return_value = employee_data
        mock_backend.get_organization.return_value = org_data
        mock_backend.get_employee_roles.return_value = []
        
        # First call - should fetch from backend
        result1 = await service.get_employee_context(employee_id, auth_token)
        assert mock_backend.get_employee.call_count == 1
        
        # Second call - should use cache
        result2 = await service.get_employee_context(employee_id, auth_token)
        assert mock_backend.get_employee.call_count == 1  # Not called again
        
        # Results should be equal
        assert result1.first_name == result2.first_name
    
    @pytest.mark.asyncio
    async def test_processes_context_uses_real_cache(self):
        """Test processes context with real cache"""
        # Create service with real cache
        real_cache = ContextCache(ttl_seconds=300)
        mock_backend = AsyncMock(spec=BackendClient)
        service = ContextEnrichmentService(
            backend_client=mock_backend,
            cache=real_cache
        )
        
        organization_id = str(uuid4())
        auth_token = "test-token"
        
        processes_data = [
            {
                "id": str(uuid4()),
                "name": "Test Process",
                "type": "operational",
                "typeLabel": "Operacional",
                "isActive": True,
                "createdAt": "2025-01-15T10:00:00Z",
                "updatedAt": "2025-01-20T14:30:00Z"
            }
        ]
        
        mock_backend.get_organization_processes.return_value = processes_data
        
        # First call - should fetch from backend
        result1 = await service.get_organization_processes(organization_id, auth_token)
        assert mock_backend.get_organization_processes.call_count == 1
        
        # Second call - should use cache
        result2 = await service.get_organization_processes(organization_id, auth_token)
        assert mock_backend.get_organization_processes.call_count == 1  # Not called again
        
        # Results should be equal
        assert len(result1) == len(result2)
        assert result1[0].name == result2[0].name
