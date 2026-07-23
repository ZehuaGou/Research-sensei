from __future__ import annotations

from researchsensei.schemas import CandidatePaper, QueryPlan, SourcePriority
from researchsensei.selection.service import SelectionService


def _make_paper(
    title: str,
    year: int | None = 2023,
    venue: str = "arXiv",
    citations: int | None = None,
    abstract: str = "",
    source: str = "arxiv",
) -> CandidatePaper:
    return CandidatePaper(
        paper_id=title.lower().replace(" ", "_")[:20],
        title=title,
        year=year,
        venue=venue,
        citation_count=citations,
        abstract=abstract,
        source=source,
    )


def _make_query(terms: list[str]) -> QueryPlan:
    return QueryPlan(
        user_query="test",
        core_terms=terms,
        related_terms=[],
    )


def test_selection_service_builds_reading_plan() -> None:
    service = SelectionService(max_a_read=3)
    query = _make_query(["time series", "anomaly detection"])
    candidates = [
        _make_paper("Time Series Anomaly Detection with Transformers", abstract="We detect anomalies in time series."),
        _make_paper("Deep Learning for Time Series Forecasting", abstract="We forecast time series."),
        _make_paper("Image Classification with CNNs", abstract="We classify images."),
    ]

    plan = service.build_reading_plan(query, candidates)

    assert plan.topic == "test"
    assert len(plan.items) > 0
    # Image classification should be filtered out
    titles = [item.paper.title for item in plan.items]
    assert "Image Classification with CNNs" not in titles


def test_selection_service_scoring_breakdown() -> None:
    service = SelectionService()
    query = _make_query(["time series", "anomaly detection"])
    candidates = [
        _make_paper("Time Series Anomaly Detection", abstract="We detect anomalies in time series.", citations=100),
    ]

    plan = service.build_reading_plan(query, candidates)

    assert len(plan.items) == 1
    item = plan.items[0]
    assert item.scoring_breakdown.relevance_score > 0
    assert item.scoring_breakdown.weighted_total > 0
    assert item.scoring_breakdown.citation_score > 0


def test_source_first_candidate_ranks_above_pdf_url_only_peer() -> None:
    service = SelectionService()
    query = _make_query(["multivariate time series", "forecasting"])
    candidates = [
        _make_paper_full(
            "Multivariate Time Series Forecasting with PDF URL",
            abstract="A multivariate time series forecasting method for sensor data.",
            pdf_url="https://example.test/paper.pdf",
            pdf_available=True,
            source_confidence="high",
            metadata_confidence="high",
        ),
        _make_paper_full(
            "Multivariate Time Series Forecasting with Source",
            abstract="A multivariate time series forecasting method for sensor data.",
            pdf_url="https://arxiv.org/pdf/2401.00001.pdf",
            pdf_available=True,
            has_valid_deep_reading_source=True,
            source_priority=SourcePriority.LATEX_SOURCE,
            preferred_analysis_input="latex_source",
            latex_source_available=True,
            source_confidence="high",
            metadata_confidence="high",
        ),
    ]

    plan = service.build_reading_plan(query, candidates)

    assert plan.items[0].paper.title == "Multivariate Time Series Forecasting with Source"
    assert plan.items[0].scoring_breakdown.pdf_available_score > plan.items[1].scoring_breakdown.pdf_available_score
    assert "analysis_input=latex_source" in plan.items[0].selection_reason


def test_mixed_intent_candidate_ranks_above_single_intent_peer() -> None:
    service = SelectionService()
    query = QueryPlan(
        user_query="多变量时间序列预测和异常检测",
        english_query="multivariate time series forecasting and anomaly detection",
        core_terms=["multivariate", "time series", "forecasting", "anomaly detection"],
        related_terms=["forecasting residual", "outlier detection"],
        query_variants=["time series forecasting anomaly detection"],
    )
    combined = _make_paper_full(
        "Forecasting Residuals for Multivariate Time Series Anomaly Detection",
        abstract="We use forecasting residuals to detect anomalies in multivariate time series sensor data.",
        citation_count=30,
        source_confidence="high",
        metadata_confidence="high",
        pdf_url="https://example.test/combined.pdf",
    )
    forecasting_only = _make_paper_full(
        "Highly Cited Multivariate Time Series Forecasting",
        abstract="A strong forecasting model for multivariate time series prediction.",
        citation_count=900,
        source_confidence="high",
        metadata_confidence="high",
        pdf_url="https://example.test/forecast.pdf",
    )

    plan = service.build_reading_plan(query, [forecasting_only, combined])

    assert plan.items[0].paper.title == "Forecasting Residuals for Multivariate Time Series Anomaly Detection"
    assert plan.items[0].scoring_breakdown.relevance_score > plan.items[1].scoring_breakdown.relevance_score
    assert plan.items[1].scoring_breakdown.penalty_noise < plan.items[0].scoring_breakdown.penalty_noise


