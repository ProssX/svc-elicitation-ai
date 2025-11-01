# API Changes - Version 1.1.0

## Overview

This document describes the API changes introduced in version 1.1.0 of the Elicitation AI Service. The primary focus is on optimizing the `/continue` endpoint to reduce payload size and improve performance.

## Summary of Changes

### 🎯 Main Optimization: `/continue` Endpoint

**What Changed:**
- The `/continue` endpoint now loads conversation history from the database automatically
- Request payload reduced by ~99% (from ~50KB to ~200 bytes)
- `conversation_history` field is now **optional** and **ignored** by the backend
- `session_id` field is now **optional** and **ignored** by the backend

**What Stayed the Same:**
- Response format unchanged
- Authentication unchanged
- All other endpoints unchanged
- Backward compatible with legacy requests

---

## Detailed Changes

### 1. `/continue` Endpoint - Request Model Changes

#### Before (v1.0.0)
```json
{
  "interview_id": "018e5f8b-1234-7890-abcd-123456789abc",
  "session_id": "legacy-session-id",
  "user_response": "Soy responsable del proceso de compras",
  "conversation_history": [
    {
      "role": "assistant",
      "content": "¿Cuál es tu rol?",
      "timestamp": "2025-10-25T10:00:00Z"
    },
    {
      "role": "user",
      "content": "Soy gerente",
      "timestamp": "2025-10-25T10:01:00Z"
    }
    // ... potentially 50+ messages (~50KB)
  ],
  "language": "es"
}
```

#### After (v1.1.0) - Recommended
```json
{
  "interview_id": "018e5f8b-1234-7890-abcd-123456789abc",
  "user_response": "Soy responsable del proceso de compras",
  "language": "es"
}
```

**Size Comparison:**
- Before: ~50KB (with full conversation history)
- After: ~200 bytes (minimal payload)
- **Reduction: 99%**

---

### 2. Request Fields

#### Required Fields
| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `interview_id` | string (UUID) | Interview identifier from database | Must be valid UUID format |
| `user_response` | string | User's answer to previous question | 1-5000 characters |
| `language` | string | Interview language | Must be "es", "en", or "pt" |

#### Optional Fields (Deprecated)
| Field | Type | Status | Notes |
|-------|------|--------|-------|
| `session_id` | string | ⚠️ DEPRECATED | Ignored by backend, kept for backward compatibility |
| `conversation_history` | array | ⚠️ DEPRECATED | Ignored by backend (loaded from DB), kept for backward compatibility |

---

### 3. Response Format (Unchanged)

The response format remains the same:

```json
{
  "status": "success",
  "code": 200,
  "message": "Question generated successfully",
  "data": {
    "question": "¿Qué procesos gestionas en tu área?",
    "question_number": 3,
    "is_final": false,
    "corrected_response": "Soy responsable del proceso de compras"
  },
  "errors": null,
  "meta": {
    "interview_id": "018e5f8b-1234-7890-abcd-123456789abc",
    "session_id": null,
    "question_count": 3,
    "language": "es"
  }
}
```

---

### 4. Error Responses - New Format (422 Validation Errors)

#### New ProssX Standard Format

All validation errors now follow the ProssX standard format:

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

#### Common Validation Errors

**Empty user_response:**
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

**Invalid language:**
```json
{
  "status": "error",
  "code": 422,
  "message": "Validation error",
  "errors": [
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

**Invalid UUID format:**
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

**Multiple validation errors:**
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

---

### 5. Other Error Responses (Unchanged)

**404 Not Found:**
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

**403 Forbidden:**
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

**401 Unauthorized:**
```json
{
  "status": "error",
  "code": 401,
  "message": "Authentication required",
  "errors": [
    {
      "field": "authorization",
      "error": "Missing or invalid authorization header"
    }
  ]
}
```

---

## How It Works

### Backend Flow (v1.1.0)

```
1. Frontend sends minimal request:
   {
     "interview_id": "...",
     "user_response": "...",
     "language": "es"
   }

2. Backend receives request (200 bytes)

3. Backend loads interview from PostgreSQL:
   - SELECT * FROM interview WHERE id_interview = ?
   
4. Backend loads full message history from PostgreSQL:
   - SELECT * FROM interview_message 
     WHERE interview_id = ? 
     ORDER BY sequence_number

5. Backend converts DB messages to conversation format

6. Backend passes history to AI agent

7. AI agent generates next question

8. Backend saves user response to DB

9. Backend saves agent question to DB

