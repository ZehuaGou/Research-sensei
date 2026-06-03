from __future__ import annotations

from pydantic import Field

from researchsensei.schemas.base import SenseiModel


class PaperSkeleton(SenseiModel):
    paper_id: str
    title: str = "UNKNOWN"
    abstract_summary: str = "UNKNOWN"
    problem: str = "UNKNOWN"
    method_overview: str = "UNKNOWN"
    experiment_overview: str = "UNKNOWN"
    formulas: list[str] = Field(default_factory=list)
    limitations: str = "UNKNOWN"
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)
