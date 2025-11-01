# Quick Reference - API v1.1.0

## 🚀 TL;DR - What Changed

The `/continue` endpoint now requires **only 3 fields** instead of sending the full conversation history:

```javascript
// ✅ NEW (v1.1.0) - Recommended
{
  "interview_id": "uuid",
  "user_response": "answer",
  "language": "es"
}

// ❌ OLD (v1.0.0) - Still works but unnecessary
{
  "interview_id": "uuid",
  "user_response": "answer",
  "language": "es",
  "session_id": "uuid",              // ⚠️ IGNORED
  "conversation_history": [...]      // ⚠️ IGNORED (50KB+)
}
```

**Result:** 99% smaller requests (50KB → 200 bytes)

---

## 📋 Quick Migration Checklist

### Frontend Changes

- [ ] Remove `conversation_history` from `/continue` requests
- [ ] Remove `session_id` from `/continue` requests
- [ ] Update error handling for 422 validation errors
- [ ] (Optional) Remove localStorage conversation history
- [ ] Test with minimal payload
- [ ] Verify request size in network tab

### Code Changes

**Before:**
```javascript
await continueInterview({
  session_id: sessionId,
  interview_id: interviewId,
  user_response: userAnswer,
  conversation_history: conversationHistory,
  language: 'es'
});
```

**After:**
```javascript
await continueInterview({
  interview_id: interviewId,
  user_response: userAnswer,
  language: 'es'
});
```

---

## 🔴 Breaking Changes

### None! (Backward Compatible)

All v1.0.0 requests still work. The backend accepts but ignores:
- `session_id` field
- `conversation_history` field

You can migrate gradually without breaking existing code.

---

## ✅ Required Fields

| Field | Type | Validation | Example |
|-------|------|------------|---------|
| `interview_id` | string (UUID) | Valid UUID format | `"018e5f8b-1234-7890-abcd-123456789abc"` |
| `user_response` | string | 1-5000 characters | `"Soy responsable del proceso de compras"` |
| `language` | string | "es" \| "en" \| "pt" | `"es"` |

---

## ❌ Common Validation Errors (422)

### Empty Response
```json
{
  "status": "error",
  "code": 422,
  "errors": [
    {
      "field": "user_response",
      "error": "String should have at least 1 character"
    }
  ]
}
```

### Invalid Language
```json
{
  "status": "error",
  "code": 422,
  "errors": [
    {
      "field": "language",
      "error": "String should match pattern '^(es|en|pt)$'"
    }
  ]
}
```

### Invalid UUID
```json
{
  "status": "error",
  "code": 422,
  "errors": [
    {
      "field": "interview_id",
      "error": "Input should be a valid UUID"
    }
  ]
}
```

---

## 🔧 Error Handling Update

**Before (v1.0.0):**
```javascript
if (error.status === 422) {
  const errors = error.detail; // FastAPI default format
  errors.forEach(err => {
    console.log(`${err.loc.join('.')}: ${err.msg}`);
  });
}
```

**After (v1.1.0):**
```javascript
if (error.status === 422) {
  const errors = error.errors; // ProssX standard format
  errors.forEach(err => {
    console.log(`${err.field}: ${err.error}`);
  });
}
```

---

## 📊 Performance Comparison

| Metric | v1.0.0 | v1.1.0 | Improvement |
|--------|--------|--------|-------------|
| Request Size | ~50KB | ~200B | **99% ↓** |
| Fields Sent | 5 | 3 | **40% ↓** |
| Network Time | High | Low | **Faster** |
| Frontend Memory | High | Low | **Lower** |

---

## 🧪 Testing Commands

### Test Minimal Request (cURL)
```bash
curl -X POST http://localhost:8002/api/v1/interviews/continue \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "interview_id": "018e5f8b-1234-7890-abcd-123456789abc",
    "user_response": "Soy gerente de compras",
    "language": "es"
  }'
```

### Test Validation Error
```bash
curl -X POST http://localhost:8002/api/v1/interviews/continue \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "interview_id": "018e5f8b-1234-7890-abcd-123456789abc",
    "user_response": "",
    "language": "es"
  }'
```

---

## 📚 Documentation Links

- **Full API Changes:** `/docs/API_CHANGES_v1.1.0.md`
- **Swagger UI:** http://localhost:8002/docs
- **ReDoc:** http://localhost:8002/redoc

---

## 💡 Tips

1. **Remove localStorage:** Backend persists everything, no need to store history
2. **Check Network Tab:** Verify request size dropped from 50KB to 200 bytes
3. **Gradual Migration:** Old requests still work, migrate at your own pace
4. **Error Handling:** Update to use `error.errors` instead of `error.detail`

---

## ❓ FAQ

**Q: Do I need to update my code immediately?**  
A: No, backward compatible. Old requests still work.

**Q: What happens to conversation_history if I send it?**  
A: It's ignored. Backend loads from database.

**Q: Can I still use session_id?**  
A: Yes, but it's ignored. Use interview_id instead.

**Q: Will my old code break?**  
A: No, all v1.0.0 requests still work.

**Q: How do I get the conversation history?**  
A: Use `GET /api/v1/interviews/{interview_id}` endpoint.

---

**Version:** 1.0  
**Last Updated:** 2025-11-01  
**API Version:** 1.1.0
