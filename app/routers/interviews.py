"""
Interview Router
Handles all interview-related endpoints
"""
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException
from app.models.interview import StartInterviewRequest, ContinueInterviewRequest, ExportInterviewRequest, InterviewExportData
from app.models.responses import success_response, error_response
from app.services.agent_service import get_agent
from app.services.context_service import get_context_service

router = APIRouter(prefix="/interviews", tags=["interviews"])


@router.post("/test")
async def test_interview(request: StartInterviewRequest):
    """
    Test endpoint - Returns mock response without calling LLM
    """
    return success_response(
        data={
            "session_id": "test-session-123",
            "question": f"Hola! Soy el Agente ProssX. Test mode activo. Usuario: {request.user_id}, Org: {request.organization_id}, Role: {request.role_id}, Language: {request.language}",
            "question_number": 1,
            "is_final": False
        },
        message="Test interview started successfully",
        meta={
            "test_mode": True,
            "language": request.language
        }
    )


@router.post("/start", response_model=None)
async def start_interview(request: StartInterviewRequest):
    """
    Start a new interview session
    
    Creates a new interview session and returns the first question.
    
    **Request Structure:**
    ```json
    {
      "user_id": "optional-user-id",
      "organization_id": "1",
      "role_id": "1",
      "language": "es"  // Optional: es|en|pt (default: "es")
    }
    ```
    
    **Response Structure:**
    ```json
    {
      "status": "success",
      "code": 200,
      "message": "Interview started successfully",
      "data": {
        "session_id": "uuid-string",
        "question": "Agent's first question in selected language",
        "question_number": 1,
        "is_final": false
      },
      "errors": null,
      "meta": {
        "user_name": "User's name",
        "organization": "Organization name",
        "language": "es"  // ⚠️ IMPORTANT: Persist this for /continue requests
      }
    }
    ```
    
    **⚠️ IMPORTANT for Frontend:**
    - Save `meta.language` from response to localStorage
    - Send it in EVERY `/continue` request
    - Backend is stateless (doesn't remember language between requests)
    
    **Note:** The `context` field (processes_identified, completeness, etc.) 
    has been removed as it's only used internally by the agent.
    """
    try:
        # Get context service
        context_service = get_context_service()
        
        # Get user context
        user_context = await context_service.get_user_context(request.user_id)
        
        # Get agent
        agent = get_agent()
        
        # Start interview with language support
        interview_response = agent.start_interview(
            user_name=user_context.get("name", "Usuario"),
            user_role=user_context.get("role", "Empleado"),
            organization=user_context.get("organization", "Organización"),
            technical_level=user_context.get("technical_level", "unknown"),
            language=request.language
        )
        
        # Generate session ID
        session_id = str(uuid.uuid4())
        
        # Prepare response data (simplified, no internal context exposed)
        data = {
            "session_id": session_id,
            "question": interview_response.question,
            "question_number": interview_response.question_number,
            "is_final": interview_response.is_final
        }
        
        return success_response(
            data=data,
            message="Interview started successfully",
            meta={
                "user_name": user_context.get("name"),
                "organization": user_context.get("organization"),
                "language": request.language  # Include language for persistence
            }
        )
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"[ERROR] Exception in start_interview:")
        print(error_detail)
        return error_response(
            message=f"Failed to start interview: {str(e)}",
            code=500,
            errors=[{"field": "general", "error": str(e), "traceback": error_detail}]
        )


@router.post("/continue", response_model=None)
async def continue_interview(request: ContinueInterviewRequest):
    """
    Continue an ongoing interview
    
    Receives user's response and returns the next question.
    
    **⚠️ IMPORTANT:** The `language` parameter is REQUIRED in each request 
    because the backend is stateless (doesn't store session data). 
    It must be sent to ensure the agent responds in the correct language.
    
    **Request Structure:**
    ```json
    {
      "session_id": "uuid-string",
      "user_response": "User's answer to previous question",
      "conversation_history": [...],
      "language": "es"  // ⚠️ REQUIRED: es|en|pt
    }
    ```
    
    **Response Structure:**
    ```json
    {
      "status": "success",
      "code": 200,
      "message": "Question generated successfully",
      "data": {
        "question": "Agent's next question",
        "question_number": 2,
        "is_final": false,
        "corrected_response": "User's response (spell-checked)"
      },
      "errors": null,
      "meta": {
        "session_id": "uuid-string",
        "question_count": 2,
        "language": "es"  // Same as request
      }
    }
    ```
    
    **Why `language` in every request?**
    - Backend is stateless (no session storage)
    - Ensures agent uses correct language for system prompt
    - Maintains conversation consistency
    - If omitted, defaults to "es" (may break multi-language conversations)
    """
    try:
        # Get context service
        context_service = get_context_service()
        
        # For now, use mock user (in production, get from session/auth)
        user_context = await context_service.get_user_context("user-123")
        
        # Get agent
        agent = get_agent()
        
        # Continue interview with language support
        interview_response = agent.continue_interview(
            user_response=request.user_response,
            conversation_history=request.conversation_history,
            user_name=user_context.get("name", "Usuario"),
            user_role=user_context.get("role", "Empleado"),
            organization=user_context.get("organization", "Organización"),
            technical_level=user_context.get("technical_level", "unknown"),
            language=request.language
        )
        
        # Prepare response data (simplified, no internal context exposed)
        data = {
            "question": interview_response.question,
            "question_number": interview_response.question_number,
            "is_final": interview_response.is_final,
            "corrected_response": interview_response.corrected_user_response
        }
        
        return success_response(
            data=data,
            message="Question generated successfully",
            meta={
                "session_id": request.session_id,
                "question_count": interview_response.question_number,
                "language": request.language  # Include language for persistence
            }
        )
        
    except Exception as e:
        return error_response(
            message="Failed to continue interview",
            code=500,
            errors=[{"field": "general", "error": str(e)}]
        )


