from __future__ import annotations

import logging
import re
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Protocol

from researchsensei.acquisition import (
    OpenAlexAdapter,
    SemanticScholarAdapter,
    make_default_search_adapter,
)
from researchsensei.acquisition.fulltext_resolver import FullTextResolver
from researchsensei.core.config import DEFAULT_SEARCH_MAX_RESULTS
from researchsensei.library import PaperLibraryStore
from researchsensei.ranking import PaperRanker, select_downloads
from researchsensei.relevance import (
    MIN_DEEP_READ_RELEVANCE_SCORE,
    MIN_RELEVANCE_SCORE,
    DeterministicRelevanceEvaluator,
    passes_strict_relevance_gate,
)
from researchsensei.schemas import (
    CanonicalQualityStatus,
    CandidatePaper,
    CandidatePool,
    DirectionBundle,
    M1LayerStatus,
    PaperSourceStatus,
    QueryPlan,
    ReadingPlan,
    SearchIntent,
    SourceResolutionResult,
    VerificationStatus,
)
from researchsensei.selection import SelectionService
from researchsensei.query import QueryPlanningError
from researchsensei.source_resolver import PaperSourceResolver
from researchsensei.verification import CandidateVerifier

logger = logging.getLogger(__name__)


class SearchAdapter(Protocol):
    def search(self, query: str, max_results: int = 20) -> list[CandidatePaper]:
        ...


class QueryPlannerAdapter(Protocol):
    async def plan(self, user_query: str) -> QueryPlan:
        ...


