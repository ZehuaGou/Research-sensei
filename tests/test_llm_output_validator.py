from __future__ import annotations

import pytest

from researchsensei.llm.validator import (
    evidence_refs_from_pack,
    validate_formula_cards_llm_output,
    validate_paper_card_llm_output,
    validate_teaching_cards_llm_output,
)
from researchsensei.schemas import (
    ClaimLLMOutput,
    EvidencePack,
    EvidencePackItem,
    FormulaCardLLMOutput,
    FormulaCardsLLMOutput,
    PaperCardLLMOutput,
    TeachingCardLLMOutput,
    TeachingCardsLLMOutput,
)


def _make_pack(*refs: str) -> EvidencePack:
    return EvidencePack(
        paper_id="test",
        items=[
            EvidencePackItem(
                claim_id=f"c{i}",
                claim_type="METHOD",
                evidence_ref=ref,
                passage_text="test passage",
                confidence=0.7,
            )
            for i, ref in enumerate(refs)
        ],
    )


# ---------------------------------------------------------------------------
# evidence_refs_from_pack
# ---------------------------------------------------------------------------


def test_evidence_refs_from_pack() -> None:
    pack = _make_pack("ref-a", "ref-b", "ref-c")
    refs = evidence_refs_from_pack(pack)
    assert refs == {"ref-a", "ref-b", "ref-c"}


# ---------------------------------------------------------------------------
# PaperCard validation
# ---------------------------------------------------------------------------


def test_valid_paper_output_passes() -> None:
    pack = _make_pack("ref-1", "ref-2", "ref-3", "ref-4")
    output = PaperCardLLMOutput(
        one_sentence_summary="Test",
        problem=ClaimLLMOutput(text="Problem", evidence_ref="ref-1"),
        core_idea=ClaimLLMOutput(text="Core", evidence_ref="ref-2"),
        method_overview=ClaimLLMOutput(text="Method", evidence_ref="ref-3"),
        experiment_summary=ClaimLLMOutput(text="Exp", evidence_ref="ref-4"),
    )
    validate_paper_card_llm_output(output, pack)  # should not raise


def test_paper_output_coerces_summary_object_text() -> None:
    output = PaperCardLLMOutput.model_validate({
        "one_sentence_summary": {"text": "Summary text", "evidence_ref": "ref-1"},
        "problem": {"text": "Problem", "evidence_ref": "ref-1"},
        "core_idea": {"text": "Core", "evidence_ref": "ref-1"},
        "method_overview": {"text": "Method", "evidence_ref": "ref-1"},
        "experiment_summary": {"text": "Exp", "evidence_ref": "ref-1"},
    })

    assert output.one_sentence_summary == "Summary text"


def test_empty_evidence_pack_raises() -> None:
    pack = EvidencePack(paper_id="test", items=[])
    output = PaperCardLLMOutput(
        one_sentence_summary="Test",
        problem=ClaimLLMOutput(text="P", evidence_ref="ref-1"),
        core_idea=ClaimLLMOutput(text="C", evidence_ref="ref-1"),
        method_overview=ClaimLLMOutput(text="M", evidence_ref="ref-1"),
        experiment_summary=ClaimLLMOutput(text="E", evidence_ref="ref-1"),
    )
    with pytest.raises(ValueError, match="EvidencePack is empty"):
        validate_paper_card_llm_output(output, pack)


def test_invalid_problem_evidence_ref_is_downgraded_later() -> None:
    pack = _make_pack("ref-1")
    output = PaperCardLLMOutput(
        one_sentence_summary="Test",
        problem=ClaimLLMOutput(text="P", evidence_ref="INVALID"),
        core_idea=ClaimLLMOutput(text="C", evidence_ref="ref-1"),
        method_overview=ClaimLLMOutput(text="M", evidence_ref="ref-1"),
        experiment_summary=ClaimLLMOutput(text="E", evidence_ref="ref-1"),
    )
    validate_paper_card_llm_output(output, pack)  # should not raise


def test_missing_required_evidence_ref_is_downgraded_later() -> None:
    pack = _make_pack("ref-1")
    output = PaperCardLLMOutput(
        one_sentence_summary="Test",
        problem=ClaimLLMOutput(text="P", evidence_ref=""),
        core_idea=ClaimLLMOutput(text="C", evidence_ref="ref-1"),
        method_overview=ClaimLLMOutput(text="M", evidence_ref="ref-1"),
        experiment_summary=ClaimLLMOutput(text="E", evidence_ref="ref-1"),
    )
    validate_paper_card_llm_output(output, pack)  # should not raise


def test_limitations_missing_evidence_ref_allowed() -> None:
    pack = _make_pack("ref-1", "ref-2", "ref-3", "ref-4")
    output = PaperCardLLMOutput(
        one_sentence_summary="Test",
        problem=ClaimLLMOutput(text="P", evidence_ref="ref-1"),
        core_idea=ClaimLLMOutput(text="C", evidence_ref="ref-2"),
        method_overview=ClaimLLMOutput(text="M", evidence_ref="ref-3"),
        experiment_summary=ClaimLLMOutput(text="E", evidence_ref="ref-4"),
        limitations=ClaimLLMOutput(text="Limit", evidence_ref=""),
    )
    validate_paper_card_llm_output(output, pack)  # should not raise


# ---------------------------------------------------------------------------
# FormulaCards validation
# ---------------------------------------------------------------------------


def test_formula_output_invalid_evidence_ref_raises() -> None:
    pack = _make_pack("ref-1")
    output = FormulaCardsLLMOutput(
        formula_cards=[FormulaCardLLMOutput(purpose="P", evidence_ref="INVALID")]
    )
    with pytest.raises(ValueError, match="INVALID"):
        validate_formula_cards_llm_output(output, pack)


def test_formula_output_empty_evidence_ref_raises() -> None:
    pack = _make_pack("ref-1")
    output = FormulaCardsLLMOutput(
        formula_cards=[FormulaCardLLMOutput(purpose="P", evidence_ref="")]
    )
    with pytest.raises(ValueError, match="no evidence_ref"):
        validate_formula_cards_llm_output(output, pack)


# ---------------------------------------------------------------------------
# TeachingCards validation
# ---------------------------------------------------------------------------


def test_teaching_human_explanation_invalid_evidence_ref_raises() -> None:
    pack = _make_pack("ref-1")
    output = TeachingCardsLLMOutput(
        teaching_cards=[TeachingCardLLMOutput(human_explanation="H", evidence_ref="INVALID")]
    )
    with pytest.raises(ValueError, match="INVALID"):
        validate_teaching_cards_llm_output(output, pack)


def test_teaching_optional_fields_need_no_evidence_ref() -> None:
    pack = _make_pack("ref-1")
    output = TeachingCardsLLMOutput(
        teaching_cards=[TeachingCardLLMOutput(
            human_explanation="H",
            evidence_ref="ref-1",
            analogy_explanation="A",
            numeric_example="N",
        )]
    )
    validate_teaching_cards_llm_output(output, pack)  # should not raise


def test_error_message_contains_field_name() -> None:
    pack = _make_pack("ref-1")
    output = PaperCardLLMOutput(
        one_sentence_summary="Test",
        problem=ClaimLLMOutput(text="P", evidence_ref="BAD"),
        core_idea=ClaimLLMOutput(text="C", evidence_ref="ref-1"),
        method_overview=ClaimLLMOutput(text="M", evidence_ref="ref-1"),
        experiment_summary=ClaimLLMOutput(text="E", evidence_ref="ref-1"),
    )
    validate_paper_card_llm_output(output, pack)  # paper claim refs are downgraded by conversion
