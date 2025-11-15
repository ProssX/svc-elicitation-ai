"""
Unit tests for InterviewAgent (Enhanced with Context Awareness)

Tests interview start with enriched context, process mention detection,
process matching integration, and response with process match info.
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call
from uuid import uuid4
from datetime import datetime

from app.services.agent_service import InterviewAgent, get_agent
from app.models.interview import (
    ConversationMessage,
    InterviewResponse,
    InterviewContext,
    ProcessMatchInfo,
    ProcessMatchResult
)
from app.models.context import (
    InterviewContextData,
    EmployeeContextData,
    RoleContextData,
    ProcessContextData,
    InterviewHistorySummary
)


@pytest.fixture
def sample_employee_context():
    """Sample employee context for testing"""
    return EmployeeContextData(
        id=uuid4(),
        first_name="Juan",
        last_name="Pérez",
        full_name="Juan Pérez",
        organization_id=str(uuid4()),
        organization_name="ProssX Demo",
        roles=[
            RoleContextData(
                id=uuid4(),
                name="Gerente de Operaciones",
                description="Responsable de supervisar las operaciones diarias"
            )
        ],
        is_active=True
    )


@pytest.fixture
def sample_processes():
    """Sample existing processes for testing"""
    return [
        ProcessContextData(
            id=uuid4(),
            name="Proceso de Aprobación de Compras",
            type="operational",
            type_label="Operacional",
            is_active=True,
            created_at=datetime(2025, 1, 15, 10, 0, 0),
            updated_at=datetime(2025, 1, 20, 14, 30, 0)
        ),
        ProcessContextData(
            id=uuid4(),
            name="Gestión de Inventario",
            type="operational",
            type_label="Operacional",
            is_active=True,
            created_at=datetime(2025, 1, 10, 10, 0, 0),
            updated_at=datetime(2025, 1, 18, 14, 30, 0)
        )
    ]


@pytest.fixture
def sample_interview_context(sample_employee_context, sample_processes):
    """Sample complete interview context"""
    return InterviewContextData(
        employee=sample_employee_context,
        organization_processes=sample_processes,
        interview_history=InterviewHistorySummary(
            total_interviews=2,
            completed_interviews=1,
            last_interview_date=datetime(2025, 1, 20, 15, 0, 0),
            topics_covered=["Proceso de compras", "Gestión de inventario"]
        ),
        context_timestamp=datetime.utcnow()
    )


@pytest.fixture
def mock_agent_response():
    """Create a mock Strands agent response"""
    def create_response(text: str):
        return MagicMock(
            message={
                'content': [
                    {'text': text}
                ]
            }
        )
    return create_response


class TestStartInterviewWithContext:
    """Test suite for starting interviews with enriched context"""
    
    def test_start_interview_with_context_spanish(
        self,
        sample_interview_context,
        mock_agent_response
    ):
        """Test starting interview with context in Spanish"""
        agent = InterviewAgent()
        
        # Mock the Agent class and PromptBuilder
        with patch('app.services.agent_service.Agent') as mock_agent_class:
            with patch('app.services.agent_service.PromptBuilder.build_interview_prompt') as mock_prompt:
                mock_prompt.return_value = "Context-aware prompt"
                
                mock_agent_instance = MagicMock()
                mock_agent_instance.return_value = mock_agent_response(
                    "Hola Juan! ¿Cuál es tu función principal en ProssX Demo?"
                )
                mock_agent_class.return_value = mock_agent_instance
                
                result = agent.start_interview(
                    context=sample_interview_context,
                    language="es"
                )
                
                # Verify context-aware prompt was built
                mock_prompt.assert_called_once_with(
                    context=sample_interview_context,
                    language="es"
                )
                
                # Verify response
                assert isinstance(result, InterviewResponse)
                assert result.question_number == 1
                assert result.is_final is False
                assert len(result.question) > 0
                assert result.process_matches == []
    
    def test_start_interview_with_context_english(
        self,
        sample_interview_context,
        mock_agent_response
    ):
        """Test starting interview with context in English"""
        agent = InterviewAgent()
        
        with patch('app.services.agent_service.Agent') as mock_agent_class:
            with patch('app.services.agent_service.PromptBuilder.build_interview_prompt') as mock_prompt:
                mock_prompt.return_value = "Context-aware prompt"
                
                mock_agent_instance = MagicMock()
                mock_agent_instance.return_value = mock_agent_response(
                    "Hello Juan! What is your main function at ProssX Demo?"
                )
                mock_agent_class.return_value = mock_agent_instance
                
                result = agent.start_interview(
                    context=sample_interview_context,
                    language="en"
                )
                
                # Verify English prompt was built
                mock_prompt.assert_called_once_with(
                    context=sample_interview_context,
                    language="en"
                )
                
                assert isinstance(result, InterviewResponse)
    
    def test_start_interview_legacy_mode_without_context(
        self,
        mock_agent_response
    ):
        """Test starting interview in legacy mode without context"""
        agent = InterviewAgent()
        
        with patch('app.services.agent_service.Agent') as mock_agent_class:
            with patch('app.services.agent_service.get_interviewer_prompt') as mock_legacy_prompt:
                mock_legacy_prompt.return_value = "Legacy prompt"
                
                mock_agent_instance = MagicMock()
                mock_agent_instance.return_value = mock_agent_response(
                    "Hola! ¿Cuál es tu función?"
                )
                mock_agent_class.return_value = mock_agent_instance
                
                result = agent.start_interview(
                    user_name="Juan Pérez",
                    user_role="Gerente",
                    organization="ProssX Demo",
                    language="es"
                )
                
                # Verify legacy prompt was used
                mock_legacy_prompt.assert_called_once()
                
                assert isinstance(result, InterviewResponse)
                assert result.question_number == 1
    
    def test_start_interview_extracts_user_info_from_context(
        self,
        sample_interview_context,
        mock_agent_response
    ):
        """Test that user info is correctly extracted from context"""
        agent = InterviewAgent()
        
        with patch('app.services.agent_service.Agent') as mock_agent_class:
            with patch('app.services.agent_service.PromptBuilder.build_interview_prompt'):
                mock_agent_instance = MagicMock()
                mock_agent_instance.return_value = mock_agent_response("Question")
                mock_agent_class.return_value = mock_agent_instance
                
                result = agent.start_interview(
                    context=sample_interview_context,
                    language="es"
                )
                
                # Verify the agent was called with correct initial message
                # containing the user's name from context
                call_args = mock_agent_instance.call_args
                assert "Juan" in str(call_args)
                assert "ProssX Demo" in str(call_args)


class TestContinueInterviewWithProcessMatching:
    """Test suite for continuing interviews with process matching"""
    
    @pytest.mark.asyncio
    async def test_continue_interview_detects_process_mention(
        self,
        sample_interview_context,
        mock_agent_response
    ):
        """Test that process mentions are detected"""
        agent = InterviewAgent()
        
        conversation_history = [
            ConversationMessage(role="assistant", content="¿Cuál es tu función?"),
            ConversationMessage(role="user", content="Soy gerente")
        ]
        
        user_response = "Me encargo del proceso de aprobación de compras"
        
        with patch('app.services.agent_service.Agent') as mock_agent_class:
            with patch('app.services.agent_service.PromptBuilder.build_interview_prompt'):
                with patch('app.services.agent_service.get_matching_agent') as mock_get_agent:
                    # Mock process matching agent
                    mock_matching_agent = AsyncMock()
                    mock_matching_agent.match_process.return_value = ProcessMatchResult(
                        is_match=True,
                        matched_process_id=sample_interview_context.organization_processes[0].id,
                        matched_process_name="Proceso de Aprobación de Compras",
                        confidence_score=0.95,
                        reasoning="Coincidencia exacta",
                        suggested_clarifying_questions=[]
                    )
                    mock_get_agent.return_value = mock_matching_agent
                    
                    mock_agent_instance = MagicMock()
                    mock_agent_instance.return_value = mock_agent_response("¿Puedes contarme más?")
                    mock_agent_class.return_value = mock_agent_instance
                    
                    result = await agent.continue_interview(
                        user_response=user_response,
                        conversation_history=conversation_history,
                        context=sample_interview_context,
                        language="es"
                    )
                    
                    # Verify process matching was invoked
                    mock_matching_agent.match_process.assert_called_once()
                    
                    # Verify process match is in response
                    assert len(result.process_matches) == 1
                    assert result.process_matches[0].process_name == "Proceso de Aprobación de Compras"
                    assert result.process_matches[0].is_new is False
                    assert result.process_matches[0].confidence >= 0.9
    
    @pytest.mark.asyncio
    async def test_continue_interview_no_process_mention(
        self,
        sample_interview_context,
        mock_agent_response
    ):
        """Test that non-process responses don't trigger matching"""
        agent = InterviewAgent()
        
        conversation_history = [
            ConversationMessage(role="assistant", content="¿Cuál es tu función?")
        ]
        
        user_response = "Trabajo en el área de operaciones"
        
        with patch('app.services.agent_service.Agent') as mock_agent_class:
            with patch('app.services.agent_service.PromptBuilder.build_interview_prompt'):
                with patch('app.services.agent_service.get_matching_agent') as mock_get_agent:
                    mock_matching_agent = AsyncMock()
                    mock_get_agent.return_value = mock_matching_agent
                    
                    mock_agent_instance = MagicMock()
                    mock_agent_instance.return_value = mock_agent_response("¿Qué haces específicamente?")
                    mock_agent_class.return_value = mock_agent_instance
                    
                    result = await agent.continue_interview(
                        user_response=user_response,
                        conversation_history=conversation_history,
                        context=sample_interview_context,
                        language="es"
                    )
                    
                    # Verify process matching was NOT invoked
                    mock_matching_agent.match_process.assert_not_called()
                    
                    # Verify no process matches in response
                    assert len(result.process_matches) == 0
    
    @pytest.mark.asyncio
    async def test_continue_interview_process_no_match(
        self,
        sample_interview_context,
        mock_agent_response
    ):
        """Test process mention that doesn't match existing processes"""
        agent = InterviewAgent()
        
        conversation_history = [
            ConversationMessage(role="assistant", content="¿Qué procesos manejas?")
        ]
        
        user_response = "Manejo el proceso de gestión de nómina"
        
        with patch('app.services.agent_service.Agent') as mock_agent_class:
            with patch('app.services.agent_service.PromptBuilder.build_interview_prompt'):
                with patch('app.services.agent_service.get_matching_agent') as mock_get_agent:
                    # Mock no match result
                    mock_matching_agent = AsyncMock()
                    mock_matching_agent.match_process.return_value = ProcessMatchResult(
                        is_match=False,
                        matched_process_id=None,
                        matched_process_name=None,
                        confidence_score=0.0,
                        reasoning="No coincide con procesos existentes",
                        suggested_clarifying_questions=[]
                    )
                    mock_get_agent.return_value = mock_matching_agent
                    
                    mock_agent_instance = MagicMock()
                    mock_agent_instance.return_value = mock_agent_response("Cuéntame más sobre ese proceso")
                    mock_agent_class.return_value = mock_agent_instance
                    
                    result = await agent.continue_interview(
                        user_response=user_response,
                        conversation_history=conversation_history,
                        context=sample_interview_context,
                        language="es"
                    )
                    
                    # Verify process matching was invoked
                    mock_matching_agent.match_process.assert_called_once()
                    
                    # Verify no process matches in response (no match found)
                    assert len(result.process_matches) == 0
    
    @pytest.mark.asyncio
    async def test_continue_interview_legacy_mode(
        self,
        mock_agent_response
    ):
        """Test continuing interview in legacy mode without context"""
        agent = InterviewAgent()
        
        conversation_history = [
            ConversationMessage(role="assistant", content="¿Cuál es tu función?")
        ]
        
        user_response = "Soy gerente de operaciones"
        
        with patch('app.services.agent_service.Agent') as mock_agent_class:
            with patch('app.services.agent_service.get_interviewer_prompt') as mock_legacy_prompt:
                mock_legacy_prompt.return_value = "Legacy prompt"
                
                mock_agent_instance = MagicMock()
                mock_agent_instance.return_value = mock_agent_response("¿Qué haces?")
                mock_agent_class.return_value = mock_agent_instance
                
                result = await agent.continue_interview(
                    user_response=user_response,
                    conversation_history=conversation_history,
                    user_name="Juan",
                    user_role="Gerente",
                    organization="ProssX",
                    language="es"
                )
                
                # Verify legacy prompt was used
                mock_legacy_prompt.assert_called_once()
                
                # Verify no process matching in legacy mode
                assert len(result.process_matches) == 0