class DirectionExplorationService:
    """Minimal M1 direction exploration loop over real paper-source adapters."""

    def __init__(
        self,
        *,
        adapters: dict[str, SearchAdapter] | None = None,
        selection_service: SelectionService | None = None,
        verifier: CandidateVerifier | None = None,
        source_resolver: PaperSourceResolver | None = None,
        fulltext_resolver: FullTextResolver | None = None,
        sources: list[str] | None = None,
        max_results_per_source: int = DEFAULT_SEARCH_MAX_RESULTS,
        max_verify_candidates: int = 12,
        max_download_candidates: int | None = 0,
        max_search_queries: int = 12,
        source_download_dir: str | Path | None = None,
        paper_library: PaperLibraryStore | None = None,
        fallback_adapters: dict[str, SearchAdapter] | None = None,
        paper_ranker: PaperRanker | None = None,
        query_planner: QueryPlannerAdapter | None = None,
        relevance_evaluator: DeterministicRelevanceEvaluator | None = None,
    ) -> None:
        if adapters is None:
            default_adapters: dict[str, SearchAdapter] = {
                "paper_search": make_default_search_adapter(),
            }
            default_fallback_adapters: dict[str, SearchAdapter] = {
                "openalex_fallback": OpenAlexAdapter(),
                "semantic_scholar_fallback": SemanticScholarAdapter(),
            }
        else:
            default_adapters = adapters
            default_fallback_adapters = {}
        self.adapters = default_adapters
        self.fallback_adapters = fallback_adapters if fallback_adapters is not None else default_fallback_adapters
        self.sources = sources or list(self.adapters.keys())
        self.selection_service = selection_service or SelectionService()
        self.verifier = verifier or CandidateVerifier(timeout_seconds=8.0)
        self.source_resolver = source_resolver or PaperSourceResolver(network_enabled=False)
        self.fulltext_resolver = fulltext_resolver or FullTextResolver(timeout_seconds=12.0)
        self.max_results_per_source = max_results_per_source
        self.max_verify_candidates = max_verify_candidates
        self.max_download_candidates = max_download_candidates
        self.max_search_queries = max(max_search_queries, 1)
        self.source_download_dir = Path(source_download_dir) if source_download_dir else None
        self.paper_library = paper_library
        self.paper_ranker = paper_ranker or PaperRanker()
        self.query_planner = query_planner
        self.relevance_evaluator = relevance_evaluator or DeterministicRelevanceEvaluator()

    def explore(
        self,
        user_query: str,
        *,
        progress: Callable[[str, int], None] | None = None,
    ) -> DirectionBundle:
        query = " ".join(user_query.split())
        if not query:
            return self._empty_bundle(
                query,
                status="BLOCKED",
                message="Direction query is empty.",
                warnings=["EMPTY_QUERY"],
            )

        report = progress or (lambda _stage, _value: None)
        report("planning_query", 5)
        query_plan = self._build_query_plan(query)
        search_query = query_plan.english_query or query_plan.direction_en or query_plan.user_query
        acquisition_variants = _unique([query_plan.user_query, *query_plan.query_variants])
        report("searching_sources", 12)
        candidates, warnings, search_log, source_metrics = self._acquire(
            search_query,
            query_variants=acquisition_variants,
            query_plan=query_plan,
        )
        report("deduplicating", 30)
        raw_pool = self.selection_service.build_candidate_pool(
            query=search_query,
            candidates=candidates,
            search_log=search_log,
            warnings=warnings,
            source_metrics=source_metrics,
        )
        deduplicated = self.selection_service.deduplicate(candidates)
        report("verifying_candidates", 38)
        verified = self._verify(deduplicated)
        # Apply the deterministic task/concept gate before issuing DOI,
        # repository, and landing-page requests. A large OA supplement can
        # contain 100+ candidates; only relevance-cleared papers need costly
        # full-text discovery for ranking and download selection.
        relevance_screened = self.relevance_evaluator.evaluate_and_rank(query_plan, verified)
        fulltext_targets = [
            candidate for candidate in relevance_screened
            if passes_strict_relevance_gate(candidate)
        ]
        report("discovering_fulltext", 48)
        enriched_targets, fulltext_metrics = self.fulltext_resolver.resolve_many(fulltext_targets, download_top_n=0)
        enriched_by_id = {candidate.paper_id: candidate for candidate in enriched_targets}
        fulltext_enriched = [
            enriched_by_id.get(candidate.paper_id, candidate)
            for candidate in relevance_screened
        ]
        source_metrics = [*source_metrics, *fulltext_metrics]
        report("ranking_candidates", 65)
        externally_ranked = self.paper_ranker.rank(search_query, fulltext_enriched)
        ranked_candidates = self.relevance_evaluator.evaluate_and_rank(query_plan, externally_ranked)
        download_queue = select_downloads(
            ranked_candidates,
            max_download_candidates=self.max_download_candidates,
            paper_library=self.paper_library,
            require_relevance_gate=True,
        )
        download_candidates = [candidate for candidate in download_queue if candidate.download_selected]
        download_dir = _direction_download_dir(self.source_download_dir, query_plan)
        report("downloading_fulltext", 75)
        source_resolution = self.source_resolver.resolve_many(
            search_query,
            download_candidates,
            download_dir=download_dir,
        )
        report("assembling_results", 92)
        resolved = self._apply_source_resolution(download_queue, source_resolution)
        reading_plan = self.selection_service.build_reading_plan(query_plan, resolved, include_ignored=True)
        card_candidates = _candidate_cards_from_reading_plan(reading_plan)
        filtered_candidates = self.selection_service.build_candidate_pool(
            query=search_query,
            candidates=[item.paper for item in reading_plan.items],
            search_log=search_log,
            warnings=warnings + reading_plan.warnings,
            source_metrics=source_metrics,
        ).model_copy(
            update={
                "retrieved_count": len(candidates),
                "deduplicated_count": len(deduplicated),
            }
        )

        download_attempt_count = len(source_resolution.items)
        downloaded_count = sum(
            1
            for item in source_resolution.items
            if item.has_valid_deep_reading_source and item.download_status == "downloaded"
        )
        download_quality_warnings = _download_attempt_warnings(download_attempt_count, downloaded_count)
        status, message = self._status_and_message(
            source_metrics=source_metrics,
            candidate_count=len(candidates),
            visible_candidate_count=len(card_candidates),
            recommended_candidate_count=sum(1 for item in reading_plan.items if item.priority != "D_IGNORE"),
            warning_count=len(warnings),
            download_selected_count=sum(1 for candidate in resolved if candidate.download_selected),
            downloaded_count=downloaded_count,
            download_attempt_count=download_attempt_count,
            download_failed_count=max(download_attempt_count - downloaded_count, 0),
        )
        relevance_passed_count = sum(1 for candidate in resolved if candidate.relevance_gate_passed)
        if candidates and relevance_passed_count == 0:
            status = "DEGRADED"
            message = (
                "Direction discovery completed, but no candidate passed the deterministic "
                "task/concept relevance gate. No paper was selected for deep reading."
            )
        pipeline_status = _pipeline_layer_status(
            source_metrics=source_metrics,
            candidate_count=len(candidates),
            warning_count=len(warnings),
            download_attempt_count=download_attempt_count,
            downloaded_count=downloaded_count,
        )
        relevance_status = _relevance_layer_status(resolved)
        source_status = _source_layer_status(resolved)
        understanding_status = _understanding_layer_status(resolved)
        overview = _overview(query_plan, len(reading_plan.items), status)
        key_sub_directions = _key_sub_directions(query_plan, reading_plan)
        method_families = _method_families(query_plan, reading_plan)
        deep_read_candidates = [
            card for card in card_candidates
            if (
                card.get("priority") in {"A_READ", "A_READ_FOR_M2"}
                and card.get("can_enter_m2") is True
                and card.get("deep_read_relevance_passed") is True
            )
        ]

        return DirectionBundle(
            status=status,
            direction_workspace_status=status,
            pipeline_status=pipeline_status,
            relevance_status=relevance_status,
            source_status=source_status,
            understanding_status=understanding_status,
            query=query,
            message=message,
            overview=overview,
            key_sub_directions=key_sub_directions,
            method_families=method_families,
            candidate_cards=card_candidates,
            recommended_reading_order=_reading_order(reading_plan),
            deep_read_candidates=deep_read_candidates,
            source_metrics=source_metrics,
            query_plan=query_plan,
            candidate_pool=raw_pool,
            source_resolution=source_resolution,
            filtered_candidates=filtered_candidates,
            reading_plan=reading_plan,
            warnings=(
                query_plan.warnings
                + warnings
                + download_quality_warnings
                + [warning.code for warning in source_resolution.warnings]
                + reading_plan.warnings
                + (["NO_CANDIDATE_PASSED_RELEVANCE_GATE"] if relevance_passed_count == 0 else [])
            ),
            verification_summary=_verification_summary(resolved),
            relevance_summary=_relevance_summary(reading_plan),
        )

    def _build_query_plan(self, query: str) -> QueryPlan:
        if self.query_planner is None:
            return build_heuristic_query_plan(query)

        try:
            plan = _run_query_planner(self.query_planner, query)
            return _complete_query_plan(plan, fallback_query=query)
        except QueryPlanningError as exc:
            logger.warning("LLM query planner failed; falling back to heuristic query plan: %s", exc)
            return _heuristic_with_planner_warning(query, exc)
        except Exception as exc:
            logger.warning("Unexpected query planner failure; falling back to heuristic query plan: %s", exc)
            return _heuristic_with_planner_warning(query, exc)

    def _acquire(
        self,
        query: str,
        *,
        query_variants: list[str] | None = None,
        query_plan: QueryPlan | None = None,
    ) -> tuple[list[CandidatePaper], list[str], list[str], list[dict[str, object]]]:
        candidates: list[CandidatePaper] = []
        warnings: list[str] = []
        search_log: list[str] = []
        source_metrics: list[dict[str, object]] = []

        queries_to_search = _prioritized_search_queries(
            query,
            query_variants or [],
            limit=self.max_search_queries,
        )

        for source_idx, source in enumerate(self.sources):
            # Polite delay between sources to avoid burst rate-limiting
            if source_idx > 0:
                time.sleep(1.0)

            adapter = self.adapters.get(source)
            if adapter is None:
                warnings.append(f"ACQUISITION_FAILED:{source}: adapter not configured")
                source_metrics.append({
                    "source": source,
                    "attempted": True,
                    "success": False,
                    "count": 0,
                    "latency_ms": 0,
                    "error": "adapter not configured",
                })
                search_log.append(f"{source}: failed (adapter missing)")
                continue

            source_candidates: list[CandidatePaper] = []
            total_latency = 0
            source_error = ""
            adapter_responded = False
            rate_limited = False
            empty_response_count = 0
            for q_idx, q in enumerate(queries_to_search):
                # Polite delay between variants
                if q_idx > 0:
                    time.sleep(0.5)
                started = time.perf_counter()
                try:
                    results = adapter.search(q, max_results=self.max_results_per_source)
                    source_candidates.extend(results)
                    adapter_responded = True
                    if results:
                        empty_response_count = 0
                    else:
                        empty_response_count += 1
                    latency_ms = int((time.perf_counter() - started) * 1000)
                    total_latency += latency_ms
                    search_log.append(f"{source}: searched '{q[:60]}' ({len(results)} results)")
                    if _preserves_primary_search_order(source) and q_idx == 0 and results:
                        search_log.append(f"{source}: primary query returned results; kept external result pool and skipped venue variants")
                        break
                    if _preserves_primary_search_order(source) and empty_response_count >= 2 and not source_candidates:
                        search_log.append(f"{source}: skipped remaining variants after repeated empty results")
                        break
                except Exception as exc:
                    latency_ms = int((time.perf_counter() - started) * 1000)
                    total_latency += latency_ms
                    is_rate_limit = "429" in str(exc) or "rate" in str(exc).lower()
                    is_transient_source_failure = _is_transient_source_failure(exc)
                    is_blocked_source_failure = _is_blocked_source_failure(exc)
                    if is_rate_limit:
                        rate_limited = True
                    logger.warning("Direction acquisition failed for %s (%s): %s", source, q[:40], exc)
                    source_error = f"{type(exc).__name__}: {str(exc)[:160]}"
                    search_log.append(f"{source}: failed '{q[:40]}' ({type(exc).__name__})")
                    if is_rate_limit:
                        search_log.append(f"{source}: skipped remaining variants after rate limit")
                        break
                    if is_blocked_source_failure:
                        search_log.append(f"{source}: skipped remaining variants after source blocked/captcha")
                        break
                    if is_transient_source_failure:
                        search_log.append(f"{source}: skipped remaining variants after transient source failure")
                        break

            if adapter_responded:
                candidates.extend(source_candidates)
                source_metrics.append({
                    "source": source,
                    "attempted": True,
                    "success": True,
                    "count": len(source_candidates),
                    "latency_ms": total_latency,
                    "error": "",
                    "rate_limited": rate_limited,
                })
            else:
                warning = f"ACQUISITION_FAILED:{source}: {source_error}" if source_error else f"ACQUISITION_FAILED:{source}: no results"
                warnings.append(warning)
                source_metrics.append({
                    "source": source,
                    "attempted": True,
                    "success": False,
                    "count": 0,
                    "latency_ms": total_latency,
                    "error": source_error or "no results",
                    "rate_limited": rate_limited,
                })

        if not candidates and self.fallback_adapters:
            primary_source = self.sources[0] if self.sources else "paper_search"
            primary_warning = (
                f"PRIMARY_DISCOVERY_BLOCKED:{primary_source}"
                if _has_blocked_warning(warnings)
                else f"PRIMARY_DISCOVERY_EMPTY:{primary_source}"
            )
            fallback_candidates, fallback_warnings, fallback_log, fallback_metrics = self._acquire_fallback(
                query,
                query_variants=query_variants,
                primary_warning=primary_warning,
                primary_source=primary_source,
            )
            candidates.extend(fallback_candidates)
            warnings.extend(fallback_warnings)
            search_log.extend(fallback_log)
            source_metrics.extend(fallback_metrics)
        elif candidates and self.fallback_adapters:
            supplement_reasons = _discovery_supplement_reasons(
                query,
                candidates,
                expected_count=min(max(self.max_results_per_source, 1), 8),
                query_plan=query_plan,
                relevance_evaluator=self.relevance_evaluator,
            )
            if supplement_reasons:
                search_log.append(
                    "primary discovery needs OA supplement: " + ", ".join(supplement_reasons)
                )
                fallback_candidates, fallback_warnings, fallback_log, fallback_metrics = self._acquire_fallback(
                    query,
                    query_variants=query_variants,
                    primary_warning="",
                    primary_source=self.sources[0] if self.sources else "paper_search",
                    query_limit=3,
                    trigger="low_coverage_oa_supplement",
                )
                candidates.extend(fallback_candidates)
                warnings.extend(fallback_warnings)
                search_log.extend(fallback_log)
                source_metrics.extend(fallback_metrics)

        return candidates, warnings, search_log, source_metrics

    def _acquire_fallback(
        self,
        query: str,
        *,
        query_variants: list[str] | None = None,
        primary_warning: str = "PRIMARY_DISCOVERY_EMPTY:paper_search",
        primary_source: str = "paper_search",
        query_limit: int | None = None,
        trigger: str = "primary_empty_or_blocked",
    ) -> tuple[list[CandidatePaper], list[str], list[str], list[dict[str, object]]]:
        warnings = [primary_warning] if primary_warning else []
        fallback_failures: list[str] = []
        candidates: list[CandidatePaper] = []
        search_log = (
            [f"{primary_source}: {primary_warning}; trying fallback discovery"]
            if primary_warning
            else [f"{primary_source}: supplementing discovery with open-access indexes"]
        )
        source_metrics: list[dict[str, object]] = []
        queries_to_search = _prioritized_search_queries(
            query,
            query_variants or [],
            limit=query_limit or self.max_search_queries,
        )
        for source, adapter in self.fallback_adapters.items():
            source_candidates: list[CandidatePaper] = []
            total_latency = 0
            source_error = ""
            adapter_responded = False
            for q_idx, q in enumerate(queries_to_search):
                if q_idx > 0:
                    time.sleep(0.25)
                started = time.perf_counter()
                try:
                    fallback_max_results = (
                        max(self.max_results_per_source, 50)
                        if trigger == "low_coverage_oa_supplement"
                        else self.max_results_per_source
                    )
                    results = adapter.search(q, max_results=fallback_max_results)
                    source_candidates.extend(results)
                    adapter_responded = True
                    latency_ms = int((time.perf_counter() - started) * 1000)
                    total_latency += latency_ms
                    search_log.append(f"{source}: fallback searched '{q[:60]}' ({len(results)} results)")
                except Exception as exc:
                    latency_ms = int((time.perf_counter() - started) * 1000)
                    total_latency += latency_ms
                    logger.warning("Fallback acquisition failed for %s (%s): %s", source, q[:40], exc)
                    source_error = f"{type(exc).__name__}: {str(exc)[:160]}"
                    search_log.append(f"{source}: fallback failed '{q[:40]}' ({type(exc).__name__})")
                    if _is_transient_source_failure(exc):
                        search_log.append(f"{source}: skipped remaining fallback variants after transient source failure")
                        break
            if adapter_responded:
                candidates.extend(source_candidates)
                source_metrics.append({
                    "source": source,
                    "attempted": True,
                    "success": True,
                    "count": len(source_candidates),
                    "latency_ms": total_latency,
                    "error": "",
                    "fallback": True,
                    "trigger": trigger,
                })
            else:
                fallback_failures.append(f"ACQUISITION_FAILED:{source}: {source_error or 'no results'}")
                source_metrics.append({
                    "source": source,
                    "attempted": True,
                    "success": False,
                    "count": 0,
                    "latency_ms": total_latency,
                    "error": source_error or "no results",
                    "fallback": True,
                    "trigger": trigger,
                })
        # A supplement is intentionally redundant. If at least one OA index
        # succeeds, another optional index being rate-limited must remain
        # visible in metrics without degrading an otherwise healthy M1 run.
        if trigger != "low_coverage_oa_supplement" or not candidates:
            warnings.extend(fallback_failures)
        return candidates, warnings, search_log, source_metrics

    def _verify(self, candidates: list[CandidatePaper]) -> list[CandidatePaper]:
        if not candidates:
            return []
        to_verify = candidates[: self.max_verify_candidates]
        rest = candidates[self.max_verify_candidates :]
        try:
            verified = self.verifier.verify_batch(to_verify)
        except Exception as exc:
            logger.warning("Candidate verification failed: %s", exc)
            verified = [
                candidate.model_copy(
                    update={
                        "verification_status": VerificationStatus.VERIFY_PENDING,
                        "verification_method": "verification_batch_failed",
                        "verification_reason": f"Verifier failed: {type(exc).__name__}.",
                        "verification_confidence": "low",
                    }
                )
                for candidate in to_verify
            ]
        if rest:
            rest = [
                candidate.model_copy(
                    update={
                        "verification_status": VerificationStatus.VERIFY_PENDING,
                        "verification_method": "verification_limit",
                        "verification_reason": "Verification was limited for the minimal direction loop.",
                        "verification_confidence": "low",
                    }
                )
                for candidate in rest
            ]
        return verified + rest

    def _status_and_message(
        self,
        *,
        source_metrics: list[dict[str, object]],
        candidate_count: int,
        visible_candidate_count: int,
        warning_count: int,
        recommended_candidate_count: int = 0,
        download_selected_count: int = 0,
        downloaded_count: int = 0,
        download_attempt_count: int = 0,
        download_failed_count: int = 0,
    ) -> tuple[str, str]:
        attempted = [metric for metric in source_metrics if metric.get("attempted")]
        successes = [metric for metric in attempted if metric.get("success")]
        failures = [metric for metric in attempted if not metric.get("success")]
        if candidate_count == 0 and not successes:
            return "BLOCKED", "No external paper source returned usable results."
        if visible_candidate_count == 0:
            return "EMPTY_RESULT", "Sources responded, but no candidate passed the relevance/readability filters."
        if recommended_candidate_count == 0:
            return "DEGRADED", "Direction exploration returned candidates, but all were marked low relevance or not recommended for the reading map."
        if download_selected_count > 0 and downloaded_count > 0:
            if download_attempt_count and (download_failed_count >= 4 or download_failed_count / download_attempt_count >= 0.4):
                return (
                    "DEGRADED",
                    f"Direction exploration used the reranked download queue and downloaded {downloaded_count}/{download_attempt_count} attempted papers; too many downloads failed.",
                )
            return (
                "SUCCESS",
                f"Direction exploration used the reranked download queue and downloaded {downloaded_count}/{download_attempt_count} attempted papers.",
            )
        if failures or warning_count:
            return "DEGRADED", "Direction exploration returned real candidates, but one or more sources or gates degraded."
        return "SUCCESS", "Direction exploration returned a structured bundle from real paper sources."

    def _empty_bundle(
        self,
        query: str,
        *,
        status: str,
        message: str,
        warnings: list[str],
    ) -> DirectionBundle:
        query_plan = build_heuristic_query_plan(query)
        pool = CandidatePool(query=query)
        reading_plan = ReadingPlan(topic=query, status="FAILED", warnings=warnings)
        return DirectionBundle(
            status=status,
            direction_workspace_status=status,
            pipeline_status=M1LayerStatus(
                status="BLOCKED",
                code="EMPTY_QUERY" if "EMPTY_QUERY" in warnings else "PIPELINE_BLOCKED",
                message=message,
                completed=False,
            ),
            relevance_status=M1LayerStatus(
                status="BLOCKED",
                code="NO_QUERY" if "EMPTY_QUERY" in warnings else "NO_CANDIDATES",
                message="Relevance cannot be evaluated without a query and candidates.",
                completed=False,
                threshold=MIN_RELEVANCE_SCORE,
            ),
            source_status=M1LayerStatus(
                status="BLOCKED",
                code="NO_RELEVANT_CANDIDATE",
                message="Source selection is blocked until a candidate passes relevance.",
                completed=False,
            ),
            understanding_status=M1LayerStatus(
                status="BLOCKED",
                code="M2_NOT_REACHED",
                message="M2 understanding was not reached.",
                completed=False,
            ),
            query=query,
            message=message,
            query_plan=query_plan,
            candidate_pool=pool,
            filtered_candidates=pool,
            reading_plan=reading_plan,
            warnings=warnings,
        )

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
            source_downloaded = bool(resolved.has_valid_deep_reading_source and resolved.local_path and resolved.sha256)
            pdf_available = bool(candidate.pdf_url or resolved.pdf_url)
            can_enter_m2 = bool(
                candidate.m2_ready
                and candidate.canonical_paper_path
                and candidate.canonical_quality_status != CanonicalQualityStatus.FAIL
                and resolved.has_valid_deep_reading_source
            )
            source_confidence = "high" if source_downloaded else ("medium" if pdf_available else candidate.source_confidence)
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
                        "latex_source_available": resolved.latex_source_available,
                        "latex_source_downloaded": resolved.latex_source_downloaded,
                        "latex_main_file": resolved.latex_main_file,
                        "metadata_only": not resolved.has_valid_deep_reading_source,
                        "source_confidence": source_confidence,
                        "metadata_confidence": metadata_confidence,
                        "degradation_reason": resolved.error or candidate.degradation_reason,
                        "raw_source_metadata": {
                            **candidate.raw_source_metadata,
                            "source_resolution": {
                                "status": resolved.status.value,
                                "local_path": resolved.local_path,
                                "sha256": resolved.sha256,
                                "file_size": resolved.file_size,
                                "content_type": resolved.content_type,
                                "download_status": resolved.download_status,
                                "error": resolved.error,
                                "error_code": resolved.error_code,
                                "metadata": resolved.metadata,
                            },
                        },
                    }
                )
            )
        return updated


