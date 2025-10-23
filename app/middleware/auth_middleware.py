"""
Authentication Middleware
Provides JWT token validation for protected endpoints
"""
import logging
from typing import Optional
from fastapi import Header, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.services.token_validator import (
    TokenValidator,
    TokenPayload,
    TokenExpiredError,
    TokenInvalidError,
    TokenMissingClaimsError,
    AuthenticationError
)
from app.services.jwks_client import JWKSClient, JWKSFetchError
from app.config import settings


logger = logging.getLogger(__name__)

# HTTP Bearer security scheme for OpenAPI documentation
security = HTTPBearer(auto_error=False)

# Global instances (will be initialized on first use)
_jwks_client: Optional[JWKSClient] = None
_token_validator: Optional[TokenValidator] = None


def _get_token_validator() -> TokenValidator:
    """
    Get or create token validator instance
    
    Lazy initialization to ensure settings are loaded before creating instances.
    
    Returns:
        TokenValidator instance
    """
    global _jwks_client, _token_validator
    
    if _token_validator is None:
        # Check if authentication is configured
        if not hasattr(settings, 'auth_service_url') or not settings.auth_service_url:
            logger.error("AUTH_SERVICE_URL not configured")
            raise HTTPException(
                status_code=503,
                detail={
                    "status": "error",
                    "code": 503,
                    "message": "Authentication service unavailable",
                    "errors": [{
                        "field": "service",
                        "error": "Authentication not configured"
                    }]
                }
            )
        
        # Construct JWKS URL
        jwks_url = f"{settings.auth_service_url}/api/v1/auth/jwks"
        
        # Get cache TTL (default to 3600 if not configured)
        cache_ttl = getattr(settings, 'jwks_cache_ttl', 3600)
        
        # Initialize JWKS client
        _jwks_client = JWKSClient(jwks_url=jwks_url, cache_ttl=cache_ttl)
        
        # Get issuer and audience (with defaults)
        issuer = getattr(settings, 'jwt_issuer', 'https://api.example.com')
        audience = getattr(settings, 'jwt_audience', 'https://api.example.com')
        
        # Initialize token validator
        _token_validator = TokenValidator(
            jwks_client=_jwks_client,
            issuer=issuer,
            audience=audience
        )
        
        logger.info(f"Initialized authentication middleware with JWKS URL: {jwks_url}")
    
    return _token_validator


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> TokenPayload:
    """
    FastAPI dependency for extracting authenticated user from JWT token
    
    Extracts Bearer token from Authorization header, validates it using
    the token validator, and returns the token payload with user information.
    
    Args:
        credentials: HTTP Authorization credentials (Bearer token)
        
    Returns:
        TokenPayload with user_id, organization_id, roles, and permissions
        
    Raises:
        HTTPException(401): If token is missing, invalid, or expired
        HTTPException(503): If authentication service is unavailable
        
    Usage in routers:
        @router.post("/interviews/start")
        async def start_interview(
            request: StartInterviewRequest,
            current_user: TokenPayload = Depends(get_current_user)
        ):
            # current_user.user_id, current_user.roles available
    """
    # Check if Authorization header is present
    if credentials is None:
        logger.warning("Request missing Authorization header")
        raise HTTPException(
            status_code=401,
            detail={
                "status": "error",
                "code": 401,
                "message": "Authentication required",
                "errors": [{
                    "field": "authorization",
                    "error": "Missing or invalid authorization header"
                }]
            }
        )
    
    # Extract token from credentials
    token = credentials.credentials
    
    if not token:
        logger.warning("Authorization header present but token is empty")
        raise HTTPException(
            status_code=401,
            detail={
                "status": "error",
                "code": 401,
                "message": "Authentication required",
                "errors": [{
                    "field": "authorization",
                    "error": "Bearer token is empty"
                }]
            }
        )
    
    try:
        # Get token validator instance
        validator = _get_token_validator()
        
        # Validate token and extract payload
        token_payload = await validator.validate_token(token)
        
        logger.info(
            f"Successfully authenticated user: {token_payload.user_id} "
            f"from organization: {token_payload.organization_id}"
        )
        
        return token_payload
    
    except TokenExpiredError as e:
        logger.warning(f"Token expired: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail={
                "status": "error",
                "code": 401,
                "message": "Token expired",
                "errors": [{
                    "field": "token",
                    "error": "JWT token has expired"
                }]
            }
        )
    
    except TokenInvalidError as e:
        logger.error(f"Invalid token: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail={
                "status": "error",
                "code": 401,
                "message": "Invalid token",
                "errors": [{
                    "field": "token",
                    "error": "Token signature verification failed"
                }]
            }
        )
    
    except TokenMissingClaimsError as e:
        logger.error(f"Token missing required claims: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail={
                "status": "error",
                "code": 401,
                "message": "Invalid token",
                "errors": [{
                    "field": "token",
                    "error": "Token missing required claims"
                }]
            }
        )
    
    except JWKSFetchError as e:
        logger.error(f"Failed to fetch JWKS: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "error",
                "code": 503,
                "message": "Authentication service unavailable",
                "errors": [{
                    "field": "service",
                    "error": "Unable to validate token"
                }]
            }
        )
    
    except AuthenticationError as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail={
                "status": "error",
                "code": 401,
                "message": "Invalid token",
                "errors": [{
                    "field": "token",
                    "error": str(e)
                }]
            }
        )
    
    except HTTPException:
        # Re-raise HTTPExceptions (like the 503 from _get_token_validator)
        raise
    
    except Exception as e:
        logger.error(f"Unexpected error during authentication: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "code": 500,
                "message": "Internal server error",
                "errors": [{
                    "field": "server",
                    "error": "An unexpected error occurred during authentication"
                }]
            }
        )
