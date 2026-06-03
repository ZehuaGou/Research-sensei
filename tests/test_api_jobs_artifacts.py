from __future__ import annotations

from pathlib import Path

from starlette.testclient import TestClient

from researchsensei.jobs import JobStore
from researchsensei.schemas import JobRecord, JobStatus, WorkspaceArtifact
from researchsensei.web.app import create_app


def _parse_sample(client: TestClient) -> str:
    response = client.post(
        "/api/v1/documents/parse",
        files={"file": ("paper.txt", b"Abstract\nA tiny paper.", "text/plain")},
    )
    assert response.status_code == 200
    return response.json()["job_id"]


def test_get_job_and_list_jobs(tmp_path: Path) -> None:
    client = TestClient(create_app(workspace_root=tmp_path / "workspace"))
    job_id = _parse_sample(client)

    job_response = client.get(f"/api/v1/jobs/{job_id}")
    list_response = client.get("/api/v1/jobs")

    assert job_response.status_code == 200
    assert job_response.json()["job_id"] == job_id
    assert list_response.status_code == 200
    assert any(job["job_id"] == job_id for job in list_response.json()["jobs"])


def test_get_job_artifacts_reads_json_content_safely(tmp_path: Path) -> None:
    client = TestClient(create_app(workspace_root=tmp_path / "workspace"))
    job_id = _parse_sample(client)

    response = client.get(f"/api/v1/jobs/{job_id}/artifacts")

    assert response.status_code == 200
    artifacts = response.json()["artifacts"]
    by_type = {artifact["artifact_type"]: artifact for artifact in artifacts}
    assert by_type["ingestion"]["content"]["paper_id"] == job_id
    assert by_type["evidence_index"]["content"]["paper_id"] == job_id
    assert by_type["paper_skeleton"]["content"]["paper_id"] == job_id
    assert by_type["paper_card"]["content"]["paper_id"] == job_id
    assert by_type["formula_cards"]["content"]["paper_id"] == job_id
    assert by_type["teaching_cards"]["content"]["paper_id"] == job_id


def test_get_missing_job_returns_404(tmp_path: Path) -> None:
    client = TestClient(create_app(workspace_root=tmp_path / "workspace"))

    response = client.get("/api/v1/jobs/missing")

    assert response.status_code == 404


def test_artifact_query_rejects_path_traversal(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    db_path = tmp_path / "jobs.sqlite3"
    run_dir = workspace_root / "runs" / "bad-job"
    run_dir.mkdir(parents=True)
    secret = tmp_path / "secret.json"
    secret.write_text('{"secret": true}', encoding="utf-8")
    jobs = JobStore(db_path)
    jobs.create(
        JobRecord(
            job_id="bad-job",
            status=JobStatus.SUCCEEDED,
            source_path=str(run_dir / "source.txt"),
            run_dir=str(run_dir),
            artifacts=[WorkspaceArtifact(artifact_type="leak", path=str(secret))],
        )
    )
    client = TestClient(create_app(workspace_root=workspace_root, job_db_path=db_path))

    response = client.get("/api/v1/jobs/bad-job/artifacts")

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsafe artifact path."
