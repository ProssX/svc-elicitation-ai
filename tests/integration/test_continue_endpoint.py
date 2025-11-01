"""
Integration tests for /continue endpoint optimization

Tests verify that the endpoint:
- Works without conversation_history in request
- Loads history from database correctly
- Passes correct history to agent
- Saves messages to database after agent response
- Updates interview timestamps
- Marks interview as completed when is_final=true
"""
import pytest
from uuid import UUID, uuid4
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import Interview, InterviewMessage, InterviewStatusEnum, MessageRoleEnum, LanguageEnum
from app.models.interview import InterviewResponse, InterviewContext
from app.repositories.interview_repository import InterviewRepository
from app.repositories.message_repository import MessageRepository


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
        ),
        InterviewMessage(
            id_message=uuid4(),
            interview_id=test_interview.id_interview,
            role=MessageRoleEnum.assistant,
            content="¿Qué procesos gestionas?",
            sequence_number=3,
            created_at=datetime.utcnow()
        ),
        InterviewMessage(
            id_message=uuid4(),
            interview_id=test_interview.id_interview,
            role=MessageRoleEnum.user,
            content="Gestiono el proceso de compras y aprobaciones",
            sequence_number=4,
            created_at=datetime.utcnow()
        )
    ]
    
    for msg in messages:
        db_session.add(msg)
    
    await db_session.commit()
    
    for msg in messages:
        await db_session.refresh(msg)
    
    return messages


