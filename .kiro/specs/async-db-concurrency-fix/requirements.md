# Requirements Document

## Introduction

This specification addresses critical database concurrency issues in the interview management endpoints. The system currently experiences asyncpg concurrency errors when multiple database operations attempt to execute on the same connection simultaneously. These errors manifest as "cannot perform operation: another operation is in progress" and "Event loop is closed" exceptions, causing endpoint failures and returning 200 OK responses instead of proper error codes (404, 422).

## Glossary

- **AsyncPG**: Asynchronous PostgreSQL database driver for Python
- **SQLAlchemy AsyncSession**: Async database session manager for SQLAlchemy ORM
- **Event Loop**: Python asyncio event loop that manages asynchronous operations
- **Database Concurrency**: Multiple database operations attempting to execute simultaneously on the same connection
- **Interview System**: The elicitation AI service that manages interview sessions
- **Endpoint**: HTTP API route that handles client requests

## Requirements

### Requirement 1: Fix Export Endpoint Database Concurrency

**User Story:** As a system administrator, I want the export endpoint to handle database queries correctly, so that non-existent interviews return 404 errors instead of 500 errors with concurrency exceptions.

#### Acceptance Criteria

1. WHEN a user requests to export a non-existent interview, THE Interview System SHALL return HTTP status code 404 with error message "Interview not found"
2. WHEN the export endpoint queries the database for interview existence, THE Interview System SHALL complete the query without triggering asyncpg concurrency errors
3. WHEN the export endpoint performs multiple database operations, THE Interview System SHALL execute them sequentially without overlapping transactions
4. IF an admin user exports any interview, THEN THE Interview System SHALL validate interview existence before attempting to load full interview data

### Requirement 2: Fix List Interviews Endpoint Database Concurrency

**User Story:** As a developer, I want the list interviews endpoint to execute count and select queries correctly, so that the endpoint returns successful responses instead of database concurrency errors.

#### Acceptance Criteria

1. WHEN a user requests the list of interviews, THE Interview System SHALL execute the count query and select query sequentially without concurrency conflicts
2. WHEN the list endpoint performs pagination queries, THE Interview System SHALL complete both count and data retrieval operations successfully
3. IF no interviews exist for a user, THEN THE Interview System SHALL return an empty list with status code 200 and proper pagination metadata
4. WHEN database queries execute in the list endpoint, THE Interview System SHALL not trigger "another operation is in progress" errors

### Requirement 3: Fix Get Interview By ID Endpoint Database Concurrency

**User Story:** As an API consumer, I want the get interview by ID endpoint to return proper 404 errors for non-existent interviews, so that I can distinguish between missing resources and server errors.

#### Acceptance Criteria

1. WHEN a user requests a non-existent interview by ID, THE Interview System SHALL return HTTP status code 404 with message "Interview not found"
2. WHEN the get interview endpoint queries for interview existence, THE Interview System SHALL complete the database operation without asyncpg interface errors
3. WHEN checking interview ownership, THE Interview System SHALL execute database queries sequentially to avoid concurrency conflicts
4. IF an interview exists but belongs to another user, THEN THE Interview System SHALL return 403 Forbidden without database concurrency errors

### Requirement 4: Fix Update Interview Status Endpoint Database Concurrency

**User Story:** As a system user, I want the update interview status endpoint to handle non-existent interviews correctly, so that I receive proper 404 errors instead of database concurrency exceptions.

#### Acceptance Criteria

1. WHEN a user attempts to update a non-existent interview status, THE Interview System SHALL return HTTP status code 404 with error message "Interview not found"
2. WHEN the update endpoint validates interview existence, THE Interview System SHALL complete database queries without triggering asyncpg concurrency errors
3. WHEN updating interview status, THE Interview System SHALL execute validation and update operations sequentially
4. IF the interview exists and update succeeds, THEN THE Interview System SHALL return status code 200 with updated interview data

### Requirement 5: Fix Continue Interview Endpoint UUID Validation

**User Story:** As an API consumer, I want invalid UUID formats to be rejected with 422 validation errors, so that I receive immediate feedback on malformed requests.

#### Acceptance Criteria

1. WHEN a user sends an invalid UUID format in the continue interview request, THE Interview System SHALL return HTTP status code 422 with validation error details
2. WHEN UUID validation fails, THE Interview System SHALL not attempt database queries
3. WHEN the continue endpoint receives "invalid-uuid" as interview_id, THE Interview System SHALL return validation error before any database operations
4. IF UUID validation passes but interview doesn't exist, THEN THE Interview System SHALL return 404 without concurrency errors

### Requirement 6: Ensure Proper Async Database Session Management

**User Story:** As a backend developer, I want all database operations to use async sessions correctly, so that the system avoids event loop and concurrency issues.

#### Acceptance Criteria

1. WHEN any endpoint performs database operations, THE Interview System SHALL use the async session provided by FastAPI dependency injection
2. WHEN multiple queries are needed in a single endpoint, THE Interview System SHALL execute them sequentially using await
3. WHEN an endpoint completes or encounters an error, THE Interview System SHALL properly close or rollback the database session
4. WHILE a database transaction is active, THE Interview System SHALL not attempt to start another transaction on the same connection

### Requirement 7: Prevent Event Loop Closure During Database Operations

**User Story:** As a system operator, I want database operations to complete successfully without event loop closure errors, so that the system remains stable under load.

#### Acceptance Criteria

1. WHEN database operations execute, THE Interview System SHALL maintain an active event loop throughout the operation
2. WHEN asyncpg attempts to send data, THE Interview System SHALL ensure the event loop proactor is available
3. IF an event loop closes prematurely, THEN THE Interview System SHALL log the error and return a proper 500 error response
4. WHEN tests execute, THE Interview System SHALL use properly configured async test clients that maintain event loop state

### Requirement 8: Maintain Backward Compatibility with Existing Tests

**User Story:** As a QA engineer, I want all existing integration tests to pass after the fixes, so that I can verify the system works correctly.

#### Acceptance Criteria

1. WHEN integration tests execute, THE Interview System SHALL pass all test cases that previously passed
2. WHEN tests check for 404 responses, THE Interview System SHALL return 404 instead of 200 with error payloads
3. WHEN tests validate error response formats, THE Interview System SHALL return consistent ProssX error format
4. IF a test expects a specific HTTP status code, THEN THE Interview System SHALL return that exact status code
