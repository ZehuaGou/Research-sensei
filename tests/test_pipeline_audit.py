from __future__ import annotations

import json
from pathlib import Path

import pytest

from researchsensei.audit.quality_auditor import QualityAuditor
from researchsensei.ingestion.pipeline import SinglePaperIngestionRunner
from researchsensei.jobs import JobStore
from researchsensei.llm.client import MockLLMClient
from researchsensei.schemas import (
    ArtifactBundle,
    AuditFinding,
    ComponentAuditResult,
    JobStatus,
    QualityReport,
)
from researchsensei.workspace import WorkspaceStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_V2_PAPER_ID = "test"


def _write_sample_md(tmp_path: Path) -> Path:
    path = tmp_path / "paper.md"
    path.write_text(
        "# Paper\n"
        "## Abstract\n"
        "We study anomaly detection in multivariate time series data. "
        "Existing methods fail to capture complex sensor dependencies.\n\n"
        "## Method\n"
        "We propose a graph neural network to model relationships between sensors. "
        "The model learns to detect anomalies by reconstructing normal patterns.\n\n"
        "## Experiments\n"
        "We evaluate on three benchmark datasets and achieve state-of-the-art results.",
        encoding="utf-8",
    )
    return path


def _valid_paper_response() -> str:
    pid = _V2_PAPER_ID
    return json.dumps({
        "one_sentence_summary": "We propose a GNN for anomaly detection.",
        "problem": {"text": "Detecting anomalies is hard.", "evidence_ref": f"{pid}:b002"},
        "core_idea": {"text": "Graph neural network.", "evidence_ref": f"{pid}:b002"},
        "method_overview": {"text": "GNN approach.", "evidence_ref": f"{pid}:b002"},
        "experiment_summary": {"text": "State-of-the-art results.", "evidence_ref": f"{pid}:b003"},
        "limitations": {"text": "Needs more data.", "evidence_ref": ""},
    })


def _valid_formula_response() -> str:
    pid = _V2_PAPER_ID
    return json.dumps({
        "formula_cards": [
            {
                "purpose": "Loss function",
                "intuition": "Minimize reconstruction error",
                "plain_summary": "Total loss",
                "evidence_ref": f"{pid}:b002",
            }
        ]
    })


def _valid_teaching_response() -> str:
    pid = _V2_PAPER_ID
    return json.dumps({
        "teaching_cards": [
            {
                "target_type": "concept",
                "title": "Core idea",
                "human_explanation": "GNN models sensor relationships.",
                "analogy_explanation": "Like social networks.",
                "evidence_ref": f"{pid}:b002",
            }
        ]
    })


def _make_v2_client() -> MockLLMClient:
    return MockLLMClient(responses=[
        _valid_paper_response(),
        _valid_formula_response(),
        _valid_teaching_response(),
    ])


class FakeAuditor:
    """Fake auditor that returns a preset QualityReport."""
    def __init__(self, report: QualityReport) -> None:
        self.report = report
        self.call_count = 0

    def audit(self, artifacts: ArtifactBundle) -> QualityReport:
        self.call_count += 1
        return self.report


# ---------------------------------------------------------------------------
# Baseline path tests
# ---------------------------------------------------------------------------


def test_baseline_writes_quality_report(tmp_path: Path) -> None:
    source = _write_sample_md(tmp_path)
    workspace = WorkspaceStore(tmp_path / "workspace")
    jobs = JobStore(tmp_path / "jobs.sqlite3")
    runner = SinglePaperIngestionRunner(workspace=workspace, jobs=jobs)

    job = runner.run(source, job_id="test-baseline")

    qr_path = tmp_path / "workspace" / "runs" / "test-baseline" / "quality_report.json"
    assert qr_path.exists()
    data = json.loads(qr_path.read_text(encoding="utf-8"))
    assert data["paper_id"] == "test-baseline"
    assert "findings" in data


def test_baseline_artifact_count_11(tmp_path: Path) -> None:
    source = _write_sample_md(tmp_path)
    workspace = WorkspaceStore(tmp_path / "workspace")
    jobs = JobStore(tmp_path / "jobs.sqlite3")
    runner = SinglePaperIngestionRunner(workspace=workspace, jobs=jobs)

    job = runner.run(source, job_id="test-count")

    assert len(job.artifacts) == 11
    artifact_types = {a.artifact_type for a in job.artifacts}
    assert "quality_report" in artifact_types


