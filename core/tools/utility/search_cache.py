"""
Search Cache - In-memory cache for web search results.

Reduces API calls by caching search results for a configurable duration.
Thread-safe implementation with automatic expiration.
"""

import time
import hashlib
from typing import Dict, Any, Optional, Tuple
from threading import Lock


class SearchCache:
    """
    Thread-safe in-memory cache for search results.

    Stores search results with automatic expiration based on TTL (time-to-live).
    """

    def __init__(self, default_ttl: int = 3600):
        """
        Initialize the search cache.

        Args:
            default_ttl: Default time-to-live in seconds (default: 3600 = 1 hour)
        """
        self.default_ttl = default_ttl
        self._cache: Dict[str, Tuple[Any, float]] = {}  # key -> (value, expiry_time)
        self._lock = Lock()
        self._hits = 0
        self._misses = 0

    def _generate_key(self, tool_name: str, **kwargs) -> str:
        """
        Generate a cache key from tool name and arguments.

        Args:
            tool_name: Name of the search tool
            **kwargs: Search arguments

        Returns:
            Hashed cache key
        """
        # Sort kwargs for consistent hashing
        sorted_args = sorted(kwargs.items())
        key_string = f"{tool_name}:{sorted_args}"
        return hashlib.sha256(key_string.encode()).hexdigest()

    def get(self, tool_name: str, **kwargs) -> Optional[str]:
        """
        Get cached search result if available and not expired.

        Args:
            tool_name: Name of the search tool
            **kwargs: Search arguments

        Returns:
            Cached result string if found and valid, None otherwise
        """
        key = self._generate_key(tool_name, **kwargs)

        with self._lock:
            if key in self._cache:
                result, expiry = self._cache[key]
                current_time = time.time()

                # Check if expired
                if current_time < expiry:
                    self._hits += 1
                    return result
                else:
                    # Remove expired entry
                    del self._cache[key]

            self._misses += 1
            return None

    def set(
        self, tool_name: str, result: str, ttl: Optional[int] = None, **kwargs
    ) -> None:
        """
        Store search result in cache.

        Args:
            tool_name: Name of the search tool
            result: Search result string to cache
            ttl: Time-to-live in seconds (uses default if None)
            **kwargs: Search arguments
        """
        key = self._generate_key(tool_name, **kwargs)
        ttl = ttl if ttl is not None else self.default_ttl
        expiry = time.time() + ttl

        with self._lock:
            self._cache[key] = (result, expiry)

    def clear(self) -> None:
        """Clear all cached entries."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def clear_expired(self) -> int:
        """
        Remove all expired entries from the cache.

        Returns:
            Number of entries removed
        """
        current_time = time.time()
        removed_count = 0

        with self._lock:
            expired_keys = [
                key
                for key, (_, expiry) in self._cache.items()
                if current_time >= expiry
            ]

            for key in expired_keys:
                del self._cache[key]
                removed_count += 1

        return removed_count

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats (size, hits, misses, hit_rate)
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0

            return {
                "size": len(self._cache),
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(hit_rate, 2),
                "default_ttl": self.default_ttl,
            }

    def set_ttl(self, ttl: int) -> None:
        """
        Update the default TTL for new cache entries.

        Args:
            ttl: New default time-to-live in seconds
        """
        self.default_ttl = ttl


# Global search cache instance
_global_cache: Optional[SearchCache] = None


def get_search_cache() -> SearchCache:
    """
    Get the global search cache instance (singleton pattern).

    Returns:
        Global SearchCache instance
    """
    global _global_cache
    if _global_cache is None:
        _global_cache = SearchCache(default_ttl=3600)  # 1 hour default
    return _global_cache


def clear_search_cache() -> None:
    """Clear the global search cache."""
    cache = get_search_cache()
    cache.clear()


def get_cache_stats() -> Dict[str, Any]:
    """
    Get global search cache statistics.

    Returns:
        Cache statistics dictionary
    """
    cache = get_search_cache()
    return cache.get_stats()
