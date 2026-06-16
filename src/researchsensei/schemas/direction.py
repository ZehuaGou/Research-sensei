from __future__ import annotations

from datetime import datetime, timezone

from pydantic import Field

from researchsensei.schemas.base import SenseiModel
from researchsensei.schemas.common import WarningItem
from researchsensei.schemas.enums import CanonicalQualityStatus, CanonicalizationStatus, PaperSourceStatus, PaperSourceType, SearchIntent, SourcePriority, VerificationStatus


class QueryPlan(SenseiModel):
    """Structured query plan generated from user direction input."""

    user_query: str
    language: str = "zh"
    direction_zh: str = ""
    direction_en: str = ""
    english_query: str = ""
    query_variants: list[str] = Field(default_factory=list)
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
    sources: list[str] = Field(default_factory=list)
    source_ids: dict[str, str] = Field(default_factory=dict)
    url: str = ""
    landing_url: str = ""
    doi: str = ""
    arxiv_id: str = ""
    semantic_scholar_id: str = ""
    abstract: str = ""
    tldr: str = ""
    citation_count: int | None = None
    pdf_url: str = ""
    source_url: str = ""
    candidate_pdf_urls: list[str] = Field(default_factory=list)
    candidate_source_urls: list[str] = Field(default_factory=list)
    candidate_html_urls: list[str] = Field(default_factory=list)
    selected_fulltext_source: str = ""
    selected_fulltext_url: str = ""
    fulltext_status: str = "metadata_only"
    fulltext_failure_reason: str = ""
    can_deep_read: bool = False
    needs_user_upload: bool = True
    code_url: str = ""
    open_access: bool = False
    pdf_available: bool = False
    pdf_downloaded: bool = False
    can_enter_m2: bool = False
    source_confidence: str = "low"
    metadata_confidence: str = "low"
    raw_source_metadata: dict[str, object] = Field(default_factory=dict)
    # M1.4 verification fields
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    verification_method: str = ""
    verification_reason: str = ""
    verification_confidence: str = "low"
    # M1.4 LLM relevance fields
    relevance_score: float = 0.0
    rule_relevance_score: float = 0.0
    llm_relevance_score: float = 0.0
    llm_relevance_label: str = ""  # HIGH, MEDIUM, LOW, IRRELEVANT
    matched_concepts: list[str] = Field(default_factory=list)
    missing_concepts: list[str] = Field(default_factory=list)
    relevance_reason: str = ""
    should_download: bool = False
    should_a_read: bool = False
    # Source-aware M1 fields
    source_priority: SourcePriority = SourcePriority.METADATA_ONLY
    preferred_m2_input: str = ""  # latex_source | structured_html | pdf | none
    has_valid_deep_reading_source: bool = False
    latex_source_available: bool = False
    latex_source_downloaded: bool = False
    latex_main_file: str = ""
    structured_html_available: bool = False
    structured_html_downloaded: bool = False
    metadata_only: bool = True
    canonicalization_status: CanonicalizationStatus = CanonicalizationStatus.NOT_ATTEMPTED
    canonical_quality_status: CanonicalQualityStatus = CanonicalQualityStatus.FAIL
    canonical_paper_path: str = ""
    m2_ready: bool = False
    degradation_reason: str = ""


class ScoringBreakdown(SenseiModel):
    """Explainable scoring breakdown for a candidate paper."""

    relevance_score: float = 0.0
    venue_prestige: float = 0.0
    citation_score: float = 0.0
    code_availability: float = 0.0
    method_representativeness: float = 0.0
    source_reliability: float = 0.0
    open_access_score: float = 0.0
    pdf_available_score: float = 0.0
    metadata_completeness: float = 0.0
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
    can_enter_m2: bool = False


