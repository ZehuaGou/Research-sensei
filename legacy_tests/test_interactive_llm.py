import os
from unittest.mock import AsyncMock, patch

import pytest

from backend.interactive import InteractiveService
from backend.llm.client import LLMClient
from backend.schemas import (
    CardType,
    InteractiveAnswer,
    InteractiveContextPackage,
    ModelProviderConfig,
)


def _make_package(**overrides):
    defaults = dict(
        session_id="s1", paper_id="p1", card_id="c1",
        card_type=CardType.PAPER_CARD, selected_text="test text",
        current_section="method", current_formula_id="",
        current_concept_id="",
        paper_metadata={"title": "Test Paper"},
        card_json={}, evidence_chunks=[],
        recent_chat_history=[], conversation_summary="",
        user_profile={"math_level": "weak"},
        user_question="什么是正则化？",
    )
    defaults.update(overrides)
    return InteractiveContextPackage(**defaults)


@pytest.mark.asyncio
async def test_interactive_llm_answer():
    config = ModelProviderConfig(name="mock", base_url="https://mock.com", api_key_env="MOCK_KEY", model="mock")
    os.environ["MOCK_KEY"] = "test"
    client = LLMClient(config)

    mock_response = {"answer": "正则化是通过惩罚大参数来约束模型复杂度的机制。"}

    with patch.object(client, "chat_json", new_callable=AsyncMock, return_value=mock_response):
        service = InteractiveService(llm_client=client)
        answer = await service.answer(_make_package())
        assert isinstance(answer, InteractiveAnswer)
        assert "正则化" in answer.answer_zh


def test_interactive_fallback():
    service = InteractiveService(llm_client=None)
    answer = service._fallback(_make_package())
    assert isinstance(answer, InteractiveAnswer)
    assert "test text" in answer.answer_zh
