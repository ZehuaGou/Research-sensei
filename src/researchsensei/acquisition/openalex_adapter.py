from __future__ import annotations

import logging
import os

import httpx
from pyalex import Works

from researchsensei.acquisition.venue_registry import VENUE_REGISTRY
from researchsensei.schemas import CandidatePaper, VenueRank

logger = logging.getLogger(__name__)

_OPENALEX_WORKS_API = "https://api.openalex.org/works"


class OpenAlexAdapter:
    """Mature OpenAlex adapter backed by `pyalex.Works`."""

    def __init__(
        self,
        works: Works | None = None,
        *,
        http_client: httpx.Client | None = None,
        enable_ccf_venue_boost: bool = True,
        ccf_venue_boost_extra_results: int = 8,
        ccf_venue_source_ids: list[str] | None = None,
    ) -> None:
        self.works = works or Works()
        self.http_client = http_client or httpx.Client(follow_redirects=True, trust_env=True)
        self.enable_ccf_venue_boost = enable_ccf_venue_boost
        self.ccf_venue_boost_extra_results = max(ccf_venue_boost_extra_results, 0)
        self.ccf_venue_source_ids = ccf_venue_source_ids or _ccf_venue_source_ids()

    def search(self, query: str, max_results: int = 20) -> list[CandidatePaper]:
        generic_error: Exception | None = None
        try:
            generic_rows = self.works.search(query).get(per_page=min(max_results, 50))
        except Exception as exc:
            generic_rows = []
            generic_error = exc

        venue_rows: list[dict] = []
        if self.enable_ccf_venue_boost:
            venue_rows = self.search_ccf_venues(query, max_results=max(max_results, self.ccf_venue_boost_extra_results))

        if generic_error and not generic_rows and not venue_rows:
            raise generic_error

        rows = _dedupe_rows([*venue_rows, *generic_rows])
        limit = max_results + (self.ccf_venue_boost_extra_results if venue_rows else 0)
        return [self._to_candidate(row) for row in rows[:limit] if row.get("title")]

    def search_ccf_venues(self, query: str, max_results: int = 20) -> list[dict]:
        """Search OpenAlex within known CCF A/A* venues via source-id filtering.

        This complements ordinary OpenAlex search: many strong CS papers are
        easier to retrieve when the search space is restricted to known venue
        sources instead of all scholarly full text.
        """
        source_ids = _unique([_normalize_openalex_source_id(value) for value in self.ccf_venue_source_ids])
        if not query.strip() or not source_ids:
            return []
        params = {
            "search": query,
            "filter": f"primary_location.source.id:{'|'.join(source_ids)}",
            "per-page": min(max_results, 50),
        }
        mailto = os.getenv("OPENALEX_EMAIL", "").strip() or os.getenv("RESEARCHSENSEI_CONTACT_EMAIL", "").strip()
        if mailto:
            params["mailto"] = mailto
        try:
            response = self.http_client.get(_OPENALEX_WORKS_API, params=params, timeout=20.0)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            logger.info("OpenAlex CCF venue boost failed for %s: %s", query[:80], exc)
            return []
        rows = data.get("results") if isinstance(data, dict) else []
        return [row for row in (rows or []) if isinstance(row, dict)]

    def _to_candidate(self, row: dict) -> CandidatePaper:
        work_id = str(row.get("id") or "")
        doi = str(row.get("doi") or "")
        primary_location = row.get("primary_location") or {}
        best_oa_location = row.get("best_oa_location") or {}
        open_access = row.get("open_access") or {}
        landing_url = (
            best_oa_location.get("landing_page_url")
            or primary_location.get("landing_page_url")
            or work_id
        )
        pdf_url = best_oa_location.get("pdf_url") or primary_location.get("pdf_url") or ""
        source = primary_location.get("source") or {}
        authors = []
        for authorship in row.get("authorships", []):
            author = authorship.get("author") or {}
            if author.get("display_name"):
                authors.append(author["display_name"])
        paper_id = work_id.rstrip("/").rsplit("/", 1)[-1] or doi or _stable_id(row.get("title", ""))
        return CandidatePaper(
            paper_id=paper_id,
            title=str(row.get("title") or ""),
            authors=authors,
            year=row.get("publication_year"),
            venue=str(source.get("display_name") or ""),
            source="openalex",
            sources=["openalex"],
            source_ids={"openalex": paper_id},
            url=work_id,
            landing_url=str(landing_url or ""),
            doi=doi,
            abstract=_openalex_abstract(row.get("abstract_inverted_index") or {}),
            citation_count=row.get("cited_by_count"),
            pdf_url=str(pdf_url or ""),
            open_access=bool((open_access or {}).get("is_oa") or pdf_url),
            pdf_available=bool(pdf_url),
            source_confidence="high" if work_id else "medium",
            metadata_confidence=_metadata_confidence(row, pdf_url),
            raw_source_metadata={
                "id": work_id,
                "doi": doi,
                "primary_location": _location_summary(primary_location),
                "best_oa_location": _location_summary(best_oa_location),
                "locations": [
                    _location_summary(location)
                    for location in (row.get("locations") or [])
                    if isinstance(location, dict)
                ],
                "open_access": {
                    "is_oa": (open_access or {}).get("is_oa"),
                    "oa_status": (open_access or {}).get("oa_status"),
                    "oa_url": (open_access or {}).get("oa_url"),
                },
            },
        )


def _openalex_abstract(inverted: dict) -> str:
    if not inverted:
        return ""
    positions: dict[int, str] = {}
    for word, indexes in inverted.items():
        for index in indexes:
            positions[int(index)] = word
    return " ".join(positions[index] for index in sorted(positions))


def _location_summary(location: dict) -> dict[str, object]:
    source = location.get("source") or {}
    source_summary = {}
    if isinstance(source, dict):
        source_summary = {
            "id": source.get("id"),
            "display_name": source.get("display_name"),
            "type": source.get("type"),
            "host_organization": source.get("host_organization"),
        }
    return {
        "pdf_url": location.get("pdf_url"),
        "landing_page_url": location.get("landing_page_url"),
        "url": location.get("url"),
        "is_oa": location.get("is_oa"),
        "license": location.get("license"),
        "version": location.get("version"),
        "source": source_summary,
        "source_display_name": source_summary.get("display_name"),
    }


def _metadata_confidence(row: dict, pdf_url: str) -> str:
    fields = [
        row.get("title"),
        row.get("publication_year"),
        row.get("doi"),
        row.get("abstract_inverted_index"),
        row.get("cited_by_count") is not None,
        pdf_url,
    ]
    filled = sum(1 for value in fields if value)
    if filled >= 5:
        return "high"
    if filled >= 3:
        return "medium"
    return "low"


def _stable_id(title: object) -> str:
    return "openalex_" + "_".join(str(title or "").lower().split())[:50]


def _ccf_venue_source_ids() -> list[str]:
    ids: list[str] = []
    for cfg in VENUE_REGISTRY.values():
        if cfg.rank in {VenueRank.A_STAR, VenueRank.A}:
            ids.extend(cfg.openalex_source_ids)
    return _unique([_normalize_openalex_source_id(value) for value in ids])


def _normalize_openalex_source_id(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return text.rstrip("/").rsplit("/", 1)[-1]


def _dedupe_rows(rows: list[dict]) -> list[dict]:
    result: list[dict] = []
    seen: set[str] = set()
    for row in rows:
        key = str(row.get("id") or row.get("doi") or row.get("title") or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(row)
    return result


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result
