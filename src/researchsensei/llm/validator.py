from __future__ import annotations

from researchsensei.schemas.evidence import EvidencePack
from researchsensei.schemas.llm_output import (
    FormulaCardsLLMOutput,
    PaperCardLLMOutput,
    TeachingCardsLLMOutput,
)


def evidence_refs_from_pack(evidence_pack: EvidencePack) -> set[str]:
    """Extract all valid evidence_refs from an EvidencePack."""
    return {item.evidence_ref for item in evidence_pack.items if item.evidence_ref}


def validate_paper_card_llm_output(
    output: PaperCardLLMOutput,
    evidence_pack: EvidencePack,
) -> None:
    """Validate PaperCardLLMOutput against EvidencePack.

    Raises ValueError if:
    - EvidencePack is empty
    - core fields have invalid evidence_ref
    """
    if not evidence_pack.items:
        raise ValueError("EvidencePack is empty, cannot validate PaperCardLLMOutput")

    valid_refs = evidence_refs_from_pack(evidence_pack)

    _check_claim_ref("problem", output.problem, valid_refs)
    _check_claim_ref("core_idea", output.core_idea, valid_refs)
    _check_claim_ref("method_overview", output.method_overview, valid_refs)
    _check_claim_ref("experiment_summary", output.experiment_summary, valid_refs)

    if output.limitations is not None and output.limitations.evidence_ref:
        _check_claim_ref("limitations", output.limitations, valid_refs)


def validate_formula_cards_llm_output(
    output: FormulaCardsLLMOutput,
    evidence_pack: EvidencePack,
) -> None:
    """Validate FormulaCardsLLMOutput against EvidencePack.

    Raises ValueError if:
    - EvidencePack is empty
    - formula card has evidence_ref but it's invalid
    - formula card has no evidence_ref when cards exist
    """
    if not evidence_pack.items:
        raise ValueError("EvidencePack is empty, cannot validate FormulaCardsLLMOutput")

    valid_refs = evidence_refs_from_pack(evidence_pack)

    for i, card in enumerate(output.formula_cards):
        if card.evidence_ref:
            if card.evidence_ref not in valid_refs:
                raise ValueError(
                    f"FormulaCard[{i}].evidence_ref '{card.evidence_ref}' not in EvidencePack"
                )
        else:
            raise ValueError(
                f"FormulaCard[{i}] has no evidence_ref"
            )


def validate_teaching_cards_llm_output(
    output: TeachingCardsLLMOutput,
    evidence_pack: EvidencePack,
) -> None:
    """Validate TeachingCardsLLMOutput against EvidencePack.

    Raises ValueError if:
    - EvidencePack is empty
    - human_explanation has no evidence_ref
    - evidence_ref is invalid
    """
    if not evidence_pack.items:
        raise ValueError("EvidencePack is empty, cannot validate TeachingCardsLLMOutput")

    valid_refs = evidence_refs_from_pack(evidence_pack)

    for i, card in enumerate(output.teaching_cards):
        if not card.evidence_ref:
            raise ValueError(
                f"TeachingCard[{i}].evidence_ref is required for human_explanation"
            )
        if card.evidence_ref not in valid_refs:
            raise ValueError(
                f"TeachingCard[{i}].evidence_ref '{card.evidence_ref}' not in EvidencePack"
            )


def _check_claim_ref(
    field_name: str,
    claim: object,
    valid_refs: set[str],
) -> None:
    """Check that a claim has a valid evidence_ref."""
    ref = getattr(claim, "evidence_ref", "")
    if not ref:
        raise ValueError(f"{field_name}.evidence_ref is required")
    if ref not in valid_refs:
        raise ValueError(f"{field_name}.evidence_ref '{ref}' not in EvidencePack")
