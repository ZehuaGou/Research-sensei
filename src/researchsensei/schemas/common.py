from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import Field

from researchsensei.schemas.base import SenseiModel


class WarningItem(SenseiModel):
    code: str
    message: str
    detail: str = ""


class ErrorItem(SenseiModel):
    code: str
    message: str
    context: dict[str, Any] = Field(default_factory=dict)


class GeneratedMetadata(SenseiModel):
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    generator_version: str = "v0.6.0"


class StatusEnvelope(SenseiModel):
    status: str
    message: str = ""
    warnings: list[WarningItem] = Field(default_factory=list)
    errors: list[ErrorItem] = Field(default_factory=list)
    data: dict[str, Any] = Field(default_factory=dict)
