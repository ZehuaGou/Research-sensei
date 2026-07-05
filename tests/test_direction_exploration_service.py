from __future__ import annotations

from researchsensei.direction.exploration import DirectionExplorationService, build_heuristic_query_plan
from researchsensei.library import PaperLibraryStore
from researchsensei.ranking import PaperRanker
from researchsensei.schemas import (
    CandidatePaper,
    CanonicalQualityStatus,
    PaperSourceStatus,
    PaperSourceType,
    QueryPlan,
    ResolvedPaperSource,
    SearchIntent,
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


class BlockedAdapter:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def search(self, query: str, max_results: int = 20) -> list[CandidatePaper]:
        self.calls.append(query)
        raise RuntimeError("paper_search_BLOCKED: PaperSearch returned an anti-bot/CAPTCHA page")


class StaticQueryPlanner:
    def __init__(self, plan: QueryPlan) -> None:
        self.plan_value = plan
        self.calls: list[str] = []

    async def plan(self, user_query: str) -> QueryPlan:
        self.calls.append(user_query)
        return self.plan_value


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


class RecordingDownloadedResolver(DownloadedResolver):
    def __init__(self) -> None:
        self.downloaded_ids: list[str] = []

    def resolve_many(
        self,
        query: str,
        candidates: list[CandidatePaper],
        *,
        download_dir: str | None = None,
    ) -> SourceResolutionResult:
        self.downloaded_ids = [candidate.paper_id for candidate in candidates]
        return super().resolve_many(query, candidates, download_dir=download_dir)


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
    paper_library: PaperLibraryStore | None = None,
    max_download_candidates: int = 8,
) -> DirectionExplorationService:
    return DirectionExplorationService(
        adapters=adapters,  # type: ignore[arg-type]
        sources=sources or list(adapters.keys()),
        verifier=StaticVerifier(),  # type: ignore[arg-type]
        source_resolver=source_resolver,  # type: ignore[arg-type]
        paper_library=paper_library,
        paper_ranker=PaperRanker(enabled=False),
        max_download_candidates=max_download_candidates,
        max_results_per_source=5,
    )


def test_default_direction_source_is_paper_search_mcp() -> None:
    service = DirectionExplorationService(
        verifier=StaticVerifier(),  # type: ignore[arg-type]
        max_results_per_source=1,
    )

    assert set(service.adapters) == {"paper_search"}
    assert service.sources == ["paper_search"]


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


def test_chinese_anomaly_explanation_query_generates_english_search_plan() -> None:
    plan = build_heuristic_query_plan("异常解释")

    assert plan.english_query == "explainable anomaly detection"
    assert "explainable anomaly detection" in plan.core_terms
    assert "anomaly attribution" in plan.related_terms
    joined = "\n".join(plan.query_variants)
    assert "anomaly explanation" in joined
    assert "root cause localization anomalies" in joined


def test_direction_exploration_uses_injected_query_planner_for_chinese_direction() -> None:
    planner = StaticQueryPlanner(
        QueryPlan(
            user_query="异常解释",
            language="zh",
            direction_zh="异常解释",
            direction_en="explainable anomaly detection",
            english_query="explainable anomaly detection",
            query_variants=["anomaly attribution"],
            core_terms=["explainable anomaly detection", "anomaly attribution"],
            related_terms=["root cause analysis"],
            search_intents=[SearchIntent.SOTA],
            sub_directions=["anomaly attribution and root cause localization"],
        )
    )
    adapter = RecordingAdapter({
        "explainable anomaly detection": [
            _candidate(
                paper_id="explain-1",
                title="Explaining Anomalies with Attribution",
                abstract="We study explainable anomaly detection and anomaly attribution.",
            )
        ],
    })
    service = DirectionExplorationService(
        adapters={"paper_search": adapter},  # type: ignore[arg-type]
        sources=["paper_search"],
        verifier=StaticVerifier(),  # type: ignore[arg-type]
        source_resolver=DownloadedResolver(),  # type: ignore[arg-type]
        query_planner=planner,
        paper_ranker=PaperRanker(enabled=False),
        max_results_per_source=5,
    )

    bundle = service.explore("异常解释")

    assert planner.calls == ["异常解释"]
    assert adapter.calls[0] == "explainable anomaly detection"
    assert bundle.query_plan.english_query == "explainable anomaly detection"
    assert "HEURISTIC_QUERY_PLAN_NO_LLM" not in bundle.warnings
    assert bundle.candidate_cards[0]["title"] == "Explaining Anomalies with Attribution"


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


