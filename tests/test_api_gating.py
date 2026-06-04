from __future__ import annotations

import json
import os
from pathlib import Path

from starlette.testclient import TestClient

from researchsensei.web.app import create_app


def _parse_sample(client: TestClient) -> str:
    response = client.post(
        "/api/v1/documents/parse",
        files={"file": ("paper.txt", b"Abstract\nA tiny paper.", "text/plain")},
    )
    assert response.status_code == 200
    return response.json()["job_id"]


# ---------------------------------------------------------------------------
# understanding_status endpoint
# ---------------------------------------------------------------------------


def test_understanding_status_endpoint_returns_status(tmp_path: Path) -> None:
    client = TestClient(create_app(workspace_root=tmp_path / "workspace"))
    job_id = _parse_sample(client)

    response = client.get(f"/api/v1/jobs/{job_id}/understanding_status")

    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job_id
    assert data["understanding_status"]["status"] == "BASELINE_ONLY"


def test_understanding_status_endpoint_missing_job_404(tmp_path: Path) -> None:
    client = TestClient(create_app(workspace_root=tmp_path / "workspace"))

    response = client.get("/api/v1/jobs/nonexistent/understanding_status")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# cards endpoint — BASELINE_ONLY
# ---------------------------------------------------------------------------


def test_cards_endpoint_baseline_only_returns_403(tmp_path: Path) -> None:
    client = TestClient(create_app(workspace_root=tmp_path / "workspace"))
    job_id = _parse_sample(client)

    response = client.get(f"/api/v1/jobs/{job_id}/cards")

    assert response.status_code == 403
    detail = response.json()["detail"]
    assert detail["status"] == "BASELINE_ONLY"
    assert "paper_card" not in detail
    assert "formula_cards" not in detail
    assert "teaching_cards" not in detail


# ---------------------------------------------------------------------------
# cards endpoint — MISSING understanding_status
# ---------------------------------------------------------------------------


def test_cards_endpoint_missing_understanding_status_404(tmp_path: Path) -> None:
    client = TestClient(create_app(workspace_root=tmp_path / "workspace"))

    response = client.get("/api/v1/jobs/nonexistent/cards")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# artifacts endpoint — debug gating
# ---------------------------------------------------------------------------


def test_artifacts_endpoint_forbidden_without_debug(tmp_path: Path) -> None:
    client = TestClient(create_app(workspace_root=tmp_path / "workspace"))
    job_id = _parse_sample(client)

    # Ensure SENSEI_DEBUG is not set
    env_patch = {"SENSEI_DEBUG": ""}
    old_env = {k: os.environ.get(k) for k in env_patch}
    for k, v in env_patch.items():
        os.environ[k] = v

    try:
        response = client.get(f"/api/v1/jobs/{job_id}/artifacts")
        assert response.status_code == 403
        detail = response.json()["detail"]
        assert "debug-only" in detail["message"]
    finally:
        for k, v in old_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_artifacts_endpoint_debug_mode_returns_all(tmp_path: Path) -> None:
    client = TestClient(create_app(workspace_root=tmp_path / "workspace"))
    job_id = _parse_sample(client)

    # Enable debug mode
    old_debug = os.environ.get("SENSEI_DEBUG")
    os.environ["SENSEI_DEBUG"] = "1"

    try:
        response = client.get(f"/api/v1/jobs/{job_id}/artifacts")
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job_id
        artifact_types = {a["artifact_type"] for a in data["artifacts"]}
        assert "understanding_status" in artifact_types
        assert "quality_report" in artifact_types
    finally:
        if old_debug is None:
            os.environ.pop("SENSEI_DEBUG", None)
        else:
            os.environ["SENSEI_DEBUG"] = old_debug


def test_artifacts_endpoint_without_debug_does_not_expose_quality_report(tmp_path: Path) -> None:
    client = TestClient(create_app(workspace_root=tmp_path / "workspace"))
    _parse_sample(client)

    # Without debug, should get 403
    response = client.get("/api/v1/jobs/test/artifacts")
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# artifacts endpoint — job not found still 404 in debug mode
# ---------------------------------------------------------------------------


def test_artifacts_endpoint_debug_mode_missing_job_404(tmp_path: Path) -> None:
    client = TestClient(create_app(workspace_root=tmp_path / "workspace"))

    old_debug = os.environ.get("SENSEI_DEBUG")
    os.environ["SENSEI_DEBUG"] = "1"

    try:
        response = client.get("/api/v1/jobs/nonexistent/artifacts")
        assert response.status_code == 404
    finally:
        if old_debug is None:
            os.environ.pop("SENSEI_DEBUG", None)
        else:
            os.environ["SENSEI_DEBUG"] = old_debug


# ---------------------------------------------------------------------------
# Existing parse API still works
# ---------------------------------------------------------------------------


