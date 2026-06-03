from __future__ import annotations

import pytest

from researchsensei.grounding import build_evidence_index
from researchsensei.llm.client import MockLLMClient
from researchsensei.llm.types import ChatMessage
from researchsensei.paper_card import build_paper_card, build_paper_card_with_llm
from researchsensei.paper_skeleton import build_paper_skeleton
from researchsensei.schemas import (
    BlockType,
    DocumentBlock,
    DocumentIngestion,
    EvidenceType,
    PaperCard,
)


def _block(
    block_id: str,
    block_type: BlockType,
    section: str,
    text: str,
    paper_id: str = "paper-1",
) -> DocumentBlock:
    return DocumentBlock(
        block_id=block_id,
        type=block_type,
        section=section,
        text=text,
        evidence_ref=f"{paper_id}:{block_id}",
    )


def _full_doc() -> DocumentIngestion:
    return DocumentIngestion(
        paper_id="paper-1",
        blocks=[
            _block("t001", BlockType.TITLE, "title", "Tiny TSAD Paper"),
            _block("b001", BlockType.ABSTRACT, "abstract", "We study anomaly detection in time series."),
            _block("b002", BlockType.PARAGRAPH, "introduction", "Current methods miss sensor dependencies."),
            _block("b003", BlockType.PARAGRAPH, "method", "We model dependencies with reconstruction error."),
            _block("eq001", BlockType.FORMULA, "method", "L = L_rec + lambda L_graph"),
            _block("b004", BlockType.PARAGRAPH, "experiments", "Table 1 reports F1 on benchmark datasets."),
        ],
    )


def _abstract_only_doc() -> DocumentIngestion:
    return DocumentIngestion(
        paper_id="paper-abstract",
        blocks=[
            _block(
                "b001",
                BlockType.ABSTRACT,
                "abstract",
                "We propose a method, but this fixture has no method or experiments section.",
                paper_id="paper-abstract",
            )
        ],
    )


# ---------------------------------------------------------------------------
# Rule-based builder tests
# ---------------------------------------------------------------------------


def test_rule_based_card_extracts_from_full_document() -> None:
    doc = _full_doc()
    evidence = build_evidence_index(doc)
    skeleton = build_paper_skeleton(doc, evidence)

    card = build_paper_card(skeleton, evidence)

    assert card.paper_id == "paper-1"
    assert card.title == "Tiny TSAD Paper"
    assert card.one_sentence_summary != "UNKNOWN"
    assert card.problem.text != "UNKNOWN"
    assert card.method_overview.text != "UNKNOWN"
    assert card.experiment_summary.text != "UNKNOWN"
    assert card.confidence > 0


def test_rule_based_card_binds_evidence_refs() -> None:
    doc = _full_doc()
    evidence = build_evidence_index(doc)
    skeleton = build_paper_skeleton(doc, evidence)

    card = build_paper_card(skeleton, evidence)

    # At least some claims should have evidence_refs
    claims_with_refs = [
        c for c in [card.problem, card.method_overview, card.experiment_summary]
        if c.evidence_ref
    ]
    assert len(claims_with_refs) > 0

    # All evidence_refs should be valid (present in evidence index)
    valid_refs = {claim.evidence_ref for claim in evidence.claims}
    for claim in claims_with_refs:
        assert claim.evidence_ref in valid_refs, f"Invalid ref: {claim.evidence_ref}"


def test_rule_based_card_marks_missing_sections_as_degraded() -> None:
    doc = _abstract_only_doc()
    evidence = build_evidence_index(doc)
    skeleton = build_paper_skeleton(doc, evidence)

    card = build_paper_card(skeleton, evidence)

    assert card.problem.text in ("UNKNOWN", "INSUFFICIENT_EVIDENCE") or card.problem.evidence_type in {
        EvidenceType.INSUFFICIENT_EVIDENCE, EvidenceType.UNVERIFIED, EvidenceType.NEEDS_HUMAN_CHECK
    }
    assert card.method_overview.evidence_type in {
        EvidenceType.INSUFFICIENT_EVIDENCE, EvidenceType.UNVERIFIED, EvidenceType.NEEDS_HUMAN_CHECK
    }
    assert card.experiment_summary.evidence_type in {
        EvidenceType.INSUFFICIENT_EVIDENCE, EvidenceType.UNVERIFIED, EvidenceType.NEEDS_HUMAN_CHECK
    }


def test_rule_based_card_overall_evidence_status() -> None:
    doc = _full_doc()
    evidence = build_evidence_index(doc)
    skeleton = build_paper_skeleton(doc, evidence)

    card = build_paper_card(skeleton, evidence)

    # Full doc should have at least SUPPORTED_BY_TEXT
    assert card.evidence_status in {
        EvidenceType.SUPPORTED_BY_TEXT,
        EvidenceType.SUPPORTED_BY_FORMULA,
        EvidenceType.SUPPORTED_BY_EXPERIMENT,
    }


