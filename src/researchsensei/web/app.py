from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from researchsensei.ingestion import SinglePaperIngestionRunner
from researchsensei.jobs import JobStore
from researchsensei.schemas import JobRecord, JobStatus, SourceStatus, WarningItem, WorkspaceArtifact
from researchsensei.source_resolver import SourceResolver
from researchsensei.workspace import WorkspaceStore


SUPPORTED_PARSE_SUFFIXES = {".md", ".txt", ".pdf"}


def _debug_enabled() -> bool:
    return os.getenv("SENSEI_DEBUG", "").lower() in {"1", "true", "yes"}


def create_app(
    workspace_root: str | Path = "workspace",
    job_db_path: str | Path | None = None,
    allowed_local_roots: list[str | Path] | None = None,
    http_client: httpx.Client | None = None,
    max_download_bytes: int = 80 * 1024 * 1024,
) -> FastAPI:
    app = FastAPI(title="ResearchSensei", version="0.5.0")
    workspace = WorkspaceStore(workspace_root)
    jobs = JobStore(job_db_path or (workspace.root / "sensei.sqlite3"))
    runner = SinglePaperIngestionRunner(workspace=workspace, jobs=jobs)
    resolver = SourceResolver(
        allowed_roots=allowed_local_roots if allowed_local_roots is not None else [workspace.root],
        http_client=http_client,
        max_download_bytes=max_download_bytes,
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "researchsensei"}

    @app.post("/api/v1/documents/parse")
    async def parse_document(
        file: UploadFile | None = File(None),
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
            job = runner.run(incoming_path, job_id=job_id, source_status=source_status)
            return _job_parse_response(job)

        run_dir = workspace.new_run_dir(job_id)
        source_status = _resolve_source(
            resolver=resolver,
            run_dir=run_dir,
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

        job = runner.run(source_status.resolved_path, job_id=job_id, source_status=source_status)
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
        return {"job_id": job.job_id, "understanding_status": content}

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
                    "warnings": [w.model_dump(mode="json") for w in job.warnings],
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

        # SUCCESS or DEGRADED_STRUCTURAL: return available card artifacts
        card_types = ["paper_card", "formula_cards", "teaching_cards"]
        cards: dict[str, object] = {}
        missing: list[str] = []

        for card_type in card_types:
            artifact = _find_artifact(job, card_type)
            if artifact is not None:
                cards[card_type] = _read_artifact_content(job, artifact.path)
            else:
                missing.append(card_type)

        result: dict[str, object] = {
            "job_id": job.job_id,
            "status": status,
            "cards": cards,
        }

        if status == "DEGRADED_STRUCTURAL":
            result["degraded"] = True
            result["missing_components"] = missing

        return result

    return app


def _find_artifact(job: JobRecord, artifact_type: str) -> WorkspaceArtifact | None:
    for artifact in job.artifacts:
        if artifact.artifact_type == artifact_type:
            return artifact
    return None


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
    local_path: str,
    pdf_url: str,
    arxiv_id: str,
    arxiv_url: str,
) -> SourceStatus:
    inputs = [value for value in [local_path, pdf_url, arxiv_id, arxiv_url] if value.strip()]
    if len(inputs) != 1:
        return SourceStatus(
            source_type="unknown",
            original_input="",
            status="rejected",
            warnings=["UNSUPPORTED_SOURCE"],
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
