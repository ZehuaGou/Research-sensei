from __future__ import annotations

import asyncio
import logging
import shutil
from pathlib import Path

from researchsensei.evidence.claim_extractor import build_claim_evidence
from researchsensei.evidence.evidence_pack import build_evidence_pack
from researchsensei.evidence.passage_index import build_passage_index
from researchsensei.evidence.retriever import EvidenceRetriever
from researchsensei.formula_card import build_formula_cards
from researchsensei.formula_card_v2 import build_formula_cards_v2
from researchsensei.grounding import build_evidence_index
from researchsensei.ingestion.lightweight import LightweightIngestionService
from researchsensei.jobs import JobStore
from researchsensei.llm.client import LLMClient, MockLLMClient
from researchsensei.paper_card import build_paper_card
from researchsensei.paper_card_v2 import build_paper_card_v2
from researchsensei.paper_skeleton import build_paper_skeleton
from researchsensei.parser.adapter import ParserAdapter
from researchsensei.schemas import (
    ClaimEvidenceBundle,
    DownstreamGates,
    EvidencePack,
    JobRecord,
    JobStatus,
    SourceStatus,
    UnderstandingStatus,
    WarningItem,
    WorkspaceArtifact,
)
from researchsensei.schemas.status import EvidencePackSummary
from researchsensei.teaching_card import build_teaching_cards
from researchsensei.teaching_card_v2 import build_teaching_cards_v2
from researchsensei.workspace import WorkspaceStore

logger = logging.getLogger(__name__)


