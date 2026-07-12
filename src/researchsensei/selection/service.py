from __future__ import annotations

import re
from datetime import date
from typing import Iterable

from researchsensei.selection.venue_rankings import (
    venue_config_for_paper,
    venue_score as venue_score_for_paper,
)
from researchsensei.schemas import (
    CandidatePaper,
    CandidatePool,
    CanonicalQualityStatus,
    QueryPlan,
    ReadingPlan,
    ReadingPlanItem,
    ScoringBreakdown,
    SourcePriority,
    VenueRank,
    VerificationStatus,
)
from researchsensei.relevance import MIN_DEEP_READ_RELEVANCE_SCORE

SOURCE_RELIABILITY = {
    "paper_search_mcp": 0.9,
    "paper_search": 0.9,
    "semantic_scholar": 0.92,
    "semantic": 0.92,
    "openalex": 0.9,
    "google_scholar": 0.86,
    "arxiv": 0.78,
    "dblp": 0.72,
}

_DOI_PREFIXES = ("https://doi.org/", "http://doi.org/", "doi:")
_CONFIDENCE_ORDER = {"low": 0, "medium": 1, "high": 2}


class SelectionService:
    """Deduplicates, scores, and prioritizes M1 candidate papers."""

    def __init__(self, max_a_read: int = 8) -> None:
        self.max_a_read = max_a_read

    def build_candidate_pool(
        self,
        query: str,
        candidates: list[CandidatePaper],
        search_log: list[str] | None = None,
        warnings: list[str] | None = None,
        source_metrics: list[dict[str, object]] | None = None,
    ) -> CandidatePool:
        normalized = [self._normalize_candidate(candidate) for candidate in candidates]
        strong_count = sum(1 for candidate in normalized if self._relevance_score_for_text(query, candidate) >= 0.55)
        return CandidatePool(
            query=query,
            retrieved_count=len(candidates),
            deduplicated_count=len(normalized),
            strong_related_count=strong_count,
            items=normalized,
            search_log=search_log or [],
            warnings=warnings or [],
            source_metrics=source_metrics or [],
        )

    def deduplicate(self, candidates: list[CandidatePaper]) -> list[CandidatePaper]:
        if not candidates:
            return []

        result: list[CandidatePaper] = []
        seen_doi: dict[str, int] = {}
        seen_arxiv: dict[str, int] = {}
        seen_s2: dict[str, int] = {}
        seen_title: dict[str, int] = {}

        for raw in candidates:
            paper = self._normalize_candidate(raw)
            match_index = self._find_duplicate_index(paper, seen_doi, seen_arxiv, seen_s2, seen_title)
            if match_index is not None:
                result[match_index] = self._merge_paper(result[match_index], paper)
                self._register_keys(result[match_index], match_index, seen_doi, seen_arxiv, seen_s2, seen_title)
                continue

            idx = len(result)
            result.append(paper)
            self._register_keys(paper, idx, seen_doi, seen_arxiv, seen_s2, seen_title)

        return result

    def build_reading_plan(
        self,
        query_plan: QueryPlan,
        candidates: list[CandidatePaper],
        *,
        include_ignored: bool = False,
    ) -> ReadingPlan:
        if not candidates:
            return ReadingPlan(
                topic=self._topic(query_plan),
                items=[],
                status="FAILED",
                warnings=["NO_CANDIDATES"],
            )

        items = [self._score_item(query_plan, self._normalize_candidate(candidate)) for candidate in candidates]
        items.sort(key=lambda item: item.scoring_breakdown.weighted_total, reverse=True)

        a_read_count = 0
        unverified_count = 0
        for item in items:
            total = item.scoring_breakdown.weighted_total
            # An LLM score can tighten an already-passing decision, but it must
            # never rescue a deterministic task/concept mismatch.
            relevance = item.scoring_breakdown.relevance_score
            is_irrelevant_llm = item.paper.llm_relevance_label == "IRRELEVANT"
            deterministic_rejected = (
                item.paper.relevance_gate_evaluated
                and not item.paper.relevance_gate_passed
            )

            if deterministic_rejected or relevance < 0.2 or total < 0.25 or item.role == "IRRELEVANT" or is_irrelevant_llm:
                item.priority = "D_IGNORE"
                item.selection_reason = _append_reason(
                    item.selection_reason,
                    "Filtered: deterministic relevance gate failed or metadata confidence was too low.",
                )
                continue
            if item.paper.verification_status != VerificationStatus.VERIFIED:
                unverified_count += 1
            if self._eligible_for_a_read(item) and a_read_count < self.max_a_read:
                item.priority = "A_READ"
                a_read_count += 1
                item.selection_reason = _append_reason(item.selection_reason, "A_READ: verified, relevant, and full text is downloaded and validated.")
            elif total >= 0.45:
                item.priority = "B_SKIM"
                item.selection_reason = _append_reason(item.selection_reason, "B_SKIM: useful background, but not cleared for deep-card generation.")
            else:
                item.priority = "C_REFERENCE"
                item.selection_reason = _append_reason(item.selection_reason, "C_REFERENCE: keep metadata only.")

        visible_items = [item for item in items if item.priority != "D_IGNORE"]
        warnings: list[str] = []
        if a_read_count == 0:
            warnings.append("NO_A_READ_WITH_DOWNLOADABLE_FULL_TEXT")
        if unverified_count > 0:
            warnings.append(f"UNVERIFIED_CANDIDATES:{unverified_count}")
        if len(visible_items) < len(items):
            warnings.append(f"FILTERED_D_IGNORE:{len(items) - len(visible_items)}")

        output_items = items if include_ignored else visible_items
        status = "OK" if a_read_count > 0 else ("DEGRADED" if output_items else "FAILED")
        return ReadingPlan(topic=self._topic(query_plan), items=output_items, status=status, warnings=warnings)

    @staticmethod
    def _topic(query_plan: QueryPlan) -> str:
        return query_plan.english_query or query_plan.direction_en or query_plan.user_query

    def _score_item(self, query_plan: QueryPlan, paper: CandidatePaper) -> ReadingPlanItem:
        relevance = self._relevance_score(query_plan, paper)
        role = self._classify_role(paper, relevance)
        venue_score = self._venue_prestige(paper)
        citation_score = min((paper.citation_count or 0) / 1000.0, 1.0)
        code_score = 1.0 if paper.code_url else 0.0
        recency = self._recency_bonus(paper)
        source_reliability = self._source_reliability(paper)
        open_access_score = 1.0 if paper.open_access else 0.0
        pdf_available_score = self._source_readiness_score(paper)
        metadata_completeness = self._metadata_completeness(paper)
        method_rep = 0.85 if role not in {"SURVEY", "IRRELEVANT"} else 0.35
        intent_penalty = 0.0 if paper.relevance_gate_evaluated else _intent_mismatch_penalty(query_plan, paper)
        penalty = (-0.5 if relevance < 0.35 else 0.0) - intent_penalty

        total = max(
            0.0,
            min(
                1.0,
                0.28 * relevance
                + 0.20 * venue_score
                + 0.10 * citation_score
                + 0.04 * code_score
                + 0.10 * method_rep
                + 0.08 * recency
                + 0.14 * source_reliability
                + 0.06 * open_access_score
                + 0.12 * pdf_available_score
                + 0.04 * metadata_completeness
                + penalty,
            ),
        )

        breakdown = ScoringBreakdown(
            relevance_score=round(relevance, 3),
            venue_prestige=round(venue_score, 3),
            citation_score=round(citation_score, 3),
            code_availability=round(code_score, 3),
            method_representativeness=round(method_rep, 3),
            source_reliability=round(source_reliability, 3),
            open_access_score=round(open_access_score, 3),
            pdf_available_score=round(pdf_available_score, 3),
            metadata_completeness=round(metadata_completeness, 3),
            recency_bonus=round(recency, 3),
            penalty_noise=round(penalty, 3),
            weighted_total=round(total, 3),
        )
        minimum_relevance = (
            MIN_DEEP_READ_RELEVANCE_SCORE
            if paper.relevance_gate_evaluated
            else 0.45
        )
        relevance_gate_ok = (
            paper.relevance_gate_passed
            if paper.relevance_gate_evaluated
            else True
        )
        can_enter_m2 = bool(
            paper.can_enter_m2
            and relevance_gate_ok
            and breakdown.relevance_score >= minimum_relevance
            and _confidence_at_least(paper.source_confidence, "medium")
            and _confidence_at_least(paper.metadata_confidence, "medium")
        )
        return ReadingPlanItem(
            paper=paper.model_copy(update={"can_enter_m2": can_enter_m2}),
            role=role,
            priority="B_SKIM",
            scoring_breakdown=breakdown,
            selection_reason=self._selection_reason(paper, role, breakdown),
            risk_note=self._risk_note(paper, can_enter_m2),
            can_enter_m2=can_enter_m2,
        )

    def _relevance_score(self, query_plan: QueryPlan, paper: CandidatePaper) -> float:
        if paper.relevance_gate_evaluated:
            return paper.rule_relevance_score
        query_terms = query_plan.core_terms or [query_plan.english_query, query_plan.direction_en]
        related_terms = query_plan.related_terms + query_plan.query_variants
        text = f"{paper.title} {paper.abstract} {paper.tldr}".lower()
        if not any(term.strip() for term in query_terms):
            return self._relevance_score_for_text(query_plan.user_query, paper)

        core_score = _term_score(text, query_terms)
        related_score = _term_score(text, related_terms)
        concept_score = _concept_coverage_score(text, query_terms)
        intent_penalty = _intent_mismatch_penalty(query_plan, paper)
        title_bonus = 0.12 if _term_score(paper.title.lower(), query_terms) > 0 else 0.0
        return min(1.0, max(0.0, 0.58 * core_score + 0.18 * related_score + 0.24 * concept_score + title_bonus - intent_penalty))

    def _relevance_score_for_text(self, query: str, paper: CandidatePaper) -> float:
        tokens = [token for token in re.split(r"[^a-z0-9]+", query.lower()) if len(token) > 2]
        return _term_score(f"{paper.title} {paper.abstract} {paper.tldr}".lower(), tokens)

    def _classify_role(self, paper: CandidatePaper, relevance: float) -> str:
        if relevance < 0.2:
            return "IRRELEVANT"
        text = f"{paper.title} {paper.abstract} {paper.tldr}".lower()
        if any(term in text for term in ("survey", "review", "systematic literature review", "tutorial")):
            return "SURVEY"
        if any(term in text for term in ("benchmark", "evaluation", "evaluating", "datasets")):
            return "BENCHMARK"
        if any(term in text for term in ("transformer", "attention", "self-attention")):
            return "TRANSFORMER_METHOD"
        if any(term in text for term in ("graph", "gnn", "gcn", "graph neural")):
            return "GRAPH_METHOD"
        if any(term in text for term in ("vae", "gan", "diffusion", "generative")):
            return "GENERATIVE_METHOD"
        if any(term in text for term in ("reconstruction", "autoencoder", "encoder-decoder")):
            return "RECONSTRUCTION_METHOD"
        if any(term in text for term in ("forecast", "prediction", "predictive", "lstm", "rnn")):
            return "PREDICTION_METHOD"
        return "METHOD"

    def _venue_prestige(self, paper: CandidatePaper) -> float:
        """Delegate to the VENUE_REGISTRY-backed venue_score.

        ``venue_score_for_paper`` handles canonical name short-circuit,
        substring alias matching, and the empty/arxiv fallback bucket in
        a single place; tests assert on the registry, not on this wrapper.
        """
        return venue_score_for_paper(paper)

    def _source_reliability(self, paper: CandidatePaper) -> float:
        sources = paper.sources or ([paper.source] if paper.source else [])
        if not sources:
            return 0.2
        return max(SOURCE_RELIABILITY.get(source, 0.45) for source in sources)

    @staticmethod
    def _metadata_completeness(paper: CandidatePaper) -> float:
        fields = [
            paper.title,
            paper.year,
            paper.authors,
            paper.abstract or paper.tldr,
            paper.doi or paper.arxiv_id or paper.semantic_scholar_id,
            paper.venue,
            paper.citation_count is not None,
            paper.pdf_url or paper.landing_url or paper.url,
        ]
        return sum(1 for field in fields if field) / len(fields)

    @staticmethod
    def _recency_bonus(paper: CandidatePaper) -> float:
        if paper.year is None:
            return 0.0
        age = date.today().year - paper.year
        if age <= 1:
            return 0.9
        if age <= 3:
            return 0.65
        if age <= 6:
            return 0.35
        return 0.1

    @staticmethod
    def _source_readiness_score(paper: CandidatePaper) -> float:
        """Rank source-first candidates above URL-only candidates without relaxing gates."""
        if (
            paper.preferred_m2_input == "latex_source"
            or paper.source_priority == SourcePriority.LATEX_SOURCE
            or paper.latex_source_downloaded
            or paper.latex_source_available
        ):
            return 1.0
        if paper.has_valid_deep_reading_source and (paper.pdf_downloaded or paper.can_enter_m2):
            return 0.92
        if paper.pdf_downloaded:
            return 0.88
        if paper.can_deep_read or paper.selected_fulltext_url:
            return 0.82
        if paper.pdf_available or paper.pdf_url:
            return 0.72
        return 0.0

    @staticmethod
    def _eligible_for_a_read(item: ReadingPlanItem) -> bool:
        """A_READ requires ALL of (AND logic, not OR):

        Canonical gate:
        - has_valid_deep_reading_source == True
        - canonical_paper_path exists (non-empty)
        - m2_ready == True
        - canonical_quality_status != FAIL
        - source_priority != METADATA_ONLY

        Selection gate:
        - verification_status == VERIFIED
        - scoring_breakdown.relevance_score >= 0.45 (rule-based)
        - if LLM relevance exists, it must not reject the paper
        - should_a_read == True or download_selected == True
        - download_selected == True
        - source_confidence >= medium
        - metadata_confidence >= medium
        - role != "IRRELEVANT"
        """
        paper = item.paper
        sr = item.scoring_breakdown

        # Canonical gate checks
        has_valid_source = paper.has_valid_deep_reading_source
        has_canonical = bool(paper.canonical_paper_path)
        m2_ready = paper.m2_ready
        quality_ok = paper.canonical_quality_status != CanonicalQualityStatus.FAIL
        not_metadata_only = paper.source_priority != SourcePriority.METADATA_ONLY

        # Selection checks
        verified = paper.verification_status == VerificationStatus.VERIFIED
        minimum_relevance = (
            MIN_DEEP_READ_RELEVANCE_SCORE
            if paper.relevance_gate_evaluated
            else 0.45
        )
        relevant = sr.relevance_score >= minimum_relevance
        deterministic_gate_ok = (
            paper.relevance_gate_passed
            if paper.relevance_gate_evaluated
            else True
        )
        llm_relevant = paper.llm_relevance_score <= 0 or paper.llm_relevance_score >= 0.65
        llm_label_ok = not paper.llm_relevance_label or paper.llm_relevance_label in ("HIGH", "MEDIUM")
        should_read = paper.should_a_read is True or paper.download_selected is True
        download_ok = paper.download_selected is True
        source_ok = _confidence_at_least(paper.source_confidence, "medium")
        meta_ok = _confidence_at_least(paper.metadata_confidence, "medium")
        role_ok = item.role != "IRRELEVANT"

        return all([
            # Canonical gate
            has_valid_source,
            has_canonical,
            m2_ready,
            quality_ok,
            not_metadata_only,
            # Selection gate
            verified,
            relevant,
            deterministic_gate_ok,
            llm_relevant,
            llm_label_ok,
            should_read,
            download_ok,
            source_ok,
            meta_ok,
            role_ok,
        ])

    @staticmethod
    def _risk_note(paper: CandidatePaper, can_enter_m2: bool) -> str:
        notes = []
        if not can_enter_m2:
            notes.append("Not cleared for M2 deep-card generation until full text is downloaded and validated.")
        if paper.source_confidence == "low" or paper.metadata_confidence == "low":
            notes.append("Metadata/source confidence is low; verify before using as an anchor paper.")
        return " ".join(notes)

    @staticmethod
    def _selection_reason(paper: CandidatePaper, role: str, breakdown: ScoringBreakdown) -> str:
        parts = [
            f"role={role}",
            f"relevance={breakdown.relevance_score}",
            f"source={','.join(paper.sources or [paper.source])}",
            f"pdf={'yes' if breakdown.pdf_available_score else 'no'}",
            f"metadata={breakdown.metadata_completeness}",
        ]
        if paper.preferred_m2_input:
            parts.append(f"m2_input={paper.preferred_m2_input}")
        if paper.has_valid_deep_reading_source:
            parts.append("source_ready=yes")
        if breakdown.venue_prestige >= 0.9:
            parts.append("top-venue-signal")
        if paper.venue_rank != VenueRank.UNRANKED:
            parts.append(f"venue_rank={paper.venue_rank.value}")
        if breakdown.citation_score >= 0.1:
            parts.append(f"citations~{int(breakdown.citation_score * 1000)}")
        return "; ".join(parts)

    @staticmethod
    def _normalize_candidate(candidate: CandidatePaper) -> CandidatePaper:
        normalized_title = _normalize_title(candidate.title)
        sources = _unique(candidate.sources or ([candidate.source] if candidate.source else []))
        source_ids = dict(candidate.source_ids)
        if candidate.source and candidate.paper_id and candidate.source not in source_ids:
            source_ids[candidate.source] = candidate.paper_id
        venue_cfg = venue_config_for_paper(candidate)
        venue_rank = venue_cfg.rank if venue_cfg is not None else VenueRank.UNRANKED
        venue_canonical_name = venue_cfg.canonical_name if venue_cfg is not None else candidate.venue_canonical_name
        return candidate.model_copy(
            update={
                "normalized_title": normalized_title,
                "sources": sources,
                "source_ids": source_ids,
                "venue_canonical_name": venue_canonical_name,
                "venue_rank": venue_rank,
                "pdf_available": bool(candidate.pdf_available or candidate.pdf_url),
                "landing_url": candidate.landing_url or candidate.url,
            }
        )

    @staticmethod
    def _find_duplicate_index(
        paper: CandidatePaper,
        seen_doi: dict[str, int],
        seen_arxiv: dict[str, int],
        seen_s2: dict[str, int],
        seen_title: dict[str, int],
    ) -> int | None:
        doi_key = _normalize_doi(paper.doi)
        if doi_key and doi_key in seen_doi:
            return seen_doi[doi_key]
        arxiv_key = _normalize_arxiv_id(paper.arxiv_id)
        if arxiv_key and arxiv_key in seen_arxiv:
            return seen_arxiv[arxiv_key]
        if paper.semantic_scholar_id and paper.semantic_scholar_id in seen_s2:
            return seen_s2[paper.semantic_scholar_id]
        if paper.normalized_title and paper.normalized_title in seen_title:
            return seen_title[paper.normalized_title]
        if paper.normalized_title and paper.year:
            title_year = f"{paper.normalized_title}:{paper.year}"
            if title_year in seen_title:
                return seen_title[title_year]
        return None

    @staticmethod
    def _register_keys(
        paper: CandidatePaper,
        index: int,
        seen_doi: dict[str, int],
        seen_arxiv: dict[str, int],
        seen_s2: dict[str, int],
        seen_title: dict[str, int],
    ) -> None:
        doi_key = _normalize_doi(paper.doi)
        arxiv_key = _normalize_arxiv_id(paper.arxiv_id)
        if doi_key:
            seen_doi[doi_key] = index
        if arxiv_key:
            seen_arxiv[arxiv_key] = index
        if paper.semantic_scholar_id:
            seen_s2[paper.semantic_scholar_id] = index
        if paper.normalized_title:
            seen_title[paper.normalized_title] = index
            if paper.year:
                seen_title[f"{paper.normalized_title}:{paper.year}"] = index

    @staticmethod
    def _merge_paper(keep: CandidatePaper, dup: CandidatePaper) -> CandidatePaper:
        sources = _unique([*(keep.sources or ([keep.source] if keep.source else [])), *(dup.sources or ([dup.source] if dup.source else []))])
        source_ids = {**keep.source_ids, **dup.source_ids}
        raw = dict(keep.raw_source_metadata)
        if dup.raw_source_metadata:
            raw[dup.source or f"source_{len(raw)}"] = dup.raw_source_metadata

        updates = {
            "sources": sources,
            "source_ids": source_ids,
            "raw_source_metadata": raw,
            "candidate_pdf_urls": _unique([*keep.candidate_pdf_urls, *dup.candidate_pdf_urls, keep.pdf_url, dup.pdf_url]),
            "candidate_source_urls": _unique([*keep.candidate_source_urls, *dup.candidate_source_urls, keep.source_url, dup.source_url]),
            "candidate_html_urls": _unique([*keep.candidate_html_urls, *dup.candidate_html_urls]),
            "open_access": bool(keep.open_access or dup.open_access),
            "pdf_available": bool(keep.pdf_available or dup.pdf_available or keep.pdf_url or dup.pdf_url),
            "pdf_downloaded": bool(keep.pdf_downloaded or dup.pdf_downloaded),
            "can_enter_m2": bool(keep.can_enter_m2 or dup.can_enter_m2),
            "source_confidence": _max_confidence(keep.source_confidence, dup.source_confidence),
            "metadata_confidence": _max_confidence(keep.metadata_confidence, dup.metadata_confidence),
        }
        for field_name in (
            "abstract",
            "tldr",
            "pdf_url",
            "source_url",
            "landing_url",
            "url",
            "doi",
            "arxiv_id",
            "semantic_scholar_id",
            "venue",
            "code_url",
        ):
            keep_value = getattr(keep, field_name)
            dup_value = getattr(dup, field_name)
            if not keep_value and dup_value:
                updates[field_name] = dup_value
            elif field_name in {"abstract", "tldr"} and len(str(dup_value or "")) > len(str(keep_value or "")):
                updates[field_name] = dup_value
        if keep.citation_count is None or (dup.citation_count or 0) > (keep.citation_count or 0):
            updates["citation_count"] = dup.citation_count
        if keep.year is None and dup.year is not None:
            updates["year"] = dup.year
        if not keep.authors and dup.authors:
            updates["authors"] = dup.authors
        return keep.model_copy(update=updates)


