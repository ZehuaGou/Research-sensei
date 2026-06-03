from __future__ import annotations

import logging
import re

from researchsensei.schemas import (
    CandidatePaper,
    CandidatePool,
    QueryPlan,
    ReadingPlan,
    ReadingPlanItem,
    ScoringBreakdown,
)

logger = logging.getLogger(__name__)

# Top venue terms for prestige scoring
TOP_VENUE_TERMS = (
    "aaai", "kdd", "sigkdd", "vldb", "pvldb", "iclr", "neurips", "icml",
    "ijcai", "www", "web conference", "proceedings of the ieee",
    "acl", "emnlp", "naacl", "cvpr", "iccv", "eccv", "sigmod", "sigir",
)


class SelectionService:
    """Scores, deduplicates, and ranks candidate papers into a reading plan."""

    def __init__(self, max_a_read: int = 8) -> None:
        self.max_a_read = max_a_read

    def build_reading_plan(
        self,
        query_plan: QueryPlan,
        candidates: list[CandidatePaper],
    ) -> ReadingPlan:
        """Build a reading plan from query plan and candidates."""
        if not candidates:
            return ReadingPlan(
                topic=query_plan.direction_en or query_plan.user_query,
                items=[],
                warnings=["NO_CANDIDATES"],
            )

        # Normalize and score each candidate
        items: list[ReadingPlanItem] = []
        for candidate in candidates:
            normalized = self._normalize_candidate(candidate)
            item = self._score_item(query_plan, normalized)
            items.append(item)

        # Sort by weighted_total descending
        items.sort(key=lambda x: x.scoring_breakdown.weighted_total, reverse=True)

        # Assign priorities
        for i, item in enumerate(items):
            if item.scoring_breakdown.weighted_total < 0.3 or item.role == "IRRELEVANT":
                item.priority = "D_IGNORE"
            elif i < self.max_a_read:
                item.priority = "A_READ"
            else:
                item.priority = "B_SKIM"

        # Filter out D_IGNORE
        filtered = [item for item in items if item.priority != "D_IGNORE"]

        return ReadingPlan(
            topic=query_plan.direction_en or query_plan.user_query,
            items=filtered,
            warnings=[] if filtered else ["NO_RELEVANT_PAPERS"],
        )

    def build_candidate_pool(
        self,
        query: str,
        candidates: list[CandidatePaper],
        search_log: list[str] | None = None,
    ) -> CandidatePool:
        """Build a candidate pool from search results."""
        return CandidatePool(
            query=query,
            retrieved_count=len(candidates),
            deduplicated_count=len(candidates),
            strong_related_count=0,
            items=candidates,
            search_log=search_log or [],
        )

    def deduplicate(self, candidates: list[CandidatePaper]) -> list[CandidatePaper]:
        """Remove duplicate papers using DOI → arXiv ID → normalized title matching.

        When duplicates are found, keeps the first occurrence and merges missing
        metadata (abstract, citation_count, pdf_url, code_url, venue) from later
        duplicates into it.
        """
        if not candidates:
            return []

        seen_doi: dict[str, int] = {}
        seen_arxiv: dict[str, int] = {}
        seen_title: dict[str, int] = {}
        result: list[CandidatePaper] = []

        for paper in candidates:
            normalized = self._normalize_candidate(paper)

            # Check DOI match
            doi_key = paper.doi.strip().lower() if paper.doi else ""
            if doi_key and doi_key in seen_doi:
                result[seen_doi[doi_key]] = self._merge_paper(result[seen_doi[doi_key]], paper)
                continue

            # Check arXiv ID match
            arxiv_key = paper.arxiv_id.strip() if paper.arxiv_id else ""
            if arxiv_key and arxiv_key in seen_arxiv:
                result[seen_arxiv[arxiv_key]] = self._merge_paper(result[seen_arxiv[arxiv_key]], paper)
                continue

            # Check normalized title match
            title_key = normalized.normalized_title
            if title_key and title_key in seen_title:
                result[seen_title[title_key]] = self._merge_paper(result[seen_title[title_key]], paper)
                continue

            # New unique paper
            idx = len(result)
            if doi_key:
                seen_doi[doi_key] = idx
            if arxiv_key:
                seen_arxiv[arxiv_key] = idx
            if title_key:
                seen_title[title_key] = idx
            result.append(normalized)

        return result

    @staticmethod
    def _merge_paper(keep: CandidatePaper, dup: CandidatePaper) -> CandidatePaper:
        """Merge missing metadata from duplicate into the kept paper."""
        updates: dict[str, object] = {}
        if not keep.abstract and dup.abstract:
            updates["abstract"] = dup.abstract
        if keep.citation_count is None and dup.citation_count is not None:
            updates["citation_count"] = dup.citation_count
        if not keep.pdf_url and dup.pdf_url:
            updates["pdf_url"] = dup.pdf_url
        if not keep.code_url and dup.code_url:
            updates["code_url"] = dup.code_url
        if not keep.venue and dup.venue:
            updates["venue"] = dup.venue
        if not keep.doi and dup.doi:
            updates["doi"] = dup.doi
        if not keep.arxiv_id and dup.arxiv_id:
            updates["arxiv_id"] = dup.arxiv_id
        if not keep.url and dup.url:
            updates["url"] = dup.url
        if updates:
            return keep.model_copy(update=updates)
        return keep

    def _normalize_candidate(self, candidate: CandidatePaper) -> CandidatePaper:
        """Normalize candidate title for dedup."""
        normalized = re.sub(r"[^a-z0-9]+", " ", candidate.title.lower()).strip()
        return candidate.model_copy(update={"normalized_title": normalized or candidate.title.lower()})

    def _score_item(self, query_plan: QueryPlan, paper: CandidatePaper) -> ReadingPlanItem:
        """Score a single paper against the query plan."""
        relevance = self._relevance_score(query_plan, paper)
        role = self._classify_role(paper, relevance)
        venue_score = self._venue_prestige(paper)
        citation_score = min((paper.citation_count or 0) / 1000.0, 1.0)
        code_score = 1.0 if paper.code_url else 0.0
        recency = self._recency_bonus(paper)
        method_rep = 0.9 if role not in ("SURVEY", "IRRELEVANT") else 0.3
        penalty = -0.8 if relevance < 0.3 else 0.0

        total = max(0.0, min(1.0,
            0.36 * relevance
            + 0.22 * venue_score
            + 0.14 * citation_score
            + 0.06 * code_score
            + 0.14 * method_rep
            + 0.08 * recency
            + penalty
        ))

        breakdown = ScoringBreakdown(
            relevance_score=relevance,
            venue_prestige=venue_score,
            citation_score=citation_score,
            code_availability=code_score,
            method_representativeness=method_rep,
            recency_bonus=recency,
            penalty_noise=penalty,
            weighted_total=total,
        )

        reason = self._selection_reason(relevance, role, total)
        risk_note = "评分可解释，需在全文解析后继续校验实验和 claim。" if total >= 0.3 else ""

        return ReadingPlanItem(
            paper=paper,
            role=role,
            priority="B_SKIM",  # Will be updated later
            scoring_breakdown=breakdown,
            selection_reason=reason,
            risk_note=risk_note,
        )

    def _relevance_score(self, query_plan: QueryPlan, paper: CandidatePaper) -> float:
        """Calculate relevance score based on query terms and paper content."""
        text = f"{paper.title} {paper.abstract}".lower()
        core_terms = [t.lower() for t in query_plan.core_terms]
        related_terms = [t.lower() for t in query_plan.related_terms]

        if not core_terms:
            return 0.5

        # Check core term matches
        core_matches = sum(1 for term in core_terms if term in text)
        core_ratio = core_matches / len(core_terms) if core_terms else 0

        # Check related term matches
        related_matches = sum(1 for term in related_terms if term in text)
        related_ratio = related_matches / len(related_terms) if related_terms else 0

        # Weighted combination
        relevance = 0.7 * core_ratio + 0.3 * related_ratio

        # Bonus for exact title match
        if any(term in paper.title.lower() for term in core_terms):
            relevance = min(1.0, relevance + 0.2)

        return round(relevance, 3)

    def _classify_role(self, paper: CandidatePaper, relevance: float) -> str:
        """Classify the role of a paper."""
        if relevance < 0.3:
            return "IRRELEVANT"

        text = f"{paper.title} {paper.abstract}".lower()

        if "survey" in text or "review" in text or "综述" in text:
            return "SURVEY"
        if "benchmark" in text or "evaluation" in text or "evaluating" in text:
            return "BENCHMARK"
        if any(term in text for term in ["transformer", "attention", "self-attention"]):
            return "METHOD"
        if any(term in text for term in ["graph", "gnn", "gcn"]):
            return "METHOD"
        if any(term in text for term in ["vae", "gan", "generative", "diffusion"]):
            return "METHOD"
        if any(term in text for term in ["reconstruction", "autoencoder", "encoder"]):
            return "METHOD"
        if any(term in text for term in ["deep", "neural", "lstm", "rnn"]):
            return "METHOD"
        return "METHOD"

    def _venue_prestige(self, paper: CandidatePaper) -> float:
        """Calculate venue prestige score."""
        text = f"{paper.venue}".lower()
        if any(term in text for term in TOP_VENUE_TERMS):
            return 0.95
        if paper.venue and paper.venue.lower() not in ("unknown", "arxiv", ""):
            return 0.55
        return 0.2

    def _recency_bonus(self, paper: CandidatePaper) -> float:
        """Calculate recency bonus based on publication year."""
        if paper.year is None:
            return 0.0
        current_year = 2026
        age = current_year - paper.year
        if age <= 1:
            return 1.0
        if age <= 3:
            return 0.7
        if age <= 5:
            return 0.4
        return 0.1

    def _selection_reason(self, relevance: float, role: str, total: float) -> str:
        """Generate a human-readable selection reason."""
        if relevance < 0.3:
            return "方向相关性低，过滤。"
        if total >= 0.7:
            return "方向强相关，且具备方法代表性或可信 venue/citation 信号。"
        if total >= 0.5:
            return "方向相关，具有一定参考价值。"
        return "方向弱相关，可作为背景参考。"
