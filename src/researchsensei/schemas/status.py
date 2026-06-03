from __future__ import annotations

from pydantic import Field

from researchsensei.schemas.base import SenseiModel
from researchsensei.schemas.common import WarningItem


class EvidencePackSummary(SenseiModel):
    included_claim_ids: list[str] = Field(default_factory=list)
    excluded_claim_ids: list[str] = Field(default_factory=list)
    total_tokens: int = 0
    claim_type_counts: dict[str, int] = Field(default_factory=dict)
    truncated_passage_ids: list[str] = Field(default_factory=list)


class DownstreamGates(SenseiModel):
    reading_display: bool = False
    phase12_patterns: bool = False
    phase12_drill: bool = False
    phase12_drill_degraded: bool = False
    advisor_questions: bool = False


class UnderstandingStatus(SenseiModel):
    schema_version: str = "v1"
    paper_id: str
    status: str  # SUCCESS / DEGRADED_STRUCTURAL / BASELINE_ONLY / BLOCKED_UNDERSTANDING / FAILED
    blocking_reason: str = ""
    warnings: list[WarningItem] = Field(default_factory=list)
    allowed_for_user_display: bool = False
    allowed_downstream: DownstreamGates = Field(default_factory=DownstreamGates)
    component_status: dict[str, str] = Field(default_factory=dict)
    checked_artifacts: list[str] = Field(default_factory=list)
    evidence_pack_summary: EvidencePackSummary | None = None
