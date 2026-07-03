from __future__ import annotations

from researchsensei.direction.exploration import DirectionExplorationService, build_heuristic_query_plan
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


class RecordingAdapter:
    def __init__(self, papers_by_query: dict[str, list[CandidatePaper]]) -> None:
        self.papers_by_query = papers_by_query
        self.calls: list[str] = []

    def search(self, query: str, max_results: int = 20) -> list[CandidatePaper]:
        self.calls.append(query)
        return self.papers_by_query.get(query, [])[:max_results]


class FailingAdapter:
    def search(self, query: str, max_results: int = 20) -> list[CandidatePaper]:
        raise RuntimeError("source unavailable")


class RateLimitedAdapter:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def search(self, query: str, max_results: int = 20) -> list[CandidatePaper]:
        self.calls.append(query)
        raise RuntimeError("429 Too Many Requests")


class TimeoutAdapter:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def search(self, query: str, max_results: int = 20) -> list[CandidatePaper]:
        self.calls.append(query)
        raise TimeoutError("The read operation timed out")


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


def test_chinese_mixed_forecasting_query_generates_aligned_variants() -> None:
    plan = build_heuristic_query_plan("\u591a\u53d8\u91cf\u65f6\u95f4\u5e8f\u5217\u9884\u6d4b\u548c\u5f02\u5e38\u68c0\u6d4b")

    assert "multivariate" in plan.english_query
    assert "forecasting" in plan.english_query
    assert "anomaly detection" in plan.english_query
    assert "forecasting" in plan.core_terms
    assert "multivariate time series forecasting" in plan.query_variants
    assert "time series forecasting anomaly detection" in plan.query_variants
    assert "survey" not in " ".join(plan.query_variants[:3])


def test_acquisition_tries_high_signal_variant_after_primary_results() -> None:
    base_candidate = _candidate(
        paper_id="base",
        title="Broad Time Series Forecasting",
        abstract="A broad forecasting paper.",
    )
    variant_candidate = _candidate(
        paper_id="variant",
        title="Time Series Forecasting Anomaly Detection",
        abstract="Forecasting residuals are used for anomaly detection.",
    )
    adapter = RecordingAdapter({
        "multivariate time series forecasting and anomaly detection": [base_candidate],
        "multivariate time series forecasting": [variant_candidate],
    })
    service = _service({"arxiv": adapter}, sources=["arxiv"])

    candidates, warnings, search_log, metrics = service._acquire(
        "multivariate time series forecasting and anomaly detection",
        query_variants=[
            "multivariate time series forecasting",
            "time series anomaly detection",
        ],
    )

    assert [candidate.paper_id for candidate in candidates] == ["base", "variant"]
    assert adapter.calls[:2] == [
        "multivariate time series forecasting and anomaly detection",
        "multivariate time series forecasting",
    ]
    assert warnings == []
    assert metrics[0]["count"] == 2
    assert any("multivariate time series forecasting" in line for line in search_log)


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


def test_rate_limited_source_skips_remaining_query_variants() -> None:
    adapter = RateLimitedAdapter()
    service = _service({"semantic_scholar": adapter}, sources=["semantic_scholar"])

    candidates, warnings, search_log, metrics = service._acquire(
        "time series anomaly detection",
        query_variants=[
            "time series anomaly detection survey",
            "time series anomaly detection review",
        ],
    )

    assert candidates == []
    assert len(adapter.calls) == 1
    assert any("ACQUISITION_FAILED:semantic_scholar" in warning for warning in warnings)
    assert any("skipped remaining variants after rate limit" in line for line in search_log)
    assert metrics[0]["rate_limited"] is True


def test_transient_source_failure_skips_remaining_query_variants() -> None:
    adapter = TimeoutAdapter()
    service = _service({"crossref": adapter}, sources=["crossref"])

    candidates, warnings, search_log, metrics = service._acquire(
        "time series anomaly detection",
        query_variants=[
            "time series anomaly detection survey",
            "time series anomaly detection review",
        ],
    )

    assert candidates == []
    assert len(adapter.calls) == 1
    assert any("ACQUISITION_FAILED:crossref" in warning for warning in warnings)
    assert any("skipped remaining variants after transient source failure" in line for line in search_log)
    assert metrics[0]["success"] is False


def test_direction_source_metrics_include_all_attempted_sources() -> None:
    service = _service(
        {
            "arxiv": StaticAdapter([_candidate()]),
            "openalex": StaticAdapter([_candidate(source="openalex", sources=["openalex"], paper_id="openalex-1")]),
            "semantic_scholar": FailingAdapter(),
            "crossref": StaticAdapter([]),
        },
        sources=["arxiv", "openalex", "semantic_scholar", "crossref"],
    )

    bundle = service.explore("time series anomaly detection")
    metrics_by_source = {metric["source"]: metric for metric in bundle.source_metrics}

    assert set(metrics_by_source) == {"arxiv", "openalex", "semantic_scholar", "crossref"}
    assert metrics_by_source["arxiv"]["attempted"] is True
    assert metrics_by_source["openalex"]["count"] >= 1
    assert metrics_by_source["semantic_scholar"]["success"] is False
    assert metrics_by_source["crossref"]["success"] is True


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