def test_selection_service_venue_prestige() -> None:
    service = SelectionService()
    query = _make_query(["test"])
    candidates = [
        _make_paper("Test Paper A", venue="NeurIPS 2023", abstract="test method"),
        _make_paper("Test Paper B", venue="arXiv", abstract="test method"),
    ]

    plan = service.build_reading_plan(query, candidates)

    items_by_title = {item.paper.title: item for item in plan.items}
    assert items_by_title["Test Paper A"].scoring_breakdown.venue_prestige > items_by_title["Test Paper B"].scoring_breakdown.venue_prestige


def test_selection_service_venue_registry_covers_ccf_a_systems_and_security() -> None:
    service = SelectionService()

    osdi_score = service._venue_prestige(
        _make_paper("OSDI Paper", venue="USENIX Symposium on Operating Systems Design and Implementation")
    )
    sp_score = service._venue_prestige(
        _make_paper("Security Paper", venue="IEEE Symposium on Security and Privacy")
    )

    assert osdi_score >= 0.95
    assert sp_score >= 0.95


def test_selection_service_infers_venue_rank_from_known_oa_url() -> None:
    service = SelectionService()
    candidate = _make_paper_full(
        "Graph Neural Network-Based Anomaly Detection in Multivariate Time Series",
        venue="",
        source="paper_search",
        pdf_url="https://ojs.aaai.org/index.php/AAAI/article/download/16523/16330",
        landing_url="https://ojs.aaai.org/index.php/AAAI/article/view/16523",
        pdf_available=True,
    )

    pool = service.build_candidate_pool("time series anomaly detection", [candidate])

    assert pool.items[0].venue_canonical_name == "AAAI"
    assert pool.items[0].venue_rank.value == "A*"


def test_selection_service_recency_bonus() -> None:
    service = SelectionService()
    query = _make_query(["test"])
    candidates = [
        _make_paper("Recent Test Paper", year=2025, abstract="test method"),
        _make_paper("Old Test Paper", year=2018, abstract="test method"),
    ]

    plan = service.build_reading_plan(query, candidates)

    items_by_title = {item.paper.title: item for item in plan.items}
    assert items_by_title["Recent Test Paper"].scoring_breakdown.recency_bonus > items_by_title["Old Test Paper"].scoring_breakdown.recency_bonus


def test_selection_service_max_a_read() -> None:
    service = SelectionService(max_a_read=2)
    query = _make_query(["time series", "anomaly detection"])
    candidates = [
        _make_paper(f"Paper {i}", abstract="time series anomaly detection") for i in range(10)
    ]

    plan = service.build_reading_plan(query, candidates)

    a_read_count = sum(1 for item in plan.items if item.priority == "A_READ")
    assert a_read_count <= 2


def test_selection_service_empty_candidates() -> None:
    service = SelectionService()
    query = _make_query(["test"])

    plan = service.build_reading_plan(query, [])

    assert len(plan.items) == 0
    assert "NO_CANDIDATES" in plan.warnings


def test_selection_service_build_candidate_pool() -> None:
    service = SelectionService()
    candidates = [
        _make_paper("Paper A"),
        _make_paper("Paper B"),
    ]

    pool = service.build_candidate_pool("test", candidates, search_log=["arxiv: searched"])

    assert pool.query == "test"
    assert pool.retrieved_count == 2
    assert len(pool.items) == 2
    assert pool.search_log == ["arxiv: searched"]


# --- Dedup tests ---


def _make_paper_full(
    title: str,
    doi: str = "",
    arxiv_id: str = "",
    **kwargs: object,
) -> CandidatePaper:
    defaults = dict(
        paper_id=title.lower().replace(" ", "_")[:20],
        title=title,
        year=2023,
        venue="arXiv",
        source="arxiv",
    )
    defaults.update(kwargs)
    return CandidatePaper(doi=doi, arxiv_id=arxiv_id, **defaults)  # type: ignore[arg-type]


