"""
Interview Router
Handles all interview-related endpoints
"""
import uuid
from datetime import datetime
from typing import Optional, Literal
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.interview import (
    StartInterviewRequest, 
    ContinueInterviewRequest, 
    ExportInterviewRequest, 
    InterviewExportData,
    InterviewFilters,
    PaginationParams,
    UpdateInterviewStatusRequest,
    ExportInterviewFromDBRequest
)
from app.models.responses import success_response, error_response
from app.services.agent_service import get_agent
from app.services.context_service import get_context_service
from app.services.interview_service import InterviewService, convert_messages_to_conversation_history
from app.middleware.auth_middleware import get_current_user
from app.services.token_validator import TokenPayload
from app.database import get_db
from app.exceptions import InterviewNotFoundError, InterviewAccessDeniedError
from app.dependencies.permissions import require_permission
from app.models.permissions import InterviewPermission
from uuid import UUID

router = APIRouter(prefix="/interviews", tags=["interviews"])


@router.get("/permissions", response_model=None)
async def get_permissions():
    """
    Get all available interview permissions
    
    Returns a list of all available permissions for interview operations.
    This endpoint is public and does not require authentication.
    
    **Authentication Required:** None (public endpoint)
    
    **Response Structure:**
    ```json
    {
      "status": "success",
      "code": 200,
      "message": "Permissions retrieved successfully",
      "data": {
        "permissions": [
          {
            "name": "interviews:create",
            "description": "Create new interviews and continue existing ones"
          },
          {
            "name": "interviews:read",
            "description": "Read own interviews"
          },
          {
            "name": "interviews:read_all",
            "description": "Read all interviews in organization (admin/manager only)"
          },
          {
            "name": "interviews:update",
            "description": "Update interview status (own interviews only)"
          },
          {
            "name": "interviews:delete",
            "description": "Delete own interviews (soft delete - future implementation)"
          },
          {
            "name": "interviews:export",
            "description": "Export interviews to documents (own interviews only)"
          }
        ]
      },
      "errors": null,
      "meta": {
        "total_permissions": 6
      }
    }
    ```
    
    **Use Case:**
    - Frontend can display available permissions to users
    - Auth service can reference this list when assigning permissions
    - Documentation for developers integrating with the API
    """
    try:
        # Define permission descriptions
        permission_descriptions = {
            InterviewPermission.CREATE: "Create new interviews and continue existing ones",
            InterviewPermission.READ: "Read own interviews",
            InterviewPermission.READ_ALL: "Read all interviews in organization (admin/manager only)",
            InterviewPermission.UPDATE: "Update interview status (own interviews only)",
            InterviewPermission.DELETE: "Delete own interviews (soft delete - future implementation)",
            InterviewPermission.EXPORT: "Export interviews to documents (own interviews only)"
        }
        
        # Build permissions list
        permissions_list = [
            {
                "name": permission.value,
                "description": permission_descriptions[permission]
            }
            for permission in InterviewPermission
        ]
        
        return success_response(
            data={
                "permissions": permissions_list
            },
            message="Permissions retrieved successfully",
            meta={
                "total_permissions": len(permissions_list)
            }
        )
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"[ERROR] Exception in get_permissions:")
        print(error_detail)
        return error_response(
            message="Failed to retrieve permissions",
            code=500,
            errors=[{"field": "general", "error": str(e), "traceback": error_detail}]
        )


@router.post("/test")
async def test_interview(
    request: StartInterviewRequest,
    current_user: TokenPayload = Depends(get_current_user)
):
    """
    Test endpoint - Returns mock response without calling LLM
    """
    return success_response(
        data={
            "session_id": "test-session-123",
            "question": f"Hola! Soy el Agente ProssX. Test mode activo. Usuario: {current_user.user_id}, Org: {current_user.organization_id}, Language: {request.language}",
            "question_number": 1,
            "is_final": False
        },
        message="Test interview started successfully",
        meta={
            "test_mode": True,
            "language": request.language,
            "user_id": current_user.user_id,
            "organization_id": current_user.organization_id
        }
    )


