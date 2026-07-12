from __future__ import annotations

import json
import hashlib
import os
import re
import sqlite3
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.concurrency import run_in_threadpool

from researchsensei.acquisition import PaperSearchMcpAdapter
from researchsensei.acquisition.fulltext_resolver import FullTextResolver
from researchsensei.core.config import AppConfig, ConfigService
from researchsensei.direction import DirectionExplorationService, SeedExpansionService
from researchsensei.ingestion import LightweightIngestionService, SinglePaperIngestionRunner
from researchsensei.jobs import JobStore
from researchsensei.library import PaperLibraryStore
from researchsensei.llm.client import LLMClient
from researchsensei.llm.types import LLMConfig
from researchsensei.m4.service import M4InteractionService
from researchsensei.query import QueryPlanner
from researchsensei.schemas import CandidatePaper, InteractiveAnswer, JobRecord, JobStatus, SourceStatus, WarningItem, WorkspaceArtifact
from researchsensei.source_resolver import PaperSourceResolver, SourceResolver
from researchsensei.workspace import WorkspaceStore
from researchsensei.web.routers import (
    DirectionRouteOps,
    create_directions_router,
    create_jobs_router,
    create_library_router,
    create_m4_router,
    create_settings_router,
)
from researchsensei.web.dependencies import WebDependencies
from researchsensei.web.services import (
    JobService,
    PersistentTaskService,
    UploadService,
    UploadValidationError,
)


def _debug_enabled() -> bool:
    return os.getenv("SENSEI_DEBUG", "").lower() in {"1", "true", "yes"}


def _ingestion_for_backend(parser_backend: str) -> LightweightIngestionService:
    if parser_backend not in {"pymupdf", "lightweight"}:
        raise ValueError(f"Unsupported parser backend: {parser_backend}")
    return LightweightIngestionService()


def _paper_search_command(config: AppConfig) -> list[str] | None:
    return config.search.command_args()


