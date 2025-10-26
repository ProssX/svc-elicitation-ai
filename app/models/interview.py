"""
Interview Domain Models
"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Optional, Literal, Any
from datetime import datetime
from uuid import UUID


class ConversationMessage(BaseModel):
    """Single message in the conversation"""
    role: Literal["user", "assistant", "system"] = Field(description="Message role")
    content: str = Field(description="Message content")
    timestamp: Optional[datetime] = Field(default=None, description="Message timestamp")


class InterviewContext(BaseModel):
    """
    Context information gathered during the interview
    
    ⚠️ **INTERNAL USE ONLY** - NOT exposed in API responses
    
    This model is used internally by the agent to:
    - Track conversation progress
    - Determine when to finish the interview
    - Analyze conversation quality
    
    It is NOT returned in API responses to keep them clean and focused.
    Only session_id, question, question_number, and is_final are exposed.
    """
    processes_identified: List[str] = Field(
        default_factory=list,
        description="List of business processes mentioned by the user"
    )
    topics_discussed: List[str] = Field(
        default_factory=list,
        description="Topics covered in the interview"
    )
    completeness: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Interview completeness score (0-1)"
    )
    user_profile_technical: bool = Field(
        default=False,
        description="Whether the user has a technical profile"
    )


class InterviewResponse(BaseModel):
    """
    Response from the agent after each interaction
    
    ℹ️ This is the INTERNAL model used by agent_service.py
    
    The API responses (in routers/interviews.py) only expose a subset:
    - question
    - question_number
    - is_final
    - corrected_response (optional)
    
    The 'context' field is kept for internal logic but NOT returned to clients.
    """
    question: str = Field(description="The next question for the user")
    question_number: int = Field(description="Current question number")
    is_final: bool = Field(description="Whether this is the final question")
    context: InterviewContext = Field(description="Accumulated context (internal only)")
    original_user_response: Optional[str] = Field(
        default=None,
        description="Original user response (before spell check)"
    )
    corrected_user_response: Optional[str] = Field(
        default=None,
        description="Spell-checked user response"
    )


class StartInterviewRequest(BaseModel):
    """Request to start a new interview session"""
    language: str = Field(
        default="es",
        description="Interview language (es=Español, en=English, pt=Português)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "language": "es"
            }
        }


class ContinueInterviewRequest(BaseModel):
    """Request to continue an ongoing interview"""
    interview_id: str = Field(description="Interview ID from database (required for persistence)")
    session_id: str = Field(description="Interview session ID (legacy, for compatibility)")
    user_response: str = Field(description="User's response to the previous question")
    conversation_history: List[ConversationMessage] = Field(
        description="Full conversation history (stateless)"
    )
    language: str = Field(
        default="es",
        description="Interview language (es=Español, en=English, pt=Português)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "interview_id": "018e5f8b-1234-7890-abcd-123456789abc",
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "user_response": "Soy responsable del proceso de aprobación de compras",
                "conversation_history": [
                    {
                        "role": "assistant",
                        "content": "¿Cuál es tu rol en la organización?",
                        "timestamp": "2025-10-03T00:00:00Z"
                    },
                    {
                        "role": "user",
                        "content": "Soy gerente de operaciones",
                        "timestamp": "2025-10-03T00:01:00Z"
                    }
                ],
                "language": "es"
            }
        }


class ExportInterviewRequest(BaseModel):
    """
    Request to export raw interview data
    
    Frontend should send the complete interview data collected during the session.
    Backend is stateless, so all data must be provided.
    """
    session_id: str = Field(description="Interview session ID")
    conversation_history: List[ConversationMessage] = Field(
        description="Complete conversation history from the interview"
    )
    language: str = Field(
        default="es",
        description="Interview language (es=Español, en=English, pt=Português)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "conversation_history": [
                    {
                        "role": "assistant",
                        "content": "¿Cuál es tu rol?",
                        "timestamp": "2025-10-08T00:00:00Z"
                    },
                    {
                        "role": "user",
                        "content": "Soy gerente",
                        "timestamp": "2025-10-08T00:01:00Z"
                    }
                ],
                "language": "es"
            }
        }


class InterviewExportData(BaseModel):
    """
    Raw interview data export
    
    This provides the complete conversation WITHOUT any AI analysis.
    
    **Design principle**: Separation of concerns
    - This service: Conducts interviews and exports raw data
    - Another service: Analyzes data and extracts processes (BPMN generation)
    
    **What's included:**
    - ✅ Full conversation history
    - ✅ Basic metrics (question count, duration)
    - ✅ User info (name, role, organization)
    - ❌ NO completeness_score (internal metric removed)
    - ❌ NO process extraction (done by another service)
    """
    session_id: str = Field(description="Interview session ID")
    user_id: Optional[str] = Field(default=None, description="User ID")
    user_name: str = Field(description="User name")
    user_role: str = Field(description="User role")
    organization: str = Field(description="Organization name")
    interview_date: datetime = Field(description="Interview completion date")
    interview_duration_minutes: Optional[int] = Field(default=None, description="Interview duration in minutes")
    total_questions: int = Field(description="Number of questions asked by the agent")
    total_user_responses: int = Field(description="Number of responses given by the user")
    is_complete: bool = Field(description="Whether interview was completed (is_final=true)")
    conversation_history: List[ConversationMessage] = Field(
        description="Full conversation history (questions + answers)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "01932e5f-8b2a-7890-b123-456789abcdef",
                "user_name": "Juan Pérez",
                "user_role": "Gerente de Operaciones",
                "organization": "ProssX Demo",
                "interview_date": "2025-10-08T14:30:00Z",
                "interview_duration_minutes": 15,
                "total_questions": 8,
                "total_user_responses": 8,
                "is_complete": True,
                "conversation_history": [
                    {
                        "role": "assistant",
                        "content": "¿Cuál es tu función principal?",
                        "timestamp": "2025-10-08T14:15:00Z"
                    },
                    {
                        "role": "user",
                        "content": "Soy gerente de compras, apruebo solicitudes",
                        "timestamp": "2025-10-08T14:16:00Z"
                    }
                ]
            }
        }



# ============================================================================
# Database Persistence Models (NEW)
# ============================================================================

class InterviewCreate(BaseModel):
    """Request model for creating a new interview"""
    language: str = Field(default="es", pattern="^(es|en|pt)$", description="Interview language")
    technical_level: str = Field(default="unknown", description="User's technical level")
    
    class Config:
        json_schema_extra = {
            "example": {
                "language": "es",
                "technical_level": "intermediate"
            }
        }


class MessageResponse(BaseModel):
    """Response model for individual interview messages"""
    id_message: str = Field(description="Message UUID")
    role: Literal["assistant", "user", "system"] = Field(description="Message role")
    content: str = Field(description="Message content")
    sequence_number: int = Field(description="Message sequence number in conversation")
    created_at: datetime = Field(description="Message creation timestamp")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id_message": "018e5f8b-2a78-7890-b123-456789abcdef",
                "role": "assistant",
                "content": "¿Cuál es tu rol en la organización?",
                "sequence_number": 1,
                "created_at": "2025-10-25T10:30:00Z"
            }
        }


class InterviewDBResponse(BaseModel):
    """Response model for basic interview information from database"""
    id_interview: str = Field(description="Interview UUID")
    employee_id: str = Field(description="Employee UUID")
    language: str = Field(description="Interview language")
    technical_level: str = Field(description="User's technical level")
    status: str = Field(description="Interview status (in_progress, completed, cancelled)")
    started_at: datetime = Field(description="Interview start timestamp")
    completed_at: Optional[datetime] = Field(default=None, description="Interview completion timestamp")
    total_messages: int = Field(description="Total number of messages in the interview")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id_interview": "018e5f8b-1234-7890-abcd-123456789abc",
                "employee_id": "01932e5f-8b2a-7890-b123-456789abcdef",
                "language": "es",
                "technical_level": "intermediate",
                "status": "in_progress",
                "started_at": "2025-10-25T10:00:00Z",
                "completed_at": None,
                "total_messages": 5
            }
        }


class InterviewWithMessages(InterviewDBResponse):
    """Response model for detailed interview with full message history"""
    messages: List[MessageResponse] = Field(default_factory=list, description="Ordered list of interview messages")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id_interview": "018e5f8b-1234-7890-abcd-123456789abc",
                "employee_id": "01932e5f-8b2a-7890-b123-456789abcdef",
                "language": "es",
                "technical_level": "intermediate",
                "status": "in_progress",
                "started_at": "2025-10-25T10:00:00Z",
                "completed_at": None,
                "total_messages": 2,
                "messages": [
                    {
                        "id_message": "018e5f8b-2a78-7890-b123-456789abcdef",
                        "role": "assistant",
                        "content": "¿Cuál es tu rol?",
                        "sequence_number": 1,
                        "created_at": "2025-10-25T10:00:00Z"
                    },
                    {
                        "id_message": "018e5f8b-3b89-7890-c234-567890abcdef",
                        "role": "user",
                        "content": "Soy gerente de operaciones",
                        "sequence_number": 2,
                        "created_at": "2025-10-25T10:01:00Z"
                    }
                ]
            }
        }


class InterviewFilters(BaseModel):
    """Query parameters for filtering interviews"""
    status: Optional[Literal["in_progress", "completed", "cancelled"]] = Field(
        default=None,
        description="Filter by interview status"
    )
    language: Optional[Literal["es", "en", "pt"]] = Field(
        default=None,
        description="Filter by interview language"
    )
    start_date: Optional[datetime] = Field(
        default=None,
        description="Filter interviews started after this date"
    )
    end_date: Optional[datetime] = Field(
        default=None,
        description="Filter interviews started before this date"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "completed",
                "language": "es",
                "start_date": "2025-10-01T00:00:00Z",
                "end_date": "2025-10-31T23:59:59Z"
            }
        }


class PaginationParams(BaseModel):
    """Query parameters for pagination"""
    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(default=20, ge=1, le=100, description="Number of items per page (max 100)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "page": 1,
                "page_size": 20
            }
        }


class PaginationMeta(BaseModel):
    """Metadata for paginated responses"""
    total_items: int = Field(description="Total number of items across all pages")
    total_pages: int = Field(description="Total number of pages")
    current_page: int = Field(description="Current page number")
    page_size: int = Field(description="Number of items per page")
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_items": 45,
                "total_pages": 3,
                "current_page": 1,
                "page_size": 20
            }
        }


class UpdateInterviewStatusRequest(BaseModel):
    """Request model for updating interview status"""
    status: Literal["in_progress", "completed", "cancelled"] = Field(
        description="New interview status"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "completed"
            }
        }

class ExportInterviewFromDBRequest(BaseModel):
    """Request model for exporting interview data from database"""
    interview_id: str = Field(description="Interview UUID to export")
    
    class Config:
        json_schema_extra = {
            "example": {
                "interview_id": "018e5f8b-1234-7890-abcd-123456789abc"
            }
        }