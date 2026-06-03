from __future__ import annotations

import pytest
from pydantic import ValidationError

from researchsensei.schemas import CardClaim, EvidenceType, PaperCard


def test_paper_card_serializes_and_deserializes() -> None:
    card = PaperCard(
        paper_id="paper-1",
        title="Tiny TSAD Paper",
        one_sentence_summary="We study anomaly detection.",
        problem=CardClaim(
            text="Current methods miss dependencies.",
            evidence_ref="paper-1:b002",
            evidence_type=EvidenceType.SUPPORTED_BY_TEXT,
            confidence=0.6,
        ),
        confidence=0.4,
        evidence_status=EvidenceType.SUPPORTED_BY_TEXT,
    )

    restored = PaperCard.model_validate_json(card.model_dump_json())

    assert restored.paper_id == "paper-1"
    assert restored.title == "Tiny TSAD Paper"
    assert restored.problem.text == "Current methods miss dependencies."
    assert restored.problem.evidence_ref == "paper-1:b002"
    assert restored.problem.evidence_type == EvidenceType.SUPPORTED_BY_TEXT
    assert restored.confidence == 0.4


def test_paper_card_allows_conservative_unknown_fields() -> None:
    card = PaperCard(paper_id="paper-1")

    assert card.title == "UNKNOWN"
    assert card.one_sentence_summary == "UNKNOWN"
    assert card.problem.text == "UNKNOWN"
    assert card.problem.evidence_type == EvidenceType.UNVERIFIED
    assert card.confidence == 0.0
    assert card.evidence_status == EvidenceType.UNVERIFIED


def test_paper_card_rejects_confidence_outside_zero_to_one() -> None:
    with pytest.raises(ValidationError):
        PaperCard(paper_id="paper-1", confidence=2.0)

    with pytest.raises(ValidationError):
        PaperCard(paper_id="paper-1", confidence=-0.1)


def test_card_claim_rejects_confidence_outside_zero_to_one() -> None:
    with pytest.raises(ValidationError):
        CardClaim(text="test", confidence=1.5)

    with pytest.raises(ValidationError):
        CardClaim(text="test", confidence=-0.1)


def test_paper_card_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        PaperCard(paper_id="paper-1", extra_field="not allowed")


def test_paper_card_with_all_fields() -> None:
    card = PaperCard(
        paper_id="paper-1",
        title="Test Paper",
        one_sentence_summary="A test.",
        problem=CardClaim(text="Problem", evidence_ref="p:b1", evidence_type=EvidenceType.SUPPORTED_BY_TEXT, confidence=0.7),
        background=CardClaim(text="Background", evidence_ref="p:b2", evidence_type=EvidenceType.SUPPORTED_BY_TEXT, confidence=0.6),
        old_methods=[CardClaim(text="Old method", evidence_ref="p:b3", evidence_type=EvidenceType.SUPPORTED_BY_TEXT, confidence=0.5)],
        bottleneck=CardClaim(text="Bottleneck", evidence_type=EvidenceType.INSUFFICIENT_EVIDENCE, confidence=0.1),
        core_idea=CardClaim(text="Core idea", evidence_ref="p:b4", evidence_type=EvidenceType.SUPPORTED_BY_FORMULA, confidence=0.7),
        method_overview=CardClaim(text="Method", evidence_ref="p:b5", evidence_type=EvidenceType.SUPPORTED_BY_TEXT, confidence=0.6),
        experiment_summary=CardClaim(text="Experiments", evidence_ref="p:b6", evidence_type=EvidenceType.SUPPORTED_BY_EXPERIMENT, confidence=0.65),
        limitations=CardClaim(text="Limitations", evidence_type=EvidenceType.NEEDS_HUMAN_CHECK, confidence=0.3),
        key_formulas=[CardClaim(text="L = L_rec", evidence_ref="p:eq1", evidence_type=EvidenceType.SUPPORTED_BY_FORMULA, confidence=0.7)],
        evidence_refs=["p:b1", "p:b2", "p:b3", "p:b4", "p:b5", "p:b6", "p:eq1"],
        confidence=0.5,
        warnings=["FORMULA_UNAVAILABLE"],
        evidence_status=EvidenceType.SUPPORTED_BY_TEXT,
    )

    restored = PaperCard.model_validate_json(card.model_dump_json())
    assert len(restored.old_methods) == 1
    assert len(restored.key_formulas) == 1
    assert len(restored.evidence_refs) == 7
    assert "FORMULA_UNAVAILABLE" in restored.warnings