def test_parse_api_still_works(tmp_path: Path) -> None:
    client = TestClient(create_app(workspace_root=tmp_path / "workspace"))

    response = client.post(
        "/api/v1/documents/parse",
        files={"file": ("paper.md", b"# Paper\n## Abstract\nWe study anomaly detection.", "text/markdown")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "succeeded"


def test_health_endpoint_still_works(tmp_path: Path) -> None:
    client = TestClient(create_app(workspace_root=tmp_path / "workspace"))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "researchsensei"}


# ---------------------------------------------------------------------------
# Helpers for constructing test jobs
# ---------------------------------------------------------------------------

from researchsensei.jobs import JobStore
from researchsensei.schemas import JobRecord, JobStatus, WorkspaceArtifact
from researchsensei.workspace import WorkspaceStore


def _write_json(workspace: WorkspaceStore, run_dir: Path, name: str, data: dict) -> Path:
    path = run_dir / name
    workspace.write_json(path, data)
    return path


def _create_job_with_cards(
    tmp_path: Path,
    job_id: str,
    status: str,
    *,
    include_paper_card: bool = True,
    include_formula_cards: bool = True,
    include_teaching_cards: bool = True,
) -> TestClient:
    """Create a test app with a job that has specific card artifacts."""
    workspace_root = tmp_path / "workspace"
    db_path = tmp_path / "jobs.sqlite3"
    workspace = WorkspaceStore(workspace_root)
    jobs = JobStore(db_path)

    run_dir = workspace.new_run_dir(job_id)

    # Always write understanding_status
    us_path = _write_json(workspace, run_dir, "understanding_status.json", {
        "paper_id": job_id,
        "status": status,
        "blocking_reason": "",
        "allowed_for_user_display": status in ("SUCCESS", "DEGRADED_STRUCTURAL"),
        "allowed_downstream": {"reading_display": True},
        "component_status": {},
    })

    artifacts = [WorkspaceArtifact(artifact_type="understanding_status", path=str(us_path))]

    if include_paper_card:
        p = _write_json(workspace, run_dir, "paper_card.json", {"paper_id": job_id, "title": "Test"})
        artifacts.append(WorkspaceArtifact(artifact_type="paper_card", path=str(p)))

    if include_formula_cards:
        f = _write_json(workspace, run_dir, "formula_cards.json", {"paper_id": job_id, "formula_cards": []})
        artifacts.append(WorkspaceArtifact(artifact_type="formula_cards", path=str(f)))

    if include_teaching_cards:
        t = _write_json(workspace, run_dir, "teaching_cards.json", {"paper_id": job_id, "teaching_cards": []})
        artifacts.append(WorkspaceArtifact(artifact_type="teaching_cards", path=str(t)))

    jobs.create(JobRecord(
        job_id=job_id,
        source_path="",
        run_dir=str(run_dir),
        status=JobStatus.SUCCEEDED,
        current_step="ingestion_completed",
        artifacts=artifacts,
    ))

    return TestClient(create_app(workspace_root=workspace_root, job_db_path=db_path))


# ---------------------------------------------------------------------------
# cards endpoint — SUCCESS
# ---------------------------------------------------------------------------


def test_cards_endpoint_success_returns_all_cards(tmp_path: Path) -> None:
    client = _create_job_with_cards(tmp_path, "job-success", "SUCCESS")

    response = client.get("/api/v1/jobs/job-success/cards")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert "paper_card" in data["cards"]
    assert "formula_cards" in data["cards"]
    assert "teaching_cards" in data["cards"]


def test_cards_endpoint_success_missing_card_returns_409(tmp_path: Path) -> None:
    client = _create_job_with_cards(
        tmp_path, "job-success-missing", "SUCCESS",
        include_teaching_cards=False,
    )

    response = client.get("/api/v1/jobs/job-success-missing/cards")

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["status"] == "SUCCESS"
    assert "teaching_cards" in detail["missing_components"]


# ---------------------------------------------------------------------------
# cards endpoint — DEGRADED_STRUCTURAL
# ---------------------------------------------------------------------------


def test_cards_endpoint_degraded_omits_failed_teaching(tmp_path: Path) -> None:
    client = _create_job_with_cards(
        tmp_path, "job-degraded", "DEGRADED_STRUCTURAL",
        include_teaching_cards=False,
    )

    response = client.get("/api/v1/jobs/job-degraded/cards")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "DEGRADED_STRUCTURAL"
    assert data["degraded"] is True
    assert "paper_card" in data["cards"]
    assert "formula_cards" in data["cards"]
    assert "teaching_cards" not in data["cards"]
    assert "teaching_cards" in data["missing_components"]


def test_cards_endpoint_degraded_missing_required_card_returns_409(tmp_path: Path) -> None:
    client = _create_job_with_cards(
        tmp_path, "job-degraded-bad", "DEGRADED_STRUCTURAL",
        include_paper_card=False,
    )

    response = client.get("/api/v1/jobs/job-degraded-bad/cards")

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["status"] == "DEGRADED_STRUCTURAL"
    assert "paper_card" in detail["missing_components"]


# ---------------------------------------------------------------------------
# cards endpoint — BLOCKED
# ---------------------------------------------------------------------------


def test_cards_endpoint_blocked_returns_403(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    db_path = tmp_path / "jobs.sqlite3"
    workspace = WorkspaceStore(workspace_root)
    jobs = JobStore(db_path)

    run_dir = workspace.new_run_dir("job-blocked")
    us_path = _write_json(workspace, run_dir, "understanding_status.json", {
        "paper_id": "job-blocked",
        "status": "BLOCKED_UNDERSTANDING",
        "blocking_reason": "LLM_FAILED",
        "allowed_for_user_display": False,
        "allowed_downstream": {},
        "component_status": {},
    })

    jobs.create(JobRecord(
        job_id="job-blocked",
        source_path="",
        run_dir=str(run_dir),
        status=JobStatus.SUCCEEDED,
        current_step="ingestion_completed",
        artifacts=[WorkspaceArtifact(artifact_type="understanding_status", path=str(us_path))],
    ))

    client = TestClient(create_app(workspace_root=workspace_root, job_db_path=db_path))

    response = client.get("/api/v1/jobs/job-blocked/cards")

    assert response.status_code == 403
    detail = response.json()["detail"]
    assert detail["status"] == "BLOCKED_UNDERSTANDING"
    assert detail["blocking_reason"] == "LLM_FAILED"
