"""
Unit tests for ProcessMatchingAgent

Tests process matching logic, confidence scoring, timeout handling,
and multi-language support.
"""
import pytest
import pytest_asyncio
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime

from app.services.process_matching_agent import ProcessMatchingAgent, get_matching_agent
from app.models.context import ProcessContextData
from app.models.interview import ProcessMatchResult


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
        ),
        ProcessContextData(
            id=uuid4(),
            name="Proceso de Onboarding de Empleados",
            type="strategic",
            type_label="Estratégico",
            is_active=True,
            created_at=datetime(2025, 1, 5, 10, 0, 0),
            updated_at=datetime(2025, 1, 15, 14, 30, 0)
        )
    ]


@pytest.fixture
def mock_agent_response():
    """Create a mock agent response"""
    def create_response(json_content: str):
        return MagicMock(
            message={
                'content': [
                    {'text': json_content}
                ]
            }
        )
    return create_response


class TestMatchProcessExactMatch:
    """Test suite for exact process name matches"""
    
    @pytest.mark.asyncio
    async def test_exact_match_spanish(self, sample_processes, mock_agent_response):
        """Test exact match with Spanish process name"""
        agent = ProcessMatchingAgent()
        
        # Mock the agent call
        json_response = """
        {
            "is_match": true,
            "matched_process_name": "Proceso de Aprobación de Compras",
            "confidence_score": 0.95,
            "reasoning": "El nombre es prácticamente idéntico",
            "suggested_clarifying_questions": [
                "¿Te referís al proceso de aprobación de compras que ya tenemos registrado?"
            ]
        }
        """
        
        with patch.object(agent, '_perform_matching') as mock_perform:
            mock_perform.return_value = ProcessMatchResult(
                is_match=True,
                matched_process_id=sample_processes[0].id,
                matched_process_name="Proceso de Aprobación de Compras",
                confidence_score=0.95,
                reasoning="El nombre es prácticamente idéntico",
                suggested_clarifying_questions=[
                    "¿Te referís al proceso de aprobación de compras que ya tenemos registrado?"
                ]
            )
            
            result = await agent.match_process(
                process_description="Proceso de Aprobación de Compras",
                existing_processes=sample_processes,
                language="es"
            )
            
            assert result.is_match is True
            assert result.matched_process_name == "Proceso de Aprobación de Compras"
            assert result.confidence_score >= 0.9
            assert result.matched_process_id == sample_processes[0].id
            assert len(result.suggested_clarifying_questions) > 0
    
    @pytest.mark.asyncio
    async def test_exact_match_english(self, mock_agent_response):
        """Test exact match with English process name"""
        agent = ProcessMatchingAgent()
        
        processes = [
            ProcessContextData(
                id=uuid4(),
                name="Purchase Approval Process",
                type="operational",
                type_label="Operational",
                is_active=True,
                created_at=datetime(2025, 1, 15, 10, 0, 0),
                updated_at=datetime(2025, 1, 20, 14, 30, 0)
            )
        ]
        
        with patch.object(agent, '_perform_matching') as mock_perform:
            mock_perform.return_value = ProcessMatchResult(
                is_match=True,
                matched_process_id=processes[0].id,
                matched_process_name="Purchase Approval Process",
                confidence_score=0.95,
                reasoning="The name is practically identical",
                suggested_clarifying_questions=[
                    "Are you referring to the purchase approval process we already have registered?"
                ]
            )
            
            result = await agent.match_process(
                process_description="Purchase Approval Process",
                existing_processes=processes,
                language="en"
            )
            
            assert result.is_match is True
            assert result.matched_process_name == "Purchase Approval Process"
            assert result.confidence_score >= 0.9
    
    @pytest.mark.asyncio
    async def test_exact_match_portuguese(self, mock_agent_response):
        """Test exact match with Portuguese process name"""
        agent = ProcessMatchingAgent()
        
        processes = [
            ProcessContextData(
                id=uuid4(),
                name="Processo de Aprovação de Compras",
                type="operational",
                type_label="Operacional",
                is_active=True,
                created_at=datetime(2025, 1, 15, 10, 0, 0),
                updated_at=datetime(2025, 1, 20, 14, 30, 0)
            )
        ]
        
        with patch.object(agent, '_perform_matching') as mock_perform:
            mock_perform.return_value = ProcessMatchResult(
                is_match=True,
                matched_process_id=processes[0].id,
                matched_process_name="Processo de Aprovação de Compras",
                confidence_score=0.95,
                reasoning="O nome é praticamente idêntico",
                suggested_clarifying_questions=[
                    "Você está se referindo ao processo de aprovação de compras que já temos registrado?"
                ]
            )
            
            result = await agent.match_process(
                process_description="Processo de Aprovação de Compras",
                existing_processes=processes,
                language="pt"
            )
            
            assert result.is_match is True
            assert result.matched_process_name == "Processo de Aprovação de Compras"
            assert result.confidence_score >= 0.9


