from __future__ import annotations

from researchsensei.direction.exploration import DirectionExplorationService
from researchsensei.schemas import (
    CandidatePaper,
    CanonicalQualityStatus,
    PaperSourceStatus,
    PaperSourceType,
    ResolvedPaperSource,
    SourcePriority,
    SourceResolutionResult,
    VerificationStatus,
)


class StaticAdapter:
    def __init__(self, papers: list[CandidatePaper]) -> None:
        self.papers = papers

    def search(self, query: str, max_results: int = 20) -> list[CandidatePaper]:
        return self.papers[:max_results]


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


class DownloadedResolver:
    def resolve_many(
        self,
        query: str,
        candidates: list[CandidatePaper],
        *,
        download_dir: str | None = None,
    ) -> SourceResolutionResult:
        return SourceResolutionResult(
            query=query,
            items=[
                ResolvedPaperSource(
                    paper_id=candidate.paper_id,
                    title=candidate.title,
                    doi=candidate.doi,
                    arxiv_id=candidate.arxiv_id,
                    pdf_url=candidate.pdf_url,
                    landing_url=candidate.landing_url,
                    source_type=PaperSourceType.PDF,
                    status=PaperSourceStatus.RESOLVED_PDF_DOWNLOADED,
                    download_status="downloaded",
                    local_path="/tmp/source.pdf",
                    sha256="a" * 64,
                    file_size=100000,
                    source_priority=SourcePriority.PDF,
                    preferred_m2_input="pdf",
                    has_valid_deep_reading_source=True,
                )
                for candidate in candidates
            ],
        )


def _candidate(**overrides: object) -> CandidatePaper:
    base = {
        "paper_id": "paper-1",
        "title": "Time Series Anomaly Detection with Transformers",
        "authors": ["A. Researcher", "B. Scientist"],
        "year": 2024,
        "venue": "NeurIPS",
        "source": "arxiv",
        "sources": ["arxiv"],
        "url": "https://arxiv.org/abs/2401.00001",
        "landing_url": "https://arxiv.org/abs/2401.00001",
        "arxiv_id": "2401.00001",
        "abstract": "We study time series anomaly detection with transformer models and benchmark datasets.",
        "pdf_url": "https://arxiv.org/pdf/2401.00001.pdf",
        "open_access": True,
        "pdf_available": True,
        "source_confidence": "high",
        "metadata_confidence": "high",
        "citation_count": 120,
    }
    base.update(overrides)
    return CandidatePaper(**base)


def _service(
    adapters: dict[str, object],
    *,
    sources: list[str] | None = None,
    source_resolver: object | None = None,
) -> DirectionExplorationService:
    return DirectionExplorationService(
        adapters=adapters,  # type: ignore[arg-type]
        sources=sources or list(adapters.keys()),
        verifier=StaticVerifier(),  # type: ignore[arg-type]
        source_resolver=source_resolver,  # type: ignore[arg-type]
        max_results_per_source=5,
    )


def test_direction_query_returns_structured_bundle() -> None:
    service = _service({"arxiv": StaticAdapter([_candidate()])})

    bundle = service.explore("time series anomaly detection")

    assert bundle.status == "SUCCESS"
    assert bundle.overview
    assert bundle.key_sub_directions
    assert bundle.method_families
    assert bundle.candidate_cards
    assert bundle.recommended_reading_order
    assert bundle.candidate_cards[0]["title"] == "Time Series Anomaly Detection with Transformers"


def test_partial_source_failure_returns_degraded_with_real_candidates() -> None:
    service = _service(
        {
            "arxiv": StaticAdapter([_candidate()]),
            "openalex": FailingAdapter(),
        },
        sources=["arxiv", "openalex"],
    )

    bundle = service.explore("time series anomaly detection")

    assert bundle.status == "DEGRADED"
    assert bundle.candidate_cards
    assert any("ACQUISITION_FAILED:openalex" in warning for warning in bundle.warnings)


def test_empty_source_results_return_empty_result() -> None:
    service = _service({"arxiv": StaticAdapter([])})

    bundle = service.explore("time series anomaly detection")

    assert bundle.status == "EMPTY_RESULT"
    assert bundle.candidate_cards == []
    assert bundle.reading_plan.items == []


def test_candidate_cards_include_required_direction_fields() -> None:
    service = _service({"semantic_scholar": StaticAdapter([_candidate(source="semantic_scholar", sources=["semantic_scholar"])])})

    bundle = service.explore("time series anomaly detection")
    card = bundle.candidate_cards[0]

    for field in (
        "source",
        "title",
        "authors",
        "year",
        "url",
        "doi",
        "arxiv_id",
        "relevance_score",
        "verification_status",
        "source_confidence",
        "pdf_available",
        "canonicalization_status",
        "m2_ready",
        "can_enter_m2",
    ):
        assert field in card


def test_a_read_for_m2_gate_is_not_relaxed_without_canonical_readiness() -> None:
    paper = _candidate(
        llm_relevance_score=0.9,
        llm_relevance_label="HIGH",
        should_a_read=True,
    )
    service = _service({"arxiv": StaticAdapter([paper])})

    bundle = service.explore("time series anomaly detection")
    card = bundle.candidate_cards[0]

    assert card["priority"] != "A_READ_FOR_M2"
    assert card["can_enter_m2"] is False
    assert card["deep_read_button_state"] == "prepare"


def test_a_read_for_m2_requires_all_existing_selection_gates() -> None:
    paper = _candidate(
        llm_relevance_score=0.9,
        llm_relevance_label="HIGH",
        should_a_read=True,
        m2_ready=True,
        canonical_paper_path="/tmp/canonical_paper.md",
        canonical_quality_status=CanonicalQualityStatus.PASS,
        has_valid_deep_reading_source=True,
        source_priority=SourcePriority.PDF,
    )
    service = _service(
        {"arxiv": StaticAdapter([paper])},
        source_resolver=DownloadedResolver(),
    )

    bundle = service.explore("time series anomaly detection")
    card = bundle.candidate_cards[0]

    assert card["priority"] == "A_READ_FOR_M2"
    assert card["can_enter_m2"] is True
    assert bundle.deep_read_candidates[0]["paper_id"] == "paper-1"
