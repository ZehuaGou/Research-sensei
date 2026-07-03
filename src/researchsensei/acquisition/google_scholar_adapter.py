from __future__ import annotations

import importlib.util
import os
import re
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlparse

from researchsensei.acquisition.venue_registry import is_known_oa_landing
from researchsensei.schemas import CandidatePaper

_MCP_REPO_URL = "https://github.com/JackKuo666/Google-Scholar-MCP-Server.git"
_MCP_MODULE_FILE = "google_scholar_web_search.py"
_CACHE_LOCK = threading.Lock()
_RESPONSE_CACHE: dict[tuple[str, int], tuple[float, list[dict[str, object]]]] = {}
_LAST_REQUEST_AT = 0.0


class GoogleScholarAdapter:
    """Google Scholar discovery adapter backed by JackKuo666's MCP project.

    The external project exposes ``google_scholar_web_search.google_scholar_search``
    and an MCP server around it. ResearchSensei keeps only a thin adapter here:
    call that project, normalize its result dictionaries into CandidatePaper,
    then let FullTextResolver handle legal OA/full-text resolution.
    """

    def __init__(
        self,
        *,
        search_function: Callable[[str, int], list[dict[str, object]]] | None = None,
        cache_ttl_seconds: float = 15 * 60,
        min_request_interval_seconds: float | None = None,
        max_results_cap: int = 20,
        clock: Callable[[], float] | None = None,
        sleeper: Callable[[float], None] | None = None,
    ) -> None:
        self.search_function = search_function
        self.cache_ttl_seconds = cache_ttl_seconds
        self.min_request_interval_seconds = (
            _env_float("RESEARCHSENSEI_GOOGLE_SCHOLAR_MIN_INTERVAL_SECONDS", 30.0)
            if min_request_interval_seconds is None
            else min_request_interval_seconds
        )
        self.max_results_cap = max(max_results_cap, 1)
        self.clock = clock or time.monotonic
        self.sleeper = sleeper or time.sleep

    def search(self, query: str, max_results: int = 20) -> list[CandidatePaper]:
        clean_query = " ".join(query.split())
        if not clean_query:
            return []
        limit = min(max_results, self.max_results_cap)
        cache_key = (clean_query.lower(), limit)
        rows = self._get_cached(cache_key)
        if rows is None:
            rows = self._search_rows(clean_query, limit)
            self._set_cached(cache_key, rows)
        return [self._to_candidate(row, index=index) for index, row in enumerate(rows, 1) if _title(row)]

    def _search_rows(self, query: str, limit: int) -> list[dict[str, object]]:
        search_function = self.search_function or _load_mcp_google_scholar_search()
        self._throttle_before_request()
        try:
            rows = search_function(query, limit)
        except Exception as exc:
            raise RuntimeError(f"Google Scholar MCP search failed: {type(exc).__name__}: {str(exc)[:160]}") from exc
        return [row for row in (rows or []) if isinstance(row, dict)]

    def _to_candidate(self, row: dict[str, object], *, index: int) -> CandidatePaper:
        title = _title(row)
        author_line = _field(row, "Authors", "authors")
        url = _field(row, "URL", "url", "Link", "link")
        abstract = _field(row, "Abstract", "abstract")
        parsed = _parse_google_scholar_author_line(author_line)
        inferred_venue = _venue_from_url(url)
        venue = _choose_venue(parsed["venue"], inferred_venue)
        scholar_id = _stable_id(title)
        arxiv_id = _arxiv_id_from_text(url)
        pdf_url = _pdf_url_from_text(url)
        return CandidatePaper(
            paper_id=f"google_scholar_{scholar_id}",
            title=title,
            authors=parsed["authors"],
            year=parsed["year"],
            venue=venue,
            source="google_scholar",
            sources=["google_scholar"],
            source_ids={"google_scholar": scholar_id},
            url=url,
            landing_url=url,
            arxiv_id=arxiv_id,
            abstract=abstract,
            pdf_url=pdf_url,
            candidate_pdf_urls=[pdf_url] if pdf_url else [],
            candidate_html_urls=[url] if url and url != pdf_url else [],
            open_access=bool(pdf_url or arxiv_id),
            pdf_available=bool(pdf_url),
            source_confidence="medium",
            metadata_confidence="medium" if title and (author_line or url) else "low",
            raw_source_metadata={
                "rank": index,
                "mcp_project": "JackKuo666/Google-Scholar-MCP-Server",
                "venue_inferred_from_url": bool(inferred_venue and inferred_venue == venue),
                "raw_result": dict(row),
                "note": "Google Scholar MCP is used for discovery; full text is resolved by legal OA/source resolvers.",
            },
        )

    def _throttle_before_request(self) -> None:
        global _LAST_REQUEST_AT
        if self.min_request_interval_seconds <= 0:
            return
        with _CACHE_LOCK:
            now = self.clock()
            wait = _LAST_REQUEST_AT + self.min_request_interval_seconds - now
            if wait > 0:
                self.sleeper(wait)
                now = self.clock()
            _LAST_REQUEST_AT = now

    def _get_cached(self, key: tuple[str, int]) -> list[dict[str, object]] | None:
        if self.cache_ttl_seconds <= 0:
            return None
        with _CACHE_LOCK:
            cached = _RESPONSE_CACHE.get(key)
            if cached is None:
                return None
            expires_at, rows = cached
            if expires_at <= self.clock():
                _RESPONSE_CACHE.pop(key, None)
                return None
            return rows

    def _set_cached(self, key: tuple[str, int], rows: list[dict[str, object]]) -> None:
        if self.cache_ttl_seconds <= 0:
            return
        with _CACHE_LOCK:
            _RESPONSE_CACHE[key] = (self.clock() + self.cache_ttl_seconds, rows)

    @classmethod
    def clear_cache(cls) -> None:
        global _LAST_REQUEST_AT
        with _CACHE_LOCK:
            _RESPONSE_CACHE.clear()
            _LAST_REQUEST_AT = 0.0