def test_paper_search_primary_results_skip_venue_variants_to_preserve_order() -> None:
    base_candidate = _candidate(paper_id="base", title="Base Candidate")
    first_variant = _candidate(paper_id="variant-1", title="AAAI Candidate", venue="AAAI")
    second_variant = _candidate(paper_id="variant-2", title="IJCAI Candidate", venue="IJCAI")
    adapter = RecordingAdapter({
        "graph neural network multivariate time series anomaly detection": [base_candidate],
        "graph neural network multivariate time series anomaly detection AAAI": [first_variant],
        "graph neural network multivariate time series anomaly detection IJCAI": [second_variant],
    })
    service = _service({"paper_search": adapter}, sources=["paper_search"])

    candidates, warnings, _search_log, metrics = service._acquire(
        "graph neural network multivariate time series anomaly detection",
        query_variants=[
            "graph neural network multivariate time series anomaly detection AAAI",
            "graph neural network multivariate time series anomaly detection IJCAI",
        ],
    )

    assert [candidate.paper_id for candidate in candidates] == ["base"]
    assert adapter.calls == ["graph neural network multivariate time series anomaly detection"]
    assert warnings == []
    assert metrics[0]["count"] == 1


def test_query_plan_prioritizes_venue_targeted_variants_for_compound_direction() -> None:
    plan = build_heuristic_query_plan("multivariate time series anomaly detection graph neural network")

    assert plan.query_variants[:6] == [
        "multivariate time series anomaly detection graph neural network",
        "graph neural network multivariate time series anomaly detection KDD",
        "graph neural network multivariate time series anomaly detection VLDB",
        "graph neural network multivariate time series anomaly detection SIGMOD",
        "graph neural network multivariate time series anomaly detection ICDE",
        "graph neural network multivariate time series anomaly detection WWW",
    ]


def test_query_plan_adds_root_cause_and_llm_variants() -> None:
    plan = build_heuristic_query_plan("large language model root cause analysis time series anomaly detection")

    joined = "\n".join(plan.query_variants)
    assert "time series anomaly root cause localization" in joined
    assert "large language model root cause analysis" in joined
    assert "LLM root cause analysis AIOps" in joined
    assert "root cause localization" in plan.related_terms


def test_acquisition_uses_fallback_when_paper_search_returns_empty() -> None:
    primary = RecordingAdapter({
        "graph anomaly detection": [],
        "graph neural network anomaly detection AAAI": [],
        "graph neural network anomaly detection IJCAI": [],
    })
    fallback = RecordingAdapter({
        "graph anomaly detection": [_candidate(paper_id="fallback", title="Fallback Graph Anomaly Detection")],
    })
    service = DirectionExplorationService(
        adapters={"paper_search": primary},  # type: ignore[arg-type]
        sources=["paper_search"],
        verifier=StaticVerifier(),  # type: ignore[arg-type]
        fallback_adapters={"openalex_fallback": fallback},  # type: ignore[arg-type]
        max_results_per_source=5,
    )

    candidates, warnings, search_log, metrics = service._acquire(
        "graph anomaly detection",
        query_variants=[
            "graph neural network anomaly detection AAAI",
            "graph neural network anomaly detection IJCAI",
        ],
    )

    assert [candidate.paper_id for candidate in candidates] == ["fallback"]
    assert primary.calls == [
        "graph anomaly detection",
        "graph neural network anomaly detection AAAI",
    ]
    assert "PRIMARY_DISCOVERY_EMPTY:paper_search" in warnings
    assert any("trying fallback discovery" in line for line in search_log)
    assert metrics[-1]["source"] == "openalex_fallback"
    assert metrics[-1]["fallback"] is True


