from __future__ import annotations

import pytest
from pydantic import ValidationError

from researchsensei.schemas import (
    EvidenceType,
    FormulaCard,
    FormulaCardBundle,
    FormulaSymbol,
    FormulaTerm,
)


def test_formula_card_serializes_and_deserializes() -> None:
    card = FormulaCard(
        formula_id="paper-1:eq:eq001",
        paper_id="paper-1",
        formula_raw="L = L_rec + lambda L_graph",
        location="method",
        purpose="定义优化目标",
        symbols=[FormulaSymbol(symbol="L", meaning="总损失", evidence_status=EvidenceType.SUPPORTED_BY_FORMULA, confidence=0.6)],
        terms=[FormulaTerm(term="L_rec", meaning="重构损失", encourages="准确重构", penalizes="重构误差", if_removed="不学习重构")],
        evidence_ref="paper-1:eq001",
        evidence_status=EvidenceType.SUPPORTED_BY_FORMULA,
        confidence=0.6,
    )

    restored = FormulaCard.model_validate_json(card.model_dump_json())

    assert restored.formula_id == "paper-1:eq:eq001"
    assert restored.formula_raw == "L = L_rec + lambda L_graph"
    assert len(restored.symbols) == 1
    assert restored.symbols[0].symbol == "L"
    assert len(restored.terms) == 1
    assert restored.terms[0].term == "L_rec"
    assert restored.evidence_ref == "paper-1:eq001"


def test_formula_card_allows_conservative_defaults() -> None:
    card = FormulaCard(formula_id="f1", paper_id="p1")

    assert card.formula_raw == ""
    assert card.purpose == "UNKNOWN"
    assert card.intuition == "UNKNOWN"
    assert card.numeric_example == "UNKNOWN"
    assert card.evidence_status == EvidenceType.UNVERIFIED
    assert card.confidence == 0.0


def test_formula_card_rejects_confidence_out_of_range() -> None:
    with pytest.raises(ValidationError):
        FormulaCard(formula_id="f1", paper_id="p1", confidence=2.0)


def test_formula_symbol_defaults() -> None:
    sym = FormulaSymbol(symbol="x")
    assert sym.meaning == "UNKNOWN"
    assert sym.evidence_status == EvidenceType.UNVERIFIED
    assert sym.confidence == 0.0


def test_formula_term_defaults() -> None:
    term = FormulaTerm(term="L_rec")
    assert term.meaning == "UNKNOWN"
    assert term.encourages == "UNKNOWN"
    assert term.penalizes == "UNKNOWN"
    assert term.if_removed == "UNKNOWN"
    assert term.evidence_status == EvidenceType.UNVERIFIED


def test_formula_card_bundle_serializes() -> None:
    bundle = FormulaCardBundle(
        paper_id="paper-1",
        formula_cards=[
            FormulaCard(formula_id="f1", paper_id="paper-1", formula_raw="x + y"),
        ],
        evidence_refs=["paper-1:eq001"],
        confidence=0.5,
        warnings=[],
        evidence_status=EvidenceType.SUPPORTED_BY_FORMULA,
    )

    restored = FormulaCardBundle.model_validate_json(bundle.model_dump_json())

    assert restored.paper_id == "paper-1"
    assert len(restored.formula_cards) == 1
    assert restored.evidence_refs == ["paper-1:eq001"]


def test_formula_card_bundle_empty_with_warning() -> None:
    bundle = FormulaCardBundle(
        paper_id="paper-1",
        formula_cards=[],
        warnings=["FORMULA_UNAVAILABLE"],
        evidence_status=EvidenceType.INSUFFICIENT_EVIDENCE,
    )

    assert len(bundle.formula_cards) == 0
    assert "FORMULA_UNAVAILABLE" in bundle.warnings
