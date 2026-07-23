from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, HTTPException

from researchsensei.jobs import JobStore
from researchsensei.learning import LearningService, LearningStore
from researchsensei.schemas import JobRecord
from researchsensei.tutor import PaperTutorService
from researchsensei.web.request_models import LearningAnswerRequest, LearningSessionRequest


def create_learning_router(
    *,
    jobs: JobStore,
    store: LearningStore,
    get_job: Callable[[JobStore, str], JobRecord],
    service_for_job: Callable[..., PaperTutorService],
    artifacts_for_job: Callable[[JobRecord], dict[str, object]],
    sync_memory: Callable[..., JobRecord],
) -> APIRouter:
    router = APIRouter(tags=["learning"])

    def job_and_service(job_id: str) -> tuple[JobRecord, LearningService]:
        job = get_job(jobs, job_id)

        def tutor_for_job(current: JobRecord) -> PaperTutorService:
            return service_for_job(current, required_gate="learning_drills")

        service = LearningService(
            store=store,
            jobs=jobs,
            tutor_for_job=tutor_for_job,
            artifacts_for_job=artifacts_for_job,
            sync_tutor_memory=sync_memory,
        )
        return job, service

    @router.get("/api/v1/learning")
    def learning_overview() -> dict[str, object]:
        return store.overview().model_dump(mode="json")

    @router.post("/api/v1/jobs/{job_id}/learning/import")
    def import_learning_items(job_id: str) -> dict[str, object]:
        job, service = job_and_service(job_id)
        service_for_job(job, required_gate="learning_drills")
        items = service.import_job(job)
        return {
            "job_id": job.job_id,
            "imported_count": len(items),
            "overview": store.overview(job_id=job.job_id).model_dump(mode="json"),
        }

    @router.get("/api/v1/jobs/{job_id}/learning")
    def job_learning_overview(job_id: str) -> dict[str, object]:
        job, service = job_and_service(job_id)
        service_for_job(job, required_gate="learning_drills")
        service.import_job(job)
        return store.overview(job_id=job.job_id).model_dump(mode="json")

    @router.post("/api/v1/jobs/{job_id}/learning/sessions")
    def start_learning_session(
        job_id: str,
        payload: LearningSessionRequest,
    ) -> dict[str, object]:
        job, service = job_and_service(job_id)
        try:
            session = service.start_session(
                job,
                count=payload.count,
                include_not_due=payload.include_not_due,
            )
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        return session.model_dump(mode="json")

    @router.get("/api/v1/jobs/{job_id}/learning/active-session")
    def get_active_learning_session(job_id: str) -> dict[str, object]:
        job, service = job_and_service(job_id)
        session = service.get_active_session(job)
        return {
            "job_id": job.job_id,
            "session": session.model_dump(mode="json") if session is not None else None,
        }

    @router.get("/api/v1/jobs/{job_id}/learning/sessions/{session_id}")
    def get_learning_session(job_id: str, session_id: str) -> dict[str, object]:
        job, service = job_and_service(job_id)
        try:
            return service.get_session(job, session_id).model_dump(mode="json")
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @router.post("/api/v1/jobs/{job_id}/learning/sessions/{session_id}/answer")
    def answer_learning_question(
        job_id: str,
        session_id: str,
        payload: LearningAnswerRequest,
    ) -> dict[str, object]:
        job, service = job_and_service(job_id)
        try:
            result = service.answer(job, session_id, payload.user_answer)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return result.model_dump(mode="json")

    return router