10. Backend returns only the next question to frontend
```

### Database Persistence

All conversation data is automatically persisted:
- ✅ User responses saved to `interview_message` table
- ✅ Agent questions saved to `interview_message` table
- ✅ Interview `updated_at` timestamp updated
- ✅ Interview `status` updated when `is_final=true`
- ✅ Interview `completed_at` set when marked as completed

---

## Backward Compatibility

### Legacy Requests Still Work

The backend accepts legacy requests with `session_id` and `conversation_history` fields:

```json
{
  "interview_id": "018e5f8b-1234-7890-abcd-123456789abc",
  "user_response": "Soy responsable del proceso de compras",
  "language": "es",
  "session_id": "legacy-session-id",        // ⚠️ IGNORED
  "conversation_history": [...]             // ⚠️ IGNORED
}
```

**Important Notes:**
- These fields are **ignored** by the backend
- No error is thrown if they are present
- This allows gradual migration without breaking existing deployments
- Frontend can remove these fields at their convenience

---

## Migration Guide for Frontend

### Step 1: Update API Call

**Before:**
```javascript
const response = await continueInterview({
  session_id: sessionId,
  interview_id: interviewId,
  user_response: userAnswer,
  conversation_history: conversationHistory,  // 50KB+ payload
  language: 'es'
});
```

**After:**
```javascript
const response = await continueInterview({
  interview_id: interviewId,
  user_response: userAnswer,
  language: 'es'
  // conversation_history removed - backend loads from DB
  // session_id removed - not needed
});
```

### Step 2: Remove localStorage (Optional)

Since the backend now persists everything, you can optionally remove localStorage:

**Before:**
```javascript
// Save to localStorage after each response
localStorage.setItem('interview_history', JSON.stringify(conversationHistory));
localStorage.setItem('session_id', sessionId);
```

**After:**
```javascript
// No need to save history - backend persists everything
// Only save interview_id for the current session
sessionStorage.setItem('interview_id', interviewId);
```

### Step 3: Update Error Handling

Update error handling to match the new 422 validation error format:

**Before:**
```javascript
if (error.status === 422) {
  // FastAPI default format
  const errors = error.detail; // Array of validation errors
  errors.forEach(err => {
    console.log(`Field: ${err.loc.join('.')}, Error: ${err.msg}`);
  });
}
```

**After:**
```javascript
if (error.status === 422) {
  // ProssX standard format
  const errors = error.errors; // Array of {field, error, type}
  errors.forEach(err => {
    console.log(`Field: ${err.field}, Error: ${err.error}`);
  });
}
```

### Step 4: Test Thoroughly

- ✅ Test starting a new interview
- ✅ Test continuing an interview with minimal payload
- ✅ Test validation errors (empty response, invalid language)
- ✅ Test error handling (404, 403, 401)
- ✅ Verify request size reduction in network tab

---

## OpenAPI/Swagger Documentation

The OpenAPI schema has been updated to reflect these changes:

### Access Documentation

- **Swagger UI:** http://localhost:8002/docs
- **ReDoc:** http://localhost:8002/redoc

### Key Updates

1. **Request Schema:**
   - `conversation_history` marked as optional (deprecated)
   - `session_id` marked as optional (deprecated)
   - Minimal request example shown by default

2. **Response Schema:**
   - 422 validation error response added
   - ProssX standard error format documented
   - Multiple error examples provided

3. **Endpoint Description:**
   - Clear indication of deprecated fields
   - Migration guide included
   - Backward compatibility notes

---

## Performance Improvements

### Metrics

| Metric | Before (v1.0.0) | After (v1.1.0) | Improvement |
|--------|-----------------|----------------|-------------|
| Request Size | ~50KB | ~200 bytes | 99% reduction |
| Network Transfer | High | Minimal | Significant |
| Frontend Memory | High (stores history) | Low (only interview_id) | Significant |
| Backend Processing | Minimal | Minimal (DB query) | Unchanged |

### Benefits

- ✅ Faster request transmission (especially on slow networks)
- ✅ Reduced frontend memory usage
- ✅ Simplified frontend code (no history management)
- ✅ Single source of truth (PostgreSQL database)
- ✅ Better scalability (no large payloads)

---

## Testing Checklist

### Backend Testing (Already Complete)

- ✅ Unit tests for request validation
- ✅ Unit tests for error handler
- ✅ Integration tests for /continue endpoint
- ✅ Integration tests for database loading
- ✅ Integration tests for backward compatibility

### Frontend Testing (Recommended)

- [ ] Test /continue with minimal request
- [ ] Test /continue with legacy fields (backward compatibility)
- [ ] Test validation error handling (422)
- [ ] Test empty user_response error
- [ ] Test invalid language error
- [ ] Test invalid UUID error
- [ ] Test 404 error (interview not found)
- [ ] Test 403 error (access denied)
- [ ] Verify request size in network tab
- [ ] Test localStorage removal (if applicable)

---

## Support and Questions

For questions or issues related to these API changes:

1. **Check OpenAPI Documentation:** http://localhost:8002/docs
2. **Review Migration Guide:** See "Migration Guide for Frontend" section above
3. **Check Error Responses:** See "Error Responses" section above
4. **Contact Backend Team:** For technical support

---

## Version History

### v1.1.0 (Current)
- ✨ Optimized /continue endpoint (99% payload reduction)
- ✨ Added standardized 422 validation error format
- ✨ Deprecated conversation_history and session_id fields
- ✨ Added comprehensive API documentation
- ✅ Backward compatible with v1.0.0

### v1.0.0
- Initial release
- Basic interview functionality
- Required conversation_history in requests

---

## Appendix: Complete API Reference

### POST /api/v1/interviews/continue

**Endpoint:** `POST /api/v1/interviews/continue`

**Authentication:** Required (Bearer token)

**Permission:** `interviews:create`

**Request Body:**
```json
{
  "interview_id": "string (UUID, required)",
  "user_response": "string (1-5000 chars, required)",
  "language": "string (es|en|pt, required)",
  "session_id": "string (optional, deprecated)",
  "conversation_history": "array (optional, deprecated)"
}
```

**Success Response (200):**
```json
{
  "status": "success",
  "code": 200,
  "message": "Question generated successfully",
  "data": {
    "question": "string",
    "question_number": "integer",
    "is_final": "boolean",
    "corrected_response": "string"
  },
  "errors": null,
  "meta": {
    "interview_id": "string",
    "session_id": "string|null",
    "question_count": "integer",
    "language": "string"
  }
}
```

**Error Responses:**
- `422` - Validation error (ProssX standard format)
- `404` - Interview not found
- `403` - Access denied
- `401` - Authentication required
- `500` - Internal server error

---

**Document Version:** 1.0  
**Last Updated:** 2025-11-01  
**API Version:** 1.1.0