@router.post("/start", response_model=None)
async def start_interview(
    request: StartInterviewRequest,
    current_user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(InterviewPermission.CREATE))
):
    """
    Start a new interview session
    
    Creates a new interview session and returns the first question.
    
    **Authentication Required:** Bearer token in Authorization header
    
    **Required Permission:** `interviews:create`
    
    **Request Structure:**
    ```json
    {
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
        "interview_id": "uuid-string",
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
    
    **Error Responses:**
    - 401: Missing or invalid authentication token
    - 403: Insufficient permissions (missing `interviews:create` permission)
      ```json
      {
        "status": "error",
        "code": 403,
        "message": "Insufficient permissions",
        "errors": [
          {
            "field": "permissions",
            "error": "Required permission: interviews:create",
            "user_permissions": []
          }
        ]
      }
      ```
    - 500: Server error
    
    **⚠️ IMPORTANT for Frontend:**
    - Save `interview_id` from response data for subsequent requests
    - Send interview_id in EVERY `/continue` request
    - Backend persists interview data in PostgreSQL automatically
    
    **Note:** The `context` field (processes_identified, completeness, etc.) 
    has been removed as it's only used internally by the agent.
    """
    try:
        # Get context service
        context_service = get_context_service()
        
        # Get user context using authenticated user_id from token
        user_context = await context_service.get_user_context(current_user.user_id)
        
        # Get agent
        agent = get_agent()
        
        # Start interview with language support (maintain existing logic)
        interview_response = agent.start_interview(
            user_name=user_context.get("name", "Usuario"),
            user_role=user_context.get("role", "Empleado"),
            organization=user_context.get("organization", "Organización"),
            technical_level=user_context.get("technical_level", "unknown"),
            language=request.language
        )
        
        # Persist interview in database (NEW)
        interview_service = InterviewService(db)
        interview, first_message = await interview_service.start_interview(
            employee_id=UUID(current_user.user_id),
            language=request.language,
            technical_level=user_context.get("technical_level", "unknown"),
            first_question=interview_response.question
        )
        
        # Prepare response data with interview_id from database
        data = {
            "interview_id": str(interview.id_interview),  # NEW: Return database interview_id
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
async def continue_interview(
    request: ContinueInterviewRequest,
    current_user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(InterviewPermission.CREATE))
):
    """
    Continue an ongoing interview
    
    Receives user's response and returns the next question. The backend automatically loads
    the conversation history from the database, so you only need to send the minimal payload.
    
    **Authentication Required:** Bearer token in Authorization header
    
    **Required Permission:** `interviews:create`
    
    **Authorization:**
    - User must own the interview (employee_id matches user_id from JWT)
    - Users with `interviews:read_all` permission can continue any interview in their organization
    
    **✨ OPTIMIZED:** This endpoint now requires only minimal data. The backend loads the
    conversation history from the database automatically, reducing request payload by ~99%
    (from ~50KB to ~200 bytes).
    
    **Request Structure (Minimal - Recommended):**
    ```json
    {
      "interview_id": "018e5f8b-1234-7890-abcd-123456789abc",
      "user_response": "Soy responsable del proceso de compras",
      "language": "es"
    }
    ```
    
    **Request Structure (Legacy - Deprecated):**
    ```json
    {
      "interview_id": "uuid-string",
      "user_response": "User's answer to previous question",
      "language": "es",
      "session_id": "uuid-string",        // ⚠️ DEPRECATED: Not used, optional for backward compatibility
      "conversation_history": [...]       // ⚠️ DEPRECATED: Backend loads from DB, optional for backward compatibility
    }
    ```
    
    **Required Fields:**
    - `interview_id` (string, UUID format): Interview identifier from database
    - `user_response` (string, 1-5000 chars): User's answer to the previous question
    - `language` (string, "es"|"en"|"pt"): Interview language
    
    **Optional Fields (Deprecated):**
    - `session_id` (string): Legacy session identifier - ignored by backend
    - `conversation_history` (array): Full conversation history - ignored by backend (loaded from DB)
    
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
        "interview_id": "018e5f8b-1234-7890-abcd-123456789abc",
        "session_id": null,
        "question_count": 2,
        "language": "es"
      }
    }
    ```
    
    **How It Works:**
    1. Backend receives minimal request (interview_id + user_response + language)
    2. Backend loads interview and full message history from PostgreSQL database
    3. Backend passes database history to AI agent for context
    4. Agent generates next question based on complete history
    5. Backend saves both user response and agent question to database
    6. Backend returns only the next question to frontend
    
    **Database Persistence:**
    - User response is saved to database before generating next question
    - Agent's next question is also saved to database
    - Interview updated_at timestamp is updated
    - If is_final=true, interview status is marked as completed
    
    **Error Responses:**
    
    **422 Unprocessable Entity - Validation Error:**
    ```json
    {
      "status": "error",
      "code": 422,
      "message": "Validation error",
      "errors": [
        {
          "field": "user_response",
          "error": "String should have at least 1 character",
          "type": "string_too_short"
        }
      ],
      "meta": {
        "endpoint": "/api/v1/interviews/continue",
        "method": "POST"
      }
    }
    ```
    
    **Common Validation Errors:**
    - Empty `user_response`: "String should have at least 1 character"
    - `user_response` too long: "String should have at most 5000 characters"
    - Invalid `language`: "String should match pattern '^(es|en|pt)$'"
    - Invalid `interview_id`: "Input should be a valid UUID"
    
    **400 Bad Request - Invalid Data:**
    - Invalid interview_id format or missing required fields
    
    **401 Unauthorized - Authentication Error:**
    - Missing or invalid authentication token
    
    **403 Forbidden - Access Denied:**
    ```json
    {
      "status": "error",
      "code": 403,
      "message": "Access denied",
      "errors": [
        {
          "field": "interview_id",
          "error": "You don't have permission to continue this interview"
        }
      ]
    }
    ```
    
    **404 Not Found - Interview Not Found:**
    ```json
    {
      "status": "error",
      "code": 404,
      "message": "Interview not found",
      "errors": [
        {
          "field": "interview_id",
          "error": "Interview does not exist"
        }
      ]
    }
    ```
    
    **500 Internal Server Error:**
    - Database connection error
    - AI service error
    - Unexpected server error
    
    **Migration Guide for Frontend:**
    
    **Before (Old Code):**
    ```javascript
    const response = await continueInterview({
      session_id: sessionId,
      interview_id: interviewId,
      user_response: userAnswer,
      conversation_history: conversationHistory,  // 50KB+ payload
      language: 'es'
    });
    ```
    
    **After (New Code - Recommended):**
    ```javascript
    const response = await continueInterview({
      interview_id: interviewId,
      user_response: userAnswer,
      language: 'es'
      // conversation_history removed - backend loads from DB
      // session_id removed - not needed
    });
    ```
    
    **Backward Compatibility:**
    The endpoint still accepts `session_id` and `conversation_history` fields for backward
    compatibility, but they are ignored. This allows gradual migration without breaking
    existing deployments.
    """
    try:
        # Get interview service
        interview_service = InterviewService(db)
        
        # Validate ownership: Check if interview belongs to user OR user has read_all permission
        interview = await interview_service.interview_repo.get_by_id(
            request.interview_id, 
            UUID(current_user.user_id)
        )
        
        # If interview not found, check if it exists at all (for proper error message)
        if not interview:
            # Check if user has read_all permission (admins can continue any interview)
            if current_user.has_permission(InterviewPermission.READ_ALL):
                # Admin with read_all can access any interview, try without employee_id filter
                from sqlalchemy import select
                from app.models.db_models import Interview as InterviewModel
                
                stmt = select(InterviewModel).where(InterviewModel.id_interview == request.interview_id)
                result = await db.execute(stmt)
                interview = result.scalar_one_or_none()
                
                if not interview:
                    error_resp = error_response(
                        message="Interview not found",
                        code=404,
                        errors=[{"field": "interview_id", "error": "Interview does not exist"}]
                    )
                    return JSONResponse(status_code=404, content=error_resp.model_dump())
                # Admin has access, continue with the interview
            else:
                # Regular user without read_all permission
                # Check if interview exists at all
                from sqlalchemy import select
                from app.models.db_models import Interview as InterviewModel
                
                stmt = select(InterviewModel).where(InterviewModel.id_interview == request.interview_id)
                result = await db.execute(stmt)
                exists = result.scalar_one_or_none() is not None
                
                if not exists:
                    error_resp = error_response(
                        message="Interview not found",
                        code=404,
                        errors=[{"field": "interview_id", "error": "Interview does not exist"}]
                    )
                    return JSONResponse(status_code=404, content=error_resp.model_dump())
                else:
                    # Interview exists but doesn't belong to user
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(
                        f"User {current_user.user_id} attempted to continue interview "
                        f"{request.interview_id} that belongs to another user"
                    )
                    error_resp = error_response(
                        message="Access denied",
                        code=403,
                        errors=[{
                            "field": "interview_id",
                            "error": "You don't have permission to continue this interview"
                        }]
                    )
                    return JSONResponse(status_code=403, content=error_resp.model_dump())
        
        # Get context service
        context_service = get_context_service()
        
        # Get user context using authenticated user_id from token
        user_context = await context_service.get_user_context(current_user.user_id)
        
        # Load conversation history from database (NEW: optimization)
        messages = await interview_service.message_repo.get_by_interview(request.interview_id)
        conversation_history = convert_messages_to_conversation_history(messages)
        
        # Get agent
        agent = get_agent()
        
        # Continue interview with language support (using history from DB, not request)
        interview_response = agent.continue_interview(
            user_response=request.user_response,
            conversation_history=conversation_history,  # CHANGED: Load from DB instead of request
            user_name=user_context.get("name", "Usuario"),
            user_role=user_context.get("role", "Empleado"),
            organization=user_context.get("organization", "Organización"),
            technical_level=user_context.get("technical_level", "unknown"),
            language=request.language
        )
        
        # Persist in database
        try:
            interview, user_message, agent_message = await interview_service.continue_interview(
                interview_id=request.interview_id,
                employee_id=UUID(current_user.user_id) if not current_user.has_permission(InterviewPermission.READ_ALL) else UUID(str(interview.employee_id)),
                user_response=request.user_response,
                agent_question=interview_response.question,
                is_final=interview_response.is_final
            )
        except ValueError as ve:
            # Handle interview not found or access denied
            error_msg = str(ve)
            if "not found" in error_msg.lower():
                return error_response(
                    message="Interview not found",
                    code=404,
                    errors=[{"field": "interview_id", "error": error_msg}]
                )
            elif "access denied" in error_msg.lower():
                return error_response(
                    message="Access denied",
                    code=403,
                    errors=[{"field": "interview_id", "error": error_msg}]
                )
            else:
                raise ve
        
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
                "interview_id": request.interview_id,  # Include interview_id from database
                "session_id": request.session_id,      # Keep for compatibility
                "question_count": interview_response.question_number,
                "language": request.language
            }
        )
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"[ERROR] Exception in continue_interview:")
        print(error_detail)
        return error_response(
            message="Failed to continue interview",
            code=500,
            errors=[{"field": "general", "error": str(e), "traceback": error_detail}]
        )


