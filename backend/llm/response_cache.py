from __future__ import annotations

import time
from dataclasses import dataclass, field
from hashlib import sha256


@dataclass
class CacheEntry:
    value: str
    version: str | None = None
    expires_at: float | None = None


@dataclass
class ResponseCache:
    _entries: dict[str, CacheEntry] = field(default_factory=dict)

    def key(self, *parts: str) -> str:
        return sha256("||".join(parts).encode("utf-8")).hexdigest()

    def get(self, key: str) -> str | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if entry.expires_at and time.time() > entry.expires_at:
            self._entries.pop(key, None)
            return None
        return entry.value

    def set(self, key: str, value: str, *, version: str | None = None, ttl_seconds: int | None = None) -> None:
        expires_at = None
        if ttl_seconds is not None:
            expires_at = time.time() + ttl_seconds
        self._entries[key] = CacheEntry(value=value, version=version, expires_at=expires_at)

    def invalidate_version(self, version: str) -> None:
        to_remove = [k for k, v in self._entries.items() if v.version == version]
        for k in to_remove:
            self._entries.pop(k, None)

    def invalidate_prefix(self, prefix: str) -> None:
        to_remove = [k for k in self._entries if k.startswith(prefix)]
        for k in to_remove:
            self._entries.pop(k, None)

    def invalidate_all(self) -> None:
        self._entries.clear()
