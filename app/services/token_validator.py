"""
Token Validator for JWT authentication
Validates JWT tokens using JWKS public keys and extracts user claims
"""
import logging
from dataclasses import dataclass
from typing import Optional
import jwt
from jwt.exceptions import (
    ExpiredSignatureError,
    InvalidTokenError,
    InvalidSignatureError,
    DecodeError,
    InvalidIssuerError,
    InvalidAudienceError,
    MissingRequiredClaimError
)

from .jwks_client import JWKSClient, KeyNotFoundError, JWKSFetchError


logger = logging.getLogger(__name__)


# Custom exception classes
class AuthenticationError(Exception):
    """Base exception for authentication errors"""
    pass


class TokenExpiredError(AuthenticationError):
    """Token has expired"""
    pass


class TokenInvalidError(AuthenticationError):
    """Token signature or format invalid"""
    pass


class TokenMissingClaimsError(AuthenticationError):
    """Required claims missing from token"""
    pass


@dataclass
class TokenPayload:
    """
    Structured representation of JWT token claims
    
    Attributes:
        user_id: User identifier from 'sub' claim
        organization_id: Organization identifier from 'organizationId' claim
        email: User email (optional, from custom claim)
        roles: List of user roles from 'roles' claim
        permissions: List of user permissions from 'permissions' claim
        issued_at: Token issued timestamp from 'iat' claim
        expires_at: Token expiration timestamp from 'exp' claim
    """
    user_id: str
    organization_id: str
    email: Optional[str]
    roles: list[str]
    permissions: list[str]
    issued_at: int
    expires_at: int
    
    def has_permission(self, permission: str) -> bool:
        """
        Check if user has a specific permission
        
        Args:
            permission: Permission string to check (e.g., "interviews:create")
            
        Returns:
            bool: True if user has the permission, False otherwise
        """
        return permission in self.permissions
    
    def has_any_permission(self, permissions: list[str]) -> bool:
        """
        Check if user has any of the specified permissions (OR logic)
        
        Args:
            permissions: List of permission strings to check
            
        Returns:
            bool: True if user has at least one of the permissions, False otherwise
        """
        return any(perm in self.permissions for perm in permissions)
    
    def has_all_permissions(self, permissions: list[str]) -> bool:
        """
        Check if user has all of the specified permissions (AND logic)
        
        Args:
            permissions: List of permission strings to check
            
        Returns:
            bool: True if user has all of the permissions, False otherwise
        """
        return all(perm in self.permissions for perm in permissions)


