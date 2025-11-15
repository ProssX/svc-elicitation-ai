"""
Interview Service
Business logic layer for interview persistence operations
"""
import logging
from typing import Tuple, List, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import Interview, InterviewMessage, InterviewStatusEnum, MessageRoleEnum, LanguageEnum
from app.models.interview import (
    InterviewDBResponse,
    InterviewWithMessages,
    MessageResponse,
    InterviewFilters,
    PaginationParams,
    PaginationMeta,
    ConversationMessage
)
from app.repositories.interview_repository import InterviewRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.process_reference_repository import ProcessReferenceRepository
from app.services.context_service import get_context_service
from app.services.context_enrichment_service import ContextEnrichmentService
from app.services.agent_service import get_agent
from app.config import settings
from app.utils.event_bus import get_event_bus
import asyncio

logger = logging.getLogger(__name__)


def convert_messages_to_conversation_history(
    messages: List[InterviewMessage]
) -> List[ConversationMessage]:
    """
    Convert database messages to conversation history format
    
    This helper function transforms InterviewMessage objects from the database
    into ConversationMessage objects that can be passed to the agent.
    
    Args:
        messages: List of InterviewMessage objects from database
        
    Returns:
        List of ConversationMessage objects for agent consumption
        
    Example:
        >>> db_messages = await message_repo.get_by_interview(interview_id)
        >>> conversation_history = convert_messages_to_conversation_history(db_messages)
        >>> agent.continue_interview(user_response, conversation_history, ...)
    """
    # Handle empty message list gracefully
    if not messages:
        return []
    
    # Convert each database message to conversation format
    conversation_history = []
    for msg in messages:
        conversation_history.append(
            ConversationMessage(
                role=msg.role.value,  # Convert enum to string ("user" or "assistant")
                content=msg.content,
                timestamp=msg.created_at
            )
        )
    
    return conversation_history


