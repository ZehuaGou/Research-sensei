from __future__ import annotations

import pytest

from researchsensei.schemas import (
    CandidatePaper,
    CandidatePool,
    DirectionBundle,
    QueryPlan,
    ReadingPlan,
    ReadingPlanItem,
    ScoringBreakdown,
    SearchIntent,
    SeedExpansionBundle,
    SeedExpansionPaper,
    SeedPaperInput,
)


def test_query_plan_serializes() -> None:
    plan = QueryPlan(
        user_query="time series anomaly detection",
        language="en",
        direction_en="Time Series Anomaly Detection",
        core_terms=["time series", "anomaly detection"],
        search_intents=[SearchIntent.SURVEY, SearchIntent.SOTA],
    )

    restored = QueryPlan.model_validate_json(plan.model_dump_json())

    assert restored.user_query == "time series anomaly detection"
    assert len(restored.core_terms) == 2
    assert SearchIntent.SURVEY in restored.search_intents


def test_candidate_paper_serializes() -> None:
    paper = CandidatePaper(
        paper_id="2301.12345",
        title="Time Series Anomaly Detection",
        authors=["John Doe", "Jane Smith"],
        year=2023,
        venue="arXiv",
        source="arxiv",
        arxiv_id="2301.12345",
        abstract="We detect anomalies.",
        citation_count=50,
    )

    restored = CandidatePaper.model_validate_json(paper.model_dump_json())

    assert restored.title == "Time Series Anomaly Detection"
    assert len(restored.authors) == 2
    assert restored.citation_count == 50


def test_scoring_breakdown_serializes() -> None:
    breakdown = ScoringBreakdown(
        relevance_score=0.9,
        venue_prestige=0.7,
        citation_score=0.5,
        weighted_total=0.75,
    )

    restored = ScoringBreakdown.model_validate_json(breakdown.model_dump_json())

    assert restored.relevance_score == 0.9
    assert restored.weighted_total == 0.75


def test_reading_plan_item_serializes() -> None:
    item = ReadingPlanItem(
        paper=CandidatePaper(paper_id="p1", title="Test Paper"),
        role="METHOD",
        priority="A_READ",
        scoring_breakdown=ScoringBreakdown(weighted_total=0.8),
        selection_reason="Strong relevance.",
    )

    restored = ReadingPlanItem.model_validate_json(item.model_dump_json())

    assert restored.paper.title == "Test Paper"
    assert restored.priority == "A_READ"


def test_reading_plan_serializes() -> None:
    plan = ReadingPlan(
        topic="Time Series Anomaly Detection",
        items=[
            ReadingPlanItem(
                paper=CandidatePaper(paper_id="p1", title="Paper 1"),
                priority="A_READ",
            ),
        ],
    )

    restored = ReadingPlan.model_validate_json(plan.model_dump_json())

    assert restored.topic == "Time Series Anomaly Detection"
    assert len(restored.items) == 1


def test_candidate_pool_serializes() -> None:
    pool = CandidatePool(
        query="test",
        retrieved_count=5,
        deduplicated_count=4,
        items=[CandidatePaper(paper_id="p1", title="Paper 1")],
        search_log=["arxiv: searched"],
    )

    restored = CandidatePool.model_validate_json(pool.model_dump_json())

    assert restored.retrieved_count == 5
    assert len(restored.items) == 1


def test_direction_bundle_serializes() -> None:
    bundle = DirectionBundle(
        query_plan=QueryPlan(user_query="test", core_terms=["test"]),
        candidate_pool=CandidatePool(query="test"),
        filtered_candidates=CandidatePool(query="test"),
        reading_plan=ReadingPlan(topic="test"),
    )

    restored = DirectionBundle.model_validate_json(bundle.model_dump_json())

    assert restored.query_plan.user_query == "test"
    assert restored.filtered_candidates.query == "test"


def test_seed_expansion_bundle_serializes() -> None:
    bundle = SeedExpansionBundle(
        status="DEGRADED",
        seed_expansion_status="DEGRADED",
        seed=SeedPaperInput(title="Seed Paper", arxiv_id="2401.00001"),
        upstream_papers=[
            SeedExpansionPaper(
                paper_id="p1",
                title="Foundation Paper",
                relation_type="upstream",
                relation_reason="weak_relation: query similarity, not a verified citation graph.",
            )
        ],
    )

    restored = SeedExpansionBundle.model_validate_json(bundle.model_dump_json())

    assert restored.seed.title == "Seed Paper"
    assert restored.upstream_papers[0].citation_graph_verified is False
    assert restored.upstream_papers[0].is_weak_relation is True


def test_search_intent_enum_values() -> None:
    assert SearchIntent.GENERAL == "GENERAL"
    assert SearchIntent.SURVEY == "SURVEY"
    assert SearchIntent.FOUNDATIONAL == "FOUNDATIONAL"
    assert SearchIntent.SOTA == "SOTA"
    assert SearchIntent.BENCHMARK == "BENCHMARK"
    assert SearchIntent.CODE == "CODE"


def test_search_intent_in_query_plan() -> None:
    plan = QueryPlan(
        user_query="test",
        search_intents=[SearchIntent.SURVEY, SearchIntent.SOTA],
    )
    restored = QueryPlan.model_validate_json(plan.model_dump_json())
    assert restored.search_intents == [SearchIntent.SURVEY, SearchIntent.SOTA]


def test_search_intent_rejects_invalid_value() -> None:
    with pytest.raises(ValueError):
        SearchIntent("INVALID_INTENT")
