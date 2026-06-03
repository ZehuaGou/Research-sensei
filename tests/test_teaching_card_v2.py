from __future__ import annotations

import json

import pytest

from researchsensei.llm.client import LLMResponseError, MockLLMClient
from researchsensei.schemas import (
    CardClaim,
    EvidencePack,
    EvidencePackItem,
    EvidenceType,
    PaperCard,
    PaperSkeleton,
    TeachingCardBundle,
)
from researchsensei.teaching_card_v2 import build_teaching_cards_v2


def _make_pack() -> EvidencePack:
    return EvidencePack(
        paper_id="test",
        items=[
            EvidencePackItem(
                claim_id="c001", claim_type="METHOD", evidence_ref="test:b001",
                passage_text="We propose a graph neural network.", confidence=0.7,
            ),
        ],
    )


def _make_paper_card() -> PaperCard:
    return PaperCard(
        paper_id="test",
        title="Test Paper",
        one_sentence_summary="We propose a GNN.",
        core_idea=CardClaim(text="Graph neural network", evidence_ref="test:b001"),
        problem=CardClaim(text="Anomaly detection", evidence_ref="test:b001"),
        method_overview=CardClaim(text="GNN approach", evidence_ref="test:b001"),
    )


def _make_skeleton() -> PaperSkeleton:
    return PaperSkeleton(paper_id="test", title="Test Paper")


def _valid_llm_response() -> str:
    return json.dumps({
        "teaching_cards": [
            {
                "target_type": "concept",
                "title": "核心创新点",
                "human_explanation": "用图神经网络来建模传感器之间的关系",
                "analogy_explanation": "就像社交网络中朋友之间的关系",
                "minimal_formula_explanation": "h_i = f(x_i, neighbors)",
                "numeric_example": "3个传感器，每对有边",
                "paper_role_explanation": "这是论文的核心方法",
                "evidence_ref": "test:b001",
            }
        ]
    })


@pytest.mark.asyncio
async def test_teaching_cards_v2_success() -> None:
    pack = _make_pack()
    card = _make_paper_card()
    skeleton = _make_skeleton()
    client = MockLLMClient(response=_valid_llm_response())

    bundle = await build_teaching_cards_v2(pack, card, skeleton, client)

    assert isinstance(bundle, TeachingCardBundle)
    assert bundle.paper_id == "test"
    assert len(bundle.teaching_cards) == 1
    assert bundle.teaching_cards[0].human_explanation == "用图神经网络来建模传感器之间的关系"
    assert len(client.calls) == 1


@pytest.mark.asyncio
async def test_teaching_cards_v2_maps_to_teaching_card_bundle() -> None:
    pack = _make_pack()
    card = _make_paper_card()
    skeleton = _make_skeleton()
    client = MockLLMClient(response=_valid_llm_response())

    bundle = await build_teaching_cards_v2(pack, card, skeleton, client)

    tc = bundle.teaching_cards[0]
    assert tc.analogy_explanation == "就像社交网络中朋友之间的关系"
    assert tc.numeric_example == "3个传感器，每对有边"
    assert tc.paper_role_explanation == "这是论文的核心方法"
    assert "test:b001" in tc.evidence_refs


@pytest.mark.asyncio
async def test_teaching_cards_v2_human_explanation_requires_evidence_ref() -> None:
    pack = _make_pack()
    card = _make_paper_card()
    skeleton = _make_skeleton()
    bad_response = json.dumps({
        "teaching_cards": [
            {"human_explanation": "H", "evidence_ref": ""}
        ]
    })
    client = MockLLMClient(response=bad_response)

    with pytest.raises(ValueError, match="required"):
        await build_teaching_cards_v2(pack, card, skeleton, client)


@pytest.mark.asyncio
async def test_teaching_cards_v2_invalid_evidence_ref_raises() -> None:
    pack = _make_pack()
    card = _make_paper_card()
    skeleton = _make_skeleton()
    bad_response = json.dumps({
        "teaching_cards": [
            {"human_explanation": "H", "evidence_ref": "INVALID"}
        ]
    })
    client = MockLLMClient(response=bad_response)

    with pytest.raises(ValueError, match="INVALID"):
        await build_teaching_cards_v2(pack, card, skeleton, client)


@pytest.mark.asyncio
async def test_teaching_cards_v2_llm_failure_raises() -> None:
    pack = _make_pack()
    card = _make_paper_card()
    skeleton = _make_skeleton()

    class FailingClient:
        async def chat(self, messages, **kwargs):
            raise RuntimeError("LLM exploded")

        async def chat_json(self, messages, **kwargs):
            raise RuntimeError("LLM exploded")

    with pytest.raises(RuntimeError, match="LLM exploded"):
        await build_teaching_cards_v2(pack, card, skeleton, FailingClient())


def test_old_build_teaching_cards_unchanged() -> None:
    from researchsensei.formula_card import build_formula_cards
    from researchsensei.grounding import build_evidence_index
    from researchsensei.ingestion.lightweight import LightweightIngestionService
    from researchsensei.paper_card import build_paper_card
    from researchsensei.paper_skeleton import build_paper_skeleton
    from researchsensei.teaching_card import build_teaching_cards

    import tempfile
    from pathlib import Path

    with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False, encoding="utf-8") as f:
        f.write("# Paper\n## Abstract\nWe study anomaly detection.\n\n## Method\nWe propose a model.")
        f.flush()
        path = Path(f.name)

    try:
        ingestion = LightweightIngestionService()
        doc = ingestion.ingest_path(path, paper_id="test-old")
        evidence = build_evidence_index(doc)
        skeleton = build_paper_skeleton(doc, evidence)
        paper_card = build_paper_card(skeleton, evidence)
        formula_cards = build_formula_cards(doc, evidence, skeleton)
        bundle = build_teaching_cards(paper_card, formula_cards, skeleton, evidence)

        assert isinstance(bundle, TeachingCardBundle)
        assert bundle.paper_id == "test-old"
    finally:
        path.unlink()
