from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from backend.schemas import JobRecord, JobStatus, WorkspaceArtifact


class JobStore:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def create(self, job: JobRecord) -> JobRecord:
        with self._connect() as conn:
            conn.execute(
                """
                insert into jobs(job_id,status,filename,source_path,run_dir,current_step,error,warnings,artifacts,created_at,updated_at)
                values(?,?,?,?,?,?,?,?,?,?,?)
                """,
                self._to_row(job),
            )
        return job

    def get(self, job_id: str) -> JobRecord:
        with self._connect() as conn:
            row = conn.execute("select * from jobs where job_id = ?", (job_id,)).fetchone()
        if row is None:
            raise KeyError(job_id)
        return self._from_row(row)

    def list_recent(self, limit: int = 20) -> list[JobRecord]:
        with self._connect() as conn:
            rows = conn.execute("select * from jobs order by created_at desc limit ?", (limit,)).fetchall()
        return [self._from_row(row) for row in rows]

    def update(
        self,
        job_id: str,
        *,
        status: JobStatus | None = None,
        current_step: str | None = None,
        error: str | None = None,
        warnings: list[str] | None = None,
        artifacts: list[WorkspaceArtifact] | None = None,
    ) -> JobRecord:
        job = self.get(job_id)
        updated = job.model_copy(
            update={
                "status": status or job.status,
                "current_step": current_step if current_step is not None else job.current_step,
                "error": error if error is not None else job.error,
                "warnings": warnings if warnings is not None else job.warnings,
                "artifacts": artifacts if artifacts is not None else job.artifacts,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        with self._connect() as conn:
            conn.execute(
                """
                update jobs
                set status=?, filename=?, source_path=?, run_dir=?, current_step=?, error=?, warnings=?, artifacts=?, created_at=?, updated_at=?
                where job_id=?
                """,
                (
                    updated.status.value,
                    updated.filename,
                    updated.source_path,
                    updated.run_dir,
                    updated.current_step,
                    updated.error,
                    json.dumps(updated.warnings, ensure_ascii=False),
                    json.dumps([artifact.model_dump(mode="json") for artifact in updated.artifacts], ensure_ascii=False),
                    updated.created_at,
                    updated.updated_at,
                    updated.job_id,
                ),
            )
        return updated

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                create table if not exists jobs(
                    job_id text primary key,
                    status text not null,
                    filename text not null,
                    source_path text not null,
                    run_dir text not null,
                    current_step text not null,
                    error text not null,
                    warnings text not null,
                    artifacts text not null,
                    created_at text not null,
                    updated_at text not null
                )
                """
            )

    def _to_row(self, job: JobRecord) -> tuple:
        return (
            job.job_id,
            job.status.value,
            job.filename,
            job.source_path,
            job.run_dir,
            job.current_step,
            job.error,
            json.dumps(job.warnings, ensure_ascii=False),
            json.dumps([artifact.model_dump(mode="json") for artifact in job.artifacts], ensure_ascii=False),
            job.created_at,
            job.updated_at,
        )

    def _from_row(self, row: sqlite3.Row) -> JobRecord:
        return JobRecord(
            job_id=row["job_id"],
            status=JobStatus(row["status"]),
            filename=row["filename"],
            source_path=row["source_path"],
            run_dir=row["run_dir"],
            current_step=row["current_step"],
            error=row["error"],
            warnings=json.loads(row["warnings"] or "[]"),
            artifacts=[WorkspaceArtifact(**item) for item in json.loads(row["artifacts"] or "[]")],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
