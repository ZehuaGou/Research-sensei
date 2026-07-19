from __future__ import annotations

import logging
import os
import threading
import time
from collections.abc import Callable
from typing import Any

import httpx

from researchsensei.schemas import CandidatePaper

logger = logging.getLogger(__name__)

_S2_API = "https://api.semanticscholar.org/graph/v1/paper/search"
_S2_FIELDS = "paperId,title,authors,year,venue,abstract,tldr,citationCount,externalIds,openAccessPdf,url"

_RETRY_CODES = {429, 503}
_MAX_RETRIES = 3
_BACKOFF_429 = [3.0, 6.0, 12.0]
_BACKOFF_503 = [2.0, 4.0, 8.0]
_CACHE_LOCK = threading.Lock()
_RESPONSE_CACHE: dict[tuple[str, int, str, bool], tuple[float, dict]] = {}
_LAST_REQUEST_AT = 0.0
_RATE_LIMIT_UNTIL = 0.0


class SemanticScholarAdapter:
    """Semantic Scholar adapter using httpx REST API with proxy support.

    Uses httpx with trust_env=True so HTTP_PROXY/HTTPS_PROXY are respected.
    Supports SEMANTIC_SCHOLAR_API_KEY, or S2_API_KEY as a compatibility alias,
    for higher rate limits.
    """

    def __init__(
        self,
        *,
        timeout: float = 15.0,
        http_client: Any | None = None,
        cache_ttl_seconds: float = 15 * 60,
        min_request_interval_seconds: float = 1.0,
        rate_limit_cooldown_seconds: float = 60.0,
        clock: Callable[[], float] | None = None,
        sleeper: Callable[[float], None] | None = None,
    ) -> None:
        self.timeout = timeout
        self.api_key = (
            os.getenv("SEMANTIC_SCHOLAR_API_KEY", "").strip()
            or os.getenv("S2_API_KEY", "").strip()
        )
        self.http_client = http_client
        self.cache_ttl_seconds = cache_ttl_seconds
        self.min_request_interval_seconds = min_request_interval_seconds
        self.rate_limit_cooldown_seconds = rate_limit_cooldown_seconds
        self.clock = clock or time.monotonic
        self.sleeper = sleeper or time.sleep

    def search(self, query: str, max_results: int = 20) -> list[CandidatePaper]:
        """Search Semantic Scholar with retry/backoff on 429/503."""
        params = {
            "query": query,
            "limit": min(max_results, 100),
            "fields": _S2_FIELDS,
        }
        headers: dict[str, str] = {}
        if self.api_key:
            headers["x-api-key"] = self.api_key

        cache_key = _cache_key(params, has_api_key=bool(self.api_key))
        data = self._get_cached(cache_key)
        if data is None:
            data = self._fetch_with_retry(params, headers)
            self._set_cached(cache_key, data)
        results = data.get("data", [])
        return [self._to_candidate(row) for row in results[:max_results] if row.get("title")]

    def _fetch_with_retry(self, params: dict, headers: dict) -> dict:
        """Fetch from S2 API with retry/backoff."""
        last_retry_reason = "retryable errors"
        for attempt in range(_MAX_RETRIES):
            try:
                self._raise_if_rate_limited()
                self._throttle_before_request()
                resp = self._get(params, headers)

                if resp.status_code in _RETRY_CODES:
                    body_msg = ""
                    try:
                        body_msg = resp.json().get("message", "")
                    except Exception:
                        pass
                    backoff = _BACKOFF_429 if resp.status_code == 429 else _BACKOFF_503
                    wait = backoff[min(attempt, len(backoff) - 1)]
                    last_retry_reason = "rate limiting" if resp.status_code == 429 else "service unavailable"
                    if resp.status_code == 429:
                        self._activate_rate_limit_cooldown()
                        if attempt >= _MAX_RETRIES - 1:
                            break
                    logger.warning(
                        "Semantic Scholar got %d (%s), retry %d/%d in %.1fs",
                        resp.status_code, body_msg[:100], attempt + 1, _MAX_RETRIES, wait,
                    )
                    self.sleeper(wait)
                    continue

                resp.raise_for_status()
                return resp.json()

            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in _RETRY_CODES:
                    backoff = _BACKOFF_429 if exc.response.status_code == 429 else _BACKOFF_503
                    wait = backoff[min(attempt, len(backoff) - 1)]
                    last_retry_reason = "rate limiting" if exc.response.status_code == 429 else "service unavailable"
                    if exc.response.status_code == 429:
                        self._activate_rate_limit_cooldown()
                        if attempt >= _MAX_RETRIES - 1:
                            break
                    logger.warning(
                        "Semantic Scholar got %d, retry %d/%d in %.1fs",
                        exc.response.status_code, attempt + 1, _MAX_RETRIES, wait,
                    )
                    self.sleeper(wait)
                    continue
                logger.warning("Semantic Scholar HTTP error: %s", exc)
                raise
            except (httpx.TimeoutException, httpx.ConnectError, OSError) as exc:
                wait = _BACKOFF_503[min(attempt, len(_BACKOFF_503) - 1)]
                last_retry_reason = "network errors"
                logger.warning(
                    "Semantic Scholar network error: %s, retry %d/%d in %.1fs",
                    exc, attempt + 1, _MAX_RETRIES, wait,
                )
                self.sleeper(wait)
                continue

        raise RuntimeError(f"Semantic Scholar API exhausted {_MAX_RETRIES} retries after {last_retry_reason}")

    def _get(self, params: dict, headers: dict):
        if self.http_client is not None:
            return self.http_client.get(_S2_API, params=params, headers=headers)
        with httpx.Client(timeout=self.timeout, follow_redirects=True, trust_env=True) as client:
            return client.get(_S2_API, params=params, headers=headers)

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

    def _raise_if_rate_limited(self) -> None:
        with _CACHE_LOCK:
            remaining = _RATE_LIMIT_UNTIL - self.clock()
        if remaining > 0:
            raise RuntimeError(f"Semantic Scholar rate limited; cooldown active for {remaining:.1f}s")

    def _activate_rate_limit_cooldown(self) -> None:
        global _RATE_LIMIT_UNTIL
        if self.rate_limit_cooldown_seconds <= 0:
            return
        with _CACHE_LOCK:
            _RATE_LIMIT_UNTIL = max(_RATE_LIMIT_UNTIL, self.clock() + self.rate_limit_cooldown_seconds)

    def _get_cached(self, key: tuple[str, int, str, bool]) -> dict | None:
        if self.cache_ttl_seconds <= 0:
            return None
        with _CACHE_LOCK:
            cached = _RESPONSE_CACHE.get(key)
            if cached is None:
                return None
            expires_at, data = cached
            if expires_at <= self.clock():
                _RESPONSE_CACHE.pop(key, None)
                return None
            return data

    def _set_cached(self, key: tuple[str, int, str, bool], data: dict) -> None:
        if self.cache_ttl_seconds <= 0:
            return
        with _CACHE_LOCK:
            _RESPONSE_CACHE[key] = (self.clock() + self.cache_ttl_seconds, data)

    @classmethod
    def clear_cache(cls) -> None:
        global _LAST_REQUEST_AT, _RATE_LIMIT_UNTIL
        with _CACHE_LOCK:
            _RESPONSE_CACHE.clear()
            _LAST_REQUEST_AT = 0.0
            _RATE_LIMIT_UNTIL = 0.0

    def _to_candidate(self, row: dict) -> CandidatePaper:
        paper_id = str(row.get("paperId") or "")
        external_ids = row.get("externalIds") or {}
        doi = str(external_ids.get("DOI") or "")
        arxiv_id = str(external_ids.get("ArXiv") or "")
        open_access_pdf = row.get("openAccessPdf") or {}
        pdf_url = str(open_access_pdf.get("url") or "")
        tldr = row.get("tldr") or {}
        authors = [a.get("name", "") for a in (row.get("authors") or []) if a.get("name")]

        return CandidatePaper(
            paper_id=paper_id or doi or arxiv_id or _stable_id(row.get("title")),
            title=str(row.get("title") or ""),
            authors=authors,
            year=row.get("year"),
            venue=str(row.get("venue") or ""),
            source="semantic_scholar",
            sources=["semantic_scholar"],
            source_ids={"semantic_scholar": paper_id} if paper_id else {},
            url=str(row.get("url") or ""),
            landing_url=str(row.get("url") or ""),
            doi=doi,
            arxiv_id=arxiv_id,
            semantic_scholar_id=paper_id,
            abstract=str(row.get("abstract") or ""),
            tldr=str(tldr.get("text") if isinstance(tldr, dict) else ""),
            citation_count=row.get("citationCount"),
            pdf_url=pdf_url,
            open_access=bool(pdf_url),
            pdf_available=bool(pdf_url),
            source_confidence="high" if paper_id else "medium",
            metadata_confidence="high" if paper_id and (row.get("abstract") or tldr) else "medium",
            raw_source_metadata={
                "paperId": paper_id,
                "externalIds": dict(external_ids),
                "openAccessPdf": dict(open_access_pdf),
                "api_key_set": bool(self.api_key),
                "proxy_used": bool(os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")),
            },
        )


def _stable_id(title: object) -> str:
    return "s2_" + "_".join(str(title or "").lower().split())[:50]


def _cache_key(params: dict, *, has_api_key: bool) -> tuple[str, int, str, bool]:
    return (
        str(params.get("query") or "").strip().lower(),
        int(params.get("limit") or 0),
        str(params.get("fields") or ""),
        has_api_key,
    )
