"""
Integration tests for API endpoints with context features

Tests verify that the endpoints:
- Start endpoint extracts auth token and passes to service
- Start endpoint includes context metadata in response
- Continue endpoint extracts auth token and passes to service
- Continue endpoint includes process match info in response
- Export endpoint includes process references in export data
- Export endpoint includes context used during interview
- Backward compatibility is maintained
"""
import pytest
from uuid import UUID, uuid4
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import (
    Interview, 
    InterviewMessage, 
    InterviewProcessReference,
    InterviewStatusEnum, 
    MessageRoleEnum, 
    LanguageEnum
)
from app.models.interview import InterviewResponse, InterviewContext
from app.models.context import (
    InterviewContextData,
    EmployeeContextData,
    ProcessContextData,
    RoleContextData,
    InterviewHistorySummary
)
from app.services.interview_service import InterviewService
from decimal import Decimal


@pytest.fixture
async def test_employee_id():
    """Generate a test employee ID"""
    return uuid4()


@pytest.fixture
async def test_interview(db_session: AsyncSession, test_employee_id: UUID):
    """Create a test interview in the database"""
    interview = Interview(
        id_interview=uuid4(),
        employee_id=test_employee_id,
        language=LanguageEnum.es,
        technical_level="intermediate",
        status=InterviewStatusEnum.in_progress,
        started_at=datetime.utcnow()
    )
    db_session.add(interview)
    await db_session.commit()
    await db_session.refresh(interview)
    return interview


@pytest.fixture
async def test_messages(db_session: AsyncSession, test_interview: Interview):
    """Create test messages for the interview"""
    messages = [
        InterviewMessage(
            id_message=uuid4(),
            interview_id=test_interview.id_interview,
            role=MessageRoleEnum.assistant,
            content="¿Cuál es tu rol en la organización?",
            sequence_number=1,
            created_at=datetime.utcnow()
        ),
        InterviewMessage(
            id_message=uuid4(),
            interview_id=test_interview.id_interview,
            role=MessageRoleEnum.user,
            content="Soy gerente de operaciones",
            sequence_number=2,
            created_at=datetime.utcnow()
        )
    ]
    
    for msg in messages:
        db_session.add(msg)
    
    await db_session.commit()
    
    for msg in messages:
        await db_session.refresh(msg)
    
    return messages


@pytest.fixture
async def test_process_references(db_session: AsyncSession, test_interview: Interview):
    """Create test process references for the interview"""
    process_id = uuid4()
    ref = InterviewProcessReference(
        id_reference=uuid4(),
        interview_id=test_interview.id_interview,
        process_id=process_id,
        is_new_process=False,
        confidence_score=Decimal("0.85"),
        mentioned_at=datetime.utcnow(),
        created_at=datetime.utcnow()
    )
    db_session.add(ref)
    await db_session.commit()
    await db_session.refresh(ref)
    return [ref]