def test_baseline_quality_report_no_block(tmp_path: Path) -> None:
    source = _write_sample_md(tmp_path)
    workspace = WorkspaceStore(tmp_path / "workspace")
    jobs = JobStore(tmp_path / "jobs.sqlite3")
    runner = SinglePaperIngestionRunner(workspace=workspace, jobs=jobs)

    job = runner.run(source, job_id="test-noblock")

    qr_path = tmp_path / "workspace" / "runs" / "test-noblock" / "quality_report.json"
    data = json.loads(qr_path.read_text(encoding="utf-8"))
    block_findings = [f for f in data["findings"] if f.get("effect") == "BLOCK"]
    assert len(block_findings) == 0


def test_baseline_status_remains_baseline_only(tmp_path: Path) -> None:
    source = _write_sample_md(tmp_path)
    workspace = WorkspaceStore(tmp_path / "workspace")
    jobs = JobStore(tmp_path / "jobs.sqlite3")
    runner = SinglePaperIngestionRunner(workspace=workspace, jobs=jobs)

    job = runner.run(source, job_id="test-status")

    status_path = tmp_path / "workspace" / "runs" / "test-status" / "understanding_status.json"
    data = json.loads(status_path.read_text(encoding="utf-8"))
    assert data["status"] == "BASELINE_ONLY"


def test_baseline_old_card_artifacts_still_written(tmp_path: Path) -> None:
    source = _write_sample_md(tmp_path)
    workspace = WorkspaceStore(tmp_path / "workspace")
    jobs = JobStore(tmp_path / "jobs.sqlite3")
    runner = SinglePaperIngestionRunner(workspace=workspace, jobs=jobs)

    job = runner.run(source, job_id="test-cards")

    run_dir = tmp_path / "workspace" / "runs" / "test-cards"
    assert (run_dir / "paper_card.json").exists()
    assert (run_dir / "formula_cards.json").exists()
    assert (run_dir / "teaching_cards.json").exists()


# ---------------------------------------------------------------------------
# V2 SUCCESS tests
# ---------------------------------------------------------------------------


def test_v2_success_writes_quality_report(tmp_path: Path) -> None:
    source = _write_sample_md(tmp_path)
    workspace = WorkspaceStore(tmp_path / "workspace")
    jobs = JobStore(tmp_path / "jobs.sqlite3")
    client = _make_v2_client()
    runner = SinglePaperIngestionRunner(workspace=workspace, jobs=jobs, llm_client=client)

    job = runner.run(source, job_id=_V2_PAPER_ID)

    qr_path = tmp_path / "workspace" / "runs" / _V2_PAPER_ID / "quality_report.json"
    assert qr_path.exists()


def test_v2_success_artifact_count_11(tmp_path: Path) -> None:
    source = _write_sample_md(tmp_path)
    workspace = WorkspaceStore(tmp_path / "workspace")
    jobs = JobStore(tmp_path / "jobs.sqlite3")
    client = _make_v2_client()
    runner = SinglePaperIngestionRunner(workspace=workspace, jobs=jobs, llm_client=client)

    job = runner.run(source, job_id=_V2_PAPER_ID)

    assert len(job.artifacts) == 11
    artifact_types = {a.artifact_type for a in job.artifacts}
    assert "quality_report" in artifact_types


def test_v2_success_quality_report_checked_artifacts(tmp_path: Path) -> None:
    source = _write_sample_md(tmp_path)
    workspace = WorkspaceStore(tmp_path / "workspace")
    jobs = JobStore(tmp_path / "jobs.sqlite3")
    client = _make_v2_client()
    runner = SinglePaperIngestionRunner(workspace=workspace, jobs=jobs, llm_client=client)

    job = runner.run(source, job_id=_V2_PAPER_ID)

    qr_path = tmp_path / "workspace" / "runs" / _V2_PAPER_ID / "quality_report.json"
    data = json.loads(qr_path.read_text(encoding="utf-8"))
    assert "paper_card" in data["checked_artifacts"]
    assert "understanding_status" in data["checked_artifacts"]


def test_v2_success_status_remains_success_when_audit_passes(tmp_path: Path) -> None:
    source = _write_sample_md(tmp_path)
    workspace = WorkspaceStore(tmp_path / "workspace")
    jobs = JobStore(tmp_path / "jobs.sqlite3")
    client = _make_v2_client()
    runner = SinglePaperIngestionRunner(workspace=workspace, jobs=jobs, llm_client=client)

    job = runner.run(source, job_id=_V2_PAPER_ID)

    status_path = tmp_path / "workspace" / "runs" / _V2_PAPER_ID / "understanding_status.json"
    data = json.loads(status_path.read_text(encoding="utf-8"))
    assert data["status"] == "SUCCESS"


# ---------------------------------------------------------------------------
# V2 DEGRADED tests
# ---------------------------------------------------------------------------


