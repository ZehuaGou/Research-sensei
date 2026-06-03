from __future__ import annotations

import pytest
from pydantic import ValidationError

from researchsensei.schemas import EvidenceType, TeachingCard, TeachingCardBundle


def test_teaching_card_serializes_and_deserializes() -> None:
    card = TeachingCard(
        card_id="p1:teach:core_idea",
        paper_id="p1",
        target_type="concept",
        target_id="p1:b003",
        title="核心创新点",
        human_explanation="用重构误差来检测异常",
        analogy_explanation="像一个自动纠错的系统",
        minimal_formula_explanation="L = L_rec",
        numeric_example="输入5，输出4.8，误差0.2",
        paper_role_explanation="这是论文的核心方法",
        evidence_refs=["p1:b003"],
        evidence_status=EvidenceType.SUPPORTED_BY_TEXT,
        confidence=0.6,
    )

    restored = TeachingCard.model_validate_json(card.model_dump_json())

    assert restored.card_id == "p1:teach:core_idea"
    assert restored.human_explanation == "用重构误差来检测异常"
    assert restored.analogy_explanation == "像一个自动纠错的系统"
    assert len(restored.evidence_refs) == 1


def test_teaching_card_allows_conservative_defaults() -> None:
    card = TeachingCard(card_id="c1", paper_id="p1")

    assert card.title == "UNKNOWN"
    assert card.human_explanation == "UNKNOWN"
    assert card.analogy_explanation == "UNKNOWN"
    assert card.minimal_formula_explanation == "UNKNOWN"
    assert card.numeric_example == "UNKNOWN"
    assert card.paper_role_explanation == "UNKNOWN"
    assert card.evidence_status == EvidenceType.UNVERIFIED
    assert card.confidence == 0.0


def test_teaching_card_rejects_confidence_out_of_range() -> None:
    with pytest.raises(ValidationError):
        TeachingCard(card_id="c1", paper_id="p1", confidence=2.0)


def test_teaching_card_bundle_serializes() -> None:
    bundle = TeachingCardBundle(
        paper_id="p1",
        teaching_cards=[
            TeachingCard(card_id="c1", paper_id="p1", human_explanation="test"),
        ],
        evidence_refs=["p1:b001"],
        confidence=0.5,
        evidence_status=EvidenceType.SUPPORTED_BY_TEXT,
    )

    restored = TeachingCardBundle.model_validate_json(bundle.model_dump_json())

    assert restored.paper_id == "p1"
    assert len(restored.teaching_cards) == 1


def test_teaching_card_bundle_empty_with_warning() -> None:
    bundle = TeachingCardBundle(
        paper_id="p1",
        teaching_cards=[],
        warnings=["NO_TEACHABLE_CONTENT"],
        evidence_status=EvidenceType.INSUFFICIENT_EVIDENCE,
    )

    assert len(bundle.teaching_cards) == 0
    assert "NO_TEACHABLE_CONTENT" in bundle.warnings
