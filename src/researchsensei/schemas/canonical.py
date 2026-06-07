"""Schema for canonical_paper.md — M1's normalized output for M2."""
from __future__ import annotations

from datetime import datetime, timezone

from pydantic import Field

from researchsensei.schemas.base import SenseiModel
from researchsensei.schemas.enums import (
    AdapterStatus,
    CanonicalizationStatus,
    FormulaOcrStatus,
    FormulaOrigin,
    SourcePriority,
)


class FormulaBlock(SenseiModel):
    """A formula block in canonical_paper.md."""

    formula_id: str
    latex: str = ""  # LaTeX formula (only for source_latex/parser_latex/ocr_latex)
    raw_formula_text: str = ""  # Raw text for raw_formula_text origin
    is_latex: bool = False  # True if latex field contains valid LaTeX
    confidence: float = 0.0  # 0-1 confidence score
    origin: FormulaOrigin = FormulaOrigin.UNKNOWN
    section: str = ""
    page: int | None = None
    bbox: list[float] = Field(default_factory=list)  # [x1, y1, x2, y2]
    ocr_status: FormulaOcrStatus = FormulaOcrStatus.NOT_TRIGGERED
    ocr_confidence: float = 0.0
    detector_confidence: float = 0.0
    warnings: list[str] = Field(default_factory=list)


class FormulaRegionResult(SenseiModel):
    """Result of FormulaRegionDetector for one formula region."""

    formula_id: str
    formula_bbox: list[float] = Field(default_factory=list)
    formula_page: int | None = None
    section: str = ""
    detector_confidence: float = 0.0
    formula_region_status: str = "not_detected"  # detected | not_detected | unavailable
    warnings: list[str] = Field(default_factory=list)


class FormulaOcrResult(SenseiModel):
    """Result of FormulaOCRAdapter for one formula region."""

    formula_id: str
    formula_latex: str = ""
    formula_origin: FormulaOrigin = FormulaOrigin.OCR_LATEX
    formula_ocr_status: FormulaOcrStatus = FormulaOcrStatus.NOT_TRIGGERED
    ocr_confidence: float = 0.0
    blocking_reason: str = ""
    warnings: list[str] = Field(default_factory=list)


class CanonicalPaperFrontMatter(SenseiModel):
    """YAML front matter for canonical_paper.md."""

    paper_id: str = ""
    title: str = ""
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    venue: str = ""
    source_type: str = ""  # latex_source | structured_html | pdf | metadata_only
    source_confidence: str = ""  # high | medium | low
    canonicalization_status: CanonicalizationStatus = CanonicalizationStatus.NOT_ATTEMPTED
    parser_used: str = ""
    m2_ready: bool = False
    degradation_reason: str = ""
    # Parser quality selection fields
    parser_candidates: list[str] = Field(default_factory=list)  # List of parser names evaluated
    selected_parser: str = ""  # The parser that was selected
    parser_quality_score: float = 0.0  # Quality score of selected parser (0-100)
    parser_selection_reason: str = ""  # Why this parser was selected


class CanonicalPaper(SenseiModel):
    """M1 normalized output: canonical_paper.md content."""

    front_matter: CanonicalPaperFrontMatter = Field(default_factory=CanonicalPaperFrontMatter)
    sections: dict[str, str] = Field(default_factory=dict)  # section_name -> content
    formula_blocks: list[FormulaBlock] = Field(default_factory=list)
    raw_markdown: str = ""
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AdapterInfo(SenseiModel):
    """Status of an external adapter."""

    name: str
    status: AdapterStatus = AdapterStatus.NOT_IMPLEMENTED
    blocking_reason: str = ""
    attempt_details: list[str] = Field(default_factory=list)


class CanonicalizationResult(SenseiModel):
    """Result of material normalization for one paper."""

    paper_id: str
    title: str
    source_type: str = ""
    source_priority: SourcePriority = SourcePriority.METADATA_ONLY
    preferred_m2_input: str = ""
    has_valid_deep_reading_source: bool = False
    canonical_paper: CanonicalPaper | None = None
    canonical_paper_path: str = ""
    canonicalization_status: CanonicalizationStatus = CanonicalizationStatus.NOT_ATTEMPTED
    m2_ready: bool = False
    degradation_reason: str = ""
    formula_blocks: list[FormulaBlock] = Field(default_factory=list)
    formula_region_results: list[FormulaRegionResult] = Field(default_factory=list)
    formula_ocr_results: list[FormulaOcrResult] = Field(default_factory=list)
    adapter_info: list[AdapterInfo] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
