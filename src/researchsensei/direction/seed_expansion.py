from __future__ import annotations

import logging
import re
import time
from typing import Protocol

from researchsensei.acquisition import make_default_search_adapter
from researchsensei.core.config import DEFAULT_SEARCH_MAX_RESULTS
from researchsensei.schemas import (
    CandidatePaper,
    SeedExpansionBundle,
    SeedExpansionOrderItem,
    SeedExpansionPaper,
    SeedPaperInput,
    VerificationStatus,
)
from researchsensei.selection import SelectionService
from researchsensei.verification import CandidateVerifier

logger = logging.getLogger(__name__)


class SearchAdapter(Protocol):
    def search(self, query: str, max_results: int = 20) -> list[CandidatePaper]:
        ...


RELATION_GROUPS = {
    "upstream": "upstream_papers",
    "downstream": "downstream_papers",
    "same_route": "same_route_papers",
    "survey": "related_surveys",
}


class SeedExpansionService:
    """Minimal literature discovery Seed Expansion loop over real paper-source adapters.

    This service intentionally does not claim citation-graph certainty. The
    current loop uses source-backed searches around the seed and marks those
    relationships as weak query/title-similarity relations unless an adapter
    later contributes explicit citation edges.
    """

    def __init__(
        self,
        *,
        adapters: dict[str, SearchAdapter] | None = None,
        selection_service: SelectionService | None = None,
        verifier: CandidateVerifier | None = None,
        sources: list[str] | None = None,
        max_results_per_source: int = DEFAULT_SEARCH_MAX_RESULTS,
        max_group_items: int = 6,
        max_verify_candidates: int = 12,
    ) -> None:
        if adapters is None:
            default_adapters: dict[str, SearchAdapter] = {
                "paper_search": make_default_search_adapter(),
            }
        else:
            default_adapters = adapters
        self.adapters = default_adapters
        self.sources = sources or list(self.adapters.keys())
        self.selection_service = selection_service or SelectionService()
        self.verifier = verifier or CandidateVerifier(timeout_seconds=8.0)
        self.max_results_per_source = max_results_per_source
        self.max_group_items = max_group_items
        self.max_verify_candidates = max_verify_candidates

    def expand(self, seed_payload: dict[str, object] | SeedPaperInput) -> SeedExpansionBundle:
        seed = _seed_from_payload(seed_payload)
        seed = self._hydrate_seed(seed)
        topic = _seed_topic(seed)
        if not topic:
            return self._empty_bundle(
                seed,
                status="BLOCKED",
                message="Seed paper requires a title, arXiv ID, DOI, paper URL, or PDF URL.",
                warnings=["EMPTY_SEED"],
            )

        queries = _relation_queries(seed, topic)
        grouped_candidates: dict[str, list[CandidatePaper]] = {}
        warnings: list[str] = []
        source_metrics: list[dict[str, object]] = []
        skip_sources: set[str] = set()

        for relation_type, query in queries.items():
            candidates, relation_warnings, relation_metrics = self._acquire(
                relation_type,
                query,
                skip_sources=skip_sources,
            )
            warnings.extend(relation_warnings)
            source_metrics.extend(relation_metrics)
            grouped_candidates[relation_type] = self._verify_and_dedupe(candidates)[: self.max_group_items]

        groups = self._build_groups(grouped_candidates, seed, topic)
        flat_papers = _flatten_groups(groups)
        status, message = _status_and_message(
            source_metrics=source_metrics,
            paper_count=len(flat_papers),
            warnings=warnings,
        )

        follow_up_improvements = _follow_up_improvements(seed, flat_papers, status)
        recommended_order = _recommended_order(groups)

        return SeedExpansionBundle(
            status=status,
            seed_expansion_status=status,
            message=message,
            query=topic,
            seed=seed,
            upstream_papers=groups["upstream"],
            downstream_papers=groups["downstream"],
            same_route_papers=groups["same_route"],
            related_surveys=groups["survey"],
            follow_up_improvements=follow_up_improvements,
            recommended_expansion_order=recommended_order,
            papers=flat_papers,
            warnings=warnings,
            source_metrics=source_metrics,
        )

    def _hydrate_seed(self, seed: SeedPaperInput) -> SeedPaperInput:
        if seed.title or not seed.arxiv_id:
            return seed
        arxiv_adapter = self.adapters.get("arxiv")
        lookup = getattr(arxiv_adapter, "search_by_id", None)
        if lookup is None:
            return seed
        try:
            paper = lookup(seed.arxiv_id)
        except Exception as exc:
            logger.warning("Seed arXiv lookup failed for %s: %s", seed.arxiv_id, exc)
            return seed
        if paper is None:
            return seed
        return seed.model_copy(
            update={
                "title": paper.title,
                "authors": paper.authors,
                "year": paper.year,
                "venue": paper.venue,
                "source": paper.source or seed.source,
                "url": paper.url or seed.url,
                "landing_url": paper.landing_url or seed.landing_url,
                "pdf_url": paper.pdf_url or seed.pdf_url,
                "paper_id": paper.paper_id or seed.paper_id,
                "source_confidence": paper.source_confidence or seed.source_confidence,
            }
        )

    def _acquire(
        self,
        relation_type: str,
        query: str,
        *,
        skip_sources: set[str] | None = None,
    ) -> tuple[list[CandidatePaper], list[str], list[dict[str, object]]]:
        candidates: list[CandidatePaper] = []
        warnings: list[str] = []
        source_metrics: list[dict[str, object]] = []
        skipped = skip_sources if skip_sources is not None else set()

        for source in self.sources:
            started = time.perf_counter()
            if source in skipped:
                source_metrics.append(_metric(
                    relation_type,
                    source,
                    False,
                    0,
                    0,
                    "skipped after previous transient source failure",
                ))
                continue
            adapter = self.adapters.get(source)
            if adapter is None:
                latency_ms = int((time.perf_counter() - started) * 1000)
                warnings.append(f"SEED_SOURCE_FAILED:{relation_type}:{source}: adapter not configured")
                source_metrics.append(_metric(relation_type, source, False, 0, latency_ms, "adapter not configured"))
                continue
            try:
                results = adapter.search(query, max_results=self.max_results_per_source)
                candidates.extend(results)
                latency_ms = int((time.perf_counter() - started) * 1000)
                source_metrics.append(_metric(relation_type, source, True, len(results), latency_ms, ""))
            except Exception as exc:
                latency_ms = int((time.perf_counter() - started) * 1000)
                logger.warning("Seed expansion acquisition failed for %s/%s: %s", relation_type, source, exc)
                warning = f"SEED_SOURCE_FAILED:{relation_type}:{source}: {type(exc).__name__}: {str(exc)[:160]}"
                warnings.append(warning)
                source_metrics.append(
                    _metric(relation_type, source, False, 0, latency_ms, f"{type(exc).__name__}: {str(exc)[:200]}")
                )
                if _is_rate_limited(exc) or _is_transient_source_failure(exc):
                    skipped.add(source)

        return candidates, warnings, source_metrics

    def _verify_and_dedupe(self, candidates: list[CandidatePaper]) -> list[CandidatePaper]:
        deduplicated = self.selection_service.deduplicate(candidates)
        if not deduplicated:
            return []
        to_verify = deduplicated[: self.max_verify_candidates]
        rest = deduplicated[self.max_verify_candidates :]
        try:
            verified = self.verifier.verify_batch(to_verify)
        except Exception as exc:
            logger.warning("Seed candidate verification failed: %s", exc)
            verified = [
                candidate.model_copy(
                    update={
                        "verification_status": VerificationStatus.VERIFY_PENDING,
                        "verification_method": "seed_verification_failed",
                        "verification_reason": f"Verifier failed: {type(exc).__name__}.",
                        "verification_confidence": "low",
                    }
                )
                for candidate in to_verify
            ]
        if rest:
            rest = [
                candidate.model_copy(
                    update={
                        "verification_status": VerificationStatus.VERIFY_PENDING,
                        "verification_method": "seed_verification_limit",
                        "verification_reason": "Verification was limited for the minimal seed expansion loop.",
                        "verification_confidence": "low",
                    }
                )
                for candidate in rest
            ]
        return verified + rest

    def _build_groups(
        self,
        grouped_candidates: dict[str, list[CandidatePaper]],
        seed: SeedPaperInput,
        topic: str,
    ) -> dict[str, list[SeedExpansionPaper]]:
        seen: set[str] = {_paper_identity_from_seed(seed)}
        groups: dict[str, list[SeedExpansionPaper]] = {name: [] for name in RELATION_GROUPS}
        for relation_type in RELATION_GROUPS:
            for candidate in grouped_candidates.get(relation_type, []):
                identity = _paper_identity(candidate)
                if not identity or identity in seen:
                    continue
                seen.add(identity)
                groups[relation_type].append(_to_expansion_paper(candidate, relation_type, seed, topic))
        return groups

    @staticmethod
    def _empty_bundle(
        seed: SeedPaperInput,
        *,
        status: str,
        message: str,
        warnings: list[str],
    ) -> SeedExpansionBundle:
        return SeedExpansionBundle(
            status=status,
            seed_expansion_status=status,
            message=message,
            seed=seed,
            warnings=warnings,
        )