def google_scholar_enabled() -> bool:
    return _env_flag("RESEARCHSENSEI_ENABLE_GOOGLE_SCHOLAR") or _env_flag("RESEARCHSENSEI_GOOGLE_SCHOLAR_ENABLED")


def _load_mcp_google_scholar_search() -> Callable[[str, int], list[dict[str, object]]]:
    try:
        from google_scholar_web_search import google_scholar_search
    except ImportError as import_error:
        for checkout in _mcp_checkout_candidates():
            search = _load_mcp_search_from_checkout(checkout)
            if search is not None:
                return search
        if _env_flag_default("RESEARCHSENSEI_GOOGLE_SCHOLAR_MCP_AUTO_CLONE", True):
            checkout = _default_mcp_checkout_dir()
            _clone_mcp_repo(checkout)
            search = _load_mcp_search_from_checkout(checkout)
            if search is not None:
                return search
        raise RuntimeError(
            "Google Scholar source requires JackKuo666/Google-Scholar-MCP-Server. "
            f"The upstream project is loaded from `{_MCP_MODULE_FILE}`, because its current Python packaging fails "
            "under pip's flat-layout module discovery. Set RESEARCHSENSEI_GOOGLE_SCHOLAR_MCP_PATH to a local clone, "
            "or allow auto-clone with RESEARCHSENSEI_GOOGLE_SCHOLAR_MCP_AUTO_CLONE=1."
        ) from import_error
    return google_scholar_search


def _mcp_checkout_candidates() -> list[Path]:
    candidates: list[Path] = []
    for env_name in ("RESEARCHSENSEI_GOOGLE_SCHOLAR_MCP_PATH", "GOOGLE_SCHOLAR_MCP_SERVER_PATH"):
        value = os.getenv(env_name, "").strip()
        if value:
            candidates.append(Path(value).expanduser())
    candidates.extend([
        _repo_root() / "third_party" / "Google-Scholar-MCP-Server",
        _default_mcp_checkout_dir(),
    ])
    result: list[Path] = []
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved not in result:
            result.append(resolved)
    return result


def _load_mcp_search_from_checkout(checkout: Path) -> Callable[[str, int], list[dict[str, object]]] | None:
    module_path = checkout / _MCP_MODULE_FILE
    if not module_path.exists():
        return None
    module_name = "researchsensei_external_google_scholar_web_search"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load Google Scholar MCP module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        raise RuntimeError(f"Google Scholar MCP module import failed from {module_path}: {type(exc).__name__}: {str(exc)[:160]}") from exc
    search = getattr(module, "google_scholar_search", None)
    if not callable(search):
        raise RuntimeError(f"Google Scholar MCP module at {module_path} has no callable google_scholar_search")
    return search


