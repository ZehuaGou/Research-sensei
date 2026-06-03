from __future__ import annotations

import asyncio
import shutil
from dataclasses import dataclass
from pathlib import Path

from backend.drill import DrillService
from backend.formula import FormulaService
from backend.grounding import GroundingService
from backend.ingestion import PdfTextExtractor
from backend.ingestion import IngestionService
from backend.jobs import JobStore
from backend.patterns import PatternService
from backend.query import QueryService
from backend.render import RenderService
from backend.schemas import (
    CandidatePaper,
    DocumentIngestion,
    DrillCard,
    EvidenceIndex,
    FormulaCard,
    JobRecord,
    JobStatus,
    PatternCard,
    PaperSkeleton,
    QueryPlan,
    ReadingPlan,
    TeachingCard,
    WorkspaceArtifact,
)
from backend.selection import SelectionService
from backend.teaching import TeachingService
from backend.understanding import UnderstandingService
from backend.workspace import WorkspaceStore


@dataclass(frozen=True)
class DirectionLearningBundle:
    query_plan: QueryPlan
    reading_plan: ReadingPlan


@dataclass(frozen=True)
class PaperLearningBundle:
    document: DocumentIngestion
    evidence: EvidenceIndex
    skeleton: PaperSkeleton
    paper_card: TeachingCard
    formula_cards: list[FormulaCard]
    pattern_card: PatternCard
    drill_card: DrillCard


class ResearchSenseiPipeline:
    """Minimal v0.5 vertical pipeline.

    This class is intentionally thin. Each domain module keeps its own contract;
    the pipeline only coordinates artifacts so the product is not a pile of
    independent helpers.
    """

    def __init__(
        self,
        query_service: QueryService | None = None,
        selection_service: SelectionService | None = None,
        ingestion_service: IngestionService | None = None,
        grounding_service: GroundingService | None = None,
        understanding_service: UnderstandingService | None = None,
        teaching_service: TeachingService | None = None,
        formula_service: FormulaService | None = None,
        pattern_service: PatternService | None = None,
        drill_service: DrillService | None = None,
    ) -> None:
        self.query_service = query_service or QueryService()
        self.selection_service = selection_service or SelectionService()
        self.ingestion_service = ingestion_service or IngestionService()
        self.grounding_service = grounding_service or GroundingService()
        self.understanding_service = understanding_service or UnderstandingService()
        self.teaching_service = teaching_service or TeachingService()
        self.formula_service = formula_service or FormulaService()
        self.pattern_service = pattern_service or PatternService()
        self.drill_service = drill_service or DrillService()

    async def plan_direction(self, query: str, candidates: list[CandidatePaper], max_a_read: int = 5) -> DirectionLearningBundle:
        query_plan = await self.query_service.understand(query)
        reading_plan = self.selection_service.build_reading_plan(
            topic=query_plan.direction_en or query,
            candidates=candidates,
            max_a_read=max_a_read,
        )
        return DirectionLearningBundle(query_plan=query_plan, reading_plan=reading_plan)

    async def build_paper_learning_bundle(
        self,
        paper_id: str,
        text: str,
        *,
        source_kind: str = "full_text",
        source_warnings: list[str] | None = None,
    ) -> PaperLearningBundle:
        document = self.ingestion_service.ingest_text(paper_id=paper_id, text=text)
        warnings = list(source_warnings or [])
        if source_kind == "metadata_only":
            warnings.append("SOURCE_KIND:METADATA_ONLY")
            warnings.append("METADATA_ONLY_SOURCE")
        if warnings:
            document = document.model_copy(update={
                "extraction_warnings": [*document.extraction_warnings, *warnings],
            })
        evidence = self.grounding_service.build_index(document)
        skeleton = await self.understanding_service.build_skeleton(document, evidence)
        paper_card = await self.teaching_service.build_paper_card(skeleton)
        formula_cards = [
            await self.formula_service.build_formula_card(
                card_id=f"formula_{paper_id}_{index + 1}",
                paper_id=paper_id,
                formula_block=formula,
            )
            for index, formula in enumerate(document.formulas)
        ]
        pattern_card = await self.pattern_service.build_pattern_card(
            card_id=f"pattern_{paper_id}",
            pattern_id=skeleton.pattern_candidates[0] if skeleton.pattern_candidates else "Research Pattern",
            skeleton=skeleton,
        )
        drill_card = await self.drill_service.build_drill_card(skeleton)
        return PaperLearningBundle(
            document=document,
            evidence=evidence,
            skeleton=skeleton,
            paper_card=paper_card,
            formula_cards=formula_cards,
            pattern_card=pattern_card,
            drill_card=drill_card,
        )


