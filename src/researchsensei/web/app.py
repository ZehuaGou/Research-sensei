from __future__ import annotations

import json
import os
import re
import sqlite3
import uuid
from pathlib import Path

import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from researchsensei.acquisition.fulltext_resolver import FullTextResolver
from researchsensei.core.config import ConfigService
from researchsensei.direction import DirectionExplorationService, SeedExpansionService
from researchsensei.ingestion import SinglePaperIngestionRunner
from researchsensei.jobs import JobStore
from researchsensei.library import PaperLibraryStore
from researchsensei.llm.client import LLMClient
from researchsensei.llm.types import LLMConfig
from researchsensei.m4.service import M4InteractionService, M4_MEMORY_FILENAME
from researchsensei.query import QueryPlanner
from researchsensei.schemas import CandidatePaper, InteractiveAnswer, JobRecord, JobStatus, SourceStatus, WarningItem, WorkspaceArtifact
from researchsensei.source_resolver import PaperSourceResolver, SourceResolver
from researchsensei.workspace import WorkspaceStore


SUPPORTED_PARSE_SUFFIXES = {".md", ".txt", ".pdf", ".tex"}


class SettingsUpdate(BaseModel):
    model: str | None = None


def _debug_enabled() -> bool:
    return os.getenv("SENSEI_DEBUG", "").lower() in {"1", "true", "yes"}


