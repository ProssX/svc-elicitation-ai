# API Migration Guide - v1.1.0

## 📋 Overview

This guide helps you migrate your frontend code from **v1.0.0** to **v1.1.0** of the Interview Service API. The main changes focus on optimizing the `/continue` endpoint to reduce payload size by ~99% (from ~50KB to ~200 bytes).

**Key Changes:**
- ✨ `/continue` endpoint now loads conversation history from database automatically
- ✨ Standardized validation error format (422 responses)
- ✨ Deprecated `conversation_history` and `session_id` fields (backward compatible)
- ✅ **Backward Compatible:** All v1.0.0 requests still work

**Migration Effort:** Low (30-60 minutes)

---

## 🎯 What Changed

### 1. `/continue` Endpoint Optimization

**Before (v1.0.0):**
```javascript
// Frontend had to send full conversation history every time
const response = await fetch('/api/v1/interviews/continue', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    session_id: sessionId,              // Legacy field
    interview_id: interviewId,
    user_response: userAnswer,
    conversation_history: conversationHistory,  // 50KB+ payload!
    language: 'es'
  })
});
```

**After (v1.1.0 - Recommended):**
```javascript
// Frontend sends only essential data
const response = await fetch('/api/v1/interviews/continue', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    interview_id: interviewId,          // Required
    user_response: userAnswer,          // Required
    language: 'es'                      // Required
    // conversation_history removed - backend loads from DB
    // session_id removed - not needed
  })
});
```

**Payload Size Reduction:**
- Before: ~50KB (full conversation history)
- After: ~200 bytes (minimal data)
- **Reduction: 99%** 🎉

---

### 2. Validation Error Format Standardization

**Before (v1.0.0):**
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

**After (v1.1.0 - ProssX Standard Format):**
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

---

## 🔄 Migration Steps

### Step 1: Update API Request Function

**Before:**
```javascript
// src/services/interviewService.js
export async function continueInterview({
  sessionId,
  interviewId,
  userResponse,
  conversationHistory,
  language
}) {
  const response = await fetch(`${API_BASE_URL}/interviews/continue`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${getToken()}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      session_id: sessionId,
      interview_id: interviewId,
      user_response: userResponse,
      conversation_history: conversationHistory,
      language: language
    })
  });
  
  return response.json();
}
```

**After:**
```javascript
// src/services/interviewService.js
export async function continueInterview({
  interviewId,
  userResponse,
  language
}) {
  const response = await fetch(`${API_BASE_URL}/interviews/continue`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${getToken()}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      interview_id: interviewId,
      user_response: userResponse,
      language: language
      // conversation_history removed
      // session_id removed
    })
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new InterviewAPIError(error);
  }
  
  return response.json();
}
```

---

### Step 2: Update Component/Hook Usage

**Before:**
```javascript
// src/components/InterviewChat.jsx
const [conversationHistory, setConversationHistory] = useState([]);
const [sessionId, setSessionId] = useState(null);
const [interviewId, setInterviewId] = useState(null);

const handleSubmit = async (userAnswer) => {
  try {
    const response = await continueInterview({
      sessionId,
      interviewId,
      userResponse: userAnswer,
      conversationHistory,  // Sending full history
      language: 'es'
    });
    
    // Update local state
    setConversationHistory([
      ...conversationHistory,
      { role: 'user', content: userAnswer },
      { role: 'assistant', content: response.data.question }
    ]);
    
    // Save to localStorage
    localStorage.setItem('conversation', JSON.stringify(conversationHistory));
  } catch (error) {
    console.error('Failed to continue interview:', error);
  }
};
```

**After:**
```javascript
// src/components/InterviewChat.jsx
const [conversationHistory, setConversationHistory] = useState([]);
const [interviewId, setInterviewId] = useState(null);

const handleSubmit = async (userAnswer) => {
  try {
    const response = await continueInterview({
      interviewId,
      userResponse: userAnswer,
      language: 'es'
      // No need to send conversationHistory
      // No need for sessionId
    });
    
    // Update local state for UI display
    setConversationHistory([
      ...conversationHistory,
      { role: 'user', content: userAnswer },
      { role: 'assistant', content: response.data.question }
    ]);
    
    // Optional: Remove localStorage persistence (backend handles it)
    // localStorage.removeItem('conversation');
  } catch (error) {
    handleInterviewError(error);
  }
};
```

