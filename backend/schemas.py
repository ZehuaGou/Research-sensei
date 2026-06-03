from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SenseiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class SearchIntent(str, Enum):
    SURVEY_PAPER = "SURVEY_PAPER"
    FOUNDATIONAL_WORK = "FOUNDATIONAL_WORK"
    CLASSIC_METHOD = "CLASSIC_METHOD"
    SOTA_METHOD = "SOTA_METHOD"
    BENCHMARK_DATASET = "BENCHMARK_DATASET"
    EVALUATION_CRITIQUE = "EVALUATION_CRITIQUE"
    OPEN_SOURCE_CODE = "OPEN_SOURCE_CODE"
    RELATED_APPLICATION = "RELATED_APPLICATION"
    RECENT_TREND = "RECENT_TREND"
    BACKGROUND_KNOWLEDGE = "BACKGROUND_KNOWLEDGE"


class PaperRole(str, Enum):
    SURVEY = "survey"
    CLASSIC_METHOD = "classic_method"
    FOUNDATIONAL_THEORY = "foundational_theory"
    SHALLOW_BASELINE = "shallow_baseline"
    DEEP_BASELINE = "deep_baseline"
    REPRESENTATION_METHOD = "representation_method"
    OBJECTIVE_METHOD = "objective_method"
    STRUCTURE_METHOD = "structure_method"
    GENERATION_METHOD = "generation_method"
    RETRIEVAL_MEMORY_METHOD = "retrieval_memory_method"
    REASONING_PLANNING_METHOD = "reasoning_planning_method"
    CAUSAL_COUNTERFACTUAL_METHOD = "causal_counterfactual_method"
    EVALUATION_CRITIQUE = "evaluation_critique"
    SYSTEM_PIPELINE = "system_pipeline"
    APPLICATION_SYSTEM = "application_system"
    RECENT_TREND = "recent_trend"
    TRANSFORMER_METHOD = "transformer_method"
    GRAPH_METHOD = "graph_method"
    RECONSTRUCTION_METHOD = "reconstruction_method"
    IRRELEVANT = "irrelevant"


class ReadingPriority(str, Enum):
    A_READ = "A_READ"
    B_SKIM = "B_SKIM"
    C_REFERENCE = "C_REFERENCE"
    D_IGNORE = "D_IGNORE"


class BlockType(str, Enum):
    TITLE = "title"
    ABSTRACT = "abstract"
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    FORMULA = "formula"
    FIGURE = "figure"
    TABLE = "table"
    ALGORITHM = "algorithm"
    REFERENCE = "reference"
    APPENDIX = "appendix"


class EvidenceType(str, Enum):
    SUPPORTED_BY_TEXT = "SUPPORTED_BY_TEXT"
    SUPPORTED_BY_FORMULA = "SUPPORTED_BY_FORMULA"
    SUPPORTED_BY_EXPERIMENT = "SUPPORTED_BY_EXPERIMENT"
    REASONABLE_INFERENCE = "REASONABLE_INFERENCE"
    UNVERIFIED = "UNVERIFIED"
    NEEDS_HUMAN_CHECK = "NEEDS_HUMAN_CHECK"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class CardType(str, Enum):
    PAPER_CARD = "paper_card"
    FORMULA_CARD = "formula_card"
    CONCEPT_CARD = "concept_card"
    PATTERN_CARD = "pattern_card"
    DRILL_CARD = "drill_card"
    DIRECTION_MAP = "direction_map"


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class RelevanceLabel(str, Enum):
    STRONG_RELATED = "strong_related"
    WEAK_RELATED = "weak_related"
    IRRELEVANT = "irrelevant"


class QueryPlan(SenseiModel):
    user_query: str
    language: str = "zh"
    direction_zh: str
    direction_en: str
    core_terms: list[str] = Field(default_factory=list)
    related_terms: list[str] = Field(default_factory=list)
    exclude_terms: list[str] = Field(default_factory=list)
    search_intents: list[SearchIntent] = Field(default_factory=list)
    sub_directions: list[str] = Field(default_factory=list)
    is_cross_domain: bool = False
    domain_components: list[str] = Field(default_factory=list)


class CandidatePaper(SenseiModel):
    paper_id: str
    title: str
    normalized_title: str = ""
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    venue: str = ""
    venue_rank_hint: str = ""
    source: str = "manual"
    url: str = ""
    doi: str = ""
    arxiv_id: str = ""
    abstract: str = ""
    citation_count: int | None = None
    pdf_url: str = ""
    latex_source_url: str = ""
    code_url: str = ""
    github_repo: str = ""
    retrieval_sources: list[str] = Field(default_factory=list)
    search_intent: SearchIntent | None = None
    raw_relevance_reason: str = ""


class SearchRun(SenseiModel):
    query: str
    source_tool: str = "reuse_first"
    api_required: bool = False
    candidate_papers: list[CandidatePaper] = Field(default_factory=list)
    search_log: list[str] = Field(default_factory=list)


