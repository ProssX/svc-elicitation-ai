# Design Document

## Overview

Este documento describe el diseño técnico para optimizar el servicio de entrevistas de IA, enfocándose en:

1. **API Optimization**: Reducir el payload de requests eliminando el envío redundante del historial de conversación
2. **Data Model Cleanup**: Simplificar el modelo Interview eliminando atributos innecesarios
3. **Error Handling Standardization**: Implementar manejo consistente de errores de validación Pydantic

### Design Goals

- **Performance**: Reducir el tamaño de requests de ~50KB a ~200 bytes
- **Simplicity**: Eliminar campos confusos o redundantes del modelo
- **Consistency**: Estandarizar respuestas de error en toda la API
- **Backward Compatibility**: Mantener compatibilidad temporal con requests legacy

## Architecture

### Current Architecture (Before)

```
Frontend                          Backend
┌─────────────────┐              ┌──────────────────────┐
│  React App      │              │  FastAPI Service     │
│                 │              │                      │
│  localStorage   │              │  ┌────────────────┐ │
│  - session_id   │   POST       │  │ /continue      │ │
│  - history[]    │─────────────>│  │                │ │
│                 │   {          │  │ Receives:      │ │
│                 │    session_id│  │ - session_id   │ │
│                 │    interview_│  │ - interview_id │ │
│                 │    history[] │  │ - history[]    │ │
│                 │    response  │  │ - response     │ │
│                 │   }          │  │                │ │
│                 │              │  │ Ignores        │ │
│                 │              │  │ history[]!     │ │
│                 │              │  └────────────────┘ │
│                 │              │         │           │
│                 │              │         v           │
│                 │              │  ┌────────────────┐ │
│                 │              │  │  PostgreSQL    │ │
│                 │              │  │  - interviews  │ │
│                 │              │  │  - messages    │ │
│                 │              │  └────────────────┘ │
└─────────────────┘              └──────────────────────┘

Problems:
- Frontend sends full history (50KB+) but backend doesn't use it
- session_id is redundant (interview_id is the real identifier)
- Wasted bandwidth and processing time
```

### New Architecture (After)

```
Frontend                          Backend
┌─────────────────┐              ┌──────────────────────┐
│  React App      │              │  FastAPI Service     │
│                 │              │                      │
│  State only     │              │  ┌────────────────┐ │
│  - interview_id │   POST       │  │ /continue      │ │
│                 │─────────────>│  │                │ │
│                 │   {          │  │ Receives:      │ │
│                 │    interview_│  │ - interview_id │ │
│                 │    response  │  │ - response     │ │
│                 │    language  │  │ - language     │ │
│                 │   }          │  │                │ │
│                 │   (~200B)    │  │ Loads history  │ │
│                 │              │  │ from DB        │ │
│                 │              │  └────────┬───────┘ │
│                 │              │           │         │
│                 │              │           v         │
│                 │              │  ┌────────────────┐ │
│                 │              │  │  PostgreSQL    │ │
│                 │              │  │  - interviews  │ │
│                 │              │  │  - messages    │ │
│                 │              │  └────────────────┘ │
│                 │              │           │         │
│                 │              │           v         │
│                 │   Response   │  ┌────────────────┐ │
│                 │<─────────────│  │ Agent Service  │ │
│                 │   {          │  │ (uses history  │ │
│                 │    question  │  │  from DB)      │ │
│                 │    is_final  │  └────────────────┘ │
│                 │   }          │                      │
└─────────────────┘              └──────────────────────┘

Benefits:
- 99% reduction in request size (50KB → 200B)
- Single source of truth (PostgreSQL)
- Simpler frontend code
- Better scalability
```

## Components and Interfaces

### 1. API Request Models (Pydantic)

#### Current ContinueInterviewRequest
```python
class ContinueInterviewRequest(BaseModel):
    interview_id: str  # Required
    session_id: str    # Legacy, not used
    user_response: str
    conversation_history: List[ConversationMessage]  # Redundant!
    language: str = "es"
```