class TestMatchProcessSimilarMatch:
    """Test suite for similar/semantic process matches"""
    
    @pytest.mark.asyncio
    async def test_semantic_match_spanish(self, sample_processes):
        """Test semantic match with different wording in Spanish"""
        agent = ProcessMatchingAgent()
        
        with patch.object(agent, '_perform_matching') as mock_perform:
            mock_perform.return_value = ProcessMatchResult(
                is_match=True,
                matched_process_id=sample_processes[0].id,
                matched_process_name="Proceso de Aprobación de Compras",
                confidence_score=0.85,
                reasoning="Autorizar solicitud de compra es semánticamente equivalente a aprobar compras",
                suggested_clarifying_questions=[
                    "¿Esto que me contás es parte del proceso de aprobación de compras?",
                    "¿Es el mismo proceso o es algo diferente?"
                ]
            )
            
            result = await agent.match_process(
                process_description="Cuando tengo que autorizar una solicitud de compra",
                existing_processes=sample_processes,
                language="es"
            )
            
            assert result.is_match is True
            assert result.matched_process_name == "Proceso de Aprobación de Compras"
            assert 0.7 <= result.confidence_score < 0.95
            assert len(result.suggested_clarifying_questions) > 0
    
    @pytest.mark.asyncio
    async def test_partial_match_lower_confidence(self, sample_processes):
        """Test partial match with lower confidence score"""
        agent = ProcessMatchingAgent()
        
        with patch.object(agent, '_perform_matching') as mock_perform:
            mock_perform.return_value = ProcessMatchResult(
                is_match=True,
                matched_process_id=sample_processes[1].id,
                matched_process_name="Gestión de Inventario",
                confidence_score=0.65,
                reasoning="Podría estar relacionado con gestión de inventario pero no es claro",
                suggested_clarifying_questions=[
                    "¿Este proceso está relacionado con la gestión de inventario?",
                    "¿Es parte del proceso de inventario o es independiente?"
                ]
            )
            
            result = await agent.match_process(
                process_description="Reviso el stock de productos",
                existing_processes=sample_processes,
                language="es"
            )
            
            assert result.is_match is True
            assert result.confidence_score < 0.8
            assert len(result.suggested_clarifying_questions) > 0
    
    @pytest.mark.asyncio
    async def test_case_insensitive_matching(self, sample_processes):
        """Test that process name matching is case-insensitive"""
        agent = ProcessMatchingAgent()
        
        with patch.object(agent, '_perform_matching') as mock_perform:
            mock_perform.return_value = ProcessMatchResult(
                is_match=True,
                matched_process_id=sample_processes[0].id,
                matched_process_name="proceso de aprobación de compras",
                confidence_score=0.95,
                reasoning="Coincidencia exacta (case-insensitive)",
                suggested_clarifying_questions=[]
            )
            
            result = await agent.match_process(
                process_description="PROCESO DE APROBACIÓN DE COMPRAS",
                existing_processes=sample_processes,
                language="es"
            )
            
            # Should find the process ID despite case difference
            assert result.matched_process_id == sample_processes[0].id


