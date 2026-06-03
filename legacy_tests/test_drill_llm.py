import os
from unittest.mock import AsyncMock, patch

import pytest

from backend.drill import DrillService
from backend.llm.client import LLMClient
from backend.schemas import DrillCard, ModelProviderConfig, PaperSkeleton, SkeletonField


def _make_skeleton():
    return PaperSkeleton(
        paper_id="p1",
        problem=SkeletonField(plain="问题", technical="tech", evidence=[]),
        mechanism=SkeletonField(plain="机制", technical="tech", evidence=[]),
    )


@pytest.mark.asyncio
async def test_drill_llm_questions():
    config = ModelProviderConfig(name="mock", base_url="https://mock.com", api_key_env="MOCK_KEY", model="mock")
    os.environ["MOCK_KEY"] = "test"
    client = LLMClient(config)

    mock_response = {
        "immediate_recall": [{"question": "复述题1", "expected_key_points": ["点1"]}],
        "next_day_review": [{"question": "复习题1", "expected_key_points": ["点2"]}],
        "one_week_transfer": [{"question": "迁移题1", "expected_key_points": ["点3"]}],
        "advisor_questions": [{"question": "追问1", "expected_key_points": ["点4"]}],
        "weakness_checks": [{"question": "检查题1", "linked_concept": "概念"}],
    }

    with patch.object(client, "chat_json", new_callable=AsyncMock, return_value=mock_response):
        service = DrillService(llm_client=client)
        card = await service.build_drill_card(_make_skeleton())
        assert isinstance(card, DrillCard)
        assert len(card.recall_questions) >= 1
        assert len(card.advisor_questions) >= 1
        assert len(card.error_attribution_prompts) >= 1


def test_drill_fallback():
    service = DrillService(llm_client=None)
    card = service._fallback(_make_skeleton())
    assert isinstance(card, DrillCard)
    assert len(card.recall_questions) >= 1