#### New ContinueInterviewRequest (Optimized)
```python
class ContinueInterviewRequest(BaseModel):
    """
    Optimized request model - only essential data
    """
    interview_id: str = Field(
        description="Interview UUID from database"
    )
    user_response: str = Field(
        description="User's answer to the previous question",
        min_length=1,
        max_length=5000
    )
    language: str = Field(
        default="es",
        pattern="^(es|en|pt)$",
        description="Interview language"
    )
    
    # Legacy fields (optional for backward compatibility)
    session_id: Optional[str] = Field(
        default=None,
        description="Legacy session ID (deprecated, not used)"
    )
    conversation_history: Optional[List[ConversationMessage]] = Field(
        default=None,
        description="Legacy field (deprecated, backend loads from DB)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "interview_id": "018e5f8b-1234-7890-abcd-123456789abc",
                "user_response": "Soy responsable del proceso de compras",
                "language": "es"
            }
        }
```

**Key Changes:**
- `conversation_history` is now Optional (backend ignores it)
- `session_id` is now Optional (deprecated)
- Added validation: `user_response` min/max length
- Added validation: `language` pattern matching
- Clear documentation about deprecated fields

### 2. Database Model Cleanup

#### Current Interview Model
```python
class Interview(Base):
    __tablename__ = "interview"
    
    id_interview = Column(UUID, primary_key=True)  # ✅ Keep
    employee_id = Column(UUID, nullable=False)     # ✅ Keep
    language = Column(Enum, nullable=False)        # ✅ Keep
    technical_level = Column(String)               # ✅ Keep
    status = Column(Enum, nullable=False)          # ✅ Keep
    started_at = Column(DateTime, nullable=False)  # ✅ Keep
    completed_at = Column(DateTime, nullable=True) # ✅ Keep
    created_at = Column(DateTime, nullable=False)  # ✅ Keep
    updated_at = Column(DateTime, nullable=False)  # ✅ Keep
    
    # Relationships
    messages = relationship("InterviewMessage", ...)  # ✅ Keep
```

**Analysis:**
- ✅ **id_interview**: Primary key, essential
- ✅ **employee_id**: Foreign key to employee, essential
- ✅ **language**: Needed for multi-language support
- ✅ **technical_level**: Used by agent for question adaptation
- ✅ **status**: Tracks interview lifecycle (in_progress, completed, cancelled)
- ✅ **started_at**: Audit trail, essential
- ✅ **completed_at**: Marks completion time, essential
- ✅ **created_at/updated_at**: Standard audit fields, essential
- ✅ **messages**: Relationship to conversation history, essential

**Conclusion:** All fields are necessary. No cleanup needed in Interview model.

**Note about session_id:**
- `session_id` does NOT exist in the database model (only in API requests)
- It's a legacy field from when interviews were stored in localStorage
- We'll deprecate it in the API but keep it optional for backward compatibility

### 3. Error Handling Architecture

#### Current Error Handling
```python
# main.py - Partial error handling
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    # Handles HTTPException but NOT RequestValidationError
    return JSONResponse(...)

@app.exception_handler(InterviewNotFoundError)
async def interview_not_found_handler(request, exc):
    # Custom exception handling
    return JSONResponse(...)
```

**Problem:** Pydantic validation errors return FastAPI's default format:
```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "user_response"],
      "msg": "String should have at least 1 character",
      "input": "",
      "ctx": {"min_length": 1}
    }
  ]
}
```

This is inconsistent with ProssX standard format used everywhere else.

#### New Error Handling (Standardized)

