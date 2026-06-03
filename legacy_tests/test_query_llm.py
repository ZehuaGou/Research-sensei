import os
from unittest.mock import AsyncMock, patch

import pytest

from backend.llm.client import LLMClient
from backend.query import QueryService
from backend.schemas import ModelProviderConfig, QueryPlan, SearchIntent


@pytest.mark.asyncio
async def test_query_llm_understanding():
    config = ModelProviderConfig(
        name="mock", base_url="https://mock.com", api_key_env="MOCK_KEY", model="mock"
    )
    os.environ["MOCK_KEY"] = "test"
    client = LLMClient(config)

    mock_response = {
        "direction_zh": "RAG可信性",
        "direction_en": "RAG trustworthiness",
        "core_terms": ["RAG", "retrieval augmented generation", "faithfulness"],
        "related_terms": ["hallucination", "grounding", "citation"],
        "exclude_terms": [],
        "search_intents": ["SURVEY_PAPER", "SOTA_METHOD"],
        "sub_directions": [],
        "is_cross_domain": False,
        "domain_components": [],
    }

    with patch.object(client, "chat_json", new_callable=AsyncMock, return_value=mock_response):
        service = QueryService(llm_client=client)
        plan = await service.understand("RAG可信性")
        assert isinstance(plan, QueryPlan)
        assert plan.direction_en == "RAG trustworthiness"
        assert SearchIntent.SURVEY_PAPER in plan.search_intents


def test_query_fallback():
    service = QueryService(llm_client=None)
    plan = service._fallback("time series anomaly detection")
    assert isinstance(plan, QueryPlan)
    assert plan.direction_en == "time series anomaly detection"
    assert SearchIntent.SURVEY_PAPER in plan.search_intents
