from __future__ import annotations

from pydantic import Field, model_validator

from researchsensei.schemas.base import SenseiModel
from researchsensei.schemas.common import WarningItem
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


class Passage(SenseiModel):
    passage_id: str
    paper_id: str
    block_ids: list[str] = Field(default_factory=list)
    section: str = ""
    text: str = ""
    normalized_text: str = ""
    page_start: int | None = None
    page_end: int | None = None
    token_count: int = 0
    evidence_refs: list[str] = Field(default_factory=list)
    source_block_types: list[str] = Field(default_factory=list)


class PassageIndexBuildConfig(SenseiModel):
    min_passage_chars: int = 50
    max_passage_chars: int = 2000
    merge_same_section: bool = True
    formula_standalone: bool = True
    table_standalone: bool = True


class PassageIndexStats(SenseiModel):
    total_passages: int = 0
    total_blocks: int = 0
    skipped_short: int = 0
    split_long: int = 0
    sections_found: list[str] = Field(default_factory=list)


class PassageIndex(SenseiModel):
    schema_version: str = "v2"
    paper_id: str
    passages: list[Passage] = Field(default_factory=list)
    warnings: list[WarningItem] = Field(default_factory=list)
    build_config: PassageIndexBuildConfig = Field(default_factory=PassageIndexBuildConfig)
    stats: PassageIndexStats | None = None


class ClaimEvidenceV2(SenseiModel):
    claim_id: str
    claim_text: str
    evidence_ref: str
    block_id: str
    passage_id: str
    section: str = ""
    claim_type: str = ""
    semantic_support: str = ""
    source_sentence: str = ""
    quote_or_summary: str = ""
    confidence: float = Field(ge=0.0, le=1.0)
    generated_by: str = "rule"


class ClaimEvidenceBundle(SenseiModel):
    schema_version: str = "v2"
    paper_id: str
    claims: list[ClaimEvidenceV2] = Field(default_factory=list)
    warnings: list[WarningItem] = Field(default_factory=list)
    source_artifacts: list[str] = Field(default_factory=list)
