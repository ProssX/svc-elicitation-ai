# Context-Aware Interviews API Documentation

## Overview

This document describes the context-aware interview features added in version 1.2.0. These features enable the AI interview agent to conduct more intelligent interviews by leveraging employee context, organizational processes, and interview history.

**Version:** 1.2.0  
**Last Updated:** 2025-11-07

---

## Table of Contents

1. [What's New](#whats-new)
2. [Context Enrichment](#context-enrichment)
3. [Process Matching](#process-matching)
4. [API Changes](#api-changes)
5. [Response Fields](#response-fields)
6. [Configuration](#configuration)
7. [Error Handling](#error-handling)
8. [Examples](#examples)

---

## What's New

### Context Enrichment

The interview agent now has access to rich contextual information:

- **Employee Profile**: Name, roles, organization details
- **Organization Processes**: Existing processes identified in previous interviews
- **Interview History**: Summary of previous interviews by the employee
- **Smart Caching**: Context is cached for 5 minutes to improve performance

### Process Matching

The agent can now intelligently detect when an employee describes an existing process:

- **Automatic Detection**: Identifies when user mentions a process
- **Confidence Scoring**: Provides confidence level (0.0 to 1.0) for matches
- **Multi-language Support**: Works in Spanish, English, and Portuguese
- **Process References**: Tracks which processes were discussed in each interview

### Performance

- Context loading: < 2 seconds
- Process matching: < 1 second  
- Total interview start time: < 3 seconds
- Graceful degradation if backend services are unavailable

---

## API Changes

### New Response Fields

#### `/start` Endpoint

**Enhanced Response:**

```json
{
  "status": "success",
  "code": 200,
  "message": "Interview started successfully",
  "data": {
    "session_id": "01932e5f-8b2a-7890-b123-456789abcdef",
    "question": "Hola Juan, me alegra tenerte aquí...",
    "question_number": 1,
    "is_final": false
  },
  "meta": {
    "user_name": "Juan Pérez",                    // NEW
    "organization": "ProssX Demo",                 // NEW
    "language": "es",
    "context_loaded": true,                        // NEW
    "processes_available": 5                       // NEW
  }
}
```

**New Fields:**
- `meta.user_name`: Employee's full name from context
- `meta.organization`: Organization name from context
- `meta.context_loaded`: Whether context enrichment succeeded
- `meta.processes_available`: Number of existing processes loaded

---

#### `/continue` Endpoint

**Enhanced Response:**

```json
{
  "status": "success",
  "code": 200,
  "message": "Question generated successfully",
  "data": {
    "question": "¿Este proceso es el mismo que el Proceso de Aprobación de Compras que ya tenemos?",
    "question_number": 3,
    "is_final": false,
    "corrected_response": "Yo apruebo las compras mayores a $1000",
    "process_matches": [                           // NEW
      {
        "process_id": "01932e5f-proc-uuid",
        "process_name": "Proceso de Aprobación de Compras",
        "is_new": false,
        "confidence": 0.85
      }
    ]
  },
  "meta": {
    "session_id": "01932e5f-8b2a-7890-b123-456789abcdef",
    "question_count": 3,
    "language": "es",
    "process_matching_performed": true             // NEW
  }
}
```

**New Fields:**
- `data.process_matches`: Array of matched processes (empty if no matches)
- `meta.process_matching_performed`: Whether process matching was attempted

---

#### `/export` Endpoint

**Enhanced Response:**

```json
{
  "status": "success",
  "code": 200,
  "message": "Interview data exported successfully",
  "data": {
    "session_id": "01932e5f-8b2a-7890-b123-456789abcdef",
    "user_id": "01932e5f-user-uuid",
    "user_name": "Juan Pérez",
    "user_role": "Gerente de Operaciones",
    "organization": "ProssX Demo",
    "interview_date": "2025-11-07T10:30:00Z",
    "interview_duration_minutes": 15,
    "total_questions": 8,
    "total_user_responses": 8,
    "is_complete": true,
    "conversation_history": [...],
    "processes_referenced": [                      // NEW
      {
        "process_id": "01932e5f-proc-uuid",
        "process_name": "Proceso de Aprobación de Compras",
        "is_new": false,
        "confidence": 0.85
      },
      {
        "process_id": "01932e5f-proc-uuid-2",
        "process_name": "Proceso de Gestión de Inventario",
        "is_new": true,
        "confidence": 0.92
      }
    ],
    "context_used": {                              // NEW
      "employee_name": "Juan Pérez",
      "organization_name": "ProssX Demo",
      "roles": ["Gerente de Operaciones"],
      "existing_processes_count": 5,
      "interview_history": {
        "total_interviews": 2,
        "last_interview_date": "2025-10-15T14:00:00Z"
      }
    }
  },
  "meta": {
    "export_date": "2025-11-07T10:45:00Z",
    "language": "es"
  }
}
```

**New Fields:**
- `data.processes_referenced`: Array of all processes discussed (existing and new)
- `data.context_used`: Context information that was available during the interview

---

## Context Enrichment

### How It Works

When you start an interview, the system automatically:

1. **Fetches Employee Context** from `svc-organizations-php`:
   - Employee profile (name, email, status)
   - Employee roles and descriptions
   - Organization details

2. **Loads Organization Processes**:
   - Active processes in the organization
   - Process names, types, and descriptions
   - Limited to 20 most recent processes

3. **Retrieves Interview History**:
   - Count of previous interviews
   - Last interview date
   - Topics covered in past interviews

4. **Builds Enriched Prompt**:
   - Includes all context in the system prompt
   - Provides instructions for process matching
   - Personalizes the conversation

### Context Data Structure

```json
{
  "employee": {
    "id": "01932e5f-8b2a-7890-b123-456789abcdef",
    "first_name": "Juan",
    "last_name": "Pérez",
    "full_name": "Juan Pérez",
    "organization_id": "01932e5f-1234-5678-9abc-def012345678",
    "organization_name": "ProssX Demo",
    "roles": [
      {
        "id": "01932e5f-role-uuid",
        "name": "Gerente de Operaciones",
        "description": "Responsable de gestionar operaciones diarias"
      }
    ],
    "is_active": true
  },
  "organization_processes": [
    {
      "id": "01932e5f-proc-uuid",
      "name": "Proceso de Aprobación de Compras",
      "type": "operational",
      "type_label": "Operacional",
      "is_active": true,
      "created_at": "2025-10-01T10:00:00Z",
      "updated_at": "2025-10-15T14:30:00Z"
    }
  ],
  "interview_history": {
    "total_interviews": 3,
    "completed_interviews": 2,
    "last_interview_date": "2025-10-20T15:00:00Z",
    "topics_covered": ["Compras", "Aprobaciones", "Inventario"]
  },
  "context_timestamp": "2025-11-07T10:00:00Z"
}
```

### Caching Strategy

- **Cache TTL**: 5 minutes (configurable via `CONTEXT_CACHE_TTL`)
- **Cache Key**: Based on employee_id and organization_id
- **Cache Invalidation**: Automatic after TTL expires
- **Cache Hit Rate**: Logged for monitoring

---

## Process Matching

### Overview

Process matching helps the agent determine if an employee is describing an existing process or a new one. This prevents duplicate process identification and enables better follow-up questions.

### How It Works

1. **Detection**: Agent detects when user mentions a process (keywords, context)
2. **Matching**: Specialized agent compares description against existing processes
3. **Scoring**: Assigns confidence score (0.0 = no match, 1.0 = exact match)
4. **Recording**: Saves process reference in database for tracking

### Process Match Result

```json
{
  "process_id": "01932e5f-proc-uuid",
  "process_name": "Proceso de Aprobación de Compras",
  "is_new": false,
  "confidence": 0.85,
  "reasoning": "User mentioned 'aprobación de compras' which closely matches existing process name"
}
```

### Confidence Scoring

The process matching agent assigns confidence scores based on:

- **0.9 - 1.0**: Exact or near-exact match (same name, clear reference)
- **0.7 - 0.89**: Strong match (similar name, same type, clear context)
- **0.5 - 0.69**: Moderate match (related terms, similar description)
- **0.3 - 0.49**: Weak match (some overlap, needs clarification)
- **0.0 - 0.29**: No match or very weak match

**Example Scenarios:**

```json
// Exact match
{
  "is_match": true,
  "matched_process_id": "01932e5f-proc-uuid",
  "matched_process_name": "Proceso de Aprobación de Compras",
  "confidence": 0.95,
  "reasoning": "Usuario mencionó exactamente 'Proceso de Aprobación de Compras'"
}

// Strong match with variation
{
  "is_match": true,
  "matched_process_id": "01932e5f-proc-uuid",
  "matched_process_name": "Proceso de Aprobación de Compras",
  "confidence": 0.82,
  "reasoning": "Usuario describió 'aprobación de órdenes de compra' que coincide con el proceso existente"
}

// No match
{
  "is_match": false,
  "matched_process_id": null,
  "matched_process_name": null,
  "confidence": 0.15,
  "reasoning": "El proceso descrito 'gestión de inventario' no coincide con ningún proceso existente"
}
```



---

## Examples

### Example 1: Starting an Interview with Context

**Request:**
```bash
curl -X POST http://localhost:8001/api/v1/interviews/start \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{"language":"es"}'
```

**Response:**
```json
{
  "status": "success",
  "code": 200,
  "message": "Interview started successfully",
  "data": {
    "session_id": "01932e5f-8b2a-7890-b123-456789abcdef",
    "question": "Hola Juan, me alegra tenerte aquí. Veo que eres Gerente de Operaciones en ProssX Demo. Antes de comenzar, quiero mencionar que ya tenemos 5 procesos identificados en tu organización, incluyendo el Proceso de Aprobación de Compras y el Proceso de Gestión de Inventario. Si mencionas alguno de estos procesos, te preguntaré si te refieres al mismo o si es algo diferente. ¿Cuál es tu función principal en la organización?",
    "question_number": 1,
    "is_final": false
  },
  "meta": {
    "user_name": "Juan Pérez",
    "organization": "ProssX Demo",
    "language": "es",
    "context_loaded": true,
    "processes_available": 5
  }
}
```

**What Happened:**
- System loaded employee context (name, role, organization)
- System loaded 5 existing processes from the organization
- Agent personalized the greeting with employee's name and role
- Agent mentioned existing processes to set context

---

### Example 2: Process Matching During Interview

**Request:**
```bash
curl -X POST http://localhost:8001/api/v1/interviews/continue \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "interview_id": "01932e5f-8b2a-7890-b123-456789abcdef",
    "user_response": "Yo me encargo de aprobar las compras mayores a $1000 dólares",
    "language": "es"
  }'
```

**Response:**
```json
{
  "status": "success",
  "code": 200,
  "message": "Question generated successfully",
  "data": {
    "question": "Entiendo que apruebas compras mayores a $1000. ¿Este proceso es el mismo que el 'Proceso de Aprobación de Compras' que ya tenemos registrado, o es un proceso diferente?",
    "question_number": 2,
    "is_final": false,
    "corrected_response": "Yo me encargo de aprobar las compras mayores a $1000 dólares",
    "process_matches": [
      {
        "process_id": "01932e5f-proc-uuid",
        "process_name": "Proceso de Aprobación de Compras",
        "is_new": false,
        "confidence": 0.85
      }
    ]
  },
  "meta": {
    "session_id": "01932e5f-8b2a-7890-b123-456789abcdef",
    "question_count": 2,
    "language": "es",
    "process_matching_performed": true
  }
}
```

**What Happened:**
- User mentioned "aprobar las compras" (approve purchases)
- System detected potential process mention
- Process matching agent compared against existing processes
- Found 85% confidence match with "Proceso de Aprobación de Compras"
- Agent asked clarifying question to confirm if it's the same process
- Process match included in response for tracking

---

### Example 3: Identifying a New Process

**Request:**
```bash
curl -X POST http://localhost:8001/api/v1/interviews/continue \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "interview_id": "01932e5f-8b2a-7890-b123-456789abcdef",
    "user_response": "También gestiono el proceso de onboarding de nuevos empleados",
    "language": "es"
  }'
```

**Response:**
```json
{
  "status": "success",
  "code": 200,
  "message": "Question generated successfully",
  "data": {
    "question": "Interesante, el proceso de onboarding de nuevos empleados parece ser algo nuevo que no tenemos registrado. ¿Podrías describir los pasos principales de este proceso?",
    "question_number": 3,
    "is_final": false,
    "corrected_response": "También gestiono el proceso de onboarding de nuevos empleados",
    "process_matches": []
  },
  "meta": {
    "session_id": "01932e5f-8b2a-7890-b123-456789abcdef",
    "question_count": 3,
    "language": "es",
    "process_matching_performed": true
  }
}
```

**What Happened:**
- User mentioned "onboarding de nuevos empleados"
- System detected potential process mention
- Process matching agent found no matches (confidence < 0.5)
- Agent recognized this as a new process
- Agent asked for more details about the new process
- No process matches in response (empty array)

---

### Example 4: Exporting Interview with Process References

**Request:**
```bash
curl -X POST http://localhost:8001/api/v1/interviews/export \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "interview_id": "01932e5f-8b2a-7890-b123-456789abcdef"
  }'
```

**Response:**
```json
{
  "status": "success",
  "code": 200,
  "message": "Interview data exported successfully",
  "data": {
    "session_id": "01932e5f-8b2a-7890-b123-456789abcdef",
    "user_id": "01932e5f-user-uuid",
    "user_name": "Juan Pérez",
    "user_role": "Gerente de Operaciones",
    "organization": "ProssX Demo",
    "interview_date": "2025-11-07T10:30:00Z",
    "interview_duration_minutes": 15,
    "total_questions": 8,
    "total_user_responses": 8,
    "is_complete": true,
    "conversation_history": [
      {
        "role": "assistant",
        "content": "Hola Juan, ¿cuál es tu función principal?",
        "timestamp": "2025-11-07T10:15:00Z"
      },
      {
        "role": "user",
        "content": "Yo me encargo de aprobar las compras mayores a $1000",
        "timestamp": "2025-11-07T10:16:00Z"
      },
      {
        "role": "assistant",
        "content": "¿Este proceso es el mismo que el Proceso de Aprobación de Compras?",
        "timestamp": "2025-11-07T10:16:30Z"
      },
      {
        "role": "user",
        "content": "Sí, es el mismo proceso",
        "timestamp": "2025-11-07T10:17:00Z"
      }
    ],
    "processes_referenced": [
      {
        "process_id": "01932e5f-proc-uuid",
        "process_name": "Proceso de Aprobación de Compras",
        "is_new": false,
        "confidence": 0.85
      },
      {
        "process_id": "01932e5f-proc-uuid-2",
        "process_name": "Proceso de Onboarding de Empleados",
        "is_new": true,
        "confidence": 0.92
      }
    ],
    "context_used": {
      "employee_name": "Juan Pérez",
      "organization_name": "ProssX Demo",
      "roles": ["Gerente de Operaciones"],
      "existing_processes_count": 5,
      "interview_history": {
        "total_interviews": 2,
        "completed_interviews": 1,
        "last_interview_date": "2025-10-15T14:00:00Z"
      }
    }
  },
  "meta": {
    "export_date": "2025-11-07T10:45:00Z",
    "language": "es"
  }
}
```

**What Happened:**
- Interview completed with 8 questions
- System tracked 2 process references:
  - 1 existing process (Aprobación de Compras) with 85% confidence
  - 1 new process (Onboarding de Empleados) with 92% confidence
- Export includes full conversation history
- Export includes context that was used during the interview
- Export includes all process references for downstream analysis

---

### Example 5: Graceful Degradation (Backend Unavailable)

**Scenario:** Backend service (svc-organizations-php) is down

**Request:**
```bash
curl -X POST http://localhost:8001/api/v1/interviews/start \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{"language":"es"}'
```

**Response:**
```json
{
  "status": "success",
  "code": 200,
  "message": "Interview started successfully (limited context)",
  "data": {
    "session_id": "01932e5f-8b2a-7890-b123-456789abcdef",
    "question": "Hola, bienvenido a la entrevista. ¿Cuál es tu función principal en la organización?",
    "question_number": 1,
    "is_final": false
  },
  "meta": {
    "user_name": "Usuario",
    "organization": "Organización",
    "language": "es",
    "context_loaded": false,
    "processes_available": 0
  }
}
```

**What Happened:**
- Backend service was unavailable
- System proceeded with minimal context (graceful degradation)
- Generic greeting without personalization
- No existing processes loaded
- Interview continues normally but without context enrichment
- `context_loaded: false` indicates limited context mode

---

## Configuration

### Feature Flags

Context-aware features can be enabled/disabled via environment variables:

```bash
# Enable/disable context enrichment (default: true)
ENABLE_CONTEXT_ENRICHMENT=true

# Enable/disable process matching (default: true)
ENABLE_PROCESS_MATCHING=true

# Context cache TTL in seconds (default: 300 = 5 minutes)
CONTEXT_CACHE_TTL=300

# Process matching timeout in seconds (default: 3)
PROCESS_MATCHING_TIMEOUT=3

# Maximum processes to include in context (default: 20)
MAX_PROCESSES_IN_CONTEXT=20
```

### Backend Integration

Configure backend service URLs:

```bash
# Backend PHP service URL (required)
BACKEND_PHP_URL=http://localhost:8000/api/v1

# Backend connection timeout in seconds (default: 5)
BACKEND_TIMEOUT=5

# Backend retry attempts (default: 2)
BACKEND_MAX_RETRIES=2
```

---

## Error Handling

### Context Loading Errors

**Scenario:** Backend service returns error or times out

**Behavior:**
- System logs warning with error details
- Interview proceeds with minimal context
- Response includes `context_loaded: false` in meta
- No process matching performed (no existing processes available)

**Example Response:**
```json
{
  "status": "success",
  "code": 200,
  "message": "Interview started successfully (limited context)",
  "data": {
    "session_id": "01932e5f-8b2a-7890-b123-456789abcdef",
    "question": "Hola, bienvenido a la entrevista...",
    "question_number": 1,
    "is_final": false
  },
  "meta": {
    "user_name": "Usuario",
    "organization": "Organización",
    "language": "es",
    "context_loaded": false,
    "processes_available": 0,
    "warning": "Context enrichment unavailable"
  }
}
```

---

### Process Matching Errors

**Scenario:** Process matching times out or fails

**Behavior:**
- System logs warning with error details
- Interview continues without process matching for this turn
- Response includes empty `process_matches` array
- Next turn will retry process matching

**Example Response:**
```json
{
  "status": "success",
  "code": 200,
  "message": "Question generated successfully",
  "data": {
    "question": "Cuéntame más sobre ese proceso...",
    "question_number": 3,
    "is_final": false,
    "process_matches": []
  },
  "meta": {
    "session_id": "01932e5f-8b2a-7890-b123-456789abcdef",
    "question_count": 3,
    "language": "es",
    "process_matching_performed": false,
    "warning": "Process matching timeout"
  }
}
```

---

## Performance Metrics

### Target Performance

- **Context Loading**: < 2 seconds
- **Process Matching**: < 1 second
- **Total Interview Start**: < 3 seconds
- **Cache Hit Rate**: > 80% (after warmup)

### Monitoring

The system logs performance metrics for monitoring:

```
INFO: Context loaded in 1.2s (cache hit)
INFO: Process matching completed in 0.8s (confidence: 0.85)
INFO: Interview started in 2.1s (total)
```

### Cache Behavior

- **Cache TTL**: 5 minutes (configurable)
- **Cache Key**: Based on employee_id and organization_id
- **Cache Invalidation**: Automatic after TTL expires
- **Cache Hit Rate**: Logged for monitoring

---

## Backward Compatibility

### Legacy Endpoints

All existing endpoints remain unchanged:
- `/api/v1/interviews/start` - Enhanced with optional context
- `/api/v1/interviews/continue` - Enhanced with optional process matching
- `/api/v1/interviews/export` - Enhanced with optional process references

### Optional Fields

All new fields are optional and backward compatible:
- `process_matches` - Empty array if no matches
- `processes_referenced` - Empty array if no processes discussed
- `context_used` - Null if context not available

### Feature Flags

Context features can be disabled for backward compatibility:
```bash
ENABLE_CONTEXT_ENRICHMENT=false
ENABLE_PROCESS_MATCHING=false
```

When disabled, the system behaves exactly like version 1.1.0.

---

## Migration Guide

### For Frontend Developers

**No breaking changes required!** The API is backward compatible.

**Optional enhancements:**

1. **Display process matches in UI:**
```javascript
if (response.data.process_matches && response.data.process_matches.length > 0) {
  // Show process match indicator
  console.log('Matched processes:', response.data.process_matches);
}
```

2. **Show context loading status:**
```javascript
if (response.meta.context_loaded) {
  console.log('Context enrichment active');
} else {
  console.log('Running in limited context mode');
}
```

3. **Display process references in export:**
```javascript
const exportData = await exportInterview(interviewId);
if (exportData.processes_referenced.length > 0) {
  // Show list of processes discussed
  exportData.processes_referenced.forEach(process => {
    console.log(`${process.process_name} (${process.is_new ? 'New' : 'Existing'})`);
  });
}
```

---

## Troubleshooting

### Context Not Loading

**Symptom:** `context_loaded: false` in responses

**Possible Causes:**
1. Backend service (svc-organizations-php) is down
2. Backend service is slow (> 5 seconds timeout)
3. Invalid employee_id or organization_id in JWT token
4. Network connectivity issues

**Solutions:**
1. Check backend service health: `curl http://localhost:8000/api/v1/health`
2. Check AI service logs: `docker logs svc-elicitation-ai | grep -i context`
3. Verify JWT token contains valid employee_id and organization_id
4. Increase timeout: `BACKEND_TIMEOUT=10`

---

### Process Matching Not Working

**Symptom:** `process_matches` always empty

**Possible Causes:**
1. No existing processes in organization
2. Process matching disabled via feature flag
3. Process matching timeout (> 3 seconds)
4. User responses don't mention processes

**Solutions:**
1. Verify organization has processes: Check backend database
2. Enable process matching: `ENABLE_PROCESS_MATCHING=true`
3. Increase timeout: `PROCESS_MATCHING_TIMEOUT=5`
4. Check logs: `docker logs svc-elicitation-ai | grep -i "process match"`

---

### High Latency

**Symptom:** Interview start takes > 3 seconds

**Possible Causes:**
1. Backend service slow response
2. Cache not working (cold start)
3. Too many processes loaded (> 20)
4. Network latency

**Solutions:**
1. Check backend performance
2. Verify cache is enabled and working
3. Reduce max processes: `MAX_PROCESSES_IN_CONTEXT=10`
4. Check network latency between services

---

## Support

For issues or questions:
- Check logs: `docker logs svc-elicitation-ai`
- Review configuration: Environment variables
- Test backend connectivity: `curl http://localhost:8000/api/v1/health`
- Contact development team

---

**Last Updated:** 2025-11-07  
**Version:** 1.2.0
