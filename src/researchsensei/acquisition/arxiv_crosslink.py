"""Reverse-lookup arxiv_id from OpenAlex / Semantic Scholar raw metadata.

Purpose:
- Many A-class papers (TPAMI, IEEE S&P, etc.) are paywalled, but authors
  simultaneously post to arXiv. OpenAlex/S2 metadata frequently records the
  arXiv version (via `primary_location.source.id` or `openAccessPdf.url`),
  even when the paper's primary venue field says something else.

- When `CandidatePaper.arxiv_id` is empty, downstream code can call
  `ArxivCrosslink.resolve(candidate)` to find a hidden arxiv_id, then route
  the candidate through arXiv's source/PDF pipeline.

Lookup strategy (return the first non-empty match):
1. Scan candidate URL-like fields (pdf_url, source_url, landing_url, url, and
   the candidate_pdf_urls/source_urls/html_urls lists) with arXiv URL regex.
2. Scan ``raw_source_metadata``:
   - OpenAlex: ``primary_location``/``best_oa_location`` whose ``source.id`` is
     an arxiv.org source id, then extract arxiv_id from the location's pdf_url
     or landing_page_url.
   - OpenAlex: ``locations`` list (multi-location), same source-id check.
   - Semantic Scholar: ``openAccessPdf.url`` containing an arxiv URL.
   - Semantic Scholar: ``externalIds.ArXiv`` (preferred when present).
3. As a last resort, call OpenAlex API to fetch the work by DOI and apply the
   same scan. This is opt-in (constructor flag ``network_lookup=True``)
   because it costs a live HTTP call per candidate.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------
# arXiv IDs follow either the new (YYMM.NNNNN) or legacy (category/YYMMNNN) format.
_ARXIV_URL_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"arxiv\.org/(?:abs|pdf|e-print)/([0-9]{4}\.[0-9]{4,5}(?:v[0-9]+)?)", re.I),
    re.compile(r"arxiv\.info/([0-9]{4}\.[0-9]{4,5}(?:v[0-9]+)?)", re.I),
    # OpenAlex occasionally wraps arxiv ids in a redirect URL like
    # /v1/works/doi:10.48550/arxiv.2103.02907 ; the DOIs of arxiv items.
    re.compile(r"10\.48550/arxiv\.([0-9]{4}\.[0-9]{4,5}(?:v[0-9]+)?)", re.I),
)

# OpenAlex source IDs for arXiv.
# S4210160352 = "arXiv.org" (legacy); S4306400000-series varies; we union all known.
_OPENALEX_ARXIV_SOURCE_IDS: frozenset[str] = frozenset(
    {
        "S4210160352",  # "arXiv.org" canonical
        "S4210160000",  # alt arxiv source id observed historically
    }
)


def _extract_arxiv_from_text(text: str) -> str:
    """Return the first arxiv_id found in `text`, or '' on miss."""
    if not text:
        return ""
    for pat in _ARXIV_URL_PATTERNS:
        m = pat.search(text)
        if m:
            return m.group(1)
    return ""


def _strip_version(arxiv_id: str) -> str:
    """Strip a trailing ``v\\d+`` from arxiv_id."""
    return re.sub(r"v\d+$", "", arxiv_id.strip())


def _normalize_openalex_source_id(value: Any) -> str:
    """Return the trailing Sxxxxxxx portion of an OpenAlex source ID URL."""
    if value is None:
        return ""
    s = str(value).strip()
    if not s:
        return ""
    # "https://openalex.org/S4306420609" -> "S4306420609"
    return s.rsplit("/", 1)[-1]


# ---------------------------------------------------------------------------
# ArxivCrosslink
# ---------------------------------------------------------------------------


class ArxivCrosslink:
    """Reverse-lookup arxiv_id from OpenAlex / Semantic Scholar raw metadata.

    Construction:
        crosslink = ArxivCrosslink()                    # offline: uses metadata already on candidate
        crosslink = ArxivCrosslink(network_lookup=True)  # may issue OpenAlex API calls
    """

    def __init__(
        self,
        *,
        network_lookup: bool = False,
        http_client: httpx.Client | None = None,
        api_timeout_seconds: float = 20.0,
    ) -> None:
        self.network_lookup = network_lookup
        self.http_client = http_client
        self.api_timeout_seconds = api_timeout_seconds

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def resolve(self, candidate) -> str:  # CandidatePaper; imported lazily to avoid cycle
        """Return the first non-empty arxiv_id found, or '' on miss.

        Order:
        1. Pre-existing `candidate.arxiv_id` (don't overwrite)
        2. URL fields on the candidate
        3. OpenAlex/S2 raw_source_metadata keys
        4. OpenAlex live API (if ``network_lookup=True`` and candidate has a DOI)
        """
        if candidate is None:
            return ""
        if getattr(candidate, "arxiv_id", ""):
            return candidate.arxiv_id

        # 1. URL fields
        arxiv_id = self._scan_url_fields(candidate)
        if arxiv_id:
            return _strip_version(arxiv_id)

        # 2. raw_source_metadata
        arxiv_id = self._scan_raw_metadata(candidate)
        if arxiv_id:
            return _strip_version(arxiv_id)

        # 3. Live OpenAlex lookup (opt-in)
        doi = str(getattr(candidate, "doi", "") or "")
        if self.network_lookup and doi:
            arxiv_id = self._api_lookup_doi(doi)
            if arxiv_id:
                return _strip_version(arxiv_id)

        return ""

    # ------------------------------------------------------------------
    # Step 1: URL fields
    # ------------------------------------------------------------------
    def _scan_url_fields(self, candidate) -> str:
        # Direct URL fields
        fields = (
            getattr(candidate, "pdf_url", ""),
            getattr(candidate, "source_url", ""),
            getattr(candidate, "landing_url", ""),
            getattr(candidate, "url", ""),
        )
        for v in fields:
            aid = _extract_arxiv_from_text(str(v or ""))
            if aid:
                return aid

        # List fields
        for list_attr in ("candidate_pdf_urls", "candidate_source_urls", "candidate_html_urls"):
            for v in getattr(candidate, list_attr, []) or []:
                aid = _extract_arxiv_from_text(str(v or ""))
                if aid:
                    return aid
        return ""

    # ------------------------------------------------------------------
    # Step 2: raw_source_metadata (works for OpenAlex adapter output and S2)
    # ------------------------------------------------------------------
    def _scan_raw_metadata(self, candidate) -> str:
        raw = getattr(candidate, "raw_source_metadata", None) or {}
        if not isinstance(raw, dict):
            return ""

        # OpenAlex: scan primary/best_oa + locations list
        for key in ("primary_location", "best_oa_location"):
            loc = raw.get(key) or {}
            aid = self._scan_openalex_location(loc)
            if aid:
                return aid

        # OpenAlex: locations list (full list of OA copies)
        locations = raw.get("locations")
        if isinstance(locations, list):
            for loc in locations:
                if not isinstance(loc, dict):
                    continue
                aid = self._scan_openalex_location(loc)
                if aid:
                    return aid

        # Semantic Scholar: openAccessPdf.url
        oa_pdf = raw.get("openAccessPdf")
        if isinstance(oa_pdf, dict):
            aid = _extract_arxiv_from_text(str(oa_pdf.get("url") or ""))
            if aid:
                return aid

        # Semantic Scholar: externalIds.ArXiv (preferred when present)
        ext_ids = raw.get("externalIds")
        if isinstance(ext_ids, dict):
            direct = str(ext_ids.get("ArXiv") or "").strip()
            if direct:
                # externalIds.ArXiv is the bare id already; sometimes is "2401.12345" or "2401.12345v2"
                if re.fullmatch(r"\d{4}\.\d{4,5}(?:v\d+)?", direct):
                    return direct
                # If it's the arxiv DOI form, extract
                aid = _extract_arxiv_from_text(f"10.48550/arxiv.{direct}")
                if aid:
                    return aid

        # Try probing nested raw OpenAlex row we may have preserved.
        raw_row = raw.get("_raw_row")
        if isinstance(raw_row, dict):
            loc = raw_row.get("primary_location") or {}
            aid = self._scan_openalex_location(loc)
            if aid:
                return aid
            loc = raw_row.get("best_oa_location") or {}
            aid = self._scan_openalex_location(loc)
            if aid:
                return aid
            for loc in raw_row.get("locations") or []:
                if not isinstance(loc, dict):
                    continue
                aid = self._scan_openalex_location(loc)
                if aid:
                    return aid

        return ""

    @staticmethod
    def _scan_openalex_location(loc: dict) -> str:
        if not isinstance(loc, dict):
            return ""
        source = loc.get("source") or {}
        if not isinstance(source, dict):
            return ""
        source_id = _normalize_openalex_source_id(source.get("id") or "")
        # OpenAlex arxiv source id check
        is_arxiv_source = (
            source_id in _OPENALEX_ARXIV_SOURCE_IDS
            or "arxiv" in (str(source.get("display_name") or "")).lower()
            or "arxiv" in source_id.lower()
        )
        # If the source is arxiv, fish the id out of its URL fields.
        if is_arxiv_source:
            for k in ("pdf_url", "landing_page_url", "url"):
                aid = _extract_arxiv_from_text(str(loc.get(k) or ""))
                if aid:
                    return aid
        # Even if not arxiv-tagged, the pdf_url itself may contain arxiv (e.g., the
        # arxiv location is the best_oa_location). Try the URL anyway.
        for k in ("pdf_url", "landing_page_url", "url"):
            aid = _extract_arxiv_from_text(str(loc.get(k) or ""))
            if aid:
                return aid
        return ""

    # ------------------------------------------------------------------
    # Step 3: OpenAlex API live lookup by DOI
    # ------------------------------------------------------------------
    def _api_lookup_doi(self, doi: str) -> str:
        doi = (doi or "").strip()
        if not doi:
            return ""
        try:
            from pyalex import Works
        except ImportError:
            logger.warning("pyalex not available; cannot live-lookup arxiv_id by DOI")
            return ""
        try:
            work_lookup = Works()
            url = doi
            if not url.startswith("http"):
                url = f"https://doi.org/{url}"
            work = work_lookup[url]
        except Exception as exc:
            logger.info("arxiv crosslink live lookup failed for %s: %s", doi, exc)
            return ""
        # Reuse the same scan via a synthetic OpenAlex-shaped record.
        synthetic_raw = {
            "primary_location": work.get("primary_location") or {},
            "best_oa_location": work.get("best_oa_location") or {},
            "locations": work.get("locations") or [],
        }
        # Also probe _raw_row since pyalex returns a dict directly.
        return self._scan_raw_metadata(
            type("SyntheticCandidate", (), {"raw_source_metadata": synthetic_raw, "arxiv_id": ""})
        )


__all__ = ["ArxivCrosslink"]
