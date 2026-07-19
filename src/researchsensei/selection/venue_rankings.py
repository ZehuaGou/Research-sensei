"""Selection-side venue ranking scoring.

Replaces the old ``TOP_VENUE_TERMS`` keyword substring match in
``SelectionService._venue_prestige`` with a lookup against the canonical
``VENUE_REGISTRY`` so that:
- CCF/CORE A* venues get the maximum boost (1.0)
- CCF/CORE A venues get a high boost (0.85)
- CCF/CORE B/C venues get partial credit (0.55/0.35)
- Unknown venues fall back to the historical 0.55/0.20 buckets.

The function intentionally does not import pyalex/httpx; the registry is
pure-data.
"""

from __future__ import annotations

import re

from researchsensei.acquisition.venue_registry import VENUE_REGISTRY, VenueConfig, is_known_oa_landing, lookup_venue
from researchsensei.schemas import CandidatePaper
from researchsensei.schemas.enums import VenueRank


# Fallback values for unknown venues; mirrors original SelectionService buckets.
_UNRANKED_NON_EMPTY_VENUE_SCORE = 0.55
_UNRANKED_EMPTY_VENUE_SCORE = 0.20
_ARXIV_BLACKLIST_VENUES = {"arxiv", "unknown", ""}


def venue_score(paper: CandidatePaper) -> float:
    """Return a venue prestige score in [0.0, 1.0] for the given candidate.

    Resolution:
    1. ``paper.venue_canonical_name`` (set by OpenAlex adapter) — short-circuit.
    2. Fuzzy ``paper.venue`` string via VENUE_REGISTRY.
    3. If the venue looks empty/arXiv -> 0.20.
    4. If the venue is unknown but non-empty -> 0.55.
    """
    venue_str = (paper.venue or "").strip()
    cfg = venue_config_for_paper(paper)
    if cfg is not None:
        return _rank_to_score(cfg.rank)
    if venue_str.lower() in _ARXIV_BLACKLIST_VENUES:
        return _UNRANKED_EMPTY_VENUE_SCORE
    return _UNRANKED_NON_EMPTY_VENUE_SCORE if venue_str else _UNRANKED_EMPTY_VENUE_SCORE


def venue_config_for_paper(paper: CandidatePaper) -> VenueConfig | None:
    """Return the registry entry that matched this paper's venue, if any."""
    canonical = (paper.venue_canonical_name or "").strip()
    if canonical:
        cfg = lookup_venue(canonical)
        if cfg is not None:
            return cfg
    cfg = lookup_venue(paper.venue or "")
    if cfg is not None:
        return cfg
    doi = str(paper.doi or "").strip().lower()
    if doi.startswith("10.1609/aaai."):
        return VENUE_REGISTRY.get("aaai")
    for venue_key in ("acl", "emnlp", "naacl", "ijcai", "vldb", "sigmod"):
        if re.search(rf"(?:^|[./_-]){venue_key}(?:[./_-]|$)", doi):
            return VENUE_REGISTRY.get(venue_key)
    for url in _candidate_venue_urls(paper):
        _is_oa, _archive_kind, url_cfg = is_known_oa_landing(url)
        if url_cfg is not None:
            return url_cfg
    return None


def venue_rank_label(paper: CandidatePaper) -> VenueRank:
    """Return the VenueRank enum value for the paper (UNRANKED if miss)."""
    cfg = venue_config_for_paper(paper)
    if cfg is not None:
        return cfg.rank
    return VenueRank.UNRANKED


def _rank_to_score(rank: VenueRank) -> float:
    if rank == VenueRank.A_STAR:
        return 1.0
    if rank == VenueRank.A:
        return 0.85
    if rank == VenueRank.B:
        return 0.55
    if rank == VenueRank.C:
        return 0.35
    return _UNRANKED_NON_EMPTY_VENUE_SCORE


def all_known_venues() -> list[str]:
    """Return canonical names for all registered venues (for diagnostics)."""
    return [cfg.canonical_name for cfg in VENUE_REGISTRY.values()]


def _candidate_venue_urls(paper: CandidatePaper) -> list[str]:
    urls = [
        paper.url,
        paper.landing_url,
        paper.pdf_url,
        paper.source_url,
        paper.selected_fulltext_url,
        *paper.candidate_pdf_urls,
        *paper.candidate_source_urls,
        *paper.candidate_html_urls,
    ]
    result: list[str] = []
    for url in urls:
        clean = str(url or "").strip()
        if clean and clean not in result:
            result.append(clean)
    return result


__all__ = [
    "venue_score",
    "venue_config_for_paper",
    "venue_rank_label",
    "all_known_venues",
]