@router.get("", response_model=None)
async def list_interviews(
    current_user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(InterviewPermission.READ)),
    status: Optional[Literal["in_progress", "completed", "cancelled"]] = Query(
        None, 
        description="Filter by interview status"
    ),
    language: Optional[Literal["es", "en", "pt"]] = Query(
        None, 
        description="Filter by interview language"
    ),
    start_date: Optional[datetime] = Query(
        None, 
        description="Filter interviews started after this date (ISO format)"
    ),
    end_date: Optional[datetime] = Query(
        None, 
        description="Filter interviews started before this date (ISO format)"
    ),
    page: int = Query(
        1, 
        ge=1, 
        description="Page number (1-indexed)"
    ),
    page_size: int = Query(
        20, 
        ge=1, 
        le=100, 
        description="Number of items per page (max 100)"
    )
):
    """
    List interviews for the authenticated employee
    
    Retrieves a paginated list of interviews with optional filtering.
    
    **Authentication Required:** Bearer token in Authorization header
    
    **Required Permission:** `interviews:read`
    
    **Query Parameters:**
    - status: Filter by interview status (in_progress, completed, cancelled)
    - language: Filter by interview language (es, en, pt)
    - start_date: Filter interviews started after this date (ISO format)
    - end_date: Filter interviews started before this date (ISO format)
    - page: Page number (default: 1, min: 1)
    - page_size: Items per page (default: 20, min: 1, max: 100)
    
    **Authorization:**
    - Users with `interviews:read` can only see their own interviews
    - Users with `interviews:read_all` can see all interviews in their organization
    - Results are automatically filtered based on permission scope
    
    **Response Structure:**
    ```json
    {
      "status": "success",
      "code": 200,
      "message": "Interviews retrieved successfully",
      "data": [
        {
          "id_interview": "018e5f8b-1234-7890-abcd-123456789abc",
          "employee_id": "01932e5f-8b2a-7890-b123-456789abcdef",
          "language": "es",
          "technical_level": "intermediate",
          "status": "completed",
          "started_at": "2025-10-25T10:00:00Z",
          "completed_at": "2025-10-25T10:15:00Z",
          "total_messages": 12
        }
      ],
      "errors": null,
      "meta": {
        "pagination": {
          "total_items": 45,
          "total_pages": 3,
          "current_page": 1,
          "page_size": 20
        },
        "filters": {
          "status": "completed",
          "language": "es",
          "start_date": "2025-10-01T00:00:00Z",
          "end_date": "2025-10-31T23:59:59Z"
        },
        "scope": "own",
        "employee_id": "01932e5f-8b2a-7890-b123-456789abcdef"
      }
    }
    ```
    
    **Example Requests:**
    - GET /interviews - All interviews for user (page 1, 20 items)
    - GET /interviews?status=completed - Only completed interviews
    - GET /interviews?language=es&page=2 - Spanish interviews, page 2
    - GET /interviews?start_date=2025-10-01T00:00:00Z - Interviews from October 2025
    - GET /interviews?page_size=50 - 50 items per page
    
    **Error Responses:**
    - 400: Invalid query parameters (e.g., invalid date format, page < 1)
    - 403: Insufficient permissions (missing `interviews:read` permission)
      ```json
      {
        "status": "error",
        "code": 403,
        "message": "Insufficient permissions",
        "errors": [
          {
            "field": "permissions",
            "error": "Required permission: interviews:read",
            "user_permissions": []
          }
        ]
      }
      ```
    - 500: Database error
    """
    try:
        # Create filter and pagination objects
        filters = InterviewFilters(
            status=status,
            language=language,
            start_date=start_date,
            end_date=end_date
        )
        
        pagination = PaginationParams(
            page=page,
            page_size=page_size
        )
        
        # Get interview service
        interview_service = InterviewService(db)
        
        # Determine scope based on permissions
        # Users with interviews:read_all can see all interviews in organization
        # Users with only interviews:read can only see their own
        has_read_all = current_user.has_permission(InterviewPermission.READ_ALL)
        scope = "organization" if has_read_all else "own"
        
        # Get interviews with filters and pagination
        interviews, pagination_meta = await interview_service.list_interviews(
            employee_id=UUID(current_user.user_id),
            filters=filters,
            pagination=pagination,
            organization_id=current_user.organization_id if has_read_all else None,
            scope=scope
        )
        
        # Convert to dict for response
        interviews_data = [interview.model_dump() for interview in interviews]
        
        return success_response(
            data=interviews_data,
            message="Interviews retrieved successfully",
            meta={
                "pagination": pagination_meta.model_dump(),
                "filters": {
                    "status": status,
                    "language": language,
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None
                },
                "scope": scope,
                "employee_id": current_user.user_id
            }
        )
        
    except ValueError as ve:
        # Handle validation errors (e.g., invalid date format)
        return error_response(
            message="Validation error",
            code=400,
            errors=[{"field": "query_params", "error": str(ve)}]
        )
    except Exception as e:
        # Log the full error for debugging
        import traceback
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in list_interviews: {str(e)}", exc_info=True)
        
        # Return generic error response without exposing internal details
        return error_response(
            message="Failed to retrieve interviews",
            code=500,
            errors=[{"field": "general", "error": "An internal error occurred while retrieving interviews"}]
        )