class TestProcessMentionDetection:
    """Test suite for process mention detection heuristic"""
    
    def test_mentions_process_spanish_keywords(self):
        """Test detection of Spanish process keywords"""
        agent = InterviewAgent()
        
        test_cases = [
            ("Me encargo del proceso de compras", True),
            ("Sigo el procedimiento de aprobación", True),
            ("El flujo de trabajo es complejo", True),
            ("Realizo actividades de gestión", True),
            ("Mi tarea principal es revisar", True),
            ("Trabajo en operaciones", False),
            ("Soy gerente", False),
            ("Uso Excel", False)
        ]
        
        for text, expected in test_cases:
            result = agent._mentions_process(text)
            assert result == expected, f"Failed for: {text}"
    
    def test_mentions_process_english_keywords(self):
        """Test detection of English process keywords"""
        agent = InterviewAgent()
        
        test_cases = [
            ("I handle the purchase process", True),
            ("I follow the approval procedure", True),
            ("The workflow is complex", True),
            ("I perform management activities", True),
            ("My main task is reviewing", True),
            ("I work in operations", True),
            ("I am a manager", False),
            ("I use Excel", False)
        ]
        
        for text, expected in test_cases:
            result = agent._mentions_process(text)
            assert result == expected, f"Failed for: {text}"
    
    def test_mentions_process_portuguese_keywords(self):
        """Test detection of Portuguese process keywords"""
        agent = InterviewAgent()
        
        test_cases = [
            ("Eu cuido do processo de compras", True),
            ("Sigo o procedimento de aprovação", True),
            ("O fluxo de trabalho é complexo", True),
            ("Realizo atividades de gestão", True),
            ("Minha tarefa principal é revisar", True),
            ("Trabalho com operação de sistemas", True),  # "operação" is a keyword
            ("Sou gerente", False),
            ("Uso Excel", False)
        ]
        
        for text, expected in test_cases:
            result = agent._mentions_process(text)
            assert result == expected, f"Failed for: {text}"
    
    def test_mentions_process_case_insensitive(self):
        """Test that detection is case-insensitive"""
        agent = InterviewAgent()
        
        assert agent._mentions_process("PROCESO DE COMPRAS") is True
        assert agent._mentions_process("Proceso De Compras") is True
        assert agent._mentions_process("proceso de compras") is True