def test_rule_based_card_abstract_only_has_degraded_claims() -> None:
    doc = _abstract_only_doc()
    evidence = build_evidence_index(doc)
    skeleton = build_paper_skeleton(doc, evidence)

    card = build_paper_card(skeleton, evidence)

    # Abstract-only: method/experiment/bottleneck should be degraded
    assert card.method_overview.evidence_type in {
        EvidenceType.INSUFFICIENT_EVIDENCE, EvidenceType.UNVERIFIED, EvidenceType.NEEDS_HUMAN_CHECK
    }
    assert card.experiment_summary.evidence_type in {
        EvidenceType.INSUFFICIENT_EVIDENCE, EvidenceType.UNVERIFIED, EvidenceType.NEEDS_HUMAN_CHECK
    }
    # But abstract itself may still be SUPPORTED_BY_TEXT
    assert card.background.evidence_type == EvidenceType.SUPPORTED_BY_TEXT


def test_rule_based_card_formula_claims() -> None:
    doc = _full_doc()
    evidence = build_evidence_index(doc)
    skeleton = build_paper_skeleton(doc, evidence)

    card = build_paper_card(skeleton, evidence)

    assert len(card.key_formulas) >= 1
    assert "L_rec" in card.key_formulas[0].text


def test_rule_based_card_includes_warnings() -> None:
    doc = _abstract_only_doc()
    evidence = build_evidence_index(doc)
    skeleton = build_paper_skeleton(doc, evidence)

    card = build_paper_card(skeleton, evidence)

    assert len(card.warnings) > 0
    assert any("MISSING" in w or "UNAVAILABLE" in w for w in card.warnings)


# ---------------------------------------------------------------------------
# LLM-enhanced builder tests (mock)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_llm_enhanced_card_uses_mock_llm() -> None:
    doc = _full_doc()
    evidence = build_evidence_index(doc)
    skeleton = build_paper_skeleton(doc, evidence)

    mock_response = '{"one_sentence_summary": "We detect anomalies.", "problem": {"text": "Miss dependencies", "evidence_ref": "paper-1:b002"}, "core_idea": {"text": "Reconstruction error", "evidence_ref": "paper-1:b003"}, "method_overview": {"text": "Graph-based model", "evidence_ref": "paper-1:b003"}, "experiment_summary": {"text": "F1 on benchmarks", "evidence_ref": "paper-1:b004"}, "limitations": {"text": "Limited datasets", "evidence_ref": ""}}'
    mock = MockLLMClient(response=mock_response)

    card = await build_paper_card_with_llm(skeleton, evidence, llm_client=mock)

    assert card.one_sentence_summary == "We detect anomalies."
    assert card.problem.text == "Miss dependencies"
    assert card.problem.evidence_ref == "paper-1:b002"
    assert card.core_idea.text == "Reconstruction error"
    # Limitations has empty ref, should be degraded
    assert card.limitations.evidence_type == EvidenceType.INSUFFICIENT_EVIDENCE


@pytest.mark.asyncio
async def test_llm_enhanced_card_rejects_hallucinated_refs() -> None:
    doc = _full_doc()
    evidence = build_evidence_index(doc)
    skeleton = build_paper_skeleton(doc, evidence)

    # LLM returns a hallucinated evidence_ref
    mock_response = '{"one_sentence_summary": "Test.", "problem": {"text": "P", "evidence_ref": "FAKE:ref"}, "core_idea": {"text": "C", "evidence_ref": "FAKE:ref"}, "method_overview": {"text": "M", "evidence_ref": "FAKE:ref"}, "experiment_summary": {"text": "E", "evidence_ref": "FAKE:ref"}, "limitations": {"text": "L", "evidence_ref": ""}}'
    mock = MockLLMClient(response=mock_response)

    card = await build_paper_card_with_llm(skeleton, evidence, llm_client=mock)

    # All hallucinated refs should be stripped
    assert card.problem.evidence_ref == ""
    assert card.problem.evidence_type == EvidenceType.INSUFFICIENT_EVIDENCE


@pytest.mark.asyncio
async def test_llm_enhanced_card_falls_back_on_llm_failure() -> None:
    doc = _full_doc()
    evidence = build_evidence_index(doc)
    skeleton = build_paper_skeleton(doc, evidence)

    mock = MockLLMClient(response="not valid json at all")

    card = await build_paper_card_with_llm(skeleton, evidence, llm_client=mock)

    # Should fall back to rule-based
    assert card.paper_id == "paper-1"
    assert card.title == "Tiny TSAD Paper"


# ---------------------------------------------------------------------------
# Integration with existing artifacts
# ---------------------------------------------------------------------------


def test_paper_card_serializes_to_json() -> None:
    doc = _full_doc()
    evidence = build_evidence_index(doc)
    skeleton = build_paper_skeleton(doc, evidence)

    card = build_paper_card(skeleton, evidence)
    json_str = card.model_dump_json()

    assert "paper-1" in json_str
    assert "Tiny TSAD Paper" in json_str

    # Round-trip
    restored = PaperCard.model_validate_json(json_str)
    assert restored.paper_id == card.paper_id
    assert restored.title == card.title
