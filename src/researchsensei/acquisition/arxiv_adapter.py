from __future__ import annotations

import logging
import os
import re
import time

import httpx

from researchsensei.schemas import CandidatePaper

logger = logging.getLogger(__name__)

_ARXIV_API = "https://export.arxiv.org/api/query"
_ARXIV_PDF_BASE = "https://arxiv.org/pdf"
_MIN_PDF_BYTES = 10_240  # 10 KB minimum for valid PDF

# Build User-Agent
_PROJECT_UA = "ResearchSensei/0.5 (+https://github.com/ZehuaGou/Research-sensei)"
_CONTACT_EMAIL = os.getenv("RESEARCHSENSEI_CONTACT_EMAIL", "").strip()
_USER_AGENT = f"{_PROJECT_UA} mailto:{_CONTACT_EMAIL}" if _CONTACT_EMAIL else _PROJECT_UA

# Retry config for 429/503
_RETRY_CODES = {429, 503}
_MAX_RETRIES = 3
_BACKOFF_429 = [5.0, 10.0, 15.0]
_BACKOFF_503 = [2.0, 4.0, 8.0]


class ArxivAdapter:
    """Robust arXiv adapter with User-Agent, retry/backoff, id_list lookup."""

    def __init__(self, *, timeout: float = 60.0) -> None:
        self.timeout = timeout
        self.headers = {"User-Agent": _USER_AGENT}

    def search(self, query: str, max_results: int = 20) -> list[CandidatePaper]:
        """Search arXiv with retry/backoff on 429/503."""
        # Try multiple query strategies
        queries = self._build_queries(query)
        all_results: list[CandidatePaper] = []
        seen_ids: set[str] = set()

        for q in queries:
            try:
                results = self._fetch_atom(q, max_results=max_results)
                for r in results:
                    aid = r.arxiv_id if hasattr(r, 'arxiv_id') else ""
                    if aid and aid not in seen_ids:
                        seen_ids.add(aid)
                        all_results.append(r)
                if all_results:
                    break  # Got results, no need to try other query forms
            except Exception as exc:
                logger.warning("arXiv query '%s' failed: %s", q[:80], exc)
                if _should_stop_query_forms(exc):
                    raise RuntimeError(f"arXiv source unavailable: {exc}") from exc
                continue

        return all_results[:max_results]

    def search_by_id(self, arxiv_id: str) -> CandidatePaper | None:
        """Lookup a specific arXiv paper by ID using id_list parameter."""
        try:
            results = self._fetch_atom("", max_results=1, id_list=[arxiv_id])
            return results[0] if results else None
        except Exception as exc:
            logger.warning("arXiv id_list lookup for '%s' failed: %s", arxiv_id, exc)
            return None

    def download_pdf(self, arxiv_id: str, dest_dir: str) -> tuple[bool, str, int, str]:
        """Download arXiv PDF with retry/backoff.

        Returns: (success, local_path, file_size, sha256)
        """
        import hashlib

        pdf_url = f"{_ARXIV_PDF_BASE}/{arxiv_id}.pdf"
        os.makedirs(dest_dir, exist_ok=True)
        dest_path = os.path.join(dest_dir, "source.pdf")

        for attempt in range(_MAX_RETRIES):
            try:
                with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                    resp = client.get(pdf_url, headers=self.headers)

                    if resp.status_code in _RETRY_CODES:
                        backoff_schedule = _BACKOFF_429 if resp.status_code == 429 else _BACKOFF_503
                        wait = backoff_schedule[min(attempt, len(backoff_schedule) - 1)]
                        logger.warning(
                            "arXiv PDF download %s got %d, retry %d/%d in %.1fs",
                            arxiv_id, resp.status_code, attempt + 1, _MAX_RETRIES, wait,
                        )
                        time.sleep(wait)
                        continue

                    resp.raise_for_status()
                    content = resp.content

                    if len(content) < _MIN_PDF_BYTES:
                        logger.warning("arXiv PDF %s too small (%d bytes), likely error page", arxiv_id, len(content))
                        return False, "", 0, ""

                    if not content[:5] == b"%PDF-":
                        logger.warning("arXiv PDF %s missing %%PDF header", arxiv_id)
                        return False, "", 0, ""

                    with open(dest_path, "wb") as f:
                        f.write(content)

                    sha256 = hashlib.sha256(content).hexdigest()
                    return True, dest_path, len(content), sha256

            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in _RETRY_CODES:
                    backoff_schedule = _BACKOFF_429 if exc.response.status_code == 429 else _BACKOFF_503
                    wait = backoff_schedule[min(attempt, len(backoff_schedule) - 1)]
                    logger.warning(
                        "arXiv PDF download %s got %d, retry %d/%d in %.1fs",
                        arxiv_id, exc.response.status_code, attempt + 1, _MAX_RETRIES, wait,
                    )
                    time.sleep(wait)
                    continue
                logger.warning("arXiv PDF download %s HTTP error: %s", arxiv_id, exc)
                return False, "", 0, ""
            except (httpx.TimeoutException, httpx.ConnectError, OSError) as exc:
                wait = _BACKOFF_503[min(attempt, len(_BACKOFF_503) - 1)]
                logger.warning(
                    "arXiv PDF download %s network error: %s, retry %d/%d in %.1fs",
                    arxiv_id, exc, attempt + 1, _MAX_RETRIES, wait,
                )
                time.sleep(wait)
                continue

        logger.warning("arXiv PDF download %s exhausted %d retries", arxiv_id, _MAX_RETRIES)
        return False, "", 0, ""

    def _fetch_atom(self, query: str, *, max_results: int, id_list: list[str] | None = None) -> list[CandidatePaper]:
        """Fetch from arXiv Atom API with retry/backoff."""
        params: dict[str, str | int] = {
            "sortBy": "relevance",
            "sortOrder": "descending",
            "start": 0,
            "max_results": max_results,
        }
        if id_list:
            params["id_list"] = ",".join(id_list)
        else:
            params["search_query"] = query

        last_retry_reason = "retryable errors"
        for attempt in range(_MAX_RETRIES):
            try:
                with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                    resp = client.get(_ARXIV_API, params=params, headers=self.headers)

                    # Check for rate limit in body
                    body = resp.text
                    if "Rate exceeded" in body or "Please reduce" in body:
                        backoff = _BACKOFF_429[min(attempt, len(_BACKOFF_429) - 1)]
                        last_retry_reason = "rate limited by response body"
                        logger.warning(
                            "arXiv rate exceeded (body), retry %d/%d in %.1fs",
                            attempt + 1, _MAX_RETRIES, backoff,
                        )
                        time.sleep(backoff)
                        continue

                    if resp.status_code in _RETRY_CODES:
                        backoff_schedule = _BACKOFF_429 if resp.status_code == 429 else _BACKOFF_503
                        wait = backoff_schedule[min(attempt, len(backoff_schedule) - 1)]
                        last_retry_reason = "rate limited (429)" if resp.status_code == 429 else "service unavailable (503)"
                        logger.warning(
                            "arXiv API got %d, retry %d/%d in %.1fs",
                            resp.status_code, attempt + 1, _MAX_RETRIES, wait,
                        )
                        time.sleep(wait)
                        continue

                    resp.raise_for_status()
                    return self._parse_atom(body)

            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in _RETRY_CODES:
                    backoff_schedule = _BACKOFF_429 if exc.response.status_code == 429 else _BACKOFF_503
                    wait = backoff_schedule[min(attempt, len(backoff_schedule) - 1)]
                    last_retry_reason = "rate limited (429)" if exc.response.status_code == 429 else "service unavailable (503)"
                    logger.warning(
                        "arXiv API got %d, retry %d/%d in %.1fs",
                        exc.response.status_code, attempt + 1, _MAX_RETRIES, wait,
                    )
                    time.sleep(wait)
                    continue
                raise
            except (httpx.TimeoutException, httpx.ConnectError, OSError) as exc:
                wait = _BACKOFF_503[min(attempt, len(_BACKOFF_503) - 1)]
                last_retry_reason = "network errors"
                logger.warning(
                    "arXiv API network error: %s, retry %d/%d in %.1fs",
                    exc, attempt + 1, _MAX_RETRIES, wait,
                )
                time.sleep(wait)
                continue

        raise RuntimeError(f"arXiv API exhausted {_MAX_RETRIES} retries after {last_retry_reason} for query: {query[:80]}")

    def _parse_atom(self, xml_text: str) -> list[CandidatePaper]:
        """Parse arXiv Atom XML into CandidatePaper list."""
        import xml.etree.ElementTree as ET

        root = ET.fromstring(xml_text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        results: list[CandidatePaper] = []

        for entry in root.findall("atom:entry", ns):
            title_el = entry.find("atom:title", ns)
            title = _clean(title_el.text if title_el is not None else "")

            summary_el = entry.find("atom:summary", ns)
            abstract = _clean(summary_el.text if summary_el is not None else "")

            entry_id_el = entry.find("atom:id", ns)
            entry_id = (entry_id_el.text or "").strip() if entry_id_el is not None else ""

            arxiv_id = entry_id.rstrip("/").rsplit("/", 1)[-1] if entry_id else ""
            # Strip version suffix for id
            arxiv_id = re.sub(r"v\d+$", "", arxiv_id)

            pdf_url = ""
            source_url = ""
            for link in entry.findall("atom:link", ns):
                link_type = link.get("type", "")
                link_title = link.get("title", "")
                href = link.get("href", "")
                if link_title == "pdf" or link_type == "application/pdf":
                    pdf_url = href
                elif link_title == "doi":
                    pass
                elif "e-print" in (href or ""):
                    source_url = href

            published_el = entry.find("atom:published", ns)
            published_str = (published_el.text or "").strip() if published_el is not None else ""
            year = None
            if published_str and len(published_str) >= 4:
                try:
                    year = int(published_str[:4])
                except ValueError:
                    pass

            authors = []
            for author_el in entry.findall("atom:author", ns):
                name_el = author_el.find("atom:name", ns)
                if name_el is not None and name_el.text:
                    authors.append(name_el.text.strip())

            if not source_url and arxiv_id:
                source_url = f"https://arxiv.org/e-print/{arxiv_id}"

            results.append(CandidatePaper(
                paper_id=arxiv_id or _stable_id(title),
                title=title,
                authors=authors,
                year=year,
                venue="arXiv",
                source="arxiv",
                sources=["arxiv"],
                source_ids={"arxiv": arxiv_id} if arxiv_id else {},
                url=entry_id,
                landing_url=entry_id,
                arxiv_id=arxiv_id,
                abstract=abstract,
                pdf_url=pdf_url,
                source_url=source_url,
                open_access=bool(pdf_url),
                pdf_available=bool(pdf_url),
                source_confidence="high" if arxiv_id else "medium",
                metadata_confidence="medium",
                raw_source_metadata={
                    "entry_id": entry_id,
                    "published": published_str,
                    "user_agent": _USER_AGENT,
                    "contact_email_set": bool(_CONTACT_EMAIL),
                },
            ))

        return results

    def _build_queries(self, query: str) -> list[str]:
        """Build multiple query strategies for arXiv."""
        queries: list[str] = []

        # Strategy 1: all-fields query
        queries.append(f'all:"{query}"')

        # Strategy 2: title-only query
        queries.append(f'ti:"{query}"')

        # Strategy 3: raw query (fallback)
        queries.append(query)

        return queries


def _clean(value: object) -> str:
    return " ".join(str(value or "").split())


def _stable_id(title: object) -> str:
    return "arxiv_" + _clean(title).lower().replace(" ", "_")[:50] or "arxiv_unknown"


def _should_stop_query_forms(exc: Exception) -> bool:
    message = str(exc).lower()
    stop_terms = (
        "rate limited",
        "rate exceeded",
        "429",
        "service unavailable",
        "503",
        "network errors",
        "exhausted",
    )
    return any(term in message for term in stop_terms)
