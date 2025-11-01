# Design Document

## Overview

This design addresses critical asyncpg concurrency issues in the interview management API endpoints. The root cause is multiple database operations attempting to execute on the same async connection simultaneously, violating asyncpg's single-operation-per-connection constraint. The solution involves refactoring endpoints to execute database queries sequentially and ensuring proper async/await patterns throughout the codebase.

## Architecture

### Current Architecture Issues

The current implementation has several architectural problems:

1. **Redundant Database Queries**: Endpoints perform duplicate queries - first checking existence, then loading full data
2. **Concurrent Query Execution**: Multiple queries attempt to execute on the same connection without proper sequencing
3. **Improper Error Handling**: Database errors are caught but return 200 OK with error payloads instead of proper HTTP status codes
4. **Event Loop Management**: Tests and production code have different event loop lifecycles causing closure issues

### Proposed Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Endpoint                         │
│  - Receives HTTP Request                                     │
│  - Validates Input (UUID, permissions)                       │
│  - Gets AsyncSession from dependency injection               │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  Interview Service Layer                     │
│  - Single entry point for data access                        │
│  - Handles all database operations sequentially              │
│  - Returns domain objects or raises exceptions               │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                Repository Layer (Existing)                   │
│  - Executes individual database queries                      │
│  - Uses provided AsyncSession                                │
│  - No concurrent operations on same session                  │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. Export Interview Endpoint Refactoring

**Current Problem:**
```python
# Line 1376: Direct database query
stmt = select(InterviewModel).where(...)
result = await db.execute(stmt)  # First query

# Line 1386: Service call that does another query
interview_with_messages = await interview_service.get_interview(...)  # Second query on same session
```

**Solution Design:**
```python
# Use service layer exclusively - single query path
try:
    interview_with_messages = await interview_service.get_interview(
        interview_id=interview_uuid,
        employee_id=employee_id,
        allow_cross_user=has_read_all  # New parameter for admin access
    )
except InterviewNotFoundError:
    return error_response(
        message="Interview not found",
        code=404,
        errors=[{"field": "interview_id", "error": "Interview does not exist"}]
    )
```

**Interface Changes:**
- Add `allow_cross_user: bool = False` parameter to `InterviewService.get_interview()`
- Service method handles both ownership validation and data retrieval in single query
- Raises `InterviewNotFoundError` for missing interviews
- Raises `InterviewAccessDeniedError` for permission issues

### 2. List Interviews Endpoint Refactoring

**Current Problem:**
```python
# Repository performs count and select separately
count_result = await self.db.execute(count_stmt)  # First query
result = await self.db.execute(stmt)  # Second query - causes concurrency error
```

**Solution Design:**
```python
# Use window function to get count and data in single query
stmt = select(
    InterviewModel,
    func.count().over().label('total_count')
).where(...)

result = await self.db.execute(stmt)
rows = result.all()

if rows:
    total_count = rows[0].total_count
    interviews = [row.Interview for row in rows]
else:
    total_count = 0
    interviews = []
```

**Alternative Solution (if window functions cause issues):**
```python
# Execute queries sequentially with explicit await
count_result = await self.db.execute(count_stmt)
total_count = count_result.scalar()

# Ensure first query completes before second
await self.db.flush()  # Force completion

result = await self.db.execute(stmt)
interviews = result.scalars().all()
```

### 3. Get Interview By ID Endpoint Refactoring

**Current Problem:**
```python
# Line 935: Direct query in endpoint
stmt = select(InterviewModel).where(...)
result = await db.execute(stmt)  # Concurrent with other operations
```

**Solution Design:**
```python
# Use service layer method that already handles this
try:
    interview_data = await interview_service.get_interview_summary(
        interview_id=interview_uuid,
        employee_id=UUID(current_user.user_id),
        allow_cross_user=has_read_all
    )
    return success_response(data=interview_data.model_dump(), ...)
except InterviewNotFoundError:
    return error_response(message="Interview not found", code=404, ...)
except InterviewAccessDeniedError:
    return error_response(message="Access denied", code=403, ...)
```

### 4. Update Interview Status Endpoint Refactoring

**Current Problem:**
```python
# Line 1122: Direct query before service call
stmt = select(InterviewModel).where(...)
result = await db.execute(stmt)  # Redundant query
```