def test_degraded_writes_quality_report(tmp_path: Path) -> None:
    source = _write_sample_md(tmp_path)
    workspace = WorkspaceStore(tmp_path / "workspace")
    jobs = JobStore(tmp_path / "jobs.sqlite3")

    call_count = 0

    class TeachingFailingClient:
        async def chat_json(self, messages, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return json.loads([_valid_paper_response(), _valid_formula_response()][call_count - 1])
            raise RuntimeError("Teaching failed")

    runner = SinglePaperIngestionRunner(workspace=workspace, jobs=jobs, llm_client=TeachingFailingClient())

    job = runner.run(source, job_id=_V2_PAPER_ID)

    qr_path = tmp_path / "workspace" / "runs" / _V2_PAPER_ID / "quality_report.json"
    assert qr_path.exists()


def test_degraded_artifact_count_10(tmp_path: Path) -> None:
    source = _write_sample_md(tmp_path)
    workspace = WorkspaceStore(tmp_path / "workspace")
    jobs = JobStore(tmp_path / "jobs.sqlite3")

    call_count = 0

    class TeachingFailingClient:
        async def chat_json(self, messages, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return json.loads([_valid_paper_response(), _valid_formula_response()][call_count - 1])
            raise RuntimeError("Teaching failed")

    runner = SinglePaperIngestionRunner(workspace=workspace, jobs=jobs, llm_client=TeachingFailingClient())

    job = runner.run(source, job_id=_V2_PAPER_ID)

    assert len(job.artifacts) == 10


# ---------------------------------------------------------------------------
# V2 BLOCKED tests
# ---------------------------------------------------------------------------


def test_blocked_writes_quality_report(tmp_path: Path) -> None:
    source = _write_sample_md(tmp_path)
    workspace = WorkspaceStore(tmp_path / "workspace")
    jobs = JobStore(tmp_path / "jobs.sqlite3")

    class FailingClient:
        async def chat_json(self, messages, **kwargs):
            raise RuntimeError("LLM exploded")

    runner = SinglePaperIngestionRunner(workspace=workspace, jobs=jobs, llm_client=FailingClient())

    job = runner.run(source, job_id="test-blocked")

    qr_path = tmp_path / "workspace" / "runs" / "test-blocked" / "quality_report.json"
    assert qr_path.exists()


def test_blocked_artifact_count_8(tmp_path: Path) -> None:
    source = _write_sample_md(tmp_path)
    workspace = WorkspaceStore(tmp_path / "workspace")
    jobs = JobStore(tmp_path / "jobs.sqlite3")

    class FailingClient:
        async def chat_json(self, messages, **kwargs):
            raise RuntimeError("LLM exploded")

    runner = SinglePaperIngestionRunner(workspace=workspace, jobs=jobs, llm_client=FailingClient())

    job = runner.run(source, job_id="test-blocked-count")

    assert len(job.artifacts) == 8


def test_blocked_status_remains_blocked(tmp_path: Path) -> None:
    source = _write_sample_md(tmp_path)
    workspace = WorkspaceStore(tmp_path / "workspace")
    jobs = JobStore(tmp_path / "jobs.sqlite3")

    class FailingClient:
        async def chat_json(self, messages, **kwargs):
            raise RuntimeError("LLM exploded")

    runner = SinglePaperIngestionRunner(workspace=workspace, jobs=jobs, llm_client=FailingClient())

    job = runner.run(source, job_id="test-blocked-status")

    status_path = tmp_path / "workspace" / "runs" / "test-blocked-status" / "understanding_status.json"
    data = json.loads(status_path.read_text(encoding="utf-8"))
    assert data["status"] == "BLOCKED_UNDERSTANDING"


# ---------------------------------------------------------------------------
# Audit BLOCK override tests
# ---------------------------------------------------------------------------


def test_audit_block_overrides_v2_success_to_blocked(tmp_path: Path) -> None:
    source = _write_sample_md(tmp_path)
    workspace = WorkspaceStore(tmp_path / "workspace")
    jobs = JobStore(tmp_path / "jobs.sqlite3")
    client = _make_v2_client()

    # Fake auditor that returns a BLOCK finding
    block_report = QualityReport(
        paper_id=_V2_PAPER_ID,
        findings=[AuditFinding(code="F-2", severity="P0", effect="BLOCK", message="invalid ref")],
        component_results=[],
    )
    fake_auditor = FakeAuditor(block_report)

    runner = SinglePaperIngestionRunner(
        workspace=workspace, jobs=jobs, llm_client=client, quality_auditor=fake_auditor,
    )

    job = runner.run(source, job_id=_V2_PAPER_ID)

    assert job.status == JobStatus.SUCCEEDED
    status_path = tmp_path / "workspace" / "runs" / _V2_PAPER_ID / "understanding_status.json"
    data = json.loads(status_path.read_text(encoding="utf-8"))
    assert data["status"] == "BLOCKED_UNDERSTANDING"
    assert data["blocking_reason"] == "AUDIT_BLOCKED"
    assert data["allowed_for_user_display"] is False

    # No card artifacts
    run_dir = tmp_path / "workspace" / "runs" / _V2_PAPER_ID
    assert not (run_dir / "paper_card.json").exists()
    assert not (run_dir / "teaching_cards.json").exists()

    # Quality report exists
    assert (run_dir / "quality_report.json").exists()


def test_audit_block_overrides_v2_degraded_to_blocked(tmp_path: Path) -> None:
    source = _write_sample_md(tmp_path)
    workspace = WorkspaceStore(tmp_path / "workspace")
    jobs = JobStore(tmp_path / "jobs.sqlite3")

    call_count = 0

    class TeachingFailingClient:
        async def chat_json(self, messages, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return json.loads([_valid_paper_response(), _valid_formula_response()][call_count - 1])
            raise RuntimeError("Teaching failed")

    block_report = QualityReport(
        paper_id=_V2_PAPER_ID,
        findings=[AuditFinding(code="F-2", severity="P0", effect="BLOCK", message="invalid ref")],
        component_results=[],
    )
    fake_auditor = FakeAuditor(block_report)

    runner = SinglePaperIngestionRunner(
        workspace=workspace, jobs=jobs, llm_client=TeachingFailingClient(), quality_auditor=fake_auditor,
    )

    job = runner.run(source, job_id=_V2_PAPER_ID)

    status_path = tmp_path / "workspace" / "runs" / _V2_PAPER_ID / "understanding_status.json"
    data = json.loads(status_path.read_text(encoding="utf-8"))
    assert data["status"] == "BLOCKED_UNDERSTANDING"
    assert data["blocking_reason"] == "AUDIT_BLOCKED"

    run_dir = tmp_path / "workspace" / "runs" / _V2_PAPER_ID
    assert not (run_dir / "paper_card.json").exists()


def test_audit_block_does_not_override_baseline_only(tmp_path: Path) -> None:
    source = _write_sample_md(tmp_path)
    workspace = WorkspaceStore(tmp_path / "workspace")
    jobs = JobStore(tmp_path / "jobs.sqlite3")

    # Fake auditor that returns BLOCK
    block_report = QualityReport(
        paper_id="test",
        findings=[AuditFinding(code="F-4", severity="P0", effect="BLOCK", message="baseline display")],
        component_results=[],
    )
    fake_auditor = FakeAuditor(block_report)

    runner = SinglePaperIngestionRunner(
        workspace=workspace, jobs=jobs, quality_auditor=fake_auditor,
    )

    job = runner.run(source, job_id="test-baseline-block")

    status_path = tmp_path / "workspace" / "runs" / "test-baseline-block" / "understanding_status.json"
    data = json.loads(status_path.read_text(encoding="utf-8"))
    # Baseline should NOT be overridden by audit BLOCK
    assert data["status"] == "BASELINE_ONLY"

    # But quality_report should contain the BLOCK finding
    qr_path = tmp_path / "workspace" / "runs" / "test-baseline-block" / "quality_report.json"
    qr_data = json.loads(qr_path.read_text(encoding="utf-8"))
    block_findings = [f for f in qr_data["findings"] if f.get("effect") == "BLOCK"]
    assert len(block_findings) == 1


def test_audit_warning_added_to_understanding_status(tmp_path: Path) -> None:
    source = _write_sample_md(tmp_path)
    workspace = WorkspaceStore(tmp_path / "workspace")
    jobs = JobStore(tmp_path / "jobs.sqlite3")
    client = _make_v2_client()

    warning_report = QualityReport(
        paper_id=_V2_PAPER_ID,
        findings=[AuditFinding(code="W-1", severity="P2", effect="WARNING", message="minor issue")],
        component_results=[],
    )
    fake_auditor = FakeAuditor(warning_report)

    runner = SinglePaperIngestionRunner(
        workspace=workspace, jobs=jobs, llm_client=client, quality_auditor=fake_auditor,
    )

    job = runner.run(source, job_id=_V2_PAPER_ID)

    status_path = tmp_path / "workspace" / "runs" / _V2_PAPER_ID / "understanding_status.json"
    data = json.loads(status_path.read_text(encoding="utf-8"))
    assert data["status"] == "SUCCESS"
    warning_codes = [w["code"] for w in data["warnings"]]
    assert "W-1" in warning_codes
