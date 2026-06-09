from __future__ import annotations

import logging
import re
import time
from pathlib import Path

from researchsensei.acquisition import ArxivAdapter, CrossrefAdapter, OpenAlexAdapter, SemanticScholarAdapter
from researchsensei.canonical import MaterialNormalizer
from researchsensei.query import QueryPlanner
from researchsensei.relevance_judge import RelevanceJudge
from researchsensei.schemas import (
    CandidatePaper,
    CanonicalizationResult,
    DirectionBundle,
    PaperSourceStatus,
    QueryPlan,
    ReadingPlan,
    SourceResolutionResult,
    SourcePriority,
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
        material_normalizer: MaterialNormalizer | None = None,
        sources: list[str] | None = None,
        max_results_per_source: int = 20,
        max_canonicalize_candidates: int | None = None,
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
        self.material_normalizer = material_normalizer or MaterialNormalizer()
        self.sources = sources or ["arxiv", "openalex", "semantic_scholar", "crossref"]
        self.max_results_per_source = max_results_per_source
        self.max_canonicalize_candidates = max_canonicalize_candidates

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
        # Download: verified/relevant + should_download=true, OR arxiv papers with PDF URLs
        download_candidates = [
            c for c in llm_judged_candidates
            if self._should_download(c) or self._should_download_arxiv(c)
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

        # Step 7.5: Material normalization — generate canonical_paper.md for each candidate
        canonicalization_results = self._canonicalize_resolved_candidates(
            resolved_candidates,
            source_resolution,
            Path(run_dir) / "canonical_papers",
        )

        # Update candidates with canonical fields
        by_canon = {cr.paper_id: cr for cr in canonicalization_results}
        resolved_candidates = self._apply_canonicalization(resolved_candidates, by_canon)

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

        # Always write a fresh summary so live eval never reads stale canonicalization data.
        canon_summary = {
            "total": len(canonicalization_results),
            "canonical_paper_generated_count": sum(1 for cr in canonicalization_results if cr.canonical_paper_path),
            "m2_ready_count": sum(1 for cr in canonicalization_results if cr.m2_ready),
            "metadata_only_blocked_count": sum(1 for cr in canonicalization_results if cr.source_priority == SourcePriority.METADATA_ONLY),
            "source_type_distribution": {},
            "canonicalization_status_distribution": {},
            "canonical_quality_status_distribution": {},
            "adapter_status": {},
        }
        for cr in canonicalization_results:
            st = cr.source_type
            canon_summary["source_type_distribution"][st] = canon_summary["source_type_distribution"].get(st, 0) + 1
            cs = cr.canonicalization_status.value
            canon_summary["canonicalization_status_distribution"][cs] = canon_summary["canonicalization_status_distribution"].get(cs, 0) + 1
            qs = cr.canonical_quality_status.value
            canon_summary["canonical_quality_status_distribution"][qs] = canon_summary["canonical_quality_status_distribution"].get(qs, 0) + 1
            for ai in cr.adapter_info:
                canon_summary["adapter_status"][ai.name] = ai.status.value
        self.workspace.write_json(run_dir / "canonicalization_summary.json", canon_summary)

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

    def _canonicalize_resolved_candidates(
        self,
        resolved_candidates: list[CandidatePaper],
        source_resolution: SourceResolutionResult,
        canonical_dir: Path,
    ) -> list[CanonicalizationResult]:
        by_source = {item.paper_id: item for item in source_resolution.items}
        candidates_with_source = [
            candidate for candidate in resolved_candidates
            if candidate.paper_id in by_source and by_source[candidate.paper_id].has_valid_deep_reading_source
        ]
        limit = self.max_canonicalize_candidates
        if limit is not None:
            candidates_with_source = candidates_with_source[:max(limit, 0)]

        canonicalization_results: list[CanonicalizationResult] = []
        for candidate in candidates_with_source:
            source_item = by_source.get(candidate.paper_id)
            try:
                canon_result = self.material_normalizer.normalize(
                    candidate, source_item, output_dir=canonical_dir / (candidate.paper_id or "unknown")
                )
                canonicalization_results.append(canon_result)
            except Exception as exc:
                logger.warning("MaterialNormalizer failed for %s: %s", candidate.paper_id, exc)
        return canonicalization_results

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

    @staticmethod
    def _should_download_arxiv(candidate: CandidatePaper) -> bool:
        """Always try to download arXiv papers with PDF URLs (reliable source)."""
        return (
            candidate.verification_status == VerificationStatus.VERIFIED
            and bool(candidate.arxiv_id)
            and bool(candidate.pdf_url)
            and candidate.rule_relevance_score >= 0.3
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
    def _apply_canonicalization(
        candidates: list[CandidatePaper],
        by_canon: dict[str, CanonicalizationResult],
    ) -> list[CandidatePaper]:
        """Apply canonicalization results to candidates."""
        updated: list[CandidatePaper] = []
        for candidate in candidates:
            canon = by_canon.get(candidate.paper_id)
            if canon is None:
                updated.append(candidate)
                continue
            updated.append(
                candidate.model_copy(
                    update={
                        "source_priority": canon.source_priority,
                        "preferred_m2_input": canon.preferred_m2_input,
                        "has_valid_deep_reading_source": canon.has_valid_deep_reading_source,
                        "canonicalization_status": canon.canonicalization_status,
                        "canonical_quality_status": canon.canonical_quality_status,
                        "canonical_paper_path": canon.canonical_paper_path,
                        "m2_ready": canon.m2_ready,
                        "degradation_reason": canon.degradation_reason,
                        "metadata_only": canon.source_priority == SourcePriority.METADATA_ONLY,
                    }
                )
            )
        return updated

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
                        "source_priority": resolved.source_priority,
                        "preferred_m2_input": resolved.preferred_m2_input,
                        "has_valid_deep_reading_source": resolved.has_valid_deep_reading_source,
                        "metadata_only": not resolved.has_valid_deep_reading_source,
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
