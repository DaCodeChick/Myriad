#!/usr/bin/env python3
"""
Test script for persistent cache functionality.

This script verifies that the search cache correctly saves to and loads from disk.
"""

import os
import sys
import time
import importlib.util
from pathlib import Path

# Load search_cache module directly without importing core package
cache_module_path = Path(__file__).parent / "core/tools/utility/search_cache.py"
spec = importlib.util.spec_from_file_location("search_cache", cache_module_path)
search_cache = importlib.util.module_from_spec(spec)
spec.loader.exec_module(search_cache)

SearchCache = search_cache.SearchCache
RateLimiter = search_cache.RateLimiter


def test_persistent_cache():
    """Test persistent cache save and load."""
    print("🧪 Testing Persistent Cache...")
    print("=" * 60)

    # Create cache with custom file
    cache_file = Path("data/test_cache.json")
    cache_file.parent.mkdir(exist_ok=True)

    # Clean up old test cache
    if cache_file.exists():
        cache_file.unlink()
        print("✓ Cleaned up old test cache")

    # Test 1: Create cache and add data
    print("\n📝 Test 1: Creating cache and adding data...")
    cache1 = SearchCache(cache_file=str(cache_file), auto_save=True)

    cache1.set("search_web", "Test result 1", ttl=3600, query="test query 1")
    cache1.set("search_web", "Test result 2", ttl=3600, query="test query 2")
    cache1.set("search_news", "News result 1", ttl=1800, query="news query")

    stats1 = cache1.get_stats()
    print(f"  Cache size: {stats1['size']} entries")
    print(f"  Disk saves: {stats1['saves']}")
    print(f"  Cache file: {cache_file}")

    assert stats1["size"] == 3, "Cache should have 3 entries"
    assert cache_file.exists(), "Cache file should exist"
    print("✓ Test 1 passed: Cache created and saved")

    # Test 2: Load cache in new instance
    print("\n📂 Test 2: Loading cache in new instance...")
    cache2 = SearchCache(cache_file=str(cache_file), auto_save=False)

    stats2 = cache2.get_stats()
    print(f"  Cache size: {stats2['size']} entries")
    print(f"  Disk loads: {stats2['loads']}")

    assert stats2["size"] == 3, "Loaded cache should have 3 entries"
    assert stats2["loads"] == 1, "Should have 1 load operation"
    print("✓ Test 2 passed: Cache loaded successfully")

    # Test 3: Verify data integrity
    print("\n🔍 Test 3: Verifying data integrity...")
    result1 = cache2.get("search_web", query="test query 1")
    result2 = cache2.get("search_web", query="test query 2")
    result3 = cache2.get("search_news", query="news query")

    assert result1 == "Test result 1", "Should retrieve correct result 1"
    assert result2 == "Test result 2", "Should retrieve correct result 2"
    assert result3 == "News result 1", "Should retrieve correct news result"

    stats3 = cache2.get_stats()
    print(f"  Cache hits: {stats3['hits']}")
    print(f"  Hit rate: {stats3['hit_rate']}%")

    assert stats3["hits"] == 3, "Should have 3 cache hits"
    print("✓ Test 3 passed: Data integrity verified")

    # Test 4: Force save
    print("\n💾 Test 4: Testing force save...")
    cache2.set("search_web", "New result", ttl=3600, query="new query")

    # Get stats before force save
    stats_before_save = cache2.get_stats()
    saves_before = stats_before_save["saves"]

    cache2.force_save()

    stats4 = cache2.get_stats()
    print(f"  Cache size: {stats4['size']} entries")
    print(f"  Disk saves: {stats4['saves']}")

    assert stats4["size"] == 4, "Cache should have 4 entries"
    assert stats4["saves"] == saves_before + 1, (
        f"Should have {saves_before + 1} save operations"
    )
    print("✓ Test 4 passed: Force save works")

    # Test 5: Clear and verify empty
    print("\n🗑️  Test 5: Testing clear...")
    cache2.clear()
    cache2.force_save()

    stats5 = cache2.get_stats()
    print(f"  Cache size: {stats5['size']} entries")

    assert stats5["size"] == 0, "Cache should be empty"
    print("✓ Test 5 passed: Clear works correctly")

    # Clean up
    if cache_file.exists():
        cache_file.unlink()
        print("\n🧹 Cleaned up test cache file")

    print("\n" + "=" * 60)
    print("✅ All persistent cache tests passed!")


def test_rate_limiter():
    """Test rate limiter functionality."""
    print("\n🚦 Testing Rate Limiter...")
    print("=" * 60)

    # Test 1: Basic rate limiting
    print("\n📝 Test 1: Basic rate limiting...")
    limiter = RateLimiter(max_requests=5, time_window=2)

    # Should allow 5 requests
    allowed_count = 0
    for i in range(10):
        if limiter.allow_request():
            allowed_count += 1

    print(f"  Allowed requests: {allowed_count} / 10")
    assert allowed_count == 5, "Should allow exactly 5 requests"
    print("✓ Test 1 passed: Rate limit enforced")

    # Test 2: Wait time calculation
    print("\n⏱️  Test 2: Wait time calculation...")
    wait_time = limiter.get_wait_time()
    print(f"  Wait time: {wait_time:.2f}s")
    assert wait_time > 0, "Should have wait time when limited"
    assert wait_time <= 2, "Wait time should be <= time window"
    print("✓ Test 2 passed: Wait time calculated correctly")

    # Test 3: Window expiration
    print("\n⏳ Test 3: Testing window expiration...")
    print(f"  Waiting {wait_time:.1f}s for window to expire...")
    time.sleep(wait_time + 0.1)

    allowed = limiter.allow_request()
    assert allowed, "Should allow request after window expires"
    print("✓ Test 3 passed: Window expiration works")

    # Test 4: Reset
    print("\n🔄 Test 4: Testing reset...")
    limiter.reset()
    wait_time = limiter.get_wait_time()

    assert wait_time == 0, "Wait time should be 0 after reset"
    print("✓ Test 4 passed: Reset works correctly")

    print("\n" + "=" * 60)
    print("✅ All rate limiter tests passed!")


if __name__ == "__main__":
    try:
        test_persistent_cache()
        test_rate_limiter()

        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
