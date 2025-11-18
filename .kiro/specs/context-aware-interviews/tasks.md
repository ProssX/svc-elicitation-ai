# Implementation Plan

- [x] 1. Set up database schema for process references






  - Create migration file for `interview_process_reference` table with UUID primary key, foreign keys, and indexes
  - Add `InterviewProcessReference` model to `app/models/db_models.py` with relationships
  - Update `Interview` model to include `process_references` relationship
  - _Requirements: 9.1, 9.2_

- [x] 2. Create data models for context enrichment





  - [x] 2.1 Create `app/models/context.py` with context data models


    - Define `EmployeeContextData`, `RoleContextData`, `ProcessContextData` models
    - Define `InterviewHistorySummary` and `InterviewContextData` models
    - Add validation and serialization logic
    - _Requirements: 5.1, 1.1, 2.1_
  
  - [x] 2.2 Create process matching models


    - Define `ProcessMatchResult` model with confidence scoring
    - Define `ProcessMatchInfo` model for export data
    - Add to `app/models/interview.py`
    - _Requirements: 3.1, 3.5_
  
  - [x] 2.3 Enhance existing interview response models


    - Add `process_matches` field to `InterviewResponse`
    - Add `processes_referenced` and `context_used` to `InterviewExportData`
    - Maintain backward compatibility with optional fields
    - _Requirements: 7.1, 7.2, 7.5_

- [x] 3. Implement backend HTTP client





  - [x] 3.1 Create `app/clients/backend_client.py` with HTTP client class


    - Implement `get_employee()` method with retry logic
    - Implement `get_organization()` method
    - Implement `get_organization_processes()` method with pagination
    - Implement `get_employee_roles()` method
    - Add timeout handling (5 seconds) and exponential backoff retry
    - _Requirements: 5.2, 5.4, 10.2, 10.3_
  
  - [x] 3.2 Write unit tests for backend client


    - Test successful API calls with mocked responses
    - Test retry logic on failures
    - Test timeout handling
    - Test error response parsing
    - _Requirements: 5.4, 5.5_

- [x] 4. Implement context caching layer





  - [x] 4.1 Create `app/services/context_cache.py` with caching logic


    - Implement in-memory cache with TTL (5 minutes)
    - Add cache key generation for employee and organization data
    - Implement cache invalidation methods
    - Add cache hit/miss metrics logging
    - _Requirements: 5.3, 5.4_
  
  - [x] 4.2 Write unit tests for caching


    - Test cache storage and retrieval
    - Test TTL expiration
    - Test cache invalidation
    - Test concurrent access
    - _Requirements: 5.3_

- [x] 5. Implement context enrichment service





  - [x] 5.1 Create `app/services/context_enrichment_service.py`


    - Implement `get_full_interview_context()` method with parallel fetching
    - Implement `get_employee_context()` method
    - Implement `get_organization_processes()` method with filtering
    - Implement `get_interview_history_summary()` method
    - Add error handling with graceful degradation
    - Integrate caching layer
    - _Requirements: 1.1, 1.2, 2.1, 2.2, 4.1, 4.2, 5.1, 5.2, 5.4, 5.5_
  
  - [x] 5.2 Write unit tests for context enrichment


    - Test full context retrieval with all data available
    - Test partial context when backend unavailable
    - Test interview history aggregation
    - Test error handling and fallbacks
    - Test caching integration
    - _Requirements: 5.4, 5.5_

- [x] 6. Create process reference repository




  - [x] 6.1 Create `app/repositories/process_reference_repository.py`


    - Implement `create()` method for new process references
    - Implement `get_by_interview()` method
    - Implement `get_by_process()` method
    - Add unique constraint handling
    - _Requirements: 9.3, 9.4, 9.5_
  
  - [x] 6.2 Write unit tests for process reference repository


    - Test creating process references
    - Test querying by interview
    - Test querying by process
    - Test unique constraint violations
    - _Requirements: 9.3, 9.4, 9.5_

- [x] 7. Implement prompt builder service




  - [x] 7.1 Create `app/services/prompt_builder.py`


    - Implement `build_interview_prompt()` with context inclusion
    - Implement `format_process_list()` for existing processes
    - Implement `format_interview_history()` for history summary
    - Add multi-language support (es/en/pt)
    - Ensure prompts stay under 4000 tokens
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_
  
  - [x] 7.2 Implement process matching prompt builder

    - Implement `build_process_matching_prompt()` method
    - Add examples of process matching in prompts
    - Support multi-language matching instructions
    - _Requirements: 3.2, 6.4, 8.3_
  
  - [x] 7.3 Write unit tests for prompt builder


    - Test prompt generation with full context
    - Test prompt generation with minimal context
    - Test process list formatting
    - Test token limit compliance
    - Test multi-language support
    - _Requirements: 6.1, 6.5_

