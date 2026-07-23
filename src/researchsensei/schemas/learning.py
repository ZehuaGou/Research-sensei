from __future__ import annotations

from typing import Literal

from pydantic import Field

from researchsensei.schemas.base import SenseiModel
from researchsensei.schemas.common import WarningItem


LearningItemType = Literal["paper", "concept", "method", "formula", "experiment", "limitation"]
LearningSessionStatus = Literal["ACTIVE", "COMPLETED"]


class LearningItem(SenseiModel):
    item_id: str
    job_id: str
    paper_title: str
    item_type: LearningItemType
    target_concept: str
    source_excerpt: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    due_at: str
    retrievability: float = Field(default=0.0, ge=0.0, le=1.0)
    stability: float | None = None
    difficulty: float | None = None
    review_count: int = 0
    lapse_count: int = 0
    last_score: float | None = Field(default=None, ge=0.0, le=1.0)
    last_review_at: str = ""
    created_at: str
    updated_at: str


class LearningQuestion(SenseiModel):
    session_id: str
    item_id: str
    position: int
    total: int
    question: str
    target_concept: str
    item_type: LearningItemType
    expected_answer_points: list[str] = Field(default_factory=list)
    why_it_matters: str = ""
    answer_format: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class LearningAttempt(SenseiModel):
    attempt_id: str
    session_id: str
    item_id: str
    job_id: str
    paper_title: str
    target_concept: str
    question: str
    user_answer: str
    score: float = Field(ge=0.0, le=1.0)
    rating: int = Field(ge=1, le=4)
    feedback: str = ""
    covered_points: list[str] = Field(default_factory=list)
    missing_points: list[str] = Field(default_factory=list)
    misconceptions: list[str] = Field(default_factory=list)
    improvement_steps: list[str] = Field(default_factory=list)
    reviewed_at: str
    next_due_at: str


class LearningSession(SenseiModel):
    session_id: str
    job_id: str
    status: LearningSessionStatus
    total: int
    completed: int
    current: LearningQuestion | None = None
    created_at: str
    updated_at: str


class LearningPaperSummary(SenseiModel):
    job_id: str
    paper_title: str
    item_count: int = 0
    due_count: int = 0
    mastered_count: int = 0
    reviewed_count: int = 0
    last_review_at: str = ""


class LearningOverview(SenseiModel):
    total_items: int = 0
    due_count: int = 0
    mastered_count: int = 0
    reviewed_today: int = 0
    papers: list[LearningPaperSummary] = Field(default_factory=list)
    due_items: list[LearningItem] = Field(default_factory=list)
    recent_attempts: list[LearningAttempt] = Field(default_factory=list)


class LearningAnswerResult(SenseiModel):
    attempt: LearningAttempt
    session: LearningSession
    warnings: list[WarningItem] = Field(default_factory=list)