**Solution Design:**
```python
# Service method handles validation internally
try:
    updated_interview = await interview_service.update_interview_status(
        interview_id=interview_uuid,
        employee_id=UUID(current_user.user_id),
        new_status=request.status,
        allow_cross_user=has_read_all
    )
    return success_response(data=updated_interview.model_dump(), ...)
except InterviewNotFoundError:
    return error_response(message="Interview not found", code=404, ...)
except InterviewAccessDeniedError:
    return error_response(message="Access denied", code=403, ...)
```

### 5. Continue Interview UUID Validation

**Current Problem:**
```python
# Validation happens after database operations start
try:
    interview_uuid = UUID(request.interview_id)
except ValueError:
    return error_response(...)  # But returns 200 instead of 422
```

**Solution Design:**
```python
# Pydantic validation at request model level
class ContinueInterviewRequest(BaseModel):
    interview_id: UUID  # Pydantic validates UUID format automatically
    user_response: str = Field(min_length=1, max_length=5000)
    language: Literal["es", "en", "pt"]
    
    @validator('interview_id')
    def validate_uuid_format(cls, v):
        if not isinstance(v, UUID):
            raise ValueError('Invalid UUID format')
        return v
```

## Data Models

### New Service Method Signatures

```python
class InterviewService:
    async def get_interview(
        self,
        interview_id: UUID,
        employee_id: UUID,
        allow_cross_user: bool = False
    ) -> InterviewWithMessages:
        """
        Get interview with messages. Raises InterviewNotFoundError if not found.
        If allow_cross_user=False, raises InterviewAccessDeniedError if employee_id doesn't match.
        """
        
    async def get_interview_summary(
        self,
        interview_id: UUID,
        employee_id: UUID,
        allow_cross_user: bool = False
    ) -> InterviewSummary:
        """
        Get interview summary without messages. Raises exceptions like get_interview.
        """
        
    async def update_interview_status(
        self,
        interview_id: UUID,
        employee_id: UUID,
        new_status: InterviewStatusEnum,
        allow_cross_user: bool = False
    ) -> Interview:
        """
        Update interview status. Validates ownership and existence internally.
        """
```

### Exception Hierarchy

```python
class InterviewError(Exception):
    """Base exception for interview operations"""
    pass

class InterviewNotFoundError(InterviewError):
    """Raised when interview doesn't exist"""
    def __init__(self, interview_id: UUID):
        self.interview_id = interview_id
        super().__init__(f"Interview {interview_id} not found")

class InterviewAccessDeniedError(InterviewError):
    """Raised when user doesn't have permission"""
    def __init__(self, interview_id: UUID, employee_id: UUID):
        self.interview_id = interview_id
        self.employee_id = employee_id
        super().__init__(f"User {employee_id} cannot access interview {interview_id}")
```

## Error Handling

### Centralized Error Handler

```python
# In app/routers/interviews.py or app/exceptions.py

def handle_interview_error(error: Exception) -> JSONResponse:
    """Convert interview exceptions to proper HTTP responses"""
    if isinstance(error, InterviewNotFoundError):
        return error_response(
            message="Interview not found",
            code=404,
            errors=[{
                "field": "interview_id",
                "error": "Interview does not exist"
            }]
        )
    elif isinstance(error, InterviewAccessDeniedError):
        return error_response(
            message="Access denied",
            code=403,
            errors=[{
                "field": "interview_id",
                "error": "You don't have permission to access this interview"
            }]
        )
    else:
        # Log unexpected errors
        logger.error(f"Unexpected error: {error}", exc_info=True)
        return error_response(
            message="Internal server error",
            code=500,
            errors=[{"field": "general", "error": str(error)}]
        )
```

### Endpoint Error Handling Pattern

```python
@router.get("/{interview_id}")
async def get_interview(
    interview_id: str,
    current_user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(InterviewPermission.READ))
):
    try:
        # Validate UUID format
        try:
            interview_uuid = UUID(interview_id)
        except ValueError:
            return error_response(
                message="Validation error",
                code=422,
                errors=[{"field": "interview_id", "error": "Invalid UUID format"}]
            )
        
        # Business logic
        interview_service = InterviewService(db)
        has_read_all = current_user.has_permission(InterviewPermission.READ_ALL)
        
        interview_data = await interview_service.get_interview_summary(
            interview_id=interview_uuid,
            employee_id=UUID(current_user.user_id),
            allow_cross_user=has_read_all
        )
        
        return success_response(data=interview_data.model_dump())
        
    except (InterviewNotFoundError, InterviewAccessDeniedError) as e:
        return handle_interview_error(e)
    except Exception as e:
        return handle_interview_error(e)
```

## Testing Strategy

### Unit Tests