class TestBuildContextAwarePrompt:
    """Test suite for building context-aware prompts"""
    
    def test_build_context_aware_prompt_calls_prompt_builder(
        self,
        sample_interview_context
    ):
        """Test that _build_context_aware_prompt uses PromptBuilder"""
        agent = InterviewAgent()
        
        with patch('app.services.agent_service.PromptBuilder.build_interview_prompt') as mock_build:
            mock_build.return_value = "Test prompt"
            
            result = agent._build_context_aware_prompt(
                context=sample_interview_context,
                language="es"
            )
            
            # Verify PromptBuilder was called with correct args
            mock_build.assert_called_once_with(
                context=sample_interview_context,
                language="es"
            )
            
            assert result == "Test prompt"
    
    def test_build_context_aware_prompt_different_languages(
        self,
        sample_interview_context
    ):
        """Test building prompts in different languages"""
        agent = InterviewAgent()
        
        languages = ["es", "en", "pt"]
        
        for lang in languages:
            with patch('app.services.agent_service.PromptBuilder.build_interview_prompt') as mock_build:
                mock_build.return_value = f"{lang} prompt"
                
                result = agent._build_context_aware_prompt(
                    context=sample_interview_context,
                    language=lang
                )
                
                # Verify correct language was passed
                call_args = mock_build.call_args
                assert call_args[1]['language'] == lang


