from __future__ import annotations

from datetime import datetime, timezone

from pydantic import Field

from researchsensei.schemas.base import SenseiModel


class SourceStatus(SenseiModel):
    source_type: str
    original_input: str
    resolved_path: str = ""
    status: str
    warnings: list[str] = Field(default_factory=list)
    degraded_flags: list[str] = Field(default_factory=list)
    content_type: str = ""
    size_bytes: int = 0
    source_url: str = ""
    pdf_url: str = ""
    source_dir: str = ""
    source_manifest_path: str = ""
    source_strategy: str = ""
    source_priority: str = ""
    preferred_m2_input: str = ""
    latex_source_available: bool = False
    latex_source_path: str = ""
    latex_main_file: str = ""
    fallback_used: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