def _seed_from_payload(payload: dict[str, object] | SeedPaperInput) -> SeedPaperInput:
    if isinstance(payload, SeedPaperInput):
        return payload
    normalized = dict(payload)
    if "paper_url" not in normalized and normalized.get("url"):
        normalized["paper_url"] = normalized.get("url")
    allowed = set(SeedPaperInput.model_fields)
    return SeedPaperInput(**{key: value for key, value in normalized.items() if key in allowed})


def _seed_topic(seed: SeedPaperInput) -> str:
    for value in (seed.title, seed.arxiv_id, seed.doi, seed.paper_url, seed.url, seed.pdf_url):
        cleaned = " ".join(str(value or "").split())
        if cleaned:
            return cleaned
    return ""


def _relation_queries(seed: SeedPaperInput, topic: str) -> dict[str, str]:
    title_topic = _search_topic(seed, topic)
    method_topic = _method_topic(title_topic)
    return {
        "upstream": f"{method_topic} foundational baseline method",
        "downstream": f"{title_topic} improvement follow-up",
        "same_route": f"{method_topic} method",
        "survey": f"{method_topic} survey review",
    }


def _search_topic(seed: SeedPaperInput, topic: str) -> str:
    if seed.title:
        return seed.title
    if seed.arxiv_id:
        return f"arxiv {seed.arxiv_id}"
    if seed.doi:
        return seed.doi
    return topic


