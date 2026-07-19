from __future__ import annotations

import asyncio
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import APIRouter, HTTPException
from starlette.concurrency import run_in_threadpool

from researchsensei.acquisition.fulltext_resolver import FullTextResolver
from researchsensei.direction import DirectionExplorationService, SeedExpansionService
from researchsensei.ingestion import SinglePaperIngestionRunner
from researchsensei.jobs import JobStore
from researchsensei.schemas import JobRecord, JobStatus, SourceStatus
from researchsensei.source_resolver import SourceResolver
from researchsensei.workspace import WorkspaceStore
from researchsensei.web.request_models import (
    DirectionDeepReadRequest,
    DirectionSearchRequest,
    SeedExpansionRequest,
)
from researchsensei.web.services import PersistentTaskService, TaskExecutionError, TaskNotFoundError


@dataclass(frozen=True)
class DirectionRouteOps:
    candidate_payload: Callable[[dict[str, object]], dict[str, object]]
    handoff_inputs: Callable[[dict[str, object]], tuple[str, str, str, str, str]]
    request_identity: Callable[..., str]
    existing_response: Callable[[JobRecord, str], dict[str, object]]
    resolve_doi: Callable[[FullTextResolver, str, str], tuple[str, str]]
    record_failed: Callable[..., JobRecord]
    doi_failure_message: Callable[[str], str]
    resolve_source: Callable[..., SourceStatus]
    source_identity: Callable[[SourceStatus, str], str]
    handoff_failure: Callable[[JobRecord, SourceStatus], dict[str, object]]
    understanding_status: Callable[[JobRecord], dict[str, object]]
    parse_response: Callable[[JobRecord], dict[str, object]]
    workspace_status: Callable[[JobRecord, object], dict[str, object]]