class CandidateMergeTrace(SenseiModel):
    merged_from_title: str
    source_platform: str = ""
    reason: str = ""


class CandidatePoolItem(SenseiModel):
    paper: CandidatePaper
    title: str
    normalized_title: str
    year: int | None = None
    venue: str = ""
    source: list[str] = Field(default_factory=list)
    url: str = ""
    doi: str = ""
    arxiv_id: str = ""
    abstract: str = ""
    citation_count: int | None = None
    source_score: int = 0
    relevance_score: float = 0.0
    relevance_label: RelevanceLabel = RelevanceLabel.IRRELEVANT
    quality_score: float = 0.0
    role: PaperRole = PaperRole.IRRELEVANT
    reading_priority: ReadingPriority = ReadingPriority.D_IGNORE
    filter_reason: str = ""
    selection_reason: str = ""
    merge_trace: list[CandidateMergeTrace] = Field(default_factory=list)


class CandidatePool(SenseiModel):
    query: str
    retrieved_count: int = 0
    deduplicated_count: int = 0
    strong_related_count: int = 0
    items: list[CandidatePoolItem] = Field(default_factory=list)
    summary: dict[str, int] = Field(default_factory=dict)
    search_log: list[str] = Field(default_factory=list)

    @property
    def a_read_items(self) -> list[CandidatePoolItem]:
        return [item for item in self.items if item.reading_priority == ReadingPriority.A_READ]

    @property
    def d_ignore_items(self) -> list[CandidatePoolItem]:
        return [item for item in self.items if item.reading_priority == ReadingPriority.D_IGNORE]


class ScoringBreakdown(SenseiModel):
    relevance_score: float = 0.0
    venue_prestige: float = 0.0
    citation_score: float = 0.0
    citation_velocity: float = 0.0
    code_availability: float = 0.0
    survey_value: float = 0.0
    method_representativeness: float = 0.0
    evaluation_value: float = 0.0
    recency_bonus: float = 0.0
    penalty_noise: float = 0.0
    weighted_total: float = 0.0


class ReadingPlanItem(SenseiModel):
    paper: CandidatePaper
    role: PaperRole
    priority: ReadingPriority
    scoring_breakdown: ScoringBreakdown
    selection_reason: str
    risk_note: str = ""


class ReadingPlan(SenseiModel):
    topic: str
    items: list[ReadingPlanItem] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    generator_version: str = "v0.5.0"

    @property
    def a_read(self) -> list[ReadingPlanItem]:
        return [item for item in self.items if item.priority == ReadingPriority.A_READ]


class ModelProviderConfig(SenseiModel):
    name: str
    kind: str = "openai_compatible"
    base_url: str = ""
    api_key_env: str = ""
    model: str = ""
    auth_header: str = "authorization"
    timeout_seconds: int = 60

    def chat_completions_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/chat/completions"


class AppRuntimeConfig(SenseiModel):
    workspace_dir: str = "workspace"
    max_upload_mb: int = 80
    parser_backend: str = "pymupdf"
    default_learning_mode: str = "reproducible_2h"


class ServerConfig(SenseiModel):
    host: str = "127.0.0.1"
    port: int = 8765
    reload: bool = False


class SearchConfig(SenseiModel):
    execution: str = "uvx"
    command: str = "paper-search"
    sources: list[str] = Field(default_factory=lambda: ["arxiv", "openalex"])
    max_results: int = 10
    timeout_seconds: int = 30
    min_citation_count: int = 0


class AppConfig(SenseiModel):
    active_provider: str = "deepseek"
    providers: dict[str, ModelProviderConfig] = Field(default_factory=dict)
    app: AppRuntimeConfig = Field(default_factory=AppRuntimeConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)

    def active_model_provider(self) -> ModelProviderConfig:
        if self.active_provider not in self.providers:
            raise KeyError(f"Unknown provider: {self.active_provider}")
        return self.providers[self.active_provider]


class WorkspaceArtifact(SenseiModel):
    artifact_type: str
    path: str


class JobRecord(SenseiModel):
    job_id: str
    status: JobStatus = JobStatus.PENDING
    filename: str
    source_path: str
    run_dir: str
    current_step: str = "uploaded"
    error: str = ""
    warnings: list[str] = Field(default_factory=list)
    artifacts: list[WorkspaceArtifact] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SourceTrustFlags(SenseiModel):
    is_peer_reviewed: bool | None = None
    is_retracted: bool = False
    venue_known: bool = False
    source_reliability: str = "unknown"
    warning: list[str] = Field(default_factory=list)


class SourceStatus(SenseiModel):
    paper_id: str
    source_kind: str = "abstract_only"
    source_path: str = ""
    warnings: list[str] = Field(default_factory=list)
    source_trust_flags: SourceTrustFlags = Field(default_factory=SourceTrustFlags)


class DocumentBlock(SenseiModel):
    block_id: str
    type: BlockType
    section: str = ""
    page: int | None = None
    text: str = ""
    normalized_text: str = ""
    offset_start: int = 0
    offset_end: int = 0
    raw_latex: str = ""
    nearby_text: str = ""
    equation_number: str = ""
    caption: str = ""
    table_html: str = ""
    figure_path: str = ""
    pseudo_code: str = ""
    evidence_ref: str