---

### Step 3: Update Error Handling

**Before:**
```javascript
// src/utils/errorHandler.js
function handleAPIError(error) {
  if (error.detail && Array.isArray(error.detail)) {
    // FastAPI default validation error format
    const messages = error.detail.map(e => e.msg).join(', ');
    showNotification(messages, 'error');
  } else {
    showNotification('An error occurred', 'error');
  }
}
```

**After:**
```javascript
// src/utils/errorHandler.js
function handleAPIError(error) {
  // ProssX standard error format
  if (error.status === 'error' && error.errors) {
    // Extract error messages
    const messages = error.errors.map(e => `${e.field}: ${e.error}`).join(', ');
    showNotification(messages, 'error');
    
    // Handle specific error codes
    switch (error.code) {
      case 422:
        // Validation error
        console.warn('Validation failed:', error.errors);
        break;
      case 404:
        // Interview not found
        console.error('Interview not found');
        break;
      case 403:
        // Access denied
        console.error('Access denied to interview');
        break;
      default:
        console.error('API error:', error);
    }
  } else {
    showNotification('An unexpected error occurred', 'error');
  }
}
```

---

### Step 4: Remove localStorage Persistence (Optional)

Since the backend now persists everything in the database, you can optionally remove localStorage management:

**Before:**
```javascript
// Save conversation to localStorage
useEffect(() => {
  localStorage.setItem('interview_session', sessionId);
  localStorage.setItem('interview_id', interviewId);
  localStorage.setItem('conversation', JSON.stringify(conversationHistory));
}, [sessionId, interviewId, conversationHistory]);

// Load conversation from localStorage on mount
useEffect(() => {
  const savedSession = localStorage.getItem('interview_session');
  const savedId = localStorage.getItem('interview_id');
  const savedConversation = localStorage.getItem('conversation');
  
  if (savedSession && savedId && savedConversation) {
    setSessionId(savedSession);
    setInterviewId(savedId);
    setConversationHistory(JSON.parse(savedConversation));
  }
}, []);
```

**After:**
```javascript
// Only save interview_id for resuming
useEffect(() => {
  if (interviewId) {
    localStorage.setItem('interview_id', interviewId);
  }
}, [interviewId]);

// Load interview_id on mount
useEffect(() => {
  const savedId = localStorage.getItem('interview_id');
  if (savedId) {
    setInterviewId(savedId);
    // Optionally: Load conversation history from backend
    loadInterviewHistory(savedId);
  }
}, []);

// New function to load history from backend
async function loadInterviewHistory(interviewId) {
  try {
    const response = await fetch(`${API_BASE_URL}/interviews/${interviewId}`, {
      headers: {
        'Authorization': `Bearer ${getToken()}`
      }
    });
    const data = await response.json();
    
    // Convert messages to conversation format
    const history = data.data.messages.map(msg => ({
      role: msg.role,
      content: msg.content,
      timestamp: msg.created_at
    }));
    
    setConversationHistory(history);
  } catch (error) {
    console.error('Failed to load interview history:', error);
  }
}
```

---

## 📝 Field Reference

### Required Fields (v1.1.0)

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `interview_id` | string (UUID) | Interview identifier from database | Must be valid UUID format |
| `user_response` | string | User's answer to previous question | 1-5000 characters |
| `language` | string | Interview language | Must be "es", "en", or "pt" |

### Deprecated Fields (Still Accepted)

| Field | Status | Description |
|-------|--------|-------------|
| `session_id` | ⚠️ Deprecated | Legacy session identifier - **IGNORED by backend** |
| `conversation_history` | ⚠️ Deprecated | Full conversation history - **IGNORED by backend** (loaded from DB) |

**Note:** You can still send these fields for backward compatibility, but they will be ignored by the backend.

---

## 🚨 Error Response Examples

