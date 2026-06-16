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


def _parse_method_sample(client: TestClient) -> str:
    response = client.post(
        "/api/v1/documents/parse",
        files={
            "file": (
                "method_paper.md",
                (
                    b"# Demo Paper\n\n"
                    b"## Abstract\n"
                    b"We propose a compact model for anomaly detection.\n\n"
                    b"## Method\n"
                    b"Our method introduces an attention architecture and reconstruction mechanism.\n\n"
                    b"## Experiments\n"
                    b"We evaluate the model on benchmark data and report stable performance.\n"
                ),
                "text/markdown",
            )
        },
    )
    assert response.status_code == 200
    return response.json()["job_id"]


def _parse_raw_formula_sample(client: TestClient) -> str:
    response = client.post(
        "/api/v1/documents/parse",
        files={
            "file": (
                "raw_formula_paper.md",
                (
                    b"# Demo Paper\n\n"
                    b"## Abstract\n"
                    b"We propose a compact model for anomaly detection.\n\n"
                    b"## Method\n"
                    b"Our method minimizes L = L_rec + lambda L_graph to train the model.\n\n"
                    b"## Experiments\n"
                    b"We evaluate the model on benchmark data and report stable performance.\n"
                ),
                "text/markdown",
            )
        },
    )
    assert response.status_code == 200
    return response.json()["job_id"]


class ScriptedApiLLM:
    def __init__(self, *, fail_paper: bool = False, fail_teaching: bool = False) -> None:
        self.fail_paper = fail_paper
        self.fail_teaching = fail_teaching
        self.calls = 0

    async def chat_json(self, messages, *, config=None):
        self.calls += 1
        text = "\n".join(message.content for message in messages)
        if "Formula evidence batch" in text:
            return {"formula_cards": []}
        if "teaching_cards" in text:
            if self.fail_teaching:
                raise RuntimeError("teaching failed")
            ref = _first_allowed_ref(text)
            return {
                "teaching_cards": [
                    {
                        "target_type": "concept",
                        "title": "Attention method",
                        "human_explanation": "The method introduces an attention architecture.",
                        "analogy_explanation": "It selects important input parts before reconstruction.",
                        "minimal_formula_explanation": "INSUFFICIENT_EVIDENCE",
                        "numeric_example": "INSUFFICIENT_EVIDENCE",
                        "paper_role_explanation": "It grounds the paper method.",
                        "evidence_ref": ref,
                    }
                ]
            }
        if self.fail_paper:
            raise RuntimeError("paper failed")
        ref = _first_allowed_ref(text)
        return {
            "one_sentence_summary": "The paper proposes an attention model for anomaly detection.",
            "problem": {"text": "The paper studies anomaly detection.", "evidence_ref": ref},
            "core_idea": {"text": "The method introduces an attention architecture.", "evidence_ref": ref},
            "method_overview": {"text": "The method introduces an attention architecture.", "evidence_ref": ref},
            "experiment_summary": {"text": "The model is evaluated on benchmark data.", "evidence_ref": ref},
            "limitations": {"text": "INSUFFICIENT_EVIDENCE", "evidence_ref": ""},
        }


def _first_allowed_ref(prompt: str) -> str:
    tail = prompt.split("Allowed evidence_ref values:", 1)[-1]
    for line in tail.splitlines():
        line = line.strip()
        if line.startswith("- "):
            value = line[2:].strip()
            if value and value != "NONE":
                return value
    raise AssertionError("No allowed evidence_ref in prompt")


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
    assert data["paper_workspace_status"]["source_type"] == "upload"
    assert data["paper_workspace_status"]["verification_status"] == "verified"
    assert data["paper_workspace_status"]["can_enter_m2"] is True
    assert data["paper_workspace_status"]["source_confidence"] == 1.0
    assert data["paper_workspace_status"]["canonicalization_status"] == "not_available"


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


def test_parse_endpoint_with_injected_llm_can_return_success_cards(tmp_path: Path) -> None:
    llm = ScriptedApiLLM()
    client = TestClient(create_app(workspace_root=tmp_path / "workspace", llm_client=llm))
    job_id = _parse_method_sample(client)
    run_dir = tmp_path / "workspace" / "runs" / job_id

    status_response = client.get(f"/api/v1/jobs/{job_id}/understanding_status")
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert status_data["understanding_status"]["status"] == "SUCCESS"
    assert status_data["paper_workspace_status"]["source_type"] == "upload"
    assert status_data["paper_workspace_status"]["evidence_status"] == "SUCCESS"

    cards_response = client.get(f"/api/v1/jobs/{job_id}/cards")
    assert cards_response.status_code == 200
    cards_data = cards_response.json()
    assert cards_data["status"] == "SUCCESS"
    assert "paper_card" in cards_data["cards"]
    assert "teaching_cards" in cards_data["cards"]
    assert cards_data["paper_workspace_status"]["quality_status"] == "pass"
    assert llm.calls == 2

    job_response = client.get(f"/api/v1/jobs/{job_id}")
    artifact_types = {artifact["artifact_type"] for artifact in job_response.json()["artifacts"]}
    assert "evidence_pack" in artifact_types
    assert "formula_evidence_pack" in artifact_types
    evidence_pack = json.loads((run_dir / "evidence_pack.json").read_text(encoding="utf-8"))
    assert any(item["claim_type"] == "METHOD" for item in evidence_pack["items"])