class TestMatchProcessNoMatch:
    """Test suite for no match scenarios"""
    
    @pytest.mark.asyncio
    async def test_no_match_different_process(self, sample_processes):
        """Test no match when describing a completely different process"""
        agent = ProcessMatchingAgent()
        
        with patch.object(agent, '_perform_matching') as mock_perform:
            mock_perform.return_value = ProcessMatchResult(
                is_match=False,
                matched_process_id=None,
                matched_process_name=None,
                confidence_score=0.0,
                reasoning="Son procesos completamente diferentes. Gestión de nómina no tiene relación con los procesos existentes",
                suggested_clarifying_questions=[]
            )
            
            result = await agent.match_process(
                process_description="Proceso de gestión de nómina y pagos",
                existing_processes=sample_processes,
                language="es"
            )
            
            assert result.is_match is False
            assert result.matched_process_id is None
            assert result.matched_process_name is None
            assert result.confidence_score == 0.0
            assert len(result.suggested_clarifying_questions) == 0
    
    @pytest.mark.asyncio
    async def test_no_match_empty_processes_list(self):
        """Test no match when no existing processes"""
        agent = ProcessMatchingAgent()
        
        result = await agent.match_process(
            process_description="Cualquier proceso",
            existing_processes=[],
            language="es"
        )
        
        assert result.is_match is False
        assert result.matched_process_id is None
        assert result.confidence_score == 0.0
        assert "no hay procesos" in result.reasoning.lower() or "no processes" in result.reasoning.lower()
    
    @pytest.mark.asyncio
    async def test_no_match_vague_description(self, sample_processes):
        """Test no match with vague process description"""
        agent = ProcessMatchingAgent()
        
        with patch.object(agent, '_perform_matching') as mock_perform:
            mock_perform.return_value = ProcessMatchResult(
                is_match=False,
                matched_process_id=None,
                matched_process_name=None,
                confidence_score=0.0,
                reasoning="La descripción es demasiado vaga para determinar una coincidencia",
                suggested_clarifying_questions=[]
            )
            
            result = await agent.match_process(
                process_description="Hago cosas",
                existing_processes=sample_processes,
                language="es"
            )
            
            assert result.is_match is False


class TestConfidenceScoring:
    """Test suite for confidence score accuracy"""
    
    @pytest.mark.asyncio
    async def test_confidence_score_range(self, sample_processes):
        """Test that confidence scores are within valid range"""
        agent = ProcessMatchingAgent()
        
        test_cases = [
            ("Proceso de Aprobación de Compras", 0.95),
            ("Autorizar compras", 0.80),
            ("Revisar solicitudes", 0.60),
            ("Proceso diferente", 0.0)
        ]
        
        for description, expected_confidence in test_cases:
            with patch.object(agent, '_perform_matching') as mock_perform:
                mock_perform.return_value = ProcessMatchResult(
                    is_match=expected_confidence > 0.5,
                    matched_process_id=sample_processes[0].id if expected_confidence > 0.5 else None,
                    matched_process_name="Proceso de Aprobación de Compras" if expected_confidence > 0.5 else None,
                    confidence_score=expected_confidence,
                    reasoning="Test reasoning",
                    suggested_clarifying_questions=[]
                )
                
                result = await agent.match_process(
                    process_description=description,
                    existing_processes=sample_processes,
                    language="es"
                )
                
                assert 0.0 <= result.confidence_score <= 1.0
                assert result.confidence_score == expected_confidence
    
    @pytest.mark.asyncio
    async def test_high_confidence_exact_match(self, sample_processes):
        """Test that exact matches have high confidence"""
        agent = ProcessMatchingAgent()
        
        with patch.object(agent, '_perform_matching') as mock_perform:
            mock_perform.return_value = ProcessMatchResult(
                is_match=True,
                matched_process_id=sample_processes[0].id,
                matched_process_name="Proceso de Aprobación de Compras",
                confidence_score=0.95,
                reasoning="Coincidencia exacta",
                suggested_clarifying_questions=[]
            )
            
            result = await agent.match_process(
                process_description="Proceso de Aprobación de Compras",
                existing_processes=sample_processes,
                language="es"
            )
            
            assert result.confidence_score >= 0.9
    
    @pytest.mark.asyncio
    async def test_medium_confidence_semantic_match(self, sample_processes):
        """Test that semantic matches have medium confidence"""
        agent = ProcessMatchingAgent()
        
        with patch.object(agent, '_perform_matching') as mock_perform:
            mock_perform.return_value = ProcessMatchResult(
                is_match=True,
                matched_process_id=sample_processes[0].id,
                matched_process_name="Proceso de Aprobación de Compras",
                confidence_score=0.75,
                reasoning="Coincidencia semántica",
                suggested_clarifying_questions=[]
            )
            
            result = await agent.match_process(
                process_description="Autorizar solicitudes de compra",
                existing_processes=sample_processes,
                language="es"
            )
            
            assert 0.6 <= result.confidence_score < 0.9


