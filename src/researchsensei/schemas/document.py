from __future__ import annotations

from pydantic import Field

from researchsensei.schemas.base import SenseiModel
from researchsensei.schemas.common import WarningItem
from researchsensei.schemas.enums import BlockType


class DocumentBlock(SenseiModel):
    block_id: str
    type: BlockType
    text: str
    evidence_ref: str
    section: str = ""
    page: int | None = None
    normalized_text: str = ""
    offset_start: int = 0
    offset_end: int = 0
    raw_latex: str = ""


class DocumentIngestion(SenseiModel):
    paper_id: str
    detected_language: str = "unknown"
    source_path: str = ""
    parser_name: str = "lightweight"
    degraded: bool = False
    warnings: list[WarningItem] = Field(default_factory=list)
    blocks: list[DocumentBlock] = Field(default_factory=list)