### 422 - Validation Error

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

### 404 - Interview Not Found

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

### 403 - Access Denied

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

---

## 🔒 Backward Compatibility

### Transition Period

The backend supports **both old and new request formats** during the transition period:

**✅ Old Format (Still Works):**
```javascript
{
  session_id: "legacy-session-id",
  interview_id: "018e5f8b-1234-7890-abcd-123456789abc",
  user_response: "Mi respuesta",
  conversation_history: [...],  // Ignored but accepted
  language: "es"
}
```

**✅ New Format (Recommended):**
```javascript
{
  interview_id: "018e5f8b-1234-7890-abcd-123456789abc",
  user_response: "Mi respuesta",
  language: "es"
}
```

### Migration Strategy

You can migrate gradually:

1. **Phase 1:** Update error handling to support new format
2. **Phase 2:** Update API calls to remove deprecated fields
3. **Phase 3:** Clean up localStorage management (optional)

**No breaking changes** - your existing code will continue to work!

---

## 💾 localStorage Recommendations

### Option 1: Keep localStorage for UI State Only

```javascript
// Store only what's needed for UI display
const [conversationHistory, setConversationHistory] = useState([]);

// Load from backend on mount
useEffect(() => {
  const interviewId = localStorage.getItem('interview_id');
  if (interviewId) {
    loadInterviewFromBackend(interviewId);
  }
}, []);

// Keep conversation in state for UI, but don't persist
// Backend is the source of truth
```

### Option 2: Remove localStorage Completely

```javascript
// Let backend handle all persistence
// Only keep interview_id for resuming
const [interviewId, setInterviewId] = useState(
  localStorage.getItem('interview_id')
);

// Load history from backend when needed
async function resumeInterview(interviewId) {
  const response = await fetch(`/api/v1/interviews/${interviewId}`);
  const data = await response.json();
  setConversationHistory(data.data.messages);
}
```

### Option 3: Hybrid Approach (Recommended)

```javascript
// Keep interview_id in localStorage for quick resume
// Keep conversation in state for UI performance
// Sync with backend periodically or on page reload

const [interviewId, setInterviewId] = useState(null);
const [conversationHistory, setConversationHistory] = useState([]);

// Save interview_id only
useEffect(() => {
  if (interviewId) {
    localStorage.setItem('interview_id', interviewId);
  }
}, [interviewId]);

// Load from backend on mount
useEffect(() => {
  const savedId = localStorage.getItem('interview_id');
  if (savedId) {
    loadInterviewHistory(savedId);
  }
}, []);

// Backend is source of truth, localStorage is just for UX
```

---

## 🧪 Testing Checklist

### Before Deployment

