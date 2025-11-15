"""
Unit tests for PromptBuilder

Tests prompt generation with full context, minimal context, process list formatting,
token limit compliance, and multi-language support.
"""
import pytest
from datetime import datetime
from uuid import uuid4

from app.services.prompt_builder import PromptBuilder
from app.models.context import (
    InterviewContextData,
    EmployeeContextData,
    RoleContextData,
    ProcessContextData,
    InterviewHistorySummary
)


class TestPromptBuilderBasicFunctionality:
    """Test suite for basic prompt builder functionality"""
    
    def test_build_interview_prompt_with_full_context(self):
        """Test building interview prompt with complete context"""
        # Create full context
        context = InterviewContextData(
            employee=EmployeeContextData(
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
                topics_covered=["Proceso de compras", "Gestión de inventario"]
            ),
            context_timestamp=datetime.utcnow()
        )
        
        # Build prompt
        prompt = PromptBuilder.build_interview_prompt(context, language="es")
        
        # Verify prompt contains key elements
        assert "Juan Pérez" in prompt
        assert "Gerente de Operaciones" in prompt
        assert "ProssX Demo" in prompt
        assert "Proceso de Aprobación de Compras" in prompt
        assert "Historial de entrevistas" in prompt
        assert "Total de entrevistas: 2" in prompt
        assert "Agente ProssX" in prompt
        assert "ROL Y PERSONALIDAD" in prompt
    
    def test_build_interview_prompt_with_minimal_context(self):
        """Test building interview prompt with minimal context (no processes, no history)"""
        # Create minimal context
        context = InterviewContextData(
            employee=EmployeeContextData(
                id=uuid4(),
                first_name="María",
                last_name="González",
                full_name="María González",
                organization_id=str(uuid4()),
                organization_name="Acme Corp",
                roles=[],
                is_active=True
            ),
            organization_processes=[],
            interview_history=InterviewHistorySummary(
                total_interviews=0,
                completed_interviews=0,
                last_interview_date=None,
                topics_covered=[]
            ),
            context_timestamp=datetime.utcnow()
        )
        
        # Build prompt
        prompt = PromptBuilder.build_interview_prompt(context, language="es")
        
        # Verify prompt contains basic elements
        assert "María González" in prompt
        assert "Acme Corp" in prompt
        assert "No hay procesos registrados" in prompt
        assert "primera entrevista" in prompt
        assert "Agente ProssX" in prompt
    
    def test_build_interview_prompt_defaults_to_spanish(self):
        """Test that invalid language defaults to Spanish"""
        context = InterviewContextData(
            employee=EmployeeContextData(
                id=uuid4(),
                first_name="Test",
                last_name="User",
                full_name="Test User",
                organization_id=str(uuid4()),
                organization_name="Test Org",
                roles=[],
                is_active=True
            ),
            organization_processes=[],
            interview_history=InterviewHistorySummary(
                total_interviews=0,
                completed_interviews=0,
                last_interview_date=None,
                topics_covered=[]
            ),
            context_timestamp=datetime.utcnow()
        )
        
        prompt = PromptBuilder.build_interview_prompt(context, language="invalid")
        
        # Should contain Spanish text
        assert "ROL Y PERSONALIDAD" in prompt
        assert "Sos un" in prompt
        assert "vos" in prompt


class TestPromptBuilderMultiLanguage:
    """Test suite for multi-language support"""
    
    def test_build_spanish_prompt(self):
        """Test building Spanish prompt"""
        context = self._create_basic_context()
        
        prompt = PromptBuilder.build_interview_prompt(context, language="es")
        
        # Verify Spanish-specific content
        assert "ROL Y PERSONALIDAD" in prompt
        assert "Sos un" in prompt
        assert "Agente ProssX" in prompt
        assert "vos" in prompt
        assert "onda argentina" in prompt
        assert "CONTEXTO DEL EMPLEADO" in prompt
        assert "PROCESOS EXISTENTES" in prompt
    
    def test_build_english_prompt(self):
        """Test building English prompt"""
        context = self._create_basic_context()
        
        prompt = PromptBuilder.build_interview_prompt(context, language="en")
        
        # Verify English-specific content
        assert "ROLE AND PERSONALITY" in prompt
        assert "You are a" in prompt
        assert "ProssX Agent" in prompt
        assert "EMPLOYEE CONTEXT" in prompt
        assert "EXISTING PROCESSES" in prompt
    
    def test_build_portuguese_prompt(self):
        """Test building Portuguese prompt"""
        context = self._create_basic_context()
        
        prompt = PromptBuilder.build_interview_prompt(context, language="pt")
        
        # Verify Portuguese-specific content
        assert "PAPEL E PERSONALIDADE" in prompt
        assert "Você é um" in prompt
        assert "Agente ProssX" in prompt
        assert "CONTEXTO DO FUNCIONÁRIO" in prompt
        assert "PROCESSOS EXISTENTES" in prompt
    
    def _create_basic_context(self):
        """Helper to create basic context for testing"""
        return InterviewContextData(
            employee=EmployeeContextData(
                id=uuid4(),
                first_name="Test",
                last_name="User",
                full_name="Test User",
                organization_id=str(uuid4()),
                organization_name="Test Org",
                roles=[],
                is_active=True
            ),
            organization_processes=[],
            interview_history=InterviewHistorySummary(
                total_interviews=0,
                completed_interviews=0,
                last_interview_date=None,
                topics_covered=[]
            ),
            context_timestamp=datetime.utcnow()
        )


