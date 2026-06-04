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