```python
# main.py - Add RequestValidationError handler
from fastapi.exceptions import RequestValidationError

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, 
    exc: RequestValidationError
) -> JSONResponse:
    """
    Handle Pydantic validation errors with ProssX standard format
    
    Transforms FastAPI's default validation error format to match
    the standard error format used across all ProssX microservices.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Extract errors from Pydantic exception
    errors = []
    for error in exc.errors():
        # Get field name from location path
        field_path = " -> ".join(str(loc) for loc in error["loc"][1:])  # Skip 'body'
        field_name = field_path if field_path else "request"
        
        # Get human-readable error message
        error_msg = error.get("msg", "Validation error")
        
        # Add to errors array
        errors.append({
            "field": field_name,
            "error": error_msg,
            "type": error.get("type", "validation_error")
        })
    
    # Log validation error for debugging
    logger.warning(
        f"Validation error on {request.method} {request.url.path}: "
        f"{len(errors)} field(s) failed validation"
    )
    
    # Return ProssX standard format
    return JSONResponse(
        status_code=422,  # Unprocessable Entity (standard for validation errors)
        content={
            "status": "error",
            "code": 422,
            "message": "Validation error",
            "errors": errors,
            "meta": {
                "endpoint": str(request.url.path),
                "method": request.method
            }
        }
    )
```

**New Error Response Format:**
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
    },
    {
      "field": "language",
      "error": "String should match pattern '^(es|en|pt)$'",
      "type": "string_pattern_mismatch"
    }
  ],
  "meta": {
    "endpoint": "/api/v1/interviews/continue",
    "method": "POST"
  }
}
```

### 4. Service Layer Changes

#### InterviewService.continue_interview()

**Current Implementation:**
```python
async def continue_interview(
    self,
    interview_id: UUID,
    employee_id: UUID,
    user_response: str,
    agent_question: str,
    is_final: bool = False
) -> Tuple[Interview, InterviewMessage, InterviewMessage]:
    # Validates ownership
    # Saves user message
    # Saves agent message
    # Updates interview
    return interview, user_message, agent_message
```

**No changes needed** - Service layer already works correctly. It:
- ✅ Validates interview ownership
- ✅ Loads interview from database
- ✅ Persists messages to database
- ✅ Updates interview status

The optimization happens at the **router level** (not service level).

#### Router Changes (interviews.py)

**Current Flow:**
```python
@router.post("/continue")
async def continue_interview(request: ContinueInterviewRequest, ...):
    # 1. Receives conversation_history from frontend (not used!)
    # 2. Calls agent.continue_interview() with history from request
    # 3. Agent generates next question
    # 4. Saves to database
    # 5. Returns response
```

**New Flow:**
```python
@router.post("/continue")
async def continue_interview(request: ContinueInterviewRequest, ...):
    # 1. Validate interview_id
    # 2. Load interview + messages from database
    # 3. Convert DB messages to conversation_history format
    # 4. Call agent.continue_interview() with history from DB
    # 5. Agent generates next question
    # 6. Save to database
    # 7. Return response
```

**Key Change:** Load history from database instead of request body.

## Data Models

### Request/Response Flow

```
┌─────────────────────────────────────────────────────────────┐
│  POST /api/v1/interviews/continue                           │
├─────────────────────────────────────────────────────────────┤
│  Request Body (ContinueInterviewRequest):                   │
│  {                                                           │
│    "interview_id": "018e5f8b-1234-7890-abcd-123456789abc",  │
│    "user_response": "Soy gerente de compras",               │
│    "language": "es"                                          │
│  }                                                           │
│                                                              │
│  Size: ~200 bytes (vs 50KB before)                          │
└─────────────────────────────────────────────────────────────┘
                            │
                            v
┌─────────────────────────────────────────────────────────────┐
│  Backend Processing:                                         │
│                                                              │
│  1. Validate request (Pydantic)                             │
│  2. Validate interview_id format (UUID)                     │
│  3. Load interview from DB:                                 │
│     SELECT * FROM interview WHERE id_interview = ?          │
│  4. Load messages from DB:                                  │
│     SELECT * FROM interview_message                         │
│     WHERE interview_id = ?                                  │
│     ORDER BY sequence_number                                │
│  5. Convert to ConversationMessage[] format                 │
│  6. Call agent.continue_interview(history_from_db)          │
│  7. Save user response to DB                                │
│  8. Save agent question to DB                               │
│  9. Update interview.updated_at                             │
│ 10. If is_final, mark interview as completed                │
└─────────────────────────────────────────────────────────────┘
                            │
                            v
