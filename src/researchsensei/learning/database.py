from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from researchsensei.core.sqlite import connect_sqlite


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_iso(value: datetime | None = None) -> str:
    return (value or utc_now()).astimezone(timezone.utc).isoformat()


def dump_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def load_string_list(value: Any) -> list[str]:
    try:
        parsed = json.loads(str(value or "[]"))
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item).strip() for item in parsed if str(item).strip()]


def learning_connection(db_path: Path) -> sqlite3.Connection:
    conn = connect_sqlite(db_path, timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("pragma busy_timeout=5000")
    conn.execute("pragma foreign_keys=on")
    return conn


def initialize_learning_database(db_path: Path) -> None:
    with learning_connection(db_path) as conn:
        conn.execute("pragma journal_mode=wal")
        conn.execute(
            """
            create table if not exists learning_items(
                item_id text primary key,
                job_id text not null references jobs(job_id) on delete cascade,
                paper_title text not null,
                item_type text not null,
                target_concept text not null,
                source_excerpt text not null default '',
                evidence_refs text not null default '[]',
                fsrs_card text not null,
                due_at text not null,
                review_count integer not null default 0,
                lapse_count integer not null default 0,
                last_score real,
                last_review_at text not null default '',
                archived integer not null default 0,
                created_at text not null,
                updated_at text not null
            )
            """
        )
        conn.execute(
            """
            create table if not exists learning_sessions(
                session_id text primary key,
                job_id text not null references jobs(job_id) on delete cascade,
                item_ids text not null,
                current_index integer not null default 0,
                status text not null,
                created_at text not null,
                updated_at text not null
            )
            """
        )
        conn.execute(
            """
            create table if not exists learning_session_prompts(
                session_id text not null references learning_sessions(session_id) on delete cascade,
                item_id text not null references learning_items(item_id) on delete cascade,
                question text not null,
                expected_points text not null default '[]',
                why_it_matters text not null default '',
                answer_format text not null default '[]',
                evidence_refs text not null default '[]',
                created_at text not null,
                primary key(session_id, item_id)
            )
            """
        )
        conn.execute(
            """
            create table if not exists learning_attempts(
                attempt_id text primary key,
                session_id text not null references learning_sessions(session_id) on delete cascade,
                item_id text not null references learning_items(item_id) on delete cascade,
                job_id text not null references jobs(job_id) on delete cascade,
                paper_title text not null,
                target_concept text not null,
                question text not null,
                user_answer text not null,
                score real not null,
                rating integer not null,
                feedback text not null default '',
                covered_points text not null default '[]',
                missing_points text not null default '[]',
                misconceptions text not null default '[]',
                improvement_steps text not null default '[]',
                review_log text not null default '{}',
                reviewed_at text not null,
                next_due_at text not null
            )
            """
        )
        conn.execute(
            "create index if not exists idx_learning_items_due on learning_items(due_at, job_id)"
        )
        conn.execute(
            "create index if not exists idx_learning_attempts_reviewed "
            "on learning_attempts(reviewed_at desc)"
        )