class TestTimeoutHandling:
    """Test suite for timeout handling"""
    
    @pytest.mark.asyncio
    async def test_timeout_returns_no_match(self, sample_processes):
        """Test that timeout returns no match result"""
        agent = ProcessMatchingAgent()
        agent.timeout = 0.1  # Very short timeout
        
        # Mock _perform_matching to take longer than timeout
        async def slow_matching(*args, **kwargs):
            await asyncio.sleep(0.5)
            return ProcessMatchResult(
                is_match=True,
                matched_process_id=sample_processes[0].id,
                matched_process_name="Test",
                confidence_score=0.9,
                reasoning="Should not reach here",
                suggested_clarifying_questions=[]
            )
        
        with patch.object(agent, '_perform_matching', side_effect=slow_matching):
            result = await agent.match_process(
                process_description="Test process",
                existing_processes=sample_processes,
                language="es"
            )
            
            assert result.is_match is False
            assert result.confidence_score == 0.0
            assert "tiempo" in result.reasoning.lower() or "timeout" in result.reasoning.lower()
    
    @pytest.mark.asyncio
    async def test_timeout_does_not_raise_exception(self, sample_processes):
        """Test that timeout is handled gracefully without raising exception"""
        agent = ProcessMatchingAgent()
        agent.timeout = 0.1
        
        async def slow_matching(*args, **kwargs):
            await asyncio.sleep(0.5)
            return ProcessMatchResult(
                is_match=True,
                matched_process_id=None,
                matched_process_name=None,
                confidence_score=0.0,
                reasoning="",
                suggested_clarifying_questions=[]
            )
        
        with patch.object(agent, '_perform_matching', side_effect=slow_matching):
            # Should not raise exception
            result = await agent.match_process(
                process_description="Test",
                existing_processes=sample_processes,
                language="es"
            )
            
            assert isinstance(result, ProcessMatchResult)
    
    @pytest.mark.asyncio
    async def test_fast_matching_completes_before_timeout(self, sample_processes):
        """Test that fast matching completes successfully"""
        agent = ProcessMatchingAgent()
        agent.timeout = 3.0  # Normal timeout
        
        with patch.object(agent, '_perform_matching') as mock_perform:
            mock_perform.return_value = ProcessMatchResult(
                is_match=True,
                matched_process_id=sample_processes[0].id,
                matched_process_name="Proceso de Aprobación de Compras",
                confidence_score=0.95,
                reasoning="Fast match",
                suggested_clarifying_questions=[]
            )
            
            result = await agent.match_process(
                process_description="Proceso de Aprobación de Compras",
                existing_processes=sample_processes,
                language="es"
            )
            
            assert result.is_match is True
            assert "timeout" not in result.reasoning.lower()