class TestResponseWithProcessMatches:
    """Test suite for responses including process match info"""
    
    @pytest.mark.asyncio
    async def test_response_includes_process_match_info(
        self,
        sample_interview_context,
        mock_agent_response
    ):
        """Test that response includes process match information"""
        agent = InterviewAgent()
        
        conversation_history = []
        user_response = "Manejo el proceso de aprobación de compras"
        
        with patch('app.services.agent_service.Agent') as mock_agent_class:
            with patch('app.services.agent_service.PromptBuilder.build_interview_prompt'):
                with patch('app.services.agent_service.get_matching_agent') as mock_get_agent:
                    process_id = sample_interview_context.organization_processes[0].id
                    
                    mock_matching_agent = AsyncMock()
                    mock_matching_agent.match_process.return_value = ProcessMatchResult(
                        is_match=True,
                        matched_process_id=process_id,
                        matched_process_name="Proceso de Aprobación de Compras",
                        confidence_score=0.92,
                        reasoning="Match found",
                        suggested_clarifying_questions=[]
                    )
                    mock_get_agent.return_value = mock_matching_agent
                    
                    mock_agent_instance = MagicMock()
                    mock_agent_instance.return_value = mock_agent_response("Next question")
                    mock_agent_class.return_value = mock_agent_instance
                    
                    result = await agent.continue_interview(
                        user_response=user_response,
                        conversation_history=conversation_history,
                        context=sample_interview_context,
                        language="es"
                    )
                    
                    # Verify process match info structure
                    assert len(result.process_matches) == 1
                    match_info = result.process_matches[0]
                    
                    assert isinstance(match_info, ProcessMatchInfo)
                    assert match_info.process_id == process_id
                    assert match_info.process_name == "Proceso de Aprobación de Compras"
                    assert match_info.is_new is False
                    assert match_info.confidence == 0.92
    
    @pytest.mark.asyncio
    async def test_response_empty_process_matches_when_no_match(
        self,
        sample_interview_context,
        mock_agent_response
    ):
        """Test that process_matches is empty when no match found"""
        agent = InterviewAgent()
        
        conversation_history = []
        user_response = "Trabajo en el área de ventas"
        
        with patch('app.services.agent_service.Agent') as mock_agent_class:
            with patch('app.services.agent_service.PromptBuilder.build_interview_prompt'):
                mock_agent_instance = MagicMock()
                mock_agent_instance.return_value = mock_agent_response("Next question")
                mock_agent_class.return_value = mock_agent_instance
                
                result = await agent.continue_interview(
                    user_response=user_response,
                    conversation_history=conversation_history,
                    context=sample_interview_context,
                    language="es"
                )
                
                # Verify process_matches is empty
                assert result.process_matches == []


class TestGlobalAgentInstance:
    """Test suite for global agent instance"""
    
    def test_get_agent_returns_instance(self):
        """Test that get_agent returns an InterviewAgent instance"""
        agent = get_agent()
        assert isinstance(agent, InterviewAgent)
    
    def test_get_agent_returns_same_instance(self):
        """Test that get_agent returns the same instance (singleton)"""
        agent1 = get_agent()
        agent2 = get_agent()
        assert agent1 is agent2
