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
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
