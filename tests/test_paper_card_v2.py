from __future__ import annotations

import json

import pytest

from researchsensei.llm.client import LLMResponseError, MockLLMClient
from researchsensei.paper_card_v2 import build_paper_card_v2
from researchsensei.schemas import (
    EvidencePack,
    EvidencePackItem,
    PaperCard,
    PaperSkeleton,
)


def _make_pack() -> EvidencePack:
    return EvidencePack(
        paper_id="test",
        items=[
            EvidencePackItem(
                claim_id="c001", claim_type="PROBLEM", evidence_ref="test:b001",
                passage_text="We study anomaly detection.", confidence=0.7,
            ),
            EvidencePackItem(
                claim_id="c002", claim_type="METHOD", evidence_ref="test:b002",
                passage_text="We propose a graph neural network.", confidence=0.7,
            ),
            EvidencePackItem(
                claim_id="c003", claim_type="RESULT", evidence_ref="test:b003",
                passage_text="We achieve 95 F1.", confidence=0.7,
            ),
            EvidencePackItem(
                claim_id="c004", claim_type="CONTRIBUTION", evidence_ref="test:b004",
                passage_text="We present a novel approach.", confidence=0.7,
            ),
        ],
    )


def _make_skeleton() -> PaperSkeleton:
    return PaperSkeleton(
        paper_id="test",
        title="Test Paper",
        abstract_summary="We study anomaly detection.",
        problem="Detecting anomalies is hard.",
        method_overview="Graph neural network.",
        experiment_overview="95 F1.",
    )


def _valid_llm_response() -> str:
    return json.dumps({
        "one_sentence_summary": "We propose a GNN for anomaly detection.",
        "problem": {"text": "Detecting anomalies is hard.", "evidence_ref": "test:b001"},
        "core_idea": {"text": "Graph neural network.", "evidence_ref": "test:b002"},
        "method_overview": {"text": "We use GNN to model dependencies.", "evidence_ref": "test:b002"},
        "experiment_summary": {"text": "95 F1 score.", "evidence_ref": "test:b003"},
        "limitations": {"text": "Needs more data.", "evidence_ref": ""},
    })


@pytest.mark.asyncio
async def test_paper_card_v2_success() -> None:
    pack = _make_pack()
    skeleton = _make_skeleton()
    client = MockLLMClient(response=_valid_llm_response())

    card = await build_paper_card_v2(pack, skeleton, client)

    assert isinstance(card, PaperCard)
    assert card.paper_id == "test"
    assert card.one_sentence_summary == "We propose a GNN for anomaly detection."
    assert len(client.calls) == 1


@pytest.mark.asyncio
async def test_paper_card_v2_maps_to_paper_card() -> None:
    pack = _make_pack()
    skeleton = _make_skeleton()
    client = MockLLMClient(response=_valid_llm_response())

    card = await build_paper_card_v2(pack, skeleton, client)

    assert card.problem.text == "Detecting anomalies is hard."
    assert card.core_idea.text == "Graph neural network."
    assert card.method_overview.text == "We use GNN to model dependencies."
    assert card.experiment_summary.text == "95 F1 score."


@pytest.mark.asyncio
async def test_paper_card_v2_evidence_refs_from_pack() -> None:
    pack = _make_pack()
    skeleton = _make_skeleton()
    client = MockLLMClient(response=_valid_llm_response())

    card = await build_paper_card_v2(pack, skeleton, client)

    assert "test:b001" in card.evidence_refs
    assert "test:b002" in card.evidence_refs
    assert "test:b003" in card.evidence_refs


@pytest.mark.asyncio
async def test_paper_card_v2_invalid_json_raises() -> None:
    pack = _make_pack()
    skeleton = _make_skeleton()
    client = MockLLMClient(response="not json at all")

    with pytest.raises(LLMResponseError):
        await build_paper_card_v2(pack, skeleton, client)


@pytest.mark.asyncio
async def test_paper_card_v2_invalid_schema_raises() -> None:
    pack = _make_pack()
    skeleton = _make_skeleton()
    client = MockLLMClient(response=json.dumps({"wrong_field": "value"}))

    with pytest.raises(Exception):
        await build_paper_card_v2(pack, skeleton, client)


@pytest.mark.asyncio
async def test_paper_card_v2_invalid_evidence_ref_raises() -> None:
    pack = _make_pack()
    skeleton = _make_skeleton()
    bad_response = json.dumps({
        "one_sentence_summary": "Test",
        "problem": {"text": "P", "evidence_ref": "INVALID"},
        "core_idea": {"text": "C", "evidence_ref": "test:b002"},
        "method_overview": {"text": "M", "evidence_ref": "test:b002"},
        "experiment_summary": {"text": "E", "evidence_ref": "test:b003"},
    })
    client = MockLLMClient(response=bad_response)

    with pytest.raises(ValueError, match="INVALID"):
        await build_paper_card_v2(pack, skeleton, client)


@pytest.mark.asyncio
async def test_paper_card_v2_llm_failure_raises_no_fallback() -> None:
    pack = _make_pack()
    skeleton = _make_skeleton()

    class FailingClient:
        async def chat(self, messages, **kwargs):
            raise RuntimeError("LLM exploded")

        async def chat_json(self, messages, **kwargs):
            raise RuntimeError("LLM exploded")

    with pytest.raises(RuntimeError, match="LLM exploded"):
        await build_paper_card_v2(pack, skeleton, FailingClient())


def test_old_build_paper_card_unchanged() -> None:
    from researchsensei.grounding import build_evidence_index
    from researchsensei.ingestion.lightweight import LightweightIngestionService
    from researchsensei.paper_card import build_paper_card
    from researchsensei.paper_skeleton import build_paper_skeleton

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
        card = build_paper_card(skeleton, evidence)

        assert isinstance(card, PaperCard)
        assert card.paper_id == "test-old"
    finally:
        path.unlink()
