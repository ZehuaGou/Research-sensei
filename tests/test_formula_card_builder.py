from __future__ import annotations

import pytest

from researchsensei.formula_card import build_formula_cards, build_formula_cards_with_llm
from researchsensei.grounding import build_evidence_index
from researchsensei.llm.client import MockLLMClient
from researchsensei.paper_skeleton import build_paper_skeleton
from researchsensei.schemas import (
    BlockType,
    DocumentBlock,
    DocumentIngestion,
    EvidenceType,
)


def _block(
    block_id: str,
    block_type: BlockType,
    section: str,
    text: str,
    paper_id: str = "paper-1",
    raw_latex: str = "",
) -> DocumentBlock:
    return DocumentBlock(
        block_id=block_id,
        type=block_type,
        section=section,
        text=text,
        evidence_ref=f"{paper_id}:{block_id}",
        raw_latex=raw_latex,
    )


def _doc_with_formulas() -> DocumentIngestion:
    return DocumentIngestion(
        paper_id="paper-1",
        blocks=[
            _block("t001", BlockType.TITLE, "title", "Tiny TSAD Paper"),
            _block("b001", BlockType.ABSTRACT, "abstract", "We study anomaly detection."),
            _block("b002", BlockType.PARAGRAPH, "method", "We minimize reconstruction error."),
            _block("eq001", BlockType.FORMULA, "method", "L = L_rec + lambda L_graph", raw_latex="L = L_{rec} + \\lambda L_{graph}"),
            _block("b003", BlockType.PARAGRAPH, "experiments", "Table 1 reports F1."),
        ],
    )


def _doc_without_formulas() -> DocumentIngestion:
    return DocumentIngestion(
        paper_id="paper-nf",
        blocks=[
            _block("b001", BlockType.ABSTRACT, "abstract", "We study anomaly detection."),
            _block("b002", BlockType.PARAGRAPH, "method", "We minimize reconstruction error."),
        ],
    )


# ---------------------------------------------------------------------------
# Rule-based builder tests
# ---------------------------------------------------------------------------


def test_rule_based_formula_cards_extract_from_document() -> None:
    doc = _doc_with_formulas()
    evidence = build_evidence_index(doc)
    skeleton = build_paper_skeleton(doc, evidence)

    bundle = build_formula_cards(doc, evidence, skeleton)

    assert bundle.paper_id == "paper-1"
    assert len(bundle.formula_cards) == 1
    card = bundle.formula_cards[0]
    assert card.formula_raw == "L = L_{rec} + \\lambda L_{graph}"
    assert card.evidence_ref == "paper-1:eq001"
    assert card.location == "method"


def test_rule_based_formula_card_binds_evidence_ref() -> None:
    doc = _doc_with_formulas()
    evidence = build_evidence_index(doc)
    skeleton = build_paper_skeleton(doc, evidence)

    bundle = build_formula_cards(doc, evidence, skeleton)
    card = bundle.formula_cards[0]

    valid_refs = {claim.evidence_ref for claim in evidence.claims}
    assert card.evidence_ref in valid_refs


def test_rule_based_formula_card_extracts_symbols() -> None:
    doc = _doc_with_formulas()
    evidence = build_evidence_index(doc)
    skeleton = build_paper_skeleton(doc, evidence)

    bundle = build_formula_cards(doc, evidence, skeleton)
    card = bundle.formula_cards[0]

    symbol_names = {s.symbol for s in card.symbols}
    assert "L" in symbol_names
    assert "lambda" in symbol_names


def test_rule_based_formula_card_extracts_terms() -> None:
    doc = _doc_with_formulas()
    evidence = build_evidence_index(doc)
    skeleton = build_paper_skeleton(doc, evidence)

    bundle = build_formula_cards(doc, evidence, skeleton)
    card = bundle.formula_cards[0]

    assert len(card.terms) >= 1


def test_rule_based_formula_card_marks_degraded_fields() -> None:
    doc = _doc_with_formulas()
    evidence = build_evidence_index(doc)
    skeleton = build_paper_skeleton(doc, evidence)

    bundle = build_formula_cards(doc, evidence, skeleton)
    card = bundle.formula_cards[0]

    # Rule-based can't determine these
    assert card.intuition == "NEEDS_HUMAN_CHECK"
    assert card.numeric_example == "NEEDS_HUMAN_CHECK"
    assert card.what_if_removed == "NEEDS_HUMAN_CHECK"