def test_acquisition_marks_paper_search_blocked_before_fallback() -> None:
    primary = BlockedAdapter()
    fallback = RecordingAdapter({
        "graph anomaly detection": [_candidate(paper_id="fallback", title="Fallback Graph Anomaly Detection")],
    })
    service = DirectionExplorationService(
        adapters={"paper_search": primary},  # type: ignore[arg-type]
        sources=["paper_search"],
        verifier=StaticVerifier(),  # type: ignore[arg-type]
        fallback_adapters={"openalex_fallback": fallback},  # type: ignore[arg-type]
        max_results_per_source=5,
    )

    candidates, warnings, search_log, metrics = service._acquire(
        "graph anomaly detection",
        query_variants=[
            "graph neural network anomaly detection AAAI",
            "graph neural network anomaly detection IJCAI",
        ],
    )

    assert [candidate.paper_id for candidate in candidates] == ["fallback"]
    assert primary.calls == ["graph anomaly detection"]
    assert "PRIMARY_DISCOVERY_BLOCKED:paper_search" in warnings
    assert any("blocked/captcha" in line for line in search_log)
    assert metrics[-1]["source"] == "openalex_fallback"


def test_fallback_continues_variants_to_expand_venue_pool() -> None:
    primary = RecordingAdapter({
        "graph anomaly detection": [],
        "graph neural network anomaly detection AAAI": [],
    })
    fallback = RecordingAdapter({
        "graph anomaly detection": [_candidate(paper_id="fallback-base", title="Fallback Base")],
        "graph neural network anomaly detection AAAI": [_candidate(paper_id="fallback-aaai", title="Fallback AAAI")],
        "graph neural network anomaly detection IJCAI": [_candidate(paper_id="fallback-ijcai", title="Fallback IJCAI")],
    })
    service = DirectionExplorationService(
        adapters={"paper_search": primary},  # type: ignore[arg-type]
        sources=["paper_search"],
        verifier=StaticVerifier(),  # type: ignore[arg-type]
        fallback_adapters={"openalex_fallback": fallback},  # type: ignore[arg-type]
        max_results_per_source=5,
        max_search_queries=4,
    )

    candidates, _warnings, _search_log, metrics = service._acquire(
        "graph anomaly detection",
        query_variants=[
            "graph neural network anomaly detection AAAI",
            "graph neural network anomaly detection IJCAI",
        ],
    )

    assert [candidate.paper_id for candidate in candidates] == [
        "fallback-base",
        "fallback-aaai",
        "fallback-ijcai",
    ]
    assert fallback.calls == [
        "graph anomaly detection",
        "graph neural network anomaly detection AAAI",
        "graph neural network anomaly detection IJCAI",
    ]
    assert metrics[-1]["count"] == 3


def test_acquisition_skips_fallback_when_primary_has_results() -> None:
    primary = RecordingAdapter({
        "graph anomaly detection": [_candidate(paper_id="primary", title="Primary Graph Anomaly Detection")],
    })
    fallback = RecordingAdapter({
        "graph anomaly detection": [_candidate(paper_id="fallback", title="Fallback Graph Anomaly Detection")],
    })
    service = DirectionExplorationService(
        adapters={"paper_search": primary},  # type: ignore[arg-type]
        sources=["paper_search"],
        verifier=StaticVerifier(),  # type: ignore[arg-type]
        fallback_adapters={"openalex_fallback": fallback},  # type: ignore[arg-type]
        max_results_per_source=5,
    )

    candidates, warnings, _search_log, metrics = service._acquire("graph anomaly detection")

    assert [candidate.paper_id for candidate in candidates] == ["primary"]
    assert warnings == []
    assert fallback.calls == []
    assert len(metrics) == 1


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


def test_low_relevance_discovery_candidates_are_still_visible() -> None:
    service = _service({
        "paper_search": StaticAdapter([
            _candidate(
                paper_id="off-topic",
                title="Image Classification with Convolutional Networks",
                abstract="We classify images with convolutional networks.",
                source="paper_search",
                sources=["paper_search"],
                arxiv_id="",
                doi="",
                pdf_url="",
                url="https://example.test/off-topic",
                landing_url="https://example.test/off-topic",
            )
        ])
    })

    bundle = service.explore("time series anomaly detection")

    assert bundle.status == "DEGRADED"
    assert bundle.candidate_cards
    assert bundle.candidate_cards[0]["paper_id"] == "off-topic"
    assert bundle.candidate_cards[0]["priority"] == "D_IGNORE"
    assert bundle.recommended_reading_order == []
    assert "FILTERED_D_IGNORE:1" in bundle.warnings


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


