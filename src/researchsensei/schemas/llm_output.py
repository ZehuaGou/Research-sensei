from __future__ import annotations

from pydantic import Field

from researchsensei.schemas.base import SenseiModel


class ClaimLLMOutput(SenseiModel):
    text: str
    evidence_ref: str = ""


class PaperCardLLMOutput(SenseiModel):
    one_sentence_summary: str
    problem: ClaimLLMOutput
    core_idea: ClaimLLMOutput
    method_overview: ClaimLLMOutput
    experiment_summary: ClaimLLMOutput
    limitations: ClaimLLMOutput | None = None


class FormulaCardLLMOutput(SenseiModel):
    formula_id: str = ""
    formula_raw: str = ""
    purpose: str
    intuition: str = ""
    numeric_example: str = ""
    plain_summary: str = ""
    evidence_ref: str = ""


class FormulaCardsLLMOutput(SenseiModel):
    formula_cards: list[FormulaCardLLMOutput] = Field(default_factory=list)


class TeachingCardLLMOutput(SenseiModel):
    card_id: str = ""
    target_type: str = "concept"
    target_id: str = ""
    title: str = ""
    human_explanation: str
    analogy_explanation: str = ""
    minimal_formula_explanation: str = ""
    numeric_example: str = ""
    paper_role_explanation: str = ""
    evidence_ref: str = ""


class TeachingCardsLLMOutput(SenseiModel):
    teaching_cards: list[TeachingCardLLMOutput] = Field(default_factory=list)
