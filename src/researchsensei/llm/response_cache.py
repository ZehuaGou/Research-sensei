from __future__ import annotations

import time
from dataclasses import dataclass, field
from hashlib import sha256


@dataclass
class CacheEntry:
    value: str
    model_name: str = ""
    prompt_version: str = ""
    created_at: float = field(default_factory=time.time)
    expires_at: float | None = None
    hit_count: int = 0


class ResponseCache:
    """In-memory LLM response cache with TTL, version, and content-hash support."""

    def __init__(self, *, default_ttl: int = 3600) -> None:
        self._entries: dict[str, CacheEntry] = {}
        self.default_ttl = default_ttl
        self._stats = {"hits": 0, "misses": 0}

    @staticmethod
    def make_key(
        *,
        model_name: str,
        prompt_version: str,
        prompt_hash: str,
        schema_version: str = "current",
    ) -> str:
        """Build a deterministic cache key from request parameters."""
        raw = f"{model_name}||{prompt_version}||{prompt_hash}||{schema_version}"
        return sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def hash_content(content: str) -> str:
        """Hash arbitrary content for use as prompt_hash."""
        return sha256(content.encode("utf-8")).hexdigest()

    def get(self, key: str) -> str | None:
        """Retrieve a cached response. Returns None on miss or expiry."""
        entry = self._entries.get(key)
        if entry is None:
            self._stats["misses"] += 1
            return None
        if entry.expires_at is not None and time.time() > entry.expires_at:
            self._entries.pop(key, None)
            self._stats["misses"] += 1
            return None
        entry.hit_count += 1
        self._stats["hits"] += 1
        return entry.value

    def set(
        self,
        key: str,
        value: str,
        *,
        model_name: str = "",
        prompt_version: str = "",
        ttl: int | None = None,
    ) -> None:
        """Store a response in the cache."""
        effective_ttl = ttl if ttl is not None else self.default_ttl
        expires_at = time.time() + effective_ttl if effective_ttl > 0 else None
        self._entries[key] = CacheEntry(
            value=value,
            model_name=model_name,
            prompt_version=prompt_version,
            expires_at=expires_at,
        )

    def invalidate(self, key: str) -> bool:
        """Remove a specific cache entry. Returns True if it existed."""
        return self._entries.pop(key, None) is not None

    def invalidate_by_version(self, prompt_version: str) -> int:
        """Remove all entries with a specific prompt_version. Returns count removed."""
        to_remove = [
            k for k, v in self._entries.items() if v.prompt_version == prompt_version
        ]
        for k in to_remove:
            self._entries.pop(k, None)
        return len(to_remove)

    def invalidate_by_model(self, model_name: str) -> int:
        """Remove all entries for a specific model. Returns count removed."""
        to_remove = [
            k for k, v in self._entries.items() if v.model_name == model_name
        ]
        for k in to_remove:
            self._entries.pop(k, None)
        return len(to_remove)

    def clear(self) -> int:
        """Remove all cache entries. Returns count removed."""
        count = len(self._entries)
        self._entries.clear()
        return count

    @property
    def size(self) -> int:
        return len(self._entries)

    @property
    def stats(self) -> dict[str, int]:
        return dict(self._stats)
