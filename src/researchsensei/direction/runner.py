from __future__ import annotations

import logging
import re
import time
from pathlib import Path

from researchsensei.acquisition import ArxivAdapter, CrossrefAdapter, OpenAlexAdapter, SemanticScholarAdapter
from researchsensei.query import QueryPlanner
from researchsensei.relevance_judge import RelevanceJudge
from researchsensei.schemas import (
    CandidatePaper,
    DirectionBundle,
    PaperSourceStatus,
    QueryPlan,
    ReadingPlan,
    SourceResolutionResult,
    VerificationStatus,
)
from researchsensei.selection import SelectionService
from researchsensei.source_resolver import PaperSourceResolver
from researchsensei.verification import CandidateVerifier
from researchsensei.workspace import WorkspaceStore

logger = logging.getLogger(__name__)


class DirectionRunner:
    """Orchestrates M1: query planning -> acquisition -> dedup -> verify -> relevance -> download -> reading plan.

    Key ordering: verification + LLM relevance happen BEFORE PDF download.
    Only verified+relevant candidates with should_download=true are downloaded.
    """

    def __init__(
        self,
        workspace: WorkspaceStore,
        query_planner: QueryPlanner | None = None,
        arxiv_adapter: ArxivAdapter | None = None,
        openalex_adapter: OpenAlexAdapter | None = None,
        semantic_scholar_adapter: SemanticScholarAdapter | None = None,
        crossref_adapter: CrossrefAdapter | None = None,
        selection_service: SelectionService | None = None,
        source_resolver: PaperSourceResolver | None = None,
        verifier: CandidateVerifier | None = None,
        relevance_judge: RelevanceJudge | None = None,
        sources: list[str] | None = None,
        max_results_per_source: int = 20,
    ) -> None:
        self.workspace = workspace
        self.query_planner = query_planner or QueryPlanner()
        self.arxiv_adapter = arxiv_adapter or ArxivAdapter()
        self.openalex_adapter = openalex_adapter or OpenAlexAdapter()
        self.semantic_scholar_adapter = semantic_scholar_adapter or SemanticScholarAdapter()
        self.crossref_adapter = crossref_adapter or CrossrefAdapter()
        self.selection_service = selection_service or SelectionService()
        self.source_resolver = source_resolver or PaperSourceResolver(network_enabled=True)
        self.verifier = verifier or CandidateVerifier()
        self.relevance_judge = relevance_judge or RelevanceJudge()
        self.sources = sources or ["arxiv", "openalex", "semantic_scholar", "crossref"]
        self.max_results_per_source = max_results_per_source

    async def run(self, user_query: str, direction_id: str | None = None) -> DirectionBundle:
        actual_id = direction_id or _slugify(user_query)
        run_dir = self.workspace.new_run_dir(actual_id)

        query_plan = await self.query_planner.plan(user_query)
        query = query_plan.english_query or query_plan.direction_en or query_plan.user_query

        # Step 1: Acquire candidates from all sources
        candidates, acquisition_warnings, search_log, source_metrics = self._acquire(query_plan)
        raw_pool = self.selection_service.build_candidate_pool(
            query=query,
            candidates=candidates,
            search_log=search_log,
            warnings=acquisition_warnings,
            source_metrics=source_metrics,
        )

        # Step 2: Deduplicate
        deduplicated = self.selection_service.deduplicate(candidates)

        # Step 3: Verify candidates (BEFORE download)
        verified_candidates = self.verifier.verify_batch(deduplicated)

        # Step 4: LLM relevance judgment (BEFORE download)
        llm_judged_candidates, relevance_metadata = await self.relevance_judge.judge_with_score(
            query, verified_candidates
        )

        # Step 5: Select candidates for download
        # Only download: verified/relevant + should_download=true
        download_candidates = [
            c for c in llm_judged_candidates
            if self._should_download(c)
        ]
        download_ids = {c.paper_id for c in download_candidates}

        # Step 6: Download PDFs for selected candidates
        source_resolution = SourceResolutionResult(query=query, items=[], warnings=[])
        if download_candidates:
            source_resolution = self.source_resolver.resolve_many(
                query=query,
                candidates=download_candidates,
                download_dir=Path(run_dir) / "source_pdfs",
            )

        # Step 7: Apply source resolution back to ALL candidates
        resolved_candidates = self._apply_source_resolution(llm_judged_candidates, source_resolution)

        # Step 8: Build filtered_candidates from final candidates
        filtered_candidates = self.selection_service.build_candidate_pool(
            query=query,
            candidates=resolved_candidates,
            search_log=search_log + [
                "dedup: applied before verification",
                f"verified: {sum(1 for c in resolved_candidates if c.verification_status == VerificationStatus.VERIFIED)}/{len(resolved_candidates)}",
                f"llm_judged: {relevance_metadata.get('llm_judged_candidate_count', 0)}",
                f"download_selected: {len(download_candidates)}",
            ],
            warnings=acquisition_warnings,
            source_metrics=source_metrics,
        ).model_copy(
            update={
                "retrieved_count": len(candidates),
                "deduplicated_count": len(deduplicated),
            }
        )

        # Step 9: Build reading plan from resolved candidates
        reading_plan = self.selection_service.build_reading_plan(query_plan, resolved_candidates)

        # Compute verification summary
        verification_summary = {
            "verified_candidate_count": sum(1 for c in resolved_candidates if c.verification_status == VerificationStatus.VERIFIED),
            "unverified_candidate_count": sum(1 for c in resolved_candidates if c.verification_status == VerificationStatus.UNVERIFIED),
            "verify_pending_count": sum(1 for c in resolved_candidates if c.verification_status == VerificationStatus.VERIFY_PENDING),
            "error_count": sum(1 for c in resolved_candidates if c.verification_status == VerificationStatus.ERROR),
        }

        # Write artifacts
        self.workspace.write_json(run_dir / "query_plan.json", query_plan)
        self.workspace.write_json(run_dir / "candidate_pool.json", raw_pool)
        self.workspace.write_json(run_dir / "source_resolution.json", source_resolution)
        self.workspace.write_json(run_dir / "filtered_candidates.json", filtered_candidates)
        self.workspace.write_json(run_dir / "reading_plan.json", reading_plan)

        return DirectionBundle(
            query_plan=query_plan,
            candidate_pool=raw_pool,
            source_resolution=source_resolution,
            filtered_candidates=filtered_candidates,
            reading_plan=reading_plan,
            warnings=(
                query_plan.warnings
                + acquisition_warnings
                + [warning.code for warning in source_resolution.warnings]
                + reading_plan.warnings
            ),
            verification_summary=verification_summary,
            relevance_summary=relevance_metadata,
        )

    @staticmethod
    def _should_download(candidate: CandidatePaper) -> bool:
        """Gate for PDF download: only verified + relevant + should_download."""
        return (
            candidate.verification_status == VerificationStatus.VERIFIED
            and candidate.should_download is True
            and candidate.llm_relevance_score >= 0.65
            and candidate.llm_relevance_label in ("HIGH", "MEDIUM")
            and candidate.rule_relevance_score >= 0.45
        )

    def _acquire(
        self,
        query_plan: QueryPlan,
    ) -> tuple[list[CandidatePaper], list[str], list[str], list[dict[str, object]]]:
        query = query_plan.english_query or query_plan.direction_en or query_plan.user_query
        candidates: list[CandidatePaper] = []
        warnings: list[str] = []
        search_log: list[str] = []
        source_metrics: list[dict[str, object]] = []

        for source in self.sources:
            started = time.perf_counter()
            try:
                adapter = self._adapter_for(source)
                results = adapter.search(query, max_results=self.max_results_per_source)
                candidates.extend(results)
                latency_ms = int((time.perf_counter() - started) * 1000)
                search_log.append(f"{source}: searched ({len(results)} results)")
                source_metrics.append(
                    {
                        "source": source,
                        "attempted": True,
                        "success": True,
                        "count": len(results),
                        "latency_ms": latency_ms,
                        "error": "",
                    }
                )
            except Exception as exc:
                latency_ms = int((time.perf_counter() - started) * 1000)
                msg = f"ACQUISITION_FAILED:{source}: {type(exc).__name__}: {str(exc)[:160]}"
                logger.warning(msg)
                warnings.append(msg)
                search_log.append(f"{source}: failed ({type(exc).__name__})")
                source_metrics.append(
                    {
                        "source": source,
                        "attempted": True,
                        "success": False,
                        "count": 0,
                        "latency_ms": latency_ms,
                        "error": f"{type(exc).__name__}: {str(exc)[:200]}",
                    }
                )

        return candidates, warnings, search_log, source_metrics

    def _adapter_for(self, source: str):
        if source == "arxiv":
            return self.arxiv_adapter
        if source == "openalex":
            return self.openalex_adapter
        if source == "semantic_scholar":
            return self.semantic_scholar_adapter
        if source == "crossref":
            return self.crossref_adapter
        raise ValueError(f"Unknown source: {source}")

    @staticmethod
    def _apply_source_resolution(
        candidates: list[CandidatePaper],
        source_resolution: SourceResolutionResult,
    ) -> list[CandidatePaper]:
        by_paper_id = {item.paper_id: item for item in source_resolution.items}
        updated: list[CandidatePaper] = []
        for candidate in candidates:
            resolved = by_paper_id.get(candidate.paper_id)
            if resolved is None:
                updated.append(candidate)
                continue
            pdf_downloaded = resolved.status == PaperSourceStatus.RESOLVED_PDF_DOWNLOADED
            pdf_available = bool(candidate.pdf_url or resolved.pdf_url)
            can_enter_m2 = bool(pdf_downloaded and resolved.local_path and resolved.sha256)
            source_confidence = "high" if pdf_downloaded else ("medium" if pdf_available else candidate.source_confidence)
            metadata_confidence = candidate.metadata_confidence
            if source_confidence == "high" and metadata_confidence == "low":
                metadata_confidence = "medium"
            updated.append(
                candidate.model_copy(
                    update={
                        "pdf_url": candidate.pdf_url or resolved.pdf_url,
                        "landing_url": candidate.landing_url or resolved.landing_url,
                        "source_url": candidate.source_url or resolved.source_url,
                        "pdf_available": pdf_available,
                        "pdf_downloaded": pdf_downloaded,
                        "can_enter_m2": can_enter_m2,
                        "source_confidence": source_confidence,
                        "metadata_confidence": metadata_confidence,
                        "raw_source_metadata": {
                            **candidate.raw_source_metadata,
                            "source_resolution": {
                                "status": resolved.status.value,
                                "local_path": resolved.local_path,
                                "sha256": resolved.sha256,
                                "file_size": resolved.file_size,
                                "content_type": resolved.content_type,
                                "pdf_metadata_check": resolved.pdf_metadata_check,
                                "pdf_title_match": resolved.pdf_title_match,
                            },
                        },
                    }
                )
            )
        return updated


def _slugify(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[-\s]+", "-", slug).strip("-")
    return slug[:50] or "direction"