class InterviewService:
    """Service for interview business logic and persistence"""
    
    def __init__(self, db: AsyncSession):
        """
        Initialize service with database session
        
        Args:
            db: Async SQLAlchemy session
        """
        self.db = db
        self.interview_repo = InterviewRepository(db)
        self.message_repo = MessageRepository(db)
        self.process_ref_repo = ProcessReferenceRepository(db)
        self.context_service = get_context_service()
        self.context_enrichment_service = ContextEnrichmentService(
            cache_ttl=settings.context_cache_ttl
        )
        self.agent = get_agent()
    
    async def start_interview(
        self,
        employee_id: UUID,
        organization_id: str,
        language: str,
        technical_level: str,
        auth_token: str
    ) -> Tuple[Interview, InterviewMessage]:
        """
        Create a new interview and save the first question from the agent
        
        Enhanced with context enrichment - fetches employee, organization,
        and process context before starting the interview.
        
        Args:
            employee_id: Employee UUID
            organization_id: Organization ID (from JWT token)
            language: Interview language (es/en/pt)
            technical_level: User's technical level
            auth_token: JWT token for backend authentication
            
        Returns:
            Tuple of (Interview, InterviewMessage)
            
        Raises:
            Exception: If employee_id doesn't exist or database error occurs
        """
        logger.info(
            f"[PERF] Starting interview for employee {employee_id}",
            extra={"employee_id": str(employee_id), "language": language}
        )
        start_time = datetime.utcnow()
        
        # Fetch enriched context before starting interview (if feature enabled)
        context = None
        context_elapsed = 0.0
        if settings.enable_context_enrichment:
            try:
                context_start = datetime.utcnow()
                context = await self.context_enrichment_service.get_full_interview_context(
                    employee_id=employee_id,
                    organization_id=organization_id,
                    auth_token=auth_token,
                    db=self.db
                )
                context_elapsed = (datetime.utcnow() - context_start).total_seconds()
                logger.info(
                    f"[PERF] Context enrichment completed in {context_elapsed:.3f}s",
                    extra={
                        "employee_id": str(employee_id),
                        "context_loading_seconds": context_elapsed,
                        "processes_count": len(context.organization_processes),
                        "interviews_count": context.interview_history.total_interviews,
                        "roles_count": len(context.employee.roles)
                    }
                )
            except Exception as e:
                context_elapsed = (datetime.utcnow() - context_start).total_seconds()
                logger.error(
                    f"[ERROR] Failed to load context for employee {employee_id}: "
                    f"{type(e).__name__}: {str(e)}",
                    extra={
                        "employee_id": str(employee_id),
                        "error_type": type(e).__name__,
                        "context_loading_seconds": context_elapsed,
                        "success": False
                    }
                )
                raise ValueError(f"Employee with ID {employee_id} not found or context unavailable")
        else:
            logger.info(
                "Context enrichment disabled - starting interview with minimal context",
                extra={"feature_flag": "enable_context_enrichment", "enabled": False}
            )
        
        # Normalize language to lowercase to match enum values
        language_lower = language.lower()
        
        # Validate language
        if language_lower not in ["es", "en", "pt"]:
            raise ValueError(f"Invalid language: {language}. Must be one of: es, en, pt")
        
        # Create Interview record
        interview = Interview(
            employee_id=employee_id,
            language=language_lower,
            technical_level=technical_level,
            status=InterviewStatusEnum.in_progress,
            started_at=datetime.utcnow()
        )
        interview = await self.interview_repo.create(interview)
        
        # Ensure interview is persisted before creating first message
        await self.db.flush()
        
        # Start interview with agent using enriched context
        agent_response = self.agent.start_interview(
            context=context,
            technical_level=technical_level,
            language=language_lower
        )
        
        # Create first message (assistant role, sequence 1)
        first_message = InterviewMessage(
            interview_id=interview.id_interview,
            role=MessageRoleEnum.assistant,
            content=agent_response.question,
            sequence_number=1
        )
        first_message = await self.message_repo.create(first_message)
        
        # Log performance
        total_elapsed = (datetime.utcnow() - start_time).total_seconds()
        logger.info(
            f"[PERF] Interview started successfully in {total_elapsed:.3f}s",
            extra={
                "employee_id": str(employee_id),
                "interview_id": str(interview.id_interview),
                "total_elapsed_seconds": total_elapsed,
                "context_loading_seconds": context_elapsed,
                "performance_target_met": total_elapsed < 3.0,
                "context_enrichment_enabled": settings.enable_context_enrichment
            }
        )
        
        return interview, first_message
    
    async def continue_interview(
        self,
        interview_id: UUID,
        employee_id: UUID,
        user_response: str,
        auth_token: str,
        organization_id: Optional[str] = None
    ) -> Tuple[Interview, InterviewMessage, InterviewMessage]:
        """
        Save user response and agent's next question
        
        Enhanced with context loading and process matching - loads context,
        invokes agent with process matching, and saves process references.
        
        Args:
            interview_id: Interview UUID
            employee_id: Employee UUID (for authorization)
            user_response: User's response to previous question
            auth_token: JWT token for backend authentication
            organization_id: Organization ID from JWT token (required for context enrichment)
            
        Returns:
            Tuple of (Interview, user_message, agent_message)
            
        Raises:
            ValueError: If interview not found or access denied
        """
        logger.info(
            f"[PERF] Continuing interview {interview_id}",
            extra={"interview_id": str(interview_id), "employee_id": str(employee_id)}
        )
        start_time = datetime.utcnow()
        
        # Validate that interview belongs to employee
        interview = await self.interview_repo.get_by_id(interview_id, employee_id)
        if not interview:
            raise ValueError(f"Interview {interview_id} not found or access denied")
        
        # Load context for process matching (if feature enabled)
        context = None
        context_elapsed = 0.0
        if settings.enable_context_enrichment:
            try:
                context_start = datetime.utcnow()
                # Use organization_id from JWT token (passed as parameter from router)
                context = await self.context_enrichment_service.get_full_interview_context(
                    employee_id=employee_id,
                    organization_id=organization_id,
                    auth_token=auth_token,
                    db=self.db
                )
                context_elapsed = (datetime.utcnow() - context_start).total_seconds()
                logger.debug(
                    f"[PERF] Context loaded for interview continuation in {context_elapsed:.3f}s",
                    extra={
                        "interview_id": str(interview_id),
                        "context_loading_seconds": context_elapsed,
                        "processes_count": len(context.organization_processes)
                    }
                )
            except Exception as e:
                context_elapsed = (datetime.utcnow() - context_start).total_seconds()
                logger.warning(
                    f"[ERROR] Failed to load context for interview {interview_id}: "
                    f"{type(e).__name__}: {str(e)}",
                    extra={
                        "interview_id": str(interview_id),
                        "error_type": type(e).__name__,
                        "context_loading_seconds": context_elapsed,
                        "fallback": "continue_without_context"
                    }
                )
                # Continue without context (graceful degradation)
                context = None
        else:
            logger.debug(
                "Context enrichment disabled - continuing interview without context",
                extra={"feature_flag": "enable_context_enrichment", "enabled": False}
            )
        
        # Load conversation history
        messages = await self.message_repo.get_by_interview(interview_id)
        conversation_history = convert_messages_to_conversation_history(messages)
        
        # Get agent's response with process matching
        agent_response = await self.agent.continue_interview(
            user_response=user_response,
            conversation_history=conversation_history,
            context=context,
            technical_level=interview.technical_level,
            language=interview.language.value,
            db=self.db,  # Pass db session for process reporter lookup
            auth_token=auth_token,  # Pass auth token for backend API calls
            organization_id=organization_id  # Pass organization ID for backend API calls
        )
        
        # Save process references if any were identified (if feature enabled)
        if settings.enable_process_matching and agent_response.process_matches:
            logger.info(
                f"[PROCESS_MATCH] Found {len(agent_response.process_matches)} process matches",
                extra={
                    "interview_id": str(interview_id),
                    "matches_count": len(agent_response.process_matches),
                    "process_matching_enabled": True
                }
            )
            for match in agent_response.process_matches:
                try:
                    await self.process_ref_repo.create(
                        interview_id=interview_id,
                        process_id=match.process_id,
                        is_new_process=match.is_new,
                        confidence_score=match.confidence
                    )
                    logger.debug(
                        f"[PROCESS_MATCH] Created process reference: {match.process_name}",
                        extra={
                            "interview_id": str(interview_id),
                            "process_id": str(match.process_id),
                            "process_name": match.process_name,
                            "confidence_score": match.confidence,
                            "is_new_process": match.is_new
                        }
                    )
                except Exception as e:
                    logger.warning(
                        f"[ERROR] Failed to create process reference: {type(e).__name__}: {str(e)}",
                        extra={
                            "interview_id": str(interview_id),
                            "process_name": match.process_name,
                            "error_type": type(e).__name__
                        }
                    )
        elif not settings.enable_process_matching and agent_response.process_matches:
            logger.debug(
                "Process matching disabled - skipping process reference creation",
                extra={"feature_flag": "enable_process_matching", "enabled": False}
            )
        
        # Ensure previous query completes before getting sequence number
        await self.db.flush()
        
        # Get last sequence number
        last_sequence = await self.message_repo.get_last_sequence(interview_id)
        
        # Create user message (sequence_number + 1)
        user_message = InterviewMessage(
            interview_id=interview_id,
            role=MessageRoleEnum.user,
            content=user_response,
            sequence_number=last_sequence + 1
        )
        user_message = await self.message_repo.create(user_message)
        
        # Ensure user message is persisted before creating agent message
        await self.db.flush()
        
        # Create agent message (sequence_number + 2)
        agent_message = InterviewMessage(
            interview_id=interview_id,
            role=MessageRoleEnum.assistant,
            content=agent_response.question,
            sequence_number=last_sequence + 2
        )
        agent_message = await self.message_repo.create(agent_message)
        
        # Update interview updated_at timestamp
        interview.updated_at = datetime.utcnow()
        
        # If final, mark interview as completed
        if agent_response.is_final:
            interview = await self.interview_repo.mark_completed(interview_id)
            logger.info(f"Interview {interview_id} marked as completed")
            
            asyncio.create_task(self._publish_interview_completed(interview_id, organization_id, auth_token))
        
        await self.db.flush()
        await self.db.refresh(interview)
        
        # Log performance
        total_elapsed = (datetime.utcnow() - start_time).total_seconds()
        logger.info(
            f"[PERF] Interview continued successfully in {total_elapsed:.3f}s",
            extra={
                "interview_id": str(interview_id),
                "total_elapsed_seconds": total_elapsed,
                "context_loading_seconds": context_elapsed,
                "is_final": agent_response.is_final,
                "process_matches_count": len(agent_response.process_matches) if agent_response.process_matches else 0
            }
        )
        
        return interview, user_message, agent_message
    
    async def get_interview(
        self,
        interview_id: UUID,
        employee_id: UUID,
        allow_cross_user: bool = False
    ) -> InterviewWithMessages:
        """
        Get interview with full message history
        
        Args:
            interview_id: Interview UUID
            employee_id: Employee UUID (for authorization)
            allow_cross_user: If True, skip employee_id validation (for admin access)
            
        Returns:
            InterviewWithMessages
            
        Raises:
            InterviewNotFoundError: When interview doesn't exist
            InterviewAccessDeniedError: When user lacks permission
        """
        from app.exceptions import InterviewNotFoundError, InterviewAccessDeniedError
        
        # Get interview with messages (repository validates employee_id)
        interview = await self.interview_repo.get_by_id(interview_id, employee_id)
        
        if not interview:
            # Check if interview exists at all (without employee_id filter)
            if allow_cross_user:
                # Try to get interview without employee_id validation
                interview = await self.interview_repo.get_by_id_no_filter(interview_id)
                if not interview:
                    raise InterviewNotFoundError(interview_id)
            else:
                # Could be either not found or access denied
                # Check if interview exists without employee filter
                interview_exists = await self.interview_repo.get_by_id_no_filter(interview_id)
                if interview_exists:
                    raise InterviewAccessDeniedError(interview_id, employee_id)
                else:
                    raise InterviewNotFoundError(interview_id)
        
        # Ensure previous query completes before fetching messages
        await self.db.flush()
        
        # Get messages ordered by sequence_number
        messages = await self.message_repo.get_by_interview(interview_id)
        
        # Convert to response models
        message_responses = [
            MessageResponse(
                id_message=str(msg.id_message),
                role=msg.role.value,
                content=msg.content,
                sequence_number=msg.sequence_number,
                created_at=msg.created_at
            )
            for msg in messages
        ]
        
        return InterviewWithMessages(
            id_interview=str(interview.id_interview),
            employee_id=str(interview.employee_id),
            language=interview.language.value,
            technical_level=interview.technical_level,
            status=interview.status.value,
            started_at=interview.started_at,
            completed_at=interview.completed_at,
            total_messages=len(messages),
            messages=message_responses
        )
    
    async def get_interview_summary(
        self,
        interview_id: UUID,
        employee_id: UUID,
        allow_cross_user: bool = False
    ) -> InterviewDBResponse:
        """
        Get interview summary without messages
        
        Args:
            interview_id: Interview UUID
            employee_id: Employee UUID (for authorization)
            allow_cross_user: If True, skip employee_id validation (for admin access)
            
        Returns:
            InterviewDBResponse with basic interview data
            
        Raises:
            InterviewNotFoundError: When interview doesn't exist
            InterviewAccessDeniedError: When user lacks permission
        """
        from app.exceptions import InterviewNotFoundError, InterviewAccessDeniedError
        
        # Get interview (repository validates employee_id)
        interview = await self.interview_repo.get_by_id(interview_id, employee_id)
        
        if not interview:
            # Check if interview exists at all (without employee_id filter)
            if allow_cross_user:
                # Try to get interview without employee_id validation
                interview = await self.interview_repo.get_by_id_no_filter(interview_id)
                if not interview:
                    raise InterviewNotFoundError(interview_id)
            else:
                # Could be either not found or access denied
                # Check if interview exists without employee filter
                interview_exists = await self.interview_repo.get_by_id_no_filter(interview_id)
                if interview_exists:
                    raise InterviewAccessDeniedError(interview_id, employee_id)
                else:
                    raise InterviewNotFoundError(interview_id)
        
        # Ensure previous query completes before counting messages
        await self.db.flush()
        
        # Count messages for the interview
        message_count = await self.message_repo.count_by_interview(interview_id)
        
        return InterviewDBResponse(
            id_interview=str(interview.id_interview),
            employee_id=str(interview.employee_id),
            language=interview.language.value,
            technical_level=interview.technical_level,
            status=interview.status.value,
            started_at=interview.started_at,
            completed_at=interview.completed_at,
            total_messages=message_count
        )
    
    async def update_interview_status(
        self,
        interview_id: UUID,
        employee_id: UUID,
        new_status: InterviewStatusEnum,
        allow_cross_user: bool = False
    ) -> InterviewDBResponse:
        """
        Update interview status
        
        Args:
            interview_id: Interview UUID
            employee_id: Employee UUID (for authorization)
            new_status: New status value
            allow_cross_user: If True, skip employee_id validation (for admin access)
            
        Returns:
            InterviewDBResponse with updated interview data
            
        Raises:
            InterviewNotFoundError: When interview doesn't exist
            InterviewAccessDeniedError: When user lacks permission
        """
        from app.exceptions import InterviewNotFoundError, InterviewAccessDeniedError
        
        # Validate interview existence and ownership
        interview = await self.interview_repo.get_by_id(interview_id, employee_id)
        
        if not interview:
            # Check if interview exists at all (without employee_id filter)
            if allow_cross_user:
                # Try to get interview without employee_id validation
                interview = await self.interview_repo.get_by_id_no_filter(interview_id)
                if not interview:
                    raise InterviewNotFoundError(interview_id)
            else:
                # Could be either not found or access denied
                # Check if interview exists without employee filter
                interview_exists = await self.interview_repo.get_by_id_no_filter(interview_id)
                if interview_exists:
                    raise InterviewAccessDeniedError(interview_id, employee_id)
                else:
                    raise InterviewNotFoundError(interview_id)
        
        # Update status
        interview.status = new_status
        interview.updated_at = datetime.utcnow()
        
        # If marking as completed, set completed_at timestamp
        if new_status == InterviewStatusEnum.completed:
            interview.completed_at = datetime.utcnow()
        
        await self.db.flush()
        await self.db.refresh(interview)
        
        # Ensure previous operations complete before counting messages
        await self.db.flush()
        
        # Count messages for the interview
        message_count = await self.message_repo.count_by_interview(interview_id)
        
        return InterviewDBResponse(
            id_interview=str(interview.id_interview),
            employee_id=str(interview.employee_id),
            language=interview.language.value,
            technical_level=interview.technical_level,
            status=interview.status.value,
            started_at=interview.started_at,
            completed_at=interview.completed_at,
            total_messages=message_count
        )
    
    async def list_interviews(
        self,
        employee_id: UUID,
        filters: InterviewFilters,
        pagination: PaginationParams,
        organization_id: Optional[str] = None,
        scope: str = "own"
    ) -> Tuple[List[InterviewDBResponse], PaginationMeta]:
        """
        List interviews with filters and pagination
        
        Args:
            employee_id: Employee UUID
            filters: Filter parameters (status, language, dates)
            pagination: Pagination parameters (page, page_size)
            organization_id: Organization ID for organization-wide queries (optional)
            scope: Query scope - "own" for employee's interviews, "organization" for all
            
        Returns:
            Tuple of (list of InterviewDBResponse, PaginationMeta)
        """
        # Get interviews from repository based on scope
        if scope == "organization" and organization_id:
            interviews, total_count = await self.interview_repo.get_by_organization(
                organization_id=organization_id,
                status=filters.status,
                language=filters.language,
                start_date=filters.start_date,
                end_date=filters.end_date,
                page=pagination.page,
                page_size=pagination.page_size
            )
        else:
            interviews, total_count = await self.interview_repo.get_by_employee(
                employee_id=employee_id,
                status=filters.status,
                language=filters.language,
                start_date=filters.start_date,
                end_date=filters.end_date,
                page=pagination.page,
                page_size=pagination.page_size
            )
        
        # Ensure previous query completes before processing interviews
        await self.db.flush()
        
        # Convert to response models
        interview_responses = []
        for interview in interviews:
            # Count messages for each interview
            message_count = await self.message_repo.count_by_interview(interview.id_interview)
            
            interview_responses.append(
                InterviewDBResponse(
                    id_interview=str(interview.id_interview),
                    employee_id=str(interview.employee_id),
                    language=interview.language.value,
                    technical_level=interview.technical_level,
                    status=interview.status.value,
                    started_at=interview.started_at,
                    completed_at=interview.completed_at,
                    total_messages=message_count
                )
            )
        
        # Calculate pagination metadata
        total_pages = (total_count + pagination.page_size - 1) // pagination.page_size
        pagination_meta = PaginationMeta(
            total_items=total_count,
            total_pages=total_pages,
            current_page=pagination.page,
            page_size=pagination.page_size
        )
        
        return interview_responses, pagination_meta
    
    async def _publish_interview_completed(self, interview_id: UUID, organization_id: str, auth_token: str):
        try:
            event_bus = get_event_bus()
            await event_bus.publish("interview.completed", {
                "interview_id": str(interview_id),
                "organization_id": organization_id,
                "auth_token": auth_token
            })
            logger.info(
                f"Published interview.completed event for interview {interview_id}",
                extra={"interview_id": str(interview_id), "organization_id": organization_id}
            )
        except Exception as e:
            logger.error(
                f"Failed to publish interview.completed event: {e}",
                extra={"interview_id": str(interview_id), "error": str(e)},
                exc_info=True
            )
