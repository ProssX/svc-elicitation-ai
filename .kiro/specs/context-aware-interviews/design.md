# Design Document

## Overview

This design document outlines the architecture for enhancing the AI interview system with comprehensive context awareness. The system will integrate with the svc-organizations-php backend to retrieve employee profiles, organizational data, and existing process information, enabling the interview agent to conduct more intelligent and personalized interviews.

The design introduces a multi-layered context enrichment system, specialized agents for process matching, and database schema extensions to track process references. The architecture maintains backward compatibility while adding powerful new capabilities for context-aware interviewing.

### Key Design Goals

1. **Rich Context**: Provide the interview agent with complete employee, organization, and process context
2. **Process Intelligence**: Enable the agent to recognize when employees describe existing processes
3. **Multi-Agent Architecture**: Support specialized agents for complex reasoning tasks
4. **Performance**: Maintain interview start times under 3 seconds despite additional context loading
5. **Backward Compatibility**: Ensure existing interviews and exports continue to work
6. **Graceful Degradation**: Handle backend service failures without breaking interviews

## Architecture

### High-Level Architecture Diagram

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
│  - HTTP Client for svc-users-python (if needed)              │
│  - Retry logic and timeout handling                          │
│  - Response caching                                           │
└───────┬──────────────────────────────────────────────────────┘
        │
┌───────▼──────────────────────────────────────────────────────┐
│              Database Layer (PostgreSQL)                      │
│  - Interview table                                            │
│  - InterviewMessage table                                     │
│  - InterviewProcessReference table (NEW)                      │
│  - Repositories for data access                               │
└───────────────────────────────────────────────────────────────┘
```

### Component Interaction Flow

**Interview Start Flow:**
```
1. User calls /start endpoint with employee_id
2. Interview Service calls Context Enrichment Service
3. Context Service fetches (in parallel):
   - Employee profile from svc-organizations-php
   - Organization details from svc-organizations-php
   - Existing processes from svc-organizations-php
   - Previous interviews from local database
4. Context Service aggregates and caches results
5. Interview Service creates Interview record in database
6. Interview Service calls Agent Service with enriched context
7. Agent Service builds system prompt with context
8. Agent generates first question
9. Interview Service saves first message
10. Response returned to user
```

**Interview Continue Flow:**
```
1. User calls /continue endpoint with interview_id and response
2. Interview Service loads interview from database
3. Interview Service loads message history from database
4. Interview Service checks if process matching is needed
5. If process mentioned:
   a. Invoke Process Matching Agent
   b. Compare against existing processes
   c. Determine if new or existing process
6. Interview Service calls Main Agent with:
   - User response
   - Conversation history
   - Process matching results (if any)
7. Agent generates next question
8. Interview Service saves user message and agent message
9. If final question, mark interview as completed
10. Response returned to user
```

## Components and Interfaces

### 1. Context Enrichment Service

**Purpose**: Aggregate contextual information from multiple sources and provide it to the interview agent.

**File**: `app/services/context_enrichment_service.py`

**Key Methods**:

```python
class ContextEnrichmentService:
    """Service for aggregating interview context from multiple sources"""
    
    def __init__(self):
        self.backend_client = BackendClient()
        self.cache = ContextCache(ttl=300)  # 5 minute cache
    
    async def get_full_interview_context(
        self,
        employee_id: UUID,
        db: AsyncSession
    ) -> InterviewContextData:
        """
        Get complete context for starting an interview
        
        Returns:
            InterviewContextData with employee, organization, processes, and history
        """
        pass
    
    async def get_employee_context(
        self,
        employee_id: UUID
    ) -> EmployeeContextData:
        """Get employee profile including roles"""
        pass
    
    async def get_organization_processes(
        self,
        organization_id: str,
        limit: int = 20
    ) -> List[ProcessContextData]:
        """Get existing processes for organization"""
        pass
    
    async def get_interview_history_summary(
        self,
        employee_id: UUID,
        db: AsyncSession
    ) -> InterviewHistorySummary:
        """Get summary of employee's previous interviews"""
        pass
