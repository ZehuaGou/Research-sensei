from __future__ import annotations

from datetime import datetime, timezone

from pydantic import Field

from researchsensei.schemas.base import SenseiModel
from researchsensei.schemas.common import WarningItem
from researchsensei.schemas.enums import JobStatus


class WorkspaceArtifact(SenseiModel):
    artifact_type: str
    path: str


class JobRecord(SenseiModel):
    job_id: str
    source_path: str
    run_dir: str
    status: JobStatus = JobStatus.PENDING
    current_step: str = "created"
    error: str = ""
    warnings: list[WarningItem] = Field(default_factory=list)
    artifacts: list[WorkspaceArtifact] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
