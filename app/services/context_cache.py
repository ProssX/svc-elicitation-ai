"""
Context caching service for storing and retrieving context data with TTL.

This module provides an in-memory cache with time-to-live (TTL) functionality
for employee and organization context data to reduce backend API calls.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from threading import Lock
from uuid import UUID

logger = logging.getLogger(__name__)


class ContextCache:
    """
    In-memory cache with TTL for context data.
    
    Provides thread-safe caching of employee and organization context
    with automatic expiration and cache hit/miss metrics logging.
    """
    
    def __init__(self, ttl_seconds: int = 300):
        """
        Initialize the context cache.
        
        Args:
            ttl_seconds: Time-to-live for cache entries in seconds (default: 300 = 5 minutes)
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._ttl_seconds = ttl_seconds
        self._lock = Lock()
        self._hits = 0
        self._misses = 0
        logger.info(f"ContextCache initialized with TTL={ttl_seconds}s")
    
    def _generate_key(self, prefix: str, identifier: UUID) -> str:
        """
        Generate cache key for employee or organization data.
        
        Args:
            prefix: Key prefix (e.g., 'employee', 'organization', 'processes')
            identifier: UUID identifier
            
        Returns:
            Cache key string
        """
        return f"{prefix}:{str(identifier)}"
    
    def _is_expired(self, entry: Dict[str, Any]) -> bool:
        """
        Check if a cache entry has expired.
        
        Args:
            entry: Cache entry with 'expires_at' timestamp
            
        Returns:
            True if expired, False otherwise
        """
        expires_at = entry.get("expires_at")
        if not expires_at:
            return True
        return datetime.utcnow() >= expires_at
    
    def get(self, prefix: str, identifier: UUID) -> Optional[Any]:
        """
        Retrieve data from cache if not expired.
        
        Args:
            prefix: Key prefix
            identifier: UUID identifier
            
        Returns:
            Cached data if found and not expired, None otherwise
        """
        key = self._generate_key(prefix, identifier)
        
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._misses += 1
                logger.debug(
                    f"[CACHE] MISS: {key}",
                    extra={
                        "cache_key": key,
                        "cache_hit": False,
                        "total_hits": self._hits,
                        "total_misses": self._misses
                    }
                )
                return None
            
            if self._is_expired(entry):
                # Remove expired entry
                del self._cache[key]
                self._misses += 1
                logger.debug(
                    f"[CACHE] MISS (expired): {key}",
                    extra={
                        "cache_key": key,
                        "cache_hit": False,
                        "reason": "expired",
                        "total_hits": self._hits,
                        "total_misses": self._misses
                    }
                )
                return None
            
            self._hits += 1
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0.0
            
            logger.debug(
                f"[CACHE] HIT: {key}",
                extra={
                    "cache_key": key,
                    "cache_hit": True,
                    "total_hits": self._hits,
                    "total_misses": self._misses,
                    "hit_rate_percent": round(hit_rate, 2)
                }
            )
            return entry.get("data")
    
    def set(self, prefix: str, identifier: UUID, data: Any) -> None:
        """
        Store data in cache with TTL.
        
        Args:
            prefix: Key prefix
            identifier: UUID identifier
            data: Data to cache
        """
        key = self._generate_key(prefix, identifier)
        expires_at = datetime.utcnow() + timedelta(seconds=self._ttl_seconds)
        
        with self._lock:
            self._cache[key] = {
                "data": data,
                "expires_at": expires_at,
                "cached_at": datetime.utcnow()
            }
            logger.debug(f"Cache SET: {key} (expires at {expires_at.isoformat()})")
    
    def invalidate(self, prefix: str, identifier: UUID) -> bool:
        """
        Invalidate (remove) a specific cache entry.
        
        Args:
            prefix: Key prefix
            identifier: UUID identifier
            
        Returns:
            True if entry was found and removed, False otherwise
        """
        key = self._generate_key(prefix, identifier)
        
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Cache INVALIDATE: {key}")
                return True
            return False
    
    def invalidate_all(self) -> int:
        """
        Invalidate all cache entries.
        
        Returns:
            Number of entries invalidated
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"Cache INVALIDATE ALL: {count} entries cleared")
            return count
    
    def invalidate_by_prefix(self, prefix: str) -> int:
        """
        Invalidate all cache entries with a specific prefix.
        
        Args:
            prefix: Key prefix to match
            
        Returns:
            Number of entries invalidated
        """
        with self._lock:
            keys_to_remove = [key for key in self._cache.keys() if key.startswith(f"{prefix}:")]
            for key in keys_to_remove:
                del self._cache[key]
            logger.debug(f"Cache INVALIDATE PREFIX '{prefix}': {len(keys_to_remove)} entries cleared")
            return len(keys_to_remove)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics including hits, misses, and hit rate
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0.0
            
            stats = {
                "hits": self._hits,
                "misses": self._misses,
                "total_requests": total_requests,
                "hit_rate_percent": round(hit_rate, 2),
                "entries_count": len(self._cache),
                "ttl_seconds": self._ttl_seconds
            }
            
            logger.info(
                f"[CACHE] Cache statistics",
                extra={
                    "cache_hits": self._hits,
                    "cache_misses": self._misses,
                    "cache_total_requests": total_requests,
                    "cache_hit_rate_percent": round(hit_rate, 2),
                    "cache_entries_count": len(self._cache),
                    "cache_ttl_seconds": self._ttl_seconds
                }
            )
            return stats
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired entries from cache.
        
        Returns:
            Number of expired entries removed
        """
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if self._is_expired(entry)
            ]
            
            for key in expired_keys:
                del self._cache[key]
            
            if expired_keys:
                logger.debug(f"Cache CLEANUP: {len(expired_keys)} expired entries removed")
            
            return len(expired_keys)