def test_direction_download_attempts_follow_rerank_queue_not_venue_gate() -> None:
    ranked = _candidate(
        paper_id="aaai-paper",
        title="Time Series Anomaly Detection at AAAI",
        venue="Proceedings of the AAAI Conference on Artificial Intelligence",
        source="paper_search",
        sources=["paper_search"],
        url="https://ojs.aaai.org/index.php/AAAI/article/download/1/2",
        landing_url="https://ojs.aaai.org/index.php/AAAI/article/download/1/2",
        pdf_url="https://ojs.aaai.org/index.php/AAAI/article/download/1/2",
        arxiv_id="",
    )
    unranked = _candidate(
        paper_id="workshop-paper",
        title="Time Series Anomaly Detection Workshop Paper",
        venue="Local Workshop",
        source="paper_search",
        sources=["paper_search"],
        url="https://example.test/workshop.pdf",
        landing_url="https://example.test/workshop.pdf",
        pdf_url="https://example.test/workshop.pdf",
        arxiv_id="",
    )
    resolver = RecordingDownloadedResolver()
    service = _service(
        {"paper_search": StaticAdapter([unranked, ranked])},
        sources=["paper_search"],
        source_resolver=resolver,
    )

    bundle = service.explore("time series anomaly detection")
    cards = {card["paper_id"]: card for card in bundle.candidate_cards}

    assert [card["paper_id"] for card in bundle.candidate_cards[:2]] == ["workshop-paper", "aaai-paper"]
    assert resolver.downloaded_ids == ["workshop-paper", "aaai-paper"]
    assert cards["aaai-paper"]["download_selected"] is True
    assert cards["aaai-paper"]["venue_rank"] == "A*"
    assert cards["aaai-paper"]["can_prepare_deep_read"] is True
    assert cards["aaai-paper"]["can_enter_m2"] is False
    assert cards["aaai-paper"]["deep_read_button_state"] == "prepare"
    assert cards["workshop-paper"]["download_selected"] is True
    assert cards["workshop-paper"]["download_decision"] == "SELECTED_BY_RERANKER"
    assert cards["workshop-paper"]["venue_rank"] == "unranked"
    assert cards["workshop-paper"]["can_prepare_deep_read"] is True
    assert cards["workshop-paper"]["search_rank"] == 1


def test_direction_download_pool_reuses_library_hit_in_rerank_queue(tmp_path: Path) -> None:
    library = PaperLibraryStore(tmp_path / "sensei.sqlite3")
    cached_pdf = tmp_path / "cached.pdf"
    cached_pdf.write_bytes(b"%PDF-1.4\ncached\n%%EOF")
    cached = _candidate(
        paper_id="cached",
        title="Time Series Anomaly Detection at AAAI",
        venue="Proceedings of the AAAI Conference on Artificial Intelligence",
        source="paper_search",
        sources=["paper_search"],
        url="https://example.test/cached",
        landing_url="https://example.test/cached",
        arxiv_id="",
        doi="10.1000/cached",
        pdf_url="https://example.test/cached.pdf",
    )
    library.upsert_download(
        cached,
        ResolvedPaperSource(
            paper_id=cached.paper_id,
            title=cached.title,
            doi=cached.doi,
            pdf_url=cached.pdf_url,
            source_type=PaperSourceType.PDF,
            status=PaperSourceStatus.RESOLVED_PDF_DOWNLOADED,
            download_status="downloaded",
            local_path=str(cached_pdf),
            sha256="c" * 64,
            file_size=cached_pdf.stat().st_size,
            has_valid_deep_reading_source=True,
            metadata={"resolution_strategy": "downloaded_validated_pdf"},
        ),
    )
    fresh = _candidate(
        paper_id="fresh",
        title="Fresh Time Series Anomaly Detection at IJCAI",
        venue="Proceedings of the AAAI Conference on Artificial Intelligence",
        source="paper_search",
        sources=["paper_search"],
        url="https://example.test/fresh",
        landing_url="https://example.test/fresh",
        arxiv_id="",
        doi="10.1000/fresh",
        pdf_url="https://example.test/fresh.pdf",
    )
    resolver = RecordingDownloadedResolver()
    service = _service(
        {"paper_search": StaticAdapter([cached, fresh])},
        sources=["paper_search"],
        source_resolver=resolver,
        paper_library=library,
        max_download_candidates=1,
    )

    bundle = service.explore("time series anomaly detection")

    assert resolver.downloaded_ids == ["cached"]
    cards = {card["paper_id"]: card for card in bundle.candidate_cards}
    assert cards["cached"]["download_selected"] is True
    assert cards["cached"]["download_decision"] == "SELECTED_BY_RERANKER"
    assert cards["fresh"]["download_selected"] is False
    assert cards["fresh"]["download_decision"] == "SKIPPED_OVER_DOWNLOAD_LIMIT"