class TestMultiLanguageSupport:
    """Test suite for multi-language support"""
    
    @pytest.mark.asyncio
    async def test_spanish_language_support(self, sample_processes):
        """Test Spanish language support"""
        agent = ProcessMatchingAgent()
        
        with patch('app.services.process_matching_agent.PromptBuilder.build_process_matching_prompt') as mock_build:
            mock_build.return_value = "Spanish prompt"
            
            with patch('app.services.process_matching_agent.Agent') as mock_agent_class:
                mock_agent_instance = MagicMock()
                mock_agent_instance.return_value = MagicMock(
                    message={'content': [{'text': '{"is_match": false, "confidence_score": 0.0, "reasoning": "Test"}'}]}
                )
                mock_agent_class.return_value = mock_agent_instance
                
                await agent.match_process(
                    process_description="Test",
                    existing_processes=sample_processes,
                    language="es"
                )
                
                # Verify Spanish prompt was built
                mock_build.assert_called_once()
                call_args = mock_build.call_args
                assert call_args[1]['language'] == "es"
    
    @pytest.mark.asyncio
    async def test_english_language_support(self):
        """Test English language support"""
        agent = ProcessMatchingAgent()
        
        processes = [
            ProcessContextData(
                id=uuid4(),
                name="Purchase Approval",
                type="operational",
                type_label="Operational",
                is_active=True,
                created_at=datetime(2025, 1, 15, 10, 0, 0),
                updated_at=datetime(2025, 1, 20, 14, 30, 0)
            )
        ]
        
        with patch('app.services.process_matching_agent.PromptBuilder.build_process_matching_prompt') as mock_build:
            mock_build.return_value = "English prompt"
            
            with patch('app.services.process_matching_agent.Agent') as mock_agent_class:
                mock_agent_instance = MagicMock()
                mock_agent_instance.return_value = MagicMock(
                    message={'content': [{'text': '{"is_match": false, "confidence_score": 0.0, "reasoning": "Test"}'}]}
                )
                mock_agent_class.return_value = mock_agent_instance
                
                await agent.match_process(
                    process_description="Test",
                    existing_processes=processes,
                    language="en"
                )
                
                # Verify English prompt was built
                mock_build.assert_called_once()
                call_args = mock_build.call_args
                assert call_args[1]['language'] == "en"
    
    @pytest.mark.asyncio
    async def test_portuguese_language_support(self):
        """Test Portuguese language support"""
        agent = ProcessMatchingAgent()
        
        processes = [
            ProcessContextData(
                id=uuid4(),
                name="Aprovação de Compras",
                type="operational",
                type_label="Operacional",
                is_active=True,
                created_at=datetime(2025, 1, 15, 10, 0, 0),
                updated_at=datetime(2025, 1, 20, 14, 30, 0)
            )
        ]
        
        with patch('app.services.process_matching_agent.PromptBuilder.build_process_matching_prompt') as mock_build:
            mock_build.return_value = "Portuguese prompt"
            
            with patch('app.services.process_matching_agent.Agent') as mock_agent_class:
                mock_agent_instance = MagicMock()
                mock_agent_instance.return_value = MagicMock(
                    message={'content': [{'text': '{"is_match": false, "confidence_score": 0.0, "reasoning": "Test"}'}]}
                )
                mock_agent_class.return_value = mock_agent_instance
                
                await agent.match_process(
                    process_description="Test",
                    existing_processes=processes,
                    language="pt"
                )
                
                # Verify Portuguese prompt was built
                mock_build.assert_called_once()
                call_args = mock_build.call_args
                assert call_args[1]['language'] == "pt"
    
    @pytest.mark.asyncio
    async def test_error_messages_in_correct_language(self):
        """Test that error messages are in the correct language"""
        agent = ProcessMatchingAgent()
        
        # Test Spanish
        result_es = await agent.match_process(
            process_description="Test",
            existing_processes=[],
            language="es"
        )
        assert any(word in result_es.reasoning.lower() for word in ["no hay", "procesos", "organización"])
        
        # Test English
        result_en = await agent.match_process(
            process_description="Test",
            existing_processes=[],
            language="en"
        )
        assert any(word in result_en.reasoning.lower() for word in ["no", "processes", "organization"])
        
        # Test Portuguese
        result_pt = await agent.match_process(
            process_description="Test",
            existing_processes=[],
            language="pt"
        )
        assert any(word in result_pt.reasoning.lower() for word in ["não", "processos", "organização"])


