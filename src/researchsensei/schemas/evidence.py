from __future__ import annotations

from pydantic import Field, model_validator

from researchsensei.schemas.base import SenseiModel
from researchsensei.schemas.enums import EvidenceType


LOW_CONFIDENCE_EVIDENCE_TYPES = {
    EvidenceType.UNVERIFIED,
    EvidenceType.NEEDS_HUMAN_CHECK,
    EvidenceType.INSUFFICIENT_EVIDENCE,
}


class ClaimEvidence(SenseiModel):
    claim_id: str
    claim_text: str
    evidence_type: EvidenceType
    evidence_ref: str
    block_id: str
    section: str
    quote_or_summary: str
    confidence: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def uncertain_claims_stay_low_confidence(self) -> "ClaimEvidence":
        if self.evidence_type in LOW_CONFIDENCE_EVIDENCE_TYPES and self.confidence > 0.5:
            raise ValueError("Uncertain evidence types cannot use confidence above 0.5.")
        if self.evidence_ref and self.block_id and not self.evidence_ref.endswith(f":{self.block_id}"):
            raise ValueError("evidence_ref must end with the referenced block_id.")
        return self


class EvidenceIndex(SenseiModel):
    paper_id: str
    claims: list[ClaimEvidence] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
