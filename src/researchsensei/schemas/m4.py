from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import Field

from researchsensei.schemas.base import SenseiModel
from researchsensei.schemas.common import WarningItem


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SelectionExplanation(SenseiModel):
    status: str = "SUCCESS"
    answer: str = ""
    cited_evidence_refs: list[str] = Field(default_factory=list)
    cited_passage_ids: list[str] = Field(default_factory=list)
    relation_to_current_section: str = ""
    relation_to_paper_claim: str = ""
    confidence: float = 0.0
    used_memory_ids: list[str] = Field(default_factory=list)
    warnings: list[WarningItem] = Field(default_factory=list)


class FormulaSymbolExplanation(SenseiModel):
    status: str = "SUCCESS"
    formula_id: str = ""
    symbol: str = ""
    meaning: str = ""
    source_sentence: str = ""
    intuition: str = ""
    numeric_example: str = ""
    role_in_method: str = ""
    evidence_ref: str = ""
    formula_origin: str = ""
    formula_ocr_status: str = ""
    formula_explanation_status: str = ""
    confidence: float = 0.0
    warnings: list[WarningItem] = Field(default_factory=list)


class GroundedClaim(SenseiModel):
    """A user-facing M4 claim whose evidence binding was checked by the backend."""

    text: str
    evidence_refs: list[str] = Field(default_factory=list)
    claim_type: Literal["paper_claim", "explanation", "toy_example"] = "paper_claim"
    support_status: Literal["SUPPORTED", "ARTIFACT_DERIVED", "MEMORY_REPLAY"] = "SUPPORTED"
    uncertainty: str = ""


class M4ContextTrace(SenseiModel):
    """User-safe description of how M4 interpreted the current turn."""

    scope: Literal["paper", "selection"] = "paper"
    continued_from_history: bool = False
    focus_question: str = ""
    evidence_count: int = 0
    selected_text_used: bool = False


class InteractiveAnswer(SenseiModel):
    status: str = "SUCCESS"
    answer: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    claims: list[GroundedClaim] = Field(default_factory=list)
    memory_refs: list[str] = Field(default_factory=list)
    uncertainty: str = ""
    follow_up_suggestions: list[str] = Field(default_factory=list)
    used_context: dict[str, bool] = Field(default_factory=dict)
    context_trace: M4ContextTrace = Field(default_factory=M4ContextTrace)
    warnings: list[WarningItem] = Field(default_factory=list)


class AdvisorQuestion(SenseiModel):
    status: str = "SUCCESS"
    question: str = ""
    user_question: str = ""
    target_concept: str = ""
    difficulty: str = "medium"
    expected_answer_points: list[str] = Field(default_factory=list)
    why_it_matters: str = ""
    answer_format: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    question_type: str = "method"
    follow_up_policy: str = "deeper"
    warnings: list[WarningItem] = Field(default_factory=list)


class AdvisorEvaluation(SenseiModel):
    status: str = "SUCCESS"
    score: float = 0.0
    covered_points: list[str] = Field(default_factory=list)
    missing_points: list[str] = Field(default_factory=list)
    misconceptions: list[str] = Field(default_factory=list)
    improvement_steps: list[str] = Field(default_factory=list)
    next_question: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    feedback: str = ""
    warnings: list[WarningItem] = Field(default_factory=list)


class M4MemoryRecord(SenseiModel):
    memory_id: str
    job_id: str
    memory_type: str
    text: str = ""
    question: str = ""
    answer: str = ""
    source_artifact: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    created_at: str = Field(default_factory=_now)
    updated_at: str = Field(default_factory=_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class M4MemoryBundle(SenseiModel):
    schema_version: Literal["m4_memory.v2"] = "m4_memory.v2"
    job_id: str
    records: list[M4MemoryRecord] = Field(default_factory=list)
    migrated_from: str = ""
    warnings: list[WarningItem] = Field(default_factory=list)


class MemoryRetrievalResult(SenseiModel):
    matched_memory_ids: list[str] = Field(default_factory=list)
    matched_artifacts: list[str] = Field(default_factory=list)
    should_call_llm: bool = True
    reason: str = ""
    estimated_token_saved: int = 0
    confidence: float = 0.0
    warnings: list[WarningItem] = Field(default_factory=list)