class TestFormatProcessList:
    """Test suite for process list formatting"""
    
    def test_format_empty_process_list_spanish(self):
        """Test formatting empty process list in Spanish"""
        result = PromptBuilder.format_process_list([], language="es")
        
        assert "No hay procesos registrados" in result
    
    def test_format_empty_process_list_english(self):
        """Test formatting empty process list in English"""
        result = PromptBuilder.format_process_list([], language="en")
        
        assert "No processes registered" in result
    
    def test_format_empty_process_list_portuguese(self):
        """Test formatting empty process list in Portuguese"""
        result = PromptBuilder.format_process_list([], language="pt")
        
        assert "não há processos registrados" in result
    
    def test_format_single_process(self):
        """Test formatting single process"""
        processes = [
            ProcessContextData(
                id=uuid4(),
                name="Proceso de Compras",
                type="operational",
                type_label="Operacional",
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        ]
        
        result = PromptBuilder.format_process_list(processes, language="es")
        
        assert "Procesos existentes" in result
        assert "1. Proceso de Compras (Operacional)" in result
    
    def test_format_multiple_processes(self):
        """Test formatting multiple processes"""
        processes = [
            ProcessContextData(
                id=uuid4(),
                name="Proceso de Compras",
                type="operational",
                type_label="Operacional",
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            ProcessContextData(
                id=uuid4(),
                name="Proceso de Ventas",
                type="strategic",
                type_label="Estratégico",
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            ProcessContextData(
                id=uuid4(),
                name="Proceso de Inventario",
                type="operational",
                type_label="Operacional",
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        ]
        
        result = PromptBuilder.format_process_list(processes, language="es")
        
        assert "1. Proceso de Compras (Operacional)" in result
        assert "2. Proceso de Ventas (Estratégico)" in result
        assert "3. Proceso de Inventario (Operacional)" in result
    
    def test_format_process_list_limits_to_20(self):
        """Test that process list is limited to 20 processes"""
        # Create 25 processes
        processes = [
            ProcessContextData(
                id=uuid4(),
                name=f"Proceso {i}",
                type="operational",
                type_label="Operacional",
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            for i in range(25)
        ]
        
        result = PromptBuilder.format_process_list(processes, language="es")
        
        # Should show count of 20
        assert "(20)" in result
        # Should have processes 0-19
        assert "Proceso 0" in result
        assert "Proceso 19" in result
        # Should NOT have process 20+
        assert "Proceso 20" not in result


class TestFormatInterviewHistory:
    """Test suite for interview history formatting"""
    
    def test_format_no_history_spanish(self):
        """Test formatting when employee has no interview history (Spanish)"""
        history = InterviewHistorySummary(
            total_interviews=0,
            completed_interviews=0,
            last_interview_date=None,
            topics_covered=[]
        )
        
        result = PromptBuilder.format_interview_history(history, language="es")
        
        assert "primera entrevista" in result
    
    def test_format_no_history_english(self):
        """Test formatting when employee has no interview history (English)"""
        history = InterviewHistorySummary(
            total_interviews=0,
            completed_interviews=0,
            last_interview_date=None,
            topics_covered=[]
        )
        
        result = PromptBuilder.format_interview_history(history, language="en")
        
        assert "first interview" in result
    
    def test_format_no_history_portuguese(self):
        """Test formatting when employee has no interview history (Portuguese)"""
        history = InterviewHistorySummary(
            total_interviews=0,
            completed_interviews=0,
            last_interview_date=None,
            topics_covered=[]
        )
        
        result = PromptBuilder.format_interview_history(history, language="pt")
        
        assert "primeira entrevista" in result
    
    def test_format_history_with_data(self):
        """Test formatting interview history with data"""
        history = InterviewHistorySummary(
            total_interviews=5,
            completed_interviews=3,
            last_interview_date=datetime(2025, 1, 15),
            topics_covered=["Compras", "Ventas", "Inventario"]
        )
        
        result = PromptBuilder.format_interview_history(history, language="es")
        
        assert "Total de entrevistas: 5" in result
        assert "Entrevistas completadas: 3" in result
        assert "2025-01-15" in result
        assert "Compras" in result
        assert "Ventas" in result
        assert "Inventario" in result
    
    def test_format_history_limits_topics_to_5(self):
        """Test that topics are limited to 5"""
        history = InterviewHistorySummary(
            total_interviews=10,
            completed_interviews=10,
            last_interview_date=datetime.utcnow(),
            topics_covered=["Topic1", "Topic2", "Topic3", "Topic4", "Topic5", "Topic6", "Topic7"]
        )
        
        result = PromptBuilder.format_interview_history(history, language="es")
        
        # Should have first 5 topics
        assert "Topic1" in result
        assert "Topic5" in result
        # Should NOT have 6th and 7th
        assert "Topic6" not in result
        assert "Topic7" not in result


class TestProcessMatchingPrompts:
    """Test suite for process matching prompt generation"""
    
    def test_build_spanish_matching_prompt(self):
        """Test building Spanish process matching prompt"""
        processes = [
            ProcessContextData(
                id=uuid4(),
                name="Proceso de Aprobación de Compras",
                type="operational",
                type_label="Operacional",
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        ]
        
        prompt = PromptBuilder.build_process_matching_prompt(
            process_description="Cuando tengo que aprobar una compra",
            existing_processes=processes,
            language="es"
        )
        
        # Verify Spanish content
        assert "ROL" in prompt
        assert "experto en análisis de procesos" in prompt
        assert "PROCESOS EXISTENTES" in prompt
        assert "Proceso de Aprobación de Compras" in prompt
        assert "Cuando tengo que aprobar una compra" in prompt
        assert "is_match" in prompt
        assert "confidence_score" in prompt
        assert "Ejemplo" in prompt
    
    def test_build_english_matching_prompt(self):
        """Test building English process matching prompt"""
        processes = [
            ProcessContextData(
                id=uuid4(),
                name="Purchase Approval Process",
                type="operational",
                type_label="Operational",
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        ]
        
        prompt = PromptBuilder.build_process_matching_prompt(
            process_description="When I need to approve a purchase",
            existing_processes=processes,
            language="en"
        )
        
        # Verify English content
        assert "ROLE" in prompt
        assert "expert in business process analysis" in prompt
        assert "EXISTING PROCESSES" in prompt
        assert "Purchase Approval Process" in prompt
        assert "When I need to approve a purchase" in prompt
        assert "is_match" in prompt
        assert "confidence_score" in prompt
        assert "Example" in prompt
    
    def test_build_portuguese_matching_prompt(self):
        """Test building Portuguese process matching prompt"""
        processes = [
            ProcessContextData(
                id=uuid4(),
                name="Processo de Aprovação de Compras",
                type="operational",
                type_label="Operacional",
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        ]
        
        prompt = PromptBuilder.build_process_matching_prompt(
            process_description="Quando preciso aprovar uma compra",
            existing_processes=processes,
            language="pt"
        )
        
        # Verify Portuguese content
        assert "PAPEL" in prompt
        assert "especialista em análise de processos" in prompt
        assert "PROCESSOS EXISTENTES" in prompt
        assert "Processo de Aprovação de Compras" in prompt
        assert "Quando preciso aprovar uma compra" in prompt
        assert "is_match" in prompt
        assert "confidence_score" in prompt
        assert "Exemplo" in prompt
    
    def test_matching_prompt_includes_examples(self):
        """Test that matching prompt includes examples"""
        processes = [
            ProcessContextData(
                id=uuid4(),
                name="Test Process",
                type="operational",
                type_label="Operational",
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        ]
        
        prompt = PromptBuilder.build_process_matching_prompt(
            process_description="Test description",
            existing_processes=processes,
            language="es"
        )
        
        # Should include example scenarios
        assert "Ejemplo 1" in prompt
        assert "Ejemplo 2" in prompt
        assert "Ejemplo 3" in prompt
        assert "Coincidencia exacta" in prompt
        assert "Coincidencia semántica" in prompt
        assert "No coincide" in prompt
    
    def test_matching_prompt_defaults_to_spanish(self):
        """Test that invalid language defaults to Spanish for matching"""
        processes = [
            ProcessContextData(
                id=uuid4(),
                name="Test Process",
                type="operational",
                type_label="Operational",
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        ]
        
        prompt = PromptBuilder.build_process_matching_prompt(
            process_description="Test",
            existing_processes=processes,
            language="invalid"
        )
        
        # Should contain Spanish text
        assert "ROL" in prompt
        assert "experto" in prompt


class TestTokenLimitCompliance:
    """Test suite for token limit compliance"""
    
    def test_prompt_with_many_processes_stays_reasonable(self):
        """Test that prompt with many processes doesn't explode in size"""
        # Create context with 20 processes (the limit)
        processes = [
            ProcessContextData(
                id=uuid4(),
                name=f"Proceso de Gestión de {i} con nombre muy largo para simular procesos reales",
                type="operational",
                type_label="Operacional",
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            for i in range(20)
        ]
        
        context = InterviewContextData(
            employee=EmployeeContextData(
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
                        description="Responsable de operaciones"
                    )
                ],
                is_active=True
            ),
            organization_processes=processes,
            interview_history=InterviewHistorySummary(
                total_interviews=5,
                completed_interviews=3,
                last_interview_date=datetime.utcnow(),
                topics_covered=["Topic1", "Topic2", "Topic3", "Topic4", "Topic5"]
            ),
            context_timestamp=datetime.utcnow()
        )
        
        prompt = PromptBuilder.build_interview_prompt(context, language="es")
        
        # Rough token estimate: 1 token ≈ 4 characters
        estimated_tokens = len(prompt) / 4
        
        # Should stay well under 4000 tokens (design requirement)
        # Being conservative, let's check it's under 3500 tokens
        assert estimated_tokens < 3500, f"Prompt too long: ~{estimated_tokens} tokens"
    
    def test_prompt_with_long_history_stays_reasonable(self):
        """Test that prompt with extensive history doesn't explode in size"""
        # Create context with many topics (but limited to 5 in formatting)
        context = InterviewContextData(
            employee=EmployeeContextData(
                id=uuid4(),
                first_name="María",
                last_name="González",
                full_name="María González",
                organization_id=str(uuid4()),
                organization_name="Acme Corp",
                roles=[],
                is_active=True
            ),
            organization_processes=[],
            interview_history=InterviewHistorySummary(
                total_interviews=50,
                completed_interviews=45,
                last_interview_date=datetime.utcnow(),
                topics_covered=[f"Very long topic name about business process {i}" for i in range(20)]
            ),
            context_timestamp=datetime.utcnow()
        )
        
        prompt = PromptBuilder.build_interview_prompt(context, language="es")
        
        # Rough token estimate
        estimated_tokens = len(prompt) / 4
        
        # Should stay under 4000 tokens
        assert estimated_tokens < 4000, f"Prompt too long: ~{estimated_tokens} tokens"


class TestPromptBuilderEdgeCases:
    """Test suite for edge cases"""
    
    def test_employee_with_multiple_roles(self):
        """Test prompt with employee having multiple roles"""
        context = InterviewContextData(
            employee=EmployeeContextData(
                id=uuid4(),
                first_name="Carlos",
                last_name="Rodríguez",
                full_name="Carlos Rodríguez",
                organization_id=str(uuid4()),
                organization_name="Multi Corp",
                roles=[
                    RoleContextData(id=uuid4(), name="Gerente", description=None),
                    RoleContextData(id=uuid4(), name="Analista", description=None),
                    RoleContextData(id=uuid4(), name="Coordinador", description=None)
                ],
                is_active=True
            ),
            organization_processes=[],
            interview_history=InterviewHistorySummary(
                total_interviews=0,
                completed_interviews=0,
                last_interview_date=None,
                topics_covered=[]
            ),
            context_timestamp=datetime.utcnow()
        )
        
        prompt = PromptBuilder.build_interview_prompt(context, language="es")
        
        # Should include all roles
        assert "Gerente, Analista, Coordinador" in prompt
    
    def test_employee_with_no_roles(self):
        """Test prompt with employee having no roles"""
        context = InterviewContextData(
            employee=EmployeeContextData(
                id=uuid4(),
                first_name="Ana",
                last_name="López",
                full_name="Ana López",
                organization_id=str(uuid4()),
                organization_name="No Role Corp",
                roles=[],
                is_active=True
            ),
            organization_processes=[],
            interview_history=InterviewHistorySummary(
                total_interviews=0,
                completed_interviews=0,
                last_interview_date=None,
                topics_covered=[]
            ),
            context_timestamp=datetime.utcnow()
        )
        
        prompt = PromptBuilder.build_interview_prompt(context, language="es")
        
        # Should use default role description
        assert "Empleado" in prompt
    
    def test_process_with_special_characters(self):
        """Test formatting process with special characters in name"""
        processes = [
            ProcessContextData(
                id=uuid4(),
                name="Proceso de Compras & Ventas (2024)",
                type="operational",
                type_label="Operacional",
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        ]
        
        result = PromptBuilder.format_process_list(processes, language="es")
        
        # Should handle special characters
        assert "Proceso de Compras & Ventas (2024)" in result
