"""
Agent Service
Core interview agent using Strands
"""
import uuid
from typing import List, Dict, Optional
from strands import Agent
from app.models.interview import (
    ConversationMessage, 
    InterviewContext, 
    InterviewResponse,
    ProcessMatchInfo
)
from app.models.context import InterviewContextData
from app.services.model_factory import create_model
from app.services.prompt_builder import PromptBuilder
from app.services.process_matching_agent import get_matching_agent
from prompts.system_prompts import get_interviewer_prompt
from app.config import settings


class InterviewAgent:
    """
    Conversational agent for requirements elicitation
    Uses Strands SDK to conduct interviews
    """
    
    def __init__(self):
        """Initialize the agent with the configured model"""
        self.model = create_model()
        
    def start_interview(
        self,
        context: Optional[InterviewContextData] = None,
        user_name: Optional[str] = None,
        user_role: Optional[str] = None,
        organization: Optional[str] = None,
        technical_level: str = "unknown",
        language: str = "es"
    ) -> InterviewResponse:
        """
        Start a new interview session with enriched context
        
        Args:
            context: Complete interview context data (NEW - preferred)
            user_name: Name of the user (legacy - used if context not provided)
            user_role: User's role in the organization (legacy)
            organization: Organization name (legacy)
            technical_level: User's technical proficiency
            language: Interview language (es/en/pt)
            
        Returns:
            InterviewResponse with the first question
        """
        try:
            # Determine if we're using context-aware mode or legacy mode
            if context is not None:
                print(f"[DEBUG] Starting context-aware interview for {context.employee.full_name}")
                print(f"[DEBUG] Organization: {context.employee.organization_name}")
                print(f"[DEBUG] Existing processes: {len(context.organization_processes)}")
                print(f"[DEBUG] Language: {language}, Technical level: {technical_level}")
                
                # Build context-aware system prompt
                system_prompt = self._build_context_aware_prompt(context, language)
                
                # Extract user info from context
                user_name = context.employee.full_name
                organization = context.employee.organization_name
            else:
                # Legacy mode - use old prompt builder
                print(f"[DEBUG] Starting legacy interview for {user_name} ({user_role}) at {organization}")
                print(f"[DEBUG] Language: {language}, Technical level: {technical_level}")
                
                # Generate system prompt with language support (legacy)
                system_prompt = get_interviewer_prompt(
                    user_name=user_name,
                    user_role=user_role,
                    organization=organization,
                    technical_level=technical_level,
                    language=language
                )
            
            print(f"[DEBUG] System prompt generated ({len(system_prompt)} chars)")
            
            # Create agent with system prompt
            print("[DEBUG] Creating Strands agent...")
            agent = Agent(
                model=self.model,
                system_prompt=system_prompt,
                callback_handler=None  # Disable console output
            )
            
            print("[DEBUG] Agent created successfully")
            
            # Get first question
            initial_prompts = {
                "es": f"Inicia la entrevista con {user_name}. Salúdalo de forma breve y cálida (onda argentina), presenta tu rol y hace tu primera pregunta específica sobre su función en {organization}.",
                "en": f"Start the interview with {user_name}. Greet them briefly and warmly, introduce your role and ask your first specific question about their function at {organization}.",
                "pt": f"Inicie a entrevista com {user_name}. Cumprimente-os brevemente e calorosamente, apresente seu papel e faça sua primeira pergunta específica sobre sua função em {organization}."
            }
            
            initial_message = initial_prompts.get(language, initial_prompts["es"])
            
            print(f"[DEBUG] Calling agent with initial message...")
            response = agent(initial_message)
            
            print(f"[DEBUG] Got response from agent: {type(response)}")
            print(f"[DEBUG] Response.message type: {type(response.message)}")
            print(f"[DEBUG] Response.message content: {response.message}")
            
            # Extract the question from response
            # response.message is a dict with 'role' and 'content'
            content = response.message.get('content', [])
            question = content[0].get('text', '') if content and len(content) > 0 else ""
            
            if not question:
                # Fallback if extraction fails
                print("[WARNING] Could not extract question from response, using fallback")
                question = str(response.message)
            
            print(f"[DEBUG] Extracted question ({len(question)} chars): {question[:100]}...")
            
            return InterviewResponse(
                question=question,
                question_number=1,
                is_final=False,
                context=InterviewContext(
                    processes_identified=[],
                    topics_discussed=[],
                    completeness=0.0,
                    user_profile_technical=(technical_level == "technical")
                ),
                process_matches=[]  # No matches on first question
            )
        except Exception as e:
            print(f"[ERROR] Exception in start_interview: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
    
    async def continue_interview(
        self,
        user_response: str,
        conversation_history: List[ConversationMessage],
        context: Optional[InterviewContextData] = None,
        user_name: Optional[str] = None,
        user_role: Optional[str] = None,
        organization: Optional[str] = None,
        technical_level: str = "unknown",
        language: str = "es",
        db = None,  # Database session for process reporter lookup
        auth_token: Optional[str] = None,  # Auth token for backend API calls
        organization_id: Optional[str] = None  # Organization ID for backend API calls
    ) -> InterviewResponse:
        """
        Continue an ongoing interview with process matching capability
        
        Args:
            user_response: User's response to previous question
            conversation_history: Full conversation history
            context: Complete interview context data (NEW - preferred)
            user_name: Name of the user (legacy - used if context not provided)
            user_role: User's role (legacy)
            organization: Organization name (legacy)
            technical_level: User's technical level
            language: Interview language (es/en/pt)
            
        Returns:
            InterviewResponse with next question and process matches
        """
        # Determine if we're using context-aware mode or legacy mode
        if context is not None:
            # Context-aware mode
            print(f"[DEBUG] Continuing context-aware interview")
            
            # Build context-aware system prompt
            system_prompt = self._build_context_aware_prompt(context, language)
            
            # Extract user info from context
            user_name = context.employee.full_name
            organization = context.employee.organization_name
        else:
            # Legacy mode
            print(f"[DEBUG] Continuing legacy interview")
            
            # Generate system prompt with language support (legacy)
            system_prompt = get_interviewer_prompt(
                user_name=user_name,
                user_role=user_role,
                organization=organization,
                technical_level=technical_level,
                language=language
            )
        
        # Check if user mentioned a process and perform matching (if feature enabled)
        process_matches = []
        match_result = None
        
        print(f"[DEBUG-TRACE] Before process matching check - enable_process_matching: {settings.enable_process_matching}, context: {context is not None}, mentions_process: {self._mentions_process(user_response) if context else 'N/A'}")
        
        if settings.enable_process_matching and context is not None and self._mentions_process(user_response):
            print(f"[DEBUG] Process matching enabled - process mention detected, invoking matching agent")
            
            # Extract organization_id from context if available (preferred), otherwise use parameter
            org_id = str(context.employee.organization_id) if context and context.employee else organization_id
            
            # Invoke process matching agent
            matching_agent = get_matching_agent()
            match_result = await matching_agent.match_process(
                process_description=user_response,
                existing_processes=context.organization_processes,
                language=language,
                db=db,  # Pass db session to get reporter info
                auth_token=auth_token,  # Pass auth token for backend API calls
                organization_id=org_id  # Pass organization ID for backend API calls
            )
            
            print(f"[DEBUG] Process match result: is_match={match_result.is_match}, confidence={match_result.confidence_score}")
            if match_result.reported_by_name:
                print(f"[DEBUG] Process originally reported by: {match_result.reported_by_name} ({match_result.reported_by_role})")
            
            # Convert match result to ProcessMatchInfo if there's a match
            if match_result.is_match and match_result.matched_process_id:
                process_matches.append(ProcessMatchInfo(
                    process_id=match_result.matched_process_id,
                    process_name=match_result.matched_process_name,
                    is_new=False,  # It's an existing process
                    confidence=match_result.confidence_score
                ))
        elif not settings.enable_process_matching and context is not None and self._mentions_process(user_response):
            print(f"[DEBUG] Process matching disabled - skipping process matching despite mention detection")
        
        # Add match-specific instructions to system prompt if there's a match
        if match_result and match_result.is_match and match_result.reported_by_name:
            if language == "es":
                match_instruction = f"""

---
**⚠️ CONTEXTO IMPORTANTE - PROCESO YA REPORTADO:**

El usuario acaba de mencionar el proceso "{match_result.matched_process_name}".
Este proceso fue reportado anteriormente por **{match_result.reported_by_name}** ({match_result.reported_by_role}).

**EN TU PRÓXIMA PREGUNTA DEBES:**
1. Mencionar que {match_result.reported_by_name} ya habló de este proceso
2. Preguntar si la experiencia coincide o hay diferencias
3. Explorar detalles adicionales desde la perspectiva del usuario actual

**EJEMPLO:** "{match_result.reported_by_name} ya mencionó el proceso de {match_result.matched_process_name}. ¿Tu experiencia coincide con la de {match_result.reported_by_name.split()[0]} o notás diferencias desde tu rol?"
"""
            elif language == "en":
                match_instruction = f"""

---
**⚠️ IMPORTANT CONTEXT - PREVIOUSLY REPORTED PROCESS:**

The user just mentioned the process "{match_result.matched_process_name}".
This process was previously reported by **{match_result.reported_by_name}** ({match_result.reported_by_role}).

**IN YOUR NEXT QUESTION YOU MUST:**
1. Mention that {match_result.reported_by_name} already discussed this process
2. Ask if the experience matches or if there are differences
3. Explore additional details from the current user's perspective

**EXAMPLE:** "{match_result.reported_by_name} already mentioned the {match_result.matched_process_name} process. Does your experience match {match_result.reported_by_name.split()[0]}'s or do you notice differences from your role?"
"""
            system_prompt += match_instruction
        
        # Create agent
        agent = Agent(
            model=self.model,
            system_prompt=system_prompt,
            callback_handler=None
        )
        
        # Build conversation for agent
        # Convert history to agent format
        conversation = []
        for msg in conversation_history:
            conversation.append({
                "role": msg.role,
                "content": msg.content
            })
        
        # Add user's latest response
        conversation.append({
            "role": "user",
            "content": user_response
        })
        
        # Get agent's response
        # For stateless operation, we simulate conversation by providing full context
        full_context = "\n".join([
            f"{'Usuario' if m['role'] == 'user' else 'Entrevistador'}: {m['content']}"
            for m in conversation
        ])
        
        # Build dynamic instructions based on process match
        match_instructions = ""
        if match_result and match_result.is_match and match_result.reported_by_name:
            if language == "es":
                match_instructions = f"""

**⚠️ IMPORTANTE - PROCESO DETECTADO:**
El usuario acaba de mencionar el proceso "{match_result.matched_process_name}" que fue reportado anteriormente por **{match_result.reported_by_name}** ({match_result.reported_by_role}).

**TU PRÓXIMA PREGUNTA DEBE:**
1. Mencionar explícitamente que {match_result.reported_by_name} ya habló de este proceso
2. Preguntar si la experiencia del usuario coincide con la de {match_result.reported_by_name} o si hay diferencias
3. Explorar detalles adicionales o perspectivas diferentes que el usuario pueda aportar

**EJEMPLO:**
"{match_result.reported_by_name} ya mencionó el proceso de {match_result.matched_process_name}. ¿Tu experiencia con este proceso coincide con la de {match_result.reported_by_name.split()[0]} o notás alguna diferencia desde tu rol?"
"""
            elif language == "en":
                match_instructions = f"""

**⚠️ IMPORTANT - PROCESS DETECTED:**
The user just mentioned the process "{match_result.matched_process_name}" which was previously reported by **{match_result.reported_by_name}** ({match_result.reported_by_role}).

**YOUR NEXT QUESTION MUST:**
1. Explicitly mention that {match_result.reported_by_name} already discussed this process
2. Ask if the user's experience matches {match_result.reported_by_name}'s or if there are differences
3. Explore additional details or different perspectives the user can provide

**EXAMPLE:**
"{match_result.reported_by_name} already mentioned the {match_result.matched_process_name} process. Does your experience with this process match {match_result.reported_by_name.split()[0]}'s or do you notice any differences from your role?"
"""
        
        prompt = f"""Contexto de la conversación hasta ahora:
{full_context}
{match_instructions}

Basándote en la conversación anterior, formula tu próxima pregunta para profundizar en los procesos de negocio.
"""
        
        response = agent(prompt)
        
        # Extract next question
        # response.message is a dict with 'role' and 'content'
        content = response.message.get('content', [])
        question = content[0].get('text', '') if content else ""
        
        # Calculate question number
        question_number = len([m for m in conversation_history if m.role == "assistant"]) + 1
        
        # Analyze context and determine if we should finish
        interview_context = self._analyze_conversation_context(conversation, user_response)
        
        # Determine if this should be the final question
        # Pass agent's question to detect closing signals
        is_final = self._should_finish_interview(
            question_number=question_number,
            context=interview_context,
            user_response=user_response,
            agent_question=question
        )
        
        # If we detected it should finish, override the question with a closing message
        if is_final:
            closing_messages = {
                "es": f"Perfecto, {user_name}! Con toda esta información ya tenemos lo necesario. ¡Muchas gracias por tu tiempo! La entrevista quedó registrada correctamente. 🎉",
                "en": f"Perfect, {user_name}! With all this information we have what we need. Thank you very much for your time! The interview has been successfully recorded. 🎉",
                "pt": f"Perfeito, {user_name}! Com todas essas informações já temos o necessário. Muito obrigado pelo seu tempo! A entrevista foi registrada corretamente. 🎉"
            }
            question = closing_messages.get(language, closing_messages["es"])
        
        return InterviewResponse(
            question=question,
            question_number=question_number,
            is_final=is_final,
            context=interview_context,
            original_user_response=user_response,
            corrected_user_response=user_response,  # TODO: Add spell checking
            process_matches=process_matches  # NEW: Include process matches
        )
    
    def _build_context_aware_prompt(
        self,
        context: InterviewContextData,
        language: str
    ) -> str:
        """
        Build system prompt with enriched context using PromptBuilder
        
        Args:
            context: Complete interview context data
            language: Interview language (es/en/pt)
            
        Returns:
            str: System prompt with context
        """
        return PromptBuilder.build_interview_prompt(
            context=context,
            language=language
        )
    
    def _mentions_process(self, text: str) -> bool:
        """
        Detect if user response mentions a process (heuristic detection)
        
        Uses simple keyword matching to determine if the user is likely
        describing a business process. This is a lightweight check to
        decide whether to invoke the process matching agent.
        
        Args:
            text: User's response text
            
        Returns:
            bool: True if text likely mentions a process
        """
        # Convert to lowercase for case-insensitive matching
        text_lower = text.lower()
        
        # Process-related keywords in multiple languages
        process_keywords = [
            # Spanish
            "proceso", "procedimiento", "flujo", "actividad", "tarea",
            "gestión", "administración", "manejo", "control", "operación",
            "aprobación", "autorización", "solicitud", "revisión",
            # English
            "process", "procedure", "workflow", "activity", "task",
            "management", "administration", "handling", "control", "operation",
            "approval", "authorization", "request", "review",
            # Portuguese
            "processo", "procedimento", "fluxo", "atividade", "tarefa",
            "gestão", "administração", "manuseio", "controle", "operação",
            "aprovação", "autorização", "solicitação", "revisão"
        ]
        
        # Check if any keyword is present
        for keyword in process_keywords:
            if keyword in text_lower:
                return True
        
        return False
    
    def _analyze_conversation_context(
        self,
        conversation: List[Dict],
        latest_response: str
    ) -> InterviewContext:
        """
        Analyze conversation to extract context information
        
        Args:
            conversation: Full conversation history
            latest_response: Latest user response
            
        Returns:
            InterviewContext with analyzed information
        """
        # Simple heuristic analysis
        # In production, this could use LLM to extract structured info
        
        processes_keywords = ["proceso", "procedimiento", "flujo", "actividad", "tarea"]
        topics_keywords = ["sistema", "herramienta", "aplicación", "plataforma"]
        
        processes = []
        topics = []
        
        # Analyze all user responses
        user_messages = [m["content"] for m in conversation if m["role"] == "user"]
        all_text = " ".join(user_messages).lower()
        
        # Simple keyword detection
        for keyword in processes_keywords:
            if keyword in all_text:
                processes.append(keyword)
        
        for keyword in topics_keywords:
            if keyword in all_text:
                topics.append(keyword)
        
        # Calculate completeness based on number of questions and responses
        num_questions = len([m for m in conversation if m["role"] == "assistant"])
        completeness = min(num_questions / settings.max_questions, 1.0)
        
        return InterviewContext(
            processes_identified=list(set(processes)),
            topics_discussed=list(set(topics)),
            completeness=completeness,
            user_profile_technical=False  # Would need to be passed from start
        )
    
    def _should_finish_interview(
        self,
        question_number: int,
        context: InterviewContext,
        user_response: str,
        agent_question: str
    ) -> bool:
        """
        Determine if the interview should end
        
        **Nueva estrategia - Delegar más al LLM**:
        
        La decisión de cuándo terminar está principalmente en el SYSTEM PROMPT del agente.
        Esta función solo verifica límites absolutos y señales explícitas.
        
        El agente (LLM) sabe cuándo terminar por el prompt:
        - Cuando tiene información detallada de 2+ procesos
        - Cuando el usuario pide terminar
        - Cuando llegó al máximo de preguntas
        
        Args:
            question_number: Current question number
            context: Interview context (usado internamente, no expuesto)
            user_response: Latest user response
            agent_question: The agent's generated question/response
            
        Returns:
            bool: True if interview should end
        """
        # 1. LÍMITE ABSOLUTO: Máximo de preguntas
        if question_number >= settings.max_questions:
            print(f"[DEBUG] Ending interview: Max questions reached ({settings.max_questions})")
            return True
        
        # 2. Usuario pide terminar EXPLÍCITAMENTE
        end_keywords = {
            "es": ["quiero terminar", "vamos a terminar", "terminemos", "finalizar la entrevista", "suficiente por hoy", "ya está bien", "nada más gracias"],
            "en": ["let's finish", "i want to finish", "let's end this", "that's enough", "nothing more"],
            "pt": ["vamos terminar", "quero terminar", "já chega", "é suficiente"]
        }
        
        response_lower = user_response.lower()
        for lang_keywords in end_keywords.values():
            if any(keyword in response_lower for keyword in lang_keywords):
                print(f"[DEBUG] Ending interview: User requested to finish")
                return True
        
        # 3. SEÑAL DEL AGENTE: Detectar si el agente dice "gracias por tu tiempo" u otras frases de cierre
        # Esto indica que el LLM decidió que ya tiene suficiente información
        closing_signals = {
            "es": ["gracias por tu tiempo", "muchas gracias", "quedó registrada", "la entrevista", "info quedó registrada"],
            "en": ["thank you for your time", "thanks for your time", "has been recorded", "successfully recorded"],
            "pt": ["obrigado pelo seu tempo", "foi registrada", "foi registrado"]
        }
        
        question_lower = agent_question.lower()
        for lang_signals in closing_signals.values():
            if any(signal in question_lower for signal in lang_signals):
                print(f"[DEBUG] Ending interview: Agent signaled completion")
                return True
        
        # 4. MÍNIMO OBLIGATORIO: No terminar antes del mínimo
        if question_number < settings.min_questions:
            return False
        
        # 5. DEFAULT: Continuar (confiar en el criterio del agente expresado en el prompt)
        return False


# Global agent instance
_agent_instance = None


def get_agent() -> InterviewAgent:
    """Get or create the global agent instance"""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = InterviewAgent()
    return _agent_instance

