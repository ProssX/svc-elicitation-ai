"""
Interview Domain Models
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal, Any
from datetime import datetime


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
    session_id: str = Field(description="Interview session ID")
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