def _run_query_planner(query_planner: QueryPlannerAdapter, query: str) -> QueryPlan:
    """Run the async planner from the sync FastAPI/service path."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(query_planner.plan(query))

    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(lambda: asyncio.run(query_planner.plan(query))).result()


def _complete_query_plan(plan: QueryPlan, *, fallback_query: str) -> QueryPlan:
    english_query = " ".join((plan.english_query or plan.direction_en or plan.user_query or fallback_query).split())
    defaults = build_heuristic_query_plan(english_query)
    language = plan.language or ("zh" if any(ord(char) > 127 for char in fallback_query) else "en")
    return plan.model_copy(
        update={
            "user_query": plan.user_query or fallback_query,
            "language": language,
            "direction_zh": plan.direction_zh or (fallback_query if language == "zh" else ""),
            "direction_en": plan.direction_en or english_query,
            "english_query": english_query,
            "query_variants": _unique([english_query, *plan.query_variants, *defaults.query_variants]),
            "core_terms": _unique([*plan.core_terms, *defaults.core_terms]),
            "related_terms": _unique([*plan.related_terms, *defaults.related_terms]),
            "search_intents": plan.search_intents or defaults.search_intents,
            "sub_directions": _unique([*plan.sub_directions, *defaults.sub_directions]),
            "warnings": [warning for warning in plan.warnings if warning != "HEURISTIC_QUERY_PLAN_NO_LLM"],
        }
    )


def _heuristic_with_planner_warning(query: str, exc: Exception) -> QueryPlan:
    fallback = build_heuristic_query_plan(query)
    reason = str(exc).strip() or type(exc).__name__
    return fallback.model_copy(
        update={
            "warnings": [
                f"LLM_QUERY_PLAN_FAILED:{type(exc).__name__}: {reason}",
                *fallback.warnings,
            ]
        }
    )


def build_heuristic_query_plan(user_query: str) -> QueryPlan:
    query = " ".join(user_query.split())
    language = "zh" if any(ord(char) > 127 for char in query) else "en"
    direction_en = _translate_direction(query)
    core_terms = _core_terms(direction_en or query)
    related_terms = _related_terms(direction_en or query)
    sub_directions = _default_sub_directions(direction_en or query)
    variants = _query_variants(direction_en or query)
    warnings = ["HEURISTIC_QUERY_PLAN_NO_LLM"]
    return QueryPlan(
        user_query=query,
        language=language,
        direction_zh=query if language == "zh" else "",
        direction_en=direction_en or query,
        english_query=direction_en or query,
        query_variants=variants,
        core_terms=core_terms,
        related_terms=related_terms,
        search_intents=[SearchIntent.SURVEY, SearchIntent.FOUNDATIONAL, SearchIntent.SOTA],
        sub_directions=sub_directions,
        warnings=warnings,
    )


def _translate_direction(query: str) -> str:
    replacements = {
        "时间序列": "time series",
        "时序": "time series",
        "多变量": "multivariate",
        "多元": "multivariate",
        "可解释异常检测": "explainable anomaly detection",
        "异常解释": "explainable anomaly detection",
        "异常归因": "anomaly attribution",
        "异常根因": "anomaly root cause analysis",
        "异常检测": "anomaly detection",
        "异常识别": "anomaly detection",
        "异常": "anomaly",
        "根因分析": "root cause analysis",
        "根因定位": "root cause localization",
        "故障定位": "fault localization",
        "故障诊断": "fault diagnosis",
        "事故诊断": "incident diagnosis",
        "日志分析": "log analysis",
        "指标分析": "metric analysis",
        "告警分析": "alert analysis",
        "预测": "forecasting",
        "预报": "forecasting",
        "分类": "classification",
        "聚类": "clustering",
        "插补": "imputation",
        "缺失值填补": "imputation",
        "缺失值补全": "imputation",
        "扩散模型": "diffusion model",
        "大语言模型": "large language model",
        "智能运维": "AIOps",
        "文献综述": "survey",
        "研究综述": "survey",
        "综述": "survey",
        "图神经网络": "graph neural network",
        "图网络": "graph neural network",
        "图": "graph",
        "用于": "for",
        "用来": "for",
        "面向": "for",
        "做": "for",
        "结合": "combined with",
        "和": "and",
        "与": "and",
    }
    if all(ord(char) < 128 for char in query):
        return query
    translated = query
    for zh, en in replacements.items():
        translated = translated.replace(zh, f" {en} ")
    translated = re.sub(r"[的在里中上]", " ", translated)
    translated = re.sub(r"\s+", " ", translated).strip()
    return translated if re.search(r"[a-zA-Z]", translated) else query


def _core_terms(direction: str) -> list[str]:
    lower = direction.lower()
    phrases = [
        "time series",
        "multivariate",
        "explainable anomaly detection",
        "anomaly explanation",
        "anomaly attribution",
        "anomaly detection",
        "root cause analysis",
        "root cause localization",
        "fault localization",
        "fault diagnosis",
        "imputation",
        "diffusion model",
        "diffusion",
        "large language model",
        "llm",
        "aiops",
        "survey",
        "graph neural network",
        "graph",
        "forecasting",
        "prediction",
        "representation learning",
        "classification",
        "clustering",
    ]
    terms = [phrase for phrase in phrases if phrase in lower]
    if terms:
        return terms
    return [token for token in re.split(r"[^a-z0-9]+", lower) if len(token) > 2][:6]


def _related_terms(direction: str) -> list[str]:
    lower = direction.lower()
    terms: list[str] = []
    if "time series" in lower:
        terms += ["temporal", "sequence", "forecasting", "representation learning", "multivariate", "imputation"]
    if "anomaly" in lower:
        terms += ["outlier detection", "novelty detection", "industrial monitoring", "abnormal detection"]
    if "explainable anomaly" in lower or "anomaly explanation" in lower or "anomaly attribution" in lower:
        terms += [
            "anomaly explanation",
            "anomaly attribution",
            "explainable AI",
            "root cause analysis",
            "fault localization",
            "incident diagnosis",
            "AIOps",
        ]
    if "imputation" in lower:
        terms += ["missing data", "masking", "diffusion", "probabilistic"]
    if "graph" in lower:
        terms += ["gnn", "graph representation", "node anomaly", "temporal graph", "spatio-temporal", "graph neural network"]
    if "forecasting" in lower or "prediction" in lower:
        terms += ["prediction", "time series", "forecast"]
    if "transformer" in lower:
        terms += ["attention", "self-attention", "transformer model"]
    if "diffusion" in lower:
        terms += ["score-based", "generative", "denoising"]
    if "root cause" in lower or "rca" in lower:
        terms += ["root cause localization", "fault localization", "failure diagnosis", "causal diagnosis"]
    if "large language model" in lower or "llm" in lower:
        terms += ["large language models", "agent", "log analysis", "diagnosis"]
    return _unique(terms)


def _default_sub_directions(direction: str) -> list[str]:
    lower = direction.lower()
    if "imputation" in lower:
        return [
            "missingness modeling",
            "probabilistic and diffusion imputation",
            "transformer/attention imputation",
            "graph-aware multivariate imputation",
            "benchmark and evaluation protocols",
        ]
    if "graph" in lower and "anomaly" in lower:
        return [
            "node-level anomaly detection",
            "edge and subgraph anomalies",
            "temporal graph anomalies",
            "self-supervised graph representation",
            "explainability and benchmarks",
        ]
    if "root cause" in lower or "rca" in lower:
        return [
            "metric and log based root cause localization",
            "causal graph diagnosis",
            "LLM-assisted incident analysis",
            "time-series anomaly attribution",
            "AIOps benchmarks and systems",
        ]
    if "explainable anomaly" in lower or "anomaly explanation" in lower or "anomaly attribution" in lower:
        return [
            "explainable anomaly detection methods",
            "anomaly attribution and root cause localization",
            "causal diagnosis for anomalies",
            "log/metric incident explanation",
            "benchmarks and evaluation protocols",
        ]
    if "time series" in lower and "anomaly" in lower:
        return [
            "reconstruction-based detection",
            "forecasting/prediction residuals",
            "transformer and foundation time-series models",
            "graph and multivariate dependency modeling",
            "benchmarks and industrial datasets",
        ]
    return [
        "survey and taxonomy",
        "foundational methods",
        "recent neural methods",
        "benchmark datasets",
        "open-source systems",
    ]


def _query_variants(direction: str) -> list[str]:
    base = direction.lower()
    variants = [base]
    variants.extend(_venue_targeted_variants(base))
    variants.extend(_anomaly_explanation_variants(base))
    variants.extend(_root_cause_variants(base))
    # Add abbreviation variants for compound queries
    _ABBREVS = {
        "graph neural network": "gnn",
        "graph neural networks": "gnn",
        "anomaly detection": "anomaly detection",
        "time series": "time series",
        "natural language processing": "nlp",
        "convolutional neural network": "cnn",
        "recurrent neural network": "rnn",
        "long short-term memory": "lstm",
        "generative adversarial network": "gan",
        "variational autoencoder": "vae",
        "diffusion model": "diffusion",
        "diffusion models": "diffusion",
        "transformer model": "transformer",
        "foundation model": "foundation model",
    }
    # Expand compound query with abbreviations
    expanded = base
    for full, abbrev in _ABBREVS.items():
        if full in expanded:
            expanded_variant = expanded.replace(full, abbrev)
            if expanded_variant != expanded:
                variants.append(expanded_variant)
    # Search the closest task/method reformulations before broad survey terms.
    variants.extend(_semantic_variants(base))
    # Add decomposed term pairs for very compound queries
    tokens = [t for t in re.split(r"[^a-z0-9]+", base) if len(t) >= 3]
    if len(tokens) >= 3:
        key_terms = [t for t in tokens if t not in {"for", "the", "and", "of", "in", "on", "to", "with", "from", "using", "based", "models", "methods"}]
        if len(key_terms) >= 2:
            variants.append(" ".join(key_terms[:2]))
            if len(key_terms) >= 3:
                variants.append(" ".join(key_terms[:3]))
    variants.extend([
        f"{base} recent method",
        f"{base} benchmark",
        f"{base} survey",
        f"{base} review",
        f"{base} state of the art",
    ])
    return _unique(variants)


def _prioritized_search_queries(query: str, query_variants: list[str], *, limit: int = 6) -> list[str]:
    """Primary query plus high-signal variants, capped to protect external APIs."""
    queries = [query]
    for variant in query_variants:
        if variant and variant.lower() != query.lower():
            queries.append(variant)
    return _unique(queries)[: max(limit, 1)]


def _discovery_supplement_reasons(
    query: str,
    candidates: list[CandidatePaper],
    *,
    expected_count: int,
    query_plan: QueryPlan | None = None,
    relevance_evaluator: DeterministicRelevanceEvaluator | None = None,
) -> list[str]:
    """Explain when a non-empty primary result still needs OA-index coverage."""

    expected = max(expected_count, 1)
    query_terms = {
        token
        for token in re.findall(r"[a-z0-9\u4e00-\u9fff]+", query.lower())
        if len(token) >= 3 and token not in {"the", "and", "for", "with", "from", "using", "method", "methods"}
    }
    relevant_count = 0
    relevant_oa_hint_count = 0
    if query_plan is not None and relevance_evaluator is not None:
        assessed = relevance_evaluator.evaluate_and_rank(query_plan, candidates)
        relevant = [candidate for candidate in assessed if passes_strict_relevance_gate(candidate)]
        relevant_count = len(relevant)
        relevant_oa_hint_count = sum(
            1 for candidate in relevant if _candidate_has_open_fulltext_hint(candidate)
        )
    else:
        for candidate in candidates:
            searchable = f"{candidate.title} {candidate.abstract}".lower()
            overlap = sum(1 for term in query_terms if term in searchable)
            likely_relevant = not query_terms or overlap >= min(2, len(query_terms))
            if likely_relevant:
                relevant_count += 1
                if _candidate_has_open_fulltext_hint(candidate):
                    relevant_oa_hint_count += 1

    reasons: list[str] = []
    if len(candidates) < expected:
        reasons.append(f"candidate_count={len(candidates)}<{expected}")
    relevant_target = min(4, expected)
    if relevant_count < relevant_target:
        reasons.append(f"topic_matches={relevant_count}<{relevant_target}")
    # The user-facing download queue needs enough relevant *and* open papers;
    # unrelated arXiv hits must not suppress OA supplementation.
    unresolved_relevant_count = max(relevant_count - relevant_oa_hint_count, 0)
    if unresolved_relevant_count:
        reasons.append(f"relevant_without_open_fulltext_hint={unresolved_relevant_count}")
    return reasons


def _candidate_has_open_fulltext_hint(candidate: CandidatePaper) -> bool:
    if candidate.arxiv_id or candidate.pdf_url or candidate.candidate_pdf_urls or candidate.candidate_source_urls:
        return True
    if candidate.open_access or candidate.pdf_available:
        return True
    raw = candidate.raw_source_metadata or {}
    if isinstance(raw.get("best_oa_location"), dict):
        return True
    open_access_pdf = raw.get("openAccessPdf")
    return isinstance(open_access_pdf, dict) and bool(open_access_pdf.get("url"))


def _direction_download_dir(root: Path | None, query_plan: QueryPlan) -> Path | None:
    if root is None:
        return None
    topic = query_plan.direction_zh or query_plan.direction_en or query_plan.user_query
    return root / _safe_topic_folder(topic)


def _safe_topic_folder(value: str) -> str:
    safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', " ", value or "").strip()
    safe = re.sub(r"\s+", " ", safe)
    safe = safe.rstrip(" .")
    return safe[:120] or "direction_search"


def _venue_targeted_variants(query: str) -> list[str]:
    """Aim broad directions at CCF-heavy venues before generic survey terms."""
    has_graph = "graph" in query or "gnn" in query
    has_time = "time series" in query or "temporal" in query
    has_anomaly = "anomaly" in query
    if has_graph and has_time and has_anomaly:
        task = "graph neural network multivariate time series anomaly detection"
    elif has_time and has_anomaly:
        task = "multivariate time series anomaly detection"
    elif has_graph and has_anomaly:
        task = "graph neural network anomaly detection"
    elif has_graph and has_time:
        task = "graph neural network time series"
    else:
        return []
    return [
        f"{task} {venue}"
        for venue in (
            "KDD",
            "VLDB",
            "SIGMOD",
            "ICDE",
            "WWW",
            "IJCAI",
            "AAAI",
            "ICLR",
            "NeurIPS",
            "ICML",
            "TPAMI",
            "TKDE",
        )
    ]


def _root_cause_variants(query: str) -> list[str]:
    lower = query.lower()
    has_rca = "root cause" in lower or "rca" in lower or "fault localization" in lower or "failure diagnosis" in lower
    has_llm = "large language model" in lower or "llm" in lower or "foundation model" in lower
    has_time = "time series" in lower or "multivariate" in lower or "temporal" in lower
    has_anomaly = "anomaly" in lower
    variants: list[str] = []
    if has_rca:
        if has_time and has_anomaly:
            variants.extend([
                "time series anomaly root cause localization",
                "multivariate time series root cause analysis",
                "causal root cause analysis for time series anomalies",
                "AIOps root cause localization time series anomaly",
            ])
        variants.extend([
            "root cause analysis anomaly detection",
            "root cause localization failure diagnosis",
            "causal graph root cause analysis",
            "AIOps root cause analysis",
        ])
    if has_llm and has_rca:
        variants.extend([
            "large language model root cause analysis",
            "LLM root cause analysis AIOps",
            "large language models for incident diagnosis",
            "LLM for fault localization and root cause analysis",
        ])
    elif has_llm and has_anomaly:
        variants.extend([
            "large language model anomaly detection",
            "LLM for anomaly detection",
            "large language models for AIOps anomaly detection",
        ])
    return variants


def _anomaly_explanation_variants(query: str) -> list[str]:
    lower = query.lower()
    has_explanation = (
        "explainable anomaly" in lower
        or "anomaly explanation" in lower
        or "anomaly attribution" in lower
        or ("explainable" in lower and "anomaly" in lower)
    )
    has_root_cause = "root cause" in lower or "rca" in lower or "fault localization" in lower
    has_time = "time series" in lower or "multivariate" in lower or "temporal" in lower
    has_logs = "log" in lower or "metric" in lower or "aiops" in lower or "incident" in lower
    if not (has_explanation or has_root_cause):
        return []

    variants = [
        "explainable anomaly detection",
        "anomaly explanation",
        "anomaly attribution",
        "root cause analysis anomaly detection",
        "root cause localization anomalies",
        "fault localization anomaly detection",
        "causal diagnosis anomaly detection",
        "AIOps root cause analysis",
    ]
    if has_time:
        variants.extend([
            "time series anomaly explanation",
            "time series anomaly attribution",
            "multivariate time series root cause localization",
            "causal root cause analysis for time series anomalies",
        ])
    if has_logs:
        variants.extend([
            "log anomaly root cause analysis",
            "metric anomaly root cause localization",
            "incident diagnosis AIOps logs metrics",
        ])
    return variants


def _semantic_variants(query: str) -> list[str]:
    """Generate semantic reformulations for compound queries that are too strict."""
    variants: list[str] = []
    has_graph = "graph" in query or "gnn" in query
    has_time = "time series" in query or "temporal" in query
    # Graph + time series compound queries
    if has_graph and has_time:
        variants.extend([
            "graph neural networks for time series",
            "temporal graph neural network",
            "spatio-temporal graph neural network",
            "graph neural network forecasting time series",
            "gnn for time series",
            "graph neural network time series analysis",
        ])
    if has_graph and "anomaly" in query:
        variants.extend([
            "graph neural network anomaly detection",
            "gnn anomaly detection",
            "graph-based anomaly detection",
        ])
    if has_graph and has_time and "anomaly" in query:
        variants.extend([
            "graph neural network anomaly detection time series",
            "gnn anomaly detection time series",
            "temporal graph anomaly detection",
        ])

    # Diffusion + time series
    if "diffusion" in query and has_time:
        variants.extend([
            "diffusion model time series",
            "score-based diffusion time series",
            "diffusion model for time series",
        ])

    # Transformer + time series
    if "transformer" in query and has_time:
        variants.extend([
            "transformer for time series",
            "attention-based time series",
            "time series transformer",
        ])

    # Forecasting + multivariate
    if "forecasting" in query and "multivariate" in query:
        variants.extend([
            "multivariate time series forecasting",
            "multivariate time series prediction",
            "time series forecasting multivariate",
            "multivariate forecasting deep learning",
        ])
    if "anomaly" in query and has_time:
        variants.extend([
            "time series anomaly detection",
            "multivariate time series anomaly detection",
            "deep anomaly detection time series",
        ])
    if "forecasting" in query and has_time and "anomaly" in query:
        variants.extend([
            "time series forecasting anomaly detection",
            "forecasting residual anomaly detection",
            "multivariate time series forecasting anomaly detection",
            "forecasting-based time series anomaly detection",
        ])
    elif "forecasting" in query and has_time:
        variants.extend([
            "time series forecasting",
            "time series prediction",
        ])

    return variants


def _pipeline_layer_status(
    *,
    source_metrics: list[dict[str, object]],
    candidate_count: int,
    warning_count: int,
    download_attempt_count: int,
    downloaded_count: int,
) -> M1LayerStatus:
    attempted = [metric for metric in source_metrics if metric.get("attempted")]
    failed = [metric for metric in attempted if not metric.get("success")]
    details = {
        "scope": "M1_DIRECTION_EXPLORATION",
        "search_completed": bool(attempted),
        "verification_completed": candidate_count > 0,
        "ranking_completed": candidate_count > 0,
        "source_resolution_completed": download_attempt_count > 0,
        "download_attempt_count": download_attempt_count,
        "downloaded_count": downloaded_count,
        "m2_completed": False,
        "cards_completed": False,
    }
    if candidate_count == 0:
        return M1LayerStatus(
            status="BLOCKED" if failed and not any(metric.get("success") for metric in attempted) else "EMPTY_RESULT",
            code="SEARCH_SOURCES_BLOCKED" if failed and not any(metric.get("success") for metric in attempted) else "NO_SEARCH_RESULTS",
            message="M1 search produced no candidates; downstream stages were not run.",
            completed=bool(attempted),
            candidate_count=0,
            details=details,
        )
    if failed or warning_count or (download_attempt_count > 0 and downloaded_count < download_attempt_count):
        return M1LayerStatus(
            status="DEGRADED",
            code="M1_PIPELINE_PARTIAL",
            message="M1 search and ranking completed, but one or more source/download operations degraded.",
            completed=True,
            candidate_count=candidate_count,
            details=details,
        )
    return M1LayerStatus(
        status="SUCCESS",
        code="M1_PIPELINE_COMPLETE",
        message="M1 search, verification, and ranking completed for this endpoint; M2/cards were not run.",
        completed=True,
        candidate_count=candidate_count,
        details=details,
    )


def _relevance_layer_status(candidates: list[CandidatePaper]) -> M1LayerStatus:
    evaluated = [candidate for candidate in candidates if candidate.relevance_gate_evaluated]
    passed = [candidate for candidate in evaluated if candidate.relevance_gate_passed]
    details = {
        "minimum_score": MIN_RELEVANCE_SCORE,
        "deep_read_minimum_score": MIN_DEEP_READ_RELEVANCE_SCORE,
        "top_candidate_id": passed[0].paper_id if passed else "",
        "top_candidate_score": passed[0].rule_relevance_score if passed else 0.0,
        "deterministic_gate": True,
        "llm_is_supplemental": True,
    }
    if not candidates:
        return M1LayerStatus(
            status="BLOCKED",
            code="NO_CANDIDATES",
            message="No candidate was available for relevance evaluation.",
            completed=False,
            threshold=MIN_RELEVANCE_SCORE,
            details=details,
        )
    if not passed:
        return M1LayerStatus(
            status="BLOCKED",
            code="NO_CANDIDATE_PASSED_RELEVANCE_GATE",
            message="Candidates were found, but none covered all required task/method concepts without an intent mismatch.",
            completed=True,
            candidate_count=len(evaluated),
            passed_candidate_count=0,
            threshold=MIN_RELEVANCE_SCORE,
            details=details,
        )
    return M1LayerStatus(
        status="SUCCESS",
        code="RELEVANCE_GATE_PASSED",
        message=f"{len(passed)}/{len(evaluated)} candidates passed deterministic relevance checks.",
        completed=True,
        candidate_count=len(evaluated),
        passed_candidate_count=len(passed),
        threshold=MIN_RELEVANCE_SCORE,
        details=details,
    )


def _source_layer_status(candidates: list[CandidatePaper]) -> M1LayerStatus:
    relevant = [candidate for candidate in candidates if candidate.relevance_gate_passed]
    source_ready = [candidate for candidate in relevant if candidate.has_valid_deep_reading_source]
    details = {
        "legal_verified_source_required": True,
        "source_ready_candidate_ids": [candidate.paper_id for candidate in source_ready],
        "metadata_only_count": sum(1 for candidate in relevant if candidate.metadata_only),
    }
    if not relevant:
        return M1LayerStatus(
            status="BLOCKED",
            code="NO_RELEVANT_CANDIDATE",
            message="Source acceptance is blocked because no candidate passed relevance.",
            completed=False,
            details=details,
        )
    if not source_ready:
        return M1LayerStatus(
            status="DEGRADED",
            code="NO_VERIFIED_FULLTEXT_FOR_RELEVANT_CANDIDATE",
            message="Relevant candidates exist, but none has a verified legal full-text source for M2.",
            completed=True,
            candidate_count=len(relevant),
            passed_candidate_count=0,
            details=details,
        )
    return M1LayerStatus(
        status="SUCCESS",
        code="VERIFIED_FULLTEXT_AVAILABLE",
        message=f"{len(source_ready)}/{len(relevant)} relevant candidates have a verified full-text source.",
        completed=True,
        candidate_count=len(relevant),
        passed_candidate_count=len(source_ready),
        details=details,
    )


def _understanding_layer_status(candidates: list[CandidatePaper]) -> M1LayerStatus:
    relevant = [candidate for candidate in candidates if candidate.relevance_gate_passed]
    source_ready = [candidate for candidate in relevant if candidate.has_valid_deep_reading_source]
    m2_ready = [
        candidate
        for candidate in source_ready
        if candidate.m2_ready and candidate.can_enter_m2
    ]
    details = {
        "m2_was_run": False,
        "cards_were_generated": False,
        "m2_ready_candidate_ids": [candidate.paper_id for candidate in m2_ready],
    }
    if not relevant:
        return M1LayerStatus(
            status="BLOCKED",
            code="RELEVANCE_GATE_BLOCKED_UNDERSTANDING",
            message="M2 understanding cannot start without a relevant candidate.",
            completed=False,
            details=details,
        )
    if not source_ready:
        return M1LayerStatus(
            status="BLOCKED",
            code="SOURCE_GATE_BLOCKED_UNDERSTANDING",
            message="M2 understanding cannot start without verified full text.",
            completed=False,
            candidate_count=len(relevant),
            details=details,
        )
    return M1LayerStatus(
        status="NOT_RUN",
        code="READY_FOR_M2" if m2_ready else "M2_PREPARATION_NOT_RUN",
        message="This direction endpoint does not run M2 or generate user-facing cards.",
        completed=False,
        candidate_count=len(source_ready),
        passed_candidate_count=len(m2_ready),
        details=details,
    )


def _overview(query_plan: QueryPlan, count: int, status: str) -> str:
    topic = query_plan.direction_en or query_plan.user_query
    return (
        f"{topic} is organized as a conservative reading landscape with {count} candidate papers. "
        f"The bundle uses PaperSearch MCP discovery, CCF venue screening, and legal full-text gates before PaperWorkspace. "
        f"Current direction status: {status}."
    )


def _key_sub_directions(query_plan: QueryPlan, reading_plan: ReadingPlan) -> list[dict[str, object]]:
    role_counts: dict[str, int] = {}
    for item in reading_plan.items:
        role_counts[item.role] = role_counts.get(item.role, 0) + 1
    return [
        {
            "name": name,
            "candidate_count": role_counts.get(_role_hint(name), 0),
            "description": _sub_direction_description(name),
        }
        for name in query_plan.sub_directions
    ]


def _method_families(query_plan: QueryPlan, reading_plan: ReadingPlan) -> list[dict[str, object]]:
    seen_roles = _unique([item.role for item in reading_plan.items if item.role and item.role != "IRRELEVANT"])
    if not seen_roles:
        seen_roles = ["SURVEY", "METHOD", "BENCHMARK"]
    return [
        {
            "name": _role_label(role),
            "role": role,
            "paper_count": sum(1 for item in reading_plan.items if item.role == role),
            "description": _role_description(role, query_plan.direction_en or query_plan.user_query),
        }
        for role in seen_roles
    ]


def _candidate_cards_from_reading_plan(reading_plan: ReadingPlan) -> list[dict[str, object]]:
    cards: list[dict[str, object]] = []
    ordered_items = sorted(
        reading_plan.items,
        key=lambda item: (
            1 if item.paper.relevance_gate_evaluated and not item.paper.relevance_gate_passed else 0,
            -item.paper.rule_relevance_score if item.paper.relevance_gate_evaluated else 0.0,
            item.paper.rerank_rank
            or _search_rank(item.paper, fallback=reading_plan.items.index(item) + 1),
        ),
    )
    for index, item in enumerate(ordered_items, start=1):
        paper = item.paper.model_copy(
            update={
                "relevance_score": item.scoring_breakdown.relevance_score,
                "rule_relevance_score": item.scoring_breakdown.relevance_score,
                "can_enter_m2": item.can_enter_m2,
            }
        )
        priority = "A_READ_FOR_M2" if item.priority == "A_READ" and item.can_enter_m2 else item.priority
        source_resolution = paper.raw_source_metadata.get("source_resolution")
        source_resolution = source_resolution if isinstance(source_resolution, dict) else {}
        cards.append({
            "rank": index,
            "search_rank": paper.search_rank or _search_rank(paper, fallback=index),
            "download_queue_rank": paper.raw_source_metadata.get("download_queue_rank", index),
            "paper_id": paper.paper_id,
            "title": paper.title,
            "authors": paper.authors,
            "year": paper.year,
            "venue": paper.venue,
            "venue_canonical_name": paper.venue_canonical_name,
            "venue_rank": paper.venue_rank.value,
            "download_selected": paper.download_selected,
            "download_decision": paper.download_decision,
            "download_reason": paper.download_reason,
            "rerank_rank": paper.rerank_rank,
            "rerank_score": paper.rerank_score,
            "rank_score": paper.rank_score,
            "rank_reason": paper.rank_reason,
            "source": paper.source,
            "sources": paper.sources,
            "discovery_sources": paper.sources,
            "source_ids": paper.source_ids,
            "url": paper.url or paper.landing_url or paper.pdf_url,
            "landing_url": paper.landing_url,
            "arxiv_url": _arxiv_url(paper),
            "doi": paper.doi,
            "arxiv_id": paper.arxiv_id,
            "pdf_url": paper.pdf_url,
            "candidate_pdf_urls": paper.candidate_pdf_urls,
            "candidate_source_urls": paper.candidate_source_urls,
            "candidate_html_urls": paper.candidate_html_urls,
            "selected_fulltext_source": paper.selected_fulltext_source,
            "selected_fulltext_url": paper.selected_fulltext_url,
            "fulltext_status": paper.fulltext_status,
            "fulltext_failure_reason": paper.fulltext_failure_reason,
            "download_status": source_resolution.get("download_status", ""),
            "download_error": source_resolution.get("error", "") or paper.degradation_reason,
            "download_error_code": source_resolution.get("error_code", ""),
            "download_local_path": source_resolution.get("local_path", ""),
            "browser_diagnostics": source_resolution.get("metadata", {}),
            "can_deep_read": paper.can_deep_read,
            "needs_user_upload": paper.needs_user_upload,
            "relevance_score": item.scoring_breakdown.relevance_score,
            "rule_relevance_score": paper.rule_relevance_score,
            "relevance_gate_evaluated": paper.relevance_gate_evaluated,
            "relevance_gate_passed": paper.relevance_gate_passed,
            "deep_read_relevance_passed": bool(
                paper.relevance_gate_passed
                and paper.rule_relevance_score >= MIN_DEEP_READ_RELEVANCE_SCORE
            ),
            "concept_coverage": paper.concept_coverage,
            "matched_concepts": paper.matched_concepts,
            "missing_concepts": paper.missing_concepts,
            "forbidden_intent_matches": paper.forbidden_intent_matches,
            "relevance_reason": paper.relevance_reason,
            "weighted_score": item.scoring_breakdown.weighted_total,
            "verification_status": paper.verification_status.value,
            "verification_reason": paper.verification_reason,
            "source_confidence": paper.source_confidence,
            "metadata_confidence": paper.metadata_confidence,
            "pdf_available": paper.pdf_available,
            "canonicalization_status": paper.canonicalization_status.value,
            "canonical_quality_status": paper.canonical_quality_status.value,
            "m2_ready": paper.m2_ready,
            "can_enter_m2": item.can_enter_m2,
            "priority": priority,
            "role": item.role,
            "selection_reason": item.selection_reason,
            "risk_note": item.risk_note,
            "can_prepare_deep_read": _can_prepare_deep_read(paper),
            "deep_read_unavailable_reason": _deep_read_unavailable_reason(paper),
            "m2_unavailable_reason": "" if item.can_enter_m2 else item.risk_note,
            "deep_read_button_state": "ready" if priority == "A_READ_FOR_M2" else (
                "prepare" if _can_prepare_deep_read(paper) else "source_unavailable"
            ),
        })
    return cards


def _reading_order(reading_plan: ReadingPlan) -> list[dict[str, object]]:
    ordered_items = sorted(
        [item for item in reading_plan.items if item.priority != "D_IGNORE"],
        key=lambda item: _search_rank(item.paper, fallback=reading_plan.items.index(item) + 1),
    )
    return [
        {
            "rank": index,
            "title": item.paper.title,
            "role": item.role,
            "priority": "A_READ_FOR_M2" if item.priority == "A_READ" and item.can_enter_m2 else item.priority,
            "reason": item.selection_reason,
            "can_enter_m2": item.can_enter_m2,
        }
        for index, item in enumerate(ordered_items, start=1)
    ]


def _verification_summary(candidates: list[CandidatePaper]) -> dict[str, int]:
    return {
        "verified_candidate_count": sum(1 for paper in candidates if paper.verification_status == VerificationStatus.VERIFIED),
        "unverified_candidate_count": sum(1 for paper in candidates if paper.verification_status == VerificationStatus.UNVERIFIED),
        "verify_pending_count": sum(1 for paper in candidates if paper.verification_status == VerificationStatus.VERIFY_PENDING),
        "error_count": sum(1 for paper in candidates if paper.verification_status == VerificationStatus.ERROR),
    }


def _relevance_summary(reading_plan: ReadingPlan) -> dict[str, int]:
    summary: dict[str, int] = {
        "candidate_count": len(reading_plan.items),
        "download_selected_count": sum(1 for item in reading_plan.items if item.paper.download_selected),
        "venue_ranked_count": sum(1 for item in reading_plan.items if item.paper.venue_rank.value != "unranked"),
        "relevance_evaluated_count": sum(1 for item in reading_plan.items if item.paper.relevance_gate_evaluated),
        "relevance_passed_count": sum(1 for item in reading_plan.items if item.paper.relevance_gate_passed),
        "relevance_blocked_count": sum(
            1
            for item in reading_plan.items
            if item.paper.relevance_gate_evaluated and not item.paper.relevance_gate_passed
        ),
    }
    for item in reading_plan.items:
        summary[item.priority] = summary.get(item.priority, 0) + 1
    return summary


def _search_rank(candidate: CandidatePaper, *, fallback: int) -> int:
    metadata = candidate.raw_source_metadata or {}
    for key in ("search_rank", "rank", "download_queue_rank"):
        value = metadata.get(key)
        try:
            rank = int(str(value))
        except (TypeError, ValueError):
            continue
        if rank > 0:
            return rank
    return fallback


def _download_attempt_warnings(attempt_count: int, downloaded_count: int) -> list[str]:
    if attempt_count <= 0:
        return []
    failed = max(attempt_count - downloaded_count, 0)
    warnings = [f"DOWNLOAD_ATTEMPT_SUMMARY:{downloaded_count}/{attempt_count}"]
    if failed >= 4 or failed / attempt_count >= 0.4:
        warnings.append(f"DOWNLOAD_FAILURE_RATE_HIGH:{failed}/{attempt_count}")
    return warnings


def _role_hint(name: str) -> str:
    lower = name.lower()
    if "survey" in lower or "taxonomy" in lower:
        return "SURVEY"
    if "benchmark" in lower or "dataset" in lower:
        return "BENCHMARK"
    if "graph" in lower:
        return "GRAPH_METHOD"
    if "transformer" in lower or "attention" in lower:
        return "TRANSFORMER_METHOD"
    if "reconstruction" in lower:
        return "RECONSTRUCTION_METHOD"
    if "forecast" in lower or "prediction" in lower:
        return "PREDICTION_METHOD"
    return "METHOD"


def _role_label(role: str) -> str:
    labels = {
        "SURVEY": "Survey and taxonomy",
        "BENCHMARK": "Benchmark and datasets",
        "TRANSFORMER_METHOD": "Transformer/attention methods",
        "GRAPH_METHOD": "Graph-based methods",
        "GENERATIVE_METHOD": "Generative methods",
        "RECONSTRUCTION_METHOD": "Reconstruction methods",
        "PREDICTION_METHOD": "Forecasting methods",
        "METHOD": "General methods",
    }
    return labels.get(role, role.replace("_", " ").title())


def _role_description(role: str, topic: str) -> str:
    if role == "SURVEY":
        return f"Survey-style anchors for building a map of {topic}."
    if role == "BENCHMARK":
        return "Evaluation, datasets, or benchmark protocols to calibrate claims."
    return "Method papers that can be skimmed first and promoted only after source/canonical gates pass."


def _sub_direction_description(name: str) -> str:
    return f"Track candidate papers and methods related to {name}."


def _arxiv_url(paper: CandidatePaper) -> str:
    if paper.arxiv_id:
        return f"https://arxiv.org/abs/{paper.arxiv_id}"
    for value in (paper.landing_url, paper.url, paper.pdf_url):
        if value and "arxiv.org/" in value:
            return value
    return ""


def _can_prepare_deep_read(paper: CandidatePaper) -> bool:
    if not paper.download_selected:
        return False
    return bool(paper.can_deep_read or paper.arxiv_id or paper.pdf_url or _arxiv_url(paper) or paper.doi)


def _deep_read_unavailable_reason(paper: CandidatePaper) -> str:
    if _can_prepare_deep_read(paper):
        return ""
    if paper.download_decision and paper.download_decision not in {"NOT_EVALUATED", "SELECTED_BY_RERANKER"}:
        return paper.download_reason or "Candidate was not selected for automatic download."
    if paper.fulltext_failure_reason:
        return paper.fulltext_failure_reason
    if paper.doi:
        return "DOI handoff will attempt legal open-access PDF resolution via Unpaywall."
    return "No arXiv ID, arXiv URL, or PDF URL is available for this candidate."


def _is_transient_source_failure(exc: Exception) -> bool:
    message = str(exc).lower()
    transient_terms = (
        "timeout",
        "timed out",
        "read operation",
        "503",
        "502",
        "504",
        "connection",
        "connect",
        "max retries",
        "temporarily",
        "service unavailable",
    )
    return any(term in message for term in transient_terms)


def _is_blocked_source_failure(exc: Exception) -> bool:
    message = str(exc).lower()
    blocked_terms = (
        "google_scholar_blocked",
        "captcha",
        "not a robot",
        "anti-bot",
        "blocked",
    )
    return any(term in message for term in blocked_terms)


def _has_blocked_warning(warnings: list[str]) -> bool:
    text = "\n".join(warnings).lower()
    return any(term in text for term in ("blocked", "captcha", "anti-bot", "not a robot"))


def _preserves_primary_search_order(source: str) -> bool:
    return source == "paper_search"


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result
