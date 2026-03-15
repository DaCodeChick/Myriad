"""
Search Cache - Persistent cache for web search results with rate limiting.

Features:
- Persistent disk storage with automatic save/load
- Thread-safe in-memory + disk cache
- Automatic expiration based on TTL
- Rate limiting to prevent API abuse
- Performance metrics and monitoring
"""

import time
import hashlib
import json
import os
from typing import Dict, Any, Optional, Tuple, List
from threading import Lock
from pathlib import Path


class RateLimiter:
    """
    Rate limiter to prevent API abuse.

    Uses sliding window algorithm to track requests per time period.
    """

    def __init__(self, max_requests: int = 30, time_window: int = 60):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum requests allowed in time window (default: 30)
            time_window: Time window in seconds (default: 60)
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self._requests: List[float] = []  # Timestamps of recent requests
        self._lock = Lock()

    def allow_request(self) -> bool:
        """
        Check if a request is allowed based on rate limits.

        Returns:
            True if request is allowed, False if rate limit exceeded
        """
        current_time = time.time()
        cutoff_time = current_time - self.time_window

        with self._lock:
            # Remove old requests outside the time window
            self._requests = [t for t in self._requests if t > cutoff_time]

            # Check if we're under the limit
            if len(self._requests) < self.max_requests:
                self._requests.append(current_time)
                return True

            return False

    def get_wait_time(self) -> float:
        """
        Get estimated wait time before next request is allowed.

        Returns:
            Wait time in seconds (0 if request can proceed now)
        """
        current_time = time.time()
        cutoff_time = current_time - self.time_window

        with self._lock:
            # Remove old requests
            self._requests = [t for t in self._requests if t > cutoff_time]

            if len(self._requests) < self.max_requests:
                return 0.0

            # Wait until oldest request expires
            oldest_request = min(self._requests)
            return max(0.0, oldest_request + self.time_window - current_time)

    def reset(self) -> None:
        """Reset the rate limiter."""
        with self._lock:
            self._requests.clear()


class SearchCache:
    """
    Thread-safe persistent cache for search results.

    Features:
    - Stores results in memory with disk persistence
    - Automatic expiration based on TTL
    - Performance metrics tracking
    - Automatic save on updates
    """

    def __init__(
        self,
        default_ttl: int = 3600,
        cache_file: Optional[str] = None,
        auto_save: bool = True,
    ):
        """
        Initialize the search cache.

        Args:
            default_ttl: Default time-to-live in seconds (default: 3600 = 1 hour)
            cache_file: Path to persistent cache file (default: data/search_cache.json)
            auto_save: Auto-save to disk on updates (default: True)
        """
        self.default_ttl = default_ttl
        self.auto_save = auto_save

        # Set cache file path
        if cache_file is None:
            cache_dir = Path(__file__).parent.parent.parent.parent / "data"
            cache_dir.mkdir(exist_ok=True)
            self.cache_file = cache_dir / "search_cache.json"
        else:
            self.cache_file = Path(cache_file)
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)

        self._cache: Dict[str, Tuple[Any, float]] = {}  # key -> (value, expiry_time)
        self._lock = Lock()
        self._hits = 0
        self._misses = 0
        self._saves = 0
        self._loads = 0

        # Load existing cache from disk
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        """Load cache from disk if file exists."""
        if not self.cache_file.exists():
            return

        try:
            with self._lock:
                with open(self.cache_file, "r") as f:
                    data = json.load(f)

                    # Load cache entries
                    self._cache = {
                        key: (value, expiry)
                        for key, (value, expiry) in data.get("cache", {}).items()
                    }

                    # Load statistics
                    stats = data.get("stats", {})
                    self._hits = stats.get("hits", 0)
                    self._misses = stats.get("misses", 0)
                    self._saves = stats.get("saves", 0)
                    self._loads = stats.get("loads", 0) + 1

                    # Clean expired entries on load (we're already in lock)
                    current_time = time.time()
                    expired_keys = [
                        key
                        for key, (_, expiry) in self._cache.items()
                        if current_time >= expiry
                    ]
                    for key in expired_keys:
                        del self._cache[key]
        except (json.JSONDecodeError, IOError, KeyError) as e:
            # If cache file is corrupted, start fresh
            print(f"Warning: Failed to load cache from {self.cache_file}: {e}")
            self._cache.clear()

    def _save_to_disk(self) -> None:
        """Save cache to disk."""
        try:
            with self._lock:
                data = {
                    "cache": {
                        key: (value, expiry)
                        for key, (value, expiry) in self._cache.items()
                    },
                    "stats": {
                        "hits": self._hits,
                        "misses": self._misses,
                        "saves": self._saves + 1,
                        "loads": self._loads,
                    },
                    "timestamp": time.time(),
                }

                # Write to temp file first, then rename (atomic operation)
                temp_file = self.cache_file.with_suffix(".tmp")
                with open(temp_file, "w") as f:
                    json.dump(data, f, indent=2)

                temp_file.replace(self.cache_file)
                self._saves += 1
        except IOError as e:
            print(f"Warning: Failed to save cache to {self.cache_file}: {e}")

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

        # Auto-save to disk if enabled
        if self.auto_save:
            self._save_to_disk()

    def clear(self) -> None:
        """Clear all cached entries and save to disk."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

        # Save empty cache to disk
        if self.auto_save:
            self._save_to_disk()

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
            Dictionary with cache stats (size, hits, misses, hit_rate, persistence info)
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
                "saves": self._saves,
                "loads": self._loads,
                "cache_file": str(self.cache_file),
                "auto_save": self.auto_save,
            }

    def set_ttl(self, ttl: int) -> None:
        """
        Update the default TTL for new cache entries.

        Args:
            ttl: New default time-to-live in seconds
        """
        self.default_ttl = ttl

    def warm_cache(self, queries: List[Tuple[str, Dict[str, Any]]]) -> None:
        """
        Warm the cache with common queries (for testing/preloading).

        This is a placeholder - actual warming should be done by calling
        the search tools with real queries.

        Args:
            queries: List of (tool_name, kwargs) tuples to warm
        """
        # This method is intentionally minimal - cache warming happens
        # naturally when search tools are called
        pass

    def force_save(self) -> None:
        """Force save cache to disk immediately."""
        self._save_to_disk()


# Global search cache instance
_global_cache: Optional[SearchCache] = None
# Global rate limiter instance
_global_rate_limiter: Optional[RateLimiter] = None


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


def get_rate_limiter() -> RateLimiter:
    """
    Get the global rate limiter instance (singleton pattern).

    Returns:
        Global RateLimiter instance (30 requests per minute by default)
    """
    global _global_rate_limiter
    if _global_rate_limiter is None:
        _global_rate_limiter = RateLimiter(max_requests=30, time_window=60)
    return _global_rate_limiter


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


def force_save_cache() -> None:
    """Force save the cache to disk immediately."""
    cache = get_search_cache()
    cache.force_save()
