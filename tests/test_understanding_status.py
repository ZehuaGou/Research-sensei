from __future__ import annotations

import json
from pathlib import Path

from researchsensei.ingestion.pipeline import SinglePaperIngestionRunner
from researchsensei.jobs import JobStore
from researchsensei.schemas import (
    DownstreamGates,
    EvidencePackSummary,
    JobStatus,
    UnderstandingStatus,
    WarningItem,
)
from researchsensei.workspace import WorkspaceStore


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


def test_downstream_gates_defaults_all_false() -> None:
    gates = DownstreamGates()
    assert gates.reading_display is False
    assert gates.learning_patterns is False
    assert gates.learning_drills is False
    assert gates.learning_drills_degraded is False
    assert gates.advisor_questions is False


def test_evidence_pack_summary_round_trip() -> None:
    summary = EvidencePackSummary(
        included_claim_ids=["c001", "c002"],
        excluded_claim_ids=["c003"],
        total_tokens=150,
        claim_type_counts={"METHOD": 1, "RESULT": 1},
        truncated_passage_ids=[],
    )

    json_str = summary.model_dump_json()
    restored = EvidencePackSummary.model_validate_json(json_str)

    assert restored.included_claim_ids == ["c001", "c002"]
    assert restored.excluded_claim_ids == ["c003"]
    assert restored.total_tokens == 150
    assert restored.claim_type_counts == {"METHOD": 1, "RESULT": 1}


def test_understanding_status_round_trip() -> None:
    status = UnderstandingStatus(
        paper_id="test",
        status="BASELINE_ONLY",
        blocking_reason="NO_LLM_CLIENT",
        allowed_for_user_display=False,
        allowed_downstream=DownstreamGates(),
        component_status={"paper_card": "BASELINE"},
        checked_artifacts=["paper_card"],
    )

    json_str = status.model_dump_json()
    restored = UnderstandingStatus.model_validate_json(json_str)

    assert restored.paper_id == "test"
    assert restored.status == "BASELINE_ONLY"
    assert restored.blocking_reason == "NO_LLM_CLIENT"
    assert restored.allowed_for_user_display is False
    assert restored.allowed_downstream.reading_display is False
    assert restored.component_status == {"paper_card": "BASELINE"}


def test_baseline_only_status_has_no_downstream_access() -> None:
    status = UnderstandingStatus(
        paper_id="test",
        status="BASELINE_ONLY",
        blocking_reason="NO_LLM_CLIENT",
        allowed_for_user_display=False,
        allowed_downstream=DownstreamGates(),
    )

    assert status.allowed_for_user_display is False
    assert status.allowed_downstream.reading_display is False
    assert status.allowed_downstream.learning_patterns is False
    assert status.allowed_downstream.learning_drills is False
    assert status.allowed_downstream.advisor_questions is False


def test_baseline_only_component_status_values() -> None:
    status = UnderstandingStatus(
        paper_id="test",
        status="BASELINE_ONLY",
        component_status={
            "paper_card": "BASELINE",
            "formula_cards": "BASELINE",
            "teaching_cards": "BASELINE",
            "llm": "SKIPPED",
            "evidence_pack": "SKIPPED",
        },
    )

    assert status.component_status["paper_card"] == "BASELINE"
    assert status.component_status["llm"] == "SKIPPED"


def test_baseline_only_warning_list_uses_warning_item() -> None:
    status = UnderstandingStatus(
        paper_id="test",
        status="BASELINE_ONLY",
        warnings=[WarningItem(code="NO_LLM", message="No LLM client provided.")],
    )

    assert len(status.warnings) == 1
    assert status.warnings[0].code == "NO_LLM"


# ---------------------------------------------------------------------------
# Pipeline integration tests
# ---------------------------------------------------------------------------


def _write_sample_md(tmp_path: Path) -> Path:
    path = tmp_path / "paper.md"
    path.write_text(
        "# Paper\n## Abstract\nWe study anomaly detection.\n\n## Method\nWe propose a model.\n\n## Experiments\nTable 1 reports F1.",
        encoding="utf-8",
    )
    return path


def test_pipeline_baseline_writes_understanding_status(tmp_path: Path) -> None:
    source = _write_sample_md(tmp_path)
    workspace = WorkspaceStore(tmp_path / "workspace")
    jobs = JobStore(tmp_path / "jobs.sqlite3")
    runner = SinglePaperIngestionRunner(workspace=workspace, jobs=jobs)

    job = runner.run(source, job_id="test-status")

    assert job.status == JobStatus.SUCCEEDED
    status_path = tmp_path / "workspace" / "runs" / "test-status" / "understanding_status.json"
    assert status_path.exists()

    data = json.loads(status_path.read_text(encoding="utf-8"))
    assert data["status"] == "BASELINE_ONLY"
    assert data["blocking_reason"] == "NO_LLM_CLIENT"
    assert data["allowed_for_user_display"] is False
    assert data["allowed_downstream"]["reading_display"] is False
    assert data["allowed_downstream"]["learning_patterns"] is False
    assert data["allowed_downstream"]["learning_drills"] is False
    assert data["allowed_downstream"]["advisor_questions"] is False


def test_pipeline_baseline_still_writes_old_card_artifacts(tmp_path: Path) -> None:
    source = _write_sample_md(tmp_path)
    workspace = WorkspaceStore(tmp_path / "workspace")
    jobs = JobStore(tmp_path / "jobs.sqlite3")
    runner = SinglePaperIngestionRunner(workspace=workspace, jobs=jobs)

    job = runner.run(source, job_id="test-cards")

    run_dir = tmp_path / "workspace" / "runs" / "test-cards"
    assert (run_dir / "paper_card.json").exists()
    assert (run_dir / "formula_cards.json").exists()
    assert (run_dir / "teaching_cards.json").exists()
    assert (run_dir / "understanding_status.json").exists()


def test_artifact_count_includes_understanding_status(tmp_path: Path) -> None:
    source = _write_sample_md(tmp_path)
    workspace = WorkspaceStore(tmp_path / "workspace")
    jobs = JobStore(tmp_path / "jobs.sqlite3")
    runner = SinglePaperIngestionRunner(workspace=workspace, jobs=jobs)

    job = runner.run(source, job_id="test-count")

    artifact_types = {a.artifact_type for a in job.artifacts}
    assert "understanding_status" in artifact_types
    assert len(job.artifacts) == 11
    expected = {
        "source_status", "ingestion", "passage_index", "claim_evidence",
        "evidence_index", "paper_skeleton", "paper_card", "formula_cards",
        "teaching_cards", "understanding_status", "quality_report",
    }
    assert artifact_types == expected


def test_no_llm_client_baseline_component_status(tmp_path: Path) -> None:
    source = _write_sample_md(tmp_path)
    workspace = WorkspaceStore(tmp_path / "workspace")
    jobs = JobStore(tmp_path / "jobs.sqlite3")
    runner = SinglePaperIngestionRunner(workspace=workspace, jobs=jobs)

    job = runner.run(source, job_id="test-comp")

    status_path = tmp_path / "workspace" / "runs" / "test-comp" / "understanding_status.json"
    data = json.loads(status_path.read_text(encoding="utf-8"))

    assert data["component_status"]["paper_card"] == "BASELINE"
    assert data["component_status"]["formula_cards"] == "BASELINE"
    assert data["component_status"]["teaching_cards"] == "BASELINE"
    assert data["component_status"]["llm"] == "SKIPPED"
    assert data["component_status"]["evidence_pack"] == "SKIPPED"
