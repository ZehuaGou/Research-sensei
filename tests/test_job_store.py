from __future__ import annotations

from pathlib import Path
import sqlite3

import pytest

from researchsensei.jobs import JobNotFoundError, JobStore
from researchsensei.schemas import JobRecord, JobStatus, WarningItem, WorkspaceArtifact


def _job(job_id: str, *, created_at: str = "2026-06-02T00:00:00+00:00") -> JobRecord:
    return JobRecord(
        job_id=job_id,
        source_path=f"workspace/runs/{job_id}/source.txt",
        run_dir=f"workspace/runs/{job_id}",
        created_at=created_at,
        updated_at=created_at,
    )


def test_job_store_creates_and_gets_job(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "jobs.sqlite3")
    created = store.create(_job("job-1"))

    restored = store.get("job-1")

    assert restored == created
    assert restored.status == JobStatus.PENDING


def test_job_store_updates_status_step_error_warnings_and_artifacts(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "jobs.sqlite3")
    store.create(_job("job-1"))

    updated = store.update(
        "job-1",
        status=JobStatus.FAILED,
        current_step="ingestion",
        error="parser unavailable",
        warnings=[WarningItem(code="PDF_DEGRADED", message="Used fallback parser")],
        artifacts=[WorkspaceArtifact(artifact_type="ingestion", path="parsed_document.json")],
    )

    assert updated.status == JobStatus.FAILED
    assert updated.current_step == "ingestion"
    assert updated.error == "parser unavailable"
    assert updated.warnings[0].code == "PDF_DEGRADED"
    assert updated.artifacts[0].path == "parsed_document.json"
    assert store.get("job-1") == updated


def test_job_store_missing_job_raises_clear_error(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "jobs.sqlite3")

    with pytest.raises(JobNotFoundError, match="missing"):
        store.get("missing")


def test_job_store_lists_recent_jobs_sorted_by_created_time(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "jobs.sqlite3")
    store.create(_job("old", created_at="2026-06-01T00:00:00+00:00"))
    store.create(_job("new", created_at="2026-06-02T00:00:00+00:00"))

    jobs = store.list_recent(limit=2)

    assert [job.job_id for job in jobs] == ["new", "old"]


def test_job_store_migrates_legacy_db_missing_source_path(tmp_path: Path) -> None:
    db_path = tmp_path / "jobs.sqlite3"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            create table jobs(
                job_id text primary key,
                status text not null,
                filename text not null,
                source_pdf text not null,
                run_dir text not null,
                current_step text not null,
                error text not null default '',
                artifacts text not null default '[]',
                created_at text not null,
                updated_at text not null
            )
            """
        )

    store = JobStore(db_path)
    created = store.create(_job("job-1"))

    assert store.get("job-1") == created
