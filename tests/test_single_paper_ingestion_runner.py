from __future__ import annotations

import json
from pathlib import Path

from researchsensei.ingestion import SinglePaperIngestionRunner
from researchsensei.ingestion.pipeline import _formula_llm_failure_warnings
from researchsensei.jobs import JobStore
from researchsensei.schemas import FormulaCard, FormulaCardBundle, JobStatus
from researchsensei.workspace import WorkspaceStore


def test_formula_llm_failures_are_reported_as_partial_without_hiding_successes() -> None:
    bundle = FormulaCardBundle(
        paper_id="paper",
        formula_cards=[
            FormulaCard(
                formula_id="f1",
                paper_id="paper",
                coverage_status="SOURCE_COVERED",
                derivation_status="derived",
            ),
            FormulaCard(
                formula_id="f2",
                paper_id="paper",
                coverage_status="LLM_FAILED",
                derivation_status="llm_failed",
            ),
        ],
    )

    warnings = _formula_llm_failure_warnings(bundle)

    assert len(warnings) == 1
    assert warnings[0].code == "FORMULA_CARDS_PARTIAL"
    assert warnings[0].detail == "failed_formula_count=1"


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
    assert {"source_status", "ingestion", "passage_index", "claim_evidence", "evidence_index", "paper_skeleton", "paper_card", "formula_cards", "teaching_cards", "understanding_status", "quality_report"} == artifact_types
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


def test_single_paper_runner_reports_real_pipeline_stages(tmp_path: Path) -> None:
    source = tmp_path / "paper.md"
    source.write_text(
        "# Paper\n## Abstract\nWe study anomaly detection.\n\n## Method\nWe minimize L = x + y.",
        encoding="utf-8",
    )
    workspace = WorkspaceStore(tmp_path / "workspace")
    jobs = JobStore(tmp_path / "jobs.sqlite3")
    updates: list[tuple[str, int]] = []

    job = SinglePaperIngestionRunner(workspace=workspace, jobs=jobs).run(
        source,
        job_id="job-progress",
        progress=lambda stage, value: updates.append((stage, value)),
    )

    assert job.status == JobStatus.SUCCEEDED
    assert [stage for stage, _ in updates] == [
        "preparing_source",
        "parsing_document",
        "indexing_evidence",
        "building_paper_card",
        "building_formula_cards",
        "formula_cards_ready",
        "building_teaching_cards",
        "auditing_understanding",
        "writing_artifacts",
    ]
    assert [value for _, value in updates] == sorted(value for _, value in updates)