```

**Context Data Models**:

```python
class EmployeeContextData(BaseModel):
    """Employee context information"""
    id: UUID
    first_name: str
    last_name: str
    full_name: str
    organization_id: str
    organization_name: str
    roles: List[RoleContextData]
    is_active: bool

class RoleContextData(BaseModel):
    """Role information"""
    id: UUID
    name: str
    description: Optional[str]

class ProcessContextData(BaseModel):
    """Process information for context"""
    id: UUID
    name: str
    type: str
    type_label: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

class InterviewHistorySummary(BaseModel):
    """Summary of employee's interview history"""
    total_interviews: int
    completed_interviews: int
    last_interview_date: Optional[datetime]
    topics_covered: List[str]  # Extracted from previous interviews

class InterviewContextData(BaseModel):
    """Complete context for an interview"""
    employee: EmployeeContextData
    organization_processes: List[ProcessContextData]
    interview_history: InterviewHistorySummary
    context_timestamp: datetime
```

### 2. Backend Client

**Purpose**: Handle HTTP communication with svc-organizations-php backend.

**File**: `app/clients/backend_client.py`

**Key Methods**:

```python
class BackendClient:
    """HTTP client for svc-organizations-php API"""
    
    def __init__(self):
        self.base_url = settings.backend_php_url
        self.timeout = 5.0
        self.max_retries = 2
    
    async def get_employee(
        self,
        employee_id: UUID,
        auth_token: str
    ) -> Optional[Dict]:
        """Fetch employee details"""
        pass
    
    async def get_organization(
        self,
        organization_id: str,
        auth_token: str
    ) -> Optional[Dict]:
        """Fetch organization details"""
        pass
    
    async def get_organization_processes(
        self,
        organization_id: str,
        auth_token: str,
        active_only: bool = True,
        limit: int = 20
    ) -> List[Dict]:
        """Fetch processes for organization"""
        pass
    
    async def get_employee_roles(
        self,
        organization_id: str,
        employee_id: UUID,
        auth_token: str
    ) -> List[Dict]:
        """Fetch roles for employee"""
        pass
```

### 3. Process Matching Agent

**Purpose**: Specialized agent that determines if a described process matches existing processes.

**File**: `app/services/process_matching_agent.py`

**Key Methods**:

```python
class ProcessMatchingAgent:
    """Specialized agent for process matching"""
    
    def __init__(self):
        self.model = create_model()
    
    async def match_process(
        self,
        process_description: str,
        existing_processes: List[ProcessContextData],
        language: str = "es"
    ) -> ProcessMatchResult:
        """
        Determine if described process matches existing processes
        
        Args:
            process_description: User's description of a process
            existing_processes: List of existing processes in organization
            language: Interview language
            
        Returns:
            ProcessMatchResult with match confidence and reasoning
        """
        pass
    
    def _build_matching_prompt(
        self,
        process_description: str,
        existing_processes: List[ProcessContextData],
        language: str
    ) -> str:
        """Build system prompt for process matching"""
        pass
```

**Process Match Result Model**:

```python
class ProcessMatchResult(BaseModel):
    """Result of process matching analysis"""
    is_match: bool
    matched_process_id: Optional[UUID]
    matched_process_name: Optional[str]
    confidence_score: float  # 0.0 to 1.0
    reasoning: str
    suggested_clarifying_questions: List[str]
