from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fsrs import Card, Rating, Scheduler

from researchsensei.learning.database import (
    dump_json,
    initialize_learning_database,
    learning_connection,
    load_string_list,
    utc_iso,
    utc_now,
)
from researchsensei.learning.records import (
    LearningPromptRecord,
    LearningSessionRecord,
    attempt_from_row,
    item_from_row,
)
from researchsensei.schemas.learning import (
    LearningAttempt,
    LearningItem,
    LearningOverview,
    LearningPaperSummary,
)


class LearningStore:
    """Persistent learning state, independent from paper-analysis artifacts."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        initialize_learning_database(self.db_path)

    def upsert_items(self, seeds: list[dict[str, object]]) -> list[LearningItem]:
        now = utc_iso()
        with self._connect() as conn:
            conn.execute("begin immediate")
            for seed in seeds:
                card = Card()
                conn.execute(
                    """
                    insert into learning_items(
                        item_id, job_id, paper_title, item_type, target_concept,
                        source_excerpt, evidence_refs, fsrs_card, due_at,
                        review_count, lapse_count, created_at, updated_at
                    ) values(?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, ?, ?)
                    on conflict(item_id) do update set
                        paper_title=excluded.paper_title,
                        target_concept=excluded.target_concept,
                        source_excerpt=excluded.source_excerpt,
                        evidence_refs=excluded.evidence_refs,
                        updated_at=excluded.updated_at
                    """,
                    (
                        str(seed["item_id"]),
                        str(seed["job_id"]),
                        str(seed["paper_title"]),
                        str(seed["item_type"]),
                        str(seed["target_concept"]),
                        str(seed.get("source_excerpt") or ""),
                        dump_json(seed.get("evidence_refs") or []),
                        card.to_json(),
                        card.due.isoformat(),
                        now,
                        now,
                    ),
                )
        job_ids = {str(seed["job_id"]) for seed in seeds}
        if len(job_ids) != 1:
            return []
        return self.list_items(job_id=next(iter(job_ids)))

    def list_items(
        self,
        *,
        job_id: str | None = None,
        due_only: bool = False,
        limit: int = 200,
    ) -> list[LearningItem]:
        clauses: list[str] = ["archived=0"]
        params: list[object] = []
        if job_id:
            clauses.append("job_id=?")
            params.append(job_id)
        if due_only:
            clauses.append("due_at<=?")
            params.append(utc_iso())
        params.append(max(1, min(int(limit), 500)))
        query = (
            "select * from learning_items where "
            + " and ".join(clauses)
            + " order by due_at asc, created_at asc limit ?"
        )
        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [item_from_row(row) for row in rows]

    def get_item(self, item_id: str) -> LearningItem:
        with self._connect() as conn:
            row = conn.execute(
                "select * from learning_items where item_id=? and archived=0",
                (item_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"Learning item not found: {item_id}")
        return item_from_row(row)

    def create_session(self, job_id: str, item_ids: list[str]) -> LearningSessionRecord:
        now = utc_iso()
        session_id = uuid.uuid4().hex[:16]
        with self._connect() as conn:
            conn.execute(
                """
                insert into learning_sessions(
                    session_id, job_id, item_ids, current_index, status, created_at, updated_at
                ) values(?, ?, ?, 0, ?, ?, ?)
                """,
                (
                    session_id,
                    job_id,
                    dump_json(item_ids),
                    "ACTIVE" if item_ids else "COMPLETED",
                    now,
                    now,
                ),
            )
        return self.get_session(session_id)

    def get_session(self, session_id: str) -> LearningSessionRecord:
        with self._connect() as conn:
            row = conn.execute(
                "select * from learning_sessions where session_id=?",
                (session_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"Learning session not found: {session_id}")
        return {
            "session_id": str(row["session_id"]),
            "job_id": str(row["job_id"]),
            "item_ids": load_string_list(row["item_ids"]),
            "current_index": int(row["current_index"]),
            "status": str(row["status"]),
            "created_at": str(row["created_at"]),
            "updated_at": str(row["updated_at"]),
        }

    def latest_active_session(self, job_id: str) -> LearningSessionRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                select session_id from learning_sessions
                where job_id=? and status='ACTIVE'
                order by updated_at desc limit 1
                """,
                (job_id,),
            ).fetchone()
        return self.get_session(str(row["session_id"])) if row is not None else None

    def current_item_id(self, session: LearningSessionRecord) -> str:
        item_ids = session["item_ids"]
        index = session["current_index"]
        return item_ids[index] if 0 <= index < len(item_ids) else ""

    def save_prompt(
        self,
        *,
        session_id: str,
        item_id: str,
        question: str,
        expected_points: list[str],
        why_it_matters: str,
        answer_format: list[str],
        evidence_refs: list[str],
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                insert into learning_session_prompts(
                    session_id, item_id, question, expected_points, why_it_matters,
                    answer_format, evidence_refs, created_at
                ) values(?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(session_id, item_id) do update set
                    question=excluded.question,
                    expected_points=excluded.expected_points,
                    why_it_matters=excluded.why_it_matters,
                    answer_format=excluded.answer_format,
                    evidence_refs=excluded.evidence_refs
                """,
                (
                    session_id,
                    item_id,
                    question,
                    dump_json(expected_points),
                    why_it_matters,
                    dump_json(answer_format),
                    dump_json(evidence_refs),
                    utc_iso(),
                ),
            )

    def get_prompt(self, session_id: str, item_id: str) -> LearningPromptRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                select * from learning_session_prompts
                where session_id=? and item_id=?
                """,
                (session_id, item_id),
            ).fetchone()
        if row is None:
            return None
        return {
            "question": str(row["question"]),
            "expected_answer_points": load_string_list(row["expected_points"]),
            "why_it_matters": str(row["why_it_matters"]),
            "answer_format": load_string_list(row["answer_format"]),
            "evidence_refs": load_string_list(row["evidence_refs"]),
        }

    def review_item(
        self,
        *,
        session_id: str,
        item: LearningItem,
        question: str,
        user_answer: str,
        score: float,
        rating: int,
        feedback: str,
        covered_points: list[str],
        missing_points: list[str],
        misconceptions: list[str],
        improvement_steps: list[str],
    ) -> LearningAttempt:
        reviewed_at = utc_now()
        with self._connect() as conn:
            row = conn.execute(
                "select fsrs_card, lapse_count from learning_items where item_id=?",
                (item.item_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"Learning item not found: {item.item_id}")
            card = Card.from_json(str(row["fsrs_card"]))
            scheduler = Scheduler(enable_fuzzing=False)
            updated_card, review_log = scheduler.review_card(
                card,
                Rating(rating),
                review_datetime=reviewed_at,
            )
            lapse_count = int(row["lapse_count"]) + (1 if rating == 1 else 0)
            attempt_id = uuid.uuid4().hex[:16]
            conn.execute("begin immediate")
            conn.execute(
                """
                update learning_items set
                    fsrs_card=?, due_at=?, review_count=review_count+1,
                    lapse_count=?, last_score=?, last_review_at=?, updated_at=?
                where item_id=?
                """,
                (
                    updated_card.to_json(),
                    updated_card.due.isoformat(),
                    lapse_count,
                    score,
                    reviewed_at.isoformat(),
                    reviewed_at.isoformat(),
                    item.item_id,
                ),
            )
            conn.execute(
                """
                insert into learning_attempts(
                    attempt_id, session_id, item_id, job_id, paper_title,
                    target_concept, question, user_answer, score, rating,
                    feedback, covered_points, missing_points, misconceptions,
                    improvement_steps, review_log, reviewed_at, next_due_at
                ) values(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    attempt_id,
                    session_id,
                    item.item_id,
                    item.job_id,
                    item.paper_title,
                    item.target_concept,
                    question,
                    user_answer,
                    score,
                    rating,
                    feedback,
                    dump_json(covered_points),
                    dump_json(missing_points),
                    dump_json(misconceptions),
                    dump_json(improvement_steps),
                    dump_json(review_log.to_dict()),
                    reviewed_at.isoformat(),
                    updated_card.due.isoformat(),
                ),
            )
            session = conn.execute(
                "select item_ids, current_index from learning_sessions where session_id=?",
                (session_id,),
            ).fetchone()
            if session is None:
                raise KeyError(f"Learning session not found: {session_id}")
            item_ids = load_string_list(session["item_ids"])
            next_index = int(session["current_index"]) + 1
            status = "COMPLETED" if next_index >= len(item_ids) else "ACTIVE"
            conn.execute(
                """
                update learning_sessions
                set current_index=?, status=?, updated_at=?
                where session_id=?
                """,
                (next_index, status, reviewed_at.isoformat(), session_id),
            )
        return self.get_attempt(attempt_id)

    def get_attempt(self, attempt_id: str) -> LearningAttempt:
        with self._connect() as conn:
            row = conn.execute(
                "select * from learning_attempts where attempt_id=?",
                (attempt_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"Learning attempt not found: {attempt_id}")
        return attempt_from_row(row)

    def overview(self, *, job_id: str | None = None, due_limit: int = 30) -> LearningOverview:
        where = "where archived=0"
        params: list[object] = []
        if job_id:
            where += " and job_id=?"
            params.append(job_id)
        now = utc_iso()
        local_now = datetime.now().astimezone()
        local_day_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_start_utc = local_day_start.astimezone(timezone.utc).isoformat()
        with self._connect() as conn:
            total = conn.execute(
                f"""
                select count(*) as total,
                    sum(case when due_at<=? then 1 else 0 end) as due_count,
                    sum(case when review_count>=2 and last_score>=0.75 then 1 else 0 end) as mastered_count
                from learning_items {where}
                """,
                (now, *params),
            ).fetchone()
            papers = conn.execute(
                f"""
                select job_id, paper_title, count(*) as item_count,
                    sum(case when due_at<=? then 1 else 0 end) as due_count,
                    sum(case when review_count>=2 and last_score>=0.75 then 1 else 0 end) as mastered_count,
                    sum(case when review_count>0 then 1 else 0 end) as reviewed_count,
                    max(last_review_at) as last_review_at
                from learning_items {where}
                group by job_id, paper_title
                order by due_count desc, last_review_at desc, paper_title asc
                """,
                (now, *params),
            ).fetchall()
            attempt_where = "where reviewed_at>=?"
            attempt_params: list[object] = [today_start_utc]
            if job_id:
                attempt_where += " and job_id=?"
                attempt_params.append(job_id)
            reviewed_today = conn.execute(
                f"select count(*) as count from learning_attempts {attempt_where}",
                tuple(attempt_params),
            ).fetchone()
            recent_where = "where job_id=?" if job_id else ""
            recent_params: tuple[object, ...] = (job_id, 12) if job_id else (12,)
            recent = conn.execute(
                f"""
                select * from learning_attempts {recent_where}
                order by reviewed_at desc limit ?
                """,
                recent_params,
            ).fetchall()
        return LearningOverview(
            total_items=int(total["total"] or 0),
            due_count=int(total["due_count"] or 0),
            mastered_count=int(total["mastered_count"] or 0),
            reviewed_today=int(reviewed_today["count"] or 0),
            papers=[
                LearningPaperSummary(
                    job_id=str(row["job_id"]),
                    paper_title=str(row["paper_title"]),
                    item_count=int(row["item_count"] or 0),
                    due_count=int(row["due_count"] or 0),
                    mastered_count=int(row["mastered_count"] or 0),
                    reviewed_count=int(row["reviewed_count"] or 0),
                    last_review_at=str(row["last_review_at"] or ""),
                )
                for row in papers
            ],
            due_items=self.list_items(job_id=job_id, due_only=True, limit=due_limit),
            recent_attempts=[attempt_from_row(row) for row in recent],
        )

    def _connect(self) -> sqlite3.Connection:
        return learning_connection(self.db_path)
