from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from researchsensei.core.sqlite import connect_sqlite

TaskOperation = Callable[[Callable[[str, int], None], threading.Event], dict[str, object]]


class TaskNotFoundError(KeyError):
    pass


class TaskExecutionError(RuntimeError):
    def __init__(self, error_type: str, message: str) -> None:
        super().__init__(message)
        self.error_type = error_type


class PersistentTaskService:
    """Small persistent task executor for long local M1 operations."""

    def __init__(self, db_path: str | Path, *, max_workers: int = 2) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="sensei-task")
        self._lock = threading.RLock()
        self._cancel_events: dict[str, threading.Event] = {}
        self._futures: dict[str, Future[object]] = {}
        self._init()
        self._mark_stale_tasks()

    def submit(self, kind: str, payload: dict[str, object], operation: TaskOperation) -> dict[str, object]:
        task_id = uuid.uuid4().hex[:16]
        now = _now()
        with self._connect() as conn:
            conn.execute(
                """
                insert into background_tasks(
                    task_id, kind, status, stage, progress, payload, result, error_type, error,
                    cancel_requested, created_at, updated_at
                ) values(?, ?, 'PENDING', 'queued', 0, ?, '{}', '', '', 0, ?, ?)
                """,
                (task_id, kind, json.dumps(payload, ensure_ascii=False), now, now),
            )
        cancel_event = threading.Event()
        with self._lock:
            self._cancel_events[task_id] = cancel_event
            self._futures[task_id] = self._executor.submit(
                self._run,
                task_id,
                operation,
                cancel_event,
            )
        return self.get(task_id)

    def get(self, task_id: str) -> dict[str, object]:
        with self._connect() as conn:
            row = conn.execute("select * from background_tasks where task_id = ?", (task_id,)).fetchone()
        if row is None:
            raise TaskNotFoundError(task_id)
        return _task_payload(row)

    def cancel(self, task_id: str) -> dict[str, object]:
        task = self.get(task_id)
        if task["status"] in {"SUCCEEDED", "FAILED", "CANCELLED", "INTERRUPTED"}:
            return task
        self._update(
            task_id,
            status="CANCEL_REQUESTED",
            stage="cancelling",
            cancel_requested=1,
        )
        with self._lock:
            event = self._cancel_events.get(task_id)
            future = self._futures.get(task_id)
            cancelled_before_start = bool(future and future.cancel())
            if event is not None:
                event.set()
        if cancelled_before_start:
            self._update(
                task_id,
                status="CANCELLED",
                stage="cancelled",
                cancel_requested=1,
            )
        return self.get(task_id)

    def close(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)

    def _run(self, task_id: str, operation: TaskOperation, cancel_event: threading.Event) -> None:
        if cancel_event.is_set():
            self._update(task_id, status="CANCELLED", stage="cancelled", progress=0, cancel_requested=1)
            return
        self._update(
            task_id,
            status="RUNNING",
            stage="starting",
            progress=1,
            error_type="",
            error="",
            cancel_requested=0,
        )
        progress_lock = threading.Lock()
        progress_high_watermark = 1

        def progress(stage: str, value: int) -> None:
            nonlocal progress_high_watermark
            bounded = max(0, min(int(value), 99))
            with progress_lock:
                progress_high_watermark = max(progress_high_watermark, bounded)
                self._update(
                    task_id,
                    stage=stage[:120],
                    progress=progress_high_watermark,
                )

        try:
            result = operation(progress, cancel_event)
            if cancel_event.is_set():
                self._update(
                    task_id,
                    status="CANCELLED",
                    stage="cancelled",
                    progress=100,
                    result=result,
                    cancel_requested=1,
                )
            else:
                self._update(
                    task_id,
                    status="SUCCEEDED",
                    stage="completed",
                    progress=100,
                    result=result,
                    error_type="",
                    error="",
                    cancel_requested=0,
                )
        except TaskExecutionError as error:
            self._update(
                task_id,
                status="FAILED",
                stage="failed",
                error_type=error.error_type,
                error=str(error)[:1000],
            )
        except Exception as error:
            self._update(
                task_id,
                status="FAILED",
                stage="failed",
                error_type=type(error).__name__,
                error=str(error)[:1000],
            )
        finally:
            with self._lock:
                self._cancel_events.pop(task_id, None)
                self._futures.pop(task_id, None)

    def _update(
        self,
        task_id: str,
        *,
        status: str | None = None,
        stage: str | None = None,
        progress: int | None = None,
        result: dict[str, object] | None = None,
        error_type: str | None = None,
        error: str | None = None,
        cancel_requested: int | None = None,
    ) -> None:
        assignments: list[str] = []
        values: list[object] = []
        for column, value in (
            ("status", status),
            ("stage", stage),
            ("progress", progress),
            ("result", json.dumps(result, ensure_ascii=False) if result is not None else None),
            ("error_type", error_type),
            ("error", error),
            ("cancel_requested", cancel_requested),
        ):
            if value is not None:
                assignments.append(f"{column} = ?")
                values.append(value)
        assignments.append("updated_at = ?")
        values.append(_now())
        values.append(task_id)
        with self._connect() as conn:
            conn.execute(
                f"update background_tasks set {', '.join(assignments)} where task_id = ?",
                tuple(values),
            )

    def _connect(self) -> sqlite3.Connection:
        conn = connect_sqlite(self.db_path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        conn.execute("pragma busy_timeout=5000")
        conn.execute("pragma journal_mode=wal")
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                create table if not exists schema_meta(
                    component text primary key,
                    version integer not null,
                    updated_at text not null
                )
                """
            )
            conn.execute(
                """
                create table if not exists background_tasks(
                    task_id text primary key,
                    kind text not null,
                    status text not null,
                    stage text not null,
                    progress integer not null,
                    payload text not null,
                    result text not null,
                    error_type text not null,
                    error text not null,
                    cancel_requested integer not null default 0,
                    created_at text not null,
                    updated_at text not null
                )
                """
            )
            conn.execute("create index if not exists idx_background_tasks_status on background_tasks(status)")
            conn.execute(
                """
                insert into schema_meta(component, version, updated_at) values('background_tasks', 1, ?)
                on conflict(component) do update set version=excluded.version, updated_at=excluded.updated_at
                """,
                (_now(),),
            )

    def _mark_stale_tasks(self) -> None:
        now = _now()
        with self._connect() as conn:
            conn.execute(
                """
                update background_tasks
                set status='INTERRUPTED', stage='service_restarted', progress=100,
                    error_type='SERVICE_RESTARTED',
                    error='The service restarted before this local task completed.',
                    updated_at=?
                where status in ('PENDING', 'RUNNING', 'CANCEL_REQUESTED')
                """,
                (now,),
            )


def _task_payload(row: sqlite3.Row) -> dict[str, object]:
    return {
        "job_id": row["task_id"],
        "task_id": row["task_id"],
        "kind": row["kind"],
        "status": row["status"],
        "stage": row["stage"],
        "progress": row["progress"],
        "result": json.loads(row["result"] or "{}"),
        "error_type": row["error_type"],
        "error": row["error"],
        "cancel_requested": bool(row["cancel_requested"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
