"""DOI/arXiv-id keyed PDF download cache.

Purpose:
- Avoid re-downloading the same paper from different directions/seeds.
- Reduce external HTTP load on OpenAlex/S2/Unpaywall and OA venue PDFs.
- Provide deterministic cache keys so tests can assert lookup paths.

Cache layout (default):
    .cache/researchsensei/pdfs/
        doi_10_1109_tpami_34/             # key derived from DOI
            source.pdf
            meta.json
        arxiv_2401_12345/
            source.tar.gz
            meta.json
        url_<sha256_16hex>/
            source.pdf
            meta.json

Key priority (first non-empty wins):
    1. normalized DOI (10.xxxx/yyy -> doi_<slugs>)
    2. arxiv_id (strip ``v\\d+$`` suffix)
    3. sha256(pdf_url)[:16] when DOI and arXiv are unavailable

Cache-corruption defense:
- meta.json stores the expected sha256.
- get() re-hashes the file and compares. Mismatch -> treat as miss, evict.
- meta.json always in UTF-8.

This cache is process-safe for single-process use. Multi-process use would
require a file lock; we deliberately don't need it because DirectionRunner
and FullTextResolver are serial within a single job.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_DOI_URL_PREFIXES = ("https://doi.org/", "http://doi.org/", "doi:", "DOI:")
_ARXIV_PREFIXES = ("arXiv:", "arxiv:")
_ARXIV_VERSION_RE = re.compile(r"v\d+$")
_SAFE_NAME_RE = re.compile(r"[^a-zA-Z0-9_.-]+")
_PDF_BYTES = b"%PDF"
_GZIP_BYTES = b"\x1f\x8b"


def _default_cache_root() -> Path:
    env = os.getenv("RESEARCHSENSEI_PDF_CACHE_DIR", "").strip()
    if env:
        return Path(env)
    return Path(".cache/researchsensei/pdfs")


def _normalize_doi(doi: str) -> str:
    if not doi:
        return ""
    s = doi.strip()
    for prefix in _DOI_URL_PREFIXES:
        if s.lower().startswith(prefix.lower()):
            s = s[len(prefix):]
            break
    return s.strip()


def _normalize_arxiv_id(arxiv_id: str) -> str:
    if not arxiv_id:
        return ""
    s = arxiv_id.strip()
    for prefix in _ARXIV_PREFIXES:
        if s.lower().startswith(prefix.lower()):
            s = s[len(prefix):]
            break
    return _ARXIV_VERSION_RE.sub("", s)


def _sanitize_key(value: str) -> str:
    safe = _SAFE_NAME_RE.sub("_", value).strip("._-")
    return safe[:120] or "raw"


def cache_key(*, doi: str = "", arxiv_id: str = "", pdf_url: str = "") -> str:
    """Return the cache directory name for the given keys, or '' if all empty."""
    norm_doi = _normalize_doi(doi)
    if norm_doi:
        return "doi_" + _sanitize_key(norm_doi)
    norm_aid = _normalize_arxiv_id(arxiv_id)
    if norm_aid:
        return "arxiv_" + _sanitize_key(norm_aid)
    if pdf_url:
        return "url_" + hashlib.sha256(pdf_url.encode("utf-8")).hexdigest()[:16]
    return ""


@dataclass(frozen=True)
class CacheMeta:
    """Snapshot of the meta.json contents."""
    doi: str = ""
    arxiv_id: str = ""
    pdf_url: str = ""
    source_url: str = ""
    sha256: str = ""
    file_size: int = 0
    content_type: str = ""
    venue: str = ""
    fulltext_source: str = ""
    fetched_at: str = ""
    extension: str = "pdf"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CacheMeta":
        return cls(
            doi=str(data.get("doi") or ""),
            arxiv_id=str(data.get("arxiv_id") or ""),
            pdf_url=str(data.get("pdf_url") or ""),
            source_url=str(data.get("source_url") or ""),
            sha256=str(data.get("sha256") or ""),
            file_size=int(data.get("file_size") or 0),
            content_type=str(data.get("content_type") or ""),
            venue=str(data.get("venue") or ""),
            fulltext_source=str(data.get("fulltext_source") or ""),
            fetched_at=str(data.get("fetched_at") or ""),
            extension=str(data.get("extension") or "pdf"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "doi": self.doi,
            "arxiv_id": self.arxiv_id,
            "pdf_url": self.pdf_url,
            "source_url": self.source_url,
            "sha256": self.sha256,
            "file_size": self.file_size,
            "content_type": self.content_type,
            "venue": self.venue,
            "fulltext_source": self.fulltext_source,
            "fetched_at": self.fetched_at,
            "extension": self.extension,
        }


class PdfCache:
    """File-system PDF cache with key normalization and sha256 validation."""

    def __init__(
        self,
        cache_root: Path | None = None,
        *,
        max_age_days: int | None = None,
        max_total_bytes: int | None = None,
    ) -> None:
        self.cache_root = Path(cache_root) if cache_root else _default_cache_root()
        self.cache_root.mkdir(parents=True, exist_ok=True)
        env_max_age_days = os.getenv("RESEARCHSENSEI_PDF_CACHE_MAX_AGE_DAYS", "")
        if max_age_days is None and env_max_age_days.strip():
            try:
                max_age_days = int(env_max_age_days)
            except ValueError:
                max_age_days = None
        self.max_age_days = max_age_days   # None or -1 = infinite
        self.max_total_bytes = max_total_bytes

    # ---------------------------------------------------------------------------
    # Public read / write
    # ---------------------------------------------------------------------------

    def get(
        self,
        *,
        doi: str = "",
        arxiv_id: str = "",
        pdf_url: str = "",
    ) -> Path | None:
        """Return the path of a cached PDF, or None on miss / corruption / expiry."""
        key = cache_key(doi=doi, arxiv_id=arxiv_id, pdf_url=pdf_url)
        if not key:
            return None
        entry_dir = self.cache_root / key
        meta_path = entry_dir / "meta.json"
        blob_name = self._blob_name_for_key(entry_dir)
        if not meta_path.exists() or not blob_name.exists():
            return None
        try:
            meta = CacheMeta.from_dict(json.loads(meta_path.read_text(encoding="utf-8")))
        except Exception:
            return None
        # expiry
        if self._is_expired(meta.fetched_at):
            return None
        # integrity
        actual_sha = hashlib.sha256(blob_name.read_bytes()).hexdigest()
        if meta.sha256 and actual_sha != meta.sha256:
            self._evict(entry_dir)
            return None
        # size sanity
        if meta.file_size and blob_name.stat().st_size != meta.file_size:
            self._evict(entry_dir)
            return None
        return blob_name

    def meta(
        self,
        *,
        doi: str = "",
        arxiv_id: str = "",
        pdf_url: str = "",
    ) -> CacheMeta | None:
        """Return cache meta for a key without loading the blob payload."""
        key = cache_key(doi=doi, arxiv_id=arxiv_id, pdf_url=pdf_url)
        if not key:
            return None
        meta_path = self.cache_root / key / "meta.json"
        if not meta_path.exists():
            return None
        try:
            return CacheMeta.from_dict(json.loads(meta_path.read_text(encoding="utf-8")))
        except Exception:
            return None

    def put(
        self,
        content: bytes,
        *,
        doi: str = "",
        arxiv_id: str = "",
        pdf_url: str = "",
        source_url: str = "",
        content_type: str = "",
        venue: str = "",
        fulltext_source: str = "",
        extension: str = "pdf",
    ) -> Path:
        """Persist content under the key derived from the strongest available identifier.

        `extension` defaults to "pdf" but should be "tar.gz" or "tex" if the
        content is arXiv LaTeX source. The blob is named `source.<ext>`.
        """
        if not content:
            raise ValueError("PdfCache.put: empty content")
        key = cache_key(doi=doi, arxiv_id=arxiv_id, pdf_url=pdf_url)
        if not key:
            # Synthesize a key from content hash so we never silently drop writes.
            key = "blob_" + hashlib.sha256(content).hexdigest()[:16]
        entry = self.cache_root / key
        entry.mkdir(parents=True, exist_ok=True)
        blob = entry / f"source.{extension}"
        blob.write_bytes(content)
        sha = hashlib.sha256(content).hexdigest()
        meta = CacheMeta(
            doi=_normalize_doi(doi),
            arxiv_id=_normalize_arxiv_id(arxiv_id),
            pdf_url=pdf_url,
            source_url=source_url,
            sha256=sha,
            file_size=len(content),
            content_type=content_type,
            venue=venue,
            fulltext_source=fulltext_source,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            extension=extension,
        )
        (entry / "meta.json").write_text(
            json.dumps(meta.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._maybe_enforce_size_budget()
        return blob

    def evict_stale(self) -> int:
        """Remove entries older than max_age_days. Returns evicted count."""
        if self.max_age_days is None or self.max_age_days < 0:
            return 0
        now = time.time()
        evicted = 0
        for entry in self.cache_root.iterdir():
            if not entry.is_dir():
                continue
            meta_path = entry / "meta.json"
            if not meta_path.exists():
                # orphan dir, no metadata — remove
                self._evict(entry)
                evicted += 1
                continue
            try:
                meta = CacheMeta.from_dict(json.loads(meta_path.read_text(encoding="utf-8")))
            except Exception:
                self._evict(entry)
                evicted += 1
                continue
            if self._is_expired(meta.fetched_at):
                self._evict(entry)
                evicted += 1
        return evicted

    def total_size_bytes(self) -> int:
        total = 0
        for entry in self.cache_root.iterdir():
            if not entry.is_dir():
                continue
            for child in entry.iterdir():
                if child.is_file():
                    try:
                        total += child.stat().st_size
                    except OSError:
                        pass
        return total

    def clear(self) -> int:
        """Delete all cache entries. Returns count removed."""
        count = 0
        for entry in self.cache_root.iterdir():
            if entry.is_dir():
                self._evict(entry)
                count += 1
        return count

    # ---------------------------------------------------------------------------
    # Internals
    # ---------------------------------------------------------------------------

    @staticmethod
    def _blob_name_for_key(entry_dir: Path) -> Path | None:
        """Return the first matching source.<ext> file in entry_dir, or None."""
        if not entry_dir.exists():
            return None
        # Prefer source.pdf > source.tar.gz > source.tex
        for ext in ("pdf", "tar.gz", "tex", "html", "txt"):
            p = entry_dir / f"source.{ext}"
            if p.exists():
                return p
        return None

    def _is_expired(self, fetched_at: str) -> bool:
        if not fetched_at or self.max_age_days is None or self.max_age_days < 0:
            return False
        try:
            ts = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
        except ValueError:
            return False
        age_sec = (datetime.now(timezone.utc) - ts).total_seconds()
        return age_sec > self.max_age_days * 86400.0

    @staticmethod
    def _evict(entry_dir: Path) -> None:
        if not entry_dir.exists():
            return
        try:
            for child in entry_dir.iterdir():
                try:
                    child.unlink()
                except OSError:
                    pass
            entry_dir.rmdir()
        except OSError:
            pass

    def _maybe_enforce_size_budget(self) -> None:
        if not self.max_total_bytes:
            return
        # LRU-ish: evict oldest until under budget
        entries: list[tuple[float, Path]] = []
        for entry in self.cache_root.iterdir():
            if not entry.is_dir():
                continue
            meta_path = entry / "meta.json"
            if not meta_path.exists():
                continue
            try:
                meta = CacheMeta.from_dict(json.loads(meta_path.read_text(encoding="utf-8")))
            except Exception:
                continue
            try:
                ts = datetime.fromisoformat(meta.fetched_at.replace("Z", "+00:00"))
                entries.append((ts.timestamp(), entry))
            except Exception:
                continue
        entries.sort(key=lambda t: t[0])
        total = self.total_size_bytes()
        for _, entry in entries:
            if total <= self.max_total_bytes:
                return
            size_entry = sum(f.stat().st_size for f in entry.iterdir() if f.is_file())
            self._evict(entry)
            total -= size_entry


__all__ = [
    "PdfCache",
    "CacheMeta",
    "cache_key",
]
