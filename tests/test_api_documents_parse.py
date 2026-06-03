from __future__ import annotations

from pathlib import Path

from starlette.testclient import TestClient

from researchsensei.web.app import create_app


def test_parse_upload_markdown_creates_job_and_artifact(tmp_path: Path) -> None:
    client = TestClient(create_app(workspace_root=tmp_path / "workspace"))

    response = client.post(
        "/api/v1/documents/parse",
        files={"file": ("paper.md", b"# Paper\n## Abstract\nWe study anomaly detection.", "text/markdown")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["job_id"]
    assert data["status"] == "succeeded"
    assert data["degraded"] is False
    assert data["artifacts"][0]["artifact_type"] == "ingestion"
    assert Path(data["artifacts"][0]["path"]).exists()
    assert isinstance(data["warnings"], list)


def test_parse_upload_markdown_generates_phase6_artifacts(tmp_path: Path) -> None:
    client = TestClient(create_app(workspace_root=tmp_path / "workspace"))

    response = client.post(
        "/api/v1/documents/parse",
        files={
            "file": (
                "paper.md",
                b"# Paper\n## Abstract\nWe study anomaly detection.\n\n## Method\nWe minimize L = L_rec.\n\n## Experiments\nTable 1 reports F1.",
                "text/markdown",
            )
        },
    )

    assert response.status_code == 200
    artifacts = response.json()["artifacts"]
    artifact_types = {artifact["artifact_type"] for artifact in artifacts}

    assert {"source_status", "ingestion", "evidence_index", "paper_skeleton", "paper_card", "formula_cards", "teaching_cards"} == artifact_types
    assert all(Path(artifact["path"]).exists() for artifact in artifacts)


def test_parse_upload_txt_creates_job_and_artifact(tmp_path: Path) -> None:
    client = TestClient(create_app(workspace_root=tmp_path / "workspace"))

    response = client.post(
        "/api/v1/documents/parse",
        files={"file": ("paper.txt", b"Abstract\nA tiny paper.", "text/plain")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["job_id"]
    assert data["status"] == "succeeded"
    assert data["artifacts"][0]["artifact_type"] == "ingestion"


def test_parse_upload_rejects_unsupported_file_type(tmp_path: Path) -> None:
    client = TestClient(create_app(workspace_root=tmp_path / "workspace"))

    response = client.post(
        "/api/v1/documents/parse",
        files={"file": ("paper.exe", b"not allowed", "application/octet-stream")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported file type: .exe"


def test_health_endpoint_is_preserved(tmp_path: Path) -> None:
    client = TestClient(create_app(workspace_root=tmp_path / "workspace"))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "researchsensei"}
