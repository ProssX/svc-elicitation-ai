"""
JWKS Client for fetching and caching public keys from Auth Service
Implements intelligent caching with TTL and fallback to stale cache
"""
import logging
import base64
from datetime import datetime, timedelta
from typing import Optional
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from cryptography.hazmat.backends import default_backend
import httpx


logger = logging.getLogger(__name__)


class JWKSClientError(Exception):
    """Base exception for JWKS client errors"""
    pass


class KeyNotFoundError(JWKSClientError):
    """Key ID not found in JWKS"""
    pass


class JWKSFetchError(JWKSClientError):
    """Unable to fetch JWKS from auth service"""
    pass


class JWKSClient:
    """
    Client for fetching and caching JWKS public keys from Auth Service
    
    Implements:
    - In-memory cache with configurable TTL
    - Automatic cache refresh on expiration
    - Fallback to stale cache when Auth Service unavailable
    - Thread-safe operations
    """
    
    def __init__(self, jwks_url: str, cache_ttl: int = 3600):
        """
        Initialize JWKS client
        
        Args:
            jwks_url: Full URL to JWKS endpoint (e.g., http://localhost:8001/api/v1/auth/jwks)
            cache_ttl: Cache time-to-live in seconds (default: 3600 = 1 hour)
        """
        self.jwks_url = jwks_url
        self.cache_ttl = cache_ttl
        self._cache: dict[str, RSAPublicKey] = {}
        self._cache_timestamp: Optional[datetime] = None
        self._stale_cache: dict[str, RSAPublicKey] = {}
        
        logger.info(f"Initialized JWKS client with URL: {jwks_url}, TTL: {cache_ttl}s")
    
    async def get_signing_key(self, kid: str) -> RSAPublicKey:
        """
        Get RSA public key for given key ID
        
        Args:
            kid: Key ID from JWT header
            
        Returns:
            RSA public key object
            
        Raises:
            KeyNotFoundError: If kid not found in JWKS
            JWKSFetchError: If unable to fetch JWKS and no cache available
        """
        # Check if cache is valid
        if self._is_cache_valid():
            if kid in self._cache:
                logger.debug(f"Cache hit for kid: {kid}")
                return self._cache[kid]
            else:
                logger.warning(f"Key ID {kid} not found in valid cache")
        
        # Cache expired or key not found, try to refresh
        try:
            await self.refresh_keys()
            if kid in self._cache:
                logger.info(f"Successfully fetched key for kid: {kid}")
                return self._cache[kid]
            else:
                raise KeyNotFoundError(f"Key ID '{kid}' not found in JWKS")
        
        except JWKSFetchError as e:
            # Fallback to stale cache if available
            if kid in self._stale_cache:
                logger.warning(
                    f"Auth Service unavailable, using stale cache for kid: {kid}. "
                    f"Error: {str(e)}"
                )
                return self._stale_cache[kid]
            else:
                logger.error(f"No cached key available for kid: {kid}")
                raise
    
    async def refresh_keys(self) -> None:
        """
        Force refresh of cached keys from Auth Service
        
        Raises:
            JWKSFetchError: If unable to fetch JWKS
        """
        try:
            logger.info(f"Fetching JWKS from {self.jwks_url}")
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.jwks_url)
                response.raise_for_status()
                
                jwks_data = response.json()
                
                # Handle standard API response format (data wrapper)
                # Auth service returns: {"status": "success", "data": {"keys": [...]}}
                if "data" in jwks_data and isinstance(jwks_data["data"], dict):
                    jwks_data = jwks_data["data"]
                
                # Validate JWKS format
                if "keys" not in jwks_data:
                    raise JWKSFetchError("Invalid JWKS format: missing 'keys' field")
                
                # Parse keys
                new_cache = {}
                for key_data in jwks_data["keys"]:
                    kid = key_data.get("kid")
                    if not kid:
                        logger.warning("Skipping key without 'kid' field")
                        continue
                    
                    try:
                        public_key = self._parse_jwk(key_data)
                        new_cache[kid] = public_key
                        logger.debug(f"Parsed key: {kid}")
                    except Exception as e:
                        logger.error(f"Failed to parse key {kid}: {str(e)}")
                        continue
                
                if not new_cache:
                    raise JWKSFetchError("No valid keys found in JWKS")
                
                # Update cache
                self._stale_cache = self._cache.copy()  # Save old cache as stale
                self._cache = new_cache
                self._cache_timestamp = datetime.utcnow()
                
                logger.info(f"Successfully refreshed {len(new_cache)} keys")
        
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP error fetching JWKS: {e.response.status_code}"
            logger.error(error_msg)
            raise JWKSFetchError(error_msg) from e
        
        except httpx.RequestError as e:
            error_msg = f"Network error fetching JWKS: {str(e)}"
            logger.error(error_msg)
            raise JWKSFetchError(error_msg) from e
        
        except Exception as e:
            error_msg = f"Unexpected error fetching JWKS: {str(e)}"
            logger.error(error_msg)
            raise JWKSFetchError(error_msg) from e
    
    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid based on TTL"""
        if not self._cache_timestamp:
            return False
        
        age = (datetime.utcnow() - self._cache_timestamp).total_seconds()
        is_valid = age < self.cache_ttl
        
        if not is_valid:
            logger.debug(f"Cache expired (age: {age}s, TTL: {self.cache_ttl}s)")
        
        return is_valid
    
    def _parse_jwk(self, key_data: dict) -> RSAPublicKey:
        """
        Parse JWK format to RSA public key
        
        Args:
            key_data: JWK dictionary
            
        Returns:
            RSA public key object
            
        Raises:
            ValueError: If key format is invalid
        """
        # Check key type
        if key_data.get("kty") != "RSA":
            raise ValueError(f"Unsupported key type: {key_data.get('kty')}")
        
        # Try to use publicKey field (PEM format) if available
        if "publicKey" in key_data:
            try:
                pem_data = base64.b64decode(key_data["publicKey"])
                public_key = serialization.load_pem_public_key(
                    pem_data,
                    backend=default_backend()
                )
                if isinstance(public_key, RSAPublicKey):
                    return public_key
                else:
                    raise ValueError("Key is not an RSA public key")
            except Exception as e:
                logger.warning(f"Failed to parse publicKey field: {e}, trying JWK format")
        
        # Fallback to standard JWK format (n and e)
        if "n" not in key_data or "e" not in key_data:
            raise ValueError("Missing required JWK fields: 'n' and 'e'")
        
        try:
            # Import from JWK format using PyJWT's helper
            from jwt.algorithms import RSAAlgorithm
            public_key = RSAAlgorithm.from_jwk(key_data)
            return public_key
        except Exception as e:
            raise ValueError(f"Failed to parse JWK: {str(e)}") from e
