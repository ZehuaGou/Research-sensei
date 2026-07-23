from __future__ import annotations

from pydantic import AliasChoices, Field, model_validator

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
    formula_ids: list[str] = Field(default_factory=list)
    formula_origins: list[str] = Field(default_factory=list)
    formula_pages: list[int] = Field(default_factory=list)
    formula_ocr_statuses: list[str] = Field(default_factory=list)
    block_sources: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)


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
    schema_version: str = "passage_index"
    paper_id: str
    passages: list[Passage] = Field(default_factory=list)
    warnings: list[WarningItem] = Field(default_factory=list)
    build_config: PassageIndexBuildConfig = Field(default_factory=PassageIndexBuildConfig)
    stats: PassageIndexStats | None = None


class ClaimEvidenceRecord(SenseiModel):
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
    formula_origin: str = ""
    formula_id: str = ""
    formula_page: int | None = None
    formula_bbox: tuple[float, float, float, float] | None = None
    formula_ocr_status: str = ""
    equation_number: str = ""
    equation_group_id: str = ""
    group_order: int = 0
    group_crop_path: str = ""
    group_overlay_path: str = ""
    source_artifact_path: str = Field(
        default="parsed_document.json",
        validation_alias=AliasChoices("source_artifact_path", "canonical_source_path"),
    )
    source_location: dict = Field(default_factory=dict)
    block_source: str = ""
    section_confidence: str = ""
    risk_flags: list[str] = Field(default_factory=list)
    parse_quality_status: str = ""
    fallback_used: bool = False
    llama_refined: bool = False


class ClaimEvidenceBundle(SenseiModel):
    schema_version: str = "claim_evidence"
    paper_id: str
    claims: list[ClaimEvidenceRecord] = Field(default_factory=list)
    warnings: list[WarningItem] = Field(default_factory=list)
    source_artifacts: list[str] = Field(default_factory=list)


class EvidenceRetrievalResult(SenseiModel):
    passage_id: str
    score: float
    matched_terms: list[str] = Field(default_factory=list)
    evidence_ref: str = ""


class EvidencePackItem(SenseiModel):
    claim_id: str
    claim_type: str
    evidence_ref: str
    passage_id: str = ""
    quote_or_summary: str = ""
    passage_text: str = ""
    confidence: float = Field(ge=0.0, le=1.0)
    retrieval_score: float = 0.0
    token_count: int = 0
    source_artifact: str = "claim_evidence"
    formula_origin: str = ""
    formula_id: str = ""
    formula_page: int | None = None
    formula_bbox: tuple[float, float, float, float] | None = None
    formula_ocr_status: str = ""
    equation_number: str = ""
    equation_group_id: str = ""
    group_order: int = 0
    group_crop_path: str = ""
    group_overlay_path: str = ""
    block_source: str = ""
    risk_flags: list[str] = Field(default_factory=list)


class EvidencePack(SenseiModel):
    paper_id: str
    items: list[EvidencePackItem] = Field(default_factory=list)
    warnings: list[WarningItem] = Field(default_factory=list)
    total_tokens: int = 0
