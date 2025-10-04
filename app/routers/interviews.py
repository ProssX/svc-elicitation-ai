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
            "is_final": False,
            "context": {
                "processes_identified": [],
                "topics_discussed": [],
                "completeness": 0.0
            }
        },
        message="Test interview started successfully",
        meta={"test_mode": True}
    )


@router.post("/start")
async def start_interview(request: StartInterviewRequest):
    """
    Start a new interview session
    
    Creates a new interview session and returns the first question
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
        
        # Prepare response data
        data = {
            "session_id": session_id,
            "question": interview_response.question,
            "question_number": interview_response.question_number,
            "is_final": interview_response.is_final,
            "context": {
                "processes_identified": interview_response.context.processes_identified,
                "topics_discussed": interview_response.context.topics_discussed,
                "completeness": interview_response.context.completeness
            }
        }
        
        return success_response(
            data=data,
            message="Interview started successfully",
            meta={
                "user_name": user_context.get("name"),
                "organization": user_context.get("organization")
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


@router.post("/continue")
async def continue_interview(request: ContinueInterviewRequest):
    """
    Continue an ongoing interview
    
    Receives user's response and returns the next question
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
        
        # Prepare response data
        data = {
            "question": interview_response.question,
            "question_number": interview_response.question_number,
            "is_final": interview_response.is_final,
            "context": {
                "processes_identified": interview_response.context.processes_identified,
                "topics_discussed": interview_response.context.topics_discussed,
                "completeness": interview_response.context.completeness
            },
            "corrected_response": interview_response.corrected_user_response
        }
        
        return success_response(
            data=data,
            message="Question generated successfully",
            meta={
                "session_id": request.session_id,
                "question_count": interview_response.question_number
            }
        )
        
    except Exception as e:
        return error_response(
            message="Failed to continue interview",
            code=500,
            errors=[{"field": "general", "error": str(e)}]
        )


@router.post("/export")
async def export_interview(request: ExportInterviewRequest):
    """
    Export raw interview data (NO AI analysis)
    
    **Design Principle**: This endpoint ONLY exports the raw conversation and metadata.
    It does NOT perform any AI analysis or process extraction.
    
    **Separation of Concerns**:
    - This service: Conducts interviews + Exports raw data
    - Another service (future): Analyzes data + Extracts processes + Generates BPMN
    
    **What this returns**:
    - ✅ Full conversation history (questions + answers)
    - ✅ User metadata (name, role, organization)
    - ✅ Interview metrics (duration, completeness, total questions)
    - ✅ Timestamps and session info
    - ❌ NO process extraction (that's for another service)
    
    **Use case**: 
    - Frontend calls this when interview is complete (is_final=true)
    - Backend PHP persists raw data to PostgreSQL
    - Another microservice/batch process analyzes it later
    
    **Example Response**:
    ```json
    {
      "status": "success",
      "data": {
        "session_id": "uuid",
        "user_name": "Juan Pérez",
        "conversation_history": [...],
        "completeness_score": 0.85,
        "total_questions": 8
      }
    }
    ```
    """
    try:
        # Get context service
        context_service = get_context_service()
        
        # Get user context (mock for MVP)
        user_context = await context_service.get_user_context("user-123")
        
        # For now, we need conversation_history from localStorage (frontend should send it)
        # In production, you might store sessions temporarily or retrieve from frontend
        # For this endpoint, we'll return what we have in the request
        
        # This is a SIMPLIFIED version - in production you'd retrieve the full session
        # For now, we'll create a basic export structure
        export_data = InterviewExportData(
            session_id=request.session_id,
            user_id="user-123",  # From auth in production
            user_name=user_context.get("name", "Usuario"),
            user_role=user_context.get("role", "Empleado"),
            organization=user_context.get("organization", "Organización"),
            interview_date=datetime.now(),
            interview_duration_minutes=None,  # Would calculate from timestamps
            total_questions=0,  # Would get from conversation_history
            total_user_responses=0,  # Would get from conversation_history
            completeness_score=0.0,  # Would get from last context
            is_complete=True,  # Assume complete if exporting
            conversation_history=[],  # Would get from localStorage or session store
            metadata={
                "technical_level": user_context.get("technical_level", "unknown"),
                "language": "es"  # Default, would come from request
            }
        )
        
        return success_response(
            data=export_data.model_dump(),
            message="Interview data exported successfully (raw data only)",
            meta={
                "session_id": request.session_id,
                "export_date": datetime.now().isoformat(),
                "note": "This is raw data. Process extraction should be done by a separate service."
            }
        )
        
    except Exception as e:
        return error_response(
            message="Failed to export interview data",
            code=500,
            errors=[{"field": "general", "error": str(e)}]
        )