class TokenValidator:
    """
    Validates JWT tokens and extracts claims
    
    Uses JWKS client to fetch public keys for signature verification.
    Validates token signature, expiration, issuer, and audience.
    """
    
    def __init__(self, jwks_client: JWKSClient, issuer: str, audience: str):
        """
        Initialize token validator
        
        Args:
            jwks_client: JWKS client for fetching public keys
            issuer: Expected token issuer (iss claim)
            audience: Expected token audience (aud claim)
        """
        self.jwks_client = jwks_client
        self.issuer = issuer
        self.audience = audience
        
        logger.info(
            f"Initialized TokenValidator with issuer: {issuer}, audience: {audience}"
        )
    
    async def validate_token(self, token: str) -> TokenPayload:
        """
        Validate JWT token and extract payload
        
        Performs the following validations:
        1. Extracts key ID (kid) from JWT header
        2. Fetches public key from JWKS client
        3. Verifies signature using PyJWT library
        4. Validates issuer, audience, and expiration
        5. Extracts and structures claims into TokenPayload
        
        Args:
            token: JWT token string (without "Bearer " prefix)
            
        Returns:
            TokenPayload with user_id, email, roles, permissions
            
        Raises:
            TokenExpiredError: Token has expired
            TokenInvalidError: Invalid signature or format
            TokenMissingClaimsError: Required claims missing
        """
        try:
            # Step 1: Decode header to get key ID (kid)
            try:
                unverified_header = jwt.get_unverified_header(token)
            except DecodeError as e:
                logger.error(f"Failed to decode JWT header: {str(e)}")
                raise TokenInvalidError("Invalid token format") from e
            
            kid = unverified_header.get("kid")
            if not kid:
                logger.error("Token header missing 'kid' field")
                raise TokenInvalidError("Token missing key ID")
            
            logger.debug(f"Validating token with kid: {kid}")
            
            # Step 2: Fetch public key from JWKS client
            try:
                public_key = await self.jwks_client.get_signing_key(kid)
            except KeyNotFoundError as e:
                logger.error(f"Key not found: {str(e)}")
                raise TokenInvalidError(f"Unknown key ID: {kid}") from e
            except JWKSFetchError as e:
                logger.error(f"Failed to fetch JWKS: {str(e)}")
                raise TokenInvalidError("Unable to verify token signature") from e
            
            # Step 3: Verify signature and decode token
            try:
                payload = jwt.decode(
                    token,
                    public_key,
                    algorithms=["RS256"],
                    issuer=self.issuer,
                    audience=self.audience,
                    options={
                        "verify_signature": True,
                        "verify_exp": True,
                        "verify_iat": True,
                        "verify_iss": True,
                        "verify_aud": True,
                        "require": ["sub", "iat", "exp", "iss", "aud"]
                    }
                )
            except ExpiredSignatureError as e:
                logger.warning(f"Token expired: {str(e)}")
                raise TokenExpiredError("Token has expired") from e
            except InvalidSignatureError as e:
                logger.error(f"Invalid token signature: {str(e)}")
                raise TokenInvalidError("Token signature verification failed") from e
            except InvalidIssuerError as e:
                logger.error(f"Invalid issuer: {str(e)}")
                raise TokenInvalidError(f"Invalid token issuer") from e
            except InvalidAudienceError as e:
                logger.error(f"Invalid audience: {str(e)}")
                raise TokenInvalidError(f"Invalid token audience") from e
            except MissingRequiredClaimError as e:
                logger.error(f"Missing required claim: {str(e)}")
                raise TokenMissingClaimsError(f"Token missing required claims") from e
            except InvalidTokenError as e:
                logger.error(f"Invalid token: {str(e)}")
                raise TokenInvalidError("Invalid token") from e
            
            # Step 4: Extract and validate required claims
            try:
                token_payload = self._extract_claims(payload)
                logger.info(
                    f"Successfully validated token for user: {token_payload.user_id}"
                )
                return token_payload
            except KeyError as e:
                logger.error(f"Missing required claim in payload: {str(e)}")
                raise TokenMissingClaimsError(
                    f"Token missing required claim: {str(e)}"
                ) from e
            except Exception as e:
                logger.error(f"Failed to extract claims: {str(e)}")
                raise TokenInvalidError("Invalid token payload") from e
        
        except (TokenExpiredError, TokenInvalidError, TokenMissingClaimsError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Catch any unexpected errors
            logger.error(f"Unexpected error validating token: {str(e)}")
            raise TokenInvalidError("Token validation failed") from e
    
    def _extract_claims(self, payload: dict) -> TokenPayload:
        """
        Extract and structure claims from JWT payload
        
        Args:
            payload: Decoded JWT payload dictionary
            
        Returns:
            TokenPayload with structured claims
            
        Raises:
            KeyError: If required claims are missing
        """
        from app.models.permissions import InterviewPermission
        
        # Extract required claims
        user_id = payload["sub"]
        organization_id = payload.get("organizationId")
        
        # Validate organization_id is present
        if not organization_id:
            raise KeyError("organizationId")
        
        # Extract optional email
        email = payload.get("email")
        
        # Extract roles (default to empty list if not present)
        roles = payload.get("roles", [])
        if not isinstance(roles, list):
            logger.warning(f"Invalid roles format, expected list: {roles}")
            roles = []
        
        # Extract permissions (default to empty list if not present)
        permissions = payload.get("permissions", [])
        
        # Validate permissions format
        if not isinstance(permissions, list):
            logger.warning(
                f"Invalid permissions format in JWT for user {user_id}: "
                f"expected list, got {type(permissions).__name__}"
            )
            permissions = []
        
        # Log warning if JWT doesn't contain permissions field
        if "permissions" not in payload:
            logger.warning(
                f"JWT for user {user_id} does not contain 'permissions' field. "
                f"Assuming empty permissions array."
            )
        
        # Filter out invalid permissions using InterviewPermission.is_valid()
        valid_permissions = []
        invalid_permissions = []
        
        for perm in permissions:
            if not isinstance(perm, str):
                invalid_permissions.append(perm)
                continue
            
            if InterviewPermission.is_valid(perm):
                valid_permissions.append(perm)
            else:
                invalid_permissions.append(perm)
        
        # Log warning if invalid permissions were found
        if invalid_permissions:
            logger.warning(
                f"JWT for user {user_id} contains invalid permissions: {invalid_permissions}. "
                f"Valid permissions: {valid_permissions}"
            )
        
        # Extract timestamps
        issued_at = payload["iat"]
        expires_at = payload["exp"]
        
        return TokenPayload(
            user_id=user_id,
            organization_id=organization_id,
            email=email,
            roles=roles,
            permissions=valid_permissions,
            issued_at=issued_at,
            expires_at=expires_at
        )
