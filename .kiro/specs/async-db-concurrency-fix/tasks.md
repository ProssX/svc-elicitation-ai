# Implementation Plan
## iniciamos este spec para poder validar los test tests\integration\test_unchanged_endpoints.py (los mismos fallaban por concurrencia, y estos estaban hechos para validar lo que habiamos implementado antes, que era el tema de ... )
### Los test deben ser corridos teniendo en cuenta que necesitmamos un token JWT generado en el micro de auth, todo se encuentra levantado en docker.

- [x] 1. Create exception classes for interview operations




  - Create `InterviewError`, `InterviewNotFoundError`, and `InterviewAccessDeniedError` exception classes in `app/exceptions.py`
  - Add proper `__init__` methods with interview_id and employee_id parameters
  - _Requirements: 6.1, 6.2, 6.3_

- [x] 2. Enhance InterviewService with new methods and parameters





- [x] 2.1 Add allow_cross_user parameter to get_interview method


  - Modify `InterviewService.get_interview()` signature to include `allow_cross_user: bool = False`
  - Update method logic to skip employee_id validation when `allow_cross_user=True`
  - Raise `InterviewNotFoundError` when interview doesn't exist
  - Raise `InterviewAccessDeniedError` when user lacks permission
  - _Requirements: 1.1, 1.2, 1.3, 1.4_


- [x] 2.2 Implement get_interview_summary method

  - Create new `InterviewService.get_interview_summary()` method that returns interview without messages
  - Use same permission logic as `get_interview()` with `allow_cross_user` parameter
  - Return `InterviewSummary` model with basic interview data
  - _Requirements: 3.1, 3.2, 3.3, 3.4_


- [x] 2.3 Implement update_interview_status method

  - Create `InterviewService.update_interview_status()` method
  - Validate interview existence and ownership internally
  - Update status and return updated interview model
  - Raise appropriate exceptions for not found or access denied scenarios
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [ ] 3. Fix repository layer database concurrency issues






- [x] 3.1 Refactor get_by_organization to use sequential queries

  - Modify `InterviewRepository.get_by_organization()` to execute count and select queries sequentially
  - Add explicit `await` between queries
  - Consider using window function `func.count().over()` for single query solution
  - Test both approaches and choose most stable
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 3.2 Add database session flush calls where needed


  - Identify locations where multiple queries execute on same session
  - Add `await self.db.flush()` between queries to ensure completion
  - Verify no concurrent operations on same connection
  - _Requirements: 6.1, 6.2, 6.3, 6.4_
- [x] 4. Refactor export interview endpoint


- [ ] 4. Refactor export interview endpoint

- [x] 4.1 Remove direct database queries from export endpoint


  - Remove direct `db.execute(stmt)` calls from export_interview endpoint
  - Use `InterviewService.get_interview()` with `allow_cross_user` parameter
  - Handle `InterviewNotFoundError` and return 404 response
  - Handle `InterviewAccessDeniedError` and return 403 response
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 4.2 Implement centralized error handling for export endpoint


  - Add try-except block to catch interview exceptions
  - Return proper HTTP status codes (404, 403, 500)
  - Maintain ProssX error response format
  - _Requirements: 1.1, 8.1, 8.2, 8.3_

- [ ] 5. Refactor list interviews endpoint





- [x] 5.1 Update list endpoint to use refactored repository method


  - Ensure endpoint calls updated `get_by_organization()` method
  - Verify sequential query execution
  - Test with empty result sets
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 5.2 Add error handling for list interviews endpoint


  - Catch database errors and return 500 with proper error format
  - Ensure empty lists return 200 with proper pagination metadata
  - _Requirements: 2.3, 8.1, 8.2_
-

- [ ] 6. Refactor get interview by ID endpoint




- [x] 6.1 Replace direct queries with service method calls


  - Remove `db.execute(stmt)` from get_interview endpoint
  - Use `InterviewService.get_interview_summary()` method
  - Pass `allow_cross_user` based on user permissions
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 6.2 Implement proper error responses for get endpoint


  - Catch `InterviewNotFoundError` and return 404
  - Catch `InterviewAccessDeniedError` and return 403
  - Maintain consistent error response format
  - _Requirements: 3.1, 3.4, 8.2, 8.3_

- [ ] 7. Refactor update interview status endpoint





- [x] 7.1 Replace validation logic with service method


  - Remove direct database query for interview validation
  - Use `InterviewService.update_interview_status()` method
  - Handle exceptions and return appropriate status codes
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [x] 7.2 Add error handling for update endpoint


  - Return 404 for non-existent interviews
  - Return 403 for unauthorized access
  - Return 200 with updated data on success
  - _Requirements: 4.1, 4.4, 8.3, 8.4_
-

- [x] 8. Fix continue interview UUID validation



- [x] 8.1 Move UUID validation to Pydantic model


  - Update `ContinueInterviewRequest` model to use `UUID` type instead of `str`
  - Add `@validator` for interview_id field if needed
  - Ensure FastAPI returns 422 for invalid UUID format
  - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [x] 8.2 Remove manual UUID validation from endpoint


  - Remove try-except UUID validation block from continue_interview endpoint
  - Rely on Pydantic validation to reject invalid UUIDs
  - Verify 422 response is returned automatically
  - _Requirements: 5.1, 5.2, 5.3_

- [x] 9. Verify backward compatibility and integration tests




- [x] 9.1 Verify response format compatibility


  - Compare response JSON structure before and after changes
  - Ensure all fields in data objects remain unchanged
  - Verify meta and pagination structures are identical
  - Confirm error response format matches ProssX standard exactly
  - _Requirements: 8.1, 8.2, 8.3, 8.4_

- [x] 9.2 Run all integration tests and verify they pass





  - Execute `pytest tests/integration/test_unchanged_endpoints.py -v`
  - Verify all 8 tests pass without concurrency errors
  - Check that proper HTTP status codes are returned (404, 403, 422, 200)
  - Confirm no changes to response data structures
  - _Requirements: 8.1, 8.2, 8.3, 8.4_

- [ ]* 9.3 Add additional test cases for edge scenarios
  - Test admin user accessing other users' interviews
  - Test concurrent requests to same endpoint
  - Test invalid UUID formats return 422
  - Test non-existent interviews return 404
  - _Requirements: 1.4, 3.4, 4.4, 5.1_

- [ ] 10. Verify event loop stability and deployment readiness






- [x] 10.1 Verify test configuration

  - Confirm pytest.ini has `asyncio_mode = auto`
  - Verify conftest.py has proper event_loop fixture
  - Ensure all test methods are properly marked as async
  - _Requirements: 7.4, 8.1_

- [x] 10.2 Manual testing of critical endpoints



  - Test /start endpoint with real auth token
  - Test /continue endpoint with valid and invalid UUIDs
  - Test /export endpoint with non-existent interview
  - Test /interviews list endpoint
  - Verify all responses match expected format exactly
  - _Requirements: 8.1, 8.2, 8.3, 8.4_

- [ ]* 10.3 Load testing under concurrent requests
  - Run load tests with multiple concurrent requests
  - Monitor for "Event loop is closed" errors
  - Verify no asyncpg concurrency errors in logs
  - _Requirements: 7.1, 7.2, 7.3, 7.4_
