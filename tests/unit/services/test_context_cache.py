"""
Unit tests for ContextCache

Tests cache storage and retrieval, TTL expiration, cache invalidation,
and concurrent access patterns.
"""
import pytest
import asyncio
import time
from datetime import datetime, timedelta
from uuid import uuid4
from threading import Thread

from app.services.context_cache import ContextCache


class TestContextCacheBasicOperations:
    """Test suite for basic cache operations"""
    
    def test_cache_initialization(self):
        """Test cache initializes with correct TTL"""
        cache = ContextCache(ttl_seconds=300)
        assert cache._ttl_seconds == 300
        assert len(cache._cache) == 0
        assert cache._hits == 0
        assert cache._misses == 0
    
    def test_cache_set_and_get(self):
        """Test basic cache storage and retrieval"""
        cache = ContextCache(ttl_seconds=300)
        employee_id = uuid4()
        data = {"name": "John Doe", "role": "Engineer"}
        
        # Set data
        cache.set("employee", employee_id, data)
        
        # Get data
        result = cache.get("employee", employee_id)
        
        assert result == data
        assert cache._hits == 1
        assert cache._misses == 0
    
    def test_cache_miss(self):
        """Test cache miss returns None"""
        cache = ContextCache(ttl_seconds=300)
        employee_id = uuid4()
        
        result = cache.get("employee", employee_id)
        
        assert result is None
        assert cache._hits == 0
        assert cache._misses == 1
    
    def test_cache_key_generation(self):
        """Test cache key generation is consistent"""
        cache = ContextCache(ttl_seconds=300)
        employee_id = uuid4()
        
        key1 = cache._generate_key("employee", employee_id)
        key2 = cache._generate_key("employee", employee_id)
        
        assert key1 == key2
        assert key1 == f"employee:{str(employee_id)}"
    
    def test_cache_different_prefixes(self):
        """Test cache handles different prefixes independently"""
        cache = ContextCache(ttl_seconds=300)
        identifier = uuid4()
        
        employee_data = {"type": "employee"}
        org_data = {"type": "organization"}
        
        cache.set("employee", identifier, employee_data)
        cache.set("organization", identifier, org_data)
        
        assert cache.get("employee", identifier) == employee_data
        assert cache.get("organization", identifier) == org_data
    
    def test_cache_overwrites_existing_data(self):
        """Test cache overwrites data for same key"""
        cache = ContextCache(ttl_seconds=300)
        employee_id = uuid4()
        
        cache.set("employee", employee_id, {"version": 1})
        cache.set("employee", employee_id, {"version": 2})
        
        result = cache.get("employee", employee_id)
        assert result == {"version": 2}


class TestContextCacheTTLExpiration:
    """Test suite for TTL expiration"""
    
    def test_cache_entry_expires_after_ttl(self):
        """Test cache entry expires after TTL"""
        cache = ContextCache(ttl_seconds=1)  # 1 second TTL
        employee_id = uuid4()
        data = {"name": "John Doe"}
        
        cache.set("employee", employee_id, data)
        
        # Should be available immediately
        result = cache.get("employee", employee_id)
        assert result == data
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be expired
        result = cache.get("employee", employee_id)
        assert result is None
        assert cache._misses == 1  # Expired counts as miss
    
    def test_cache_entry_not_expired_before_ttl(self):
        """Test cache entry is available before TTL expires"""
        cache = ContextCache(ttl_seconds=2)  # 2 second TTL
        employee_id = uuid4()
        data = {"name": "John Doe"}
        
        cache.set("employee", employee_id, data)
        
        # Wait less than TTL
        time.sleep(0.5)
        
        # Should still be available
        result = cache.get("employee", employee_id)
        assert result == data
        assert cache._hits == 1
    
    def test_is_expired_method(self):
        """Test _is_expired method correctly identifies expired entries"""
        cache = ContextCache(ttl_seconds=300)
        
        # Entry that expires in the future
        future_entry = {
            "data": "test",
            "expires_at": datetime.utcnow() + timedelta(seconds=60)
        }
        assert cache._is_expired(future_entry) is False
        
        # Entry that expired in the past
        past_entry = {
            "data": "test",
            "expires_at": datetime.utcnow() - timedelta(seconds=60)
        }
        assert cache._is_expired(past_entry) is True
        
        # Entry without expires_at
        invalid_entry = {"data": "test"}
        assert cache._is_expired(invalid_entry) is True
    
    def test_expired_entry_removed_from_cache(self):
        """Test expired entries are removed when accessed"""
        cache = ContextCache(ttl_seconds=1)
        employee_id = uuid4()
        
        cache.set("employee", employee_id, {"name": "John"})
        
        # Verify entry exists in internal cache
        key = cache._generate_key("employee", employee_id)
        assert key in cache._cache
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Access expired entry
        cache.get("employee", employee_id)
        
        # Verify entry was removed
        assert key not in cache._cache