```

### 4. Enhanced Agent Service

**Purpose**: Extend existing agent service to use enriched context and invoke process matching.

**File**: `app/services/agent_service.py` (enhanced)

**Key Changes**:

```python
class InterviewAgent:
    """Enhanced interview agent with context awareness"""
    
    def __init__(self):
        self.model = create_model()
        self.process_matcher = ProcessMatchingAgent()
    
    async def start_interview(
        self,
        context: InterviewContextData,
        language: str = "es"
    ) -> InterviewResponse:
        """
        Start interview with enriched context
        
        Args:
            context: Complete interview context
            language: Interview language
            
        Returns:
            InterviewResponse with first question
        """
        # Build system prompt with context
        system_prompt = self._build_context_aware_prompt(context, language)
        
        # Create agent with enriched prompt
        agent = Agent(
            model=self.model,
            system_prompt=system_prompt,
            callback_handler=None
        )
        
        # Generate first question
        # ... existing logic
    
    async def continue_interview(
        self,
        user_response: str,
        conversation_history: List[ConversationMessage],
        context: InterviewContextData,
        language: str = "es"
    ) -> InterviewResponse:
        """
        Continue interview with process matching capability
        
        Args:
            user_response: User's response
            conversation_history: Full conversation history
            context: Interview context
            language: Interview language
            
        Returns:
            InterviewResponse with next question and process matches
        """
        # Check if user mentioned a process
        if self._mentions_process(user_response):
            # Invoke process matching agent
            match_result = await self.process_matcher.match_process(
                process_description=user_response,
                existing_processes=context.organization_processes,
                language=language
            )
            
            # Include match result in context for next question
            # ... logic to incorporate match result
        
        # Generate next question with context
        # ... existing logic
    
    def _build_context_aware_prompt(
        self,
        context: InterviewContextData,
        language: str
    ) -> str:
        """Build system prompt with enriched context"""
        pass
    
    def _mentions_process(self, text: str) -> bool:
        """Detect if user response mentions a process"""
        pass
```

### 5. Prompt Builder

**Purpose**: Build system prompts that include contextual information.

**File**: `app/services/prompt_builder.py`

**Key Methods**:

```python
class PromptBuilder:
    """Builds context-aware system prompts"""
    
    @staticmethod
    def build_interview_prompt(
        context: InterviewContextData,
        language: str
    ) -> str:
        """
        Build system prompt with context
        
        Includes:
        - Employee name and roles
        - Organization information
        - Existing processes
        - Interview history summary
        - Process matching instructions
        """
        pass
    
    @staticmethod
    def build_process_matching_prompt(
        process_description: str,
        existing_processes: List[ProcessContextData],
        language: str
    ) -> str:
        """Build prompt for process matching agent"""
        pass
    
    @staticmethod
    def format_process_list(
        processes: List[ProcessContextData],
        language: str
    ) -> str:
        """Format process list for inclusion in prompt"""
        pass
    
    @staticmethod
    def format_interview_history(
        history: InterviewHistorySummary,
        language: str
    ) -> str:
        """Format interview history for inclusion in prompt"""
        pass
```

### 6. Database Schema Extensions

**New Table**: `interview_process_reference`

**Purpose**: Track which processes were discussed in which interviews.

**Schema**:

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
```

**Model**:

```python
class InterviewProcessReference(Base):
    """Reference between interviews and processes"""
    __tablename__ = "interview_process_reference"
    
    id_reference = Column(UUID(as_uuid=True), primary_key=True, default=uuid_generate)
    interview_id = Column(UUID(as_uuid=True), ForeignKey('interview.id_interview', ondelete='CASCADE'), nullable=False)
    process_id = Column(UUID(as_uuid=True), nullable=False)  # Logical FK
    is_new_process = Column(Boolean, nullable=False, default=False)
    confidence_score = Column(Numeric(3, 2), nullable=True)
    mentioned_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationship
    interview = relationship("Interview", back_populates="process_references")
```

**Repository**:

```python
class ProcessReferenceRepository:
    """Repository for interview process references"""
    
    async def create(
        self,
        interview_id: UUID,
        process_id: UUID,
        is_new_process: bool,
        confidence_score: Optional[float]
    ) -> InterviewProcessReference:
        """Create a process reference"""
        pass
    
    async def get_by_interview(
        self,
        interview_id: UUID
    ) -> List[InterviewProcessReference]:
        """Get all process references for an interview"""
        pass
    
    async def get_by_process(
        self,
        process_id: UUID
    ) -> List[InterviewProcessReference]:
        """Get all interviews that referenced a process"""
        pass
```

### 7. Enhanced Interview Service

**File**: `app/services/interview_service.py` (enhanced)

**Key Changes**:

