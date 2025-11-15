"""
Integration tests for InterviewService with context enrichment

Tests verify that the service:
- Fetches context before starting interview
- Loads context when continuing interview
- Performs process matching during interview
- Creates process references when matches found
- Handles context loading failures gracefully
- Maintains performance under 3 seconds
"""
import pytest
from uuid import UUID, uuid4
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import Interview, InterviewMessage, InterviewStatusEnum, MessageRoleEnum, LanguageEnum
from app.models.interview import InterviewResponse, InterviewContext, ProcessMatchInfo
from app.models.context import (
    InterviewContextData,
    EmployeeContextData,
    RoleContextData,
    ProcessContextData,
    InterviewHistorySummary
)
from app.repositories.interview_repository import InterviewRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.process_reference_repository import ProcessReferenceRepository


@pytest.fixture
def mock_employee_context():
    """Create mock employee context data"""
    return EmployeeContextData(
        id=uuid4(),
        first_name="Juan",
        last_name="Pérez",
        full_name="Juan Pérez",
        organization_id="org-123",
        organization_name="Test Organization",
        roles=[
            RoleContextData(
                id=uuid4(),
                name="Operations Manager",
                description="Manages daily operations"
            )
        ],
        is_active=True
    )


@pytest.fixture
def mock_process_context():
    """Create mock process context data"""
    return [
        ProcessContextData(
            id=uuid4(),
            name="Purchase Approval Process",
            type="approval",
            type_label="Approval",
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        ),
        ProcessContextData(
            id=uuid4(),
            name="Invoice Processing",
            type="operational",
            type_label="Operational",
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    ]


@pytest.fixture
def mock_interview_context(mock_employee_context, mock_process_context):
    """Create complete mock interview context"""
    return InterviewContextData(
        employee=mock_employee_context,
        organization_processes=mock_process_context,
        interview_history=InterviewHistorySummary(
            total_interviews=2,
            completed_interviews=1,
            last_interview_date=datetime.utcnow(),
            topics_covered=["procurement", "approvals"]
        ),
        context_timestamp=datetime.utcnow()
    )


@pytest.fixture
async def test_interview(db_session: AsyncSession):
    """Create a test interview in the database"""
    interview = Interview(
        id_interview=uuid4(),
        employee_id=uuid4(),
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


class TestInterviewServiceContextIntegration:
    """Test suite for InterviewService with context enrichment"""
    
    @pytest.mark.asyncio
    async def test_start_interview_with_context_enrichment(
        self,
        db_session: AsyncSession,
        mock_interview_context: InterviewContextData
    ):
        """Test start_interview fetches context before starting"""
        from app.services.interview_service import InterviewService
        
        # Create service
        interview_service = InterviewService(db_session)
        
        # Mock context enrichment service
        mock_context_service = AsyncMock()
        mock_context_service.get_full_interview_context.return_value = mock_interview_context
        interview_service.context_enrichment_service = mock_context_service
        
        # Mock agent response
        mock_agent_response = InterviewResponse(
            question="Hola Juan, ¿cuéntame sobre tu rol?",
            question_number=1,
            is_final=False,
            context=InterviewContext(),
            process_matches=[]
        )
        
        # Mock agent
        mock_agent = Mock()
        mock_agent.start_interview.return_value = mock_agent_response
        interview_service.agent = mock_agent
        
        # Start interview
        employee_id = uuid4()
        interview, first_message = await interview_service.start_interview(
            employee_id=employee_id,
            language="es",
            technical_level="intermediate",
            auth_token="test-token"
        )
        
        # Verify context was fetched
        mock_context_service.get_full_interview_context.assert_called_once_with(
            employee_id=employee_id,
            auth_token="test-token",
            db=db_session
        )
        
        # Verify agent was called with context
        mock_agent.start_interview.assert_called_once()
        call_kwargs = mock_agent.start_interview.call_args[1]
        assert call_kwargs["context"] == mock_interview_context
        assert call_kwargs["language"] == "es"
        assert call_kwargs["technical_level"] == "intermediate"
        
        # Verify interview was created
        assert interview is not None
        assert interview.employee_id == employee_id
        assert interview.status == InterviewStatusEnum.in_progress
        
        # Verify first message was saved
        assert first_message is not None
        assert first_message.content == "Hola Juan, ¿cuéntame sobre tu rol?"
        assert first_message.sequence_number == 1
    
    @pytest.mark.asyncio
    async def test_continue_interview_with_process_matching(
        self,
        db_session: AsyncSession,
        test_interview: Interview,
        test_messages: list,
        mock_interview_context: InterviewContextData
    ):
        """Test continue_interview performs process matching"""
        from app.services.interview_service import InterviewService
        
        # Create service
        interview_service = InterviewService(db_session)
        
        # Mock context enrichment service
        mock_context_service = AsyncMock()
        mock_context_service.get_full_interview_context.return_value = mock_interview_context
        interview_service.context_enrichment_service = mock_context_service
        
        # Create process match
        process_match = ProcessMatchInfo(
            process_id=mock_interview_context.organization_processes[0].id,
            process_name="Purchase Approval Process",
            is_new=False,
            confidence=0.85
        )
        
        # Mock agent response with process match
        mock_agent_response = InterviewResponse(
            question="¿Puedes describir los pasos del proceso de aprobación?",
            question_number=2,
            is_final=False,
            context=InterviewContext(),
            process_matches=[process_match]
        )
        
        # Mock agent
        mock_agent = AsyncMock()
        mock_agent.continue_interview.return_value = mock_agent_response
        interview_service.agent = mock_agent
        
        # Continue interview
        interview, user_msg, agent_msg = await interview_service.continue_interview(
            interview_id=test_interview.id_interview,
            employee_id=test_interview.employee_id,
            user_response="Gestiono el proceso de aprobación de compras",
            auth_token="test-token"
        )
        
        # Verify context was loaded
        mock_context_service.get_full_interview_context.assert_called_once()
        
        # Verify agent was called with context
        mock_agent.continue_interview.assert_called_once()
        call_kwargs = mock_agent.continue_interview.call_args[1]
        assert call_kwargs["context"] == mock_interview_context
        
        # Verify messages were saved
        assert user_msg.content == "Gestiono el proceso de aprobación de compras"
        assert agent_msg.content == "¿Puedes describir los pasos del proceso de aprobación?"
        
        # Verify process reference was created
        process_refs = await interview_service.process_ref_repo.get_by_interview(
            test_interview.id_interview
        )
        assert len(process_refs) == 1
        assert process_refs[0].process_id == process_match.process_id
        assert process_refs[0].is_new_process == False
        assert float(process_refs[0].confidence_score) == 0.85
    
    @pytest.mark.asyncio
    async def test_process_reference_creation(
        self,
        db_session: AsyncSession,
        test_interview: Interview,
        test_messages: list,
        mock_interview_context: InterviewContextData
    ):
        """Test process references are created when matches found"""
        from app.services.interview_service import InterviewService
        
        # Create service
        interview_service = InterviewService(db_session)
        
        # Mock context enrichment service
        mock_context_service = AsyncMock()
        mock_context_service.get_full_interview_context.return_value = mock_interview_context
        interview_service.context_enrichment_service = mock_context_service
        
        # Create multiple process matches
        process_matches = [
            ProcessMatchInfo(
                process_id=mock_interview_context.organization_processes[0].id,
                process_name="Purchase Approval Process",
                is_new=False,
                confidence=0.90
            ),
            ProcessMatchInfo(
                process_id=mock_interview_context.organization_processes[1].id,
                process_name="Invoice Processing",
                is_new=False,
                confidence=0.75
            )
        ]
        
        # Mock agent response with multiple matches
        mock_agent_response = InterviewResponse(
            question="¿Cómo se relacionan estos procesos?",
            question_number=2,
            is_final=False,
            context=InterviewContext(),
            process_matches=process_matches
        )
        
        # Mock agent
        mock_agent = AsyncMock()
        mock_agent.continue_interview.return_value = mock_agent_response
        interview_service.agent = mock_agent
        
        # Continue interview
        await interview_service.continue_interview(
            interview_id=test_interview.id_interview,
            employee_id=test_interview.employee_id,
            user_response="Gestiono aprobaciones y facturas",
            auth_token="test-token"
        )
        
        # Verify both process references were created
        process_refs = await interview_service.process_ref_repo.get_by_interview(
            test_interview.id_interview
        )
        assert len(process_refs) == 2
        
        # Verify first reference
        assert process_refs[0].process_id == process_matches[0].process_id
        assert float(process_refs[0].confidence_score) == 0.90
        
        # Verify second reference
        assert process_refs[1].process_id == process_matches[1].process_id
        assert float(process_refs[1].confidence_score) == 0.75
    
    @pytest.mark.asyncio
    async def test_performance_under_3_seconds(
        self,
        db_session: AsyncSession,
        test_interview: Interview,
        test_messages: list,
        mock_interview_context: InterviewContextData
    ):
        """Test interview operations complete within 3 seconds"""
        from app.services.interview_service import InterviewService
        import time
        
        # Create service
        interview_service = InterviewService(db_session)
        
        # Mock context enrichment service (fast response)
        mock_context_service = AsyncMock()
        mock_context_service.get_full_interview_context.return_value = mock_interview_context
        interview_service.context_enrichment_service = mock_context_service
        
        # Mock agent response
        mock_agent_response = InterviewResponse(
            question="Next question",
            question_number=2,
            is_final=False,
            context=InterviewContext(),
            process_matches=[]
        )
        
        # Mock agent
        mock_agent = AsyncMock()
        mock_agent.continue_interview.return_value = mock_agent_response
        interview_service.agent = mock_agent
        
        # Measure time for continue_interview
        start_time = time.time()
        
        await interview_service.continue_interview(
            interview_id=test_interview.id_interview,
            employee_id=test_interview.employee_id,
            user_response="My response",
            auth_token="test-token"
        )
        
        elapsed_time = time.time() - start_time
        
        # Verify performance (should be well under 3 seconds with mocks)
        assert elapsed_time < 3.0, f"Operation took {elapsed_time:.2f}s, expected < 3.0s"
    
    @pytest.mark.asyncio
    async def test_graceful_degradation_on_context_failure(
        self,
        db_session: AsyncSession,
        test_interview: Interview,
        test_messages: list
    ):
        """Test interview continues when context loading fails"""
        from app.services.interview_service import InterviewService
        
        # Create service
        interview_service = InterviewService(db_session)
        
        # Mock context enrichment service to fail
        mock_context_service = AsyncMock()
        mock_context_service.get_full_interview_context.side_effect = Exception("Backend unavailable")
        interview_service.context_enrichment_service = mock_context_service
        
        # Mock agent response (without context)
        mock_agent_response = InterviewResponse(
            question="Next question",
            question_number=2,
            is_final=False,
            context=InterviewContext(),
            process_matches=[]
        )
        
        # Mock agent
        mock_agent = AsyncMock()
        mock_agent.continue_interview.return_value = mock_agent_response
        interview_service.agent = mock_agent
        
        # Continue interview should not raise exception
        interview, user_msg, agent_msg = await interview_service.continue_interview(
            interview_id=test_interview.id_interview,
            employee_id=test_interview.employee_id,
            user_response="My response",
            auth_token="test-token"
        )
        
        # Verify interview continued despite context failure
        assert interview is not None
        assert user_msg is not None
        assert agent_msg is not None
        
        # Verify agent was called with None context (graceful degradation)
        mock_agent.continue_interview.assert_called_once()
        call_kwargs = mock_agent.continue_interview.call_args[1]
        assert call_kwargs["context"] is None
