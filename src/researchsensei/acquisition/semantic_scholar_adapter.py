from __future__ import annotations

import logging
import os
import time

import httpx

from researchsensei.schemas import CandidatePaper

logger = logging.getLogger(__name__)

_S2_API = "https://api.semanticscholar.org/graph/v1/paper/search"
_S2_FIELDS = "paperId,title,authors,year,venue,abstract,tldr,citationCount,externalIds,openAccessPdf,url"

_RETRY_CODES = {429, 503}
_MAX_RETRIES = 3
_BACKOFF_429 = [3.0, 6.0, 12.0]
_BACKOFF_503 = [2.0, 4.0, 8.0]


class SemanticScholarAdapter:
    """Semantic Scholar adapter using httpx REST API with proxy support.

    Uses httpx with trust_env=True so HTTP_PROXY/HTTPS_PROXY are respected.
    Supports SEMANTIC_SCHOLAR_API_KEY for higher rate limits.
    """

    def __init__(self, *, timeout: float = 15.0) -> None:
        self.timeout = timeout
        self.api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "").strip()

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

        data = self._fetch_with_retry(params, headers)
        results = data.get("data", [])
        return [self._to_candidate(row) for row in results[:max_results] if row.get("title")]

    def _fetch_with_retry(self, params: dict, headers: dict) -> dict:
        """Fetch from S2 API with retry/backoff."""
        for attempt in range(_MAX_RETRIES):
            try:
                with httpx.Client(timeout=self.timeout, follow_redirects=True, trust_env=True) as client:
                    resp = client.get(_S2_API, params=params, headers=headers)

                    if resp.status_code in _RETRY_CODES:
                        body_msg = ""
                        try:
                            body_msg = resp.json().get("message", "")
                        except Exception:
                            pass
                        backoff = _BACKOFF_429 if resp.status_code == 429 else _BACKOFF_503
                        wait = backoff[min(attempt, len(backoff) - 1)]
                        logger.warning(
                            "Semantic Scholar got %d (%s), retry %d/%d in %.1fs",
                            resp.status_code, body_msg[:100], attempt + 1, _MAX_RETRIES, wait,
                        )
                        time.sleep(wait)
                        continue

                    resp.raise_for_status()
                    return resp.json()

            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in _RETRY_CODES:
                    backoff = _BACKOFF_429 if exc.response.status_code == 429 else _BACKOFF_503
                    wait = backoff[min(attempt, len(backoff) - 1)]
                    logger.warning(
                        "Semantic Scholar got %d, retry %d/%d in %.1fs",
                        exc.response.status_code, attempt + 1, _MAX_RETRIES, wait,
                    )
                    time.sleep(wait)
                    continue
                logger.warning("Semantic Scholar HTTP error: %s", exc)
                raise
            except (httpx.TimeoutException, httpx.ConnectError, OSError) as exc:
                wait = _BACKOFF_503[min(attempt, len(_BACKOFF_503) - 1)]
                logger.warning(
                    "Semantic Scholar network error: %s, retry %d/%d in %.1fs",
                    exc, attempt + 1, _MAX_RETRIES, wait,
                )
                time.sleep(wait)
                continue

        raise RuntimeError(f"Semantic Scholar API exhausted {_MAX_RETRIES} retries")

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