```python
class InterviewService:
    """Enhanced interview service with context awareness"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.interview_repo = InterviewRepository(db)
        self.message_repo = MessageRepository(db)
        self.process_ref_repo = ProcessReferenceRepository(db)
        self.context_service = ContextEnrichmentService()
        self.agent = InterviewAgent()
    
    async def start_interview(
        self,
        employee_id: UUID,
        language: str,
        technical_level: str,
        auth_token: str  # NEW: for backend calls
    ) -> Tuple[Interview, InterviewMessage]:
        """
        Start interview with context enrichment
        
        NEW: Fetches context before starting interview
        """
        # Get enriched context
        context = await self.context_service.get_full_interview_context(
            employee_id=employee_id,
            db=self.db
        )
        
        # Start interview with context
        response = await self.agent.start_interview(
            context=context,
            language=language
        )
        
        # Create interview record
        # ... existing logic
    
    async def continue_interview(
        self,
        interview_id: UUID,
        employee_id: UUID,
        user_response: str,
        auth_token: str  # NEW: for backend calls
    ) -> Tuple[Interview, InterviewMessage, InterviewMessage]:
        """
        Continue interview with process matching
        
        NEW: Checks for process matches and saves references
        """
        # Load interview and context
        interview = await self.interview_repo.get_by_id(interview_id, employee_id)
        context = await self.context_service.get_full_interview_context(
            employee_id=employee_id,
            db=self.db
        )
        
        # Load conversation history
        messages = await self.message_repo.get_by_interview(interview_id)
        conversation_history = convert_messages_to_conversation_history(messages)
        
        # Continue interview with context
        response = await self.agent.continue_interview(
            user_response=user_response,
            conversation_history=conversation_history,
            context=context,
            language=interview.language.value
        )
        
        # Save process references if any were identified
        if response.process_matches:
            for match in response.process_matches:
                await self.process_ref_repo.create(
                    interview_id=interview_id,
                    process_id=match.process_id,
                    is_new_process=match.is_new,
                    confidence_score=match.confidence
                )
        
        # Save messages
        # ... existing logic
```

## Data Models

### Enhanced Interview Response Models

```python
class ProcessMatchInfo(BaseModel):
    """Information about a matched process"""
    process_id: UUID
    process_name: str
    is_new: bool
    confidence: float
    reasoning: str

class InterviewResponse(BaseModel):
    """Enhanced response from interview agent"""
    question: str
    question_number: int
    is_final: bool
    context: InterviewContext
    process_matches: List[ProcessMatchInfo] = []  # NEW
    original_user_response: Optional[str] = None
    corrected_user_response: Optional[str] = None

class InterviewExportData(BaseModel):
    """Enhanced export data"""
    interview_id: str
    employee_id: str
    employee_name: str  # NEW
    organization_name: str  # NEW
    language: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    conversation: List[ConversationMessage]
    processes_referenced: List[ProcessMatchInfo] = []  # NEW
    context_used: InterviewContextData  # NEW
```

## Error Handling

### Error Scenarios and Handling

1. **Backend Service Unavailable**
   - Retry up to 2 times with exponential backoff
   - If all retries fail, proceed with minimal context
   - Log warning with details
   - Return partial context to agent

2. **Invalid Employee ID**
   - Return 404 error immediately
   - Do not create interview record
   - Log error with employee_id

3. **Process Matching Timeout**
   - Set timeout of 3 seconds for process matching
   - If timeout, skip process matching for this turn
   - Continue interview without match result
   - Log timeout event

4. **Database Connection Issues**
   - Existing error handling remains
   - Add retry logic for transient failures
   - Return 503 if database unavailable

5. **Context Cache Failures**
   - If cache read fails, fetch from source
   - If cache write fails, log warning and continue
   - Never block interview flow due to cache issues

## Testing Strategy

### Unit Tests

1. **Context Enrichment Service Tests**
   - Test employee context fetching
   - Test organization process fetching
   - Test interview history aggregation
   - Test caching behavior
   - Test error handling and fallbacks

2. **Process Matching Agent Tests**
   - Test exact process name matches
   - Test similar process name matches
   - Test no match scenarios
   - Test confidence scoring
   - Test multi-language support

