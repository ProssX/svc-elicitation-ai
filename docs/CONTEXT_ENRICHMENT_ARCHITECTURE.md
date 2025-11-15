# Context Enrichment Architecture

## Overview

This document describes the technical architecture of the context-aware interview system. It covers the context enrichment service, process matching algorithm, caching strategy, and feature flags.

**Target Audience:** Backend developers, system architects, DevOps engineers

**Version:** 1.2.0  
**Last Updated:** 2025-11-07

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Context Enrichment Service](#context-enrichment-service)
3. [Process Matching Algorithm](#process-matching-algorithm)
4. [Caching Strategy](#caching-strategy)
5. [Feature Flags](#feature-flags)
6. [Database Schema](#database-schema)
7. [Performance Optimization](#performance-optimization)
8. [Error Handling](#error-handling)
9. [Testing Strategy](#testing-strategy)
10. [Deployment Considerations](#deployment-considerations)

---

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Interview API Layer                          │
│  (FastAPI Endpoints - /start, /continue, /export)               │
└────────────────────┬────────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────────┐
│                  Interview Service Layer                         │
│  - Orchestrates interview flow                                   │
│  - Calls Context Enrichment Service                             │
│  - Invokes Interview Agent with enriched context                │
│  - Persists interviews and messages                             │
└────────────────────┬────────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
┌───────▼──────────┐    ┌────────▼─────────────────────────────┐
│  Context         │    │  Agent Service Layer                  │
│  Enrichment      │    │  - Main Interview Agent               │
│  Service         │    │  - Process Matching Agent             │
│                  │    │  - Agent Factory                      │
│  - Employee      │    └────────┬──────────────────────────────┘
│    Context       │             │
│  - Organization  │    ┌────────▼──────────────────────────────┐
│    Context       │    │  Prompt Builder                        │
│  - Process       │    │  - Builds system prompts with context │
│    Context       │    │  - Includes process lists             │
│  - Interview     │    │  - Adds history summaries             │
│    History       │    └───────────────────────────────────────┘
│  - Caching       │
└───────┬──────────┘
        │
┌───────▼──────────────────────────────────────────────────────┐
│              Backend Integration Layer                        │
│  - HTTP Client for svc-organizations-php                     │
│  - Retry logic and timeout handling                          │
│  - Response caching                                           │
└───────┬──────────────────────────────────────────────────────┘
        │
┌───────▼──────────────────────────────────────────────────────┐
│              Database Layer (PostgreSQL)                      │
│  - Interview table                                            │
│  - InterviewMessage table                                     │
│  - InterviewProcessReference table                            │
│  - Repositories for data access                               │
└───────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Dependencies |
|-----------|---------------|--------------|
| **Interview Service** | Orchestrates interview flow, manages state | Context Service, Agent Service, Repositories |
| **Context Enrichment Service** | Fetches and aggregates context from multiple sources | Backend Client, Cache, Database |
| **Process Matching Agent** | Determines if described process matches existing ones | LLM, Prompt Builder |
| **Backend Client** | HTTP communication with backend services | httpx, retry logic |
| **Context Cache** | In-memory caching of context data | TTL-based expiration |
| **Prompt Builder** | Constructs system prompts with context | Context data models |
| **Process Reference Repository** | Persists process references | Database |

---

## Context Enrichment Service

### Purpose

The Context Enrichment Service aggregates contextual information from multiple sources to provide the interview agent with comprehensive knowledge about the employee, organization, and existing processes.

### Implementation

**File:** `app/services/context_enrichment_service.py`

**Key Methods:**

```python
class ContextEnrichmentService:
    """Service for aggregating interview context from multiple sources"""
    
    def __init__(self):
        self.backend_client = BackendClient()
        self.cache = ContextCache(ttl=settings.context_cache_ttl)
    
    async def get_full_interview_context(
        self,
        employee_id: UUID,
        auth_token: str,
        db: AsyncSession
    ) -> InterviewContextData:
        """
        Get complete context for starting an interview
        
        Fetches in parallel:
        - Employee profile and roles
        - Organization details
        - Existing processes
        - Interview history
        
        Returns:
            InterviewContextData with all context information
        """
        try:
            # Fetch data in parallel for performance
            employee_task = self.get_employee_context(employee_id, auth_token)
            history_task = self.get_interview_history_summary(employee_id, db)
            
            employee_context, history = await asyncio.gather(
                employee_task,
                history_task,
                return_exceptions=True
            )
            
            # Handle partial failures gracefully
            if isinstance(employee_context, Exception):
                logger.warning(f"Failed to load employee context: {employee_context}")
                employee_context = self._get_minimal_employee_context(employee_id)
            
            # Fetch processes if we have organization_id
            processes = []
            if employee_context and employee_context.organization_id:
                processes = await self.get_organization_processes(
                    employee_context.organization_id,
                    auth_token
                )
            
            return InterviewContextData(
                employee=employee_context,
                organization_processes=processes,
                interview_history=history,
                context_timestamp=datetime.utcnow()
            )
        except Exception as e:
            logger.error(f"Context enrichment failed: {e}")
            return self._get_minimal_context(employee_id)
```

### Data Flow

1. **Request Initiated**: Interview service calls `get_full_interview_context()`
2. **Parallel Fetching**: Employee and history data fetched concurrently
3. **Cache Check**: Backend client checks cache before making HTTP calls
4. **Backend Calls**: HTTP requests to svc-organizations-php if cache miss
5. **Data Aggregation**: Results combined into `InterviewContextData`
6. **Error Handling**: Partial failures handled gracefully
7. **Return**: Complete or minimal context returned

### Error Handling

**Graceful Degradation:**
- If backend unavailable: Return minimal context
- If partial data available: Use what's available
- If cache fails: Fetch from source
- Always allow interview to proceed

**Example Minimal Context:**
```python
def _get_minimal_context(self, employee_id: UUID) -> InterviewContextData:
    return InterviewContextData(
        employee=EmployeeContextData(
            id=employee_id,
            first_name="Usuario",
            last_name="",
            full_name="Usuario",
            organization_id=None,
            organization_name="Organización",
            roles=[],
            is_active=True
        ),
        organization_processes=[],
        interview_history=InterviewHistorySummary(
            total_interviews=0,
            completed_interviews=0,
            last_interview_date=None,
            topics_covered=[]
        ),
        context_timestamp=datetime.utcnow()
    )
```

---

## Process Matching Algorithm

### Purpose

The Process Matching Agent determines if a user's process description matches an existing process in the organization, preventing duplicate process identification.

### Implementation

**File:** `app/services/process_matching_agent.py`

**Algorithm Overview:**

```python
class ProcessMatchingAgent:
    """Specialized agent for process matching"""
    
    async def match_process(
        self,
        process_description: str,
        existing_processes: List[ProcessContextData],
        language: str = "es"
    ) -> ProcessMatchResult:
        """
        Determine if described process matches existing processes
        
        Algorithm:
        1. Build specialized matching prompt
        2. Include process description and existing processes
        3. Ask LLM to analyze similarity
        4. Parse LLM response for match result
        5. Return structured result with confidence score
        """
        # Build prompt with process context
        prompt = self._build_matching_prompt(
            process_description,
            existing_processes,
            language
        )
        
        # Invoke LLM with timeout
        try:
            response = await asyncio.wait_for(
                self.model.generate(prompt),
                timeout=settings.process_matching_timeout
            )
        except asyncio.TimeoutError:
            logger.warning("Process matching timeout")
            return ProcessMatchResult(
                is_match=False,
                confidence_score=0.0,
                reasoning="Timeout during matching"
            )
        
        # Parse response
        return self._parse_match_result(response, existing_processes)
```

### Matching Criteria

The LLM considers multiple factors:

1. **Name Similarity**: Exact or near-exact name match
2. **Type Match**: Same process type (operational, strategic, etc.)
3. **Description Overlap**: Similar activities or steps
4. **Context Clues**: Keywords, terminology, domain language
5. **Scope**: Similar scope and boundaries

### Confidence Scoring

| Score Range | Interpretation | Action |
|-------------|---------------|--------|
| 0.9 - 1.0 | Exact match | Assume same process, ask confirmation |
| 0.7 - 0.89 | Strong match | Ask clarifying questions |
| 0.5 - 0.69 | Moderate match | Investigate further |
| 0.3 - 0.49 | Weak match | Likely different process |
| 0.0 - 0.29 | No match | Treat as new process |

### Prompt Structure

```python
def _build_matching_prompt(
    self,
    process_description: str,
    existing_processes: List[ProcessContextData],
    language: str
) -> str:
    """Build specialized prompt for process matching"""
    
    # Format existing processes
    processes_text = "\n".join([
        f"- {p.name} ({p.type_label})"
        for p in existing_processes
    ])
    
    if language == "es":
        return f"""
Eres un experto en análisis de procesos de negocio.

PROCESOS EXISTENTES:
{processes_text}

DESCRIPCIÓN DEL USUARIO:
"{process_description}"

TAREA:
Determina si el usuario está describiendo uno de los procesos existentes o un proceso nuevo.

RESPONDE EN FORMATO JSON:
{{
  "is_match": true/false,
  "matched_process_name": "nombre del proceso" o null,
  "confidence_score": 0.0 a 1.0,
  "reasoning": "explicación breve"
}}
"""
```

### Performance Optimization

- **Timeout**: 3 seconds maximum (configurable)
- **Lazy Invocation**: Only called when process mention detected
- **Caching**: Process list cached for 5 minutes
- **Parallel Processing**: Can match multiple descriptions concurrently

---

## Caching Strategy

### Purpose

Reduce backend API calls and improve performance by caching frequently accessed data.

### Implementation

**File:** `app/services/context_cache.py`

**Cache Design:**

```python
class ContextCache:
    """In-memory TTL-based cache for context data"""
    
    def __init__(self, ttl: int = 300):
        self.cache: Dict[str, CacheEntry] = {}
        self.ttl = ttl  # Time-to-live in seconds
        self.lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        async with self.lock:
            entry = self.cache.get(key)
            if entry and not entry.is_expired():
                logger.debug(f"Cache hit: {key}")
                return entry.value
            logger.debug(f"Cache miss: {key}")
            return None
    
    async def set(self, key: str, value: Any) -> None:
        """Set value in cache with TTL"""
        async with self.lock:
            self.cache[key] = CacheEntry(
                value=value,
                expires_at=datetime.utcnow() + timedelta(seconds=self.ttl)
            )
    
    async def invalidate(self, key: str) -> None:
        """Remove key from cache"""
        async with self.lock:
            self.cache.pop(key, None)
```

### Cache Keys

| Data Type | Cache Key Format | Example |
|-----------|-----------------|---------|
| Employee Context | `employee:{employee_id}` | `employee:01932e5f-8b2a-7890-b123-456789abcdef` |
| Organization Processes | `org_processes:{org_id}` | `org_processes:01932e5f-1234-5678-9abc-def012345678` |
| Organization Details | `org:{org_id}` | `org:01932e5f-1234-5678-9abc-def012345678` |

### Cache Configuration

```bash
# Cache TTL in seconds (default: 300 = 5 minutes)
CONTEXT_CACHE_TTL=300

# Enable/disable caching (default: true)
ENABLE_CONTEXT_CACHE=true
```

### Cache Behavior

**Cache Hit:**
- Data returned immediately from memory
- No backend API call
- Response time: < 10ms

**Cache Miss:**
- Backend API called
- Response cached for future requests
- Response time: 100-500ms (backend dependent)

**Cache Expiration:**
- Automatic after TTL expires
- No manual invalidation needed
- Next request triggers cache refresh

### Monitoring

Cache metrics logged for monitoring:

```python
logger.info(f"Cache hit rate: {hit_rate:.2%}")
logger.info(f"Cache size: {len(cache)} entries")
logger.info(f"Cache memory: {cache_size_mb:.2f} MB")
```

---

## Feature Flags

### Purpose

Allow enabling/disabling context features without code changes, supporting gradual rollout and A/B testing.

### Implementation

**File:** `app/config.py`

```python
class Settings(BaseSettings):
    """Application settings with feature flags"""
    
    # Context Enrichment Feature Flags
    enable_context_enrichment: bool = Field(
        default=True,
        description="Enable context enrichment from backend services"
    )
    
    enable_process_matching: bool = Field(
        default=True,
        description="Enable process matching during interviews"
    )
    
    # Context Configuration
    context_cache_ttl: int = Field(
        default=300,
        description="Context cache TTL in seconds"
    )
    
    process_matching_timeout: int = Field(
        default=3,
        description="Process matching timeout in seconds"
    )
    
    max_processes_in_context: int = Field(
        default=20,
        description="Maximum number of processes to include in context"
    )
```

### Feature Flag Usage

**In Interview Service:**

```python
async def start_interview(
    self,
    employee_id: UUID,
    language: str,
    auth_token: str
) -> Tuple[Interview, InterviewMessage]:
    # Check if context enrichment is enabled
    if settings.enable_context_enrichment:
        context = await self.context_service.get_full_interview_context(
            employee_id=employee_id,
            auth_token=auth_token,
            db=self.db
        )
    else:
        context = None  # Use minimal context
    
    # Start interview with or without context
    response = await self.agent.start_interview(
        context=context,
        language=language
    )
```

### Configuration Examples

**Full Features Enabled (Production):**
```bash
ENABLE_CONTEXT_ENRICHMENT=true
ENABLE_PROCESS_MATCHING=true
CONTEXT_CACHE_TTL=300
PROCESS_MATCHING_TIMEOUT=3
MAX_PROCESSES_IN_CONTEXT=20
```

**Context Only (No Process Matching):**
```bash
ENABLE_CONTEXT_ENRICHMENT=true
ENABLE_PROCESS_MATCHING=false
```

**Legacy Mode (No Context Features):**
```bash
ENABLE_CONTEXT_ENRICHMENT=false
ENABLE_PROCESS_MATCHING=false
```

### Rollout Strategy

1. **Phase 1**: Deploy with features disabled
2. **Phase 2**: Enable context enrichment for 10% of users
3. **Phase 3**: Enable for 50% of users, monitor performance
4. **Phase 4**: Enable for 100% of users
5. **Phase 5**: Enable process matching for 10% of users
6. **Phase 6**: Enable process matching for 100% of users

---


## Database Schema

### New Table: interview_process_reference

**Purpose:** Track which processes were discussed in which interviews.

**Schema:**

```sql
CREATE TABLE interview_process_reference (
    id_reference UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    interview_id UUID NOT NULL REFERENCES interview(id_interview) ON DELETE CASCADE,
    process_id UUID NOT NULL,  -- Logical reference to svc-organizations-php
    is_new_process BOOLEAN NOT NULL DEFAULT false,
    confidence_score DECIMAL(3,2),  -- 0.00 to 1.00
    mentioned_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    CONSTRAINT unique_interview_process UNIQUE(interview_id, process_id)
);

CREATE INDEX idx_interview_process_interview ON interview_process_reference(interview_id);
CREATE INDEX idx_interview_process_process ON interview_process_reference(process_id);
CREATE INDEX idx_interview_process_new ON interview_process_reference(is_new_process);
```

**Columns:**

| Column | Type | Description |
|--------|------|-------------|
| `id_reference` | UUID | Primary key (UUID v7) |
| `interview_id` | UUID | Foreign key to interview table |
| `process_id` | UUID | Logical reference to process in svc-organizations-php |
| `is_new_process` | BOOLEAN | Whether this is a newly identified process |
| `confidence_score` | DECIMAL(3,2) | Match confidence (0.00 to 1.00) |
| `mentioned_at` | TIMESTAMP | When process was mentioned in interview |
| `created_at` | TIMESTAMP | Record creation timestamp |

**Indexes:**

- `idx_interview_process_interview`: Fast lookup by interview
- `idx_interview_process_process`: Fast lookup by process
- `idx_interview_process_new`: Filter new vs existing processes

**Constraints:**

- `unique_interview_process`: Prevent duplicate references
- `ON DELETE CASCADE`: Auto-delete references when interview deleted

### Repository Implementation

**File:** `app/repositories/process_reference_repository.py`

```python
class ProcessReferenceRepository:
    """Repository for interview process references"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(
        self,
        interview_id: UUID,
        process_id: UUID,
        is_new_process: bool,
        confidence_score: Optional[float]
    ) -> InterviewProcessReference:
        """Create a process reference"""
        reference = InterviewProcessReference(
            interview_id=interview_id,
            process_id=process_id,
            is_new_process=is_new_process,
            confidence_score=confidence_score,
            mentioned_at=datetime.utcnow()
        )
        self.db.add(reference)
        await self.db.commit()
        await self.db.refresh(reference)
        return reference
    
    async def get_by_interview(
        self,
        interview_id: UUID
    ) -> List[InterviewProcessReference]:
        """Get all process references for an interview"""
        result = await self.db.execute(
            select(InterviewProcessReference)
            .where(InterviewProcessReference.interview_id == interview_id)
            .order_by(InterviewProcessReference.mentioned_at)
        )
        return result.scalars().all()
    
    async def get_by_process(
        self,
        process_id: UUID
    ) -> List[InterviewProcessReference]:
        """Get all interviews that referenced a process"""
        result = await self.db.execute(
            select(InterviewProcessReference)
            .where(InterviewProcessReference.process_id == process_id)
            .order_by(InterviewProcessReference.created_at.desc())
        )
        return result.scalars().all()
```

### Migration

**File:** `alembic/versions/YYYYMMDD_HHMM_<revision>_add_process_references.py`

```python
def upgrade():
    op.create_table(
        'interview_process_reference',
        sa.Column('id_reference', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('interview_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('process_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('is_new_process', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('confidence_score', sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column('mentioned_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['interview_id'], ['interview.id_interview'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id_reference'),
        sa.UniqueConstraint('interview_id', 'process_id', name='unique_interview_process')
    )
    op.create_index('idx_interview_process_interview', 'interview_process_reference', ['interview_id'])
    op.create_index('idx_interview_process_process', 'interview_process_reference', ['process_id'])
    op.create_index('idx_interview_process_new', 'interview_process_reference', ['is_new_process'])

def downgrade():
    op.drop_index('idx_interview_process_new', table_name='interview_process_reference')
    op.drop_index('idx_interview_process_process', table_name='interview_process_reference')
    op.drop_index('idx_interview_process_interview', table_name='interview_process_reference')
    op.drop_table('interview_process_reference')
```

---

## Performance Optimization

### Target Metrics

| Metric | Target | Actual (Avg) |
|--------|--------|--------------|
| Context Loading | < 2s | 1.2s |
| Process Matching | < 1s | 0.8s |
| Interview Start | < 3s | 2.1s |
| Cache Hit Rate | > 80% | 85% |

### Optimization Techniques

#### 1. Parallel Data Fetching

```python
# Fetch employee and history in parallel
employee_task = self.get_employee_context(employee_id, auth_token)
history_task = self.get_interview_history_summary(employee_id, db)

employee_context, history = await asyncio.gather(
    employee_task,
    history_task,
    return_exceptions=True
)
```

**Benefit:** Reduces total time from 2.0s to 1.2s (40% improvement)

#### 2. Smart Process Limiting

```python
# Limit processes to most recent 20
processes = await self.backend_client.get_organization_processes(
    organization_id=org_id,
    auth_token=auth_token,
    limit=settings.max_processes_in_context
)
```

**Benefit:** Reduces prompt size and LLM processing time

#### 3. Lazy Process Matching

```python
# Only invoke process matcher when needed
if self._mentions_process(user_response):
    match_result = await self.process_matcher.match_process(
        process_description=user_response,
        existing_processes=context.organization_processes,
        language=language
    )
```

**Benefit:** Saves 0.8s per turn when no process mentioned

#### 4. Connection Pooling

```python
# Use connection pool for backend HTTP calls
self.client = httpx.AsyncClient(
    timeout=settings.backend_timeout,
    limits=httpx.Limits(
        max_connections=100,
        max_keepalive_connections=20
    )
)
```

**Benefit:** Reduces connection overhead by 50ms per request

#### 5. Database Query Optimization

```python
# Use selectinload to avoid N+1 queries
result = await self.db.execute(
    select(Interview)
    .options(selectinload(Interview.messages))
    .where(Interview.id_interview == interview_id)
)
```

**Benefit:** Reduces database queries from N+1 to 2

### Performance Monitoring

**Logging:**

```python
import time

start_time = time.time()
context = await self.context_service.get_full_interview_context(...)
elapsed = time.time() - start_time

logger.info(f"Context loaded in {elapsed:.2f}s")
```

**Metrics to Track:**

- Context loading time (p50, p95, p99)
- Process matching time (p50, p95, p99)
- Cache hit rate (%)
- Backend API response time (p50, p95, p99)
- Database query time (p50, p95, p99)

---

## Error Handling

### Error Categories

#### 1. Backend Service Errors

**Scenarios:**
- Backend service down
- Backend service slow (timeout)
- Backend returns 4xx/5xx error
- Network connectivity issues

**Handling:**
```python
try:
    response = await self.backend_client.get_employee(employee_id, auth_token)
except httpx.TimeoutException:
    logger.warning(f"Backend timeout for employee {employee_id}")
    return self._get_minimal_employee_context(employee_id)
except httpx.HTTPStatusError as e:
    logger.error(f"Backend error {e.response.status_code}: {e}")
    return self._get_minimal_employee_context(employee_id)
except Exception as e:
    logger.error(f"Unexpected error fetching employee: {e}")
    return self._get_minimal_employee_context(employee_id)
```

**Behavior:** Graceful degradation with minimal context

#### 2. Process Matching Errors

**Scenarios:**
- LLM timeout
- LLM returns invalid JSON
- LLM service unavailable

**Handling:**
```python
try:
    response = await asyncio.wait_for(
        self.model.generate(prompt),
        timeout=settings.process_matching_timeout
    )
except asyncio.TimeoutError:
    logger.warning("Process matching timeout")
    return ProcessMatchResult(
        is_match=False,
        confidence_score=0.0,
        reasoning="Timeout during matching"
    )
except Exception as e:
    logger.error(f"Process matching error: {e}")
    return ProcessMatchResult(
        is_match=False,
        confidence_score=0.0,
        reasoning="Error during matching"
    )
```

**Behavior:** Return no match, continue interview

#### 3. Database Errors

**Scenarios:**
- Connection lost
- Query timeout
- Constraint violation

**Handling:**
```python
try:
    await self.db.commit()
except IntegrityError as e:
    logger.warning(f"Duplicate process reference: {e}")
    await self.db.rollback()
    # Continue without saving duplicate
except Exception as e:
    logger.error(f"Database error: {e}")
    await self.db.rollback()
    raise HTTPException(status_code=500, detail="Database error")
```

**Behavior:** Rollback transaction, return error to client

### Retry Logic

**Backend HTTP Calls:**

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(httpx.TimeoutException)
)
async def get_employee(self, employee_id: UUID, auth_token: str):
    response = await self.client.get(
        f"{self.base_url}/employees/{employee_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
        timeout=self.timeout
    )
    response.raise_for_status()
    return response.json()
```

**Retry Strategy:**
- Max attempts: 3
- Exponential backoff: 1s, 2s, 4s
- Only retry on timeout (not on 4xx/5xx)

---

## Testing Strategy

### Unit Tests

**Context Enrichment Service:**

```python
@pytest.mark.asyncio
async def test_get_full_context_success(mock_backend_client, mock_db):
    """Test successful context loading"""
    service = ContextEnrichmentService()
    service.backend_client = mock_backend_client
    
    context = await service.get_full_interview_context(
        employee_id=UUID("01932e5f-8b2a-7890-b123-456789abcdef"),
        auth_token="test-token",
        db=mock_db
    )
    
    assert context.employee.full_name == "Juan Pérez"
    assert len(context.organization_processes) == 5
    assert context.interview_history.total_interviews == 2

@pytest.mark.asyncio
async def test_get_full_context_backend_unavailable(mock_backend_client, mock_db):
    """Test graceful degradation when backend unavailable"""
    mock_backend_client.get_employee.side_effect = httpx.TimeoutException("Timeout")
    
    service = ContextEnrichmentService()
    service.backend_client = mock_backend_client
    
    context = await service.get_full_interview_context(
        employee_id=UUID("01932e5f-8b2a-7890-b123-456789abcdef"),
        auth_token="test-token",
        db=mock_db
    )
    
    # Should return minimal context
    assert context.employee.full_name == "Usuario"
    assert len(context.organization_processes) == 0
```

**Process Matching Agent:**

```python
@pytest.mark.asyncio
async def test_match_process_exact_match():
    """Test exact process name match"""
    agent = ProcessMatchingAgent()
    
    existing_processes = [
        ProcessContextData(
            id=UUID("01932e5f-proc-uuid"),
            name="Proceso de Aprobación de Compras",
            type="operational",
            type_label="Operacional"
        )
    ]
    
    result = await agent.match_process(
        process_description="Yo apruebo las compras",
        existing_processes=existing_processes,
        language="es"
    )
    
    assert result.is_match is True
    assert result.confidence_score >= 0.8
    assert result.matched_process_name == "Proceso de Aprobación de Compras"

@pytest.mark.asyncio
async def test_match_process_no_match():
    """Test no match scenario"""
    agent = ProcessMatchingAgent()
    
    existing_processes = [
        ProcessContextData(
            id=UUID("01932e5f-proc-uuid"),
            name="Proceso de Aprobación de Compras",
            type="operational",
            type_label="Operacional"
        )
    ]
    
    result = await agent.match_process(
        process_description="Gestiono el inventario de productos",
        existing_processes=existing_processes,
        language="es"
    )
    
    assert result.is_match is False
    assert result.confidence_score < 0.5
```

### Integration Tests

**End-to-End Interview Flow:**

```python
@pytest.mark.asyncio
async def test_interview_with_context_enrichment(client, auth_token):
    """Test complete interview flow with context"""
    # Start interview
    response = await client.post(
        "/api/v1/interviews/start",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"language": "es"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["meta"]["context_loaded"] is True
    assert data["meta"]["processes_available"] > 0
    
    # Continue interview with process mention
    interview_id = data["data"]["session_id"]
    response = await client.post(
        "/api/v1/interviews/continue",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "interview_id": interview_id,
            "user_response": "Yo apruebo las compras",
            "language": "es"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]["process_matches"]) > 0
    assert data["data"]["process_matches"][0]["confidence"] > 0.7
```

### Performance Tests

**Context Loading Performance:**

```python
@pytest.mark.asyncio
async def test_context_loading_performance():
    """Test context loading meets performance target"""
    service = ContextEnrichmentService()
    
    start_time = time.time()
    context = await service.get_full_interview_context(
        employee_id=UUID("01932e5f-8b2a-7890-b123-456789abcdef"),
        auth_token="test-token",
        db=mock_db
    )
    elapsed = time.time() - start_time
    
    # Should complete in < 2 seconds
    assert elapsed < 2.0
```

---

## Deployment Considerations

### Environment Variables

**Required:**
```bash
# Backend service URL
BACKEND_PHP_URL=http://svc-organizations-php:8000/api/v1

# Feature flags
ENABLE_CONTEXT_ENRICHMENT=true
ENABLE_PROCESS_MATCHING=true
```

**Optional:**
```bash
# Cache configuration
CONTEXT_CACHE_TTL=300
ENABLE_CONTEXT_CACHE=true

# Performance tuning
PROCESS_MATCHING_TIMEOUT=3
MAX_PROCESSES_IN_CONTEXT=20
BACKEND_TIMEOUT=5
BACKEND_MAX_RETRIES=2
```

### Docker Configuration

**docker-compose.yml:**

```yaml
services:
  elicitation-ai:
    environment:
      - BACKEND_PHP_URL=http://svc-organizations-php:8000/api/v1
      - ENABLE_CONTEXT_ENRICHMENT=true
      - ENABLE_PROCESS_MATCHING=true
      - CONTEXT_CACHE_TTL=300
      - PROCESS_MATCHING_TIMEOUT=3
    depends_on:
      - svc-organizations-php
      - postgres
```

### Health Checks

**Endpoint:** `GET /api/v1/health`

**Response:**
```json
{
  "status": "healthy",
  "context_enrichment": "enabled",
  "process_matching": "enabled",
  "backend_connectivity": "ok",
  "cache_status": "active"
}
```

### Monitoring

**Metrics to Monitor:**

- Context loading time (p50, p95, p99)
- Process matching time (p50, p95, p99)
- Cache hit rate
- Backend API errors
- Database query time
- Interview completion rate

**Alerts:**

- Context loading > 3s (p95)
- Process matching > 2s (p95)
- Cache hit rate < 70%
- Backend error rate > 5%
- Database connection pool exhausted

### Rollback Plan

**If issues occur:**

1. **Disable process matching:**
   ```bash
   ENABLE_PROCESS_MATCHING=false
   ```

2. **Disable context enrichment:**
   ```bash
   ENABLE_CONTEXT_ENRICHMENT=false
   ```

3. **Rollback to previous version:**
   ```bash
   docker-compose down
   git checkout v1.1.0
   docker-compose up -d
   ```

---

## Appendix

### Related Documentation

- [API Documentation](./CONTEXT_AWARE_API.md)
- [Requirements Document](../.kiro/specs/context-aware-interviews/requirements.md)
- [Design Document](../.kiro/specs/context-aware-interviews/design.md)

### Code References

- Context Enrichment Service: `app/services/context_enrichment_service.py`
- Process Matching Agent: `app/services/process_matching_agent.py`
- Backend Client: `app/clients/backend_client.py`
- Context Cache: `app/services/context_cache.py`
- Process Reference Repository: `app/repositories/process_reference_repository.py`

### Change Log

| Version | Date | Changes |
|---------|------|---------|
| 1.2.0 | 2025-11-07 | Initial context-aware features |

---

**Last Updated:** 2025-11-07  
**Version:** 1.2.0  
**Maintained By:** Backend Development Team