def create_app(
    workspace_root: str | Path | None = None,
    job_db_path: str | Path | None = None,
    allowed_local_roots: list[str | Path] | None = None,
    http_client: httpx.Client | None = None,
    max_download_bytes: int | None = None,
    llm_client: LLMClient | None = None,
    enable_configured_llm: bool | None = None,
    llm_provider: str = "",
    llm_config: LLMConfig | None = None,
    config_service: ConfigService | None = None,
    direction_service: DirectionExplorationService | None = None,
    seed_expansion_service: SeedExpansionService | None = None,
) -> FastAPI:
    app = FastAPI(title="ResearchSensei", version="0.6.0")

    @app.exception_handler(RequestValidationError)
    async def request_validation_error(_request: Request, error: RequestValidationError) -> JSONResponse:
        details = jsonable_encoder(error.errors())
        return JSONResponse(
            status_code=422,
            content={
                "detail": details,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed.",
                    "details": details,
                },
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_request: Request, error: StarletteHTTPException) -> JSONResponse:
        detail = error.detail
        if isinstance(detail, dict):
            code = str(detail.get("code") or detail.get("status") or f"HTTP_{error.status_code}")
            message = str(detail.get("message") or code)
        else:
            code = f"HTTP_{error.status_code}"
            message = str(detail)
        return JSONResponse(
            status_code=error.status_code,
            headers=error.headers,
            content={
                "detail": jsonable_encoder(detail),
                "error": {"code": code, "message": message},
            },
        )

    resolved_config_service = config_service or ConfigService()
    runtime_config = resolved_config_service.load()
    resolved_workspace_root = Path(workspace_root) if workspace_root is not None else Path(runtime_config.app.workspace_dir)
    resolved_max_bytes = (
        int(max_download_bytes)
        if max_download_bytes is not None
        else runtime_config.app.max_upload_mb * 1024 * 1024
    )
    workspace = WorkspaceStore(resolved_workspace_root)
    db_path = Path(job_db_path or (workspace.root / "sensei.sqlite3"))
    jobs = JobStore(db_path)
    job_service = JobService(jobs, workspace.root)
    paper_library = PaperLibraryStore(db_path, managed_roots=[workspace.root])
    background_tasks = PersistentTaskService(db_path)
    resolved_llm_client = llm_client or _configured_llm_client(
        enable_configured_llm=enable_configured_llm,
        provider_name=llm_provider,
        llm_config=llm_config,
        config_service=resolved_config_service,
        app_config=runtime_config,
    )
    runner = SinglePaperIngestionRunner(
        workspace=workspace,
        jobs=jobs,
        ingestion=_ingestion_for_backend(runtime_config.app.parser_backend),
        llm_client=resolved_llm_client,
    )
    resolver = SourceResolver(
        allowed_roots=allowed_local_roots if allowed_local_roots is not None else [workspace.root],
        http_client=http_client,
        max_download_bytes=resolved_max_bytes,
    )
    fulltext_resolver = FullTextResolver(
        http_client=http_client,
        max_download_bytes=resolved_max_bytes,
        timeout_seconds=float(runtime_config.search.timeout_seconds),
    )
    m1_source_dir = workspace.root / "m1_searches"
    paper_library.import_manifests(m1_source_dir)
    configured_search_adapter = PaperSearchMcpAdapter(
        sources=runtime_config.search.sources,
        command=_paper_search_command(runtime_config),
        timeout_seconds=float(runtime_config.search.timeout_seconds),
    )
    resolved_direction_service = direction_service or DirectionExplorationService(
        adapters={"paper_search": configured_search_adapter},
        source_resolver=PaperSourceResolver(
            network_enabled=True,
            download_dir=m1_source_dir,
            http_client=http_client,
            timeout_seconds=float(runtime_config.search.timeout_seconds),
            max_download_bytes=resolved_max_bytes,
            paper_library=paper_library,
        ),
        fulltext_resolver=fulltext_resolver,
        source_download_dir=m1_source_dir,
        paper_library=paper_library,
        max_results_per_source=runtime_config.search.max_results,
        query_planner=QueryPlanner(resolved_llm_client) if resolved_llm_client is not None else None,
    )
    resolved_seed_expansion_service = seed_expansion_service or SeedExpansionService(
        adapters={"paper_search": configured_search_adapter},
        max_results_per_source=runtime_config.search.max_results,
    )
    app.state.runtime_config = runtime_config
    app.state.workspace = workspace
    app.state.jobs = jobs
    app.state.job_service = job_service
    app.state.paper_library = paper_library
    app.state.background_tasks = background_tasks
    app.state.dependencies = WebDependencies(
        config_service=resolved_config_service,
        config=runtime_config,
        workspace=workspace,
        jobs=jobs,
        job_service=job_service,
        paper_library=paper_library,
        background_tasks=background_tasks,
        source_resolver=resolver,
        direction_service=resolved_direction_service,
        seed_expansion_service=resolved_seed_expansion_service,
        runner=runner,
        llm_client=resolved_llm_client,
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        try:
            yield
        finally:
            background_tasks.close()

    app.router.lifespan_context = lifespan

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "researchsensei"}

    app.include_router(
        create_settings_router(
            config_service=resolved_config_service,
            llm_client=resolved_llm_client,
            settings_payload=_settings_payload,
            env_writer=_set_env_value,
        )
    )
    app.include_router(
        create_directions_router(
            workspace=workspace,
            jobs=jobs,
            resolver=resolver,
            fulltext_resolver=fulltext_resolver,
            runner=runner,
            direction_service=resolved_direction_service,
            seed_service=resolved_seed_expansion_service,
            tasks=background_tasks,
            ops=DirectionRouteOps(
                candidate_payload=_direction_candidate_payload,
                handoff_inputs=_direction_handoff_inputs,
                request_identity=_request_source_identity,
                existing_response=_existing_job_response,
                resolve_doi=_resolve_doi_to_legal_pdf,
                record_failed=_record_failed_source_job,
                doi_failure_message=_doi_failure_message,
                resolve_source=_resolve_source,
                source_identity=_source_status_identity,
                handoff_failure=_direction_handoff_failure,
                understanding_status=_job_understanding_status,
                parse_response=_job_parse_response,
                workspace_status=_paper_workspace_status,
            ),
        )
    )
    app.include_router(create_library_router(paper_library))
    app.include_router(create_jobs_router(jobs=jobs, job_service=job_service, job_payload=_job_response))
    app.include_router(
        create_m4_router(
            jobs=jobs,
            llm_client=resolved_llm_client,
            get_job=_get_job_or_404,
            service_for_job=_m4_service_for_job,
            sync_memory=_sync_m4_memory_artifact,
            runtime_answer=_runtime_self_answer,
            get_config=lambda: app.state.runtime_config,
        )
    )

    @app.post("/api/v1/documents/parse")
    async def parse_document(
        file: UploadFile | None = File(None),
        title: str = Form(""),
        doi: str = Form(""),
        local_path: str = Form(""),
        pdf_url: str = Form(""),
        arxiv_id: str = Form(""),
        arxiv_url: str = Form(""),
        force: bool = Form(False),
    ) -> dict[str, object]:
        job_id = uuid.uuid4().hex[:12]
        if file is not None and file.filename:
            upload_service = UploadService(
                workspace.root / "incoming",
                max_bytes=resolved_max_bytes,
            )
            try:
                saved_upload = await upload_service.save(file)
            except UploadValidationError as error:
                raise HTTPException(
                    status_code=error.status_code,
                    detail={"code": error.code, "message": error.message},
                ) from error
            try:
                source_status = resolver.resolve_upload(
                    saved_upload.path,
                    original_filename=saved_upload.original_filename,
                    content_type=saved_upload.content_type,
                )
                source_identity = _request_source_identity(
                    doi=doi,
                    arxiv_id=arxiv_id,
                    arxiv_url=arxiv_url,
                ) or _path_cache_identity(str(saved_upload.path))
                existing = jobs.find_by_source_identity(source_identity)
                if existing is not None and not force:
                    return _existing_job_response(existing, source_identity)
                if force:
                    source_identity = f"{source_identity}:force:{job_id}"
                job = await run_in_threadpool(
                    runner.run,
                    source_status.resolved_path,
                    job_id=job_id,
                    source_status=source_status,
                    source_identity=source_identity,
                )
                return _job_parse_response(job)
            finally:
                upload_service.cleanup(saved_upload)

        run_dir = workspace.new_run_dir(job_id)
        if local_path.strip():
            m2_artifact_job = _try_register_m2_artifact_job(
                resolver=resolver,
                jobs=jobs,
                job_id=job_id,
                artifact_dir_text=local_path.strip(),
            )
            if m2_artifact_job is not None:
                return _job_parse_response(m2_artifact_job)

        request_identity = _request_source_identity(
            doi=doi,
            pdf_url=pdf_url,
            arxiv_id=arxiv_id,
            arxiv_url=arxiv_url,
        )
        if request_identity and not force:
            existing = jobs.find_by_source_identity(request_identity)
            if existing is not None:
                return _existing_job_response(existing, request_identity)

        if doi.strip() and not any(value.strip() for value in [local_path, pdf_url, arxiv_id, arxiv_url]):
            resolved_pdf_url, resolve_error = _resolve_doi_to_legal_pdf(
                fulltext_resolver,
                doi.strip(),
                title,
            )
            if resolved_pdf_url:
                pdf_url = resolved_pdf_url
                doi = ""
            else:
                source_status = SourceStatus(
                    source_type="doi",
                    original_input=doi.strip(),
                    status="rejected",
                    warnings=[resolve_error],
                    degraded_flags=["FULL_TEXT_MISSING", "ABSTRACT_ONLY", "FORMULA_UNAVAILABLE"],
                )
                job = _record_failed_source_job(workspace, jobs, job_id, run_dir, source_status)
                raise HTTPException(
                    status_code=400,
                    detail={
                        "job_id": job.job_id,
                        "status": "NO_LEGAL_OA_FULLTEXT_FOUND",
                        "message": _doi_failure_message(resolve_error),
                        "source_status": source_status.model_dump(mode="json"),
                    },
                )

        request_identity = request_identity or _request_source_identity(
            pdf_url=pdf_url,
            arxiv_id=arxiv_id,
            arxiv_url=arxiv_url,
        )
        source_status = _resolve_source(
            resolver=resolver,
            run_dir=run_dir,
            title=title,
            doi=doi,
            local_path=local_path,
            pdf_url=pdf_url,
            arxiv_id=arxiv_id,
            arxiv_url=arxiv_url,
        )
        if source_status.status != "resolved":
            job = _record_failed_source_job(workspace, jobs, job_id, run_dir, source_status)
            raise HTTPException(
                status_code=400,
                detail={
                    "job_id": job.job_id,
                    "source_status": source_status.model_dump(mode="json"),
                },
            )

        source_identity = _source_status_identity(source_status, request_identity)
        existing = jobs.find_by_source_identity(source_identity)
        if existing is not None and not force:
            return _existing_job_response(existing, source_identity)
        if force:
            source_identity = f"{source_identity}:force:{job_id}"

        job = await run_in_threadpool(
            runner.run,
            source_status.resolved_path,
            job_id=job_id,
            source_status=source_status,
            source_identity=source_identity,
        )
        return _job_parse_response(job)

    @app.post("/api/v1/jobs/{job_id}/reparse")
    async def reparse_job(job_id: str) -> dict[str, object]:
        original = _get_job_or_404(jobs, job_id)
        source_path = Path(original.source_path)
        if not source_path.exists() or source_path.is_dir():
            raise HTTPException(
                status_code=400,
                detail={
                    "status": "SOURCE_UNAVAILABLE",
                    "message": "The original job source is not a reusable file path.",
                    "source_path": original.source_path,
                },
            )

        new_job_id = uuid.uuid4().hex[:12]
        source_status = SourceStatus(
            source_type="reparse",
            original_input=original.source_path,
            resolved_path=str(source_path),
            status="resolved",
        )
        source_identity = f"{original.source_identity or _path_cache_identity(str(source_path))}:reparse:{new_job_id}"
        job = await run_in_threadpool(
            runner.run,
            str(source_path),
            job_id=new_job_id,
            source_status=source_status,
            source_identity=source_identity,
        )
        return {
            **_job_parse_response(job),
            "status": "JOB_CREATED",
            "handoff_status": "JOB_CREATED",
            "source_job_id": job_id,
        }

    @app.get("/api/v1/jobs/{job_id}/artifacts")
    def get_job_artifacts(job_id: str) -> dict[str, object]:
        if not _debug_enabled():
            raise HTTPException(
                status_code=403,
                detail={"message": "Raw artifacts are debug-only. Use /understanding_status or /cards."},
            )
        try:
            job = jobs.get(job_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Job not found.") from error
        return {
            "job_id": job.job_id,
            "artifacts": [_artifact_response(job, artifact.path, artifact.artifact_type) for artifact in job.artifacts],
        }

    @app.get("/api/v1/jobs/{job_id}/understanding_status")
    def get_understanding_status(job_id: str) -> dict[str, object]:
        try:
            job = jobs.get(job_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Job not found.") from error

        artifact = _find_artifact(job, "understanding_status")
        if artifact is None:
            raise HTTPException(status_code=404, detail="understanding_status not found.")

        content = _read_artifact_content(job, artifact.path)
        return {
            "job_id": job.job_id,
            "understanding_status": content,
            "paper_workspace_status": _paper_workspace_status(job, content),
        }

    @app.get("/api/v1/jobs/{job_id}/cards")
    def get_cards(job_id: str) -> dict[str, object]:
        try:
            job = jobs.get(job_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Job not found.") from error

        # Read understanding_status
        us_artifact = _find_artifact(job, "understanding_status")
        if us_artifact is None:
            raise HTTPException(status_code=404, detail="understanding_status not found.")

        status_content = _read_artifact_content(job, us_artifact.path)
        status = status_content.get("status", "")
        blocking_reason = status_content.get("blocking_reason", "")
        paper_workspace_status = _paper_workspace_status(job, status_content)
        component_status = status_content.get("component_status", {})
        if not isinstance(component_status, dict):
            component_status = {}

        # Gating by status
        if status == "BASELINE_ONLY":
            raise HTTPException(
                status_code=403,
                detail={
                    "status": "BASELINE_ONLY",
                    "blocking_reason": blocking_reason,
                    "message": "Baseline artifacts are not final understanding cards.",
                },
            )

        if status == "BLOCKED_UNDERSTANDING":
            raise HTTPException(
                status_code=403,
                detail={
                    "status": "BLOCKED_UNDERSTANDING",
                    "blocking_reason": blocking_reason,
                    "warnings": status_content.get("warnings", []),
                },
            )

        if status == "FAILED":
            raise HTTPException(
                status_code=403,
                detail={
                    "status": "FAILED",
                    "message": "Pipeline failed. No cards available.",
                },
            )

        # SUCCESS or DEGRADED_STRUCTURAL: check card artifacts
        card_types = ["paper_card", "formula_cards", "teaching_cards"]
        cards: dict[str, object] = {}
        missing: list[str] = []

        for card_type in card_types:
            artifact = _find_artifact(job, card_type)
            if status == "DEGRADED_STRUCTURAL":
                status_for_component = str(component_status.get(card_type) or "").upper()
                if status_for_component and status_for_component != "SUCCESS":
                    if status_for_component != "SKIPPED":
                        missing.append(card_type)
                    continue
            if artifact is not None:
                cards[card_type] = _read_artifact_content(job, artifact.path)
            else:
                status_for_component = str(component_status.get(card_type) or "").upper()
                if status_for_component != "SKIPPED":
                    missing.append(card_type)

        # SUCCESS requires all cards
        if status == "SUCCESS" and missing:
            raise HTTPException(
                status_code=409,
                detail={
                    "status": "SUCCESS",
                    "message": "SUCCESS status requires all card artifacts.",
                    "missing_components": missing,
                },
            )

        # DEGRADED requires paper_card + formula_cards; teaching_cards may be missing
        if status == "DEGRADED_STRUCTURAL":
            required_missing = [
                m for m in missing
                if _degraded_missing_component_is_required(m, component_status)
            ]
            if required_missing:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "status": "DEGRADED_STRUCTURAL",
                        "message": "DEGRADED status requires paper_card and formula_cards.",
                        "missing_components": missing,
                    },
                )

        result: dict[str, object] = {
            "job_id": job.job_id,
            "status": status,
            "paper_workspace_status": paper_workspace_status,
            "cards": cards,
        }

        if status == "DEGRADED_STRUCTURAL":
            result["degraded"] = True
            result["missing_components"] = missing

        return result

    return app


M2_ARTIFACT_TYPES = {
    "source_status.json": "source_status",
    "canonical_status.json": "canonical_status",
    "parsed_document.json": "parsed_document",
    "passage_index.json": "passage_index",
    "claim_evidence.json": "claim_evidence",
    "evidence_index.json": "evidence_index",
    "paper_skeleton.json": "paper_skeleton",
    "evidence_pack.json": "evidence_pack",
    "formula_evidence_pack.json": "formula_evidence_pack",
    "survey_status.json": "survey_status",
    "survey_landscape.json": "survey_landscape",
    "method_taxonomy.json": "method_taxonomy",
    "extracted_key_papers.json": "extracted_key_papers",
    "survey_claims.json": "survey_claims",
    "paper_card.json": "paper_card",
    "formula_cards.json": "formula_cards",
    "teaching_cards.json": "teaching_cards",
    "quality_report.json": "quality_report",
    "understanding_status.json": "understanding_status",
    "m4_memory.json": "m4_memory",
    "m2_run_summary.json": "m2_run_summary",
    "m2_full_report.md": "m2_full_report",
}


def _try_register_m2_artifact_job(
    *,
    resolver: SourceResolver,
    jobs: JobStore,
    job_id: str,
    artifact_dir_text: str,
) -> JobRecord | None:
    try:
        artifact_dir = Path(artifact_dir_text).resolve(strict=True)
    except OSError:
        return None
    if not artifact_dir.is_dir() or not _looks_like_m2_artifact_dir(artifact_dir):
        return None
    if not resolver._is_allowed(artifact_dir):
        raise HTTPException(
            status_code=400,
            detail={
                "job_id": job_id,
                "source_status": SourceStatus(
                    source_type="m2_artifact_dir",
                    original_input=artifact_dir_text,
                    status="rejected",
                    warnings=["SECURITY_REJECTED"],
                    degraded_flags=["FULL_TEXT_MISSING", "ABSTRACT_ONLY", "FORMULA_UNAVAILABLE"],
                ).model_dump(mode="json"),
            },
        )

    artifacts = [
        WorkspaceArtifact(artifact_type=artifact_type, path=str(artifact_dir / filename))
        for filename, artifact_type in M2_ARTIFACT_TYPES.items()
        if (artifact_dir / filename).exists()
    ]
    status_content = _read_json_file(artifact_dir / "understanding_status.json")
    source_status = _read_json_file(artifact_dir / "source_status.json")
    warnings = [
        WarningItem(code="M2_ARTIFACT_JOB", message="Registered existing M2 artifact run for PaperWorkspace display.")
    ]
    for warning in status_content.get("warnings", []):
        if isinstance(warning, dict):
            warnings.append(WarningItem(
                code=str(warning.get("code") or "M2_WARNING"),
                message=str(warning.get("message") or ""),
                detail=str(warning.get("detail") or ""),
            ))

    return jobs.create(JobRecord(
        job_id=job_id,
        source_path=str(source_status.get("resolved_path") or artifact_dir),
        run_dir=str(artifact_dir),
        status=JobStatus.SUCCEEDED,
        current_step="m2_artifacts_registered",
        warnings=warnings,
        artifacts=artifacts,
    ))


def _looks_like_m2_artifact_dir(path: Path) -> bool:
    return (path / "understanding_status.json").exists() and (
        (path / "m2_run_summary.json").exists()
        or (path / "paper_card.json").exists()
        or (path / "quality_report.json").exists()
    )


def _read_json_file(path: Path) -> dict[str, object]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _get_job_or_404(jobs: JobStore, job_id: str) -> JobRecord:
    try:
        return jobs.get(job_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Job not found.") from error


def _m4_service_for_job(
    job: JobRecord,
    *,
    llm_client: LLMClient | None = None,
    required_gate: str = "reading_display",
) -> M4InteractionService:
    status = _job_understanding_status(job)
    if not status:
        raise HTTPException(status_code=404, detail="understanding_status not found.")
    if status.get("allowed_for_user_display") is not True:
        raise HTTPException(
            status_code=403,
            detail={
                "status": status.get("status", "BLOCKED"),
                "blocking_reason": status.get("blocking_reason", ""),
                "message": "M4 requires user-facing M2 understanding artifacts.",
            },
        )
    downstream = status.get("allowed_downstream")
    downstream = downstream if isinstance(downstream, dict) else {}
    if required_gate and downstream.get(required_gate) is not True:
        raise HTTPException(
            status_code=403,
            detail={
                "status": status.get("status", "BLOCKED"),
                "blocking_reason": status.get("blocking_reason", ""),
                "gate": f"allowed_downstream.{required_gate}",
                "message": f"M4 route requires allowed_downstream.{required_gate}.",
            },
        )
    return M4InteractionService(
        job_id=job.job_id,
        run_dir=Path(job.run_dir),
        artifacts=_m4_artifacts(job),
        llm_client=llm_client,
    )


def _m4_artifacts(job: JobRecord) -> dict[str, object]:
    allowed_types = {
        "understanding_status",
        "paper_card",
        "formula_cards",
        "teaching_cards",
        "passage_index",
        "claim_evidence",
        "evidence_index",
        "paper_skeleton",
    }
    artifacts: dict[str, object] = {}
    for artifact in job.artifacts:
        if artifact.artifact_type not in allowed_types:
            continue
        artifacts[artifact.artifact_type] = _read_artifact_content(job, artifact.path)
    return artifacts


def _sync_m4_memory_artifact(jobs: JobStore, job: JobRecord, memory_path: Path) -> JobRecord:
    if not memory_path.exists():
        return job
    if any(artifact.artifact_type == "m4_memory" for artifact in job.artifacts):
        return job
    return jobs.update(
        job.job_id,
        artifacts=[*job.artifacts, WorkspaceArtifact(artifact_type="m4_memory", path=str(memory_path))],
    )


def _runtime_self_answer(
    payload: dict[str, object],
    *,
    llm_client: LLMClient | None,
    config_service: ConfigService | AppConfig | None,
) -> InteractiveAnswer | None:
    question = _compact_question_text(payload.get("question") or payload.get("user_question"))
    if not _is_runtime_self_question(question):
        return None

    settings = _runtime_llm_payload(llm_client=llm_client, config_service=config_service)
    provider = str(settings.get("active_provider") or settings.get("provider_display_name") or "未配置")
    model = str(settings.get("model") or "未配置")
    endpoint = str(settings.get("request_endpoint") or "")
    route_note = str(settings.get("route_note") or "")
    llm_enabled = bool(settings.get("llm_enabled"))
    provider_known = bool(settings.get("provider_known", True))
    api_key_configured = bool(settings.get("api_key_configured", True))

    lines = [
        "我是 ResearchSensei 的 M4 论文助教，负责基于当前论文证据解释论文、公式和追问。",
        f"当前模型配置是 {model}。",
        f"提供方是 {provider}。",
    ]
    if endpoint:
        lines.append(f"请求通道是 {endpoint}。")
    if route_note:
        lines.append(route_note)
    if not provider_known:
        lines.append("不过当前 provider 没在配置里找到，所以不能确认真实请求会成功。")
    elif not llm_enabled:
        lines.append("不过 API LLM 现在没有启用，论文问答会退回到本地卡片证据。")
    elif not api_key_configured:
        lines.append("不过当前 provider 的 API key 没有配置完整，真实调用可能不可用。")

    return InteractiveAnswer(
        status="SUCCESS",
        answer="\n".join(lines),
        evidence_refs=[],
        memory_refs=[],
        uncertainty="这是运行时配置问题，不属于论文证据问答，所以没有引用 evidence_ref。",
        follow_up_suggestions=["要不要我打开设置页看模型列表？", "要不要切换当前模型？"],
        used_context={"memory": False, "artifacts": False, "llm": False},
        warnings=[],
    )


def _runtime_llm_payload(
    *,
    llm_client: LLMClient | None,
    config_service: ConfigService | AppConfig | None,
) -> dict[str, object]:
    provider = getattr(llm_client, "provider", None)
    if provider is not None:
        return {
            "active_provider": _public_provider_name(str(getattr(provider, "name", "") or "")),
            "provider_key": str(getattr(provider, "name", "") or ""),
            "provider_display_name": _public_provider_name(str(getattr(provider, "name", "") or "")),
            "provider_kind": str(getattr(provider, "kind", "") or ""),
            "base_url": str(getattr(provider, "base_url", "") or ""),
            "request_endpoint": _provider_request_endpoint(provider),
            "api_key_env": str(getattr(provider, "api_key_env", "") or ""),
            "model": str(getattr(provider, "model", "") or ""),
            "auth_header": str(getattr(provider, "auth_header", "") or ""),
            "route_note": _provider_route_note(provider),
            "llm_enabled": True,
            "api_key_configured": bool(os.getenv(str(getattr(provider, "api_key_env", "") or ""), ""))
            if getattr(provider, "api_key_env", "")
            else True,
            "provider_known": True,
        }
    return _settings_payload(config_service)


def _compact_question_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _is_runtime_self_question(question: str) -> bool:
    if not question:
        return False
    text = re.sub(r"\s+", "", question.lower())
    paper_markers = ("这篇论文", "当前论文", "论文里", "论文中", "文中", "文章里", "方法里")
    self_markers = (
        "你",
        "m4",
        "助教",
        "系统",
        "当前配置",
        "运行配置",
        "provider",
        "提供方",
        "api",
        "接口",
        "ccswitch",
        "cc_switch",
    )
    if any(marker in text for marker in paper_markers) and not any(marker in text for marker in self_markers):
        return False

    if _is_runtime_identity_question(text):
        return True

    target_markers = ("模型", "model", "provider", "提供方", "接口", "api", "baseurl", "base_url", "ccswitch", "cc_switch")
    action_markers = ("用", "使用", "调用", "接入", "跑", "配置", "当前", "现在", "哪个", "什么", "是谁")
    subject_markers = (*self_markers, "当前", "现在")
    return (
        any(marker in text for marker in subject_markers)
        and any(marker in text for marker in target_markers)
        and any(marker in text for marker in action_markers)
    )


def _is_runtime_identity_question(compact_lower_question: str) -> bool:
    identity_markers = ("你是谁", "你现在是谁", "你是哪个", "你是什么", "你能做什么", "m4是谁", "助教是谁")
    return any(marker in compact_lower_question for marker in identity_markers)


def _configured_llm_client(
    *,
    enable_configured_llm: bool | None,
    provider_name: str,
    llm_config: LLMConfig | None,
    config_service: ConfigService | None,
    app_config: AppConfig | None = None,
) -> LLMClient | None:
    """Build the real API LLM client only when explicitly enabled."""
    service = config_service or ConfigService()
    config = app_config or service.load()
    enabled = (
        _env_truthy("RESEARCHSENSEI_ENABLE_API_LLM")
        if enable_configured_llm is None
        else enable_configured_llm
    )
    if not enabled:
        return None

    actual_provider = _canonical_provider_name(
        provider_name or os.getenv("RESEARCHSENSEI_LLM_PROVIDER", "") or config.active_provider,
        config.providers,
    )
    if actual_provider not in config.providers:
        raise RuntimeError(f"Unknown LLM provider for API: {actual_provider}")

    provider = config.providers[actual_provider]
    if provider.api_key_env and not os.getenv(provider.api_key_env, ""):
        raise RuntimeError(provider.missing_api_key_message())

    provider_timeout = float(provider.timeout_seconds or 60)
    runtime_config = llm_config or LLMConfig(
        temperature=0.2,
        max_tokens=12000 if provider.kind == "anthropic_compatible" else 2400,
        json_mode=True,
        timeout=max(provider_timeout, 300.0) if provider.kind == "anthropic_compatible" else provider_timeout,
        max_retries=2,
        retry_delay=1.0,
        disable_thinking=provider.kind == "anthropic_compatible",
    )
    return LLMClient(provider, config=runtime_config)


def _settings_payload(config_service: ConfigService | AppConfig | None) -> dict[str, object]:
    config = config_service if isinstance(config_service, AppConfig) else (config_service or ConfigService()).load()
    requested_provider = _canonical_provider_name(
        os.getenv("RESEARCHSENSEI_LLM_PROVIDER", "") or config.active_provider,
        config.providers,
    )
    provider = config.providers.get(requested_provider)
    if provider is None:
        return {
            "active_provider": _public_provider_name(requested_provider),
            "provider_key": requested_provider,
            "provider_display_name": _public_provider_name(requested_provider),
            "provider_kind": "",
            "base_url": "",
            "request_endpoint": "",
            "api_key_env": "",
            "model": "",
            "auth_header": "",
            "route_note": "",
            "model_options": [],
            "enable_env": "RESEARCHSENSEI_ENABLE_API_LLM",
            "llm_enabled": _env_truthy("RESEARCHSENSEI_ENABLE_API_LLM"),
            "api_key_configured": False,
            "provider_known": False,
        }

    return {
        "active_provider": _public_provider_name(provider.name),
        "provider_key": provider.name,
        "provider_display_name": _public_provider_name(provider.name),
        "provider_kind": provider.kind,
        "base_url": provider.base_url,
        "request_endpoint": _provider_request_endpoint(provider),
        "api_key_env": provider.api_key_env,
        "model": provider.model,
        "auth_header": provider.auth_header,
        "route_note": _provider_route_note(provider),
        "model_options": _model_options_for_provider(provider),
        "model_env": "RESEARCHSENSEI_LLM_MODEL",
        "enable_env": "RESEARCHSENSEI_ENABLE_API_LLM",
        "llm_enabled": _env_truthy("RESEARCHSENSEI_ENABLE_API_LLM"),
        "api_key_configured": bool(os.getenv(provider.api_key_env, "")) if provider.api_key_env else True,
        "provider_known": True,
    }


def _canonical_provider_name(name: str, providers: dict[str, object]) -> str:
    if name == "ccswitch" and "cc_switch" in providers:
        return "cc_switch"
    return name


def _public_provider_name(name: str) -> str:
    return "ccswitch" if name in {"cc_switch", "ccswitch"} else name


def _provider_request_endpoint(provider: object) -> str:
    kind = str(getattr(provider, "kind", "") or "")
    base_url = str(getattr(provider, "base_url", "") or "").rstrip("/")
    if not base_url:
        return ""
    return f"{base_url}/messages" if kind == "anthropic_compatible" else f"{base_url}/chat/completions"


def _provider_route_note(provider: object) -> str:
    name = str(getattr(provider, "name", "") or "")
    kind = str(getattr(provider, "kind", "") or "")
    if _public_provider_name(name) == "ccswitch" and kind == "anthropic_compatible":
        return "ccswitch 当前按 Claude/Anthropic 兼容通道请求 /v1/messages；实际上游 API 和路由由 ccswitch 的 Claude provider 配置决定。"
    if kind == "openai_compatible":
        return "当前提供方按 OpenAI 兼容通道请求 /chat/completions。"
    return "当前提供方按配置中的兼容通道发送请求。"


def _model_options_for_provider(provider: object) -> list[dict[str, str]]:
    current_model = str(getattr(provider, "model", "") or "").strip()
    options: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(model_id: object, *, label: object = "", source: str = "") -> None:
        model = str(model_id or "").strip()
        if not model or model in seen:
            return
        seen.add(model)
        options.append({
            "id": model,
            "label": str(label or model).strip() or model,
            "source": source,
        })

    add(current_model, source="当前配置")
    if _public_provider_name(str(getattr(provider, "name", "") or "")) == "ccswitch":
        for model in _ccswitch_current_provider_models():
            add(model, source="ccswitch 当前 provider")
        for model in _ccswitch_live_models(str(getattr(provider, "base_url", "") or "")):
            add(model.get("id"), label=model.get("label"), source="ccswitch 接口")
        for model in _ccswitch_recent_models():
            add(model, source="ccswitch 请求历史")
        for model_id, label in _ccswitch_pricing_models():
            add(model_id, label=label, source="ccswitch 模型库")
    return options[:80]


def _ccswitch_live_models(base_url: str) -> list[dict[str, str]]:
    if not base_url:
        return []
    try:
        with httpx.Client(timeout=1.2) as client:
            response = client.get(f"{base_url.rstrip('/')}/models")
            response.raise_for_status()
            payload = response.json()
    except Exception:
        return []
    raw_items = payload.get("models") or payload.get("data") or []
    if not isinstance(raw_items, list):
        return []
    models: list[dict[str, str]] = []
    for item in raw_items:
        if isinstance(item, str):
            models.append({"id": item, "label": item})
        elif isinstance(item, dict):
            model_id = item.get("id") or item.get("model") or item.get("name")
            if model_id:
                models.append({
                    "id": str(model_id),
                    "label": str(item.get("display_name") or item.get("label") or item.get("name") or model_id),
                })
    return models


def _ccswitch_db_path() -> Path:
    return Path.home() / ".cc-switch" / "cc-switch.db"


def _ccswitch_recent_models() -> list[str]:
    path = _ccswitch_db_path()
    if not path.exists():
        return []
    try:
        with sqlite3.connect(path) as connection:
            rows = connection.execute(
                """
                SELECT model_id
                FROM (
                    SELECT COALESCE(NULLIF(request_model, ''), NULLIF(model, '')) AS model_id,
                           MAX(created_at) AS last_seen
                    FROM proxy_request_logs
                    WHERE COALESCE(NULLIF(request_model, ''), NULLIF(model, '')) IS NOT NULL
                    GROUP BY model_id
                    ORDER BY last_seen DESC
                    LIMIT 30
                )
                """
            ).fetchall()
    except sqlite3.Error:
        return []
    return [str(row[0]) for row in rows if row and row[0]]


def _ccswitch_current_provider_models() -> list[str]:
    path = _ccswitch_db_path()
    if not path.exists():
        return []
    try:
        with sqlite3.connect(path) as connection:
            rows = connection.execute(
                """
                SELECT settings_config, meta
                FROM providers
                WHERE is_current = 1
                LIMIT 20
                """
            ).fetchall()
    except sqlite3.Error:
        return []
    found: list[str] = []
    pattern = re.compile(r"\b(?:claude|gpt|deepseek|gemini|minimax|qwen|kimi|glm|mistral|llama|doubao)[A-Za-z0-9_.:/-]*", re.I)
    for settings_config, meta in rows:
        text = f"{settings_config or ''} {meta or ''}"
        found.extend(match.group(0) for match in pattern.finditer(text) if _is_plausible_model_id(match.group(0)))
    return _unique_strings(found)


def _ccswitch_pricing_models() -> list[tuple[str, str]]:
    path = _ccswitch_db_path()
    if not path.exists():
        return []
    try:
        with sqlite3.connect(path) as connection:
            rows = connection.execute(
                """
                SELECT model_id, COALESCE(NULLIF(display_name, ''), model_id)
                FROM model_pricing
                ORDER BY model_id
                LIMIT 80
                """
            ).fetchall()
    except sqlite3.Error:
        return []
    return [(str(model_id), str(label)) for model_id, label in rows if model_id]


def _unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            result.append(text)
            seen.add(text)
    return result


def _is_plausible_model_id(value: str) -> bool:
    text = value.strip()
    lower = text.lower()
    if not text or "_" in text:
        return False
    if any(term in lower for term in ["plugin", "desktop", "traffic", "mode", "route"]):
        return False
    return bool(re.search(r"[\d.-]", text))


def _set_env_value(env_path: str | Path, key: str, value: str) -> None:
    path = Path(env_path)
    lines: list[str] = []
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    rendered = f'{key}="{escaped}"'
    updated = False
    result: list[str] = []
    for line in lines:
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            result.append(line)
            continue
        current_key = line.split("=", 1)[0].strip().lstrip("\ufeff")
        if current_key == key:
            result.append(rendered)
            updated = True
        else:
            result.append(line)
    if not updated:
        if result and result[-1].strip():
            result.append("")
        result.append(rendered)
    path.write_text("\n".join(result).rstrip() + "\n", encoding="utf-8")


def _env_truthy(name: str) -> bool:
    return os.getenv(name, "").lower() in {"1", "true", "yes", "on"}


def _direction_candidate_payload(payload: dict[str, object]) -> dict[str, object]:
    candidate = payload.get("candidate")
    if isinstance(candidate, dict):
        return candidate
    return payload


def _direction_handoff_inputs(candidate: dict[str, object]) -> tuple[str, str, str, str, str]:
    title = str(candidate.get("title") or "").strip()
    doi = str(candidate.get("doi") or "").strip()
    pdf_url = str(candidate.get("pdf_url") or "").strip()
    arxiv_id = str(candidate.get("arxiv_id") or "").strip()
    arxiv_url = str(candidate.get("arxiv_url") or "").strip()
    if arxiv_url and not SourceResolver.arxiv_to_pdf_url(arxiv_url=arxiv_url):
        arxiv_url = ""
    for key in ("url", "landing_url", "source_url"):
        value = str(candidate.get(key) or "").strip()
        if value and not arxiv_url and SourceResolver.arxiv_to_pdf_url(arxiv_url=value):
            arxiv_url = value
    # Choose one resolvable source. Direction candidates often carry both
    # arxiv_id and pdf_url; parse API intentionally accepts only one source.
    if arxiv_id:
        return title, "", "", arxiv_id, ""
    if arxiv_url:
        return title, "", "", "", arxiv_url
    if pdf_url:
        return title, "", pdf_url, "", ""
    if doi:
        return title, doi, "", "", ""
    return title, "", "", "", ""


def _direction_handoff_failure(job: JobRecord, source_status: SourceStatus) -> dict[str, object]:
    status = _direction_failure_status(source_status)
    return {
        "status": status,
        "handoff_status": status,
        "job_id": job.job_id,
        "message": _direction_failure_message(status, source_status),
        "source_status": source_status.model_dump(mode="json"),
    }


def _direction_failure_status(source_status: SourceStatus) -> str:
    warnings = set(source_status.warnings)
    if "NO_LEGAL_OA_FULLTEXT_FOUND" in warnings:
        return "NO_LEGAL_OA_FULLTEXT_FOUND"
    if "DOWNLOAD_FAILED" in warnings or source_status.status == "failed":
        return "PDF_DOWNLOAD_FAILED"
    if "INVALID_ARXIV_ID" in warnings or "UNSUPPORTED_SOURCE" in warnings:
        return "SOURCE_UNAVAILABLE"
    if "UNPAYWALL_EMAIL_MISSING" in warnings:
        return "NO_LEGAL_OA_FULLTEXT_FOUND"
    if "UNPAYWALL_NOT_FOUND" in warnings:
        return "NO_LEGAL_OA_FULLTEXT_FOUND"
    if "UNPAYWALL_NO_OA_LOCATION" in warnings:
        return "NO_LEGAL_OA_FULLTEXT_FOUND"
    if "UNPAYWALL_LANDING_ONLY" in warnings:
        return "NO_LEGAL_OA_FULLTEXT_FOUND"
    if source_status.status in {"rejected", "failed"}:
        return "SOURCE_UNAVAILABLE"
    return "BLOCKED"


def _direction_failure_message(status: str, source_status: SourceStatus) -> str:
    if status == "NO_LEGAL_OA_FULLTEXT_FOUND":
        return "No legal open-access full text found for this DOI. Try providing a PDF URL or arXiv ID."
    if status == "PDF_DOWNLOAD_FAILED":
        return "PDF download failed for the direction candidate."
    if status == "SOURCE_UNAVAILABLE":
        return "No supported full-text source is available for this direction candidate."
    return "; ".join(source_status.warnings) or "Direction candidate handoff was blocked."


def _resolve_doi_to_legal_pdf(
    fulltext_resolver: FullTextResolver,
    doi: str,
    title: str,
) -> tuple[str, str]:
    """Resolve DOI to a legal OA PDF URL via FullTextResolver.

    Returns (pdf_url, error). If pdf_url is non-empty, it is a legal OA PDF.
    If pdf_url is empty, error describes why resolution failed.
    """
    candidate = CandidatePaper(
        paper_id=doi,
        title=title,
        doi=doi,
    )
    resolved, _metrics = fulltext_resolver.resolve(candidate, download=False)
    if resolved.can_deep_read and resolved.selected_fulltext_url:
        source = resolved.selected_fulltext_source or ""
        # Only accept actual PDF sources, not landing pages or HTML
        if source.endswith("_pdf") or "pdf" in source.lower():
            return resolved.selected_fulltext_url, ""
        if resolved.selected_fulltext_url.lower().endswith(".pdf"):
            return resolved.selected_fulltext_url, ""
        # Landing page or HTML-only — not suitable for deep_read parse
        return "", "UNPAYWALL_LANDING_ONLY"
    reason = resolved.fulltext_failure_reason or "NO_LEGAL_OA_FULLTEXT_FOUND"
    return "", reason


def _doi_failure_message(error: str) -> str:
    if error == "UNPAYWALL_EMAIL_MISSING":
        return "Unpaywall email is not configured. Set UNPAYWALL_EMAIL or RESEARCHSENSEI_CONTACT_EMAIL."
    if error == "UNPAYWALL_NOT_FOUND":
        return "DOI was not found in Unpaywall. Try providing a PDF URL or arXiv ID."
    if error == "UNPAYWALL_NO_OA_LOCATION":
        return "No legal open-access location found for this DOI. Try providing a PDF URL or arXiv ID."
    if error == "UNPAYWALL_LANDING_ONLY":
        return "Only a landing page was found for this DOI, not a downloadable PDF. Try providing a PDF URL."
    if error == "DOI_MISSING":
        return "DOI is empty or invalid."
    return "No legal open-access full text found for this DOI. Try providing a PDF URL or arXiv ID."


def _job_understanding_status(job: JobRecord) -> dict[str, object]:
    artifact = _find_artifact(job, "understanding_status")
    if artifact is None:
        return {}
    content = _read_artifact_content(job, artifact.path)
    return content if isinstance(content, dict) else {}


def _degraded_missing_component_is_required(component: str, component_status: dict[str, object]) -> bool:
    status = str(component_status.get(component) or "").upper()
    if status:
        return status == "SUCCESS"
    return component in {"paper_card", "formula_cards"}


def _find_artifact(job: JobRecord, artifact_type: str) -> WorkspaceArtifact | None:
    for artifact in job.artifacts:
        if artifact.artifact_type == artifact_type:
            return artifact
    return None


def _paper_workspace_status(job: JobRecord, understanding_status: object) -> dict[str, object]:
    status_content = understanding_status if isinstance(understanding_status, dict) else {}
    source_status = _artifact_content_dict(job, "source_status")
    canonical_status = _artifact_content_dict(job, "canonical_status")
    claim_evidence = _artifact_content_dict(job, "claim_evidence")
    passage_index = _artifact_content_dict(job, "passage_index")
    quality_report = _artifact_content_dict(job, "quality_report")
    formula_origin, formula_ocr_status = _formula_status_summary(
        claim_evidence=claim_evidence,
        passage_index=passage_index,
    )
    component_status = status_content.get("component_status", {})
    source_type = str(source_status.get("source_type", "unknown"))
    source_resolved = source_status.get("status") == "resolved"
    m2_ready = canonical_status.get("m2_ready")
    return {
        "source_type": source_type,
        "source_status": source_status.get("status", "unknown"),
        "source_strategy": source_status.get("source_strategy", ""),
        "source_priority": source_status.get("source_priority", ""),
        "preferred_m2_input": source_status.get("preferred_m2_input", ""),
        "latex_source_available": source_status.get("latex_source_available", False),
        "latex_source_path": source_status.get("latex_source_path", ""),
        "fallback_used": source_status.get("fallback_used", ""),
        "verification_status": "verified" if source_resolved else "unverified",
        "pdf_metadata_check": source_status.get("pdf_metadata_check", "not_available"),
        "pdf_title_match": source_status.get("pdf_title_match", "not_available"),
        "can_enter_m2": bool(m2_ready) if m2_ready is not None else source_resolved,
        "source_confidence": 1.0 if source_resolved else 0.0,
        "canonicalization_status": canonical_status.get("canonicalization_status", "not_available"),
        "m2_ready": m2_ready,
        "degradation_reason": (
            canonical_status.get("degradation_reason")
            or "; ".join(source_status.get("degraded_flags", []))
            or status_content.get("blocking_reason", "")
        ),
        "formula_origin": formula_origin,
        "formula_ocr_status": formula_ocr_status,
        "evidence_status": _evidence_status(status_content, claim_evidence),
        "quality_status": _quality_status(quality_report),
        "component_status": component_status if isinstance(component_status, dict) else {},
        "allowed_downstream": status_content.get("allowed_downstream", {}),
    }


def _artifact_content_dict(job: JobRecord, artifact_type: str) -> dict[str, object]:
    artifact = _find_artifact(job, artifact_type)
    if artifact is None:
        return {}
    content = _read_artifact_content(job, artifact.path)
    return content if isinstance(content, dict) else {}


def _formula_status_summary(
    *,
    claim_evidence: dict[str, object],
    passage_index: dict[str, object],
) -> tuple[str, str]:
    origins: set[str] = set()
    ocr_statuses: set[str] = set()
    claims = claim_evidence.get("claims", [])
    if isinstance(claims, list):
        for claim in claims:
            if not isinstance(claim, dict):
                continue
            if claim.get("claim_type") != "FORMULA_CONTEXT":
                continue
            origin = str(claim.get("formula_origin") or "").strip()
            ocr_status = str(claim.get("formula_ocr_status") or "").strip()
            if origin:
                origins.add(origin)
            if ocr_status:
                ocr_statuses.add(ocr_status)

    passages = passage_index.get("passages", [])
    if isinstance(passages, list):
        for passage in passages:
            if not isinstance(passage, dict):
                continue
            for origin in passage.get("formula_origins", []) or []:
                if origin:
                    origins.add(str(origin))
            for ocr_status in passage.get("formula_ocr_statuses", []) or []:
                if ocr_status:
                    ocr_statuses.add(str(ocr_status))

    return (
        ", ".join(sorted(origins)) if origins else "not_applicable",
        ", ".join(sorted(ocr_statuses)) if ocr_statuses else "not_applicable",
    )


def _evidence_status(status_content: dict[str, object], claim_evidence: dict[str, object]) -> str:
    component_status = status_content.get("component_status", {})
    if isinstance(component_status, dict):
        evidence_component = component_status.get("evidence_pack")
        if evidence_component:
            return str(evidence_component)
    claims = claim_evidence.get("claims", [])
    if isinstance(claims, list) and claims:
        return "CLAIMS_AVAILABLE"
    return "UNKNOWN"


def _quality_status(quality_report: dict[str, object]) -> str:
    findings = quality_report.get("findings", [])
    if not isinstance(findings, list):
        return "unknown"
    effects = {str(f.get("effect", "")).upper() for f in findings if isinstance(f, dict)}
    if "BLOCK" in effects:
        return "blocked"
    if "WARNING" in effects:
        return "warning"
    return "pass" if quality_report else "unknown"


def _read_artifact_content(job: JobRecord, artifact_path: str) -> object:
    path = Path(artifact_path)
    run_dir = Path(job.run_dir)
    try:
        resolved_path = path.resolve()
        resolved_run_dir = run_dir.resolve()
        resolved_path.relative_to(resolved_run_dir)
    except ValueError as error:
        raise HTTPException(status_code=400, detail="Unsafe artifact path.") from error
    if not resolved_path.exists():
        raise HTTPException(status_code=404, detail="Artifact not found.")
    content = resolved_path.read_text(encoding="utf-8")
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return content


def _resolve_source(
    *,
    resolver: SourceResolver,
    run_dir: Path,
    title: str,
    doi: str,
    local_path: str,
    pdf_url: str,
    arxiv_id: str,
    arxiv_url: str,
) -> SourceStatus:
    inputs = [value for value in [doi, local_path, pdf_url, arxiv_id, arxiv_url] if value.strip()]
    if len(inputs) != 1:
        return SourceStatus(
            source_type="unknown",
            original_input=title.strip(),
            status="rejected",
            warnings=["UNSUPPORTED_SOURCE"],
            degraded_flags=["FULL_TEXT_MISSING", "ABSTRACT_ONLY", "FORMULA_UNAVAILABLE"],
        )
    if doi.strip():
        return SourceStatus(
            source_type="doi",
            original_input=doi.strip(),
            status="rejected",
            warnings=["NO_LEGAL_OA_FULLTEXT_FOUND"],
            degraded_flags=["FULL_TEXT_MISSING", "ABSTRACT_ONLY", "FORMULA_UNAVAILABLE"],
        )
    if local_path.strip():
        return resolver.resolve_local_path(local_path.strip(), run_dir=run_dir)
    if pdf_url.strip():
        return resolver.resolve_pdf_url(pdf_url.strip(), run_dir)
    if arxiv_id.strip():
        return resolver.resolve_arxiv_id(arxiv_id.strip(), run_dir)
    return resolver.resolve_arxiv_url(arxiv_url.strip(), run_dir)


def _request_source_identity(
    *,
    doi: str = "",
    local_path: str = "",
    pdf_url: str = "",
    arxiv_id: str = "",
    arxiv_url: str = "",
) -> str:
    if arxiv_id.strip():
        return f"arxiv:{_normalize_arxiv_id(arxiv_id)}"
    if arxiv_url.strip():
        extracted = _extract_arxiv_id(arxiv_url)
        return f"arxiv:{extracted}" if extracted else f"arxiv_url:{arxiv_url.strip()}"
    if doi.strip():
        return f"doi:{doi.strip().lower()}"
    if pdf_url.strip():
        return f"pdf_url:{pdf_url.strip()}"
    if local_path.strip():
        return _path_cache_identity(local_path.strip())
    return ""


def _source_status_identity(source_status: SourceStatus, fallback: str = "") -> str:
    if fallback:
        return fallback
    status = source_status.model_dump(mode="json")
    original = str(status.get("original_input") or "")
    resolved = str(status.get("resolved_path") or "")
    source_type = str(status.get("source_type") or "")
    if source_type in {"arxiv_id", "arxiv_pdf", "arxiv_source", "arxiv_url"} and original:
        extracted = _extract_arxiv_id(original)
        return f"arxiv:{extracted}" if extracted else f"{source_type}:{original}"
    if source_type == "doi" and original:
        return f"doi:{original.lower()}"
    if source_type == "pdf_url" and original:
        return f"pdf_url:{original}"
    if resolved:
        return _path_cache_identity(resolved)
    return ""


def _path_cache_identity(path_text: str) -> str:
    try:
        path = Path(path_text).resolve(strict=True)
    except OSError:
        return f"local_path:{path_text}"
    if path.is_file():
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return f"sha256:{digest.hexdigest()}"
    return f"local_path:{str(path).lower()}"


def _normalize_arxiv_id(value: str) -> str:
    return value.strip().lower().removeprefix("arxiv:").strip()


def _extract_arxiv_id(value: str) -> str:
    text = value.strip()
    match = re.search(r"arxiv\.org/(?:abs|pdf)/([^?#/]+)", text, flags=re.I)
    if match:
        return _normalize_arxiv_id(match.group(1).removesuffix(".pdf"))
    return _normalize_arxiv_id(text)


def _record_failed_source_job(
    workspace: WorkspaceStore,
    jobs: JobStore,
    job_id: str,
    run_dir: Path,
    source_status: SourceStatus,
) -> JobRecord:
    source_status_path = run_dir / "source_status.json"
    workspace.write_json(source_status_path, source_status)
    job = JobRecord(
        job_id=job_id,
        source_path="",
        run_dir=str(run_dir),
        status=JobStatus.FAILED,
        current_step="source_resolution_failed",
        error=";".join(source_status.warnings),
        warnings=[WarningItem(code=warning, message=warning) for warning in source_status.warnings],
        artifacts=[WorkspaceArtifact(artifact_type="source_status", path=str(source_status_path))],
    )
    return jobs.create(job)


def _existing_job_response(job: JobRecord, source_identity: str) -> dict[str, object]:
    """Return response for an existing SUCCEEDED job (skip re-ingestion)."""
    understanding_status = _job_understanding_status(job)
    response: dict[str, object] = {
        **_job_parse_response(job),
        "status": "JOB_REUSED",
        "handoff_status": "JOB_REUSED",
        "cache_hit": True,
        "source_identity": source_identity,
    }
    if understanding_status:
        response["understanding_status"] = understanding_status
        response["paper_workspace_status"] = _paper_workspace_status(job, understanding_status)
        response["final_status"] = understanding_status.get("status", "")
    return response


def _job_parse_response(job: JobRecord) -> dict[str, object]:
    return {
        "job_id": job.job_id,
        "status": job.status.value,
        "current_step": job.current_step,
        "source_identity": job.source_identity,
        "artifacts": [artifact.model_dump(mode="json") for artifact in job.artifacts],
        "warnings": [warning.model_dump(mode="json") for warning in job.warnings],
        "degraded": job.current_step == "ingestion_degraded",
    }


def _job_response(job: JobRecord) -> dict[str, object]:
    return {
        "job_id": job.job_id,
        "status": job.status.value,
        "source_path": job.source_path,
        "run_dir": job.run_dir,
        "source_identity": job.source_identity,
        "current_step": job.current_step,
        "error": job.error,
        "warnings": [warning.model_dump(mode="json") for warning in job.warnings],
        "artifacts": [artifact.model_dump(mode="json") for artifact in job.artifacts],
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }


def _artifact_response(job: JobRecord, artifact_path: str, artifact_type: str) -> dict[str, object]:
    content = _read_artifact_content(job, artifact_path)
    return {
        "artifact_type": artifact_type,
        "path": str(Path(artifact_path).resolve()),
        "content": content,
    }