def _normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def _normalize_doi(doi: str) -> str:
    normalized = doi.strip().lower()
    for prefix in _DOI_PREFIXES:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
    return normalized


def _normalize_arxiv_id(arxiv_id: str) -> str:
    normalized = arxiv_id.strip()
    if normalized.lower().startswith("arxiv:"):
        normalized = normalized[6:]
    return re.sub(r"v\d+$", "", normalized)


def _concept_coverage_score(text: str, query_terms: Iterable[str]) -> float:
    groups = _required_concept_groups(query_terms)
    if not groups:
        return 0.0
    hits = sum(1 for _name, terms, _weight in groups if any(term in text for term in terms))
    return hits / len(groups)


def _intent_mismatch_penalty(query_plan: QueryPlan, paper: CandidatePaper) -> float:
    query_terms = query_plan.core_terms or [query_plan.english_query, query_plan.direction_en]
    groups = _required_concept_groups(query_terms)
    if not groups:
        return 0.0
    text = f"{paper.title} {paper.abstract} {paper.tldr}".lower()
    missing_weight = sum(weight for _name, terms, weight in groups if not any(term in text for term in terms))
    return min(0.36, missing_weight)


def _required_concept_groups(query_terms: Iterable[str]) -> list[tuple[str, tuple[str, ...], float]]:
    query_text = " ".join(term.lower() for term in query_terms if term)
    groups: list[tuple[str, tuple[str, ...], float]] = []
    if "time series" in query_text or "temporal" in query_text:
        groups.append(("time_series", ("time series", "temporal", "sequence"), 0.06))
    if "multivariate" in query_text:
        groups.append(("multivariate", ("multivariate", "multi-variate", "multiple variables", "sensor"), 0.05))
    if "anomaly" in query_text or "outlier" in query_text:
        groups.append(("anomaly", ("anomaly", "anomalies", "outlier", "novelty", "abnormal"), 0.14))
    if "forecast" in query_text or "prediction" in query_text:
        groups.append(("forecasting", ("forecast", "forecasting", "prediction", "predictive", "residual"), 0.14))
    if "imputation" in query_text:
        groups.append(("imputation", ("imputation", "missing data", "missing values", "masking"), 0.14))
    if "graph" in query_text or "gnn" in query_text:
        groups.append(("graph", ("graph", "gnn", "graph neural", "spatio-temporal"), 0.12))
    return groups


def _term_score(text: str, terms: Iterable[str]) -> float:
    cleaned_terms = [term.lower().strip() for term in terms if term and term.strip()]
    if not cleaned_terms:
        return 0.0
    hits = sum(1 for term in cleaned_terms if term in text)
    return hits / len(cleaned_terms)


def _unique(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result


def _confidence_at_least(value: str, minimum: str) -> bool:
    return _CONFIDENCE_ORDER.get(value, 0) >= _CONFIDENCE_ORDER.get(minimum, 0)


def _max_confidence(left: str, right: str) -> str:
    return left if _CONFIDENCE_ORDER.get(left, 0) >= _CONFIDENCE_ORDER.get(right, 0) else right


def _append_reason(reason: str, extra: str) -> str:
    return f"{reason}; {extra}" if reason else extra