1. **Service Layer Tests**: Test new service methods with mocked repositories
2. **Exception Tests**: Verify correct exceptions are raised for various scenarios
3. **Validation Tests**: Test UUID validation at Pydantic model level

### Integration Tests

1. **Endpoint Tests**: Verify correct HTTP status codes (404, 403, 422, 200)
2. **Concurrency Tests**: Ensure no asyncpg concurrency errors occur
3. **Error Format Tests**: Validate ProssX error response format
4. **Permission Tests**: Test admin vs regular user access patterns

### Test Configuration

```python
# tests/conftest.py - ensure proper async setup
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for entire test session"""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture
async def client():
    """Async test client with proper event loop"""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
```

## Implementation Plan

### Phase 1: Service Layer Enhancements
1. Add `allow_cross_user` parameter to existing service methods
2. Implement new exception classes
3. Add `get_interview_summary()` method
4. Add `update_interview_status()` method

### Phase 2: Repository Layer Optimization
1. Refactor `get_by_organization()` to use window function or sequential queries
2. Ensure all repository methods use single query where possible
3. Add explicit `await` and `flush()` calls where needed

### Phase 3: Endpoint Refactoring
1. Remove direct database queries from endpoints
2. Use service layer methods exclusively
3. Implement centralized error handling
4. Add proper try-except blocks

### Phase 4: Validation Improvements
1. Move UUID validation to Pydantic models
2. Add field validators for all request models
3. Ensure 422 responses for validation errors

### Phase 5: Testing
1. Update integration tests to use async client
2. Add new test cases for error scenarios
3. Verify all tests pass
4. Add concurrency stress tests

## Performance Considerations

### Query Optimization

- **Before**: 2-3 queries per endpoint (existence check + data load + optional permission check)
- **After**: 1 query per endpoint (combined existence + data load with permission filter)
- **Expected Improvement**: 50-66% reduction in database round trips

### Connection Pool Management

- Maintain existing connection pool settings
- No changes needed to `app/database.py` configuration
- Async session lifecycle managed by FastAPI dependency injection

### Caching Strategy (Future Enhancement)

Consider adding Redis caching for:
- Interview existence checks
- User permission lookups
- Frequently accessed interview summaries

## Backward Compatibility

**CRITICAL**: All changes must maintain 100% backward compatibility with existing frontend code.

### Response Format Preservation

1. **Success Responses**: Keep exact same structure
   ```json
   {
     "status": "success",
     "code": 200,
     "message": "...",
     "data": { ... },
     "errors": null,
     "meta": { ... }
   }
   ```

2. **Error Responses**: Maintain ProssX format exactly
   ```json
   {
     "status": "error",
     "code": 404,
     "message": "Interview not found",
     "errors": [{"field": "interview_id", "error": "..."}],
     "meta": { ... }
   }
   ```

3. **Data Structure**: No changes to data field structure
   - Interview objects keep same fields
   - Pagination metadata unchanged
   - Meta information preserved

### Endpoint Behavior Preservation

1. **Export Endpoint**: Same response structure, only fix error codes (200→404)
2. **List Endpoint**: Same pagination and data format
3. **Get By ID**: Same interview data structure
4. **Update Status**: Same response format
5. **Continue Interview**: Same question/response format

### What Changes (Internal Only)

- ✅ Database query execution order (sequential instead of concurrent)
- ✅ Error handling logic (proper exceptions)
- ✅ HTTP status codes (404 instead of 200 with errors)
- ❌ Response JSON structure (NO CHANGES)
- ❌ Field names or types (NO CHANGES)
- ❌ Endpoint URLs or methods (NO CHANGES)

## Security Considerations

1. **Permission Validation**: Always validate permissions before data access
2. **SQL Injection**: Use parameterized queries (already implemented via SQLAlchemy)
3. **Information Disclosure**: Return generic 404 for both non-existent and unauthorized interviews (configurable)
4. **Audit Logging**: Log all access denied attempts for security monitoring

## Rollback Plan

If issues arise after deployment:

1. **Immediate**: Revert to previous version via Docker image rollback
2. **Database**: No schema changes, so no database rollback needed
3. **Monitoring**: Watch for increased 500 errors or response time degradation
4. **Gradual Rollout**: Deploy to staging first, then production with canary deployment

## Success Metrics

- ✅ Zero asyncpg concurrency errors in production logs
- ✅ All integration tests passing (8/8)
- ✅ Correct HTTP status codes (404, 403, 422) returned
- ✅ Response time improvement of 20-30% due to reduced queries
- ✅ No increase in 500 error rate
