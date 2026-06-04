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
