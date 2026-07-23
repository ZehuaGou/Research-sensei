from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from researchsensei.schemas import JobRecord, JobStatus, WorkspaceArtifact
from researchsensei.web.app import create_app


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    with TestClient(create_app(workspace_root=tmp_path / "workspace")) as value:
        yield value


def _write_json(path: Path, value: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    return path


def _create_learning_job(
    client: TestClient, tmp_path: Path, job_id: str = "learning-paper"
) -> JobRecord:
    run_dir = tmp_path / "workspace" / "runs" / job_id
    status_path = _write_json(
        run_dir / "understanding_status.json",
        {
            "status": "SUCCESS",
            "allowed_for_user_display": True,
            "allowed_downstream": {
                "reading_display": True,
                "advisor_questions": True,
                "learning_drills": True,
            },
        },
    )
    paper_card_path = _write_json(
        run_dir / "paper_card.json",
        {
            "paper_id": job_id,
            "title": "A Test Paper",
            "problem": {
                "text": "Existing methods cannot model temporal dependencies.",
                "evidence_ref": "passage:problem",
            },
            "core_idea": {
                "text": "The paper combines a temporal encoder with causal discovery.",
                "evidence_ref": "passage:method",
            },
            "method_overview": {
                "text": "The encoder produces representations before graph discovery.",
                "evidence_ref": "passage:pipeline",
            },
            "experiment_summary": {
                "text": "The method improves root-cause ranking on two datasets.",
                "evidence_ref": "passage:experiment",
            },
            "limitations": {
                "text": "The study only evaluates two datasets.",
                "evidence_ref": "passage:limitation",
            },
        },
    )
    teaching_path = _write_json(
        run_dir / "teaching_cards.json",
        {
            "teaching_cards": [
                {
                    "card_id": "teach-1",
                    "title": "Temporal encoder",
                    "target_type": "concept",
                    "human_explanation": "It summarizes temporal context.",
                    "paper_role_explanation": "It feeds the causal discovery stage.",
                    "evidence_refs": ["passage:pipeline"],
                }
            ]
        },
    )
    job = JobRecord(
        job_id=job_id,
        source_path=str(tmp_path / "paper.pdf"),
        run_dir=str(run_dir),
        status=JobStatus.SUCCEEDED,
        artifacts=[
            WorkspaceArtifact(artifact_type="understanding_status", path=str(status_path)),
            WorkspaceArtifact(artifact_type="paper_card", path=str(paper_card_path)),
            WorkspaceArtifact(artifact_type="teaching_cards", path=str(teaching_path)),
        ],
    )
    client.app.state.jobs.create(job)
    return job


def test_learning_session_persists_attempt_and_fsrs_schedule(
    client: TestClient,
    tmp_path: Path,
) -> None:
    job = _create_learning_job(client, tmp_path)

    imported = client.post(f"/api/v1/jobs/{job.job_id}/learning/import")
    started = client.post(
        f"/api/v1/jobs/{job.job_id}/learning/sessions",
        json={"count": 2},
    )

    assert imported.status_code == 200
    assert imported.json()["imported_count"] == 6
    assert started.status_code == 200
    session = started.json()
    assert session["status"] == "ACTIVE"
    assert session["total"] == 2
    assert session["current"]["question"]
    assert session["current"]["evidence_refs"]

    active = client.get(f"/api/v1/jobs/{job.job_id}/learning/active-session")
    assert active.status_code == 200
    assert active.json()["session"]["session_id"] == session["session_id"]

    answered = client.post(
        f"/api/v1/jobs/{job.job_id}/learning/sessions/{session['session_id']}/answer",
        json={
            "user_answer": (
                "The temporal encoder summarizes dependencies, then its representation "
                "is used by causal discovery to rank root causes."
            )
        },
    )

    assert answered.status_code == 200
    result = answered.json()
    assert result["attempt"]["score"] >= 0
    assert result["attempt"]["next_due_at"] > result["attempt"]["reviewed_at"]
    assert result["session"]["completed"] == 1

    overview = client.get(f"/api/v1/jobs/{job.job_id}/learning")
    assert overview.status_code == 200
    body = overview.json()
    assert body["total_items"] == 6
    assert body["reviewed_today"] == 1
    assert body["recent_attempts"][0]["user_answer"].startswith("The temporal encoder")


def test_learning_requires_learning_drill_gate(client: TestClient, tmp_path: Path) -> None:
    job = _create_learning_job(client, tmp_path, job_id="blocked-learning")
    status_path = Path(job.run_dir) / "understanding_status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    status["allowed_downstream"]["learning_drills"] = False
    _write_json(status_path, status)

    response = client.post(f"/api/v1/jobs/{job.job_id}/learning/import")

    assert response.status_code == 403
    assert response.json()["detail"]["gate"] == "allowed_downstream.learning_drills"


def test_learning_requests_reject_unknown_fields(client: TestClient) -> None:
    response = client.post(
        "/api/v1/jobs/missing/learning/sessions",
        json={"count": 5, "extra": True},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
