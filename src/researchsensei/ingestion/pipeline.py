from __future__ import annotations

import shutil
from pathlib import Path

from researchsensei.formula_card import build_formula_cards
from researchsensei.grounding import build_evidence_index
from researchsensei.ingestion.lightweight import LightweightIngestionService
from researchsensei.jobs import JobStore
from researchsensei.paper_card import build_paper_card
from researchsensei.paper_skeleton import build_paper_skeleton
from researchsensei.parser.adapter import ParserAdapter
from researchsensei.schemas import JobRecord, JobStatus, SourceStatus, WarningItem, WorkspaceArtifact
from researchsensei.teaching_card import build_teaching_cards
from researchsensei.workspace import WorkspaceStore


class SinglePaperIngestionRunner:
    def __init__(
        self,
        workspace: WorkspaceStore,
        jobs: JobStore,
        ingestion: LightweightIngestionService | None = None,
        parser_adapter: ParserAdapter | None = None,
    ) -> None:
        self.workspace = workspace
        self.jobs = jobs
        self.ingestion = ingestion or LightweightIngestionService()
        self.parser_adapter = parser_adapter

    def run(
        self,
        source_path: str | Path,
        job_id: str | None = None,
        source_status: SourceStatus | None = None,
    ) -> JobRecord:
        source = Path(source_path)
        actual_job_id = job_id or source.stem
        run_dir = self.workspace.new_run_dir(actual_job_id)
        copied_source = run_dir / f"source{source.suffix.lower()}"
        if source.resolve() != copied_source.resolve():
            shutil.copy2(source, copied_source)
        resolved_source_status = self._source_status(source_status, source, copied_source)

        job = JobRecord(
            job_id=actual_job_id,
            source_path=str(copied_source),
            run_dir=str(run_dir),
            current_step="ingestion_started",
        )
        self.jobs.create(job)

        try:
            if self.parser_adapter is not None:
                if not self.parser_adapter.supports(copied_source):
                    raise ValueError(
                        f"Parser adapter does not support source type: {copied_source.suffix}"
                    )
                result = self.parser_adapter.parse(copied_source, paper_id=actual_job_id)
                document = result.document
            else:
                document = self.ingestion.ingest_path(copied_source, paper_id=actual_job_id)
            evidence_index = build_evidence_index(document)
            paper_skeleton = build_paper_skeleton(document, evidence_index)
            paper_card = build_paper_card(paper_skeleton, evidence_index)
            formula_cards = build_formula_cards(document, evidence_index, paper_skeleton)
            teaching_cards = build_teaching_cards(paper_card, formula_cards, paper_skeleton, evidence_index)
        except Exception as exc:
            error_summary = f"{type(exc).__name__}: {str(exc)[:200]}"
            return self.jobs.update(
                actual_job_id,
                status=JobStatus.FAILED,
                current_step="pipeline_error",
                error=error_summary,
                warnings=[WarningItem(code="PIPELINE_FAILED", message=error_summary)],
            )
        source_status_path = run_dir / "source_status.json"
        parsed_path = run_dir / "parsed_document.json"
        evidence_path = run_dir / "evidence_index.json"
        skeleton_path = run_dir / "paper_skeleton.json"
        card_path = run_dir / "paper_card.json"
        formula_path = run_dir / "formula_cards.json"
        teaching_path = run_dir / "teaching_cards.json"
        self.workspace.write_json(source_status_path, resolved_source_status)
        self.workspace.write_json(parsed_path, document)
        self.workspace.write_json(evidence_path, evidence_index)
        self.workspace.write_json(skeleton_path, paper_skeleton)
        self.workspace.write_json(card_path, paper_card)
        self.workspace.write_json(formula_path, formula_cards)
        self.workspace.write_json(teaching_path, teaching_cards)

        current_step = "ingestion_degraded" if document.degraded else "ingestion_completed"
        return self.jobs.update(
            actual_job_id,
            status=JobStatus.SUCCEEDED,
            current_step=current_step,
            warnings=document.warnings,
            artifacts=[
                WorkspaceArtifact(artifact_type="ingestion", path=str(parsed_path)),
                WorkspaceArtifact(artifact_type="source_status", path=str(source_status_path)),
                WorkspaceArtifact(artifact_type="evidence_index", path=str(evidence_path)),
                WorkspaceArtifact(artifact_type="paper_skeleton", path=str(skeleton_path)),
                WorkspaceArtifact(artifact_type="paper_card", path=str(card_path)),
                WorkspaceArtifact(artifact_type="formula_cards", path=str(formula_path)),
                WorkspaceArtifact(artifact_type="teaching_cards", path=str(teaching_path)),
            ],
        )

    def _source_status(
        self,
        source_status: SourceStatus | None,
        original_source: Path,
        copied_source: Path,
    ) -> SourceStatus:
        if source_status is not None:
            return source_status.model_copy(
                update={
                    "resolved_path": str(copied_source),
                    "size_bytes": copied_source.stat().st_size,
                }
            )
        return SourceStatus(
            source_type="upload",
            original_input=original_source.name,
            resolved_path=str(copied_source),
            status="resolved",
            content_type=self._content_type(copied_source),
            size_bytes=copied_source.stat().st_size,
        )

    def _content_type(self, path: Path) -> str:
        return {
            ".md": "text/markdown",
            ".txt": "text/plain",
            ".pdf": "application/pdf",
        }.get(path.suffix.lower(), "")
