import os
from unittest.mock import AsyncMock, patch

import pytest

from backend.llm.client import LLMClient
from backend.schemas import ModelProviderConfig, PaperSkeleton, SkeletonField, TeachingCard
from backend.teaching import TeachingService


def _make_skeleton():
    return PaperSkeleton(
        paper_id="p1",
        problem=SkeletonField(plain="问题", technical="tech", evidence=[]),
        mechanism=SkeletonField(plain="机制", technical="tech", evidence=[]),
    )


@pytest.mark.asyncio
async def test_teaching_five_layer():
    config = ModelProviderConfig(name="mock", base_url="https://mock.com", api_key_env="MOCK_KEY", model="mock")
    os.environ["MOCK_KEY"] = "test"
    client = LLMClient(config)

    mock_response = {
        "thirty_second": "30秒总结",
        "five_minute": "5分钟讲解",
        "deep_dive": "深入推导",
    }

    with patch.object(client, "chat_json", new_callable=AsyncMock, return_value=mock_response):
        service = TeachingService(llm_client=client)
        card = await service.build_paper_card(_make_skeleton())
        assert isinstance(card, TeachingCard)
        assert card.thirty_second == "30秒总结"
        assert card.five_minute == "5分钟讲解"


def test_teaching_fallback():
    service = TeachingService(llm_client=None)
    card = service._fallback(_make_skeleton())
    assert isinstance(card, TeachingCard)
    assert card.thirty_second == "问题"
