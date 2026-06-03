from __future__ import annotations

import re

from backend.schemas import (
    CandidatePaper,
    CandidatePool,
    CandidatePoolItem,
    PaperRole,
    ReadingPlan,
    ReadingPlanItem,
    ReadingPriority,
    ScoringBreakdown,
)


TOP_VENUE_TERMS = (
    "aaai",
    "kdd",
    "sigkdd",
    "vldb",
    "pvldb",
    "iclr",
    "neurips",
    "icml",
    "ijcai",
    "www",
    "web conference",
    "proceedings of the ieee",
)


class SelectionService:
    """Turns raw candidates into an explainable reading plan."""

    def build_reading_plan(self, topic: str, candidates: list[CandidatePaper], max_a_read: int = 8) -> ReadingPlan:
        items = [self._score_item(topic, self._normalize_candidate(candidate)) for candidate in candidates]
        top_candidates = [item for item in items if item.priority != ReadingPriority.D_IGNORE]
        a_read_candidates = sorted(top_candidates, key=lambda item: item.scoring_breakdown.weighted_total, reverse=True)
        selected_ids = {id(item) for item in a_read_candidates[:max_a_read]}
        normalized_items: list[ReadingPlanItem] = []
        for item in items:
            if item.priority != ReadingPriority.D_IGNORE:
                item.priority = ReadingPriority.A_READ if id(item) in selected_ids else ReadingPriority.B_SKIM
            normalized_items.append(item)
        normalized_items.sort(key=lambda item: (
            item.priority != ReadingPriority.A_READ,
            -item.scoring_breakdown.weighted_total,
        ))
        return ReadingPlan(topic=topic, items=normalized_items)

    def _normalize_candidate(self, candidate: CandidatePaper) -> CandidatePaper:
        normalized = re.sub(r"[^a-z0-9]+", " ", candidate.title.lower()).strip()
        return candidate.model_copy(update={"normalized_title": normalized or candidate.normalized_title})

    def _score_item(self, topic: str, paper: CandidatePaper) -> ReadingPlanItem:
        relevance, noise_reason = self._relevance(topic, paper)
        role = self._role(paper, relevance)
        venue = self._venue_prestige(paper)
        citations = min((paper.citation_count or 0) / 1000.0, 1.0)
        code = 1.0 if paper.code_url or paper.github_repo else 0.0
        method_rep = 0.9 if role not in {PaperRole.SURVEY, PaperRole.IRRELEVANT} else 0.3
        evaluation = 0.8 if role == PaperRole.EVALUATION_CRITIQUE else 0.2
        penalty = -0.8 if relevance < 0.3 else 0.0
        total = max(0.0, min(1.0, 0.36 * relevance + 0.22 * venue + 0.14 * citations + 0.06 * code + 0.14 * method_rep + 0.08 * evaluation + penalty))
        priority = ReadingPriority.D_IGNORE if relevance < 0.3 or role == PaperRole.IRRELEVANT else ReadingPriority.B_SKIM
        breakdown = ScoringBreakdown(
            relevance_score=relevance,
            venue_prestige=venue,
            citation_score=citations,
            code_availability=code,
            method_representativeness=method_rep,
            evaluation_value=evaluation,
            penalty_noise=penalty,
            weighted_total=total,
        )
        reason = (
            "方向强相关，且具备方法代表性或可信 venue/citation 信号。"
            if priority != ReadingPriority.D_IGNORE
            else f"过滤：{noise_reason}"
        )
        return ReadingPlanItem(
            paper=paper,
            role=role,
            priority=priority,
            scoring_breakdown=breakdown,
            selection_reason=reason,
            risk_note="评分可解释，需在全文解析后继续校验实验和 claim。",
        )

    def _relevance(self, topic: str, paper: CandidatePaper) -> tuple[float, str]:
        text = f"{paper.title} {paper.abstract}".lower()
        if "time series" in topic.lower() or "时间序列" in topic:
            known = {"tranad", "usad", "anomaly transformer", "gdn"}
            if any(alias in paper.title.lower() for alias in known):
                return 0.95, ""
            has_time = any(term in text for term in ["time series", "temporal", "multivariate"])
            has_anomaly = any(term in text for term in ["anomaly", "outlier", "fault detection"])
            if "forecast" in text and ("without anomaly" in text or "no anomaly" in text):
                return 0.05, "pure forecasting"
            if has_time and has_anomaly:
                return 0.95, ""
            if "forecast" in text and not has_anomaly:
                return 0.05, "pure forecasting"
            if "intrusion detection" in text and not has_time:
                return 0.05, "intrusion detection only"
            return 0.2, "missing required time-series anomaly signals"
        return (0.7 if topic.lower() in text else 0.4, "")

    def _role(self, paper: CandidatePaper, relevance: float) -> PaperRole:
        text = f"{paper.title} {paper.abstract}".lower()
        if relevance < 0.3:
            return PaperRole.IRRELEVANT
        if "survey" in text or "review" in text:
            return PaperRole.SURVEY
        if "tranad" in text or "transformer" in text or "attention" in text:
            return PaperRole.TRANSFORMER_METHOD
        if "graph" in text or "gdn" in text:
            return PaperRole.STRUCTURE_METHOD
        if "vae" in text or "gan" in text or "generative" in text:
            return PaperRole.GENERATION_METHOD
        if "reconstruction" in text or "usad" in text or "autoencoder" in text:
            return PaperRole.RECONSTRUCTION_METHOD
        if (
            "benchmark" in paper.title.lower()
            or "evaluation protocol" in text
            or "evaluating" in paper.title.lower()
            or "critique" in text
        ):
            return PaperRole.EVALUATION_CRITIQUE
        if "deep" in text or "neural" in text or "lstm" in text:
            return PaperRole.DEEP_BASELINE
        return PaperRole.CLASSIC_METHOD

    def _venue_prestige(self, paper: CandidatePaper) -> float:
        text = f"{paper.venue} {paper.venue_rank_hint} {paper.doi}".lower()
        if any(term in text for term in TOP_VENUE_TERMS):
            return 0.95
        if paper.venue and paper.venue.lower() not in {"unknown", "google_scholar"}:
            return 0.55
        return 0.2