- [x] 8. Implement process matching agent




  - [x] 8.1 Create `app/services/process_matching_agent.py`


    - Implement `ProcessMatchingAgent` class with LLM integration
    - Implement `match_process()` method with confidence scoring
    - Implement `_build_matching_prompt()` for specialized prompts
    - Add multi-language support
    - Set timeout of 3 seconds for matching
    - _Requirements: 3.1, 3.2, 3.4, 8.1, 8.2, 8.3, 8.4_
  
  - [x] 8.2 Write unit tests for process matching agent


    - Test exact process name matches
    - Test similar process name matches
    - Test no match scenarios
    - Test confidence scoring accuracy
    - Test timeout handling
    - Test multi-language support
    - _Requirements: 3.1, 3.2, 3.4, 8.4_

- [ ] 9. Enhance interview agent service




  - [x] 9.1 Update `app/services/agent_service.py` to use context


    - Modify `start_interview()` to accept `InterviewContextData`
    - Modify `continue_interview()` to accept context and detect process mentions
    - Implement `_build_context_aware_prompt()` using PromptBuilder
    - Implement `_mentions_process()` heuristic detection
    - Integrate ProcessMatchingAgent for process matching
    - Add process match results to InterviewResponse
    - _Requirements: 1.3, 2.3, 3.1, 3.3, 6.1, 6.2, 8.5_
  
  - [x] 9.2 Write unit tests for enhanced agent service


    - Test interview start with enriched context
    - Test process mention detection
    - Test process matching integration
    - Test response with process match info
    - _Requirements: 1.3, 3.1, 3.3_

- [x] 10. Enhance interview service with context integration




  - [x] 10.1 Update `app/services/interview_service.py`


    - Modify `start_interview()` to fetch context before starting
    - Modify `continue_interview()` to load context and check process matches
    - Add process reference creation when matches found
    - Pass auth token to context service for backend calls
    - Add performance logging for context loading
    - _Requirements: 1.1, 1.2, 2.1, 3.3, 3.5, 9.3, 10.1, 10.5_
  
  - [x] 10.2 Write integration tests for interview service


    - Test start interview with context enrichment
    - Test continue interview with process matching
    - Test process reference creation
    - Test performance under 3 seconds
    - _Requirements: 10.1, 10.5_

- [x] 11. Update API endpoints to support context features





  - [x] 11.1 Update `app/routers/interviews.py` start endpoint


    - Extract auth token from request headers
    - Pass auth token to interview service
    - Update response to include context metadata
    - Add error handling for context loading failures
    - _Requirements: 1.1, 1.5_
  
  - [x] 11.2 Update continue endpoint


    - Extract auth token from request headers
    - Pass auth token to interview service
    - Include process match info in response
    - Handle process matching timeouts gracefully
    - _Requirements: 3.1, 3.3_
  
  - [x] 11.3 Update export endpoint


    - Include process references in export data
    - Include context used during interview
    - Add employee and organization names
    - Maintain backward compatibility
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_
  
  - [x] 11.4 Write API integration tests


    - Test start endpoint with context
    - Test continue endpoint with process matching
    - Test export endpoint with enhanced data
    - Test backward compatibility
    - _Requirements: 7.5_

- [x] 12. Add configuration and feature flags




  - [x] 12.1 Update `app/config.py` with new settings


    - Add `enable_context_enrichment` feature flag
    - Add `enable_process_matching` feature flag
    - Add `context_cache_ttl` setting
    - Add `process_matching_timeout` setting
    - Add `max_processes_in_context` setting
    - _Requirements: 2.4, 10.3_
  
  - [x] 12.2 Implement feature flag checks


    - Add conditional logic in interview service
    - Fallback to basic mode when flags disabled
    - Log feature flag states on startup
    - _Requirements: 5.4_

- [x] 13. Add monitoring and logging






  - [x] 13.1 Add performance metrics logging

    - Log context loading time
    - Log process matching time
    - Log total interview start time
    - Log backend API success/failure rates
    - Log cache hit/miss rates
    - _Requirements: 10.5_
  

  - [x] 13.2 Add error logging

    - Log backend integration errors with details
    - Log process matching failures
    - Log context loading failures
    - Ensure no sensitive data in logs
    - _Requirements: 5.5_

- [x] 14. Create database migration script






  - Create Alembic migration for `interview_process_reference` table
  - Test migration up and down
  - Verify indexes are created
  - Test on development database
  - _Requirements: 9.1, 9.2_

- [-] 15. Update documentation






  - [x] 15.1 Update API documentation



    - Document new response fields
    - Document context enrichment behavior
    - Document process matching feature
    - Add examples with process references
    - _Requirements: 7.5_
  
  - [x] 15.2 Create developer documentation


    - Document context enrichment architecture
    - Document process matching algorithm
    - Document caching strategy
    - Document feature flags
    - _Requirements: 5.1, 8.1_
  
  - [-] 15.3 Update README

    - Add context enrichment feature description
    - Add configuration instructions
    - Add troubleshooting guide
    - _Requirements: 5.1_

- [ ] 16. Performance optimization and testing
  - [ ] 16.1 Run performance tests
    - Measure context loading time (target < 2s)
    - Measure process matching time (target < 1s)
    - Measure total interview start time (target < 3s)
    - Test with varying numbers of processes
    - _Requirements: 10.1, 10.2, 10.3_
  
  - [ ] 16.2 Optimize based on results
    - Optimize slow queries
    - Adjust cache TTL if needed
    - Optimize process list limiting
    - _Requirements: 10.1, 10.2_
