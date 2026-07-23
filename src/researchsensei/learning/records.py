from __future__ import annotations

import sqlite3
from typing import TypedDict

from fsrs import Card, Scheduler

from researchsensei.learning.database import load_string_list
from researchsensei.schemas.learning import LearningAttempt, LearningItem


class LearningSessionRecord(TypedDict):
    session_id: str
    job_id: str
    item_ids: list[str]
    current_index: int
    status: str
    created_at: str
    updated_at: str


class LearningPromptRecord(TypedDict):
    question: str
    expected_answer_points: list[str]
    why_it_matters: str
    answer_format: list[str]
    evidence_refs: list[str]


def item_from_row(row: sqlite3.Row) -> LearningItem:
    card = Card.from_json(str(row["fsrs_card"]))
    try:
        retrievability = Scheduler(enable_fuzzing=False).get_card_retrievability(card)
    except (TypeError, ValueError, ZeroDivisionError):
        retrievability = 0.0
    return LearningItem(
        item_id=str(row["item_id"]),
        job_id=str(row["job_id"]),
        paper_title=str(row["paper_title"]),
        item_type=str(row["item_type"]),
        target_concept=str(row["target_concept"]),
        source_excerpt=str(row["source_excerpt"]),
        evidence_refs=load_string_list(row["evidence_refs"]),
        due_at=str(row["due_at"]),
        retrievability=max(0.0, min(float(retrievability), 1.0)),
        stability=card.stability,
        difficulty=card.difficulty,
        review_count=int(row["review_count"]),
        lapse_count=int(row["lapse_count"]),
        last_score=float(row["last_score"]) if row["last_score"] is not None else None,
        last_review_at=str(row["last_review_at"] or ""),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def attempt_from_row(row: sqlite3.Row) -> LearningAttempt:
    return LearningAttempt(
        attempt_id=str(row["attempt_id"]),
        session_id=str(row["session_id"]),
        item_id=str(row["item_id"]),
        job_id=str(row["job_id"]),
        paper_title=str(row["paper_title"]),
        target_concept=str(row["target_concept"]),
        question=str(row["question"]),
        user_answer=str(row["user_answer"]),
        score=float(row["score"]),
        rating=int(row["rating"]),
        feedback=str(row["feedback"]),
        covered_points=load_string_list(row["covered_points"]),
        missing_points=load_string_list(row["missing_points"]),
        misconceptions=load_string_list(row["misconceptions"]),
        improvement_steps=load_string_list(row["improvement_steps"]),
        reviewed_at=str(row["reviewed_at"]),
        next_due_at=str(row["next_due_at"]),
    )