def test_dedup_by_doi() -> None:
    service = SelectionService()
    candidates = [
        _make_paper_full("Paper A", doi="10.1234/abc", source="arxiv"),
        _make_paper_full("Paper A duplicate", doi="10.1234/ABC", source="openalex"),
    ]

    result = service.deduplicate(candidates)

    assert len(result) == 1
    assert result[0].doi == "10.1234/abc"


def test_dedup_by_arxiv_id() -> None:
    service = SelectionService()
    candidates = [
        _make_paper_full("Paper A", arxiv_id="2301.12345", source="arxiv"),
        _make_paper_full("Paper A Same Paper", arxiv_id="2301.12345", source="openalex"),
    ]

    result = service.deduplicate(candidates)

    assert len(result) == 1
    assert result[0].arxiv_id == "2301.12345"


def test_dedup_by_normalized_title() -> None:
    service = SelectionService()
    candidates = [
        _make_paper_full("Time-Series Anomaly Detection!", source="arxiv"),
        _make_paper_full("Time Series Anomaly Detection", source="openalex"),
    ]

    result = service.deduplicate(candidates)

    assert len(result) == 1


def test_dedup_keeps_different_papers() -> None:
    service = SelectionService()
    candidates = [
        _make_paper_full("Paper A", doi="10.1234/a"),
        _make_paper_full("Paper B", doi="10.1234/b"),
        _make_paper_full("Paper C", doi="10.1234/c"),
    ]

    result = service.deduplicate(candidates)

    assert len(result) == 3


def test_dedup_merges_metadata_from_duplicate() -> None:
    service = SelectionService()
    candidates = [
        _make_paper_full("Paper A", doi="10.1234/abc", abstract="", citation_count=None, pdf_url=""),
        _make_paper_full("Paper A dup", doi="10.1234/ABC", abstract="We study A.", citation_count=42, pdf_url="http://pdf"),
    ]

    result = service.deduplicate(candidates)

    assert len(result) == 1
    assert result[0].abstract == "We study A."
    assert result[0].citation_count == 42
    assert result[0].pdf_url == "http://pdf"


def test_dedup_preserves_sources_and_source_ids_from_duplicates() -> None:
    service = SelectionService()
    candidates = [
        _make_paper_full(
            "Time Series Anomaly Detection",
            doi="10.1234/abc",
            source="arxiv",
            sources=["arxiv"],
            source_ids={"arxiv": "2401.00001"},
            arxiv_id="2401.00001",
            pdf_url="https://arxiv.org/pdf/2401.00001.pdf",
        ),
        _make_paper_full(
            "Time-Series Anomaly Detection!",
            doi="10.1234/ABC",
            source="openalex",
            sources=["openalex"],
            source_ids={"openalex": "W123"},
            landing_url="https://openalex.org/W123",
        ),
    ]

    result = service.deduplicate(candidates)

    assert len(result) == 1
    assert result[0].sources == ["arxiv", "openalex"]
    assert result[0].source_ids == {"arxiv": "2401.00001", "openalex": "W123"}
    assert result[0].arxiv_id == "2401.00001"
    assert result[0].landing_url == "https://openalex.org/W123"


def test_dedup_empty_list() -> None:
    service = SelectionService()

    result = service.deduplicate([])

    assert result == []


def test_dedup_preserves_order() -> None:
    service = SelectionService()
    candidates = [
        _make_paper_full("First Paper", doi="10.1/first"),
        _make_paper_full("Second Paper", doi="10.1/second"),
        _make_paper_full("First Paper dup", doi="10.1/FIRST"),
    ]

    result = service.deduplicate(candidates)

    assert len(result) == 2
    assert result[0].title == "First Paper"
    assert result[1].title == "Second Paper"


def test_max_a_read_does_not_exceed_12() -> None:
    service = SelectionService(max_a_read=12)
    query = _make_query(["time series", "anomaly detection"])
    candidates = [
        _make_paper(f"Time Series Anomaly Detection Paper {i}", abstract="We detect anomalies in time series data.") for i in range(20)
    ]

    plan = service.build_reading_plan(query, candidates)

    a_read_count = sum(1 for item in plan.items if item.priority == "A_READ")
    assert a_read_count <= 12
