from __future__ import annotations

import time

from researchsensei.llm.response_cache import ResponseCache


def test_cache_stores_and_retrieves() -> None:
    cache = ResponseCache()
    key = cache.make_key(
        model_name="test-model",
        prompt_version="default",
        prompt_hash="abc123",
    )
    cache.set(key, "cached response")
    assert cache.get(key) == "cached response"


def test_cache_miss_returns_none() -> None:
    cache = ResponseCache()
    assert cache.get("nonexistent-key") is None


def test_cache_hit_miss_stats() -> None:
    cache = ResponseCache()
    key = cache.make_key(model_name="m", prompt_version="default", prompt_hash="h")
    cache.get(key)  # miss
    cache.set(key, "value")
    cache.get(key)  # hit
    stats = cache.stats
    assert stats["hits"] == 1
    assert stats["misses"] == 1


def test_cache_ttl_expiry() -> None:
    cache = ResponseCache(default_ttl=1)  # 1 second TTL
    key = cache.make_key(model_name="m", prompt_version="default", prompt_hash="h")
    cache.set(key, "value")
    assert cache.get(key) == "value"
    # Simulate expiry by setting expires_at in the past
    cache._entries[key].expires_at = time.time() - 1
    assert cache.get(key) is None


def test_cache_ttl_zero_means_no_expiry() -> None:
    cache = ResponseCache()
    key = cache.make_key(model_name="m", prompt_version="default", prompt_hash="h")
    cache.set(key, "value", ttl=0)
    assert cache.get(key) == "value"


def test_cache_make_key_is_deterministic() -> None:
    k1 = ResponseCache.make_key(model_name="m", prompt_version="default", prompt_hash="h")
    k2 = ResponseCache.make_key(model_name="m", prompt_version="default", prompt_hash="h")
    assert k1 == k2


def test_cache_make_key_varies_by_model() -> None:
    k1 = ResponseCache.make_key(model_name="m1", prompt_version="default", prompt_hash="h")
    k2 = ResponseCache.make_key(model_name="m2", prompt_version="default", prompt_hash="h")
    assert k1 != k2


def test_cache_make_key_varies_by_version() -> None:
    k1 = ResponseCache.make_key(model_name="m", prompt_version="default", prompt_hash="h")
    k2 = ResponseCache.make_key(model_name="m", prompt_version="evidence_grounded", prompt_hash="h")
    assert k1 != k2


def test_cache_make_key_varies_by_hash() -> None:
    k1 = ResponseCache.make_key(model_name="m", prompt_version="default", prompt_hash="h1")
    k2 = ResponseCache.make_key(model_name="m", prompt_version="default", prompt_hash="h2")
    assert k1 != k2


def test_cache_make_key_varies_by_schema_version() -> None:
    k1 = ResponseCache.make_key(
        model_name="m", prompt_version="default", prompt_hash="h", schema_version="current"
    )
    k2 = ResponseCache.make_key(
        model_name="m", prompt_version="default", prompt_hash="h", schema_version="legacy"
    )
    assert k1 != k2


def test_hash_content_is_deterministic() -> None:
    h1 = ResponseCache.hash_content("hello world")
    h2 = ResponseCache.hash_content("hello world")
    assert h1 == h2
    assert len(h1) == 64  # SHA256 hex


def test_cache_invalidate_by_version() -> None:
    cache = ResponseCache()
    k1 = cache.make_key(model_name="m", prompt_version="default", prompt_hash="h1")
    k2 = cache.make_key(model_name="m", prompt_version="default", prompt_hash="h2")
    k3 = cache.make_key(model_name="m", prompt_version="evidence_grounded", prompt_hash="h3")
    cache.set(k1, "a", model_name="m", prompt_version="default")
    cache.set(k2, "b", model_name="m", prompt_version="default")
    cache.set(k3, "c", model_name="m", prompt_version="evidence_grounded")

    removed = cache.invalidate_by_version("default")
    assert removed == 2
    assert cache.get(k1) is None
    assert cache.get(k2) is None
    assert cache.get(k3) == "c"


def test_cache_invalidate_by_model() -> None:
    cache = ResponseCache()
    k1 = cache.make_key(model_name="m1", prompt_version="default", prompt_hash="h1")
    k2 = cache.make_key(model_name="m1", prompt_version="evidence_grounded", prompt_hash="h2")
    k3 = cache.make_key(model_name="m2", prompt_version="default", prompt_hash="h3")
    cache.set(k1, "a", model_name="m1", prompt_version="default")
    cache.set(k2, "b", model_name="m1", prompt_version="evidence_grounded")
    cache.set(k3, "c", model_name="m2", prompt_version="default")

    removed = cache.invalidate_by_model("m1")
    assert removed == 2
    assert cache.get(k1) is None
    assert cache.get(k3) == "c"


def test_cache_clear() -> None:
    cache = ResponseCache()
    k1 = cache.make_key(model_name="m", prompt_version="default", prompt_hash="h1")
    k2 = cache.make_key(model_name="m", prompt_version="default", prompt_hash="h2")
    cache.set(k1, "a")
    cache.set(k2, "b")

    count = cache.clear()
    assert count == 2
    assert cache.size == 0


def test_cache_size() -> None:
    cache = ResponseCache()
    assert cache.size == 0
    k = cache.make_key(model_name="m", prompt_version="default", prompt_hash="h")
    cache.set(k, "v")
    assert cache.size == 1


def test_cache_invalidate_specific_key() -> None:
    cache = ResponseCache()
    k = cache.make_key(model_name="m", prompt_version="default", prompt_hash="h")
    cache.set(k, "v")
    assert cache.invalidate(k) is True
    assert cache.get(k) is None
    assert cache.invalidate(k) is False
