from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from researchsensei.schemas.base import SenseiModel


RoleGuess = Literal[
    "loss function",
    "attention computation",
    "reconstruction objective",
    "anomaly score",
    "contrastive objective",
    "regularization",
    "definition",
    "metric",
    "bound/derivation",
    "unknown",
]


class M2SourceTrace(SenseiModel):
    formula_id: str = ""
    block_id: str = ""
    source_artifacts: list[str] = Field(default_factory=list)
    immutable_fields: dict[str, Any] = Field(default_factory=dict)
    nearby_block_ids: list[str] = Field(default_factory=list)
    canonical_comment_present: bool = False


class M2FormulaUnderstanding(SenseiModel):
    formula_id: str
    equation_group_id: str = ""
    equation_number: int | None = None
    page: int
    section: str = ""
    final_latex: str = ""
    nearby_text_used: str = "unknown"
    group_context_used: str = "standalone"
    role_guess: RoleGuess = "unknown"
    plain_language_explanation: str = "unknown"
    upstream_downstream_context: str = "unknown"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    risk_flags: list[str] = Field(default_factory=list)
    source_trace: M2SourceTrace


class M2FormulaUnderstandingBundle(SenseiModel):
    paper_id: str
    title: str = ""
    formulas: list[M2FormulaUnderstanding] = Field(default_factory=list)
    skipped_formula_count: int = 0
    used_group_info: bool = False


class M2RunResult(SenseiModel):
    paper_understanding_markdown: str
    formula_understanding: M2FormulaUnderstandingBundle
    method_graph: dict[str, Any]
    source_trace: dict[str, Any]
    risk_report_markdown: str
    run_summary: dict[str, Any]