@router.get("/{interview_id}", response_model=None)
async def get_interview(
    interview_id: str,
    current_user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(InterviewPermission.READ))
):
    """
    Get a specific interview with full message history
    
    Retrieves a complete interview including all messages ordered by sequence number.
    
    **Authentication Required:** Bearer token in Authorization header
    
    **Required Permission:** `interviews:read`
    
    **Path Parameters:**
    - interview_id: UUID of the interview to retrieve
    
    **Authorization:**
    - Users with `interviews:read` can only access their own interviews
    - Users with `interviews:read_all` can access any interview in their organization
    - Returns 404 if interview doesn't exist (to avoid revealing existence)
    - Returns 403 if interview exists but user doesn't have access
    
    **Response Structure:**
    ```json
    {
      "status": "success",
      "code": 200,
      "message": "Interview retrieved successfully",
      "data": {
        "id_interview": "018e5f8b-1234-7890-abcd-123456789abc",
        "employee_id": "01932e5f-8b2a-7890-b123-456789abcdef",
        "language": "es",
        "technical_level": "intermediate",
        "status": "in_progress",
        "started_at": "2025-10-25T10:00:00Z",
        "completed_at": null,
        "total_messages": 4,
        "messages": [
          {
            "id_message": "018e5f8b-2a78-7890-b123-456789abcdef",
            "role": "assistant",
            "content": "¿Cuál es tu rol en la organización?",
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
      },
      "errors": null,
      "meta": {
        "interview_id": "018e5f8b-1234-7890-abcd-123456789abc",
        "employee_id": "01932e5f-8b2a-7890-b123-456789abcdef"
      }
    }
    ```
    
    **Error Responses:**
    - 400: Invalid interview_id format
    - 401: Missing or invalid authentication token
    - 403: Insufficient permissions or access denied to interview
      ```json
      {
        "status": "error",
        "code": 403,
        "message": "Insufficient permissions",
        "errors": [
          {
            "field": "permissions",
            "error": "Required permission: interviews:read",
            "user_permissions": []
          }
        ]
      }
      ```
    - 404: Interview not found (returned even if interview exists but user lacks access, to avoid revealing existence)
    - 500: Database error
    """
    try:
        # Validate interview_id format
        try:
            interview_uuid = UUID(interview_id)
        except ValueError:
            return error_response(
                message="Validation error",
                code=400,
                errors=[{"field": "interview_id", "error": "Invalid UUID format"}]
            )
        
        # Get interview service
        interview_service = InterviewService(db)
        
        # Check if user has read_all permission (admins can see any interview)
        has_read_all = current_user.has_permission(InterviewPermission.READ_ALL)
        
        # Use service method with allow_cross_user parameter
        interview_with_messages = await interview_service.get_interview(
            interview_id=interview_uuid,
            employee_id=UUID(current_user.user_id),
            allow_cross_user=has_read_all
        )
        
        return success_response(
            data=interview_with_messages.model_dump(),
            message="Interview retrieved successfully",
            meta={
                "interview_id": interview_id,
                "employee_id": current_user.user_id
            }
        )
        
    except InterviewNotFoundError as e:
        error_resp = error_response(
            message="Interview not found",
            code=404,
            errors=[{"field": "interview_id", "error": "Interview does not exist"}]
        )
        return JSONResponse(status_code=404, content=error_resp.model_dump())
    except InterviewAccessDeniedError as e:
        # Return 404 instead of 403 to avoid revealing interview existence
        error_resp = error_response(
            message="Interview not found",
            code=404,
            errors=[{"field": "interview_id", "error": "Interview does not exist"}]
        )
        return JSONResponse(status_code=404, content=error_resp.model_dump())
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"[ERROR] Exception in get_interview:")
        print(error_detail)
        return error_response(
            message="Failed to retrieve interview",
            code=500,
            errors=[{"field": "general", "error": str(e), "traceback": error_detail}]
        )


