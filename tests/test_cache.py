import time

from app.cache import TTLCache


def test_get_returns_stored_value():
    cache = TTLCache(max_entries=2, ttl_s=60)
    cache.set("a", 1)
    assert cache.get("a") == 1


def test_expired_entries_are_dropped():
    cache = TTLCache(max_entries=2, ttl_s=0.01)
    cache.set("a", 1)
    time.sleep(0.02)
    assert cache.get("a") is None


def test_oldest_entry_is_evicted_when_full():
    cache = TTLCache(max_entries=2, ttl_s=60)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)
    assert cache.get("a") is None
    assert cache.get("b") == 2
    assert cache.get("c") == 3


def test_recently_used_entry_survives_eviction():
    cache = TTLCache(max_entries=2, ttl_s=60)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.get("a")  # refresh "a" so "b" becomes the eviction candidate
    cache.set("c", 3)
    assert cache.get("a") == 1
    assert cache.get("b") is None