def create_app(
    workspace_root: str | Path = "workspace",
    job_db_path: str | Path | None = None,
    allowed_local_roots: list[str | Path] | None = None,
    http_client: httpx.Client | None = None,
    max_download_bytes: int = 80 * 1024 * 1024,
    llm_client: LLMClient | None = None,
    enable_configured_llm: bool | None = None,
    llm_provider: str = "",
    llm_config: LLMConfig | None = None,
    config_service: ConfigService | None = None,
    direction_service: DirectionExplorationService | None = None,
    seed_expansion_service: SeedExpansionService | None = None,
) -> FastAPI:
    app = FastAPI(title="ResearchSensei", version="0.5.0")
    workspace = WorkspaceStore(workspace_root)
    db_path = Path(job_db_path or (workspace.root / "sensei.sqlite3"))
    jobs = JobStore(db_path)
    paper_library = PaperLibraryStore(db_path)
    resolved_llm_client = llm_client or _configured_llm_client(
        enable_configured_llm=enable_configured_llm,
        provider_name=llm_provider,
        llm_config=llm_config,
        config_service=config_service,
    )
    runner = SinglePaperIngestionRunner(
        workspace=workspace,
        jobs=jobs,
        llm_client=resolved_llm_client,
    )
    resolver = SourceResolver(
        allowed_roots=allowed_local_roots if allowed_local_roots is not None else [workspace.root],
        http_client=http_client,
        max_download_bytes=max_download_bytes,
    )
    fulltext_resolver = FullTextResolver(
        http_client=http_client,
        max_download_bytes=max_download_bytes,
    )
    m1_source_dir = workspace.root / "m1_searches"
    paper_library.import_manifests(m1_source_dir)
    resolved_direction_service = direction_service or DirectionExplorationService(
        source_resolver=PaperSourceResolver(
            network_enabled=True,
            download_dir=m1_source_dir,
            http_client=http_client,
            max_download_bytes=max_download_bytes,
            paper_library=paper_library,
        ),
        fulltext_resolver=fulltext_resolver,
        source_download_dir=m1_source_dir,
        paper_library=paper_library,
        query_planner=QueryPlanner(resolved_llm_client) if resolved_llm_client is not None else None,
    )
    resolved_seed_expansion_service = seed_expansion_service or SeedExpansionService()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "researchsensei"}

    @app.get("/api/v1/settings")
    def get_settings() -> dict[str, object]:
        return _settings_payload(config_service)

    @app.patch("/api/v1/settings")
    def update_settings(payload: SettingsUpdate) -> dict[str, object]:
        model = (payload.model or "").strip()
        if not model:
            raise HTTPException(status_code=422, detail="model must not be empty")
        if len(model) > 160:
            raise HTTPException(status_code=422, detail="model is too long")
        service = config_service or ConfigService()
        _set_env_value(service.env_path, "RESEARCHSENSEI_LLM_MODEL", model)
        os.environ["RESEARCHSENSEI_LLM_MODEL"] = model
        if resolved_llm_client is not None:
            resolved_llm_client.provider = resolved_llm_client.provider.model_copy(update={"model": model})
        return _settings_payload(service)

    @app.post("/api/v1/settings/test")
    def test_settings() -> dict[str, object]:
        payload = _settings_payload(config_service)
        active_provider = str(payload.get("active_provider") or "")
        if not active_provider:
            return {
                **payload,
                "ok": False,
                "message": "No model provider is configured.",
            }
        if not payload.get("llm_enabled"):
            return {
                **payload,
                "ok": False,
                "message": "API LLM is disabled. Set RESEARCHSENSEI_ENABLE_API_LLM=1 to enable live calls.",
            }
        if not payload.get("api_key_configured"):
            return {
                **payload,
                "ok": False,
                "message": f"Missing API key. Set environment variable {payload.get('api_key_env')}.",
            }
        return {
            **payload,
            "ok": True,
            "message": "Provider configuration is ready. No live LLM call was made.",
        }

    @app.post("/api/v1/documents/parse")
    async def parse_document(
        file: UploadFile | None = File(None),
        title: str = Form(""),
        doi: str = Form(""),
        local_path: str = Form(""),
        pdf_url: str = Form(""),
        arxiv_id: str = Form(""),
        arxiv_url: str = Form(""),
    ) -> dict[str, object]:
        job_id = uuid.uuid4().hex[:12]
        if file is not None and file.filename:
            suffix = Path(file.filename).suffix.lower()
            if suffix not in SUPPORTED_PARSE_SUFFIXES:
                raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix or '<none>'}")
            incoming_dir = workspace.root / "incoming"
            incoming_dir.mkdir(parents=True, exist_ok=True)
            incoming_path = incoming_dir / f"{uuid.uuid4().hex[:12]}{suffix}"
            incoming_path.write_bytes(await file.read())
            source_status = resolver.resolve_upload(
                incoming_path,
                original_filename=file.filename,
                content_type=file.content_type or "",
            )
            source_identity = (arxiv_id or doi or "").strip()
            job = await run_in_threadpool(
                runner.run,
                source_status.resolved_path,
                job_id=job_id,
                source_status=source_status,
                source_identity=source_identity,
            )
            return _job_parse_response(job)

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

        job = await run_in_threadpool(
            runner.run,
            source_status.resolved_path,
            job_id=job_id,
            source_status=source_status,
        )
        return _job_parse_response(job)

    @app.get("/api/v1/jobs")
    def list_jobs(limit: int = 20) -> dict[str, object]:
        return {"jobs": [_job_response(job) for job in jobs.list_recent(limit=limit)]}

    @app.get("/api/v1/jobs/{job_id}")
    def get_job(job_id: str) -> dict[str, object]:
        try:
            return _job_response(jobs.get(job_id))
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Job not found.") from error

    @app.delete("/api/v1/jobs/{job_id}")
    def delete_job(job_id: str) -> dict[str, object]:
        try:
            jobs.delete(job_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Job not found.") from error
        return {"status": "DELETED", "job_id": job_id}

    @app.get("/api/v1/library/papers")
    def list_library_papers(
        query: str = "",
        limit: int = 100,
        include_deleted: bool = False,
    ) -> dict[str, object]:
        return {
            "papers": paper_library.list_papers(
                query=query,
                limit=limit,
                include_deleted=include_deleted,
            )
        }

    @app.get("/api/v1/library/search_runs")
    def list_library_search_runs(limit: int = 50) -> dict[str, object]:
        return {"search_runs": paper_library.list_search_runs(limit=limit)}

    @app.delete("/api/v1/library/papers/{paper_id}")
    def delete_library_paper(paper_id: str, remove_file: bool = True) -> dict[str, object]:
        if not paper_library.delete_paper(paper_id, remove_file=remove_file):
            raise HTTPException(status_code=404, detail="Paper not found.")
        return {"status": "DELETED", "paper_id": paper_id, "remove_file": remove_file}

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

    @app.post("/api/v1/jobs/{job_id}/selection/explain")
    def explain_selection(job_id: str, payload: dict[str, object]) -> dict[str, object]:
        job = _get_job_or_404(jobs, job_id)
        service = _m4_service_for_job(job, llm_client=resolved_llm_client)
        result = service.explain_selection(payload)
        _sync_m4_memory_artifact(jobs, job, service.memory_path)
        return result.model_dump(mode="json")

    @app.post("/api/v1/jobs/{job_id}/formula/explain")
    def explain_formula(job_id: str, payload: dict[str, object]) -> dict[str, object]:
        job = _get_job_or_404(jobs, job_id)
        service = _m4_service_for_job(job, llm_client=resolved_llm_client)
        result = service.explain_formula(payload)
        _sync_m4_memory_artifact(jobs, job, service.memory_path)
        return result.model_dump(mode="json")

    @app.post("/api/v1/jobs/{job_id}/ask")
    def ask_job(job_id: str, payload: dict[str, object]) -> dict[str, object]:
        job = _get_job_or_404(jobs, job_id)
        runtime_answer = _runtime_self_answer(
            payload,
            llm_client=resolved_llm_client,
            config_service=config_service,
        )
        if runtime_answer is not None:
            return runtime_answer.model_dump(mode="json")
        service = _m4_service_for_job(job, llm_client=resolved_llm_client)
        result = service.answer_question(payload)
        _sync_m4_memory_artifact(jobs, job, service.memory_path)
        return result.model_dump(mode="json")

    @app.post("/api/v1/jobs/{job_id}/advisor/question")
    def advisor_question(job_id: str, payload: dict[str, object]) -> dict[str, object]:
        job = _get_job_or_404(jobs, job_id)
        service = _m4_service_for_job(job, llm_client=resolved_llm_client, required_gate="advisor_questions")
        result = service.advisor_question(payload)
        _sync_m4_memory_artifact(jobs, job, service.memory_path)
        return result.model_dump(mode="json")

    @app.post("/api/v1/jobs/{job_id}/advisor/evaluate")
    def advisor_evaluate(job_id: str, payload: dict[str, object]) -> dict[str, object]:
        job = _get_job_or_404(jobs, job_id)
        service = _m4_service_for_job(job, llm_client=resolved_llm_client, required_gate="advisor_questions")
        result = service.advisor_evaluate(payload)
        _sync_m4_memory_artifact(jobs, job, service.memory_path)
        return result.model_dump(mode="json")

    @app.get("/api/v1/jobs/{job_id}/memory")
    def get_memory(job_id: str) -> dict[str, object]:
        job = _get_job_or_404(jobs, job_id)
        service = _m4_service_for_job(job, llm_client=resolved_llm_client)
        return service.get_memory().model_dump(mode="json")

    @app.delete("/api/v1/jobs/{job_id}/memory")
    def clear_memory(job_id: str) -> dict[str, object]:
        job = _get_job_or_404(jobs, job_id)
        service = _m4_service_for_job(job, llm_client=resolved_llm_client)
        bundle = service.clear_memory()
        _sync_m4_memory_artifact(jobs, job, service.memory_path)
        return {"status": "CLEARED", **bundle.model_dump(mode="json")}

    @app.post("/api/v1/directions/search")
    def search_direction(payload: dict[str, object]) -> dict[str, object]:
        query = str(payload.get("query") or "")
        bundle = resolved_direction_service.explore(query)
        response = bundle.model_dump(mode="json")
        response["papers"] = response.get("candidate_cards", [])
        return response

    @app.post("/api/v1/directions/deep_read")
    async def direction_deep_read(payload: dict[str, object]) -> dict[str, object]:
        candidate = _direction_candidate_payload(payload)
        title, doi, pdf_url, arxiv_id, arxiv_url = _direction_handoff_inputs(candidate)

        # Compute source identity for job dedup: arxiv_id first, then doi
        source_identity = (arxiv_id or doi or "").strip()

        # Check for existing SUCCEEDED job for the same paper
        if source_identity:
            existing = jobs.find_by_source_identity(source_identity)
            if existing is not None:
                return _existing_job_response(existing, source_identity)

        job_id = uuid.uuid4().hex[:12]
        run_dir = workspace.new_run_dir(job_id)

        # DOI-only path: resolve DOI -> legal OA PDF via FullTextResolver
        if doi and not pdf_url and not arxiv_id and not arxiv_url:
            resolved_pdf_url, resolve_error = _resolve_doi_to_legal_pdf(
                fulltext_resolver, doi, title,
            )
            if resolved_pdf_url:
                pdf_url = resolved_pdf_url
                doi = ""
            else:
                job = _record_failed_source_job(
                    workspace, jobs, job_id, run_dir,
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
                        "message": _doi_failure_message(resolve_error),
                        "doi": doi,
                    },
                )

        source_status = _resolve_source(
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
            job = _record_failed_source_job(workspace, jobs, job_id, run_dir, source_status)
            raise HTTPException(
                status_code=400,
                detail=_direction_handoff_failure(job, source_status),
            )

        job = await run_in_threadpool(
            runner.run,
            source_status.resolved_path,
            job_id=job_id,
            source_status=source_status,
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

        understanding_status = _job_understanding_status(job)
        response = {
            **_job_parse_response(job),
            "status": "JOB_CREATED",
            "handoff_status": "JOB_CREATED",
            "source_status": source_status.model_dump(mode="json"),
        }
        if understanding_status:
            response["understanding_status"] = understanding_status
            response["paper_workspace_status"] = _paper_workspace_status(job, understanding_status)
            response["final_status"] = understanding_status.get("status", "")
        return response

    @app.post("/api/v1/directions/seed_expansion")
    def seed_expansion(payload: dict[str, object]) -> dict[str, object]:
        seed_payload = payload.get("seed") or payload.get("candidate") or payload
        if not isinstance(seed_payload, dict):
            raise HTTPException(
                status_code=400,
                detail={"status": "BLOCKED", "message": "Seed payload must be an object."},
            )
        bundle = resolved_seed_expansion_service.expand(seed_payload)
        return bundle.model_dump(mode="json")

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
    config_service: ConfigService | None,
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
    config_service: ConfigService | None,
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
) -> LLMClient | None:
    """Build the real API LLM client only when explicitly enabled."""
    service = config_service or ConfigService()
    config = service.load()
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


def _settings_payload(config_service: ConfigService | None) -> dict[str, object]:
    service = config_service or ConfigService()
    config = service.load()
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