def _method_topic(topic: str) -> str:
    lower = topic.lower()
    phrases = [
        "time series anomaly detection",
        "multivariate time series imputation",
        "graph neural network anomaly detection",
        "time series",
        "anomaly detection",
        "imputation",
        "graph neural network",
    ]
    for phrase in phrases:
        if phrase in lower:
            return phrase
    tokens = [token for token in re.split(r"[^a-zA-Z0-9]+", topic) if len(token) > 2]
    return " ".join(tokens[:8]) or topic


def _to_expansion_paper(
    paper: CandidatePaper,
    relation_type: str,
    seed: SeedPaperInput,
    topic: str,
) -> SeedExpansionPaper:
    arxiv_url = _arxiv_url(paper)
    paper_url = paper.url or paper.landing_url or arxiv_url or paper.pdf_url or _doi_url(paper.doi)
    can_prepare = bool(paper.arxiv_id or arxiv_url or paper.pdf_url or paper.doi)
    confidence = _weak_relation_confidence(paper, seed, topic)
    return SeedExpansionPaper(
        paper_id=paper.paper_id or _stable_id(paper.title),
        source=paper.source,
        title=paper.title,
        authors=paper.authors,
        year=paper.year,
        venue=paper.venue,
        url=paper.url,
        landing_url=paper.landing_url,
        paper_url=paper_url,
        doi=paper.doi,
        arxiv_id=paper.arxiv_id,
        arxiv_url=arxiv_url,
        pdf_url=paper.pdf_url,
        relation_type=relation_type,
        relation_reason=_relation_reason(relation_type, seed, topic),
        relation_basis="query_similarity",
        citation_graph_verified=False,
        confidence=confidence,
        verification_status=_verification_status(paper),
        source_confidence=paper.source_confidence,
        can_enter_analysis=can_prepare,
        can_prepare_deep_read=can_prepare,
        deep_read_unavailable_reason="" if can_prepare else _deep_read_unavailable_reason(paper),
        is_weak_relation=True,
    )


def _relation_reason(relation_type: str, seed: SeedPaperInput, topic: str) -> str:
    seed_label = seed.title or seed.arxiv_id or seed.doi or "the seed paper"
    descriptions = {
        "upstream": "foundation/baseline query around the seed topic",
        "downstream": "recent improvement/follow-up query around the seed topic",
        "same_route": "method-route query around the seed topic",
        "survey": "survey/review query around the seed topic",
    }
    return (
        f"weak_relation: {descriptions.get(relation_type, 'related query')} for '{seed_label}'. "
        f"Relation is based on title/query similarity for '{topic}', not a verified citation graph."
    )


def _weak_relation_confidence(paper: CandidatePaper, seed: SeedPaperInput, topic: str) -> float:
    seed_tokens = set(_tokens(seed.title or topic))
    paper_tokens = set(_tokens(paper.title + " " + paper.abstract))
    if not seed_tokens or not paper_tokens:
        return 0.25
    overlap = len(seed_tokens & paper_tokens) / max(len(seed_tokens), 1)
    base = 0.25 + min(overlap, 0.6)
    if paper.arxiv_id or paper.pdf_url:
        base += 0.05
    if paper.source_confidence == "high":
        base += 0.05
    return round(min(base, 0.75), 2)


def _flatten_groups(groups: dict[str, list[SeedExpansionPaper]]) -> list[SeedExpansionPaper]:
    papers: list[SeedExpansionPaper] = []
    for relation_type in ("survey", "upstream", "same_route", "downstream"):
        papers.extend(groups.get(relation_type, []))
    return papers