def test_direction_download_pool_preserves_rerank_queue_without_venue_diversification() -> None:
    papers = [
        _candidate(
            paper_id="aaai-1",
            title="Graph Anomaly Detection AAAI One",
            venue="Proceedings of the AAAI Conference on Artificial Intelligence",
            arxiv_id="",
            doi="10.1000/aaai1",
            pdf_url="https://example.test/aaai1.pdf",
        ),
        _candidate(
            paper_id="aaai-2",
            title="Graph Anomaly Detection AAAI Two",
            venue="Proceedings of the AAAI Conference on Artificial Intelligence",
            arxiv_id="",
            doi="10.1000/aaai2",
            pdf_url="https://example.test/aaai2.pdf",
        ),
        _candidate(
            paper_id="vldb-1",
            title="Graph Anomaly Detection VLDB",
            venue="Proceedings of the VLDB Endowment",
            arxiv_id="",
            doi="10.1000/vldb1",
            pdf_url="https://example.test/vldb1.pdf",
        ),
        _candidate(
            paper_id="tpami-1",
            title="Graph Anomaly Detection TPAMI",
            venue="IEEE Transactions on Pattern Analysis and Machine Intelligence",
            arxiv_id="",
            doi="10.1000/tpami1",
            pdf_url="https://example.test/tpami1.pdf",
        ),
    ]
    resolver = RecordingDownloadedResolver()
    service = _service(
        {"paper_search": StaticAdapter(papers)},
        sources=["paper_search"],
        source_resolver=resolver,
        max_download_candidates=3,
    )

    bundle = service.explore("graph anomaly detection")

    assert [card["paper_id"] for card in bundle.candidate_cards[:4]] == ["aaai-1", "aaai-2", "vldb-1", "tpami-1"]
    assert resolver.downloaded_ids == ["aaai-1", "aaai-2", "vldb-1"]
    cards = {card["paper_id"]: card for card in bundle.candidate_cards}
    assert cards["aaai-1"]["download_selected"] is True
    assert cards["aaai-2"]["download_selected"] is True
    assert cards["vldb-1"]["download_selected"] is True
    assert cards["tpami-1"]["download_selected"] is False
    assert cards["tpami-1"]["download_selected"] is False
    assert cards["tpami-1"]["download_decision"] == "SKIPPED_OVER_DOWNLOAD_LIMIT"


def test_direction_download_pool_does_not_cap_single_venue_when_rerank_orders_it_first() -> None:
    aaai_papers = [
        _candidate(
            paper_id=f"aaai-{index}",
            title=f"Graph Anomaly Detection AAAI {index}",
            venue="Proceedings of the AAAI Conference on Artificial Intelligence",
            arxiv_id="",
            doi=f"10.1000/aaai{index}",
            pdf_url=f"https://example.test/aaai{index}.pdf",
            citation_count=200 - index,
        )
        for index in range(1, 6)
    ]
    papers = [
        *aaai_papers,
        _candidate(
            paper_id="vldb-1",
            title="Graph Anomaly Detection VLDB",
            venue="Proceedings of the VLDB Endowment",
            arxiv_id="",
            doi="10.1000/vldb1",
            pdf_url="https://example.test/vldb1.pdf",
        ),
        _candidate(
            paper_id="tpami-1",
            title="Graph Anomaly Detection TPAMI",
            venue="IEEE Transactions on Pattern Analysis and Machine Intelligence",
            arxiv_id="",
            doi="10.1000/tpami1",
            pdf_url="https://example.test/tpami1.pdf",
        ),
    ]
    resolver = RecordingDownloadedResolver()
    service = _service(
        {"paper_search": StaticAdapter(papers)},
        sources=["paper_search"],
        source_resolver=resolver,
        max_download_candidates=8,
    )

    bundle = service.explore("graph anomaly detection")

    assert len(resolver.downloaded_ids) == 5
    assert resolver.downloaded_ids == ["aaai-1", "aaai-2", "aaai-3", "aaai-4", "aaai-5"]
    assert sum(paper_id.startswith("aaai-") for paper_id in resolver.downloaded_ids) == 5
    selected_cards = [card for card in bundle.candidate_cards if card["download_selected"]]
    assert len(selected_cards) == 5


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