class TestErrorHandling:
    """Test suite for error handling"""
    
    @pytest.mark.asyncio
    async def test_json_parsing_error_returns_no_match(self, sample_processes):
        """Test that JSON parsing errors return no match"""
        agent = ProcessMatchingAgent()
        
        # Mock agent to return invalid JSON
        with patch('app.services.process_matching_agent.Agent') as mock_agent_class:
            mock_agent_instance = MagicMock()
            mock_agent_instance.return_value = MagicMock(
                message={'content': [{'text': 'Invalid JSON {{{'}]}
            )
            mock_agent_class.return_value = mock_agent_instance
            
            result = await agent.match_process(
                process_description="Test",
                existing_processes=sample_processes,
                language="es"
            )
            
            assert result.is_match is False
            assert result.confidence_score == 0.0
    
    @pytest.mark.asyncio
    async def test_agent_exception_returns_no_match(self, sample_processes):
        """Test that agent exceptions return no match"""
        agent = ProcessMatchingAgent()
        
        with patch.object(agent, '_perform_matching', side_effect=Exception("Agent error")):
            result = await agent.match_process(
                process_description="Test",
                existing_processes=sample_processes,
                language="es"
            )
            
            assert result.is_match is False
            assert result.confidence_score == 0.0
    
    @pytest.mark.asyncio
    async def test_process_id_not_found_returns_none(self, sample_processes):
        """Test that unmatched process names return None for ID"""
        agent = ProcessMatchingAgent()
        
        with patch.object(agent, '_perform_matching') as mock_perform:
            mock_perform.return_value = ProcessMatchResult(
                is_match=True,
                matched_process_id=None,
                matched_process_name="Nonexistent Process",
                confidence_score=0.8,
                reasoning="Test",
                suggested_clarifying_questions=[]
            )
            
            result = await agent.match_process(
                process_description="Test",
                existing_processes=sample_processes,
                language="es"
            )
            
            # Should not find ID for nonexistent process name
            assert result.matched_process_id is None


class TestGlobalAgentInstance:
    """Test suite for global agent instance"""
    
    def test_get_matching_agent_returns_instance(self):
        """Test that get_matching_agent returns an instance"""
        agent = get_matching_agent()
        assert isinstance(agent, ProcessMatchingAgent)
    
    def test_get_matching_agent_returns_same_instance(self):
        """Test that get_matching_agent returns the same instance"""
        agent1 = get_matching_agent()
        agent2 = get_matching_agent()
        assert agent1 is agent2


class TestJSONParsing:
    """Test suite for JSON response parsing"""
    
    def test_parse_pure_json(self):
        """Test parsing pure JSON response"""
        agent = ProcessMatchingAgent()
        
        json_str = '{"is_match": true, "confidence_score": 0.9}'
        result = agent._parse_json_response(json_str)
        
        assert result["is_match"] is True
        assert result["confidence_score"] == 0.9
    
    def test_parse_json_with_markdown(self):
        """Test parsing JSON wrapped in markdown code blocks"""
        agent = ProcessMatchingAgent()
        
        json_str = '''```json
        {"is_match": true, "confidence_score": 0.9}
        ```'''
        result = agent._parse_json_response(json_str)
        
        assert result["is_match"] is True
    
    def test_parse_json_with_extra_text(self):
        """Test parsing JSON with surrounding text"""
        agent = ProcessMatchingAgent()
        
        json_str = 'Here is the result: {"is_match": false, "confidence_score": 0.0} end'
        result = agent._parse_json_response(json_str)
        
        assert result["is_match"] is False
    
    def test_parse_invalid_json_raises_error(self):
        """Test that invalid JSON raises ValueError"""
        agent = ProcessMatchingAgent()
        
        with pytest.raises((ValueError, Exception)):
            agent._parse_json_response("Not valid JSON at all")


class TestProcessIdFinding:
    """Test suite for finding process IDs by name"""
    
    def test_find_process_id_exact_match(self, sample_processes):
        """Test finding process ID with exact name match"""
        agent = ProcessMatchingAgent()
        
        process_id = agent._find_process_id(
            "Proceso de Aprobación de Compras",
            sample_processes
        )
        
        assert process_id == sample_processes[0].id
    
    def test_find_process_id_case_insensitive(self, sample_processes):
        """Test finding process ID with case-insensitive match"""
        agent = ProcessMatchingAgent()
        
        process_id = agent._find_process_id(
            "proceso de aprobación de compras",
            sample_processes
        )
        
        assert process_id == sample_processes[0].id
    
    def test_find_process_id_not_found(self, sample_processes):
        """Test that nonexistent process name returns None"""
        agent = ProcessMatchingAgent()
        
        process_id = agent._find_process_id(
            "Nonexistent Process",
            sample_processes
        )
        
        assert process_id is None
    
    def test_find_process_id_empty_list(self):
        """Test finding process ID in empty list"""
        agent = ProcessMatchingAgent()
        
        process_id = agent._find_process_id(
            "Any Process",
            []
        )
        
        assert process_id is None
