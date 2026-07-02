from __future__ import annotations

from researchsensei.direction.seed_expansion import SeedExpansionService
from researchsensei.schemas import CandidatePaper, VerificationStatus


class RelationAdapter:
    def search(self, query: str, max_results: int = 20) -> list[CandidatePaper]:
        lower = query.lower()
        if "survey" in lower or "review" in lower:
            return [_candidate("survey-1", "A Survey of Time Series Anomaly Detection", source="arxiv", arxiv_id="2401.00010")]
        if "foundational" in lower or "baseline" in lower:
            return [_candidate("upstream-1", "Foundations of Time Series Anomaly Detection", source="openalex", doi="10.1000/base")]
        if "improvement" in lower or "follow-up" in lower:
            return [_candidate("downstream-1", "Improving Transformer Anomaly Detection", source="arxiv", arxiv_id="2401.00011")]
        return [_candidate("same-route-1", "Transformer Routes for Time Series Anomaly Detection", source="semantic_scholar", pdf_url="https://example.test/paper.pdf")]


class EmptyAdapter:
    def search(self, query: str, max_results: int = 20) -> list[CandidatePaper]:
        return []


class FailingAdapter:
    def search(self, query: str, max_results: int = 20) -> list[CandidatePaper]:
        raise RuntimeError("source unavailable")


class StaticVerifier:
    def verify_batch(self, candidates: list[CandidatePaper]) -> list[CandidatePaper]:
        return [
            candidate.model_copy(
                update={
                    "verification_status": VerificationStatus.VERIFIED,
                    "verification_method": "fixture",
                    "verification_reason": "fixture-confirmed",
                    "verification_confidence": "high",
                }
            )
            for candidate in candidates
        ]


def _candidate(
    paper_id: str,
    title: str,
    *,
    source: str = "arxiv",
    arxiv_id: str = "",
    doi: str = "",
    pdf_url: str = "",
) -> CandidatePaper:
    return CandidatePaper(
        paper_id=paper_id,
        title=title,
        authors=["A. Researcher"],
        year=2024,
        venue="arXiv" if source == "arxiv" else "Conference",
        source=source,
        sources=[source],
        url=f"https://example.test/{paper_id}",
        landing_url=f"https://example.test/{paper_id}",
        doi=doi,
        arxiv_id=arxiv_id,
        abstract="time series anomaly detection transformer baseline survey improvement",
        pdf_url=pdf_url or (f"https://arxiv.org/pdf/{arxiv_id}.pdf" if arxiv_id else ""),
        pdf_available=bool(pdf_url or arxiv_id),
        source_confidence="high" if arxiv_id else "medium",
        metadata_confidence="high",
    )


def _service(adapters: dict[str, object], *, sources: list[str] | None = None) -> SeedExpansionService:
    return SeedExpansionService(
        adapters=adapters,  # type: ignore[arg-type]
        sources=sources or list(adapters.keys()),
        verifier=StaticVerifier(),  # type: ignore[arg-type]
        max_results_per_source=3,
        max_group_items=4,
    )


def test_seed_expansion_returns_structured_bundle() -> None:
    service = _service({"arxiv": RelationAdapter()})

    bundle = service.expand({"title": "Time Series Anomaly Detection with Transformers", "arxiv_id": "2401.00001"})

    assert bundle.status == "SUCCESS"
    assert bundle.upstream_papers
    assert bundle.downstream_papers
    assert bundle.same_route_papers
    assert bundle.related_surveys
    assert bundle.follow_up_improvements
    assert bundle.recommended_expansion_order
    paper = bundle.papers[0]
    assert paper.source
    assert paper.title
    assert paper.relation_type in {"survey", "upstream", "same_route", "downstream"}
    assert paper.relation_reason
    assert paper.confidence > 0
    assert "weak_relation" in paper.relation_reason


def test_partial_source_failure_returns_degraded_with_real_candidates() -> None:
    service = _service(
        {
            "arxiv": RelationAdapter(),
            "openalex": FailingAdapter(),
        },
        sources=["arxiv", "openalex"],
    )

    bundle = service.expand({"title": "Time Series Anomaly Detection with Transformers"})

    assert bundle.status == "DEGRADED"
    assert bundle.papers
    assert any("SEED_SOURCE_FAILED" in warning for warning in bundle.warnings)


def test_empty_source_results_return_empty_result() -> None:
    service = _service({"arxiv": EmptyAdapter()})

    bundle = service.expand({"title": "Very Narrow Seed"})

    assert bundle.status == "EMPTY_RESULT"
    assert bundle.papers == []
    assert bundle.recommended_expansion_order == []


def test_seed_expansion_does_not_fabricate_citation_graph() -> None:
    service = _service({"arxiv": RelationAdapter()})

    bundle = service.expand({"title": "Time Series Anomaly Detection with Transformers"})

    assert bundle.papers
    assert all(paper.citation_graph_verified is False for paper in bundle.papers)
    assert all(paper.relation_basis == "query_similarity" for paper in bundle.papers)
    assert all("not a verified citation graph" in paper.relation_reason for paper in bundle.papers)


def test_can_enter_m2_accepts_resolvable_handoff_sources() -> None:
    service = _service({"crossref": RelationAdapter()}, sources=["crossref"])

    bundle = service.expand({"title": "Time Series Anomaly Detection with Transformers"})

    by_title = {paper.title: paper for paper in bundle.papers}
    assert by_title["Foundations of Time Series Anomaly Detection"].can_enter_m2 is True
    assert by_title["A Survey of Time Series Anomaly Detection"].can_enter_m2 is True
    assert by_title["Improving Transformer Anomaly Detection"].can_prepare_deep_read is True
