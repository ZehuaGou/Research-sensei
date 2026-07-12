from __future__ import annotations

from pathlib import Path

from researchsensei.jobs import JobStore
from researchsensei.schemas import JobRecord
from researchsensei.web.services import JobService


def _record(job_id: str, run_dir: Path) -> JobRecord:
    return JobRecord(
        job_id=job_id,
        source_path=str(run_dir / "source.md"),
        run_dir=str(run_dir),
    )


def test_job_service_removes_only_managed_run_directory(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    run_dir = workspace / "runs" / "job-1"
    run_dir.mkdir(parents=True)
    (run_dir / "source.md").write_text("paper", encoding="utf-8")
    jobs = JobStore(workspace / "sensei.sqlite3")
    jobs.create(_record("job-1", run_dir))

    result = JobService(jobs, workspace).delete("job-1")

    assert result["artifacts_removed"] is True
    assert not run_dir.exists()
    assert "job-1" not in jobs.list_ids()


def test_job_service_does_not_remove_external_run_directory(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    external = tmp_path / "external" / "job-1"
    external.mkdir(parents=True)
    (external / "source.md").write_text("paper", encoding="utf-8")
    jobs = JobStore(workspace / "sensei.sqlite3")
    jobs.create(_record("job-1", external))

    result = JobService(jobs, workspace).delete("job-1")

    assert result["artifacts_removed"] is False
    assert result["cleanup_warning"]
    assert external.exists()


def test_job_service_scans_and_cleans_confirmed_orphans(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    known = workspace / "runs" / "known"
    orphan = workspace / "runs" / "orphan"
    known.mkdir(parents=True)
    orphan.mkdir(parents=True)
    jobs = JobStore(workspace / "sensei.sqlite3")
    jobs.create(_record("known", known))
    service = JobService(jobs, workspace)

    assert service.scan_orphans() == [str(orphan.resolve())]
    assert service.cleanup_orphans() == [str(orphan.resolve())]
    assert known.exists()
    assert not orphan.exists()