class TestContextCacheInvalidation:
    """Test suite for cache invalidation"""
    
    def test_invalidate_specific_entry(self):
        """Test invalidating a specific cache entry"""
        cache = ContextCache(ttl_seconds=300)
        employee_id = uuid4()
        
        cache.set("employee", employee_id, {"name": "John"})
        
        # Invalidate
        result = cache.invalidate("employee", employee_id)
        
        assert result is True
        assert cache.get("employee", employee_id) is None
    
    def test_invalidate_nonexistent_entry(self):
        """Test invalidating non-existent entry returns False"""
        cache = ContextCache(ttl_seconds=300)
        employee_id = uuid4()
        
        result = cache.invalidate("employee", employee_id)
        
        assert result is False
    
    def test_invalidate_all_entries(self):
        """Test invalidating all cache entries"""
        cache = ContextCache(ttl_seconds=300)
        
        # Add multiple entries
        cache.set("employee", uuid4(), {"name": "John"})
        cache.set("employee", uuid4(), {"name": "Jane"})
        cache.set("organization", uuid4(), {"name": "Acme"})
        
        # Invalidate all
        count = cache.invalidate_all()
        
        assert count == 3
        assert len(cache._cache) == 0
    
    def test_invalidate_by_prefix(self):
        """Test invalidating entries by prefix"""
        cache = ContextCache(ttl_seconds=300)
        
        emp_id1 = uuid4()
        emp_id2 = uuid4()
        org_id = uuid4()
        
        cache.set("employee", emp_id1, {"name": "John"})
        cache.set("employee", emp_id2, {"name": "Jane"})
        cache.set("organization", org_id, {"name": "Acme"})
        
        # Invalidate only employee entries
        count = cache.invalidate_by_prefix("employee")
        
        assert count == 2
        assert cache.get("employee", emp_id1) is None
        assert cache.get("employee", emp_id2) is None
        assert cache.get("organization", org_id) is not None
    
    def test_invalidate_by_prefix_no_matches(self):
        """Test invalidating by prefix with no matches"""
        cache = ContextCache(ttl_seconds=300)
        
        cache.set("employee", uuid4(), {"name": "John"})
        
        count = cache.invalidate_by_prefix("organization")
        
        assert count == 0


class TestContextCacheStatistics:
    """Test suite for cache statistics"""
    
    def test_get_stats_initial_state(self):
        """Test statistics in initial state"""
        cache = ContextCache(ttl_seconds=300)
        
        stats = cache.get_stats()
        
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["total_requests"] == 0
        assert stats["hit_rate_percent"] == 0.0
        assert stats["entries_count"] == 0
        assert stats["ttl_seconds"] == 300
    
    def test_get_stats_after_operations(self):
        """Test statistics after cache operations"""
        cache = ContextCache(ttl_seconds=300)
        employee_id = uuid4()
        
        # Set data
        cache.set("employee", employee_id, {"name": "John"})
        
        # Hit
        cache.get("employee", employee_id)
        
        # Miss
        cache.get("employee", uuid4())
        
        stats = cache.get_stats()
        
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["total_requests"] == 2
        assert stats["hit_rate_percent"] == 50.0
        assert stats["entries_count"] == 1
    
    def test_hit_rate_calculation(self):
        """Test hit rate percentage calculation"""
        cache = ContextCache(ttl_seconds=300)
        employee_id = uuid4()
        
        cache.set("employee", employee_id, {"name": "John"})
        
        # 3 hits
        cache.get("employee", employee_id)
        cache.get("employee", employee_id)
        cache.get("employee", employee_id)
        
        # 1 miss
        cache.get("employee", uuid4())
        
        stats = cache.get_stats()
        
        assert stats["hits"] == 3
        assert stats["misses"] == 1
        assert stats["total_requests"] == 4
        assert stats["hit_rate_percent"] == 75.0


