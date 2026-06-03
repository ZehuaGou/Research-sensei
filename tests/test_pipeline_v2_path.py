from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from researchsensei.ingestion.pipeline import SinglePaperIngestionRunner, _run_async_builder
from researchsensei.jobs import JobStore
from researchsensei.llm.client import MockLLMClient
from researchsensei.schemas import JobStatus
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


# ---------------------------------------------------------------------------
# Async bridge tests
# ---------------------------------------------------------------------------


def test_run_async_builder_sync_context() -> None:
    async def coro():
        return 42

    result = _run_async_builder(coro())
    assert result == 42


def test_run_async_builder_active_event_loop_raises() -> None:
    async def coro():
        return 42

    async def run_inside_loop():
        with pytest.raises(RuntimeError, match="active event loop"):
            _run_async_builder(coro())

    asyncio.run(run_inside_loop())


# ---------------------------------------------------------------------------
# Baseline path tests
# ---------------------------------------------------------------------------


def test_no_llm_client_still_baseline_only(tmp_path: Path) -> None:
    source = _write_sample_md(tmp_path)
    workspace = WorkspaceStore(tmp_path / "workspace")
    jobs = JobStore(tmp_path / "jobs.sqlite3")
    runner = SinglePaperIngestionRunner(workspace=workspace, jobs=jobs)

    job = runner.run(source, job_id="test-baseline")

    assert job.status == JobStatus.SUCCEEDED
    status_path = tmp_path / "workspace" / "runs" / "test-baseline" / "understanding_status.json"
    data = json.loads(status_path.read_text(encoding="utf-8"))
    assert data["status"] == "BASELINE_ONLY"


def test_baseline_writes_10_artifacts(tmp_path: Path) -> None:
    source = _write_sample_md(tmp_path)
    workspace = WorkspaceStore(tmp_path / "workspace")
    jobs = JobStore(tmp_path / "jobs.sqlite3")
    runner = SinglePaperIngestionRunner(workspace=workspace, jobs=jobs)

    job = runner.run(source, job_id="test-count")

    assert len(job.artifacts) == 10


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
# V2 success tests
# ---------------------------------------------------------------------------


def test_llm_client_triggers_v2_path(tmp_path: Path) -> None:
    source = _write_sample_md(tmp_path)
    workspace = WorkspaceStore(tmp_path / "workspace")
    jobs = JobStore(tmp_path / "jobs.sqlite3")
    client = _make_v2_client()
    runner = SinglePaperIngestionRunner(workspace=workspace, jobs=jobs, llm_client=client)

    job = runner.run(source, job_id=_V2_PAPER_ID)

    assert job.status == JobStatus.SUCCEEDED
    assert client._call_count == 3


def test_v2_success_status_success(tmp_path: Path) -> None:
    source = _write_sample_md(tmp_path)
    workspace = WorkspaceStore(tmp_path / "workspace")
    jobs = JobStore(tmp_path / "jobs.sqlite3")
    client = _make_v2_client()
    runner = SinglePaperIngestionRunner(workspace=workspace, jobs=jobs, llm_client=client)

    job = runner.run(source, job_id=_V2_PAPER_ID)

    status_path = tmp_path / "workspace" / "runs" / _V2_PAPER_ID / "understanding_status.json"
    data = json.loads(status_path.read_text(encoding="utf-8"))
    assert data["status"] == "SUCCESS"
    assert data["allowed_for_user_display"] is True


def test_v2_success_allowed_downstream_all_true(tmp_path: Path) -> None:
    source = _write_sample_md(tmp_path)
    workspace = WorkspaceStore(tmp_path / "workspace")
    jobs = JobStore(tmp_path / "jobs.sqlite3")
    client = _make_v2_client()
    runner = SinglePaperIngestionRunner(workspace=workspace, jobs=jobs, llm_client=client)

    job = runner.run(source, job_id=_V2_PAPER_ID)

    status_path = tmp_path / "workspace" / "runs" / _V2_PAPER_ID / "understanding_status.json"
    data = json.loads(status_path.read_text(encoding="utf-8"))
    gates = data["allowed_downstream"]
    assert gates["reading_display"] is True
    assert gates["phase12_patterns"] is True
    assert gates["phase12_drill"] is True
    assert gates["phase12_drill_degraded"] is False
    assert gates["advisor_questions"] is True


def test_v2_success_writes_10_artifacts(tmp_path: Path) -> None:
    source = _write_sample_md(tmp_path)
    workspace = WorkspaceStore(tmp_path / "workspace")
    jobs = JobStore(tmp_path / "jobs.sqlite3")
    client = _make_v2_client()
    runner = SinglePaperIngestionRunner(workspace=workspace, jobs=jobs, llm_client=client)

    job = runner.run(source, job_id=_V2_PAPER_ID)

    assert len(job.artifacts) == 10
    artifact_types = {a.artifact_type for a in job.artifacts}
    assert "paper_card" in artifact_types
    assert "teaching_cards" in artifact_types


def test_v2_success_paper_card_uses_v2_output(tmp_path: Path) -> None:
    source = _write_sample_md(tmp_path)
    workspace = WorkspaceStore(tmp_path / "workspace")
    jobs = JobStore(tmp_path / "jobs.sqlite3")
    client = _make_v2_client()
    runner = SinglePaperIngestionRunner(workspace=workspace, jobs=jobs, llm_client=client)

    job = runner.run(source, job_id=_V2_PAPER_ID)

    card_path = tmp_path / "workspace" / "runs" / _V2_PAPER_ID / "paper_card.json"
    data = json.loads(card_path.read_text(encoding="utf-8"))
    assert data["one_sentence_summary"] == "We propose a GNN for anomaly detection."


