"""Schema for canonical_paper.md — M1's normalized output for M2."""
from __future__ import annotations

from datetime import datetime, timezone

from pydantic import Field

from researchsensei.schemas.base import SenseiModel
from researchsensei.schemas.enums import (
    AdapterStatus,
    CanonicalQualityStatus,
    CanonicalizationStatus,
    FormulaOcrStatus,
    FormulaOrigin,
    SourcePriority,
)


class FormulaSlot(SenseiModel):
    """A detected formula with position, crop path, and resolution status.

    Produced by MarkerDocumentFormulaDetector, enriched by FormulaCropper,
    and merged into canonical_paper.md by FormulaMerger.
    """

    formula_id: str = ""  # e.g. "formula_001"
    page: int = 0  # 0-indexed page number
    bbox: list[float] = Field(default_factory=list)  # [min_x, min_y, max_x, max_y] in PDF points
    polygon: list[list[float]] = Field(default_factory=list)  # 4-corner coords (clockwise from top-left)
    block_type: str = ""  # "Equation" or "TextInlineMath"
    detection_source: str = "marker_document"  # "marker_document"
    detection_confidence: float = 0.0  # 0-1
    marker_text: str = ""  # raw text from Marker block
    marker_latex: str = ""  # LaTeX extracted from Marker block (if available)
    nearby_text_before: str = ""  # text before formula in reading order
    nearby_text_after: str = ""  # text after formula in reading order
    section: str = ""  # inferred section name (trusted only: Abstract, Introduction, etc.)
    section_confidence: str = "low"  # "high" | "medium" | "low"
    section_source: str = "unknown"  # "heading_above" | "page_context" | "unknown"
    section_reason: str = ""  # human-readable explanation
    slot_marker: str = ""  # Marker block ID
    crop_path: str = ""  # path to cropped formula image (relative to paper output dir)
    ocr_latex: str = ""  # OCR result (only when triggered)
    ocr_status: FormulaOcrStatus = FormulaOcrStatus.NOT_REQUIRED
    final_latex: str = ""  # resolved LaTeX (after priority merge)
    final_origin: FormulaOrigin = FormulaOrigin.UNRESOLVED
    unresolved_reason: str = ""  # reason if unresolved


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
    canonical_quality_status: CanonicalQualityStatus = CanonicalQualityStatus.FAIL
    parser_used: str = ""
    m2_ready: bool = False
    m2_ready_for_formula_understanding: bool = True
    degradation_reason: str = ""
    # Parser quality selection fields
    parser_candidates: list[str] = Field(default_factory=list)  # List of parser names evaluated
    selected_parser: str = ""  # The parser that was selected
    parser_quality_score: float = 0.0  # Quality score of selected parser (0-100)
    parser_selection_reason: str = ""  # Why this parser was selected
    # Detailed parser quality scores (stored as JSON string for serialization)
    parser_quality_details_json: str = ""  # JSON string of detailed scores
    # Body parser selection (three-pipeline architecture)
    body_selected_parser: str = ""  # Body pipeline selected parser
    body_parser_quality_score: float = 0.0  # Body parser quality score (0-100)
    body_parser_selection_reason: str = ""  # Why this body parser was selected
    # Formula pipeline metadata
    formula_detector: str = ""  # e.g. "marker_document"
    formula_selected_parser: str = ""  # Parser used for formula detection
    formula_slot_count: int = 0  # Total FormulaSlot entries detected
    formula_crop_count: int = 0  # Number of successfully cropped formulas
    parser_latex_count: int = 0  # Formulas with parser_latex origin
    ocr_latex_count: int = 0  # Formulas with ocr_latex origin
    raw_formula_text_count: int = 0  # Formulas with raw_formula_text origin
    unresolved_formula_count: int = 0  # Formulas with unresolved origin
    canonical_quality_status_formula: str = ""  # Formula quality status


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
    canonical_quality_status: CanonicalQualityStatus = CanonicalQualityStatus.FAIL
    m2_ready: bool = False
    m2_ready_for_formula_understanding: bool = True
    degradation_reason: str = ""
    formula_blocks: list[FormulaBlock] = Field(default_factory=list)
    formula_region_results: list[FormulaRegionResult] = Field(default_factory=list)
    formula_ocr_results: list[FormulaOcrResult] = Field(default_factory=list)
    adapter_info: list[AdapterInfo] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