@router.patch("/{interview_id}", response_model=None)
async def update_interview_status(
    interview_id: str,
    request: UpdateInterviewStatusRequest,
    current_user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(InterviewPermission.UPDATE))
):
    """
    Update interview status
    
    Updates the status of an existing interview. Currently only supports updating the status field.
    
    **Authentication Required:** Bearer token in Authorization header
    
    **Required Permission:** `interviews:update`
    
    **Path Parameters:**
    - interview_id: UUID of the interview to update
    
    **Request Structure:**
    ```json
    {
      "status": "completed"  // in_progress | completed | cancelled
    }
    ```
    
    **Authorization:**
    - User must own the interview (employee_id matches user_id from JWT)
    - Users with `interviews:read_all` permission can update any interview in their organization
    - Returns 403 if trying to update another employee's interview without proper permissions
    
    **Response Structure:**
    ```json
    {
      "status": "success",
      "code": 200,
      "message": "Interview status updated successfully",
      "data": {
        "id_interview": "018e5f8b-1234-7890-abcd-123456789abc",
        "employee_id": "01932e5f-8b2a-7890-b123-456789abcdef",
        "language": "es",
        "technical_level": "intermediate",
        "status": "completed",
        "started_at": "2025-10-25T10:00:00Z",
        "completed_at": "2025-10-25T10:15:00Z",
        "total_messages": 8
      },
      "errors": null,
      "meta": {
        "interview_id": "018e5f8b-1234-7890-abcd-123456789abc",
        "employee_id": "01932e5f-8b2a-7890-b123-456789abcdef",
        "updated_fields": ["status", "completed_at"]
      }
    }
    ```
    
    **Business Rules:**
    - When status is changed to "completed", completed_at is automatically set to current timestamp
    - When status is changed from "completed" to other status, completed_at is set to null
    - updated_at timestamp is always updated
    
    **Error Responses:**
    - 400: Invalid interview_id format or invalid status value
    - 401: Missing or invalid authentication token
    - 403: Insufficient permissions or access denied
      ```json
      {
        "status": "error",
        "code": 403,
        "message": "Insufficient permissions",
        "errors": [
          {
            "field": "permissions",
            "error": "Required permission: interviews:update",
            "user_permissions": []
          }
        ]
      }
      ```
    - 404: Interview not found
    - 500: Database error
    """
    try:
        # Validate interview_id format
        try:
            interview_uuid = UUID(interview_id)
        except ValueError:
            return error_response(
                message="Validation error",
                code=400,
                errors=[{"field": "interview_id", "error": "Invalid UUID format"}]
            )
        
        # Get interview service
        interview_service = InterviewService(db)
        
        # Check if user has read_all permission (admins can update any interview)
        has_read_all = current_user.has_permission(InterviewPermission.READ_ALL)
        
        # Convert status string to enum
        from app.models.db_models import InterviewStatusEnum
        status_enum = InterviewStatusEnum[request.status]
        
        # Use service method to update interview status
        # This handles validation, ownership check, and update in one call
        updated_interview = await interview_service.update_interview_status(
            interview_id=interview_uuid,
            employee_id=UUID(current_user.user_id),
            new_status=status_enum,
            allow_cross_user=has_read_all
        )
        
        # Log the update with user_id
        import logging
        logger = logging.getLogger(__name__)
        logger.info(
            f"Interview {interview_id} status updated to '{request.status}' by user {current_user.user_id}"
        )
        
        # Prepare response data from service response
        response_data = {
            "id_interview": updated_interview.id_interview,
            "employee_id": updated_interview.employee_id,
            "language": updated_interview.language,
            "technical_level": updated_interview.technical_level,
            "status": updated_interview.status,
            "started_at": updated_interview.started_at,
            "completed_at": updated_interview.completed_at,
            "total_messages": updated_interview.total_messages
        }
        
        # Determine which fields were updated
        updated_fields = ["status", "updated_at"]
        if request.status == "completed":
            updated_fields.append("completed_at")
        
        return success_response(
            data=response_data,
            message="Interview status updated successfully",
            meta={
                "interview_id": interview_id,
                "employee_id": current_user.user_id,
                "updated_fields": updated_fields
            }
        )
        
    except InterviewNotFoundError as e:
        error_resp = error_response(
            message="Interview not found",
            code=404,
            errors=[{"field": "interview_id", "error": "Interview does not exist"}]
        )
        return JSONResponse(status_code=404, content=error_resp.model_dump())
    except InterviewAccessDeniedError as e:
        error_resp = error_response(
            message="Access denied",
            code=403,
            errors=[{
                "field": "interview_id",
                "error": "You don't have permission to update this interview"
            }]
        )
        return JSONResponse(status_code=403, content=error_resp.model_dump())
    except ValueError as ve:
        # Handle validation errors (e.g., invalid status value)
        return error_response(
            message="Validation error",
            code=400,
            errors=[{"field": "status", "error": str(ve)}]
        )
    except Exception as e:
        # Handle unexpected errors
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        error_detail = traceback.format_exc()
        logger.error(f"Unexpected error in update_interview_status: {error_detail}")
        return error_response(
            message="Failed to update interview status",
            code=500,
            errors=[{"field": "general", "error": str(e)}]
        )


