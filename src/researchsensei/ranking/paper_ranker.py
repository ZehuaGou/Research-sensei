from __future__ import annotations

import os
from collections.abc import Callable, Sequence
from datetime import date
from typing import Any

from researchsensei.library import PaperLibraryStore
from researchsensei.schemas import CandidatePaper

DEFAULT_RERANKER_MODEL = "ms-marco-MiniLM-L-12-v2"


class PaperRanker:
    """Rerank paper candidates with an external model, then apply small quality guards."""

    def __init__(
        self,
        *,
        enabled: bool | None = None,
        model_name: str | None = None,
        max_length: int | None = None,
        ranker: Any | None = None,
        ranker_factory: Callable[..., Any] | None = None,
    ) -> None:
        # An explicitly injected ranker is a test/runtime dependency choice and
        # must not be silently disabled by a process-level environment value.
        self.enabled = (
            (ranker is not None or ranker_factory is not None or _env_enabled())
            if enabled is None
            else enabled
        )
        self.model_name = model_name or os.getenv("RESEARCHSENSEI_RERANKER_MODEL", "").strip() or DEFAULT_RERANKER_MODEL
        self.max_length = max_length or int(os.getenv("RESEARCHSENSEI_RERANKER_MAX_LENGTH", "384"))
        self._ranker = ranker
        self._ranker_factory = ranker_factory
        self.last_status = "not_loaded"
        self.last_error = ""

    def rank(self, query: str, candidates: Sequence[CandidatePaper]) -> list[CandidatePaper]:
        prepared = [_with_search_rank(candidate, index) for index, candidate in enumerate(candidates, start=1)]
        if not prepared:
            return []
        if not self.enabled:
            self.last_status = "disabled"
            return [_with_rank_result(candidate, index, None, 0.0, "reranker disabled") for index, candidate in enumerate(prepared, start=1)]

        try:
            ranker = self._load_ranker()
            request = self._request(query, prepared)
            raw_results = ranker.rerank(request)
        except Exception as exc:
            self.last_status = "fallback"
            self.last_error = f"{type(exc).__name__}: {str(exc)[:200]}"
            return [
                _with_rank_result(candidate, index, None, _quality_adjustment(candidate), f"reranker fallback: {self.last_error}")
                for index, candidate in enumerate(prepared, start=1)
            ]

        ranked: list[tuple[float, int, CandidatePaper, float]] = []
        by_index = {index: candidate for index, candidate in enumerate(prepared)}
        for fallback_rank, result in enumerate(raw_results, start=1):
            idx = int(result.get("id", fallback_rank - 1))
            candidate = by_index.get(idx)
            if candidate is None:
                continue
            rerank_score = float(result.get("score") or 0.0)
            quality = _quality_adjustment(candidate)
            rank_score = rerank_score + quality
            ranked.append((rank_score, fallback_rank, candidate, rerank_score))

        seen = {id(candidate) for _score, _rank, candidate, _rerank in ranked}
        for candidate in prepared:
            if id(candidate) not in seen:
                ranked.append((_quality_adjustment(candidate), len(ranked) + 1, candidate, 0.0))

        ranked.sort(key=lambda item: item[0], reverse=True)
        self.last_status = "flashrank"
        self.last_error = ""
        return [
            _with_rank_result(candidate, index, rerank_score, rank_score, _rank_reason(candidate, quality_score=rank_score - rerank_score))
            for index, (rank_score, _model_rank, candidate, rerank_score) in enumerate(ranked, start=1)
        ]

    def _load_ranker(self) -> Any:
        if self._ranker is not None:
            return self._ranker
        if self._ranker_factory is not None:
            self._ranker = self._ranker_factory(model_name=self.model_name, max_length=self.max_length)
            return self._ranker
        from flashrank import Ranker

        self._ranker = Ranker(model_name=self.model_name, max_length=self.max_length)
        return self._ranker

    @staticmethod
    def _request(query: str, candidates: Sequence[CandidatePaper]) -> Any:
        passages = [
            {
                "id": index,
                "text": _paper_text(candidate),
                "meta": {"paper_id": candidate.paper_id},
            }
            for index, candidate in enumerate(candidates)
        ]
        try:
            from flashrank import RerankRequest
        except ModuleNotFoundError:
            # Injected test/custom rankers can accept this dependency-free
            # request shape. The default loader still requires flashrank.
            return {"query": query, "passages": passages}
        return RerankRequest(query=query, passages=passages)