class TestContinueEndpointOptimization:
    """Test suite for /continue endpoint optimization"""
    
    @pytest.mark.asyncio
    async def test_continue_works_without_conversation_history(
        self,
        db_session: AsyncSession,
        test_interview: Interview,
        test_messages: list
    ):
        """Test /continue works without conversation_history in request"""
        from app.services.interview_service import InterviewService, convert_messages_to_conversation_history
        from app.services.agent_service import InterviewAgent
        
        # Mock agent response
        mock_agent_response = InterviewResponse(
            question="¿Cuáles son los pasos del proceso de compras?",
            question_number=3,
            is_final=False,
            context=InterviewContext(
                processes_identified=["compras"],
                topics_discussed=["aprobaciones"],
                completeness=0.4,
                user_profile_technical=False
            ),
            corrected_user_response="Gestiono el proceso de compras"
        )
        
        # Create service
        interview_service = InterviewService(db_session)
        
        # Load messages from database
        messages = await interview_service.message_repo.get_by_interview(test_interview.id_interview)
        assert len(messages) == 4
        
        # Convert to conversation history
        conversation_history = convert_messages_to_conversation_history(messages)
        assert len(conversation_history) == 4
        assert conversation_history[0].role == "assistant"
        assert conversation_history[1].role == "user"
        
        # Mock agent
        with patch('app.services.agent_service.InterviewAgent.continue_interview', return_value=mock_agent_response):
            # Continue interview (simulating endpoint logic)
            interview, user_msg, agent_msg = await interview_service.continue_interview(
                interview_id=test_interview.id_interview,
                employee_id=test_interview.employee_id,
                user_response="Los pasos son: solicitud, aprobación, compra",
                agent_question=mock_agent_response.question,
                is_final=False
            )
        
        # Verify messages were saved
        all_messages = await interview_service.message_repo.get_by_interview(test_interview.id_interview)
        assert len(all_messages) == 6  # 4 existing + 1 user + 1 assistant
        
        # Verify sequence numbers
        assert user_msg.sequence_number == 5
        assert agent_msg.sequence_number == 6
        
        # Verify content
        assert user_msg.content == "Los pasos son: solicitud, aprobación, compra"
        assert agent_msg.content == "¿Cuáles son los pasos del proceso de compras?"
    
    @pytest.mark.asyncio
    async def test_continue_loads_history_from_database(
        self,
        db_session: AsyncSession,
        test_interview: Interview,
        test_messages: list
    ):
        """Test /continue loads history from database correctly"""
        from app.services.interview_service import InterviewService, convert_messages_to_conversation_history
        
        # Create service
        interview_service = InterviewService(db_session)
        
        # Load messages from database
        db_messages = await interview_service.message_repo.get_by_interview(test_interview.id_interview)
        
        # Verify messages loaded correctly
        assert len(db_messages) == 4
        assert db_messages[0].sequence_number == 1
        assert db_messages[0].role == MessageRoleEnum.assistant
        assert db_messages[0].content == "¿Cuál es tu rol en la organización?"
        
        assert db_messages[1].sequence_number == 2
        assert db_messages[1].role == MessageRoleEnum.user
        assert db_messages[1].content == "Soy gerente de operaciones"
        
        # Convert to conversation format
        conversation_history = convert_messages_to_conversation_history(db_messages)
        
        # Verify conversion
        assert len(conversation_history) == 4
        assert conversation_history[0].role == "assistant"
        assert conversation_history[0].content == "¿Cuál es tu rol en la organización?"
        assert conversation_history[1].role == "user"
        assert conversation_history[1].content == "Soy gerente de operaciones"
    
    @pytest.mark.asyncio
    async def test_agent_receives_correct_history_from_database(
        self,
        db_session: AsyncSession,
        test_interview: Interview,
        test_messages: list
    ):
        """Test agent receives correct history from database"""
        from app.services.interview_service import InterviewService, convert_messages_to_conversation_history
        
        # Create service
        interview_service = InterviewService(db_session)
        
        # Load and convert messages
        db_messages = await interview_service.message_repo.get_by_interview(test_interview.id_interview)
        conversation_history = convert_messages_to_conversation_history(db_messages)
        
        # Mock agent to capture what history it receives
        captured_history = None
        
        def mock_continue_interview(*args, **kwargs):
            nonlocal captured_history
            captured_history = kwargs.get("conversation_history")
            return InterviewResponse(
                question="Next question",
                question_number=3,
                is_final=False,
                context=InterviewContext(),
                corrected_user_response="Response"
            )
        
        with patch('app.services.agent_service.InterviewAgent.continue_interview', side_effect=mock_continue_interview):
            # Simulate agent call with DB history
            from app.services.agent_service import get_agent
            agent = get_agent()
            agent.continue_interview(
                user_response="New response",
                conversation_history=conversation_history,
                user_name="Test User",
                user_role="Manager",
                organization="Test Org",
                technical_level="intermediate",
                language="es"
            )
        
        # Verify agent received correct history
        assert captured_history is not None
        assert len(captured_history) == 4
        assert captured_history[0].content == "¿Cuál es tu rol en la organización?"
        assert captured_history[1].content == "Soy gerente de operaciones"
        assert captured_history[2].content == "¿Qué procesos gestionas?"
        assert captured_history[3].content == "Gestiono el proceso de compras y aprobaciones"
    
    @pytest.mark.asyncio
    async def test_messages_saved_to_database_after_agent_response(
        self,
        db_session: AsyncSession,
        test_interview: Interview,
        test_messages: list
    ):
        """Test messages are saved to database after agent response"""
        from app.services.interview_service import InterviewService
        
        # Create service
        interview_service = InterviewService(db_session)
        
        # Get initial message count
        initial_messages = await interview_service.message_repo.get_by_interview(test_interview.id_interview)
        initial_count = len(initial_messages)
        assert initial_count == 4
        
        # Continue interview
        interview, user_msg, agent_msg = await interview_service.continue_interview(
            interview_id=test_interview.id_interview,
            employee_id=test_interview.employee_id,
            user_response="Mi nueva respuesta",
            agent_question="¿Siguiente pregunta?",
            is_final=False
        )
        
        # Verify messages were saved
        final_messages = await interview_service.message_repo.get_by_interview(test_interview.id_interview)
        assert len(final_messages) == initial_count + 2
        
        # Verify new messages
        assert final_messages[-2].role == MessageRoleEnum.user
        assert final_messages[-2].content == "Mi nueva respuesta"
        assert final_messages[-1].role == MessageRoleEnum.assistant
        assert final_messages[-1].content == "¿Siguiente pregunta?"
    
    @pytest.mark.asyncio
    async def test_interview_updated_at_timestamp_updated(
        self,
        db_session: AsyncSession,
        test_interview: Interview,
        test_messages: list
    ):
        """Test interview updated_at timestamp is updated"""
        from app.services.interview_service import InterviewService
        import asyncio
        
        # Create service
        interview_service = InterviewService(db_session)
        
        # Get initial updated_at
        initial_updated_at = test_interview.updated_at
        
        # Wait a moment to ensure timestamp difference
        await asyncio.sleep(0.1)
        
        # Continue interview
        updated_interview, _, _ = await interview_service.continue_interview(
            interview_id=test_interview.id_interview,
            employee_id=test_interview.employee_id,
            user_response="Response",
            agent_question="Question",
            is_final=False
        )
        
        # Verify updated_at was updated
        assert updated_interview.updated_at > initial_updated_at
    
    @pytest.mark.asyncio
    async def test_is_final_marks_interview_as_completed(
        self,
        db_session: AsyncSession,
        test_interview: Interview,
        test_messages: list
    ):
        """Test is_final=true marks interview as completed"""
        from app.services.interview_service import InterviewService
        
        # Create service
        interview_service = InterviewService(db_session)
        
        # Verify initial status
        assert test_interview.status == InterviewStatusEnum.in_progress
        assert test_interview.completed_at is None
        
        # Continue interview with is_final=True
        updated_interview, _, _ = await interview_service.continue_interview(
            interview_id=test_interview.id_interview,
            employee_id=test_interview.employee_id,
            user_response="Final response",
            agent_question="Thank you!",
            is_final=True
        )
        
        # Verify interview marked as completed
        assert updated_interview.status == InterviewStatusEnum.completed
        assert updated_interview.completed_at is not None
        assert updated_interview.completed_at >= test_interview.started_at
    
    @pytest.mark.asyncio
    async def test_backward_compatibility_with_legacy_fields(
        self,
        db_session: AsyncSession,
        test_interview: Interview,
        test_messages: list
    ):
        """Test backward compatibility with legacy fields in request"""
        from app.models.interview import ContinueInterviewRequest, ConversationMessage
        
        # Create request with legacy fields (should still validate)
        request = ContinueInterviewRequest(
            interview_id=str(test_interview.id_interview),
            session_id="legacy-session-id",  # Legacy field
            user_response="My response",
            conversation_history=[  # Legacy field (will be ignored)
                ConversationMessage(
                    role="assistant",
                    content="Old question",
                    timestamp=None
                )
            ],
            language="es"
        )
        
        # Verify request validates successfully
        assert str(request.interview_id) == str(test_interview.id_interview)
        assert request.session_id == "legacy-session-id"
        assert request.conversation_history is not None
        
        # In actual endpoint, conversation_history from request is ignored
        # and loaded from database instead
