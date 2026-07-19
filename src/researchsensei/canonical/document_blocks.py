"""M1 canonical document block schema.

This schema is intentionally separate from ``schemas.document.DocumentBlock``:
the latter is the downstream ingestion/evidence block.  M1 needs parser
provenance, page/bbox identity, source-specific latex, and section-risk fields
before canonical markdown is safe for M2.
"""
from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator

from researchsensei.schemas.base import SenseiModel


CanonicalBlockType = Literal[
    "title",
    "text",
    "formula",
    "table",
    "figure",
    "caption",
    "reference",
    "unknown",
]


class CanonicalDocumentBlock(SenseiModel):
    """Normalized parser block for M1 canonical pipeline."""

    block_id: str
    page: int = 1
    bbox: list[float] = Field(default_factory=list)
    block_type: CanonicalBlockType = "text"
    text: str = ""
    latex: str = ""
    html: str = ""
    reading_order: int = 0
    source: str = ""  # mineru25pro | marker_document | pymupdf | markitdown
    confidence: float = 0.0
    parent_section: str = ""
    raw_payload_ref: str = ""
    section: str = ""
    section_confidence: str = "low"
    section_reason: str = ""
    risk_flags: list[str] = Field(default_factory=list)

    @field_validator("page", mode="before")
    @classmethod
    def _normalize_page(cls, value: object) -> int:
        page = int(str(value or 1))
        return max(page, 1)

    @field_validator("bbox", mode="before")
    @classmethod
    def _normalize_bbox(cls, value: object) -> list[float]:
        if value in (None, ""):
            return []
        if not isinstance(value, (list, tuple)):
            return []
        values = [float(v) for v in value[:4]]
        return values if len(values) == 4 else []

    @field_validator("block_type", mode="before")
    @classmethod
    def _normalize_block_type(cls, value: object) -> str:
        raw = str(value or "text").lower()
        if raw in {"equation", "math", "formula", "inline_formula"} or "formula" in raw or "equation" in raw:
            return "formula"
        if "title" in raw or "heading" in raw:
            return "title"
        if "table" in raw:
            return "table"
        if "figure" in raw or "image" in raw:
            return "figure"
        if "caption" in raw:
            return "caption"
        if "reference" in raw or raw == "ref":
            return "reference"
        if "text" in raw or "paragraph" in raw:
            return "text"
        return "unknown"

    @field_validator(
        "text",
        "latex",
        "html",
        "source",
        "parent_section",
        "raw_payload_ref",
        "section",
        "section_confidence",
        "section_reason",
        mode="before",
    )
    @classmethod
    def _normalize_string(cls, value: object) -> str:
        if value is None:
            return ""
        return str(value)

    @property
    def content(self) -> str:
        return self.latex if self.block_type == "formula" and self.latex else self.text

    @property
    def identity_key(self) -> tuple[str, int, tuple[float, ...], str]:
        return (self.block_id, self.page, tuple(self.bbox), self.source)
