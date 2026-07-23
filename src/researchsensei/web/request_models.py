from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


ShortText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=600)]
LongText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=4000)]
EvidenceRef = Annotated[str, StringConstraints(strip_whitespace=True, max_length=240)]


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SettingsUpdate(StrictRequest):
    model: (
        Annotated[
            str,
            StringConstraints(strip_whitespace=True, min_length=1, max_length=160),
        ]
        | None
    ) = None
    paper_model: (
        Annotated[
            str,
            StringConstraints(strip_whitespace=True, min_length=1, max_length=160),
        ]
        | None
    ) = None
    tutor_model: (
        Annotated[
            str,
            StringConstraints(strip_whitespace=True, min_length=1, max_length=160),
        ]
        | None
    ) = None

    @model_validator(mode="after")
    def require_one_model(self) -> "SettingsUpdate":
        if not any((self.model, self.paper_model, self.tutor_model)):
            raise ValueError("At least one model selection is required.")
        return self


class SettingsValidationRequest(StrictRequest):
    live: bool = False
    timeout_seconds: float = Field(default=8.0, gt=0, le=30)


class OrphanCleanupRequest(StrictRequest):
    confirm: bool = False


class ConversationTurn(StrictRequest):
    role: Literal["user", "assistant", "system"]
    content: LongText


class SelectionExplainRequest(StrictRequest):
    selected_text: LongText = ""
    user_question: LongText = ""
    action: Literal["ask", "simplify", "example", "explain"] | None = None


class FormulaExplainRequest(StrictRequest):
    formula_id: ShortText = ""
    symbol: ShortText = ""
    selected_symbol: ShortText = ""


class TutorAskRequest(StrictRequest):
    question: Annotated[str, StringConstraints(strip_whitespace=True, max_length=1200)] = ""
    user_question: Annotated[str, StringConstraints(strip_whitespace=True, max_length=1200)] = ""
    selected_text: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)] = ""
    context_scope: Literal["paper", "selection"] = "paper"
    answer_mode: Literal["full_paper", "evidence_only"] = "full_paper"
    conversation_history: list[ConversationTurn] = Field(default_factory=list, max_length=20)


class AdvisorQuestionRequest(StrictRequest):
    advisor_mode: Literal["group_meeting", "defense", "qualifying_exam"] = "group_meeting"
    user_question: ShortText = ""
    focus_question: ShortText = ""
    question: ShortText = ""
    selected_text: Annotated[str, StringConstraints(strip_whitespace=True, max_length=900)] = ""


class AdvisorEvaluateRequest(StrictRequest):
    question: LongText = ""
    user_question: ShortText = ""
    user_answer: LongText = ""
    answer: LongText = ""
    expected_answer_points: list[ShortText] = Field(default_factory=list, max_length=20)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list, max_length=20)


class LearningSessionRequest(StrictRequest):
    count: int = Field(default=5, ge=1, le=20)
    include_not_due: bool = False


class LearningAnswerRequest(StrictRequest):
    user_answer: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=8000),
    ]


class DirectionSearchRequest(StrictRequest):
    query: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class CandidateRequest(BaseModel):
    """Evolving literature discovery candidate payload.

    Known source fields are bounded below. Extra metadata is intentionally
    accepted because candidates originate from multiple discovery providers;
    unknown fields are never used as source identities or file paths.
    """

    model_config = ConfigDict(extra="allow")

    title: Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)] = ""
    doi: ShortText = ""
    pdf_url: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2048)] = ""
    arxiv_id: ShortText = ""
    arxiv_url: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2048)] = ""
    url: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2048)] = ""
    source_url: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2048)] = ""
    landing_url: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2048)] = ""
    relevance_gate_evaluated: bool = False
    relevance_gate_passed: bool = False
    deep_read_relevance_passed: bool | None = None
    rule_relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    relevance_reason: Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)] = ""


class DirectionDeepReadRequest(StrictRequest):
    candidate: CandidateRequest | None = None
    force: bool = False
    title: Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)] = ""
    doi: ShortText = ""
    pdf_url: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2048)] = ""
    arxiv_id: ShortText = ""
    arxiv_url: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2048)] = ""

    @model_validator(mode="after")
    def require_candidate_or_source(self) -> "DirectionDeepReadRequest":
        if self.candidate is None and not any(
            (self.doi, self.pdf_url, self.arxiv_id, self.arxiv_url)
        ):
            raise ValueError("candidate or a DOI/arXiv/PDF source is required")
        return self


class SeedExpansionRequest(StrictRequest):
    seed: CandidateRequest | None = None
    candidate: CandidateRequest | None = None

    @model_validator(mode="after")
    def require_seed(self) -> "SeedExpansionRequest":
        if self.seed is None and self.candidate is None:
            raise ValueError("seed or candidate is required")
        return self
