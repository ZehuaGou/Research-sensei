from __future__ import annotations

import json

import pytest

from researchsensei.llm.client import MockLLMClient
from researchsensei.query.planner import QueryPlanner, QueryPlanningError


@pytest.mark.asyncio
async def test_query_planner_requires_llm() -> None:
    planner = QueryPlanner()

    with pytest.raises(QueryPlanningError, match="REQUIRES_REAL_LLM"):
        await planner.plan("time series anomaly detection")


@pytest.mark.asyncio
async def test_query_planner_llm_enhanced() -> None:
    mock_response = json.dumps(
        {
            "direction_zh": "时间序列异常检测",
            "direction_en": "Time Series Anomaly Detection",
            "english_query": "time series anomaly detection transformer",
            "query_variants": ["multivariate time series anomaly detection"],
            "core_terms": ["time series", "anomaly detection"],
            "related_terms": ["outlier detection"],
            "exclude_terms": ["forecasting only"],
            "search_intents": ["SURVEY", "SOTA"],
            "sub_directions": [],
            "is_cross_domain": False,
            "domain_components": [],
        }
    )
    mock = MockLLMClient(response=mock_response)
    planner = QueryPlanner(llm_client=mock)

    plan = await planner.plan("时间序列异常检测")

    assert plan.direction_en == "Time Series Anomaly Detection"
    assert plan.english_query == "time series anomaly detection transformer"
    assert "time series" in plan.core_terms
    assert plan.search_intents[0].value == "SURVEY"


@pytest.mark.asyncio
async def test_query_planner_llm_failure_does_not_fall_back() -> None:
    mock = MockLLMClient(response="not valid json")
    planner = QueryPlanner(llm_client=mock)

    with pytest.raises(QueryPlanningError, match="QUERY_PLANNING_FAILED"):
        await planner.plan("test query")


@pytest.mark.asyncio
async def test_query_planner_missing_english_query_fails() -> None:
    mock = MockLLMClient(response=json.dumps({"direction_zh": "时间序列异常检测"}))
    planner = QueryPlanner(llm_client=mock)

    with pytest.raises(QueryPlanningError, match="missing english_query"):
        await planner.plan("时间序列异常检测")
