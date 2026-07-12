from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, HTTPException, Query

from researchsensei.jobs import JobStore
from researchsensei.schemas import JobRecord
from researchsensei.web.request_models import OrphanCleanupRequest
from researchsensei.web.services import JobService


JobPayload = Callable[[JobRecord], dict[str, object]]


def create_jobs_router(
    *,
    jobs: JobStore,
    job_service: JobService,
    job_payload: JobPayload,
) -> APIRouter:
    router = APIRouter(tags=["jobs"])

    @router.get("/api/v1/jobs")
    def list_jobs(limit: int = Query(default=20, ge=1, le=200)) -> dict[str, object]:
        return {"jobs": [job_payload(job) for job in jobs.list_recent(limit=limit)]}

    @router.get("/api/v1/jobs/{job_id}")
    def get_job(job_id: str) -> dict[str, object]:
        try:
            return job_payload(jobs.get(job_id))
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Job not found.") from error

    @router.delete("/api/v1/jobs/{job_id}")
    def delete_job(job_id: str, remove_artifacts: bool = True) -> dict[str, object]:
        try:
            return job_service.delete(job_id, remove_artifacts=remove_artifacts)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Job not found.") from error

    @router.get("/api/v1/maintenance/orphan-runs")
    def list_orphan_runs() -> dict[str, object]:
        paths = job_service.scan_orphans()
        return {"orphan_runs": paths, "count": len(paths)}

    @router.post("/api/v1/maintenance/orphan-runs/cleanup")
    def cleanup_orphan_runs(payload: OrphanCleanupRequest) -> dict[str, object]:
        if not payload.confirm:
            raise HTTPException(
                status_code=409,
                detail={"code": "CONFIRMATION_REQUIRED", "message": "Set confirm=true to remove orphan runs."},
            )
        removed = job_service.cleanup_orphans()
        return {"status": "CLEANED", "removed": removed, "count": len(removed)}

    return router