def _recommended_order(groups: dict[str, list[SeedExpansionPaper]]) -> list[SeedExpansionOrderItem]:
    ordered: list[SeedExpansionOrderItem] = []
    for relation_type in ("survey", "upstream", "same_route", "downstream"):
        for paper in groups.get(relation_type, [])[:3]:
            ordered.append(
                SeedExpansionOrderItem(
                    rank=len(ordered) + 1,
                    title=paper.title,
                    relation_type=paper.relation_type,
                    reason=paper.relation_reason,
                    can_enter_analysis=paper.can_enter_analysis,
                )
            )
    return ordered


def _follow_up_improvements(seed: SeedPaperInput, papers: list[SeedExpansionPaper], status: str) -> list[dict[str, object]]:
    if not papers:
        return []
    source_backed = sum(1 for paper in papers if paper.can_prepare_deep_read)
    seed_label = seed.title or seed.arxiv_id or seed.doi or "seed"
    return [
        {
            "name": "Verify source-backed expansion papers",
            "reason": f"{source_backed} expansion candidates expose arXiv/PDF source fields and can be handed to PaperWorkspace.",
        },
        {
            "name": "Upgrade weak relations with citation data",
            "reason": f"The minimal loop did not verify a citation graph for {seed_label}; relations remain query-similarity based.",
        },
        {
            "name": "Read surveys and upstream papers before follow-ups",
            "reason": f"Current seed expansion status is {status}; use the recommended order as a conservative reading path.",
        },
    ]


def _status_and_message(
    *,
    source_metrics: list[dict[str, object]],
    paper_count: int,
    warnings: list[str],
) -> tuple[str, str]:
    attempted = [metric for metric in source_metrics if metric.get("attempted")]
    successes = [metric for metric in attempted if metric.get("success")]
    failures = [metric for metric in attempted if not metric.get("success")]
    if paper_count == 0 and not successes:
        return "BLOCKED", "No external source returned usable seed expansion candidates."
    if paper_count == 0:
        return "EMPTY_RESULT", "Sources responded, but no expansion candidates were found."
    if failures or warnings:
        return "DEGRADED", "Seed expansion returned real candidates, but one or more sources degraded."
    return "SUCCESS", "Seed expansion returned a source-backed weak-relation reading network."


def _metric(
    relation_type: str,
    source: str,
    success: bool,
    count: int,
    latency_ms: int,
    error: str,
) -> dict[str, object]:
    return {
        "relation_type": relation_type,
        "source": source,
        "attempted": True,
        "success": success,
        "count": count,
        "latency_ms": latency_ms,
        "error": error,
    }


def _paper_identity(paper: CandidatePaper) -> str:
    return (paper.arxiv_id or paper.doi or paper.paper_id or _stable_id(paper.title)).lower()


def _paper_identity_from_seed(seed: SeedPaperInput) -> str:
    return (seed.arxiv_id or seed.doi or seed.paper_id or _stable_id(seed.title)).lower()


def _verification_status(paper: CandidatePaper) -> str:
    value = paper.verification_status
    return value.value if hasattr(value, "value") else str(value)


def _arxiv_url(paper: CandidatePaper) -> str:
    if paper.arxiv_id:
        return f"https://arxiv.org/abs/{paper.arxiv_id}"
    for value in (paper.landing_url, paper.url, paper.pdf_url):
        if value and "arxiv.org/" in value:
            return value.replace("/pdf/", "/abs/").removesuffix(".pdf")
    return ""


def _deep_read_unavailable_reason(paper: CandidatePaper) -> str:
    if paper.doi:
        return "DOI handoff will attempt legal open-access PDF resolution via Unpaywall."
    return "No arXiv ID, arXiv URL, or PDF URL is available for this expansion paper."


def _is_rate_limited(exc: Exception) -> bool:
    message = str(exc).lower()
    return "429" in message or "rate" in message


def _is_transient_source_failure(exc: Exception) -> bool:
    message = str(exc).lower()
    transient_terms = (
        "timeout",
        "timed out",
        "read operation",
        "503",
        "502",
        "504",
        "connection",
        "connect",
        "max retries",
        "temporarily",
        "service unavailable",
    )
    return any(term in message for term in transient_terms)


def _doi_url(doi: str) -> str:
    clean = doi.strip()
    if not clean:
        return ""
    if clean.lower().startswith(("http://", "https://")):
        return clean
    clean = clean.removeprefix("doi:").removeprefix("DOI:")
    return f"https://doi.org/{clean}"


def _tokens(value: str) -> list[str]:
    return [token for token in re.split(r"[^a-z0-9]+", value.lower()) if len(token) > 2]


def _stable_id(title: str) -> str:
    return "seed_" + "_".join(_tokens(title))[:80] if title else "seed_unknown"