class CandidatePool(SenseiModel):
    """Collection of candidate papers from search."""

    query: str
    retrieved_count: int = 0
    deduplicated_count: int = 0
    strong_related_count: int = 0
    items: list[CandidatePaper] = Field(default_factory=list)
    search_log: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    source_metrics: list[dict[str, object]] = Field(default_factory=list)


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
    download_status: str = ""
    final_url: str = ""
    content_type: str = ""
    file_size: int = 0
    sha256: str = ""
    local_path: str = ""
    error_code: str = ""
    warnings: list[WarningItem] = Field(default_factory=list)
    error: str = ""
    metadata: dict[str, str] = Field(default_factory=dict)
    # M1.3 PDF metadata validation fields
    pdf_metadata_check: str = ""  # "passed", "failed", "skipped"
    pdf_title_match: str = ""  # "match", "mismatch", "unknown"
    pdf_metadata_warning: str = ""
    # Source-aware M1 fields
    source_priority: SourcePriority = SourcePriority.METADATA_ONLY
    preferred_m2_input: str = ""
    has_valid_deep_reading_source: bool = False
    latex_source_available: bool = False
    latex_source_downloaded: bool = False
    latex_main_file: str = ""
    latex_source_path: str = ""
    latex_source_sha256: str = ""
    structured_html_available: bool = False
    structured_html_downloaded: bool = False
    structured_html_path: str = ""
    canonicalization_status: CanonicalizationStatus = CanonicalizationStatus.NOT_ATTEMPTED
    canonical_quality_status: CanonicalQualityStatus = CanonicalQualityStatus.FAIL
    canonical_paper_path: str = ""
    m2_ready: bool = False
    degradation_reason: str = ""


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
    status: str = "OK"
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    warnings: list[str] = Field(default_factory=list)


class DirectionBundle(SenseiModel):
    """Complete direction analysis bundle."""

    status: str = "UNKNOWN"
    direction_workspace_status: str = "UNKNOWN"
    query: str = ""
    message: str = ""
    overview: str = ""
    key_sub_directions: list[dict[str, object]] = Field(default_factory=list)
    method_families: list[dict[str, object]] = Field(default_factory=list)
    candidate_cards: list[dict[str, object]] = Field(default_factory=list)
    recommended_reading_order: list[dict[str, object]] = Field(default_factory=list)
    deep_read_candidates: list[dict[str, object]] = Field(default_factory=list)
    source_metrics: list[dict[str, object]] = Field(default_factory=list)
    seed_expansion_status: str = "NOT_IMPLEMENTED"
    query_plan: QueryPlan
    candidate_pool: CandidatePool
    source_resolution: SourceResolutionResult = Field(default_factory=lambda: SourceResolutionResult(query=""))
    filtered_candidates: CandidatePool
    reading_plan: ReadingPlan
    warnings: list[str] = Field(default_factory=list)
    # M1.4 verification and relevance metadata
    verification_summary: dict[str, int] = Field(default_factory=dict)
    relevance_summary: dict[str, int] = Field(default_factory=dict)


class SeedPaperInput(SenseiModel):
    """Seed paper payload accepted by the minimal Seed Expansion loop."""

    title: str = ""
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    venue: str = ""
    source: str = ""
    url: str = ""
    landing_url: str = ""
    paper_url: str = ""
    doi: str = ""
    arxiv_id: str = ""
    arxiv_url: str = ""
    pdf_url: str = ""
    paper_id: str = ""
    source_confidence: str = "low"
    verification_status: str = "unverified"


class SeedExpansionPaper(SenseiModel):
    """One paper in the seed expansion reading network."""

    paper_id: str
    source: str = ""
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    venue: str = ""
    url: str = ""
    landing_url: str = ""
    paper_url: str = ""
    doi: str = ""
    arxiv_id: str = ""
    arxiv_url: str = ""
    pdf_url: str = ""
    relation_type: str
    relation_reason: str
    relation_basis: str = "query_similarity"
    citation_graph_verified: bool = False
    confidence: float = 0.0
    verification_status: str = "unverified"
    source_confidence: str = "low"
    can_enter_m2: bool = False
    can_prepare_deep_read: bool = False
    deep_read_unavailable_reason: str = ""
    is_weak_relation: bool = True


class SeedExpansionOrderItem(SenseiModel):
    """Recommended reading order item for seed expansion."""

    rank: int
    title: str
    relation_type: str
    reason: str = ""
    can_enter_m2: bool = False


class SeedExpansionBundle(SenseiModel):
    """Minimal seed-paper expansion bundle built from real source adapters."""

    status: str = "UNKNOWN"
    seed_expansion_status: str = "UNKNOWN"
    message: str = ""
    query: str = ""
    seed: SeedPaperInput = Field(default_factory=SeedPaperInput)
    upstream_papers: list[SeedExpansionPaper] = Field(default_factory=list)
    downstream_papers: list[SeedExpansionPaper] = Field(default_factory=list)
    same_route_papers: list[SeedExpansionPaper] = Field(default_factory=list)
    related_surveys: list[SeedExpansionPaper] = Field(default_factory=list)
    follow_up_improvements: list[dict[str, object]] = Field(default_factory=list)
    recommended_expansion_order: list[SeedExpansionOrderItem] = Field(default_factory=list)
    papers: list[SeedExpansionPaper] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    source_metrics: list[dict[str, object]] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
