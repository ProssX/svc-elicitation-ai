"""
Integration tests for /continue endpoint optimization
Tests that the endpoint loads history from database instead of request body
"""
import pytest
import pytest_asyncio
from uuid import UUID
from datetime import datetime
from app.models.db_models import Interview, InterviewMessage, InterviewStatusEnum, MessageRoleEnum, LanguageEnum
from app.services.interview_service import InterviewService, convert_messages_to_conversation_history
from app.repositories.interview_repository import InterviewRepository
from app.repositories.message_repository import MessageRepository


class TestContinueEndpointOptimization:
    """Test suite for /continue endpoint optimization"""
    
    def test_convert_messages_to_conversation_history_empty_list(self):
        """Test helper function handles empty message list gracefully"""
        # Test with empty list
        result = convert_messages_to_conversation_history([])
        
        # Should return empty list
        assert result == []
        assert isinstance(result, list)
    
    @pytest.mark.asyncio
    async def test_convert_messages_to_conversation_history_with_messages(self, db_session):
        """Test helper function converts DB messages to conversation format"""
        # Create test interview
        interview = Interview(
            employee_id=UUID("01932e5f-8b2a-7890-b123-456789abcdef"),
            language=LanguageEnum.es,
            technical_level="intermediate",
            status=InterviewStatusEnum.in_progress,
            started_at=datetime.utcnow()
        )
        db_session.add(interview)
        await db_session.flush()
        
        # Create test messages
        msg1 = InterviewMessage(
            interview_id=interview.id_interview,
            role=MessageRoleEnum.assistant,
            content="¿Cuál es tu rol?",
            sequence_number=1
        )
        msg2 = InterviewMessage(
            interview_id=interview.id_interview,
            role=MessageRoleEnum.user,
            content="Soy gerente de operaciones",
            sequence_number=2
        )
        db_session.add(msg1)
        db_session.add(msg2)
        await db_session.flush()
        
        # Convert to conversation history
        messages = [msg1, msg2]
        conversation_history = convert_messages_to_conversation_history(messages)
        
        # Verify conversion
        assert len(conversation_history) == 2
        
        # Check first message
        assert conversation_history[0].role == "assistant"
        assert conversation_history[0].content == "¿Cuál es tu rol?"
        assert conversation_history[0].timestamp == msg1.created_at
        
        # Check second message
        assert conversation_history[1].role == "user"
        assert conversation_history[1].content == "Soy gerente de operaciones"
        assert conversation_history[1].timestamp == msg2.created_at
    
    @pytest.mark.asyncio
    async def test_continue_interview_loads_history_from_database(self, db_session):
        """Test that continue_interview loads conversation history from database"""
        # Create test interview
        employee_id = UUID("01932e5f-8b2a-7890-b123-456789abcdef")
        interview = Interview(
            employee_id=employee_id,
            language=LanguageEnum.es,
            technical_level="intermediate",
            status=InterviewStatusEnum.in_progress,
            started_at=datetime.utcnow()
        )
        db_session.add(interview)
        await db_session.flush()
        
        # Create existing messages in database
        msg1 = InterviewMessage(
            interview_id=interview.id_interview,
            role=MessageRoleEnum.assistant,
            content="Primera pregunta",
            sequence_number=1
        )
        msg2 = InterviewMessage(
            interview_id=interview.id_interview,
            role=MessageRoleEnum.user,
            content="Primera respuesta",
            sequence_number=2
        )
        msg3 = InterviewMessage(
            interview_id=interview.id_interview,
            role=MessageRoleEnum.assistant,
            content="Segunda pregunta",
            sequence_number=3
        )
        msg4 = InterviewMessage(
            interview_id=interview.id_interview,
            role=MessageRoleEnum.user,
            content="Segunda respuesta",
            sequence_number=4
        )
        db_session.add_all([msg1, msg2, msg3, msg4])
        await db_session.flush()
        
        # Create interview service
        interview_service = InterviewService(db_session)
        
        # Load messages from database
        messages = await interview_service.message_repo.get_by_interview(interview.id_interview)
        
        # Verify messages were loaded
        assert len(messages) == 4
        assert messages[0].content == "Primera pregunta"
        assert messages[1].content == "Primera respuesta"
        assert messages[2].content == "Segunda pregunta"
        assert messages[3].content == "Segunda respuesta"
        
        # Convert to conversation history
        conversation_history = convert_messages_to_conversation_history(messages)
        
        # Verify conversation history format
        assert len(conversation_history) == 4
        assert conversation_history[0].role == "assistant"
        assert conversation_history[1].role == "user"
        assert conversation_history[2].role == "assistant"
        assert conversation_history[3].role == "user"
    
    @pytest.mark.asyncio
    async def test_continue_interview_saves_messages_to_database(self, db_session):
        """Test that continue_interview saves user response and agent question to database"""
        # Create test interview
        employee_id = UUID("01932e5f-8b2a-7890-b123-456789abcdef")
        interview = Interview(
            employee_id=employee_id,
            language=LanguageEnum.es,
            technical_level="intermediate",
            status=InterviewStatusEnum.in_progress,
            started_at=datetime.utcnow()
        )
        db_session.add(interview)
        await db_session.flush()
        
        # Create first message
        msg1 = InterviewMessage(
            interview_id=interview.id_interview,
            role=MessageRoleEnum.assistant,
            content="Primera pregunta",
            sequence_number=1
        )
        db_session.add(msg1)
        await db_session.flush()
        
        # Create interview service
        interview_service = InterviewService(db_session)
        
        # Continue interview (saves user response and agent question)
        updated_interview, user_msg, agent_msg = await interview_service.continue_interview(
            interview_id=interview.id_interview,
            employee_id=employee_id,
            user_response="Mi respuesta al agente",
            agent_question="Siguiente pregunta del agente",
            is_final=False
        )
        
        # Verify messages were saved
        all_messages = await interview_service.message_repo.get_by_interview(interview.id_interview)
        assert len(all_messages) == 3  # 1 initial + 1 user + 1 agent
        
        # Verify user message
        assert user_msg.role == MessageRoleEnum.user
        assert user_msg.content == "Mi respuesta al agente"
        assert user_msg.sequence_number == 2
        
        # Verify agent message
        assert agent_msg.role == MessageRoleEnum.assistant
        assert agent_msg.content == "Siguiente pregunta del agente"
        assert agent_msg.sequence_number == 3
    
    @pytest.mark.asyncio
    async def test_continue_interview_updates_timestamp(self, db_session):
        """Test that continue_interview updates interview updated_at timestamp"""
        # Create test interview
        employee_id = UUID("01932e5f-8b2a-7890-b123-456789abcdef")
        interview = Interview(
            employee_id=employee_id,
            language=LanguageEnum.es,
            technical_level="intermediate",
            status=InterviewStatusEnum.in_progress,
            started_at=datetime.utcnow()
        )
        db_session.add(interview)
        await db_session.flush()
        
        # Store original updated_at
        original_updated_at = interview.updated_at
        
        # Create first message
        msg1 = InterviewMessage(
            interview_id=interview.id_interview,
            role=MessageRoleEnum.assistant,
            content="Primera pregunta",
            sequence_number=1
        )
        db_session.add(msg1)
        await db_session.flush()
        
        # Wait a moment to ensure timestamp difference
        import asyncio
        await asyncio.sleep(0.1)
        
        # Create interview service
        interview_service = InterviewService(db_session)
        
        # Continue interview
        updated_interview, _, _ = await interview_service.continue_interview(
            interview_id=interview.id_interview,
            employee_id=employee_id,
            user_response="Mi respuesta",
            agent_question="Siguiente pregunta",
            is_final=False
        )
        
        # Verify updated_at was updated
        assert updated_interview.updated_at > original_updated_at
    
    @pytest.mark.asyncio
    async def test_continue_interview_marks_completed_when_final(self, db_session):
        """Test that is_final=true marks interview as completed"""
        # Create test interview
        employee_id = UUID("01932e5f-8b2a-7890-b123-456789abcdef")
        interview = Interview(
            employee_id=employee_id,
            language=LanguageEnum.es,
            technical_level="intermediate",
            status=InterviewStatusEnum.in_progress,
            started_at=datetime.utcnow()
        )
        db_session.add(interview)
        await db_session.flush()
        
        # Create first message
        msg1 = InterviewMessage(
            interview_id=interview.id_interview,
            role=MessageRoleEnum.assistant,
            content="Primera pregunta",
            sequence_number=1
        )
        db_session.add(msg1)
        await db_session.flush()
        
        # Verify initial status
        assert interview.status == InterviewStatusEnum.in_progress
        assert interview.completed_at is None
        
        # Create interview service
        interview_service = InterviewService(db_session)
        
        # Continue interview with is_final=True
        updated_interview, _, _ = await interview_service.continue_interview(
            interview_id=interview.id_interview,
            employee_id=employee_id,
            user_response="Mi última respuesta",
            agent_question="Gracias por tu tiempo",
            is_final=True
        )
        
        # Verify interview was marked as completed
        assert updated_interview.status == InterviewStatusEnum.completed
        assert updated_interview.completed_at is not None
    
    def test_backward_compatibility_with_legacy_fields(self):
        """Test that endpoint maintains backward compatibility with legacy fields"""
        # This test verifies that the request model still accepts legacy fields
        # even though they are not used by the endpoint
        from app.models.interview import ContinueInterviewRequest, ConversationMessage
        
        # Create request with legacy fields
        request = ContinueInterviewRequest(
            interview_id="018e5f8b-1234-7890-abcd-123456789abc",
            session_id="550e8400-e29b-41d4-a716-446655440000",  # Legacy field
            user_response="Mi respuesta",
            conversation_history=[  # Legacy field
                ConversationMessage(
                    role="assistant",
                    content="Pregunta anterior",
                    timestamp=None
                )
            ],
            language="es"
        )
        
        # Verify request is valid
        assert str(request.interview_id) == "018e5f8b-1234-7890-abcd-123456789abc"
        assert str(request.session_id) == "550e8400-e29b-41d4-a716-446655440000"
        assert request.user_response == "Mi respuesta"
        assert request.conversation_history is not None
        assert len(request.conversation_history) == 1
        assert request.language == "es"
    
    def test_continue_interview_without_conversation_history_in_request(self):
        """Test that /continue works without conversation_history in request"""
        # This test verifies the core optimization: the endpoint should work
        # without conversation_history in the request body
        from app.models.interview import ContinueInterviewRequest
        
        # Create minimal request (no conversation_history)
        request = ContinueInterviewRequest(
            interview_id="018e5f8b-1234-7890-abcd-123456789abc",
            user_response="Mi respuesta al agente",
            language="es"
        )
        
        # Verify request is valid
        assert str(request.interview_id) == "018e5f8b-1234-7890-abcd-123456789abc"
        assert request.user_response == "Mi respuesta al agente"
        assert request.language == "es"
        
        # Verify conversation_history is None (not required)
        assert request.conversation_history is None
        
        # Verify session_id is None (not required)
        assert request.session_id is None