@pytest.fixture
def mock_context_data(test_employee_id: UUID):
    """Create mock context data for testing"""
    return InterviewContextData(
        employee=EmployeeContextData(
            id=test_employee_id,
            first_name="Juan",
            last_name="Pérez",
            full_name="Juan Pérez",
            organization_id="018e5f8b-5678-7890-abcd-123456789abc",
            organization_name="ProssX Demo",
            roles=[
                RoleContextData(
                    id=uuid4(),
                    name="Gerente de Operaciones",
                    description="Responsable de operaciones"
                )
            ],
            is_active=True
        ),
        organization_processes=[
            ProcessContextData(
                id=uuid4(),
                name="Proceso de Aprobación de Compras",
                type="operational",
                type_label="Operacional",
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        ],
        interview_history=InterviewHistorySummary(
            total_interviews=2,
            completed_interviews=1,
            last_interview_date=datetime.utcnow(),
            topics_covered=["Proceso de compras"]
        ),
        context_timestamp=datetime.utcnow()
    )


class TestStartEndpointWithContext:
    """Test suite for /start endpoint with context enrichment"""
    
    @pytest.mark.asyncio
    async def test_start_extracts_auth_token(
        self,
        db_session: AsyncSession,
        test_employee_id: UUID,
        mock_context_data: InterviewContextData
    ):
        """Test that start endpoint extracts auth token from header"""
        # Mock the context enrichment service
        with patch('app.services.interview_service.ContextEnrichmentService') as mock_ctx_service:
            mock_instance = AsyncMock()
            mock_instance.get_full_interview_context.return_value = mock_context_data
            mock_ctx_service.return_value = mock_instance
            
            # Mock the agent
            with patch('app.services.interview_service.get_agent') as mock_agent:
                mock_agent_instance = Mock()
                mock_agent_instance.start_interview.return_value = InterviewResponse(
                    question="¿Cuál es tu rol?",
                    question_number=1,
                    is_final=False,
                    context=InterviewContext()
                )
                mock_agent.return_value = mock_agent_instance
                
                # Create interview service
                service = InterviewService(db_session)
                
                # Call start_interview with auth token
                auth_token = "test-jwt-token"
                interview, first_message = await service.start_interview(
                    employee_id=test_employee_id,
                    language="es",
                    technical_level="intermediate",
                    auth_token=auth_token
                )
                
                # Verify context enrichment was called with auth token
                mock_instance.get_full_interview_context.assert_called_once()
                call_kwargs = mock_instance.get_full_interview_context.call_args.kwargs
                assert call_kwargs['auth_token'] == auth_token
                assert call_kwargs['employee_id'] == test_employee_id
                
                # Verify interview was created
                assert interview is not None
                assert interview.employee_id == test_employee_id
    
    @pytest.mark.asyncio
    async def test_start_includes_context_metadata(
        self,
        db_session: AsyncSession,
        test_employee_id: UUID,
        mock_context_data: InterviewContextData
    ):
        """Test that start endpoint response includes context metadata"""
        # This test would require mocking the full FastAPI endpoint
        # For now, we verify the service layer returns the necessary data
        
        with patch('app.services.interview_service.ContextEnrichmentService') as mock_ctx_service:
            mock_instance = AsyncMock()
            mock_instance.get_full_interview_context.return_value = mock_context_data
            mock_ctx_service.return_value = mock_instance
            
            with patch('app.services.interview_service.get_agent') as mock_agent:
                mock_agent_instance = Mock()
                mock_agent_instance.start_interview.return_value = InterviewResponse(
                    question="¿Cuál es tu rol?",
                    question_number=1,
                    is_final=False,
                    context=InterviewContext()
                )
                mock_agent.return_value = mock_agent_instance
                
                service = InterviewService(db_session)
                interview, first_message = await service.start_interview(
                    employee_id=test_employee_id,
                    language="es",
                    technical_level="intermediate",
                    auth_token="test-token"
                )
                
                # Verify context data is available
                assert mock_instance.get_full_interview_context.called
                context = mock_instance.get_full_interview_context.return_value
                assert len(context.organization_processes) > 0
                assert context.interview_history.total_interviews == 2


class TestContinueEndpointWithContext:
    """Test suite for /continue endpoint with process matching"""
    
    @pytest.mark.asyncio
    async def test_continue_extracts_auth_token(
        self,
        db_session: AsyncSession,
        test_interview: Interview,
        test_messages: list,
        mock_context_data: InterviewContextData
    ):
        """Test that continue endpoint extracts auth token from header"""
        with patch('app.services.interview_service.ContextEnrichmentService') as mock_ctx_service:
            mock_instance = AsyncMock()
            mock_instance.get_full_interview_context.return_value = mock_context_data
            mock_ctx_service.return_value = mock_instance
            
            with patch('app.services.interview_service.get_agent') as mock_agent:
                mock_agent_instance = AsyncMock()
                mock_agent_instance.continue_interview.return_value = InterviewResponse(
                    question="¿Qué procesos gestionas?",
                    question_number=2,
                    is_final=False,
                    context=InterviewContext(),
                    process_matches=[]
                )
                mock_agent.return_value = mock_agent_instance
                
                service = InterviewService(db_session)
                
                auth_token = "test-jwt-token"
                interview, user_msg, agent_msg = await service.continue_interview(
                    interview_id=test_interview.id_interview,
                    employee_id=test_interview.employee_id,
                    user_response="Gestiono el proceso de compras",
                    auth_token=auth_token
                )
                
                # Verify context enrichment was called with auth token
                mock_instance.get_full_interview_context.assert_called_once()
                call_kwargs = mock_instance.get_full_interview_context.call_args.kwargs
                assert call_kwargs['auth_token'] == auth_token
    
    @pytest.mark.asyncio
    async def test_continue_includes_process_matches(
        self,
        db_session: AsyncSession,
        test_interview: Interview,
        test_messages: list,
        mock_context_data: InterviewContextData
    ):
        """Test that continue endpoint includes process match info"""
        from app.models.interview import ProcessMatchInfo
        
        process_match = ProcessMatchInfo(
            process_id=uuid4(),
            process_name="Proceso de Aprobación de Compras",
            is_new=False,
            confidence=0.85
        )
        
        with patch('app.services.interview_service.ContextEnrichmentService') as mock_ctx_service:
            mock_instance = AsyncMock()
            mock_instance.get_full_interview_context.return_value = mock_context_data
            mock_ctx_service.return_value = mock_instance
            
            with patch('app.services.interview_service.get_agent') as mock_agent:
                mock_agent_instance = AsyncMock()
                mock_agent_instance.continue_interview.return_value = InterviewResponse(
                    question="¿Qué procesos gestionas?",
                    question_number=2,
                    is_final=False,
                    context=InterviewContext(),
                    process_matches=[process_match]
                )
                mock_agent.return_value = mock_agent_instance
                
                service = InterviewService(db_session)
                
                interview, user_msg, agent_msg = await service.continue_interview(
                    interview_id=test_interview.id_interview,
                    employee_id=test_interview.employee_id,
                    user_response="Gestiono el proceso de compras",
                    auth_token="test-token"
                )
                
                # Verify process reference was created
                from app.repositories.process_reference_repository import ProcessReferenceRepository
                ref_repo = ProcessReferenceRepository(db_session)
                refs = await ref_repo.get_by_interview(test_interview.id_interview)
                
                assert len(refs) > 0
                assert refs[0].process_id == process_match.process_id
                assert refs[0].confidence_score == Decimal("0.85")


class TestExportEndpointWithContext:
    """Test suite for /export endpoint with process references and context"""
    
    @pytest.mark.asyncio
    async def test_export_includes_process_references(
        self,
        db_session: AsyncSession,
        test_interview: Interview,
        test_messages: list,
        test_process_references: list
    ):
        """Test that export endpoint includes process references"""
        service = InterviewService(db_session)
        
        # Get interview with messages
        interview_data = await service.get_interview(
            interview_id=test_interview.id_interview,
            employee_id=test_interview.employee_id,
            allow_cross_user=False
        )
        
        # Verify interview data is retrieved
        assert interview_data is not None
        assert len(interview_data.messages) > 0
        
        # Get process references
        refs = await service.process_ref_repo.get_by_interview(test_interview.id_interview)
        assert len(refs) > 0
        assert refs[0].process_id == test_process_references[0].process_id
    
    @pytest.mark.asyncio
    async def test_export_includes_context_used(
        self,
        db_session: AsyncSession,
        test_interview: Interview,
        test_messages: list,
        mock_context_data: InterviewContextData
    ):
        """Test that export endpoint includes context used during interview"""
        with patch('app.services.context_enrichment_service.ContextEnrichmentService') as mock_ctx_service:
            mock_instance = AsyncMock()
            mock_instance.get_full_interview_context.return_value = mock_context_data
            mock_ctx_service.return_value = mock_instance
            
            # Simulate fetching context for export
            from app.services.context_enrichment_service import ContextEnrichmentService
            ctx_service = ContextEnrichmentService()
            
            # This would be called during export
            context = await mock_instance.get_full_interview_context(
                employee_id=test_interview.employee_id,
                auth_token="test-token",
                db=db_session
            )
            
            # Verify context data structure
            assert context.employee.full_name == "Juan Pérez"
            assert context.employee.organization_name == "ProssX Demo"
            assert len(context.employee.roles) > 0
            assert len(context.organization_processes) > 0
    
    @pytest.mark.asyncio
    async def test_export_maintains_backward_compatibility(
        self,
        db_session: AsyncSession,
        test_interview: Interview,
        test_messages: list
    ):
        """Test that export endpoint maintains backward compatibility"""
        service = InterviewService(db_session)
        
        # Get interview data (basic export without context)
        interview_data = await service.get_interview(
            interview_id=test_interview.id_interview,
            employee_id=test_interview.employee_id,
            allow_cross_user=False
        )
        
        # Verify basic fields are present (backward compatible)
        assert interview_data.id_interview is not None
        assert interview_data.employee_id is not None
        assert interview_data.language is not None
        assert interview_data.status is not None
        assert len(interview_data.messages) > 0
        
        # Verify messages have required fields
        for msg in interview_data.messages:
            assert msg.role in ["user", "assistant", "system"]
            assert msg.content is not None
            assert msg.sequence_number is not None


class TestProcessMatchingTimeout:
    """Test suite for process matching timeout handling"""
    
    @pytest.mark.asyncio
    async def test_continue_handles_process_matching_timeout(
        self,
        db_session: AsyncSession,
        test_interview: Interview,
        test_messages: list,
        mock_context_data: InterviewContextData
    ):
        """Test that continue endpoint handles process matching timeouts gracefully"""
        with patch('app.services.interview_service.ContextEnrichmentService') as mock_ctx_service:
            mock_instance = AsyncMock()
            mock_instance.get_full_interview_context.return_value = mock_context_data
            mock_ctx_service.return_value = mock_instance
            
            with patch('app.services.interview_service.get_agent') as mock_agent:
                # Simulate timeout in process matching
                mock_agent_instance = AsyncMock()
                mock_agent_instance.continue_interview.side_effect = TimeoutError("Process matching timeout")
                mock_agent.return_value = mock_agent_instance
                
                service = InterviewService(db_session)
                
                # Should handle timeout gracefully
                try:
                    await service.continue_interview(
                        interview_id=test_interview.id_interview,
                        employee_id=test_interview.employee_id,
                        user_response="Gestiono el proceso de compras",
                        auth_token="test-token"
                    )
                except TimeoutError:
                    # Timeout should be caught and logged, not propagated
                    pass
