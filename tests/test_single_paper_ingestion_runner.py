from __future__ import annotations

import json
from pathlib import Path

from researchsensei.ingestion import SinglePaperIngestionRunner
from researchsensei.jobs import JobStore
from researchsensei.schemas import JobStatus
from researchsensei.workspace import WorkspaceStore


def test_single_paper_runner_writes_artifact_and_updates_job(tmp_path: Path) -> None:
    source = tmp_path / "paper.md"
    source.write_text("# Paper\n## Abstract\nWe study anomaly detection.", encoding="utf-8")
    workspace = WorkspaceStore(tmp_path / "workspace")
    jobs = JobStore(tmp_path / "jobs.sqlite3")

    job = SinglePaperIngestionRunner(workspace=workspace, jobs=jobs).run(source, job_id="job-md")

    parsed_path = tmp_path / "workspace" / "runs" / "job-md" / "parsed_document.json"
    copied_source = tmp_path / "workspace" / "runs" / "job-md" / "source.md"
    assert copied_source.exists()
    assert parsed_path.exists()
    assert json.loads(parsed_path.read_text(encoding="utf-8"))["paper_id"] == "job-md"
    assert job.status == JobStatus.SUCCEEDED
    assert job.current_step == "ingestion_completed"
    assert job.artifacts[0].path == str(parsed_path)
    assert jobs.get("job-md") == job


def test_single_paper_runner_writes_evidence_and_skeleton_artifacts(tmp_path: Path) -> None:
    source = tmp_path / "paper.md"
    source.write_text(
        """
# Paper
## Abstract
We study anomaly detection.

## Method
We minimize L = L_rec.

## Experiments
Table 1 reports F1.
""".strip(),
        encoding="utf-8",
    )
    workspace = WorkspaceStore(tmp_path / "workspace")
    jobs = JobStore(tmp_path / "jobs.sqlite3")

    job = SinglePaperIngestionRunner(workspace=workspace, jobs=jobs).run(source, job_id="job-phase6")

    run_dir = tmp_path / "workspace" / "runs" / "job-phase6"
    evidence_path = run_dir / "evidence_index.json"
    skeleton_path = run_dir / "paper_skeleton.json"
    artifact_types = {artifact.artifact_type for artifact in job.artifacts}

    assert evidence_path.exists()
    assert skeleton_path.exists()
    assert {"source_status", "ingestion", "passage_index", "claim_evidence", "evidence_index", "paper_skeleton", "paper_card", "formula_cards", "teaching_cards", "understanding_status"} == artifact_types
    assert json.loads(evidence_path.read_text(encoding="utf-8"))["claims"]
    assert json.loads(skeleton_path.read_text(encoding="utf-8"))["method_overview"] == "We minimize L = L_rec."


def test_single_paper_runner_records_degraded_pdf_warnings(tmp_path: Path) -> None:
    source = tmp_path / "broken.pdf"
    source.write_bytes(b"not a pdf")
    workspace = WorkspaceStore(tmp_path / "workspace")
    jobs = JobStore(tmp_path / "jobs.sqlite3")

    job = SinglePaperIngestionRunner(workspace=workspace, jobs=jobs).run(source, job_id="job-pdf")

    parsed_path = tmp_path / "workspace" / "runs" / "job-pdf" / "parsed_document.json"
    parsed = json.loads(parsed_path.read_text(encoding="utf-8"))
    assert parsed["degraded"] is True
    assert any(warning["code"] == "PDF_PARSE_FAILED" for warning in parsed["warnings"])
    assert job.status == JobStatus.SUCCEEDED
    assert job.current_step == "ingestion_degraded"
    assert any(warning.code == "PDF_PARSE_FAILED" for warning in job.warnings)
