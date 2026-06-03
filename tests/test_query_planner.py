from __future__ import annotations

import pytest

from researchsensei.llm.client import MockLLMClient
from researchsensei.query.planner import QueryPlanner


@pytest.mark.asyncio
async def test_query_planner_fallback_with_chinese() -> None:
    planner = QueryPlanner()
    plan = await planner.plan("时间序列异常检测")

    assert plan.user_query == "时间序列异常检测"
    assert plan.language == "zh"
    assert plan.direction_zh == "时间序列异常检测"
    assert len(plan.core_terms) > 0
    assert "RULE_BASED_FALLBACK" in plan.warnings


@pytest.mark.asyncio
async def test_query_planner_fallback_with_english() -> None:
    planner = QueryPlanner()
    plan = await planner.plan("time series anomaly detection")

    assert plan.user_query == "time series anomaly detection"
    assert plan.language == "en"
    assert plan.direction_en == "time series anomaly detection"
    assert len(plan.core_terms) > 0


@pytest.mark.asyncio
async def test_query_planner_fallback_with_comma_separated() -> None:
    planner = QueryPlanner()
    plan = await planner.plan("anomaly detection, time series, deep learning")

    assert len(plan.core_terms) == 3
    assert "anomaly detection" in plan.core_terms


@pytest.mark.asyncio
async def test_query_planner_llm_enhanced() -> None:
    mock_response = '{"direction_zh": "时间序列异常检测", "direction_en": "Time Series Anomaly Detection", "core_terms": ["time series", "anomaly detection"], "related_terms": ["outlier detection"], "exclude_terms": [], "search_intents": ["SURVEY", "SOTA"], "sub_directions": [], "is_cross_domain": false, "domain_components": []}'
    mock = MockLLMClient(response=mock_response)
    planner = QueryPlanner(llm_client=mock)

    plan = await planner.plan("时间序列异常检测")

    assert plan.direction_en == "Time Series Anomaly Detection"
    assert "time series" in plan.core_terms
    assert "SURVEY" in plan.search_intents


@pytest.mark.asyncio
async def test_query_planner_llm_failure_falls_back() -> None:
    mock = MockLLMClient(response="not valid json")
    planner = QueryPlanner(llm_client=mock)

    plan = await planner.plan("test query")

    assert plan.user_query == "test query"
    assert "RULE_BASED_FALLBACK" in plan.warnings