def _clone_mcp_repo(checkout: Path) -> None:
    module_path = checkout / _MCP_MODULE_FILE
    if module_path.exists():
        return
    if checkout.exists():
        raise RuntimeError(f"Google Scholar MCP checkout exists but is missing {_MCP_MODULE_FILE}: {checkout}")
    checkout.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", _MCP_REPO_URL, str(checkout)],
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except Exception as exc:
        raise RuntimeError(f"Could not clone Google Scholar MCP project from {_MCP_REPO_URL}: {type(exc).__name__}: {str(exc)[:200]}") from exc


def _default_mcp_checkout_dir() -> Path:
    return _repo_root() / ".cache" / "researchsensei" / "google-scholar-mcp-server"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _title(row: dict[str, object]) -> str:
    return _field(row, "Title", "title").strip()


def _field(row: dict[str, object], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value is not None:
            return str(value).strip()
    return ""


def _parse_google_scholar_author_line(value: str) -> dict[str, object]:
    parts = [part.strip() for part in str(value or "").split(" - ") if part.strip()]
    authors = _authors(parts[0] if parts else "")
    year = None
    venue = ""
    info_parts = parts[1:]
    for part in info_parts:
        match = re.search(r"\b(19|20)\d{2}\b", part)
        if match:
            year = int(match.group(0))
            break
    for part in info_parts:
        candidate = re.sub(r"\b(19|20)\d{2}\b", "", part).strip(" ,")
        if candidate and not _looks_like_host(candidate):
            venue = candidate
            break
    if not venue and info_parts:
        venue = re.sub(r"\b(19|20)\d{2}\b", "", info_parts[0]).strip(" ,")
    return {"authors": authors, "year": year, "venue": venue}


def _authors(raw: str) -> list[str]:
    text = str(raw or "").strip()
    if not text or text == "No authors available":
        return []
    return [author.strip() for author in re.split(r"\s+and\s+|,\s*", text) if author.strip()]


def _arxiv_id_from_text(text: str) -> str:
    match = re.search(r"arxiv\.org/(?:abs|pdf|e-print)/([0-9]{4}\.[0-9]{4,5}(?:v[0-9]+)?)", text, re.I)
    return match.group(1) if match else ""


def _pdf_url_from_text(text: str) -> str:
    value = str(text or "")
    lower = value.lower()
    if not lower.startswith(("http://", "https://")):
        return ""
    if "ojs.aaai.org" in lower and re.search(r"/article/(?:download|view)/\d+/\d+", lower):
        return value
    if "ieeexplore.ieee.org/stamp/stamp.jsp" in lower:
        return value
    return value if lower.endswith(".pdf") or "/pdf" in lower else ""


def _venue_from_url(url: str) -> str:
    value = str(url or "")
    if not value:
        return ""
    _, _, cfg = is_known_oa_landing(value)
    if cfg is not None:
        return cfg.canonical_name
    host = urlparse(value).netloc.lower()
    host_map = {
        "dl.acm.org": "ACM Digital Library",
        "ieeexplore.ieee.org": "IEEE Xplore",
        "link.springer.com": "Springer",
        "proceedings.neurips.cc": "NeurIPS",
        "proceedings.mlr.press": "PMLR",
        "openreview.net": "OpenReview",
        "aclanthology.org": "ACL Anthology",
        "www.usenix.org": "USENIX",
        "jmlr.org": "JMLR",
    }
    return host_map.get(host, "")


def _choose_venue(parsed_venue: str, inferred_venue: str) -> str:
    parsed = str(parsed_venue or "").strip()
    inferred = str(inferred_venue or "").strip()
    if inferred and (not parsed or _looks_like_host(parsed)):
        return inferred
    return parsed or inferred


def _looks_like_host(value: str) -> bool:
    lower = str(value or "").strip().lower()
    return bool(re.fullmatch(r"(?:www\.)?[a-z0-9.-]+\.[a-z]{2,}(?:/.*)?", lower))


def _stable_id(title: str) -> str:
    return "_".join(re.findall(r"[a-z0-9]+", title.lower()))[:80] or "unknown"


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _env_flag_default(name: str, default: bool) -> bool:
    value = os.getenv(name, "").strip().lower()
    if not value:
        return default
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off", "disabled"}:
        return False
    return default


def _env_float(name: str, default: float) -> float:
    try:
        value = os.getenv(name, "").strip()
        return float(value) if value else default
    except ValueError:
        return default
