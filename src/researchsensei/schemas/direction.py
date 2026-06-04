from __future__ import annotations

from datetime import datetime, timezone

from pydantic import Field

from researchsensei.schemas.base import SenseiModel
from researchsensei.schemas.common import WarningItem
from researchsensei.schemas.enums import PaperSourceStatus, PaperSourceType, SearchIntent


class QueryPlan(SenseiModel):
    """Structured query plan generated from user direction input."""

    user_query: str
    language: str = "zh"
    direction_zh: str = ""
    direction_en: str = ""
    core_terms: list[str] = Field(default_factory=list)
    related_terms: list[str] = Field(default_factory=list)
    exclude_terms: list[str] = Field(default_factory=list)
    search_intents: list[SearchIntent] = Field(default_factory=lambda: [SearchIntent.GENERAL])
    sub_directions: list[str] = Field(default_factory=list)
    is_cross_domain: bool = False
    domain_components: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CandidatePaper(SenseiModel):
    """A candidate paper from search results."""

    paper_id: str
    title: str
    normalized_title: str = ""
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    venue: str = ""
    source: str = ""  # arxiv, openalex, etc.
    url: str = ""
    doi: str = ""
    arxiv_id: str = ""
    abstract: str = ""
    citation_count: int | None = None
    pdf_url: str = ""
    code_url: str = ""


class ScoringBreakdown(SenseiModel):
    """Explainable scoring breakdown for a candidate paper."""

    relevance_score: float = 0.0
    venue_prestige: float = 0.0
    citation_score: float = 0.0
    code_availability: float = 0.0
    method_representativeness: float = 0.0
    recency_bonus: float = 0.0
    penalty_noise: float = 0.0
    weighted_total: float = 0.0


class ReadingPlanItem(SenseiModel):
    """A single item in a reading plan."""

    paper: CandidatePaper
    role: str = "METHOD"  # SURVEY, METHOD, BASELINE, BENCHMARK, CODE, etc.
    priority: str = "B_SKIM"  # A_READ, B_SKIM, C_REFERENCE, D_IGNORE
    scoring_breakdown: ScoringBreakdown = Field(default_factory=ScoringBreakdown)
    selection_reason: str = ""
    risk_note: str = ""


class CandidatePool(SenseiModel):
    """Collection of candidate papers from search."""

    query: str
    retrieved_count: int = 0
    deduplicated_count: int = 0
    strong_related_count: int = 0
    items: list[CandidatePaper] = Field(default_factory=list)
    search_log: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ResolvedPaperSource(SenseiModel):
    """M1.3 source acquisition result for one candidate paper.

    This records source material availability only. It must not contain parsed
    paper content; parsing belongs to M2.
    """

    paper_id: str
    title: str
    doi: str = ""
    arxiv_id: str = ""
    source_url: str = ""
    pdf_url: str = ""
    landing_url: str = ""
    source_type: PaperSourceType = PaperSourceType.METADATA_ONLY
    status: PaperSourceStatus = PaperSourceStatus.NOT_FOUND
    warnings: list[WarningItem] = Field(default_factory=list)
    error: str = ""
    metadata: dict[str, str] = Field(default_factory=dict)


class SourceResolutionResult(SenseiModel):
    """M1.3 source acquisition artifact for a candidate pool."""

    query: str
    items: list[ResolvedPaperSource] = Field(default_factory=list)
    warnings: list[WarningItem] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ReadingPlan(SenseiModel):
    """Structured reading plan with prioritized papers."""

    topic: str
    items: list[ReadingPlanItem] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    warnings: list[str] = Field(default_factory=list)


class DirectionBundle(SenseiModel):
    """Complete direction analysis bundle."""

    query_plan: QueryPlan
    candidate_pool: CandidatePool
    source_resolution: SourceResolutionResult = Field(default_factory=lambda: SourceResolutionResult(query=""))
    filtered_candidates: CandidatePool
    reading_plan: ReadingPlan
    warnings: list[str] = Field(default_factory=list)
