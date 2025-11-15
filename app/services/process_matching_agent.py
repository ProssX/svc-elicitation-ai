"""
Process Matching Agent Service

Specialized agent that determines if a user's process description
matches any existing processes in the organization.
"""
import json
import asyncio
from typing import List, Optional
from strands import Agent
from app.models.context import ProcessContextData
from app.models.interview import ProcessMatchResult
from app.services.model_factory import create_model
from app.services.prompt_builder import PromptBuilder
from app.config import settings


class ProcessMatchingAgent:
    """
    Specialized agent for process matching
    
    This agent analyzes a user's process description and determines
    if it matches any existing processes in the organization using
    LLM-based semantic analysis.
    """
    
    def __init__(self):
        """Initialize the process matching agent with the configured model"""
        self.model = create_model()
        self.timeout = settings.process_matching_timeout  # Timeout from config
    
    async def match_process(
        self,
        process_description: str,
        existing_processes: List[ProcessContextData],
        language: str = "es",
        db = None,  # Optional: AsyncSession for querying reporter info
        auth_token: Optional[str] = None,  # For backend API authentication
        organization_id: Optional[str] = None  # For backend API calls
    ) -> ProcessMatchResult:
        """
        Determine if described process matches existing processes
        
        Uses LLM to perform semantic analysis and determine if the user's
        process description refers to an existing process or is new.
        
        Args:
            process_description: User's description of a process
            existing_processes: List of existing processes in organization
            language: Interview language (es/en/pt)
            db: Optional database session for querying reporter information
            
        Returns:
            ProcessMatchResult with match confidence and reasoning
            
        Raises:
            asyncio.TimeoutError: If matching takes longer than timeout
        """
        import logging
        logger = logging.getLogger(__name__)
        
        from datetime import datetime
        start_time = datetime.utcnow()
        
        # Handle edge case: no existing processes
        if not existing_processes:
            logger.info(
                "[PROCESS_MATCH] No existing processes to match against",
                extra={
                    "processes_count": 0,
                    "language": language,
                    "result": "no_processes"
                }
            )
            return ProcessMatchResult(
                is_match=False,
                matched_process_id=None,
                matched_process_name=None,
                confidence_score=0.0,
                reasoning=self._get_no_processes_message(language),
                suggested_clarifying_questions=[]
            )
        
        logger.info(
            f"[PERF] Starting process matching against {len(existing_processes)} processes",
            extra={
                "processes_count": len(existing_processes),
                "language": language,
                "timeout_seconds": self.timeout
            }
        )
        
        try:
            # Run matching with timeout
            result = await asyncio.wait_for(
                self._perform_matching(
                    process_description,
                    existing_processes,
                    language,
                    db,
                    auth_token=auth_token,
                    organization_id=organization_id
                ),
                timeout=self.timeout
            )
            
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            logger.info(
                f"[PERF] Process matching completed in {elapsed:.3f}s",
                extra={
                    "elapsed_seconds": elapsed,
                    "is_match": result.is_match,
                    "confidence_score": result.confidence_score,
                    "matched_process": result.matched_process_name,
                    "processes_count": len(existing_processes),
                    "performance_target_met": elapsed < 1.0,
                    "success": True
                }
            )
            return result
        
        except asyncio.TimeoutError:
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            logger.error(
                f"[ERROR] Process matching timeout after {elapsed:.3f}s",
                extra={
                    "elapsed_seconds": elapsed,
                    "timeout_seconds": self.timeout,
                    "processes_count": len(existing_processes),
                    "error_type": "timeout",
                    "success": False,
                    "fallback": "no_match"
                }
            )
            # Return no match on timeout
            return ProcessMatchResult(
                is_match=False,
                matched_process_id=None,
                matched_process_name=None,
                confidence_score=0.0,
                reasoning=self._get_timeout_message(language),
                suggested_clarifying_questions=[]
            )
        
        except Exception as e:
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            logger.error(
                f"[ERROR] Process matching failed: {type(e).__name__}: {str(e)}",
                extra={
                    "elapsed_seconds": elapsed,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "processes_count": len(existing_processes),
                    "success": False,
                    "fallback": "no_match"
                }
            )
            # Return no match on any error
            return ProcessMatchResult(
                is_match=False,
                matched_process_id=None,
                matched_process_name=None,
                confidence_score=0.0,
                reasoning=self._get_error_message(language),
                suggested_clarifying_questions=[]
            )
    
    async def _perform_matching(
        self,
        process_description: str,
        existing_processes: List[ProcessContextData],
        language: str,
        db = None,
        auth_token: Optional[str] = None,
        organization_id: Optional[str] = None
    ) -> ProcessMatchResult:
        """
        Perform the actual process matching using LLM
        
        Args:
            process_description: User's description of a process
            existing_processes: List of existing processes
            language: Interview language
            db: Optional database session for querying reporter info
            
        Returns:
            ProcessMatchResult with match analysis
        """
        # Build specialized matching prompt
        system_prompt = self._build_matching_prompt(
            process_description,
            existing_processes,
            language
        )
        
        # Create agent with matching prompt
        agent = Agent(
            model=self.model,
            system_prompt=system_prompt,
            callback_handler=None
        )
        
        # Get matching analysis from agent
        # The prompt instructs the agent to respond in JSON format
        response = agent("Analyze the process description and respond in JSON format.")
        
        # Extract response content
        content = response.message.get('content', [])
        response_text = content[0].get('text', '') if content and len(content) > 0 else ""
        
        if not response_text:
            response_text = str(response.message)
        
        # Parse JSON response
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            match_data = self._parse_json_response(response_text)
        except Exception as e:
            logger.error(
                f"[ERROR] Failed to parse process matching JSON response: {type(e).__name__}: {str(e)}",
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "response_length": len(response_text),
                    "success": False,
                    "fallback": "no_match"
                }
            )
            logger.debug(
                f"[DEBUG] Unparseable response text: {response_text[:500]}...",
                extra={"response_preview": response_text[:500]}
            )
            # Return no match if parsing fails
            return ProcessMatchResult(
                is_match=False,
                matched_process_id=None,
                matched_process_name=None,
                confidence_score=0.0,
                reasoning="Failed to parse matching analysis",
                suggested_clarifying_questions=[]
            )
        
        # Find matched process ID if there's a match
        matched_process_id = None
        if match_data.get("is_match") and match_data.get("matched_process_name"):
            matched_process_id = self._find_process_id(
                match_data["matched_process_name"],
                existing_processes
            )
        
        # Query reporter information if we have a match and db session
        reported_by_employee_id = None
        reported_by_name = None
        reported_by_role = None
        
        logger.info(f"[PROCESS_REPORTER] Checking reporter conditions - matched_process_id: {matched_process_id}, has_db: {db is not None}, has_auth_token: {auth_token is not None}, organization_id: {organization_id}")
        
        if matched_process_id and db and auth_token and organization_id:
            logger.info(f"[PROCESS_REPORTER] Calling _get_process_reporter for process {matched_process_id}")
            reporter_info = await self._get_process_reporter(
                matched_process_id, 
                db,
                auth_token=auth_token,
                organization_id=organization_id
            )
            logger.info(f"[PROCESS_REPORTER] Reporter info result: {reporter_info}")
            if reporter_info:
                reported_by_employee_id = reporter_info.get("employee_id")
                reported_by_name = reporter_info.get("employee_name")
                reported_by_role = reporter_info.get("employee_role")
                logger.info(f"[PROCESS_REPORTER] Reporter extracted: {reported_by_name} ({reported_by_role})")
        
        # Build result
        return ProcessMatchResult(
            is_match=match_data.get("is_match", False),
            matched_process_id=matched_process_id,
            matched_process_name=match_data.get("matched_process_name"),
            confidence_score=float(match_data.get("confidence_score", 0.0)),
            reasoning=match_data.get("reasoning", ""),
            suggested_clarifying_questions=match_data.get("suggested_clarifying_questions", []),
            reported_by_employee_id=reported_by_employee_id,
            reported_by_name=reported_by_name,
            reported_by_role=reported_by_role
        )
    
    def _build_matching_prompt(
        self,
        process_description: str,
        existing_processes: List[ProcessContextData],
        language: str
    ) -> str:
        """
        Build system prompt for process matching
        
        Uses PromptBuilder to create a specialized prompt that instructs
        the LLM to analyze the process description and return a structured
        JSON response with matching results.
        
        Args:
            process_description: User's description of a process
            existing_processes: List of existing processes
            language: Interview language (es/en/pt)
            
        Returns:
            str: System prompt for process matching
        """
        return PromptBuilder.build_process_matching_prompt(
            process_description=process_description,
            existing_processes=existing_processes,
            language=language
        )
    
    def _parse_json_response(self, response_text: str) -> dict:
        """
        Parse JSON response from LLM
        
        Handles various formats:
        - Pure JSON
        - JSON wrapped in markdown code blocks
        - JSON with extra text
        
        Args:
            response_text: Raw response text from LLM
            
        Returns:
            dict: Parsed JSON data
            
        Raises:
            ValueError: If JSON cannot be parsed
        """
        # Try to extract JSON from markdown code blocks
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            if end != -1:
                response_text = response_text[start:end].strip()
        elif "```" in response_text:
            start = response_text.find("```") + 3
            end = response_text.find("```", start)
            if end != -1:
                response_text = response_text[start:end].strip()
        
        # Try to find JSON object boundaries
        if "{" in response_text and "}" in response_text:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            response_text = response_text[start:end]
        
        # Parse JSON
        return json.loads(response_text)
    
    def _find_process_id(
        self,
        process_name: str,
        existing_processes: List[ProcessContextData]
    ) -> Optional[str]:
        """
        Find process ID by name
        
        Performs case-insensitive matching to find the process ID
        corresponding to the matched process name.
        
        Args:
            process_name: Name of the matched process
            existing_processes: List of existing processes
            
        Returns:
            UUID of the matched process, or None if not found
        """
        process_name_lower = process_name.lower()
        for process in existing_processes:
            if process.name.lower() == process_name_lower:
                return process.id
        return None
    
    # ========================================================================
    # Helper messages for different scenarios
    # ========================================================================
    
    def _get_no_processes_message(self, language: str) -> str:
        """Get message when no processes exist"""
        messages = {
            "es": "No hay procesos existentes en la organización para comparar",
            "en": "No existing processes in the organization to compare",
            "pt": "Não há processos existentes na organização para comparar"
        }
        return messages.get(language, messages["es"])
    
    def _get_timeout_message(self, language: str) -> str:
        """Get message when matching times out"""
        messages = {
            "es": "El análisis de coincidencia excedió el tiempo límite",
            "en": "Process matching analysis timed out",
            "pt": "A análise de correspondência excedeu o tempo limite"
        }
        return messages.get(language, messages["es"])
    
    def _get_error_message(self, language: str) -> str:
        """Get message when matching fails"""
        messages = {
            "es": "Error al analizar la coincidencia del proceso",
            "en": "Error analyzing process match",
            "pt": "Erro ao analisar a correspondência do processo"
        }
        return messages.get(language, messages["es"])
    
    async def _get_process_reporter(
        self, 
        process_id: str, 
        db,
        auth_token: Optional[str] = None,
        organization_id: Optional[str] = None
    ) -> Optional[dict]:
        """
        Get information about the employee who first reported a process
        
        Queries the interview_process_reference table to find the first
        interview that mentioned this process, then retrieves the employee
        information from the backend PHP service.
        
        Args:
            process_id: UUID of the process
            db: Database session (AsyncSession)
            auth_token: JWT token for backend authentication
            organization_id: Organization UUID for backend API call
            
        Returns:
            dict with employee_id, employee_name, employee_role, or None if not found
        """
        if not db:
            return None
        
        try:
            from sqlalchemy import select
            from uuid import UUID
            from app.models.db_models import InterviewProcessReference, Interview
            from app.clients.backend_client import BackendClient
            
            import logging
            logger = logging.getLogger(__name__)
            
            # Step 1: Find the earliest interview that mentioned this process
            # process_id might already be a UUID object, convert to UUID if string
            proc_uuid = process_id if isinstance(process_id, UUID) else UUID(process_id)
            stmt = (
                select(InterviewProcessReference)
                .where(InterviewProcessReference.process_id == proc_uuid)
                .order_by(InterviewProcessReference.created_at.asc())
                .limit(1)
            )
            
            result = await db.execute(stmt)
            reference = result.scalars().first()
            
            if not reference:
                logger.debug(f"[PROCESS_REPORTER] No reference found for process {process_id}")
                return None
            
            # Step 2: Get the interview to find employee_id
            interview_stmt = (
                select(Interview)
                .where(Interview.id_interview == reference.interview_id)
            )
            interview_result = await db.execute(interview_stmt)
            interview = interview_result.scalars().first()
            
            if not interview:
                logger.debug(f"[PROCESS_REPORTER] Interview not found for reference {reference.interview_id}")
                return None
            
            employee_id = interview.employee_id
            
            # Step 3: Get employee details from backend PHP service
            if not auth_token or not organization_id:
                logger.warning(
                    f"[PROCESS_REPORTER] Missing auth_token or organization_id - cannot fetch employee details",
                    extra={
                        "process_id": process_id,
                        "employee_id": str(employee_id),
                        "has_token": bool(auth_token),
                        "has_org_id": bool(organization_id)
                    }
                )
                # Return partial info
                return {
                    "employee_id": employee_id,
                    "employee_name": None,
                    "employee_role": None
                }
            
            # Fetch employee from backend
            backend_client = BackendClient()
            employee_data = await backend_client.get_employee(
                employee_id=employee_id,
                organization_id=str(organization_id),  # Convert UUID to string
                auth_token=auth_token
            )
            
            if not employee_data:
                logger.warning(
                    f"[PROCESS_REPORTER] Employee not found in backend: {employee_id}",
                    extra={
                        "process_id": process_id,
                        "employee_id": str(employee_id),
                        "organization_id": organization_id
                    }
                )
                return {
                    "employee_id": employee_id,
                    "employee_name": None,
                    "employee_role": None
                }
            
            # Extract employee info from backend response
            first_name = employee_data.get("firstName", "")
            last_name = employee_data.get("lastName", "")
            employee_name = f"{first_name} {last_name}".strip()
            
            # Get role name - backend returns roleIds, need to fetch role details
            employee_role = "Unknown"
            role_ids = employee_data.get("roleIds", [])
            
            if role_ids and len(role_ids) > 0:
                try:
                    # Fetch first role details
                    role_data = await backend_client.get_role(
                        role_id=role_ids[0],
                        organization_id=str(organization_id),
                        auth_token=auth_token
                    )
                    if role_data:
                        employee_role = role_data.get("name", "Unknown")
                        logger.info(
                            f"[PROCESS_REPORTER] Successfully fetched role: {employee_role}",
                            extra={"role_id": role_ids[0], "role_name": employee_role}
                        )
                except Exception as e:
                    logger.warning(
                        f"[PROCESS_REPORTER] Failed to fetch role details: {type(e).__name__}: {str(e)}",
                        extra={"role_id": role_ids[0], "error": str(e)}
                    )
            
            logger.info(
                f"[PROCESS_REPORTER] Found reporter for process {process_id}: {employee_name}",
                extra={
                    "process_id": process_id,
                    "employee_id": str(employee_id),
                    "employee_name": employee_name,
                    "employee_role": employee_role
                }
            )
            
            return {
                "employee_id": employee_id,
                "employee_name": employee_name,
                "employee_role": employee_role
            }
        
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(
                f"[PROCESS_REPORTER] Error fetching reporter info: {type(e).__name__}: {str(e)}",
                extra={
                    "process_id": process_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                },
                exc_info=True
            )
            return None


# Global agent instance
_matching_agent_instance = None


def get_matching_agent() -> ProcessMatchingAgent:
    """Get or create the global process matching agent instance"""
    global _matching_agent_instance
    if _matching_agent_instance is None:
        _matching_agent_instance = ProcessMatchingAgent()
    return _matching_agent_instance
