# Implementation Plan

**IMPORTANT: ALL TASKS ARE FOR svc-elicitation-ai ONLY**

The Auth Service (svc-users-python) already has all necessary functionality including the JWKS endpoint at `/api/v1/auth/jwks`. DO NOT modify any files in svc-users-python. All implementation work is exclusively in the svc-elicitation-ai directory.

---

- [x] 1. Implement JWKS client in AI Service





  - Create `svc-elicitation-ai/app/services/jwks_client.py` with `JWKSClient` class
  - Implement `get_signing_key(kid: str)` method to fetch and cache public keys from existing Auth Service endpoint
  - Fetch JWKS from `${AUTH_SERVICE_URL}/api/v1/auth/jwks` (existing endpoint)
  - Implement in-memory cache with configurable TTL (default 3600 seconds)
  - Add automatic cache refresh logic on expiration
  - Implement fallback to stale cache when Auth Service unavailable
  - Add proper error handling for network failures and invalid JWKS format
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 4.1, 4.2, 4.3_

- [x] 2. Implement token validator in AI Service





  - Create `svc-elicitation-ai/app/services/token_validator.py` with `TokenValidator` class
  - Create `TokenPayload` dataclass for structured token claims
  - Implement `validate_token(token: str)` method using PyJWT library
  - Add validation for signature, expiration, issuer, and audience
  - Extract user claims (user_id, organization_id, roles, permissions) from token
  - Create custom exception classes (TokenExpiredError, TokenInvalidError, etc.)
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 3. Create authentication middleware in AI Service






  - Create `svc-elicitation-ai/app/middleware/auth_middleware.py` with `get_current_user` dependency
  - Extract Bearer token from Authorization header
  - Call token validator to verify token
  - Return TokenPayload for use in route handlers
  - Implement error responses for missing, expired, and invalid tokens (401)
  - Implement error response for auth service unavailable (503)
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 7.3_

- [x] 4. Update AI Service configuration





  - Add authentication settings to `svc-elicitation-ai/app/config.py` (auth_service_url, jwt_issuer, jwt_audience, jwks_cache_ttl)
  - Update `svc-elicitation-ai/.env.example` with new environment variables
  - Add validation for AUTH_SERVICE_URL (must be valid HTTP/HTTPS URL)
  - Add startup check to fail fast if AUTH_SERVICE_URL not configured
  - Configure JWKS URL as `${AUTH_SERVICE_URL}/api/v1/auth/jwks`
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 4.1_

- [x] 5. Update interview endpoints to use authentication




  - Add `current_user: TokenPayload = Depends(get_current_user)` to `/interviews/start` endpoint in `svc-elicitation-ai/app/routers/`
  - Add `current_user: TokenPayload = Depends(get_current_user)` to `/interviews/continue` endpoint
  - Add `current_user: TokenPayload = Depends(get_current_user)` to `/interviews/export` endpoint
  - Remove `user_id`, `organization_id`, and `role_id` fields from `StartInterviewRequest` model
  - Use `current_user.user_id` and `current_user.organization_id` from token instead of request body
  - Update context service calls to use authenticated user_id
  - Ensure health check endpoints remain unauthenticated
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 7.1, 7.2, 7.4, 7.5_

- [x] 6. Remove mock user system





  - Delete `svc-elicitation-ai/data/mock_users.json` file
  - Remove mock user loading logic from context service in `svc-elicitation-ai/app/services/`
  - Update context service to fetch real user data (or use token claims directly)
  - Remove any references to mock users in code and comments
  - _Requirements: 3.1_

- [x] 7. Add Python dependencies





  - Add `PyJWT[crypto]` to `svc-elicitation-ai/requirements.txt` for JWT validation
  - Add `cryptography` to `svc-elicitation-ai/requirements.txt` for RSA key handling
  - Add `httpx` to `svc-elicitation-ai/requirements.txt` for async HTTP requests to JWKS endpoint
  - Install dependencies in development environment
  - _Requirements: 1.2, 1.3, 2.1_

- [ ]* 8. Write unit tests for AI Service authentication components
  - Create `svc-elicitation-ai/tests/test_jwks_client.py` for JWKS client tests
  - Test fetching and parsing JWKS successfully from existing Auth Service endpoint
  - Test caching keys for TTL duration
  - Test refreshing keys after TTL expiration
  - Test handling network errors gracefully
  - Test using stale cache when service unavailable
  - Create `svc-elicitation-ai/tests/test_token_validator.py` for token validator tests
  - Test validating valid token successfully
  - Test rejecting expired token
  - Test rejecting token with invalid signature
  - Test rejecting token with wrong issuer/audience
  - Test extracting claims correctly
  - Create `svc-elicitation-ai/tests/test_auth_middleware.py` for middleware tests
  - Test allowing requests with valid token
  - Test rejecting requests without token (401)
  - Test rejecting requests with invalid token (401)
  - Test returning 503 when auth service unavailable
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4, 2.5, 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ]* 9. Write integration tests for end-to-end authentication flow
  - Create `svc-elicitation-ai/tests/integration/test_auth_flow.py`
  - Test login to existing Auth Service and obtain JWT token
  - Test calling AI Service with valid token (success)
  - Test calling AI Service without token (401)
  - Test calling AI Service with expired token (401)
  - Test calling AI Service with tampered token (401)
  - Test Auth Service unavailable with cached keys (success)
  - Test Auth Service unavailable without cached keys (503)
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 5.1, 5.2, 5.3, 5.4, 7.3_

- [x] 10. Update API documentation





  - Update OpenAPI/Swagger docs in `svc-elicitation-ai` to show authentication requirement
  - Add security scheme definition for Bearer token
  - Document which endpoints require authentication
  - Add examples of authentication error responses
  - Update `svc-elicitation-ai/README.md` with authentication setup instructions
  - Document how to obtain tokens from the existing Auth Service
  - _Requirements: 7.5_
