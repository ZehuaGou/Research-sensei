from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from researchsensei.acquisition.fulltext_resolver import FullTextResolver
from researchsensei.core.config import ConfigService
from researchsensei.direction import DirectionExplorationService, SeedExpansionService
from researchsensei.ingestion import SinglePaperIngestionRunner
from researchsensei.jobs import JobStore
from researchsensei.llm.client import LLMClient
from researchsensei.llm.types import LLMConfig
from researchsensei.schemas import CandidatePaper, JobRecord, JobStatus, SourceStatus, WarningItem, WorkspaceArtifact
from researchsensei.source_resolver import SourceResolver
from researchsensei.workspace import WorkspaceStore


SUPPORTED_PARSE_SUFFIXES = {".md", ".txt", ".pdf", ".tex"}


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
    jobs = JobStore(job_db_path or (workspace.root / "sensei.sqlite3"))
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
    resolved_direction_service = direction_service or DirectionExplorationService()
    resolved_seed_expansion_service = seed_expansion_service or SeedExpansionService()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "researchsensei"}

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
            job = await run_in_threadpool(
                runner.run,
                incoming_path,
                job_id=job_id,
                source_status=source_status,
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

    actual_provider = provider_name or os.getenv("RESEARCHSENSEI_LLM_PROVIDER", "") or config.active_provider
    if actual_provider not in config.providers:
        raise RuntimeError(f"Unknown LLM provider for API: {actual_provider}")

    provider = config.providers[actual_provider]
    if provider.api_key_env and not os.getenv(provider.api_key_env, ""):
        raise RuntimeError(provider.missing_api_key_message())

    runtime_config = llm_config or LLMConfig(
        temperature=0.2,
        max_tokens=2400,
        json_mode=True,
        timeout=float(provider.timeout_seconds or 60),
        max_retries=0,
    )
    return LLMClient(provider, config=runtime_config)


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
    if "DOI_NOT_IMPLEMENTED" in warnings:
        return "DOI_NOT_IMPLEMENTED"
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
    if status == "DOI_NOT_IMPLEMENTED":
        return "DOI handoff is not implemented. Use an arXiv ID, arXiv URL, or PDF URL."
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
            warnings=["DOI_NOT_IMPLEMENTED"],
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