def test_parse_endpoint_with_injected_llm_can_return_degraded_cards(tmp_path: Path) -> None:
    llm = ScriptedApiLLM(fail_teaching=True)
    client = TestClient(create_app(workspace_root=tmp_path / "workspace", llm_client=llm))
    job_id = _parse_method_sample(client)

    status_response = client.get(f"/api/v1/jobs/{job_id}/understanding_status")
    assert status_response.status_code == 200
    assert status_response.json()["understanding_status"]["status"] == "DEGRADED_STRUCTURAL"

    cards_response = client.get(f"/api/v1/jobs/{job_id}/cards")
    assert cards_response.status_code == 200
    cards_data = cards_response.json()
    assert cards_data["degraded"] is True
    assert "paper_card" in cards_data["cards"]
    assert "formula_cards" not in cards_data["cards"]
    assert "teaching_cards" not in cards_data["cards"]
    assert "teaching_cards" in cards_data["missing_components"]
    assert "formula_cards" not in cards_data["missing_components"]


def test_parse_endpoint_degrades_raw_formula_derivation_and_hides_formula_cards(tmp_path: Path) -> None:
    llm = ScriptedApiLLM()
    client = TestClient(create_app(workspace_root=tmp_path / "workspace", llm_client=llm))
    job_id = _parse_raw_formula_sample(client)

    status_response = client.get(f"/api/v1/jobs/{job_id}/understanding_status")
    assert status_response.status_code == 200
    status_data = status_response.json()["understanding_status"]
    assert status_data["status"] == "DEGRADED_STRUCTURAL"
    assert status_data["blocking_reason"] == "FORMULA_DERIVATION_BLOCKED"
    assert status_data["component_status"]["paper_card"] == "SUCCESS"
    assert status_data["component_status"]["formula_cards"] == "FAILED"
    assert status_data["component_status"]["teaching_cards"] == "SUCCESS"

    cards_response = client.get(f"/api/v1/jobs/{job_id}/cards")
    assert cards_response.status_code == 200
    cards_data = cards_response.json()
    assert cards_data["status"] == "DEGRADED_STRUCTURAL"
    assert set(cards_data["cards"]) == {"paper_card", "teaching_cards"}
    assert "formula_cards" in cards_data["missing_components"]


def test_parse_endpoint_with_injected_llm_can_return_blocked_status(tmp_path: Path) -> None:
    llm = ScriptedApiLLM(fail_paper=True)
    client = TestClient(create_app(workspace_root=tmp_path / "workspace", llm_client=llm))
    job_id = _parse_method_sample(client)

    status_response = client.get(f"/api/v1/jobs/{job_id}/understanding_status")
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert status_data["understanding_status"]["status"] == "BLOCKED_UNDERSTANDING"
    assert status_data["understanding_status"]["allowed_for_user_display"] is False

    cards_response = client.get(f"/api/v1/jobs/{job_id}/cards")
    assert cards_response.status_code == 403
    detail = cards_response.json()["detail"]
    assert detail["status"] == "BLOCKED_UNDERSTANDING"
    assert detail["blocking_reason"] == "PAPER_CARD_FAILED"
    assert "paper_card" not in detail


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
    component_status: dict[str, str] | None = None,
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
        "component_status": component_status or {},
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


def test_cards_endpoint_degraded_filters_failed_components_even_if_artifact_exists(tmp_path: Path) -> None:
    client = _create_job_with_cards(
        tmp_path,
        "job-degraded-filter",
        "DEGRADED_STRUCTURAL",
        include_teaching_cards=True,
        component_status={
            "paper_card": "SUCCESS",
            "formula_cards": "SUCCESS",
            "teaching_cards": "FAILED",
        },
    )

    response = client.get("/api/v1/jobs/job-degraded-filter/cards")

    assert response.status_code == 200
    data = response.json()
    assert set(data["cards"]) == {"paper_card", "formula_cards"}
    assert "teaching_cards" in data["missing_components"]


def test_cards_endpoint_degraded_allows_failed_formula_component_to_be_hidden(tmp_path: Path) -> None:
    client = _create_job_with_cards(
        tmp_path,
        "job-degraded-formula-failed",
        "DEGRADED_STRUCTURAL",
        include_formula_cards=False,
        include_teaching_cards=False,
        component_status={
            "paper_card": "SUCCESS",
            "formula_cards": "FAILED",
            "teaching_cards": "FAILED",
        },
    )

    response = client.get("/api/v1/jobs/job-degraded-formula-failed/cards")

    assert response.status_code == 200
    data = response.json()
    assert set(data["cards"]) == {"paper_card"}
    assert "formula_cards" in data["missing_components"]
    assert "teaching_cards" in data["missing_components"]


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


def test_cards_endpoint_failed_returns_403(tmp_path: Path) -> None:
    client = _create_job_with_cards(tmp_path, "job-failed", "FAILED")

    response = client.get("/api/v1/jobs/job-failed/cards")

    assert response.status_code == 403
    assert response.json()["detail"]["status"] == "FAILED"