┌─────────────────────────────────────────────────────────────┐
│  Response (StandardResponse):                                │
│  {                                                           │
│    "status": "success",                                      │
│    "code": 200,                                              │
│    "message": "Question generated successfully",             │
│    "data": {                                                 │
│      "question": "¿Qué procesos gestionas?",                │
│      "question_number": 3,                                   │
│      "is_final": false                                       │
│    },                                                        │
│    "meta": {                                                 │
│      "interview_id": "018e5f8b-1234-7890-abcd-123456789abc",│
│      "question_count": 3,                                    │
│      "language": "es"                                        │
│    }                                                         │
│  }                                                           │
└─────────────────────────────────────────────────────────────┘
```

### Database Schema (No Changes)

```sql
-- interview table (no changes needed)
CREATE TABLE interview (
    id_interview UUID PRIMARY KEY,
    employee_id UUID NOT NULL,
    language language_enum NOT NULL,
    technical_level VARCHAR(20) NOT NULL DEFAULT 'unknown',
    status interview_status_enum NOT NULL DEFAULT 'in_progress',
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- interview_message table (no changes needed)
CREATE TABLE interview_message (
    id_message UUID PRIMARY KEY,
    interview_id UUID NOT NULL REFERENCES interview(id_interview) ON DELETE CASCADE,
    role message_role_enum NOT NULL,
    content TEXT NOT NULL,
    sequence_number INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_interview_sequence ON interview_message(interview_id, sequence_number);
```

**Analysis:** Schema is already optimal. No migrations needed.

## Error Handling

### Error Scenarios and Responses

#### 1. Validation Error (Pydantic)

**Scenario:** Frontend sends empty user_response

**Request:**
```json
{
  "interview_id": "018e5f8b-1234-7890-abcd-123456789abc",
  "user_response": "",
  "language": "es"
}
```

**Response (422):**
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

#### 2. Invalid UUID Format

**Scenario:** Frontend sends malformed interview_id

**Request:**
```json
{
  "interview_id": "invalid-uuid",
  "user_response": "Mi respuesta",
  "language": "es"
}
```

**Response (422):**
```json
{
  "status": "error",
  "code": 422,
  "message": "Validation error",
  "errors": [
    {
      "field": "interview_id",
      "error": "Input should be a valid UUID",
      "type": "uuid_parsing"
    }
  ],
  "meta": {
    "endpoint": "/api/v1/interviews/continue",
    "method": "POST"
  }
}
```

#### 3. Interview Not Found

**Scenario:** interview_id doesn't exist in database

**Response (404):**
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

#### 4. Access Denied

**Scenario:** User tries to continue another user's interview

**Response (403):**
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

## Testing Strategy

### Unit Tests

#### 1. Test Request Validation
```python
# tests/unit/test_request_validation.py

def test_continue_interview_request_valid():
    """Test valid request passes validation"""
    request = ContinueInterviewRequest(
        interview_id="018e5f8b-1234-7890-abcd-123456789abc",
        user_response="Mi respuesta",
        language="es"
    )
    assert request.interview_id is not None
    assert request.user_response == "Mi respuesta"
    assert request.language == "es"

def test_continue_interview_request_empty_response():
    """Test empty user_response fails validation"""
    with pytest.raises(ValidationError) as exc_info:
        ContinueInterviewRequest(
            interview_id="018e5f8b-1234-7890-abcd-123456789abc",
            user_response="",
            language="es"
        )
    errors = exc_info.value.errors()
    assert any(e["loc"] == ("user_response",) for e in errors)

def test_continue_interview_request_invalid_language():
    """Test invalid language fails validation"""
    with pytest.raises(ValidationError) as exc_info:
        ContinueInterviewRequest(
            interview_id="018e5f8b-1234-7890-abcd-123456789abc",
            user_response="Mi respuesta",
            language="fr"  # Not supported
        )
    errors = exc_info.value.errors()
    assert any(e["loc"] == ("language",) for e in errors)

def test_continue_interview_request_legacy_fields_optional():
    """Test legacy fields are optional"""
    request = ContinueInterviewRequest(
        interview_id="018e5f8b-1234-7890-abcd-123456789abc",
        user_response="Mi respuesta",
        language="es"
        # session_id and conversation_history not provided
    )
    assert request.session_id is None
    assert request.conversation_history is None
```

#### 2. Test Error Handler
```python
# tests/unit/test_error_handlers.py

async def test_validation_error_handler_format():
    """Test RequestValidationError returns ProssX format"""
    # Create mock request
    request = Mock(spec=Request)
    request.url.path = "/api/v1/interviews/continue"
    request.method = "POST"
    
    # Create validation error
    exc = RequestValidationError([
        {
            "loc": ("body", "user_response"),
            "msg": "String should have at least 1 character",
            "type": "string_too_short"
        }
    ])
    
    # Call handler
    response = await validation_exception_handler(request, exc)
    
    # Assert format
    assert response.status_code == 422
    content = json.loads(response.body)
    assert content["status"] == "error"
    assert content["code"] == 422
    assert content["message"] == "Validation error"
    assert len(content["errors"]) == 1
    assert content["errors"][0]["field"] == "user_response"
```

### Integration Tests

#### 1. Test Continue Interview Without History
```python
# tests/integration/test_continue_interview.py

async def test_continue_interview_without_history(client, db_session, auth_token):
    """Test /continue works without conversation_history in request"""
    # Setup: Create interview with messages in DB
    interview = await create_test_interview(db_session)
    await create_test_messages(db_session, interview.id_interview, count=4)
    
    # Request without conversation_history
    response = await client.post(
        "/api/v1/interviews/continue",
        json={
            "interview_id": str(interview.id_interview),
            "user_response": "Gestiono el proceso de compras",
            "language": "es"
        },
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    # Assert success
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "question" in data["data"]
    assert data["data"]["question_number"] == 3  # Next question number
    
    # Verify messages were saved to DB
    messages = await get_interview_messages(db_session, interview.id_interview)
    assert len(messages) == 6  # 4 existing + 1 user + 1 assistant

async def test_continue_interview_loads_history_from_db(
    client, db_session, auth_token, mock_agent
):
    """Test that backend loads conversation history from database"""
    # Setup: Create interview with specific messages
    interview = await create_test_interview(db_session)
    msg1 = await create_message(db_session, interview.id_interview, 
                                 role="assistant", content="Question 1", seq=1)
    msg2 = await create_message(db_session, interview.id_interview,
                                 role="user", content="Answer 1", seq=2)
    
    # Mock agent to capture what history it receives
    captured_history = None
    def capture_history(*args, **kwargs):
        nonlocal captured_history
        captured_history = kwargs.get("conversation_history")
        return Mock(question="Next question", question_number=2, is_final=False)
    
    mock_agent.continue_interview = capture_history
    
    # Make request
    response = await client.post(
        "/api/v1/interviews/continue",
        json={
            "interview_id": str(interview.id_interview),
            "user_response": "Answer 2",
            "language": "es"
        },
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    # Assert agent received history from DB (not from request)
    assert captured_history is not None
    assert len(captured_history) == 2
    assert captured_history[0].content == "Question 1"
    assert captured_history[1].content == "Answer 1"
```

#### 2. Test Validation Error Response Format
```python
async def test_validation_error_returns_prossx_format(client, auth_token):
    """Test validation errors return ProssX standard format"""
    response = await client.post(
        "/api/v1/interviews/continue",
        json={
            "interview_id": "018e5f8b-1234-7890-abcd-123456789abc",
            "user_response": "",  # Empty (invalid)
            "language": "fr"      # Invalid language
        },
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 422
    data = response.json()
    
    # Assert ProssX format
    assert data["status"] == "error"
    assert data["code"] == 422
    assert data["message"] == "Validation error"
    assert "errors" in data
    assert isinstance(data["errors"], list)
    assert len(data["errors"]) == 2  # Two validation errors
    
    # Check error structure
    for error in data["errors"]:
        assert "field" in error
        assert "error" in error
        assert "type" in error
```

### Manual Testing Checklist

- [ ] Test /continue with minimal request (interview_id + user_response + language)
- [ ] Test /continue with legacy fields (should still work)
- [ ] Test /continue without conversation_history (should load from DB)
- [ ] Test validation error for empty user_response
- [ ] Test validation error for invalid language
- [ ] Test validation error for invalid UUID format
- [ ] Test 404 error for non-existent interview
- [ ] Test 403 error for unauthorized access
- [ ] Verify error responses match ProssX format
- [ ] Verify request size reduction (check network tab)
- [ ] Test with Postman/curl to verify API contract

## Implementation Notes

### Phase 1: Error Handling (Low Risk)
1. Add RequestValidationError handler to main.py
2. Test with invalid requests
3. Verify error format matches ProssX standard
4. Deploy and monitor

### Phase 2: API Optimization (Medium Risk)
1. Update ContinueInterviewRequest model (make fields optional)
2. Update /continue endpoint to load history from DB
3. Add backward compatibility tests
4. Deploy with feature flag (if needed)
5. Monitor performance metrics

### Phase 3: Documentation (No Risk)
1. Generate README for frontend team
2. Document API changes
3. Provide migration examples
4. Share with frontend team

### Rollback Plan

If issues arise:
1. **Error Handling**: Remove RequestValidationError handler (revert to FastAPI default)
2. **API Changes**: Revert ContinueInterviewRequest to require conversation_history
3. **Database**: No rollback needed (no schema changes)

### Performance Metrics to Monitor

- Request payload size (should drop from ~50KB to ~200B)
- Response time for /continue (should improve slightly)
- Database query count (should stay the same)
- Error rate (should not increase)
- Memory usage (should decrease slightly)

## Security Considerations

### No New Security Risks

- ✅ Authentication still required (JWT token)
- ✅ Authorization still enforced (employee_id validation)
- ✅ Input validation improved (Pydantic constraints)
- ✅ SQL injection prevented (SQLAlchemy ORM)
- ✅ No sensitive data in error messages

### Improved Security

- ✅ Smaller request payloads = less attack surface
- ✅ Better validation = fewer edge cases
- ✅ Consistent error handling = no information leakage

## Migration Guide for Frontend

### Summary of Changes

**What Changed:**
- `/continue` endpoint now accepts minimal request (interview_id + user_response + language)
- `conversation_history` field is now optional (backend loads from database)
- `session_id` field is now optional (deprecated)

**What Stayed the Same:**
- Response format unchanged
- Authentication unchanged
- All other endpoints unchanged

### Before (Old Code)
```javascript
// Frontend sends full history every time
const response = await continueInterview({
  session_id: sessionId,
  interview_id: interviewId,
  user_response: userAnswer,
  conversation_history: conversationHistory,  // 50KB+
  language: 'es'
});
```

### After (New Code)
```javascript
// Frontend sends only essential data
const response = await continueInterview({
  interview_id: interviewId,  // Required
  user_response: userAnswer,  // Required
  language: 'es'              // Required
  // conversation_history removed (backend loads from DB)
  // session_id removed (deprecated)
});
```

### Migration Steps

1. **Update API calls** - Remove `conversation_history` and `session_id` from requests
2. **Remove localStorage** (optional) - No longer needed, backend persists everything
3. **Handle errors** - Update error handling to match new format (422 for validation)
4. **Test thoroughly** - Verify interviews work end-to-end

### Backward Compatibility

The backend will accept requests with legacy fields for a transition period:
- If `conversation_history` is sent, it will be ignored
- If `session_id` is sent, it will be ignored

This allows gradual migration without breaking existing deployments.