def test_v2_success_understanding_status_has_evidence_pack_summary(tmp_path: Path) -> None:
    source = _write_sample_md(tmp_path)
    workspace = WorkspaceStore(tmp_path / "workspace")
    jobs = JobStore(tmp_path / "jobs.sqlite3")
    client = _make_v2_client()
    runner = SinglePaperIngestionRunner(workspace=workspace, jobs=jobs, llm_client=client)

    job = runner.run(source, job_id=_V2_PAPER_ID)

    status_path = tmp_path / "workspace" / "runs" / _V2_PAPER_ID / "understanding_status.json"
    data = json.loads(status_path.read_text(encoding="utf-8"))
    summary = data.get("evidence_pack_summary")
    assert summary is not None
    assert "included_claim_ids" in summary


# ---------------------------------------------------------------------------
# V2 blocked tests
# ---------------------------------------------------------------------------


def test_paper_card_v2_failure_blocks(tmp_path: Path) -> None:
    source = _write_sample_md(tmp_path)
    workspace = WorkspaceStore(tmp_path / "workspace")
    jobs = JobStore(tmp_path / "jobs.sqlite3")

    class FailingClient:
        async def chat_json(self, messages, **kwargs):
            raise RuntimeError("LLM exploded")

    runner = SinglePaperIngestionRunner(workspace=workspace, jobs=jobs, llm_client=FailingClient())

    job = runner.run(source, job_id="test-blocked")

    assert job.status == JobStatus.SUCCEEDED
    status_path = tmp_path / "workspace" / "runs" / "test-blocked" / "understanding_status.json"
    data = json.loads(status_path.read_text(encoding="utf-8"))
    assert data["status"] == "BLOCKED_UNDERSTANDING"
    assert data["allowed_for_user_display"] is False


def test_blocked_job_status_succeeded(tmp_path: Path) -> None:
    source = _write_sample_md(tmp_path)
    workspace = WorkspaceStore(tmp_path / "workspace")
    jobs = JobStore(tmp_path / "jobs.sqlite3")

    class FailingClient:
        async def chat_json(self, messages, **kwargs):
            raise RuntimeError("LLM exploded")

    runner = SinglePaperIngestionRunner(workspace=workspace, jobs=jobs, llm_client=FailingClient())

    job = runner.run(source, job_id="test-succeeded")

    assert job.status == JobStatus.SUCCEEDED


def test_blocked_does_not_write_card_artifacts(tmp_path: Path) -> None:
    source = _write_sample_md(tmp_path)
    workspace = WorkspaceStore(tmp_path / "workspace")
    jobs = JobStore(tmp_path / "jobs.sqlite3")

    class FailingClient:
        async def chat_json(self, messages, **kwargs):
            raise RuntimeError("LLM exploded")

    runner = SinglePaperIngestionRunner(workspace=workspace, jobs=jobs, llm_client=FailingClient())

    job = runner.run(source, job_id="test-nocards")

    run_dir = tmp_path / "workspace" / "runs" / "test-nocards"
    assert not (run_dir / "paper_card.json").exists()
    assert not (run_dir / "formula_cards.json").exists()
    assert not (run_dir / "teaching_cards.json").exists()
    assert (run_dir / "understanding_status.json").exists()


# ---------------------------------------------------------------------------
# V2 degraded tests
# ---------------------------------------------------------------------------


def test_teaching_failure_degraded(tmp_path: Path) -> None:
    source = _write_sample_md(tmp_path)
    workspace = WorkspaceStore(tmp_path / "workspace")
    jobs = JobStore(tmp_path / "jobs.sqlite3")

    call_count = 0

    class TeachingFailingClient:
        async def chat_json(self, messages, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return json.loads(_valid_paper_response())
            elif call_count == 2:
                return json.loads(_valid_formula_response())
            else:
                raise RuntimeError("Teaching LLM failed")

    runner = SinglePaperIngestionRunner(workspace=workspace, jobs=jobs, llm_client=TeachingFailingClient())

    job = runner.run(source, job_id=_V2_PAPER_ID)

    assert job.status == JobStatus.SUCCEEDED
    status_path = tmp_path / "workspace" / "runs" / _V2_PAPER_ID / "understanding_status.json"
    data = json.loads(status_path.read_text(encoding="utf-8"))
    assert data["status"] == "DEGRADED_STRUCTURAL"
    assert data["allowed_for_user_display"] is True
    assert data["allowed_downstream"]["advisor_questions"] is False
    assert data["allowed_downstream"]["phase12_drill_degraded"] is True


def test_degraded_job_status_succeeded(tmp_path: Path) -> None:
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

    assert job.status == JobStatus.SUCCEEDED


def test_degraded_does_not_write_teaching_artifact(tmp_path: Path) -> None:
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

    run_dir = tmp_path / "workspace" / "runs" / _V2_PAPER_ID
    assert (run_dir / "paper_card.json").exists()
    assert (run_dir / "formula_cards.json").exists()
    assert not (run_dir / "teaching_cards.json").exists()
    assert (run_dir / "understanding_status.json").exists()

    artifact_types = {a.artifact_type for a in job.artifacts}
    assert "paper_card" in artifact_types
    assert "teaching_cards" not in artifact_types