@router.post("/export", response_model=None)
async def export_interview(request: ExportInterviewRequest):
    """
    Export raw interview data (NO AI analysis)
    
    **Design Principle**: This endpoint ONLY exports the raw conversation data.
    It does NOT perform any AI analysis or process extraction.
    
    **Request Structure:**
    ```json
    {
      "session_id": "uuid-string",
      "conversation_history": [...],  // Complete conversation from localStorage
      "language": "es"  // Interview language
    }
    ```
    
    **Separation of Concerns**:
    - This service: Conducts interviews + Exports raw data
    - Another service (future): Analyzes data + Extracts processes + Generates BPMN
    
    **What this returns**:
    - ✅ Full conversation history (questions + answers)
    - ✅ User info (name, role, organization)
    - ✅ Interview metrics (total questions, duration)
    - ✅ Timestamps and session info
    - ❌ NO completeness_score (internal metric, removed)
    - ❌ NO process extraction (done by another service)
    
    **Response Structure:**
    ```json
    {
      "status": "success",
      "code": 200,
      "message": "Interview data exported successfully",
      "data": {
        "session_id": "uuid",
        "user_name": "Juan Pérez",
        "conversation_history": [...],
        "total_questions": 8,
        "total_user_responses": 8,
        "is_complete": true
      },
      "errors": null,
      "meta": {
        "session_id": "uuid",
        "export_date": "2025-10-08T...",
        "language": "es",  // ⚠️ Language in meta (consistent with other endpoints)
        "technical_level": "non-technical"
      }
    }
    ```
    
    **Use case**: 
    - Frontend calls this when interview is complete (is_final=true)
    - Backend PHP persists raw data to PostgreSQL
    - Another microservice analyzes it later for BPMN generation
    """
    try:
        # Get context service
        context_service = get_context_service()
        
        # Get user context (mock for MVP)
        user_context = await context_service.get_user_context("user-123")
        
        # Calculate metrics from conversation_history
        total_questions = len([m for m in request.conversation_history if m.role == "assistant"])
        total_user_responses = len([m for m in request.conversation_history if m.role == "user"])
        
        # Calculate duration if timestamps available
        interview_duration_minutes = None
        if request.conversation_history and len(request.conversation_history) >= 2:
            first_msg = request.conversation_history[0]
            last_msg = request.conversation_history[-1]
            if first_msg.timestamp and last_msg.timestamp:
                duration = (last_msg.timestamp - first_msg.timestamp).total_seconds() / 60
                interview_duration_minutes = int(duration)
        
        # Create export data
        export_data = InterviewExportData(
            session_id=request.session_id,
            user_id="user-123",  # From auth in production
            user_name=user_context.get("name", "Usuario"),
            user_role=user_context.get("role", "Empleado"),
            organization=user_context.get("organization", "Organización"),
            interview_date=datetime.now(),
            interview_duration_minutes=interview_duration_minutes,
            total_questions=total_questions,
            total_user_responses=total_user_responses,
            is_complete=True,  # Assume complete if exporting
            conversation_history=request.conversation_history
        )
        
        return success_response(
            data=export_data.model_dump(),
            message="Interview data exported successfully (raw data only)",
            meta={
                "session_id": request.session_id,
                "export_date": datetime.now().isoformat(),
                "language": request.language,  # ✅ Language in meta (consistent)
                "technical_level": user_context.get("technical_level", "unknown"),
                "note": "This is raw data. Process extraction should be done by a separate service."
            }
        )
        
    except Exception as e:
        return error_response(
            message="Failed to export interview data",
            code=500,
            errors=[{"field": "general", "error": str(e)}]
        )

