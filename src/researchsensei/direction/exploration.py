from __future__ import annotations

import logging
import re
import time
from pathlib import Path
from typing import Protocol

from researchsensei.acquisition import ArxivAdapter, CrossrefAdapter, DBLPAdapter, FullTextResolver, OpenAlexAdapter, SemanticScholarAdapter
from researchsensei.schemas import (
    CandidatePaper,
    CandidatePool,
    DirectionBundle,
    PaperSourceStatus,
    QueryPlan,
    ReadingPlan,
    SearchIntent,
    SourceResolutionResult,
    VerificationStatus,
)
from researchsensei.selection import SelectionService
from researchsensei.source_resolver import PaperSourceResolver
from researchsensei.verification import CandidateVerifier

logger = logging.getLogger(__name__)


class SearchAdapter(Protocol):
    def search(self, query: str, max_results: int = 20) -> list[CandidatePaper]:
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
        max_results_per_source: int = 8,
        max_verify_candidates: int = 12,
        source_download_dir: str | Path | None = None,
    ) -> None:
        self.adapters = adapters or {
            "arxiv": ArxivAdapter(timeout=12.0),
            "openalex": OpenAlexAdapter(),
            "semantic_scholar": SemanticScholarAdapter(timeout=12.0),
            "crossref": CrossrefAdapter(),
            "dblp": DBLPAdapter(timeout=12.0),
        }
        self.sources = sources or list(self.adapters.keys())
        self.selection_service = selection_service or SelectionService()
        self.verifier = verifier or CandidateVerifier(timeout_seconds=8.0)
        self.source_resolver = source_resolver or PaperSourceResolver(network_enabled=False)
        self.fulltext_resolver = fulltext_resolver or FullTextResolver(timeout_seconds=12.0)
        self.max_results_per_source = max_results_per_source
        self.max_verify_candidates = max_verify_candidates
        self.source_download_dir = Path(source_download_dir) if source_download_dir else None

    def explore(self, user_query: str) -> DirectionBundle:
        query = " ".join(user_query.split())
        if not query:
            return self._empty_bundle(
                query,
                status="BLOCKED",
                message="Direction query is empty.",
                warnings=["EMPTY_QUERY"],
            )

        query_plan = build_heuristic_query_plan(query)
        search_query = query_plan.english_query or query_plan.direction_en or query_plan.user_query
        candidates, warnings, search_log, source_metrics = self._acquire(
            search_query,
            query_variants=query_plan.query_variants,
        )
        raw_pool = self.selection_service.build_candidate_pool(
            query=search_query,
            candidates=candidates,
            search_log=search_log,
            warnings=warnings,
            source_metrics=source_metrics,
        )
        deduplicated = self.selection_service.deduplicate(candidates)
        verified = self._verify(deduplicated)
        fulltext_enriched, fulltext_metrics = self.fulltext_resolver.resolve_many(verified, download_top_n=0)
        source_metrics = [*source_metrics, *fulltext_metrics]
        source_resolution = self.source_resolver.resolve_many(
            search_query,
            fulltext_enriched,
            download_dir=self.source_download_dir,
        )
        resolved = self._apply_source_resolution(fulltext_enriched, source_resolution)
        reading_plan = self.selection_service.build_reading_plan(query_plan, resolved)
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

        status, message = self._status_and_message(
            source_metrics=source_metrics,
            candidate_count=len(candidates),
            visible_candidate_count=len(reading_plan.items),
            warning_count=len(warnings),
        )
        overview = _overview(query_plan, len(reading_plan.items), status)
        key_sub_directions = _key_sub_directions(query_plan, reading_plan)
        method_families = _method_families(query_plan, reading_plan)
        deep_read_candidates = [
            card for card in card_candidates
            if card.get("priority") in {"A_READ", "A_READ_FOR_M2"} and card.get("can_enter_m2") is True
        ]

        return DirectionBundle(
            status=status,
            direction_workspace_status=status,
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
                + [warning.code for warning in source_resolution.warnings]
                + reading_plan.warnings
            ),
            verification_summary=_verification_summary(resolved),
            relevance_summary=_relevance_summary(reading_plan),
        )

    def _acquire(
        self,
        query: str,
        *,
        query_variants: list[str] | None = None,
    ) -> tuple[list[CandidatePaper], list[str], list[str], list[dict[str, object]]]:
        candidates: list[CandidatePaper] = []
        warnings: list[str] = []
        search_log: list[str] = []
        source_metrics: list[dict[str, object]] = []

        # Build the set of queries to search: primary + a few expanded variants.
        # Limit to 4 total to avoid rate-limiting external APIs.
        queries_to_search = [query]
        if query_variants:
            for variant in query_variants:
                if variant and variant.lower() != query.lower():
                    queries_to_search.append(variant)
            queries_to_search = queries_to_search[:4]

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
            for q_idx, q in enumerate(queries_to_search):
                # Polite delay between variants
                if q_idx > 0:
                    time.sleep(0.5)
                started = time.perf_counter()
                try:
                    results = adapter.search(q, max_results=self.max_results_per_source)
                    source_candidates.extend(results)
                    adapter_responded = True
                    latency_ms = int((time.perf_counter() - started) * 1000)
                    total_latency += latency_ms
                    search_log.append(f"{source}: searched '{q[:60]}' ({len(results)} results)")
                    # If query returned results, skip remaining variants for this source
                    if results:
                        break
                except Exception as exc:
                    latency_ms = int((time.perf_counter() - started) * 1000)
                    total_latency += latency_ms
                    is_rate_limit = "429" in str(exc) or "rate" in str(exc).lower()
                    if is_rate_limit:
                        rate_limited = True
                    logger.warning("Direction acquisition failed for %s (%s): %s", source, q[:40], exc)
                    source_error = f"{type(exc).__name__}: {str(exc)[:160]}"
                    search_log.append(f"{source}: failed '{q[:40]}' ({type(exc).__name__})")

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
    ) -> tuple[str, str]:
        attempted = [metric for metric in source_metrics if metric.get("attempted")]
        successes = [metric for metric in attempted if metric.get("success")]
        failures = [metric for metric in attempted if not metric.get("success")]
        if candidate_count == 0 and not successes:
            return "BLOCKED", "No external paper source returned usable results."
        if visible_candidate_count == 0:
            return "EMPTY_RESULT", "Sources responded, but no candidate passed the relevance/readability filters."
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
            can_enter_m2 = source_downloaded
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
                            },
                        },
                    }
                )
            )
        return updated


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
    lower = query.lower()
    replacements = {
        "时间序列": "time series",
        "多变量": "multivariate",
        "异常检测": "anomaly detection",
        "插补": "imputation",
        "图神经网络": "graph neural network",
        "图": "graph",
    }
    if all(ord(char) < 128 for char in query):
        return query
    translated = query
    for zh, en in replacements.items():
        translated = translated.replace(zh, f" {en} ")
    translated = re.sub(r"\s+", " ", translated).strip()
    return translated if re.search(r"[a-zA-Z]", translated) else query