def select_downloads(
    candidates: Sequence[CandidatePaper],
    *,
    max_download_candidates: int,
    paper_library: PaperLibraryStore | None = None,
    require_relevance_gate: bool = False,
) -> list[CandidatePaper]:
    limit = max(max_download_candidates, 0)
    selected: list[CandidatePaper] = []
    selected_count = 0
    for index, candidate in enumerate(candidates, start=1):
        relevance_eligible = bool(
            not require_relevance_gate
            or (
                candidate.relevance_gate_evaluated
                and candidate.relevance_gate_passed
            )
        )
        is_selected = relevance_eligible and selected_count < limit
        if is_selected:
            selected_count += 1
        cached = paper_library.find_match(candidate) if paper_library is not None else None
        download_rank = int(candidate.rerank_rank or candidate.search_rank or index)
        raw_metadata = {
            **candidate.raw_source_metadata,
            "download_queue_rank": index,
            "download_selected": is_selected,
        }
        if paper_library is not None:
            raw_metadata["paper_library"] = {
                "status": "reusable" if cached is not None else "new_candidate",
                "paper_id": cached.paper_id if cached is not None else "",
                "local_path": cached.local_path if cached is not None else "",
            }
        venue = candidate.venue_canonical_name or candidate.venue or "unknown venue"
        venue_rank = candidate.venue_rank.value
        if not relevance_eligible:
            decision = "SKIPPED_RELEVANCE_GATE"
            reason = (
                "Not attempted because the deterministic relevance gate did not "
                f"pass: {candidate.relevance_reason or 'missing relevance assessment'}."
            )
        elif is_selected:
            decision = "SELECTED_BY_RERANKER"
            reuse_note = " local library hit; reuse before network download." if cached is not None else ""
            reason = (
                f"Selected for download by reranked order #{download_rank}; "
                f"venue='{venue}', CCF rank={venue_rank}.{reuse_note}"
            )
        else:
            decision = "SKIPPED_OVER_DOWNLOAD_LIMIT"
            reason = f"Not attempted because it is beyond the top {limit} relevance-cleared reranked download candidates."
        selected.append(
            candidate.model_copy(
                update={
                    "raw_source_metadata": raw_metadata,
                    "download_selected": is_selected,
                    "download_decision": decision,
                    "download_reason": reason,
                    "should_download": is_selected,
                    "should_a_read": is_selected,
                }
            )
        )
    return selected


def _with_search_rank(candidate: CandidatePaper, fallback: int) -> CandidatePaper:
    rank = _search_rank(candidate, fallback=fallback)
    return candidate.model_copy(
        update={
            "search_rank": rank,
            "raw_source_metadata": {
                **candidate.raw_source_metadata,
                "search_rank": rank,
            },
        }
    )


def _with_rank_result(
    candidate: CandidatePaper,
    rank: int,
    rerank_score: float | None,
    rank_score: float,
    reason: str,
) -> CandidatePaper:
    return candidate.model_copy(
        update={
            "rerank_rank": rank,
            "rerank_score": rerank_score,
            "rank_score": round(rank_score, 6),
            "rank_reason": reason,
            "raw_source_metadata": {
                **candidate.raw_source_metadata,
                "rerank_rank": rank,
                "rerank_score": rerank_score,
                "rank_score": round(rank_score, 6),
                "rank_reason": reason,
            },
        }
    )


def _paper_text(candidate: CandidatePaper) -> str:
    categories = candidate.raw_source_metadata.get("categories") or []
    if isinstance(categories, list):
        categories_text = "; ".join(str(item) for item in categories[:8])
    else:
        categories_text = str(categories)
    return "\n".join(
        value
        for value in [
            f"Title: {candidate.title}",
            f"Abstract: {(candidate.abstract or candidate.tldr)[:1600]}",
            f"Venue: {candidate.venue_canonical_name or candidate.venue}",
            f"Year: {candidate.year or ''}",
            f"Source: {candidate.source}",
            f"Categories: {categories_text}",
            f"DOI: {candidate.doi}",
        ]
        if value.strip().split(": ", 1)[-1]
    )


def _quality_adjustment(candidate: CandidatePaper) -> float:
    score = 0.0
    source = (candidate.source or "").lower()
    if source in {"arxiv", "dblp", "semantic", "semantic_scholar", "openalex"}:
        score += 0.04
    elif source == "crossref":
        score -= 0.05
    elif source == "core":
        score -= 0.07

    if candidate.fulltext_status == "source_ready":
        score += 0.08
    elif candidate.fulltext_status == "pdf_ready":
        score += 0.07
    elif candidate.fulltext_status == "html_ready":
        score += 0.01
    elif candidate.fulltext_status in {"failed", "metadata_only"}:
        score -= 0.12

    if candidate.arxiv_id or candidate.candidate_source_urls:
        score += 0.04
    elif candidate.pdf_url or candidate.candidate_pdf_urls:
        score += 0.03

    venue_rank = candidate.venue_rank.value
    if venue_rank == "A*":
        score += 0.06
    elif venue_rank == "A":
        score += 0.05
    elif venue_rank == "B":
        score += 0.03
    elif venue_rank == "C":
        score += 0.01
    elif candidate.venue or candidate.venue_canonical_name:
        score += 0.005

    citations = candidate.citation_count or 0
    if citations >= 1000:
        score += 0.03
    elif citations >= 100:
        score += 0.02
    elif citations >= 20:
        score += 0.01

    current_year = date.today().year
    if candidate.year is None:
        score -= 0.03
    elif candidate.year <= 1970 or candidate.year > current_year + 1:
        score -= 0.12
    return score


def _rank_reason(candidate: CandidatePaper, *, quality_score: float) -> str:
    parts = [f"flashrank model relevance; quality_guard={quality_score:+.2f}"]
    if candidate.fulltext_status:
        parts.append(f"fulltext={candidate.fulltext_status}")
    if candidate.source:
        parts.append(f"source={candidate.source}")
    if candidate.venue_rank.value != "unranked":
        parts.append(f"venue_rank={candidate.venue_rank.value}")
    if candidate.citation_count is not None:
        parts.append(f"citations={candidate.citation_count}")
    if candidate.year:
        parts.append(f"year={candidate.year}")
    return "; ".join(parts)


def _search_rank(candidate: CandidatePaper, *, fallback: int) -> int:
    metadata = candidate.raw_source_metadata or {}
    for key in ("search_rank", "rank", "download_queue_rank"):
        value = metadata.get(key)
        try:
            rank = int(str(value))
        except (TypeError, ValueError):
            continue
        if rank > 0:
            return rank
    return fallback


def _env_enabled() -> bool:
    value = os.getenv("RESEARCHSENSEI_RERANKER_ENABLED", "1").strip().lower()
    return value not in {"0", "false", "no", "off"}