def test_no_formulas_returns_formula_unavailable() -> None:
    doc = _doc_without_formulas()
    evidence = build_evidence_index(doc)
    skeleton = build_paper_skeleton(doc, evidence)

    bundle = build_formula_cards(doc, evidence, skeleton)

    assert len(bundle.formula_cards) == 0
    assert "FORMULA_UNAVAILABLE" in bundle.warnings
    assert bundle.evidence_status == EvidenceType.INSUFFICIENT_EVIDENCE


def test_formula_card_evidence_status_from_evidence_index() -> None:
    doc = _doc_with_formulas()
    evidence = build_evidence_index(doc)
    skeleton = build_paper_skeleton(doc, evidence)

    bundle = build_formula_cards(doc, evidence, skeleton)
    card = bundle.formula_cards[0]

    # Should be SUPPORTED_BY_FORMULA since the formula block generates that evidence type
    assert card.evidence_status == EvidenceType.SUPPORTED_BY_FORMULA


def test_formula_card_bundle_confidence() -> None:
    doc = _doc_with_formulas()
    evidence = build_evidence_index(doc)
    skeleton = build_paper_skeleton(doc, evidence)

    bundle = build_formula_cards(doc, evidence, skeleton)

    assert bundle.confidence > 0
    assert bundle.confidence <= 1.0


# ---------------------------------------------------------------------------
# LLM-enhanced builder tests (mock)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_llm_enhanced_formula_card_uses_mock_llm() -> None:
    doc = _doc_with_formulas()
    evidence = build_evidence_index(doc)
    skeleton = build_paper_skeleton(doc, evidence)

    mock_response = '''{
        "purpose": "定义总损失函数",
        "intuition": "既要重构准确，又要保持图结构",
        "numeric_example": "L_rec=2, L_graph=0.5, lambda=0.1, L=2+0.1*0.5=2.05",
        "what_if_removed": "去掉图约束，模型只追求重构",
        "weight_sensitivity": "lambda大更重视图结构",
        "plain_summary": "平衡重构和结构约束",
        "symbols": [{"symbol": "L", "meaning": "总损失"}],
        "terms": [{"term": "L_rec", "meaning": "重构损失", "encourages": "准确重构", "penalizes": "误差", "if_removed": "不学习重构"}],
        "evidence_ref": "paper-1:eq001"
    }'''
    mock = MockLLMClient(response=mock_response)

    bundle = await build_formula_cards_with_llm(doc, evidence, skeleton, llm_client=mock)

    assert len(bundle.formula_cards) == 1
    card = bundle.formula_cards[0]
    assert card.purpose == "定义总损失函数"
    assert card.intuition == "既要重构准确，又要保持图结构"
    assert card.numeric_example == "L_rec=2, L_graph=0.5, lambda=0.1, L=2+0.1*0.5=2.05"
    assert card.plain_summary == "平衡重构和结构约束"
    assert len(card.symbols) == 1
    assert card.symbols[0].meaning == "总损失"


@pytest.mark.asyncio
async def test_llm_enhanced_formula_card_rejects_hallucinated_refs() -> None:
    doc = _doc_with_formulas()
    evidence = build_evidence_index(doc)
    skeleton = build_paper_skeleton(doc, evidence)

    mock_response = '''{
        "purpose": "test",
        "intuition": "test",
        "numeric_example": "test",
        "what_if_removed": "test",
        "weight_sensitivity": "test",
        "plain_summary": "test",
        "symbols": [],
        "terms": [],
        "evidence_ref": "FAKE:ref"
    }'''
    mock = MockLLMClient(response=mock_response)

    bundle = await build_formula_cards_with_llm(doc, evidence, skeleton, llm_client=mock)
    card = bundle.formula_cards[0]

    # Hallucinated ref should be stripped
    assert card.evidence_ref != "FAKE:ref"


@pytest.mark.asyncio
async def test_llm_enhanced_formula_card_falls_back_on_failure() -> None:
    doc = _doc_with_formulas()
    evidence = build_evidence_index(doc)
    skeleton = build_paper_skeleton(doc, evidence)

    mock = MockLLMClient(response="not valid json")

    bundle = await build_formula_cards_with_llm(doc, evidence, skeleton, llm_client=mock)

    # Should fall back to rule-based
    assert len(bundle.formula_cards) == 1
    card = bundle.formula_cards[0]
    assert card.intuition == "NEEDS_HUMAN_CHECK"  # rule-based fallback


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


def test_formula_card_serializes_to_json() -> None:
    doc = _doc_with_formulas()
    evidence = build_evidence_index(doc)
    skeleton = build_paper_skeleton(doc, evidence)

    bundle = build_formula_cards(doc, evidence, skeleton)
    json_str = bundle.model_dump_json()

    assert "paper-1" in json_str
    assert "eq001" in json_str

    # Verify serialization works
    assert len(json_str) > 100
