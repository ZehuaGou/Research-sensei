import os
from unittest.mock import AsyncMock, patch

import pytest

from backend.formula import FormulaService
from backend.llm.client import LLMClient
from backend.schemas import BlockType, DocumentBlock, FormulaCard, ModelProviderConfig


def _make_block():
    return DocumentBlock(
        block_id="eq001",
        type=BlockType.FORMULA,
        section="method",
        page=3,
        raw_latex="\\mathcal{L} = \\mathcal{L}_{task} + \\lambda \\mathcal{L}_{reg}",
        nearby_text="The total loss combines task and regularization",
        equation_number="1",
        evidence_ref="p1:eq001",
    )


@pytest.mark.asyncio
async def test_formula_llm_breakdown():
    config = ModelProviderConfig(name="mock", base_url="https://mock.com", api_key_env="MOCK_KEY", model="mock")
    os.environ["MOCK_KEY"] = "test"
    client = LLMClient(config)

    mock_response = {
        "formula_latex": "\\mathcal{L} = \\mathcal{L}_{task} + \\lambda \\mathcal{L}_{reg}",
        "problem": "定义总损失函数",
        "symbols": [
            {"symbol": "\\mathcal{L}", "meaning": "总损失", "role": "优化目标"},
            {"symbol": "\\lambda", "meaning": "平衡系数", "role": "控制权重"},
        ],
        "numeric_example": "L_task=0.8, L_reg=0.3, λ=0.5 → L=0.95",
        "remove_effect": "去掉正则项→过拟合",
        "weight_change_effect": "λ太大→欠拟合，太小→过拟合",
        "plain_summary": "总损失 = 做对任务 + 控制复杂度",
    }

    with patch.object(client, "chat_json", new_callable=AsyncMock, return_value=mock_response):
        service = FormulaService(llm_client=client)
        card = await service.build_formula_card("f1", "p1", _make_block())
        assert isinstance(card, FormulaCard)
        assert len(card.symbols) == 2
        assert card.plain_summary == "总损失 = 做对任务 + 控制复杂度"


def test_formula_fallback():
    service = FormulaService(llm_client=None)
    card = service._fallback("f1", "p1", _make_block())
    assert isinstance(card, FormulaCard)
    assert card.formula_ref == "eq001"
