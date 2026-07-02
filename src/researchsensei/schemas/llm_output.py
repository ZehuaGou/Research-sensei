from __future__ import annotations

from pydantic import Field, model_validator

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

    @model_validator(mode="before")
    @classmethod
    def coerce_summary_object(cls, data):
        if isinstance(data, dict) and isinstance(data.get("one_sentence_summary"), dict):
            summary = data["one_sentence_summary"]
            data = {**data, "one_sentence_summary": str(summary.get("text") or "")}
        return data


class FormulaCardLLMOutput(SenseiModel):
    formula_id: str = ""
    formula_raw: str = ""
    formula_origin: str = ""
    formula_ocr_status: str = ""
    formula_explanation_status: str = ""
    purpose: str
    symbols: list[dict] = Field(default_factory=list)
    terms: list[dict] = Field(default_factory=list)
    intuition: str = ""
    numeric_example: str = ""
    what_if_removed: str = ""
    weight_sensitivity: str = ""
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
