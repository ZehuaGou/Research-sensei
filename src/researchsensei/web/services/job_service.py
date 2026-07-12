from __future__ import annotations

import shutil
from pathlib import Path

from researchsensei.jobs import JobStore


class JobService:
    """Coordinates database deletion with workspace-bounded artifact cleanup."""

    def __init__(self, jobs: JobStore, workspace_root: str | Path) -> None:
        self.jobs = jobs
        self.workspace_root = Path(workspace_root).resolve()
        self.runs_root = (self.workspace_root / "runs").resolve()

    def delete(self, job_id: str, *, remove_artifacts: bool = True) -> dict[str, object]:
        job = self.jobs.get(job_id)
        removed = False
        warning = ""
        if remove_artifacts and job.run_dir:
            run_dir = Path(job.run_dir)
            if self._is_managed_run_dir(run_dir, job_id=job_id):
                if run_dir.exists():
                    shutil.rmtree(run_dir)
                    removed = True
            else:
                warning = "Run directory is outside the managed workspace and was not removed."
        self.jobs.delete(job_id)
        return {
            "status": "DELETED",
            "job_id": job_id,
            "artifacts_removed": removed,
            "cleanup_warning": warning,
        }

    def scan_orphans(self) -> list[str]:
        if not self.runs_root.exists():
            return []
        known = self.jobs.list_ids()
        return sorted(
            str(path)
            for path in self.runs_root.iterdir()
            if path.is_dir() and path.name not in known and self._is_managed_run_dir(path)
        )

    def cleanup_orphans(self) -> list[str]:
        removed: list[str] = []
        for raw_path in self.scan_orphans():
            path = Path(raw_path)
            if not self._is_managed_run_dir(path):
                continue
            shutil.rmtree(path)
            removed.append(str(path))
        return removed

    def _is_managed_run_dir(self, path: Path, *, job_id: str = "") -> bool:
        try:
            resolved = path.resolve(strict=False)
        except OSError:
            return False
        if resolved.parent != self.runs_root:
            return False
        if job_id and resolved.name != job_id:
            return False
        return self.runs_root == resolved.parent and self.workspace_root in resolved.parents