3. **Prompt Builder Tests**
   - Test prompt generation with full context
   - Test prompt generation with minimal context
   - Test process list formatting
   - Test history formatting
   - Test token limit compliance

4. **Backend Client Tests**
   - Test successful API calls
   - Test retry logic
   - Test timeout handling
   - Test error response handling
   - Mock HTTP responses

### Integration Tests

1. **End-to-End Interview Flow**
   - Test start interview with context
   - Test continue interview with process matching
   - Test interview completion
   - Test export with process references

2. **Database Integration**
   - Test process reference creation
   - Test process reference queries
   - Test cascade deletes

3. **Backend Integration**
   - Test with real backend (in test environment)
   - Test with backend unavailable
   - Test with partial backend responses

### Performance Tests

1. **Context Loading Performance**
   - Measure time to load full context
   - Ensure under 2 seconds
   - Test with varying numbers of processes

2. **Process Matching Performance**
   - Measure time for process matching
   - Ensure under 1 second
   - Test with varying numbers of existing processes

3. **Cache Effectiveness**
   - Measure cache hit rates
   - Verify cache reduces backend calls
   - Test cache expiration

## Migration Strategy

### Database Migration

1. Create `interview_process_reference` table
2. Add indexes for performance
3. No changes to existing tables
4. Backward compatible

### Code Migration

1. **Phase 1**: Add new services without breaking existing code
   - Add ContextEnrichmentService
   - Add ProcessMatchingAgent
   - Add PromptBuilder
   - Keep existing agent service working

2. **Phase 2**: Enhance existing services
   - Update InterviewService to use context
   - Update agent_service to use new prompts
   - Add process matching logic

3. **Phase 3**: Update API endpoints
   - Add auth_token parameter to endpoints
   - Update response models
   - Maintain backward compatibility

### Rollout Plan

1. Deploy database migration
2. Deploy new services (inactive)
3. Enable context enrichment with feature flag
4. Monitor performance and errors
5. Enable process matching with feature flag
6. Full rollout after validation

## Performance Considerations

### Optimization Strategies

1. **Parallel Context Loading**
   - Fetch employee, organization, and processes in parallel
   - Use asyncio.gather() for concurrent requests
   - Reduce total context loading time

2. **Smart Caching**
   - Cache employee context for 5 minutes
   - Cache organization processes for 5 minutes
   - Invalidate cache on updates (if webhook available)

3. **Process List Limiting**
   - Limit to 20 most recent processes
   - Prioritize active processes
   - Sort by updated_at descending

4. **Lazy Process Matching**
   - Only invoke process matcher when needed
   - Detect process mentions with simple heuristics first
   - Skip matching if no processes exist

5. **Database Query Optimization**
   - Use selectinload for relationships
   - Add indexes on foreign keys
   - Use window functions for pagination

### Monitoring Metrics

1. Context loading time (target: < 2s)
2. Process matching time (target: < 1s)
3. Total interview start time (target: < 3s)
4. Backend API success rate
5. Cache hit rate
6. Process match accuracy (manual review)

## Security Considerations

1. **Authentication**
   - Pass JWT token to backend calls
   - Validate token before context loading
   - Ensure employee_id matches token claims

2. **Authorization**
   - Verify employee belongs to organization
   - Check permissions for process access
   - Validate interview ownership

3. **Data Privacy**
   - Do not log sensitive employee data
   - Sanitize process descriptions in logs
   - Respect data retention policies

4. **API Security**
   - Use HTTPS for backend calls
   - Implement rate limiting
   - Validate all backend responses

## Future Enhancements

1. **Real-time Process Updates**
   - WebSocket connection to backend
   - Live process list updates
   - Immediate cache invalidation

2. **Advanced Process Matching**
   - Use embeddings for semantic matching
   - Train custom model on process descriptions
   - Multi-process matching in single response

3. **Interview Analytics**
   - Track process discovery rates
   - Identify common processes across organizations
   - Generate insights from interview patterns

4. **Collaborative Interviews**
   - Multiple employees in same interview
   - Shared context across team
   - Consensus building features