class DocumentIngestion(SenseiModel):
    paper_id: str
    detected_language: str = "en"
    sections: dict[str, str] = Field(default_factory=dict)
    formulas: list[DocumentBlock] = Field(default_factory=list)
    figures: list[DocumentBlock] = Field(default_factory=list)
    tables: list[DocumentBlock] = Field(default_factory=list)
    references: list[dict[str, Any]] = Field(default_factory=list)
    extraction_warnings: list[str] = Field(default_factory=list)
    blocks: list[DocumentBlock] = Field(default_factory=list)


class EvidenceClaim(SenseiModel):
    claim_id: str
    claim_text: str
    evidence_type: EvidenceType
    section: str = ""
    evidence_ref: str = ""
    quote_or_summary: str = ""
    confidence: float = 0.0


class EvidenceIndex(SenseiModel):
    paper_id: str
    claims: list[EvidenceClaim] = Field(default_factory=list)


class SkeletonField(SenseiModel):
    plain: str = ""
    technical: str = ""
    evidence: list[str] = Field(default_factory=list)


class ObjectiveItem(SenseiModel):
    formula_ref: str
    purpose: str
    why_this_form: str


class PaperSkeleton(SenseiModel):
    paper_id: str
    evidence_status: EvidenceType = EvidenceType.UNVERIFIED
    problem: SkeletonField
    old_methods: list[dict[str, str]] = Field(default_factory=list)
    bottleneck: list[dict[str, str]] = Field(default_factory=list)
    assumption: list[dict[str, str]] = Field(default_factory=list)
    representation: list[dict[str, str]] = Field(default_factory=list)
    mechanism: SkeletonField
    objective: list[ObjectiveItem] = Field(default_factory=list)
    experiments: list[dict[str, str]] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    transfer: list[dict[str, Any]] = Field(default_factory=list)
    pattern_candidates: list[str] = Field(default_factory=list)


class FormulaSymbol(SenseiModel):
    symbol: str
    meaning: str
    role: str


class FormulaCard(SenseiModel):
    card_id: str
    paper_id: str
    formula_ref: str
    formula_latex: str
    problem: str
    symbols: list[FormulaSymbol] = Field(default_factory=list)
    numeric_example: str = ""
    remove_effect: str = ""
    weight_change_effect: str = ""
    plain_summary: str = ""
    evidence_status: EvidenceType = EvidenceType.UNVERIFIED


class TeachingCard(SenseiModel):
    card_id: str
    paper_id: str
    card_type: CardType
    thirty_second: str
    five_minute: str
    deep_dive: str = ""
    evidence_status: EvidenceType = EvidenceType.UNVERIFIED


class PatternCard(SenseiModel):
    card_id: str
    pattern_id: str
    definition: str
    signals: list[str] = Field(default_factory=list)
    transfer_template: str = ""


class DrillCard(SenseiModel):
    card_id: str
    target: str
    recall_questions: list[str] = Field(default_factory=list)
    advisor_questions: list[str] = Field(default_factory=list)
    error_attribution_prompts: list[str] = Field(default_factory=list)


class InteractiveContextPackage(SenseiModel):
    session_id: str
    paper_id: str
    card_id: str
    card_type: CardType
    selected_text: str = ""
    current_section: str = ""
    current_formula_id: str = ""
    current_concept_id: str = ""
    paper_metadata: dict[str, Any] = Field(default_factory=dict)
    card_json: dict[str, Any] = Field(default_factory=dict)
    evidence_chunks: list[dict[str, str]] = Field(default_factory=list)
    recent_chat_history: list[dict[str, str]] = Field(default_factory=list)
    conversation_summary: str = ""
    user_profile: dict[str, str] = Field(default_factory=lambda: {
        "language": "zh",
        "math_level": "weak",
        "preferred_style": "concise_but_explain_clearly",
    })
    user_question: str


class SessionMemory(SenseiModel):
    session_id: str
    paper_id: str = ""
    understood_items: list[str] = Field(default_factory=list)
    confusing_items: list[str] = Field(default_factory=list)
    asked_questions: list[str] = Field(default_factory=list)
    weak_concepts: list[str] = Field(default_factory=list)
    review_cards: list[str] = Field(default_factory=list)
    user_profile: dict[str, str] = Field(default_factory=dict)


class InteractiveAnswer(SenseiModel):
    answer_zh: str
    context_used: InteractiveContextPackage
    evidence_status: EvidenceType = EvidenceType.UNVERIFIED
    add_to_review_suggestion: bool = False


class VersionedArtifact(SenseiModel):
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    generator_version: str = "v0.5.0"
    content_hash: str
    path: str


def to_plain_data(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [to_plain_data(item) for item in value]
    if isinstance(value, dict):
        return {key: to_plain_data(item) for key, item in value.items()}
    return value