class CandidatePoolBuilder:
    """Build a CandidatePool from raw search results."""

    def __init__(self, max_a_read: int = 5) -> None:
        self.max_a_read = max_a_read
        self._selection_service = SelectionService()

    def build(
        self,
        query: str,
        candidates: list[CandidatePaper],
        *,
        search_log: list[str] | None = None,
    ) -> CandidatePool:
        reading_plan = self._selection_service.build_reading_plan(
            query, candidates, max_a_read=self.max_a_read
        )
        items: list[CandidatePoolItem] = []
        for plan_item in reading_plan.items:
            paper = plan_item.paper
            items.append(
                CandidatePoolItem(
                    paper=paper,
                    title=paper.title,
                    normalized_title=paper.normalized_title or paper.title.lower(),
                    year=paper.year,
                    venue=paper.venue,
                    source=[paper.source] if paper.source else [],
                    url=paper.url,
                    doi=paper.doi,
                    arxiv_id=paper.arxiv_id,
                    abstract=paper.abstract,
                    citation_count=paper.citation_count,
                    relevance_score=plan_item.scoring_breakdown.relevance_score,
                    quality_score=plan_item.scoring_breakdown.weighted_total,
                    role=plan_item.role,
                    reading_priority=plan_item.priority,
                    selection_reason=plan_item.selection_reason,
                )
            )
        return CandidatePool(
            query=query,
            retrieved_count=len(candidates),
            deduplicated_count=len(candidates),
            strong_related_count=sum(1 for i in items if i.reading_priority == ReadingPriority.A_READ),
            items=items,
            search_log=search_log or [],
        )
