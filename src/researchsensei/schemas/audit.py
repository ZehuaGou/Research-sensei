from __future__ import annotations

from pydantic import Field

from researchsensei.schemas.base import SenseiModel


class AuditFinding(SenseiModel):
    code: str
    severity: str  # P0 / P1 / P2
    effect: str  # BLOCK / WARNING
    message: str
    artifact: str = ""
    field: str = ""


class ComponentAuditResult(SenseiModel):
    component: str
    status: str  # PASS / FAIL / SKIP
    findings: list[AuditFinding] = Field(default_factory=list)


class ArtifactBundle(SenseiModel):
    canonical_status: dict | None = None
    paper_card: dict | None = None
    formula_cards: dict | None = None
    teaching_cards: dict | None = None
    evidence_index: dict | None = None
    claim_evidence: dict | None = None
    passage_index: dict | None = None
    paper_skeleton: dict | None = None
    understanding_status: dict | None = None
    survey_status: dict | None = None
    survey_landscape: dict | None = None
    method_taxonomy: dict | None = None
    extracted_key_papers: dict | None = None
    survey_claims: dict | None = None


class QualityReport(SenseiModel):
    schema_version: str = "v1"
    paper_id: str
    findings: list[AuditFinding] = Field(default_factory=list)
    component_results: list[ComponentAuditResult] = Field(default_factory=list)
    checked_artifacts: list[str] = Field(default_factory=list)
    audit_version: str = "v1"
    created_at: str = ""