def create_directions_router(
    *,
    workspace: WorkspaceStore,
    jobs: JobStore,
    resolver: SourceResolver,
    fulltext_resolver: FullTextResolver,
    runner: SinglePaperIngestionRunner,
    direction_service: DirectionExplorationService,
    seed_service: SeedExpansionService,
    tasks: PersistentTaskService,
    ops: DirectionRouteOps,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/directions", tags=["directions"])

    @router.post("/search")
    def search_direction(payload: DirectionSearchRequest) -> dict[str, object]:
        bundle = direction_service.explore(payload.query)
        response = bundle.model_dump(mode="json")
        response["papers"] = response.get("candidate_cards", [])
        return response

    @router.post("/deep_read")
    async def deep_read(payload: DirectionDeepReadRequest) -> dict[str, object]:
        request_payload = payload.model_dump(mode="json", exclude_none=True)
        candidate = ops.candidate_payload(request_payload)
        force = payload.force
        if candidate.get("relevance_gate_evaluated") is True:
            deep_read_passed = candidate.get("deep_read_relevance_passed")
            score = float(str(candidate.get("rule_relevance_score") or 0.0))
            if (
                candidate.get("relevance_gate_passed") is not True
                or deep_read_passed is False
                or score < 0.72
            ):
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "RELEVANCE_GATE_FAILED",
                        "status": "BLOCKED",
                        "message": "The candidate does not meet the deterministic deep-read relevance threshold.",
                        "relevance_score": score,
                        "relevance_reason": str(candidate.get("relevance_reason") or ""),
                    },
                )
        title, doi, pdf_url, arxiv_id, arxiv_url = ops.handoff_inputs(candidate)
        identity = ops.request_identity(doi=doi, pdf_url=pdf_url, arxiv_id=arxiv_id, arxiv_url=arxiv_url)
        if identity and not force:
            existing = jobs.find_by_source_identity(identity)
            if existing is not None:
                return ops.existing_response(existing, identity)

        job_id = uuid.uuid4().hex[:12]
        run_dir = workspace.new_run_dir(job_id)
        if doi and not pdf_url and not arxiv_id and not arxiv_url:
            resolved_pdf_url, resolve_error = ops.resolve_doi(fulltext_resolver, doi, title)
            if resolved_pdf_url:
                pdf_url = resolved_pdf_url
                doi = ""
            else:
                job = ops.record_failed(
                    workspace,
                    jobs,
                    job_id,
                    run_dir,
                    SourceStatus(
                        source_type="doi",
                        original_input=doi,
                        status="rejected",
                        warnings=[resolve_error],
                        degraded_flags=["FULL_TEXT_MISSING", "ABSTRACT_ONLY", "FORMULA_UNAVAILABLE"],
                    ),
                )
                raise HTTPException(
                    status_code=400,
                    detail={
                        "status": "NO_LEGAL_OA_FULLTEXT_FOUND",
                        "handoff_status": "NO_LEGAL_OA_FULLTEXT_FOUND",
                        "job_id": job.job_id,
                        "message": ops.doi_failure_message(resolve_error),
                        "doi": doi,
                    },
                )

        source_status = ops.resolve_source(
            resolver=resolver,
            run_dir=run_dir,
            title=title,
            doi=doi,
            local_path="",
            pdf_url=pdf_url,
            arxiv_id=arxiv_id,
            arxiv_url=arxiv_url,
        )
        if source_status.status != "resolved":
            job = ops.record_failed(workspace, jobs, job_id, run_dir, source_status)
            raise HTTPException(status_code=400, detail=ops.handoff_failure(job, source_status))

        identity = ops.source_identity(source_status, identity)
        existing = jobs.find_by_source_identity(identity)
        if existing is not None and not force:
            return ops.existing_response(existing, identity)
        if force:
            identity = f"{identity}:force:{job_id}"

        job = await run_in_threadpool(
            runner.run,
            source_status.resolved_path,
            job_id=job_id,
            source_status=source_status,
            source_identity=identity,
            title_hint=title,
        )
        if job.status == JobStatus.FAILED:
            raise HTTPException(
                status_code=409,
                detail={
                    "status": "BLOCKED",
                    "handoff_status": "BLOCKED",
                    "job_id": job.job_id,
                    "message": job.error or "Direction candidate handoff failed during PaperWorkspace parsing.",
                    "source_status": source_status.model_dump(mode="json"),
                },
            )

        understanding = ops.understanding_status(job)
        response = {
            **ops.parse_response(job),
            "status": "JOB_CREATED",
            "handoff_status": "JOB_CREATED",
            "source_status": source_status.model_dump(mode="json"),
        }
        if understanding:
            response["understanding_status"] = understanding
            response["paper_workspace_status"] = ops.workspace_status(job, understanding)
            response["final_status"] = understanding.get("status", "")
        return response

    @router.post("/seed_expansion")
    def seed_expansion(payload: SeedExpansionRequest) -> dict[str, object]:
        seed_model = payload.seed or payload.candidate
        seed_payload = seed_model.model_dump(mode="json") if seed_model is not None else {}
        return seed_service.expand(seed_payload).model_dump(mode="json")

    @router.post("/jobs/search", status_code=202)
    def create_search_job(payload: DirectionSearchRequest) -> dict[str, object]:
        def operation(progress: Callable[[str, int], None], cancelled: threading.Event) -> dict[str, object]:
            if cancelled.is_set():
                return {}
            progress("searching", 15)
            bundle = direction_service.explore(payload.query)
            progress("ranking", 75)
            response = bundle.model_dump(mode="json")
            response["papers"] = response.get("candidate_cards", [])
            return response

        return tasks.submit("direction_search", payload.model_dump(mode="json"), operation)

    @router.post("/jobs/deep_read", status_code=202)
    def create_deep_read_job(payload: DirectionDeepReadRequest) -> dict[str, object]:
        def operation(progress: Callable[[str, int], None], cancelled: threading.Event) -> dict[str, object]:
            if cancelled.is_set():
                return {}
            progress("resolving_source", 10)
            try:
                result = asyncio.run(deep_read(payload))
            except HTTPException as error:
                detail = error.detail
                if isinstance(detail, dict):
                    error_type = str(detail.get("status") or detail.get("code") or f"HTTP_{error.status_code}")
                    message = str(detail.get("message") or detail)
                else:
                    error_type = f"HTTP_{error.status_code}"
                    message = str(detail)
                raise TaskExecutionError(error_type, message) from error
            progress("building_understanding", 90)
            return result

        return tasks.submit(
            "direction_deep_read",
            payload.model_dump(mode="json", exclude_none=True),
            operation,
        )

    @router.get("/jobs/{task_id}")
    def get_job(task_id: str) -> dict[str, object]:
        try:
            return tasks.get(task_id)
        except TaskNotFoundError as error:
            raise HTTPException(status_code=404, detail={"code": "TASK_NOT_FOUND", "message": "Task not found."}) from error

    @router.delete("/jobs/{task_id}")
    def cancel_job(task_id: str) -> dict[str, object]:
        try:
            return tasks.cancel(task_id)
        except TaskNotFoundError as error:
            raise HTTPException(status_code=404, detail={"code": "TASK_NOT_FOUND", "message": "Task not found."}) from error

    return router
