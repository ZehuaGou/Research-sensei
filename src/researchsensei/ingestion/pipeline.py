from __future__ import annotations

import asyncio
import logging
import shutil
from collections.abc import Callable
from pathlib import Path

from researchsensei.audit.quality_auditor import QualityAuditor
from researchsensei.evidence.claim_extractor import build_claim_evidence
from researchsensei.evidence.evidence_pack import build_evidence_pack
from researchsensei.evidence.passage_index import build_passage_index
from researchsensei.evidence.retriever import EvidenceRetriever
from researchsensei.formula_card_baseline import build_formula_cards as build_formula_cards_baseline
from researchsensei.formula_card import build_formula_cards
from researchsensei.grounding import build_evidence_index
from researchsensei.ingestion.lightweight import LightweightIngestionService
from researchsensei.jobs import DuplicateSourceJobError, JobStore
from researchsensei.llm.client import LLMClient
from researchsensei.paper_card_baseline import build_paper_card as build_paper_card_baseline
from researchsensei.paper_card import (
    build_paper_card,
    looks_like_paper_card_raw_copy,
    summarize_paper_card_field,
)
from researchsensei.paper_skeleton import build_paper_skeleton
from researchsensei.parser.adapter import ParserAdapter
from researchsensei.schemas import (
    ArtifactBundle,
    BlockType,
    ClaimEvidenceBundle,
    DownstreamGates,
    EvidencePack,
    DocumentBlock,
    DocumentIngestion,
    JobRecord,
    JobStatus,
    PaperCard,
    QualityReport,
    SourceStatus,
    UnderstandingStatus,
    WarningItem,
    WorkspaceArtifact,
)
from researchsensei.schemas.status import EvidencePackSummary
from researchsensei.teaching_card_baseline import build_teaching_cards as build_teaching_cards_baseline
from researchsensei.teaching_card import build_teaching_cards
from researchsensei.workspace import WorkspaceStore

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[str, int], None]