class ArtifactPipelineRunner:
    def __init__(
        self,
        job_store: JobStore,
        workspace: WorkspaceStore,
        pipeline: ResearchSenseiPipeline | None = None,
        renderer: RenderService | None = None,
        pdf_extractor: PdfTextExtractor | None = None,
    ) -> None:
        self.job_store = job_store
        self.workspace = workspace
        self.pipeline = pipeline or ResearchSenseiPipeline()
        self.renderer = renderer or RenderService()
        self.pdf_extractor = pdf_extractor or PdfTextExtractor()

    async def run_uploaded_paper(self, job_id: str) -> JobRecord:
        job = self.job_store.update(job_id, status=JobStatus.RUNNING, current_step="ingestion", error="", artifacts=[])
        run_dir = Path(job.run_dir)
        artifacts: list[WorkspaceArtifact] = []
        warnings: list[str] = []
        try:
            text, extract_warnings = self.pdf_extractor.extract(Path(job.source_path))
            warnings.extend(extract_warnings)
            bundle = await self.pipeline.build_paper_learning_bundle(
                job.paper_id if hasattr(job, "paper_id") else job.job_id,
                text,
                source_kind="full_text",
                source_warnings=warnings,
            )
            artifacts.extend(self._write_bundle(run_dir, job, bundle, warnings=warnings))
            return self.job_store.update(
                job_id,
                status=JobStatus.SUCCEEDED,
                current_step="done",
                warnings=[*warnings, *bundle.document.extraction_warnings],
                artifacts=artifacts,
            )
        except Exception as error:
            self.job_store.update(job_id, status=JobStatus.FAILED, current_step="failed", error=str(error), warnings=warnings)
            raise

    async def run_text_source(self, job_id: str, text: str, warnings: list[str] | None = None) -> JobRecord:
        job = self.job_store.update(job_id, status=JobStatus.RUNNING, current_step="ingestion", error="", artifacts=[])
        run_dir = Path(job.run_dir)
        warning_list = warnings or []
        try:
            bundle = await self.pipeline.build_paper_learning_bundle(
                job.job_id,
                text,
                source_kind="metadata_only",
                source_warnings=warning_list,
            )
            artifacts = self._write_bundle(run_dir, job, bundle, warnings=warning_list)
            return self.job_store.update(
                job_id,
                status=JobStatus.SUCCEEDED,
                current_step="done",
                warnings=[*warning_list, *bundle.document.extraction_warnings],
                artifacts=artifacts,
            )
        except Exception as error:
            self.job_store.update(job_id, status=JobStatus.FAILED, current_step="failed", error=str(error), warnings=warning_list)
            raise

    def _write_bundle(
        self,
        run_dir: Path,
        job: JobRecord,
        bundle: PaperLearningBundle,
        warnings: list[str] | None = None,
    ) -> list[WorkspaceArtifact]:
        artifacts: list[WorkspaceArtifact] = []
        json_dir = run_dir / "cards" / "json"
        html_dir = run_dir / "cards" / "html"
        data = {
            "parsed_document": bundle.document,
            "evidence_index": bundle.evidence,
            "paper_skeleton": bundle.skeleton,
            "paper_card": bundle.paper_card,
            "pattern_card": bundle.pattern_card,
            "drill_card": bundle.drill_card,
        }
        for name, value in data.items():
            path = self.workspace.write_json(run_dir / f"{name}.json", value)
            artifacts.append(WorkspaceArtifact(artifact_type=name, path=str(path)))
        for index, card in enumerate(bundle.formula_cards, start=1):
            path = self.workspace.write_json(json_dir / f"formula_card_{index}.json", card)
            artifacts.append(WorkspaceArtifact(artifact_type="formula_card", path=str(path)))
        self.workspace.write_json(json_dir / "paper_card.json", bundle.paper_card)
        html = self.renderer.render_learning_workspace(
            title=job.filename,
            paper_card=bundle.paper_card,
            formula_cards=bundle.formula_cards,
            pattern_card=bundle.pattern_card,
            drill_card=bundle.drill_card,
            job_id=job.job_id,
            warnings=[*(job.warnings or []), *(warnings or []), *bundle.document.extraction_warnings],
        )
        html_path = self.workspace.write_text(html_dir / "learning_workspace.html", html)
        artifacts.append(WorkspaceArtifact(artifact_type="learning_workspace", path=str(html_path)))
        return artifacts

    def zip_artifacts(self, job: JobRecord) -> Path:
        archive_base = Path(job.run_dir) / f"{job.job_id}-artifacts"
        archive = shutil.make_archive(str(archive_base), "zip", job.run_dir)
        return Path(archive)