class TestContextCacheCleanup:
    """Test suite for cache cleanup operations"""
    
    def test_cleanup_expired_entries(self):
        """Test cleanup removes only expired entries"""
        cache = ContextCache(ttl_seconds=1)
        
        # Add entries
        id1 = uuid4()
        id2 = uuid4()
        cache.set("employee", id1, {"name": "John"})
        
        # Wait for first to expire
        time.sleep(1.1)
        
        # Add another entry (not expired)
        cache.set("employee", id2, {"name": "Jane"})
        
        # Cleanup
        count = cache.cleanup_expired()
        
        assert count == 1
        assert cache.get("employee", id1) is None
        assert cache.get("employee", id2) is not None
    
    def test_cleanup_no_expired_entries(self):
        """Test cleanup with no expired entries"""
        cache = ContextCache(ttl_seconds=300)
        
        cache.set("employee", uuid4(), {"name": "John"})
        cache.set("employee", uuid4(), {"name": "Jane"})
        
        count = cache.cleanup_expired()
        
        assert count == 0
        assert len(cache._cache) == 2
    
    def test_cleanup_all_expired(self):
        """Test cleanup when all entries are expired"""
        cache = ContextCache(ttl_seconds=1)
        
        cache.set("employee", uuid4(), {"name": "John"})
        cache.set("employee", uuid4(), {"name": "Jane"})
        
        # Wait for expiration
        time.sleep(1.1)
        
        count = cache.cleanup_expired()
        
        assert count == 2
        assert len(cache._cache) == 0


class TestContextCacheConcurrency:
    """Test suite for concurrent access"""
    
    def test_concurrent_reads(self):
        """Test concurrent read operations are thread-safe"""
        cache = ContextCache(ttl_seconds=300)
        employee_id = uuid4()
        data = {"name": "John Doe"}
        
        cache.set("employee", employee_id, data)
        
        results = []
        
        def read_cache():
            result = cache.get("employee", employee_id)
            results.append(result)
        
        # Create multiple threads reading simultaneously
        threads = [Thread(target=read_cache) for _ in range(10)]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All reads should succeed
        assert len(results) == 10
        assert all(r == data for r in results)
    
    def test_concurrent_writes(self):
        """Test concurrent write operations are thread-safe"""
        cache = ContextCache(ttl_seconds=300)
        employee_id = uuid4()
        
        def write_cache(value):
            cache.set("employee", employee_id, {"value": value})
        
        # Create multiple threads writing simultaneously
        threads = [Thread(target=write_cache, args=(i,)) for i in range(10)]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Cache should have one entry (last write wins)
        result = cache.get("employee", employee_id)
        assert result is not None
        assert "value" in result
    
    def test_concurrent_invalidation(self):
        """Test concurrent invalidation operations are thread-safe"""
        cache = ContextCache(ttl_seconds=300)
        
        # Add multiple entries
        ids = [uuid4() for _ in range(10)]
        for emp_id in ids:
            cache.set("employee", emp_id, {"name": f"Employee {emp_id}"})
        
        results = []
        
        def invalidate_entry(emp_id):
            result = cache.invalidate("employee", emp_id)
            results.append(result)
        
        # Create threads to invalidate simultaneously
        threads = [Thread(target=invalidate_entry, args=(emp_id,)) for emp_id in ids]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All invalidations should succeed
        assert len(results) == 10
        assert all(r is True for r in results)
        assert len(cache._cache) == 0
    
    def test_concurrent_stats_access(self):
        """Test concurrent statistics access is thread-safe"""
        cache = ContextCache(ttl_seconds=300)
        employee_id = uuid4()
        cache.set("employee", employee_id, {"name": "John"})
        
        stats_results = []
        
        def get_stats():
            stats = cache.get_stats()
            stats_results.append(stats)
        
        def access_cache():
            cache.get("employee", employee_id)
        
        # Mix of stats reads and cache accesses
        threads = []
        for i in range(20):
            if i % 2 == 0:
                threads.append(Thread(target=get_stats))
            else:
                threads.append(Thread(target=access_cache))
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All stats calls should succeed
        assert len(stats_results) == 10
        assert all("hits" in s for s in stats_results)
    
    def test_concurrent_cleanup(self):
        """Test concurrent cleanup operations are thread-safe"""
        cache = ContextCache(ttl_seconds=1)
        
        # Add entries
        for _ in range(5):
            cache.set("employee", uuid4(), {"name": "Test"})
        
        # Wait for expiration
        time.sleep(1.1)
        
        cleanup_results = []
        
        def cleanup():
            count = cache.cleanup_expired()
            cleanup_results.append(count)
        
        # Multiple threads trying to cleanup
        threads = [Thread(target=cleanup) for _ in range(3)]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Total cleaned should equal original count
        total_cleaned = sum(cleanup_results)
        assert total_cleaned == 5
        assert len(cache._cache) == 0