def _run_async_builder(coro):
    """Execute an async card builder from a sync context.

    Raises RuntimeError if already inside an active event loop.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # No running loop; safe to use asyncio.run.
        return asyncio.run(coro)
    # Close coroutine to avoid "was never awaited" warning
    if hasattr(coro, "close"):
        coro.close()
    raise RuntimeError(
        "SinglePaperIngestionRunner.run cannot execute async LLM builders "
        "inside an active event loop"
    )


class SinglePaperIngestionRunner:
    def __init__(
        self,
        workspace: WorkspaceStore,
        jobs: JobStore,
        ingestion: LightweightIngestionService | None = None,
        parser_adapter: ParserAdapter | None = None,
        llm_client: LLMClient | None = None,
        quality_auditor: QualityAuditor | None = None,
    ) -> None:
        self.workspace = workspace
        self.jobs = jobs
        self.ingestion = ingestion or LightweightIngestionService()
        self.parser_adapter = parser_adapter
        self.llm_client = llm_client
        self.quality_auditor = quality_auditor or QualityAuditor()

    def run(
        self,
        source_path: str | Path,
        job_id: str | None = None,
        source_status: SourceStatus | None = None,
        source_identity: str = "",
        title_hint: str = "",
        progress: ProgressCallback | None = None,
    ) -> JobRecord:
        report = progress or (lambda _stage, _value: None)
        source = Path(source_path)
        actual_job_id = job_id or source.stem
        run_dir = self.workspace.new_run_dir(actual_job_id)
        report("preparing_source", 14)
        copied_source = run_dir / f"source{source.suffix.lower()}"
        if source.resolve() != copied_source.resolve():
            shutil.copy2(source, copied_source)
        resolved_source_status = self._source_status(source_status, source, copied_source)

        job = JobRecord(
            job_id=actual_job_id,
            source_path=str(copied_source),
            run_dir=str(run_dir),
            source_identity=source_identity,
            current_step="ingestion_started",
        )
        try:
            self.jobs.create(job)
        except DuplicateSourceJobError as error:
            return error.job

        try:
            self.jobs.update(
                actual_job_id,
                status=JobStatus.RUNNING,
                current_step="parsing_document",
            )
            report("parsing_document", 20)
            # Common preprocessing
            if self.parser_adapter is not None:
                if not self.parser_adapter.supports(copied_source):
                    raise ValueError(
                        f"Parser adapter does not support source type: {copied_source.suffix}"
                    )
                result = self.parser_adapter.parse(copied_source, paper_id=actual_job_id)
                document = result.document
            else:
                document = self.ingestion.ingest_path(copied_source, paper_id=actual_job_id)
            document = _apply_title_hint(document, title_hint)
            report("indexing_evidence", 32)
            passage_index = build_passage_index(document)
            claim_evidence = build_claim_evidence(document, passage_index)
            evidence_index = build_evidence_index(document)
            paper_skeleton = build_paper_skeleton(document, evidence_index)
            evidence_pack: EvidencePack | None = None
            formula_evidence_pack: EvidencePack | None = None
            structural_artifacts = self._write_structural_artifacts(
                run_dir,
                resolved_source_status,
                document,
                passage_index,
                claim_evidence,
                evidence_index,
                paper_skeleton,
            )
            self.jobs.update(
                actual_job_id,
                current_step="evidence_ready",
                artifacts=structural_artifacts,
            )

            if self.llm_client is None:
                # Baseline path
                report("building_paper_card", 50)
                paper_card = build_paper_card_baseline(paper_skeleton, evidence_index)
                report("building_formula_cards", 58)
                formula_cards = build_formula_cards_baseline(document, evidence_index, paper_skeleton)
                report("formula_cards_ready", 84)
                report("building_teaching_cards", 88)
                teaching_cards = build_teaching_cards_baseline(paper_card, formula_cards, paper_skeleton, evidence_index)
                understanding_status = _build_baseline_understanding_status(actual_job_id)
                card_artifacts = {
                    "paper_card": paper_card,
                    "formula_cards": formula_cards,
                    "teaching_cards": teaching_cards,
                }
            else:
                # LLM card path
                report("building_evidence_pack", 42)
                evidence_pack = build_evidence_pack(claim_evidence, passage_index, EvidenceRetriever())
                formula_claim_count = sum(
                    1 for claim in claim_evidence.claims
                    if claim.claim_type == "FORMULA_CONTEXT"
                )
                formula_evidence_pack = build_evidence_pack(
                    claim_evidence,
                    passage_index,
                    None,
                    max_total_tokens=max(5000, formula_claim_count * 1800),
                    max_items_per_type=0,
                    max_formula_items=max(formula_claim_count, 0),
                    max_passage_chars=1600,
                )
                evidence_pack_summary = _build_evidence_pack_summary(evidence_pack, claim_evidence)
                structural_artifacts = self._write_structural_artifacts(
                    run_dir,
                    resolved_source_status,
                    document,
                    passage_index,
                    claim_evidence,
                    evidence_index,
                    paper_skeleton,
                    evidence_pack=evidence_pack,
                    formula_evidence_pack=formula_evidence_pack,
                )
                self.jobs.update(
                    actual_job_id,
                    current_step="evidence_ready",
                    artifacts=structural_artifacts,
                )

                if not evidence_pack.items:
                    understanding_status = _build_blocked_status(
                        actual_job_id,
                        blocking_reason="EMPTY_EVIDENCE_PACK",
                        component_status=_component_status(
                            blocked=True,
                            llm="SKIPPED",
                            evidence_pack="FAILED",
                        ),
                        evidence_pack_summary=evidence_pack_summary,
                    )
                    card_artifacts = {}
                elif not _has_method_evidence(evidence_pack):
                    understanding_status = _build_blocked_status(
                        actual_job_id,
                        blocking_reason="MISSING_METHOD_EVIDENCE",
                        component_status=_component_status(
                            blocked=True,
                            llm="SKIPPED",
                            evidence_pack="SUCCESS",
                        ),
                        evidence_pack_summary=evidence_pack_summary,
                    )
                    card_artifacts = {}
                else:
                    card_artifacts, understanding_status = self._run_card_builders(
                        actual_job_id,
                        evidence_pack,
                        formula_evidence_pack,
                        claim_evidence,
                        passage_index,
                        paper_skeleton,
                        evidence_pack_summary,
                        progress=report,
                    )

        except Exception as exc:
            error_summary = f"{type(exc).__name__}: {str(exc)[:200]}"
            return self.jobs.update(
                actual_job_id,
                status=JobStatus.FAILED,
                current_step="pipeline_error",
                error=error_summary,
                warnings=[WarningItem(code="PIPELINE_FAILED", message=error_summary)],
            )

        # Audit: construct candidate ArtifactBundle and run QualityAuditor
        report("auditing_understanding", 95)
        quality_report, understanding_status, card_artifacts = self._run_audit(
            actual_job_id,
            understanding_status,
            card_artifacts,
            evidence_index,
            claim_evidence,
            passage_index,
            paper_skeleton,
        )

        # Write artifacts
        report("writing_artifacts", 98)
        return self._write_artifacts(
            actual_job_id,
            run_dir,
            document,
            resolved_source_status,
            passage_index,
            claim_evidence,
            evidence_index,
            paper_skeleton,
            understanding_status,
            card_artifacts,
            quality_report,
            evidence_pack=evidence_pack,
            formula_evidence_pack=formula_evidence_pack,
        )

    def _run_audit(
        self,
        paper_id: str,
        understanding_status: UnderstandingStatus,
        card_artifacts: dict,
        evidence_index,
        claim_evidence,
        passage_index,
        paper_skeleton,
    ) -> tuple[QualityReport, UnderstandingStatus, dict]:
        """Run QualityAuditor on candidate artifacts. May override status."""
        card_artifacts = _summarize_raw_copy_paper_card_fields(
            card_artifacts,
            claim_evidence,
            evidence_index,
            paper_skeleton,
        )
        bundle = _build_artifact_bundle(
            paper_card=card_artifacts.get("paper_card"),
            formula_cards=card_artifacts.get("formula_cards"),
            teaching_cards=card_artifacts.get("teaching_cards"),
            evidence_index=evidence_index,
            claim_evidence=claim_evidence,
            passage_index=passage_index,
            paper_skeleton=paper_skeleton,
            understanding_status=understanding_status,
        )

        quality_report = self.quality_auditor.audit(bundle)

        # Check for BLOCK findings
        block_findings = [f for f in quality_report.findings if f.effect == "BLOCK"]
        current_status = understanding_status.status

        # Only override LLM SUCCESS / DEGRADED to BLOCKED
        if block_findings and current_status in ("SUCCESS", "DEGRADED_STRUCTURAL"):
            audit_warnings = _convert_findings_to_warnings(
                [f for f in quality_report.findings if f.effect == "WARNING"]
            )
            understanding_status = _build_blocked_status(
                paper_id,
                blocking_reason="AUDIT_BLOCKED",
                component_status={
                    "paper_card": "FAILED",
                    "formula_cards": "SKIPPED",
                    "teaching_cards": "SKIPPED",
                    "llm": "SUCCESS",
                    "evidence_pack": "SUCCESS",
                    "audit": "FAILED",
                },
                evidence_pack_summary=understanding_status.evidence_pack_summary,
                warnings=audit_warnings,
            )
            card_artifacts = {}

        # Add WARNING findings to status warnings (for non-overridden cases)
        elif not block_findings:
            warning_items = _convert_findings_to_warnings(
                [f for f in quality_report.findings if f.effect == "WARNING"]
            )
            if warning_items:
                understanding_status = understanding_status.model_copy(
                    update={"warnings": [*understanding_status.warnings, *warning_items]}
                )

        return quality_report, understanding_status, card_artifacts

    def _run_card_builders(
        self,
        paper_id: str,
        evidence_pack: EvidencePack,
        formula_evidence_pack: EvidencePack,
        claim_evidence: ClaimEvidenceBundle,
        passage_index,
        paper_skeleton,
        evidence_pack_summary: EvidencePackSummary,
        progress: ProgressCallback | None = None,
    ) -> tuple[dict, UnderstandingStatus]:
        """Execute LLM card builders and return card artifacts + status.

        paper_card and formula_cards have no data dependency, so they run
        in parallel under a single event loop. teaching_cards depends on
        paper_card and runs after both complete.
        """
        llm_client = self.llm_client
        assert llm_client is not None
        report = progress or (lambda _stage, _value: None)

        def formula_progress(completed: int, total: int) -> None:
            if total <= 0:
                report("building_formula_cards:0/0", 84)
                return
            value = 52 + round((completed / total) * 32)
            report(f"building_formula_cards:{completed}/{total}", value)

        async def _run_all() -> tuple[dict, UnderstandingStatus]:
            # paper_card and formula_cards are independent — run in parallel
            report("building_paper_card", 50)
            paper_task = asyncio.create_task(
                build_paper_card(evidence_pack, paper_skeleton, llm_client)
            )
            formula_task = asyncio.create_task(
                build_formula_cards(
                    formula_evidence_pack,
                    paper_skeleton,
                    llm_client,
                    progress=formula_progress,
                )
            )

            paper_card: PaperCard | None = None
            paper_error: Exception | None = None
            formula_cards = None
            formula_error: Exception | None = None

            try:
                paper_card = await paper_task
                report("paper_card_ready", 66)
            except Exception as exc:
                paper_error = exc
                logger.warning("paper_card failed: %s", exc)

            try:
                formula_cards = await formula_task
                report("formula_cards_ready", 84)
            except Exception as exc:
                formula_error = exc
                logger.warning("formula_cards failed: %s", exc)

            # Handle paper_card failure (teaching_cards depends on it)
            if paper_error is not None:
                return {}, _build_blocked_status(
                    paper_id,
                    blocking_reason="PAPER_CARD_FAILED",
                    component_status=_component_status(
                        blocked=True,
                        paper_card="FAILED",
                        evidence_pack="SUCCESS",
                    ),
                    evidence_pack_summary=evidence_pack_summary,
                    warnings=[WarningItem(code="CARD_BUILDER_FAILED", message=f"paper_card: {paper_error}")],
                )

            # Handle formula_cards failure (pipeline stops before teaching_cards)
            if formula_error is not None:
                return {}, _build_blocked_status(
                    paper_id,
                    blocking_reason="FORMULA_CARDS_FAILED",
                    component_status=_component_status(
                        blocked=True,
                        paper_card="SUCCESS",
                        formula_cards="FAILED",
                        evidence_pack="SUCCESS",
                    ),
                    evidence_pack_summary=evidence_pack_summary,
                    warnings=[WarningItem(code="CARD_BUILDER_FAILED", message=f"formula_cards: {formula_error}")],
                )

            # Both succeeded — run teaching_cards
            try:
                report("building_teaching_cards", 88)
                teaching_cards = await build_teaching_cards(evidence_pack, paper_card, paper_skeleton, llm_client)  # type: ignore[arg-type]
                report("teaching_cards_ready", 92)
            except Exception as exc:
                logger.warning("teaching_cards failed: %s", exc)
                return {}, _build_blocked_status(
                    paper_id,
                    blocking_reason="TEACHING_CARDS_FAILED",
                    component_status=_component_status(
                        blocked=True,
                        paper_card="SUCCESS",
                        formula_cards="SUCCESS",
                        teaching_cards="FAILED",
                        evidence_pack="SUCCESS",
                    ),
                    evidence_pack_summary=evidence_pack_summary,
                    warnings=[WarningItem(code="CARD_BUILDER_FAILED", message=f"teaching_cards: {exc}")],
                )

            # Success
            card_artifacts = {
                "paper_card": paper_card,
                "formula_cards": formula_cards,
                "teaching_cards": teaching_cards,
            }
            formula_warnings = _formula_derivation_warnings(formula_cards)
            if formula_warnings:
                understanding_status = _build_degraded_status(
                    paper_id,
                    formula_cards=formula_cards,
                    evidence_pack_summary=evidence_pack_summary,
                    warnings=formula_warnings,
                    blocking_reason="FORMULA_DERIVATION_BLOCKED",
                    formula_cards_status="FAILED",
                    teaching_cards_status="SUCCESS",
                )
            else:
                understanding_status = _build_success_status(
                    paper_id,
                    formula_cards=formula_cards,
                    evidence_pack_summary=evidence_pack_summary,
                )
            return card_artifacts, understanding_status

        return _run_async_builder(_run_all())

    def _write_structural_artifacts(
        self,
        run_dir: Path,
        resolved_source_status,
        document,
        passage_index,
        claim_evidence,
        evidence_index,
        paper_skeleton,
        *,
        evidence_pack: EvidencePack | None = None,
        formula_evidence_pack: EvidencePack | None = None,
    ) -> list[WorkspaceArtifact]:
        """Persist evidence artifacts before slow LLM work without exposing unaudited cards."""
        values = [
            ("source_status", "source_status.json", resolved_source_status),
            ("ingestion", "parsed_document.json", document),
            ("passage_index", "passage_index.json", passage_index),
            ("claim_evidence", "claim_evidence.json", claim_evidence),
            ("evidence_index", "evidence_index.json", evidence_index),
            ("paper_skeleton", "paper_skeleton.json", paper_skeleton),
        ]
        if evidence_pack is not None:
            values.append(("evidence_pack", "evidence_pack.json", evidence_pack))
        if formula_evidence_pack is not None:
            values.append(("formula_evidence_pack", "formula_evidence_pack.json", formula_evidence_pack))

        artifacts: list[WorkspaceArtifact] = []
        for artifact_type, filename, value in values:
            path = run_dir / filename
            self.workspace.write_json(path, value)
            artifacts.append(WorkspaceArtifact(artifact_type=artifact_type, path=str(path)))
        return artifacts

    def _write_artifacts(
        self,
        paper_id: str,
        run_dir: Path,
        document,
        resolved_source_status,
        passage_index,
        claim_evidence,
        evidence_index,
        paper_skeleton,
        understanding_status: UnderstandingStatus,
        card_artifacts: dict,
        quality_report: QualityReport,
        evidence_pack: EvidencePack | None = None,
        formula_evidence_pack: EvidencePack | None = None,
    ) -> JobRecord:
        """Write all artifacts and update job."""
        source_status_path = run_dir / "source_status.json"
        parsed_path = run_dir / "parsed_document.json"
        passage_index_path = run_dir / "passage_index.json"
        claim_evidence_path = run_dir / "claim_evidence.json"
        evidence_path = run_dir / "evidence_index.json"
        skeleton_path = run_dir / "paper_skeleton.json"
        evidence_pack_path = run_dir / "evidence_pack.json"
        formula_evidence_pack_path = run_dir / "formula_evidence_pack.json"
        understanding_status_path = run_dir / "understanding_status.json"
        quality_report_path = run_dir / "quality_report.json"

        self.workspace.write_json(source_status_path, resolved_source_status)
        self.workspace.write_json(parsed_path, document)
        self.workspace.write_json(passage_index_path, passage_index)
        self.workspace.write_json(claim_evidence_path, claim_evidence)
        self.workspace.write_json(evidence_path, evidence_index)
        self.workspace.write_json(skeleton_path, paper_skeleton)
        self.workspace.write_json(understanding_status_path, understanding_status)
        self.workspace.write_json(quality_report_path, quality_report)

        artifacts = [
            WorkspaceArtifact(artifact_type="ingestion", path=str(parsed_path)),
            WorkspaceArtifact(artifact_type="source_status", path=str(source_status_path)),
            WorkspaceArtifact(artifact_type="passage_index", path=str(passage_index_path)),
            WorkspaceArtifact(artifact_type="claim_evidence", path=str(claim_evidence_path)),
            WorkspaceArtifact(artifact_type="evidence_index", path=str(evidence_path)),
            WorkspaceArtifact(artifact_type="paper_skeleton", path=str(skeleton_path)),
        ]

        if evidence_pack is not None:
            self.workspace.write_json(evidence_pack_path, evidence_pack)
            artifacts.append(WorkspaceArtifact(artifact_type="evidence_pack", path=str(evidence_pack_path)))

        if formula_evidence_pack is not None:
            self.workspace.write_json(formula_evidence_pack_path, formula_evidence_pack)
            artifacts.append(WorkspaceArtifact(artifact_type="formula_evidence_pack", path=str(formula_evidence_pack_path)))

        # Write card artifacts if available
        if "paper_card" in card_artifacts:
            card_path = run_dir / "paper_card.json"
            self.workspace.write_json(card_path, card_artifacts["paper_card"])
            artifacts.append(WorkspaceArtifact(artifact_type="paper_card", path=str(card_path)))

        if "formula_cards" in card_artifacts:
            formula_path = run_dir / "formula_cards.json"
            self.workspace.write_json(formula_path, card_artifacts["formula_cards"])
            artifacts.append(WorkspaceArtifact(artifact_type="formula_cards", path=str(formula_path)))

        if "teaching_cards" in card_artifacts:
            teaching_path = run_dir / "teaching_cards.json"
            self.workspace.write_json(teaching_path, card_artifacts["teaching_cards"])
            artifacts.append(WorkspaceArtifact(artifact_type="teaching_cards", path=str(teaching_path)))

        artifacts.append(WorkspaceArtifact(artifact_type="understanding_status", path=str(understanding_status_path)))
        artifacts.append(WorkspaceArtifact(artifact_type="quality_report", path=str(quality_report_path)))

        current_step = "ingestion_degraded" if document.degraded else "ingestion_completed"
        return self.jobs.update(
            paper_id,
            status=JobStatus.SUCCEEDED,
            current_step=current_step,
            warnings=document.warnings,
            artifacts=artifacts,
        )

    def _source_status(
        self,
        source_status: SourceStatus | None,
        original_source: Path,
        copied_source: Path,
    ) -> SourceStatus:
        if source_status is not None:
            update_fields = {
                "resolved_path": str(copied_source),
                "size_bytes": copied_source.stat().st_size,
            }
            if source_status.preferred_m2_input == "latex_source" or copied_source.suffix.lower() == ".tex":
                update_fields.update({
                    "latex_source_path": str(copied_source),
                    "latex_main_file": str(copied_source),
                    "latex_source_available": True,
                })
            return source_status.model_copy(
                update=update_fields
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
            ".tex": "text/x-tex",
        }.get(path.suffix.lower(), "")


def _apply_title_hint(document: DocumentIngestion, title_hint: str) -> DocumentIngestion:
    """Attach trusted request/library title metadata before skeleton construction."""
    title = " ".join(str(title_hint or "").split()).strip()
    if not title:
        return document
    title_block = DocumentBlock(
        block_id="title-meta",
        type=BlockType.TITLE,
        text=title,
        normalized_text=title.casefold(),
        section="title",
        evidence_ref=f"{document.paper_id}:title-meta",
        block_source="request_metadata",
    )
    blocks = [block for block in document.blocks if block.type != BlockType.TITLE]
    return document.model_copy(update={"blocks": [title_block, *blocks]})


# ---------------------------------------------------------------------------
# Status helpers
# ---------------------------------------------------------------------------


def _build_baseline_understanding_status(paper_id: str) -> UnderstandingStatus:
    return UnderstandingStatus(
        paper_id=paper_id,
        status="BASELINE_ONLY",
        blocking_reason="NO_LLM_CLIENT",
        allowed_for_user_display=False,
        allowed_downstream=DownstreamGates(),
        component_status={
            "paper_card": "BASELINE",
            "formula_cards": "BASELINE",
            "teaching_cards": "BASELINE",
            "llm": "SKIPPED",
            "evidence_pack": "SKIPPED",
        },
        checked_artifacts=[
            "source_status", "parsed_document", "passage_index",
            "claim_evidence", "evidence_index", "paper_skeleton",
            "paper_card", "formula_cards", "teaching_cards",
        ],
    )


def _build_success_status(
    paper_id: str,
    formula_cards,
    evidence_pack_summary: EvidencePackSummary,
    warnings: list[WarningItem] | None = None,
) -> UnderstandingStatus:
    formula_status = "SKIPPED" if not formula_cards.formula_cards else "SUCCESS"
    return UnderstandingStatus(
        paper_id=paper_id,
        status="SUCCESS",
        blocking_reason="",
        warnings=warnings or [],
        allowed_for_user_display=True,
        allowed_downstream=DownstreamGates(
            reading_display=True,
            learning_patterns=True,
            learning_drills=True,
            learning_drills_degraded=False,
            advisor_questions=True,
        ),
        component_status={
            "paper_card": "SUCCESS",
            "formula_cards": formula_status,
            "teaching_cards": "SUCCESS",
            "llm": "SUCCESS",
            "evidence_pack": "SUCCESS",
        },
        checked_artifacts=[
            "source_status", "parsed_document", "passage_index",
            "claim_evidence", "evidence_index", "paper_skeleton",
            "paper_card", "formula_cards", "teaching_cards",
        ],
        evidence_pack_summary=evidence_pack_summary,
    )


def _build_degraded_status(
    paper_id: str,
    formula_cards,
    evidence_pack_summary: EvidencePackSummary,
    warnings: list[WarningItem] | None = None,
    *,
    blocking_reason: str = "TEACHING_CARDS_FAILED",
    formula_cards_status: str | None = None,
    teaching_cards_status: str = "FAILED",
) -> UnderstandingStatus:
    formula_status = formula_cards_status or ("SKIPPED" if not formula_cards.formula_cards else "SUCCESS")
    teaching_succeeded = teaching_cards_status == "SUCCESS"
    return UnderstandingStatus(
        paper_id=paper_id,
        status="DEGRADED_STRUCTURAL",
        blocking_reason=blocking_reason,
        warnings=warnings or [],
        allowed_for_user_display=True,
        allowed_downstream=DownstreamGates(
            reading_display=True,
            learning_patterns=True,
            learning_drills=teaching_succeeded,
            learning_drills_degraded=not teaching_succeeded,
            advisor_questions=True,
        ),
        component_status={
            "paper_card": "SUCCESS",
            "formula_cards": formula_status,
            "teaching_cards": teaching_cards_status,
            "llm": "SUCCESS",
            "evidence_pack": "SUCCESS",
        },
        checked_artifacts=[
            "source_status", "parsed_document", "passage_index",
            "claim_evidence", "evidence_index", "paper_skeleton",
            "paper_card", "formula_cards",
        ],
        evidence_pack_summary=evidence_pack_summary,
    )


def _build_blocked_status(
    paper_id: str,
    blocking_reason: str,
    component_status: dict[str, str],
    evidence_pack_summary: EvidencePackSummary | None = None,
    warnings: list[WarningItem] | None = None,
) -> UnderstandingStatus:
    return UnderstandingStatus(
        paper_id=paper_id,
        status="BLOCKED_UNDERSTANDING",
        blocking_reason=blocking_reason,
        warnings=warnings or [],
        allowed_for_user_display=False,
        allowed_downstream=DownstreamGates(),
        component_status=component_status,
        checked_artifacts=[
            "source_status", "parsed_document", "passage_index",
            "claim_evidence", "evidence_index", "paper_skeleton",
        ],
        evidence_pack_summary=evidence_pack_summary,
    )


def _component_status(
    blocked: bool = False,
    paper_card: str = "SKIPPED",
    formula_cards: str = "SKIPPED",
    teaching_cards: str = "SKIPPED",
    llm: str = "FAILED",
    evidence_pack: str = "SUCCESS",
    audit: str = "SKIPPED",
) -> dict[str, str]:
    if blocked:
        return {
            "paper_card": paper_card,
            "formula_cards": formula_cards,
            "teaching_cards": teaching_cards,
            "llm": llm,
            "evidence_pack": evidence_pack,
            "audit": audit,
        }
    return {}


def _has_method_evidence(evidence_pack: EvidencePack) -> bool:
    return any(item.claim_type == "METHOD" for item in evidence_pack.items)


def _formula_derivation_warnings(formula_cards) -> list[WarningItem]:
    cards = getattr(formula_cards, "formula_cards", []) or []
    blocked = [
        card for card in cards
        if getattr(card, "derivation_status", "") == "blocked"
        or getattr(card, "coverage_status", "") == "BLOCKED_RAW_ONLY"
    ]
    if not blocked:
        return []
    origins = sorted({
        str(getattr(card, "formula_origin", "") or "unknown")
        for card in blocked
    })
    return [
        WarningItem(
            code="FORMULA_DERIVATION_BLOCKED",
            message="Formula derivation was blocked because formula provenance is raw or unknown.",
            detail=f"blocked_formula_count={len(blocked)}; formula_origins={','.join(origins)}",
        )
    ]


def _build_evidence_pack_summary(
    evidence_pack: EvidencePack,
    claim_bundle: ClaimEvidenceBundle,
) -> EvidencePackSummary:
    included = [item.claim_id for item in evidence_pack.items]
    included_set = set(included)
    excluded = [c.claim_id for c in claim_bundle.claims if c.claim_id not in included_set]
    claim_type_counts: dict[str, int] = {}
    for item in evidence_pack.items:
        claim_type_counts[item.claim_type] = claim_type_counts.get(item.claim_type, 0) + 1
    return EvidencePackSummary(
        included_claim_ids=included,
        excluded_claim_ids=excluded,
        total_tokens=evidence_pack.total_tokens,
        claim_type_counts=claim_type_counts,
        truncated_passage_ids=[],
    )


def _summarize_raw_copy_paper_card_fields(
    card_artifacts: dict,
    claim_evidence,
    evidence_index,
    paper_skeleton,
) -> dict:
    paper_card = card_artifacts.get("paper_card")
    if paper_card is None:
        return card_artifacts
    data = paper_card if isinstance(paper_card, dict) else paper_card.model_dump(mode="json")
    evidence_by_ref = _evidence_text_by_ref(claim_evidence, evidence_index)
    changed = False
    warnings = list(data.get("warnings") or [])
    for field in ("problem", "core_idea", "method_overview", "experiment_summary"):
        claim = data.get(field)
        if not isinstance(claim, dict):
            continue
        ref = str(claim.get("evidence_ref") or "")
        text = str(claim.get("text") or "")
        evidence_text = evidence_by_ref.get(ref, "")
        if ref and looks_like_paper_card_raw_copy(text, evidence_text):
            claim["text"] = summarize_paper_card_field(field, evidence_text, paper_skeleton)
            warnings.append(f"PAPER_CARD_FIELD_SUMMARIZED_FROM_RAW_COPY: {field}")
            changed = True
    if not changed:
        return card_artifacts
    data["warnings"] = list(dict.fromkeys(warnings))
    updated = dict(card_artifacts)
    updated["paper_card"] = PaperCard.model_validate(data)
    return updated


def _evidence_text_by_ref(claim_evidence, evidence_index) -> dict[str, str]:
    by_ref: dict[str, list[str]] = {}
    for bundle in (claim_evidence, evidence_index):
        for claim in getattr(bundle, "claims", []) or []:
            ref = str(_field(claim, "evidence_ref") or "")
            if not ref:
                continue
            text = (
                _field(claim, "quote_or_summary")
                or _field(claim, "source_sentence")
                or _field(claim, "claim_text")
                or ""
            )
            if text:
                by_ref.setdefault(ref, []).append(str(text))
    return {ref: " ".join(values) for ref, values in by_ref.items()}


def _field(obj, name: str):
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


def _build_artifact_bundle(
    *,
    paper_card=None,
    formula_cards=None,
    teaching_cards=None,
    evidence_index=None,
    claim_evidence=None,
    passage_index=None,
    paper_skeleton=None,
    understanding_status=None,
) -> ArtifactBundle:
    """Build ArtifactBundle from in-memory objects for audit."""
    def _to_dict(obj):
        if obj is None:
            return None
        if isinstance(obj, dict):
            return obj
        return obj.model_dump(mode="json")

    return ArtifactBundle(
        paper_card=_to_dict(paper_card),
        formula_cards=_to_dict(formula_cards),
        teaching_cards=_to_dict(teaching_cards),
        evidence_index=_to_dict(evidence_index),
        claim_evidence=_to_dict(claim_evidence),
        passage_index=_to_dict(passage_index),
        paper_skeleton=_to_dict(paper_skeleton),
        understanding_status=_to_dict(understanding_status),
    )


def _convert_findings_to_warnings(findings) -> list[WarningItem]:
    """Convert AuditFinding WARNING items to WarningItem for UnderstandingStatus."""
    items: list[WarningItem] = []
    for f in findings:
        items.append(WarningItem(
            code=f.code,
            message=f.message,
            detail=f"artifact={f.artifact}; field={f.field}; severity={f.severity}; effect={f.effect}",
        ))
    return items
