from __future__ import annotations

import json

import pytest

from researchsensei.formula_card_v2 import build_formula_cards_v2
from researchsensei.llm.client import LLMResponseError, MockLLMClient
from researchsensei.schemas import (
    EvidencePack,
    EvidencePackItem,
    FormulaCardBundle,
    PaperSkeleton,
)


def _make_pack() -> EvidencePack:
    return EvidencePack(
        paper_id="test",
        items=[
            EvidencePackItem(
                claim_id="c001", claim_type="FORMULA_CONTEXT", evidence_ref="test:eq001",
                passage_text="L = L_rec + lambda * L_reg", confidence=0.7,
            ),
        ],
    )


def _make_skeleton() -> PaperSkeleton:
    return PaperSkeleton(
        paper_id="test",
        title="Test Paper",
        formulas=["L = L_rec + lambda * L_reg"],
    )


def _valid_llm_response() -> str:
    return json.dumps({
        "formula_cards": [
            {
                "purpose": "定义损失函数",
                "intuition": "重构误差加正则化",
                "numeric_example": "L_rec=0.5, lambda=0.1, L=0.6",
                "plain_summary": "总损失等于重构损失加正则项",
                "evidence_ref": "test:eq001",
            }
        ]
    })


@pytest.mark.asyncio
async def test_formula_cards_v2_success() -> None:
    pack = _make_pack()
    skeleton = _make_skeleton()
    client = MockLLMClient(response=_valid_llm_response())

    bundle = await build_formula_cards_v2(pack, skeleton, client)

    assert isinstance(bundle, FormulaCardBundle)
    assert bundle.paper_id == "test"
    assert len(bundle.formula_cards) == 1
    assert bundle.formula_cards[0].purpose == "定义损失函数"
    assert len(client.calls) == 1


@pytest.mark.asyncio
async def test_formula_cards_v2_empty_returns_empty_bundle() -> None:
    pack = _make_pack()
    skeleton = _make_skeleton()
    client = MockLLMClient(response=json.dumps({"formula_cards": []}))

    bundle = await build_formula_cards_v2(pack, skeleton, client)

    assert len(bundle.formula_cards) == 0
    assert "NO_FORMULA_CARDS_FROM_LLM" in bundle.warnings


@pytest.mark.asyncio
async def test_formula_cards_v2_invalid_evidence_ref_raises() -> None:
    pack = _make_pack()
    skeleton = _make_skeleton()
    bad_response = json.dumps({
        "formula_cards": [
            {"purpose": "P", "evidence_ref": "INVALID"}
        ]
    })
    client = MockLLMClient(response=bad_response)

    with pytest.raises(ValueError, match="INVALID"):
        await build_formula_cards_v2(pack, skeleton, client)


@pytest.mark.asyncio
async def test_formula_cards_v2_missing_evidence_ref_raises() -> None:
    pack = _make_pack()
    skeleton = _make_skeleton()
    bad_response = json.dumps({
        "formula_cards": [
            {"purpose": "P", "evidence_ref": ""}
        ]
    })
    client = MockLLMClient(response=bad_response)

    with pytest.raises(ValueError, match="no evidence_ref"):
        await build_formula_cards_v2(pack, skeleton, client)


@pytest.mark.asyncio
async def test_formula_cards_v2_llm_failure_raises() -> None:
    pack = _make_pack()
    skeleton = _make_skeleton()

    class FailingClient:
        async def chat(self, messages, **kwargs):
            raise RuntimeError("LLM exploded")

    with pytest.raises(RuntimeError, match="LLM exploded"):
        await build_formula_cards_v2(pack, skeleton, FailingClient())


def test_old_build_formula_cards_unchanged() -> None:
    from researchsensei.formula_card import build_formula_cards
    from researchsensei.grounding import build_evidence_index
    from researchsensei.ingestion.lightweight import LightweightIngestionService
    from researchsensei.paper_skeleton import build_paper_skeleton

    import tempfile
    from pathlib import Path

    with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False, encoding="utf-8") as f:
        f.write("# Paper\n## Abstract\nWe study anomaly detection.\n\n## Method\nWe minimize L = L_rec.")
        f.flush()
        path = Path(f.name)

    try:
        ingestion = LightweightIngestionService()
        doc = ingestion.ingest_path(path, paper_id="test-old")
        evidence = build_evidence_index(doc)
        skeleton = build_paper_skeleton(doc, evidence)
        bundle = build_formula_cards(doc, evidence, skeleton)

        assert isinstance(bundle, FormulaCardBundle)
        assert bundle.paper_id == "test-old"
    finally:
        path.unlink()
