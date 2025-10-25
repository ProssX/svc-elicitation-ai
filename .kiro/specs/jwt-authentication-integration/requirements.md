# Requirements Document

## Introduction

This document specifies the requirements for integrating JWT-based authentication from the svc-users-python microservice into the svc-elicitation-ai microservice. The integration will replace the current mock user system with real JWT token validation using JWKS (JSON Web Key Set), enabling secure authentication and role-based access control (RBAC) for the AI elicitation service.

**IMPORTANT:** The Auth Service (svc-users-python) already has all necessary functionality including the JWKS endpoint at `/api/v1/auth/jwks`. This integration work is EXCLUSIVELY focused on the AI Service (svc-elicitation-ai). NO modifications should be made to svc-users-python.

## Glossary

- **Auth Service**: The svc-users-python microservice that generates and manages JWT tokens with RS256 signing
- **AI Service**: The svc-elicitation-ai microservice that conducts requirements elicitation interviews
- **JWT**: JSON Web Token, a secure token format for authentication
- **JWKS**: JSON Web Key Set, a set of public keys used to verify JWT signatures
- **RBAC**: Role-Based Access Control, a permission system based on user roles
- **RS256**: RSA Signature with SHA-256, an asymmetric signing algorithm
- **Bearer Token**: An authentication token passed in the HTTP Authorization header
- **Token Validation**: The process of verifying a JWT's signature, expiration, and claims

## Requirements

### Requirement 1

**User Story:** As an AI Service, I want to validate JWT tokens from the Auth Service, so that I can authenticate users without direct database access

#### Acceptance Criteria

1. WHEN the AI Service receives a request with a Bearer token, THE AI Service SHALL extract the token from the Authorization header
2. THE AI Service SHALL fetch the JWKS public keys from the Auth Service endpoint
3. WHEN validating a token, THE AI Service SHALL verify the token signature using the JWKS public key
4. IF the token signature is invalid, THEN THE AI Service SHALL return a 401 Unauthorized response
5. WHEN the token is valid, THE AI Service SHALL extract user claims including user_id, email, and roles

### Requirement 2

**User Story:** As an AI Service, I want to cache JWKS public keys, so that I can validate tokens efficiently without fetching keys on every request

#### Acceptance Criteria

1. THE AI Service SHALL cache JWKS public keys in memory with a configurable TTL (time-to-live)
2. WHEN the cache expires, THE AI Service SHALL refresh the JWKS keys from the Auth Service
3. IF fetching JWKS keys fails, THEN THE AI Service SHALL use cached keys if available
4. THE AI Service SHALL log warnings when using stale cached keys
5. THE AI Service SHALL provide a configuration option for JWKS cache TTL with a default of 3600 seconds

### Requirement 3

**User Story:** As an AI Service, I want to replace mock users with authenticated users, so that interviews are associated with real user accounts

#### Acceptance Criteria

1. THE AI Service SHALL remove the mock_users.json file and related mock user logic
2. WHEN creating an interview, THE AI Service SHALL use the authenticated user_id from the JWT token
3. THE AI Service SHALL store the user_id in the interview data model
4. WHEN retrieving interviews, THE AI Service SHALL filter results by the authenticated user_id
5. THE AI Service SHALL ensure users can only access their own interviews

### Requirement 4

**User Story:** As an AI Service, I want to consume the existing JWKS endpoint from the Auth Service, so that I can validate JWT tokens independently

**Note:** The Auth Service (svc-users-python) already has a functional JWKS endpoint at `/api/v1/auth/jwks`. This requirement is about consuming that existing endpoint, NOT creating a new one.

#### Acceptance Criteria

1. THE AI Service SHALL fetch JWKS from the Auth Service endpoint at `/api/v1/auth/jwks`
2. THE AI Service SHALL parse the public key from JWK format
3. THE AI Service SHALL use the key ID (kid) from the JWKS response to match with JWT header
4. THE AI Service SHALL handle CORS appropriately when making cross-origin requests
5. THE AI Service SHALL not require any modifications to the Auth Service JWKS endpoint

### Requirement 5

**User Story:** As a developer, I want the AI Service to handle authentication errors gracefully, so that users receive clear error messages

#### Acceptance Criteria

1. WHEN a token is missing, THE AI Service SHALL return a 401 response with message "Authentication required"
2. WHEN a token is expired, THE AI Service SHALL return a 401 response with message "Token expired"
3. WHEN a token signature is invalid, THE AI Service SHALL return a 401 response with message "Invalid token"
4. WHEN the JWKS endpoint is unreachable, THE AI Service SHALL return a 503 response with message "Authentication service unavailable"
5. THE AI Service SHALL log all authentication failures with relevant details for debugging

### Requirement 6

**User Story:** As a system administrator, I want to configure the Auth Service URL, so that the AI Service can connect to different environments

#### Acceptance Criteria

1. THE AI Service SHALL read the Auth Service URL from an environment variable AUTH_SERVICE_URL
2. THE AI Service SHALL construct the JWKS endpoint URL by appending /.well-known/jwks.json to the base URL
3. IF the AUTH_SERVICE_URL is not configured, THEN THE AI Service SHALL fail to start with a clear error message
4. THE AI Service SHALL validate that the AUTH_SERVICE_URL is a valid HTTP/HTTPS URL
5. THE AI Service SHALL support both HTTP (development) and HTTPS (production) protocols

### Requirement 7

**User Story:** As an API consumer, I want protected endpoints to require authentication, so that unauthorized users cannot access sensitive operations

#### Acceptance Criteria

1. THE AI Service SHALL protect all interview endpoints with JWT authentication
2. THE AI Service SHALL allow health check endpoints to remain unauthenticated
3. WHEN an unauthenticated request is made to a protected endpoint, THE AI Service SHALL return a 401 response
4. THE AI Service SHALL apply authentication middleware globally to all protected routes
5. THE AI Service SHALL document which endpoints require authentication in the API documentation