def _core_terms(direction: str) -> list[str]:
    lower = direction.lower()
    phrases = [
        "time series",
        "multivariate",
        "anomaly detection",
        "imputation",
        "graph neural network",
        "graph",
        "forecasting",
        "representation learning",
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
    if "imputation" in lower:
        terms += ["missing data", "masking", "diffusion", "probabilistic"]
    if "graph" in lower:
        terms += ["gnn", "graph representation", "node anomaly", "temporal graph", "spatio-temporal", "graph neural network"]
    if "forecasting" in lower:
        terms += ["prediction", "time series", "forecast"]
    if "transformer" in lower:
        terms += ["attention", "self-attention", "transformer model"]
    if "diffusion" in lower:
        terms += ["score-based", "generative", "denoising"]
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
    variants = [
        base,
        f"{base} survey",
        f"{base} review",
        f"{base} benchmark",
        f"{base} state of the art",
    ]
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
    # Add semantic reformulations for compound queries
    variants.extend(_semantic_variants(base))
    # Add decomposed term pairs for very compound queries
    tokens = [t for t in re.split(r"[^a-z0-9]+", base) if len(t) >= 3]
    if len(tokens) >= 3:
        key_terms = [t for t in tokens if t not in {"for", "the", "and", "of", "in", "on", "to", "with", "from", "using", "based", "models", "methods"}]
        if len(key_terms) >= 2:
            variants.append(" ".join(key_terms[:2]))
            if len(key_terms) >= 3:
                variants.append(" ".join(key_terms[:3]))
    return _unique(variants)


def _semantic_variants(query: str) -> list[str]:
    """Generate semantic reformulations for compound queries that are too strict."""
    variants: list[str] = []
    has_graph = "graph" in query or "gnn" in query
    has_time = "time series" in query or "temporal" in query
    has_neural = "neural" in query or "gnn" in query

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
    elif "forecasting" in query and has_time:
        variants.extend([
            "time series forecasting",
            "time series prediction",
        ])

    return variants


def _overview(query_plan: QueryPlan, count: int, status: str) -> str:
    topic = query_plan.direction_en or query_plan.user_query
    return (
        f"{topic} is organized as a conservative reading landscape with {count} candidate papers. "
        f"The bundle uses real source adapters and keeps PaperWorkspace entry gated by verified full-text/canonical readiness. "
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
    for index, item in enumerate(reading_plan.items, start=1):
        paper = item.paper.model_copy(
            update={
                "relevance_score": item.scoring_breakdown.relevance_score,
                "rule_relevance_score": item.scoring_breakdown.relevance_score,
                "can_enter_m2": item.can_enter_m2,
            }
        )
        priority = "A_READ_FOR_M2" if item.priority == "A_READ" and item.can_enter_m2 else item.priority
        cards.append({
            "rank": index,
            "paper_id": paper.paper_id,
            "title": paper.title,
            "authors": paper.authors,
            "year": paper.year,
            "venue": paper.venue,
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
            "can_deep_read": paper.can_deep_read,
            "needs_user_upload": paper.needs_user_upload,
            "relevance_score": item.scoring_breakdown.relevance_score,
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
    return [
        {
            "rank": index,
            "title": item.paper.title,
            "role": item.role,
            "priority": "A_READ_FOR_M2" if item.priority == "A_READ" and item.can_enter_m2 else item.priority,
            "reason": item.selection_reason,
            "can_enter_m2": item.can_enter_m2,
        }
        for index, item in enumerate(reading_plan.items, start=1)
    ]


def _verification_summary(candidates: list[CandidatePaper]) -> dict[str, int]:
    return {
        "verified_candidate_count": sum(1 for paper in candidates if paper.verification_status == VerificationStatus.VERIFIED),
        "unverified_candidate_count": sum(1 for paper in candidates if paper.verification_status == VerificationStatus.UNVERIFIED),
        "verify_pending_count": sum(1 for paper in candidates if paper.verification_status == VerificationStatus.VERIFY_PENDING),
        "error_count": sum(1 for paper in candidates if paper.verification_status == VerificationStatus.ERROR),
    }


def _relevance_summary(reading_plan: ReadingPlan) -> dict[str, int]:
    summary: dict[str, int] = {"candidate_count": len(reading_plan.items)}
    for item in reading_plan.items:
        summary[item.priority] = summary.get(item.priority, 0) + 1
    return summary


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
    return bool(paper.can_deep_read or paper.arxiv_id or paper.pdf_url or _arxiv_url(paper) or paper.doi)


def _deep_read_unavailable_reason(paper: CandidatePaper) -> str:
    if _can_prepare_deep_read(paper):
        return ""
    if paper.fulltext_failure_reason:
        return paper.fulltext_failure_reason
    if paper.doi:
        return "DOI handoff will attempt legal open-access PDF resolution via Unpaywall."
    return "No arXiv ID, arXiv URL, or PDF URL is available for this candidate."


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result