@router.post("/export", response_model=None)
async def export_interview(
    request: ExportInterviewFromDBRequest,
    current_user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(InterviewPermission.EXPORT))
):
    """
    Export raw interview data from database (NO AI analysis)
    
    **UPDATED:** Now retrieves interview data from database instead of request body.
    
    **Authentication Required:** Bearer token in Authorization header
    
    **Required Permission:** `interviews:export`
    
    **Design Principle**: This endpoint ONLY exports the raw conversation data.
    It does NOT perform any AI analysis or process extraction.
    
    **Request Structure:**
    ```json
    {
      "interview_id": "018e5f8b-1234-7890-abcd-123456789abc"
    }
    ```
    
    **Separation of Concerns**:
    - This service: Conducts interviews + Exports raw data from DB
    - Another service (future): Analyzes data + Extracts processes + Generates BPMN
    
    **What this returns**:
    - ✅ Full conversation history (questions + answers) from database
    - ✅ User info (name, role, organization) from context service
    - ✅ Interview metrics (total questions, duration) calculated from DB data
    - ✅ Timestamps and interview info from database
    - ❌ NO completeness_score (internal metric, removed)
    - ❌ NO process extraction (done by another service)
    
    **Response Structure:**
    ```json
    {
      "status": "success",
      "code": 200,
      "message": "Interview data exported successfully",
      "data": {
        "session_id": null,
        "user_name": "Juan Pérez",
        "conversation_history": [...],
        "total_questions": 8,
        "total_user_responses": 8,
        "is_complete": true,
        "interview_id": "018e5f8b-1234-7890-abcd-123456789abc",
        "interview_date": "2025-10-25T10:00:00Z",
        "interview_duration_minutes": 15
      },
      "errors": null,
      "meta": {
        "interview_id": "018e5f8b-1234-7890-abcd-123456789abc",
        "export_date": "2025-10-25T15:30:00Z",
        "language": "es",
        "technical_level": "intermediate",
        "data_source": "database"
      }
    }
    ```
    
    **Authorization:**
    - User must own the interview (employee_id matches user_id from JWT)
    - Users with `interviews:read_all` permission can export any interview in their organization
    - Returns 403 if trying to export another employee's interview without proper permissions
    
    **Error Responses:**
    - 400: Invalid interview_id format
    - 401: Missing or invalid authentication token
    - 403: Insufficient permissions or access denied
      ```json
      {
        "status": "error",
        "code": 403,
        "message": "Insufficient permissions",
        "errors": [
          {
            "field": "permissions",
            "error": "Required permission: interviews:export",
            "user_permissions": []
          }
        ]
      }
      ```
    - 404: Interview not found
    - 500: Database error
    
    **Use case**: 
    - Frontend calls this when user wants to export completed interview
    - Backend retrieves complete interview data from PostgreSQL
    - Another microservice can analyze exported data for BPMN generation
    """
    try:
        # Validate interview_id format
        try:
            interview_uuid = UUID(request.interview_id)
        except ValueError:
            return error_response(
                message="Validation error",
                code=400,
                errors=[{"field": "interview_id", "error": "Invalid UUID format"}]
            )
        
        # Get interview service
        interview_service = InterviewService(db)
        
        # Check if user has read_all permission (admins can export any interview)
        has_read_all = current_user.has_permission(InterviewPermission.READ_ALL)
        
        # Use service layer with allow_cross_user parameter
        # This eliminates direct database queries and handles authorization internally
        interview_with_messages = await interview_service.get_interview(
            interview_id=interview_uuid,
            employee_id=UUID(current_user.user_id),
            allow_cross_user=has_read_all
        )
        
        # Get context service for user info
        context_service = get_context_service()
        user_context = await context_service.get_user_context(current_user.user_id)
        
        # Convert database messages to conversation history format
        conversation_history = []
        for msg in interview_with_messages.messages:
            conversation_history.append({
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.created_at
            })
        
        # Calculate metrics from database data
        total_questions = len([m for m in interview_with_messages.messages if m.role == "assistant"])
        total_user_responses = len([m for m in interview_with_messages.messages if m.role == "user"])
        
        # Calculate duration from database timestamps
        interview_duration_minutes = None
        if interview_with_messages.completed_at and interview_with_messages.started_at:
            duration = (interview_with_messages.completed_at - interview_with_messages.started_at).total_seconds() / 60
            interview_duration_minutes = int(duration)
        
        # Create export data (modified to include interview_id and use DB data)
        export_data = InterviewExportData(
            session_id=None,  # No session_id for DB-persisted interviews
            user_id=current_user.user_id,
            user_name=user_context.get("name", "Usuario"),
            user_role=user_context.get("role", "Empleado"),
            organization=user_context.get("organization", "Organización"),
            interview_date=interview_with_messages.started_at,
            interview_duration_minutes=interview_duration_minutes,
            total_questions=total_questions,
            total_user_responses=total_user_responses,
            is_complete=(interview_with_messages.status == "completed"),
            conversation_history=conversation_history
        )
        
        # Add interview_id to export data (extend the model data)
        export_dict = export_data.model_dump()
        export_dict["interview_id"] = request.interview_id
        
        # Log the export with timestamp and user_id
        import logging
        logger = logging.getLogger(__name__)
        logger.info(
            f"Interview {request.interview_id} exported by user {current_user.user_id} "
            f"at {datetime.utcnow().isoformat()}"
        )
        
        return success_response(
            data=export_dict,
            message="Interview data exported successfully (from database)",
            meta={
                "interview_id": request.interview_id,
                "export_date": datetime.utcnow().isoformat(),
                "language": interview_with_messages.language,
                "technical_level": interview_with_messages.technical_level,
                "data_source": "database"
            }
        )
        
    except InterviewNotFoundError as e:
        error_resp = error_response(
            message="Interview not found",
            code=404,
            errors=[{"field": "interview_id", "error": "Interview does not exist"}]
        )
        return JSONResponse(status_code=404, content=error_resp.model_dump())
    except InterviewAccessDeniedError as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(
            f"User {current_user.user_id} attempted to export interview "
            f"{request.interview_id} that belongs to another user"
        )
        error_resp = error_response(
            message="Access denied",
            code=403,
            errors=[{
                "field": "interview_id",
                "error": "You don't have permission to export this interview"
            }]
        )
        return JSONResponse(status_code=403, content=error_resp.model_dump())
    except Exception as e:
        import traceback
        import logging
        logger = logging.getLogger(__name__)
        error_detail = traceback.format_exc()
        logger.error(f"Exception in export_interview: {error_detail}")
        return error_response(
            message="Failed to export interview data",
            code=500,
            errors=[{"field": "general", "error": str(e)}]
        )