def test_parse_registers_existing_m2_artifacts_and_cards_are_gated(tmp_path: Path) -> None:
    artifact_dir = _write_m2_artifact_run(tmp_path / "m2_success")
    client = TestClient(
        create_app(
            workspace_root=tmp_path / "workspace",
            allowed_local_roots=[tmp_path],
        )
    )

    parse_response = client.post(
        "/api/v1/documents/parse",
        data={"local_path": str(artifact_dir)},
    )

    assert parse_response.status_code == 200
    job_id = parse_response.json()["job_id"]

    status_response = client.get(f"/api/v1/jobs/{job_id}/understanding_status")
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert status_data["understanding_status"]["status"] == "SUCCESS"
    assert status_data["paper_workspace_status"]["source_type"] == "m1_canonical_bundle"
    assert status_data["paper_workspace_status"]["canonicalization_status"] == "success"
    assert status_data["paper_workspace_status"]["m2_ready"] is True
    assert status_data["paper_workspace_status"]["formula_origin"] == "mineru_latex"
    assert status_data["paper_workspace_status"]["formula_ocr_status"] == "not_required"
    assert status_data["paper_workspace_status"]["evidence_status"] == "SUCCESS"

    cards_response = client.get(f"/api/v1/jobs/{job_id}/cards")
    assert cards_response.status_code == 200
    cards_data = cards_response.json()
    assert cards_data["status"] == "SUCCESS"
    assert set(cards_data["cards"]) == {"paper_card", "formula_cards", "teaching_cards"}
    assert cards_data["cards"]["paper_card"]["problem"]["evidence_ref"] == "paper:b001"
    assert cards_data["cards"]["formula_cards"]["formula_cards"][0]["formula_origin"] == "mineru_latex"


def _write_m2_artifact_run(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    _plain_write_json(root / "source_status.json", {
        "source_type": "m1_canonical_bundle",
        "original_input": "m1",
        "resolved_path": str(root / "canonical_paper.md"),
        "status": "resolved",
        "content_type": "text/markdown",
        "size_bytes": 100,
    })
    _plain_write_json(root / "canonical_status.json", {
        "paper_id": "paper",
        "title": "M2 Artifact Paper",
        "canonicalization_status": "success",
        "m2_ready": True,
    })
    _plain_write_json(root / "understanding_status.json", {
        "schema_version": "understanding_status",
        "paper_id": "paper",
        "status": "SUCCESS",
        "blocking_reason": "",
        "warnings": [],
        "allowed_for_user_display": True,
        "allowed_downstream": {"reading_display": True, "advisor_questions": True},
        "component_status": {
            "paper_card": "SUCCESS",
            "formula_cards": "SUCCESS",
            "teaching_cards": "SUCCESS",
            "llm": "SUCCESS",
            "evidence_pack": "SUCCESS",
            "audit": "SUCCESS",
        },
        "checked_artifacts": ["paper_card", "formula_cards", "teaching_cards"],
    })
    _plain_write_json(root / "passage_index.json", {
        "paper_id": "paper",
        "passages": [{
            "passage_id": "p1",
            "evidence_refs": ["paper:b001"],
            "formula_origins": ["mineru_latex"],
            "formula_ocr_statuses": ["not_required"],
        }],
    })
    _plain_write_json(root / "claim_evidence.json", {
        "paper_id": "paper",
        "claims": [{
            "claim_id": "c1",
            "evidence_ref": "paper:b001",
            "passage_id": "p1",
            "claim_type": "FORMULA_CONTEXT",
            "formula_origin": "mineru_latex",
            "formula_ocr_status": "not_required",
        }],
    })
    _plain_write_json(root / "quality_report.json", {"paper_id": "paper", "findings": []})
    _plain_write_json(root / "paper_card.json", {
        "paper_id": "paper",
        "title": "M2 Artifact Paper",
        "one_sentence_summary": "A real M2 artifact-style paper card.",
        "problem": {"text": "Problem", "evidence_ref": "paper:b001"},
        "core_idea": {"text": "Idea", "evidence_ref": "paper:b001"},
        "method_overview": {"text": "Method", "evidence_ref": "paper:b001"},
        "experiment_summary": {"text": "Experiment", "evidence_ref": "paper:b001"},
    })
    _plain_write_json(root / "formula_cards.json", {
        "paper_id": "paper",
        "formula_cards": [{
            "formula_id": "f1",
            "purpose": "Formula purpose",
            "formula_origin": "mineru_latex",
            "formula_ocr_status": "not_required",
            "evidence_ref": "paper:b001",
        }],
    })
    _plain_write_json(root / "teaching_cards.json", {
        "paper_id": "paper",
        "teaching_cards": [{
            "card_id": "t1",
            "title": "Teaching",
            "human_explanation": "A teaching explanation.",
            "evidence_refs": ["paper:b001"],
        }],
    })
    _plain_write_json(root / "m2_run_summary.json", {"paper_id": "paper", "status": "SUCCESS"})
    return root


def _plain_write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