class TestContextCacheEdgeCases:
    """Test suite for edge cases"""
    
    def test_cache_with_none_data(self):
        """Test caching None values"""
        cache = ContextCache(ttl_seconds=300)
        employee_id = uuid4()
        
        cache.set("employee", employee_id, None)
        result = cache.get("employee", employee_id)
        
        assert result is None
        assert cache._hits == 1  # Should count as hit, not miss
    
    def test_cache_with_empty_dict(self):
        """Test caching empty dictionaries"""
        cache = ContextCache(ttl_seconds=300)
        employee_id = uuid4()
        
        cache.set("employee", employee_id, {})
        result = cache.get("employee", employee_id)
        
        assert result == {}
        assert cache._hits == 1
    
    def test_cache_with_complex_data(self):
        """Test caching complex nested data structures"""
        cache = ContextCache(ttl_seconds=300)
        employee_id = uuid4()
        
        complex_data = {
            "name": "John Doe",
            "roles": [
                {"id": str(uuid4()), "name": "Engineer"},
                {"id": str(uuid4()), "name": "Lead"}
            ],
            "metadata": {
                "created_at": "2024-01-01",
                "tags": ["python", "backend"]
            }
        }
        
        cache.set("employee", employee_id, complex_data)
        result = cache.get("employee", employee_id)
        
        assert result == complex_data
        assert result["roles"][0]["name"] == "Engineer"
    
    def test_cache_with_zero_ttl(self):
        """Test cache with zero TTL expires immediately"""
        cache = ContextCache(ttl_seconds=0)
        employee_id = uuid4()
        
        cache.set("employee", employee_id, {"name": "John"})
        
        # Even immediate access should be expired
        time.sleep(0.01)
        result = cache.get("employee", employee_id)
        
        assert result is None
    
    def test_cache_with_very_long_ttl(self):
        """Test cache with very long TTL"""
        cache = ContextCache(ttl_seconds=86400)  # 24 hours
        employee_id = uuid4()
        
        cache.set("employee", employee_id, {"name": "John"})
        result = cache.get("employee", employee_id)
        
        assert result == {"name": "John"}
        
        # Verify expires_at is set correctly
        key = cache._generate_key("employee", employee_id)
        entry = cache._cache[key]
        assert entry["expires_at"] > datetime.utcnow() + timedelta(hours=23)
