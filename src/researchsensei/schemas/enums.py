from __future__ import annotations

from enum import Enum


class SearchIntent(str, Enum):
    """Valid search intents for query planning."""

    GENERAL = "GENERAL"
    SURVEY = "SURVEY"
    FOUNDATIONAL = "FOUNDATIONAL"
    SOTA = "SOTA"
    BENCHMARK = "BENCHMARK"
    CODE = "CODE"


class PaperSourceStatus(str, Enum):
    RESOLVED = "RESOLVED"
    PARTIAL = "PARTIAL"
    NOT_FOUND = "NOT_FOUND"
    FAILED = "FAILED"
    UNSUPPORTED = "UNSUPPORTED"
    RESOLVED_PDF_DOWNLOADED = "RESOLVED_PDF_DOWNLOADED"
    RESOLVED_PDF_URL_ONLY = "RESOLVED_PDF_URL_ONLY"
    RESOLVED_LANDING_ONLY = "RESOLVED_LANDING_ONLY"
    METADATA_ONLY = "METADATA_ONLY"
    FAILED_DOWNLOAD = "FAILED_DOWNLOAD"
    NO_SOURCE_FOUND = "NO_SOURCE_FOUND"


class VerificationStatus(str, Enum):
    """M1.4 candidate verification status."""

    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    VERIFY_PENDING = "verify_pending"
    ERROR = "error"


class PaperSourceType(str, Enum):
    ARXIV_SOURCE = "ARXIV_SOURCE"
    PDF = "PDF"
    LANDING_PAGE = "LANDING_PAGE"
    METADATA_ONLY = "METADATA_ONLY"


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class BlockType(str, Enum):
    TITLE = "title"
    ABSTRACT = "abstract"
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    FORMULA = "formula"
    FIGURE = "figure"
    TABLE = "table"
    REFERENCE = "reference"


class EvidenceType(str, Enum):
    SUPPORTED_BY_TEXT = "SUPPORTED_BY_TEXT"
    SUPPORTED_BY_FORMULA = "SUPPORTED_BY_FORMULA"
    SUPPORTED_BY_EXPERIMENT = "SUPPORTED_BY_EXPERIMENT"
    REASONABLE_INFERENCE = "REASONABLE_INFERENCE"
    UNVERIFIED = "UNVERIFIED"
    NEEDS_HUMAN_CHECK = "NEEDS_HUMAN_CHECK"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


# --- Source-aware M1 enums ---

class SourcePriority(str, Enum):
    """Source priority for best available source resolution."""
    LATEX_SOURCE = "latex_source"
    STRUCTURED_HTML = "structured_html"
    PDF = "pdf"
    LOW_CONFIDENCE_TEXT = "low_confidence_text"
    METADATA_ONLY = "metadata_only"


class CanonicalizationStatus(str, Enum):
    """Status of material normalization to canonical_paper.md."""
    SUCCESS = "success"
    DEGRADED = "degraded"
    FAILED = "failed"
    NOT_ATTEMPTED = "not_attempted"


class CanonicalQualityStatus(str, Enum):
    """Quality gate status for whether canonical_paper.md may enter M2."""
    PASS = "PASS"
    DEGRADED = "DEGRADED"
    FAIL = "FAIL"


class FormulaOrigin(str, Enum):
    """Origin of formula content in canonical_paper.md."""
    SOURCE_LATEX = "source_latex"
    MINERU_LATEX = "mineru_latex"
    MARKER_LATEX = "marker_latex"
    PARSER_LATEX = "parser_latex"
    OCR_LATEX = "ocr_latex"
    RAW_FORMULA_TEXT = "raw_formula_text"
    UNRESOLVED = "unresolved"
    UNKNOWN = "unknown"


class FormulaOcrStatus(str, Enum):
    """Status of formula OCR attempt."""
    NOT_REQUIRED = "not_required"
    CROPPED = "cropped"
    OCR_PENDING = "ocr_pending"
    OCR_SUCCESS = "ocr_success"
    OCR_FAILED = "ocr_failed"
    SKIPPED_BY_POLICY = "skipped_by_policy"
    # Legacy aliases
    SUCCESS = "success"
    FAILED = "failed"
    UNAVAILABLE = "unavailable"
    NOT_TRIGGERED = "not_triggered"


class AdapterStatus(str, Enum):
    """Status of external adapter integration."""
    IMPLEMENTED = "IMPLEMENTED"
    DEGRADED_IMPLEMENTED = "DEGRADED_IMPLEMENTED"
    DEPENDENCY_AVAILABLE_NOT_WIRED = "DEPENDENCY_AVAILABLE_NOT_WIRED"
    BLOCKED = "BLOCKED"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"


# --- M1 venue-quality + fulltext source labels ---

class VenueRank(str, Enum):
    """A-conference / A-journal quality rank.

    `A_STAR` is reserved for CCF A + CORE A* top venues (NeurIPS, ICML, CVPR, ...).
    `A` is for CCF A / CORE A tier.
    `B` is for CCF B / CORE B.
    `C` is for CCF C / CORE C.
    `UNRANKED` for venues outside the rankings.
    """
    A_STAR = "A*"
    A = "A"
    B = "B"
    C = "C"
    UNRANKED = "unranked"


class FulltextSource(str, Enum):
    """Label of which path produced a paper's resolved full text.

    Used for audit and visualization; downstream code can branch on this to
    decide which download path produced a PDF.
    """
    ARXIV_SOURCE = "arxiv_source"
    ARXIV_PDF = "arxiv_pdf"
    UNPAYWALL_OA = "unpaywall_oa"
    OPENALEX_OA = "openalex_oa"
    S2_OA = "semantic_scholar_oa"
    LANDING_EXTRACTED = "landing_extracted"       # extracted PDF URL from OA venue landing HTML
    ARXIV_CROSSLINK = "arxiv_crosslink"           # arxiv_id reverse-found in OpenAlex/S2 metadata
    PDF_CACHE = "pdf_cache"                       # PDF cache hit; no new HTTP fetch
    METADATA_ONLY = "metadata_only"