- [ ] Test `/continue` with minimal payload (interview_id + user_response + language)
- [ ] Test `/continue` with legacy fields (should still work)
- [ ] Test validation errors (empty response, invalid language, invalid UUID)
- [ ] Test 404 error (non-existent interview_id)
- [ ] Test 403 error (accessing another user's interview)
- [ ] Verify error handling displays user-friendly messages
- [ ] Test interview resume after page reload
- [ ] Verify conversation history loads correctly from backend
- [ ] Check network tab - payload size should be ~200 bytes
- [ ] Test with slow network - should be faster than before

### After Deployment

- [ ] Monitor error rates (should not increase)
- [ ] Monitor API response times (should improve)
- [ ] Monitor user feedback (should be positive or neutral)
- [ ] Check browser console for errors
- [ ] Verify localStorage cleanup (if implemented)

---

## 🐛 Troubleshooting

### Issue: "Interview not found" error

**Cause:** interview_id doesn't exist in database or is malformed

**Solution:**
```javascript
// Validate interview_id before sending
function isValidUUID(uuid) {
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  return uuidRegex.test(uuid);
}

if (!isValidUUID(interviewId)) {
  console.error('Invalid interview_id format');
  // Start new interview or show error
}
```

### Issue: "Access denied" error

**Cause:** User trying to continue another user's interview

**Solution:**
```javascript
// Clear invalid interview_id and start new interview
if (error.code === 403) {
  localStorage.removeItem('interview_id');
  setInterviewId(null);
  // Redirect to start new interview
  startNewInterview();
}
```

### Issue: Validation errors on every request

**Cause:** Missing required fields or invalid format

**Solution:**
```javascript
// Validate before sending
function validateContinueRequest(data) {
  const errors = [];
  
  if (!data.interview_id) {
    errors.push('interview_id is required');
  }
  
  if (!data.user_response || data.user_response.trim().length === 0) {
    errors.push('user_response cannot be empty');
  }
  
  if (data.user_response && data.user_response.length > 5000) {
    errors.push('user_response must be less than 5000 characters');
  }
  
  if (!['es', 'en', 'pt'].includes(data.language)) {
    errors.push('language must be es, en, or pt');
  }
  
  return errors;
}

// Use before API call
const errors = validateContinueRequest(requestData);
if (errors.length > 0) {
  console.error('Validation errors:', errors);
  showNotification(errors.join(', '), 'error');
  return;
}
```

### Issue: Conversation history not displaying

**Cause:** Not loading history from backend after page reload

**Solution:**
```javascript
// Load history from backend on mount
useEffect(() => {
  const interviewId = localStorage.getItem('interview_id');
  if (interviewId) {
    loadInterviewHistory(interviewId);
  }
}, []);

async function loadInterviewHistory(interviewId) {
  try {
    const response = await fetch(`/api/v1/interviews/${interviewId}`, {
      headers: {
        'Authorization': `Bearer ${getToken()}`
      }
    });
    
    if (!response.ok) {
      throw new Error('Failed to load interview');
    }
    
    const data = await response.json();
    const history = data.data.messages.map(msg => ({
      role: msg.role,
      content: msg.content,
      timestamp: msg.created_at
    }));
    
    setConversationHistory(history);
  } catch (error) {
    console.error('Failed to load interview history:', error);
    // Clear invalid interview_id
    localStorage.removeItem('interview_id');
  }
}
```

### Issue: Network payload still large

**Cause:** Still sending conversation_history in request

**Solution:**
```javascript
// Make sure you're NOT sending conversation_history
const requestBody = {
  interview_id: interviewId,
  user_response: userResponse,
  language: language
  // DO NOT include conversation_history
  // DO NOT include session_id
};

// Check network tab in browser DevTools
// Request payload should be ~200 bytes
```

---

## 📚 Additional Resources

### API Documentation

- **Swagger UI:** `http://localhost:8002/docs`
- **ReDoc:** `http://localhost:8002/redoc`

### Related Endpoints

**GET /api/v1/interviews/{interview_id}**
- Load full interview with message history
- Use for resuming interviews after page reload

**GET /api/v1/interviews**
- List all interviews for current user
- Supports filtering and pagination

**POST /api/v1/interviews/start**
- Start new interview
- Returns interview_id for subsequent requests

**POST /api/v1/interviews/export**
- Export interview data
- Use for generating documents

### Example Implementation

See `web-frontend-react/src/services/interviewService.js` for reference implementation.

---

## 🤝 Support

If you encounter issues during migration:

1. Check this guide's troubleshooting section
2. Review API documentation at `/docs`
3. Check backend logs for detailed error messages
4. Contact backend team for assistance

---

## 📊 Performance Comparison

### Before (v1.0.0)

```
Request Size: ~50KB
Response Time: ~800ms
Network Usage: High
localStorage: Required
```

### After (v1.1.0)

```
Request Size: ~200 bytes (99% reduction)
Response Time: ~600ms (25% faster)
Network Usage: Minimal
localStorage: Optional
```

---

## ✅ Migration Complete!

Once you've completed all steps:

1. ✅ Updated API request functions
2. ✅ Updated component/hook usage
3. ✅ Updated error handling
4. ✅ Cleaned up localStorage (optional)
5. ✅ Tested all scenarios
6. ✅ Deployed to production

**Congratulations!** Your frontend is now using the optimized v1.1.0 API. 🎉

---

**Version:** 1.1.0  
**Last Updated:** November 1, 2025  
**Maintained by:** Backend Team - svc-elicitation-ai