def _run_async_builder(coro):
    """Execute an async v2 builder from a sync context.

    Raises RuntimeError if already inside an active event loop.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # No running loop — safe to use asyncio.run
        return asyncio.run(coro)
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
        llm_client: LLMClient | MockLLMClient | None = None,
    ) -> None:
        self.workspace = workspace
        self.jobs = jobs
        self.ingestion = ingestion or LightweightIngestionService()
        self.parser_adapter = parser_adapter
        self.llm_client = llm_client

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
            passage_index = build_passage_index(document)
            claim_evidence = build_claim_evidence(document, passage_index)
            evidence_index = build_evidence_index(document)
            paper_skeleton = build_paper_skeleton(document, evidence_index)

            if self.llm_client is None:
                # Baseline path
                paper_card = build_paper_card(paper_skeleton, evidence_index)
                formula_cards = build_formula_cards(document, evidence_index, paper_skeleton)
                teaching_cards = build_teaching_cards(paper_card, formula_cards, paper_skeleton, evidence_index)
                understanding_status = _build_baseline_understanding_status(actual_job_id)
                card_artifacts = {
                    "paper_card": paper_card,
                    "formula_cards": formula_cards,
                    "teaching_cards": teaching_cards,
                }
            else:
                # V2 path
                evidence_pack = build_evidence_pack(claim_evidence, passage_index, EvidenceRetriever())
                evidence_pack_summary = _build_evidence_pack_summary(evidence_pack, claim_evidence)

                if not evidence_pack.items:
                    understanding_status = _build_blocked_status(
                        actual_job_id,
                        blocking_reason="EMPTY_EVIDENCE_PACK",
                        component_status=_component_status(blocked=True),
                        evidence_pack_summary=evidence_pack_summary,
                    )
                    card_artifacts = {}
                elif not _has_method_evidence(evidence_pack):
                    understanding_status = _build_blocked_status(
                        actual_job_id,
                        blocking_reason="MISSING_METHOD_EVIDENCE",
                        component_status=_component_status(blocked=True),
                        evidence_pack_summary=evidence_pack_summary,
                    )
                    card_artifacts = {}
                else:
                    card_artifacts, understanding_status = self._run_v2_builders(
                        actual_job_id,
                        evidence_pack,
                        claim_evidence,
                        passage_index,
                        paper_skeleton,
                        evidence_pack_summary,
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

        # Write artifacts
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
        )

    def _run_v2_builders(
        self,
        paper_id: str,
        evidence_pack: EvidencePack,
        claim_evidence: ClaimEvidenceBundle,
        passage_index,
        paper_skeleton,
        evidence_pack_summary: EvidencePackSummary,
    ) -> tuple[dict, UnderstandingStatus]:
        """Execute v2 builders and return card artifacts + status."""
        llm_client = self.llm_client
        assert llm_client is not None

        # Paper card v2
        try:
            paper_card = _run_async_builder(
                build_paper_card_v2(evidence_pack, paper_skeleton, llm_client)
            )
        except Exception as exc:
            logger.warning("paper_card_v2 failed: %s", exc)
            return {}, _build_blocked_status(
                paper_id,
                blocking_reason="PAPER_CARD_V2_FAILED",
                component_status=_component_status(blocked=True, paper_card="FAILED"),
                evidence_pack_summary=evidence_pack_summary,
                warnings=[WarningItem(code="V2_BUILDER_FAILED", message=f"paper_card_v2: {exc}")],
            )

        # Formula cards v2
        try:
            formula_cards = _run_async_builder(
                build_formula_cards_v2(evidence_pack, paper_skeleton, llm_client)
            )
        except Exception as exc:
            logger.warning("formula_cards_v2 failed: %s", exc)
            return {}, _build_blocked_status(
                paper_id,
                blocking_reason="FORMULA_CARDS_V2_FAILED",
                component_status=_component_status(
                    blocked=True,
                    paper_card="SUCCESS",
                    formula_cards="FAILED",
                ),
                evidence_pack_summary=evidence_pack_summary,
                warnings=[WarningItem(code="V2_BUILDER_FAILED", message=f"formula_cards_v2: {exc}")],
            )

        # Teaching cards v2
        try:
            teaching_cards = _run_async_builder(
                build_teaching_cards_v2(evidence_pack, paper_card, paper_skeleton, llm_client)
            )
            # Success
            card_artifacts = {
                "paper_card": paper_card,
                "formula_cards": formula_cards,
                "teaching_cards": teaching_cards,
            }
            understanding_status = _build_success_status(
                paper_id,
                formula_cards=formula_cards,
                evidence_pack_summary=evidence_pack_summary,
            )
            return card_artifacts, understanding_status

        except Exception as exc:
            logger.warning("teaching_cards_v2 failed: %s", exc)
            # Teaching failure → DEGRADED, but still write paper_card + formula_cards
            card_artifacts = {
                "paper_card": paper_card,
                "formula_cards": formula_cards,
            }
            understanding_status = _build_degraded_status(
                paper_id,
                formula_cards=formula_cards,
                evidence_pack_summary=evidence_pack_summary,
                warnings=[WarningItem(code="V2_BUILDER_FAILED", message=f"teaching_cards_v2: {exc}")],
            )
            return card_artifacts, understanding_status

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
    ) -> JobRecord:
        """Write all artifacts and update job."""
        source_status_path = run_dir / "source_status.json"
        parsed_path = run_dir / "parsed_document.json"
        passage_index_path = run_dir / "passage_index.json"
        claim_evidence_path = run_dir / "claim_evidence.json"
        evidence_path = run_dir / "evidence_index.json"
        skeleton_path = run_dir / "paper_skeleton.json"
        understanding_status_path = run_dir / "understanding_status.json"

        self.workspace.write_json(source_status_path, resolved_source_status)
        self.workspace.write_json(parsed_path, document)
        self.workspace.write_json(passage_index_path, passage_index)
        self.workspace.write_json(claim_evidence_path, claim_evidence)
        self.workspace.write_json(evidence_path, evidence_index)
        self.workspace.write_json(skeleton_path, paper_skeleton)
        self.workspace.write_json(understanding_status_path, understanding_status)

        artifacts = [
            WorkspaceArtifact(artifact_type="ingestion", path=str(parsed_path)),
            WorkspaceArtifact(artifact_type="source_status", path=str(source_status_path)),
            WorkspaceArtifact(artifact_type="passage_index", path=str(passage_index_path)),
            WorkspaceArtifact(artifact_type="claim_evidence", path=str(claim_evidence_path)),
            WorkspaceArtifact(artifact_type="evidence_index", path=str(evidence_path)),
            WorkspaceArtifact(artifact_type="paper_skeleton", path=str(skeleton_path)),
        ]

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
            phase12_patterns=True,
            phase12_drill=True,
            phase12_drill_degraded=False,
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
) -> UnderstandingStatus:
    formula_status = "SKIPPED" if not formula_cards.formula_cards else "SUCCESS"
    return UnderstandingStatus(
        paper_id=paper_id,
        status="DEGRADED_STRUCTURAL",
        blocking_reason="TEACHING_CARDS_FAILED",
        warnings=warnings or [],
        allowed_for_user_display=True,
        allowed_downstream=DownstreamGates(
            reading_display=True,
            phase12_patterns=True,
            phase12_drill=True,
            phase12_drill_degraded=True,
            advisor_questions=False,
        ),
        component_status={
            "paper_card": "SUCCESS",
            "formula_cards": formula_status,
            "teaching_cards": "FAILED",
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
) -> dict[str, str]:
    if blocked:
        return {
            "paper_card": paper_card,
            "formula_cards": formula_cards,
            "teaching_cards": teaching_cards,
            "llm": "FAILED",
            "evidence_pack": "FAILED",
        }
    return {}


def _has_method_evidence(evidence_pack: EvidencePack) -> bool:
    return any(item.claim_type == "METHOD" for item in evidence_pack.items)


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
