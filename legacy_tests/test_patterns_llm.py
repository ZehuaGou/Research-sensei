import os
from unittest.mock import AsyncMock, patch

import pytest

from backend.llm.client import LLMClient
from backend.patterns import PatternService
from backend.schemas import ModelProviderConfig, PaperSkeleton, SkeletonField, PatternCard


def _make_skeleton():
    return PaperSkeleton(
        paper_id="p1",
        problem=SkeletonField(plain="test", technical="test", evidence=[]),
        mechanism=SkeletonField(plain="test", technical="test", evidence=[]),
    )


@pytest.mark.asyncio
async def test_pattern_llm():
    config = ModelProviderConfig(name="mock", base_url="https://mock.com", api_key_env="MOCK_KEY", model="mock")
    os.environ["MOCK_KEY"] = "test"
    client = LLMClient(config)

    mock_response = {
        "pattern_name": "Structure Pattern",
        "definition": "通过设计新架构提升性能",
        "why_this_pattern": "核心创新是新注意力结构",
        "how_paper_uses_it": "稀疏注意力替换自注意力",
        "transfer_guidance": "序列建模任务可考虑高效注意力变体",
    }

    with patch.object(client, "chat_json", new_callable=AsyncMock, return_value=mock_response):
        service = PatternService(llm_client=client)
        card = await service.build_pattern_card("pc1", "structure", _make_skeleton())
        assert isinstance(card, PatternCard)
        assert card.definition == "通过设计新架构提升性能"
        assert "核心创新" in card.signals[0]


def test_pattern_fallback():
    service = PatternService(llm_client=None)
    card = service._fallback("pc1", "structure")
    assert isinstance(card, PatternCard)
    assert card.definition == "把论文创新归入通用科研模式，便于迁移到其他方向。"
