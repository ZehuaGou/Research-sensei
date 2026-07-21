from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path

from starlette.testclient import TestClient

from researchsensei.schemas import CandidatePool, DirectionBundle, QueryPlan, ReadingPlan
from researchsensei.web.app import create_app
from researchsensei.web.services import PersistentTaskService, TaskExecutionError


def _wait(service: PersistentTaskService, task_id: str, timeout: float = 2.0) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        task = service.get(task_id)
        if task["status"] in {"SUCCEEDED", "FAILED", "CANCELLED", "INTERRUPTED"}:
            return task
        time.sleep(0.01)
    raise AssertionError(f"task {task_id} did not finish")


def test_persistent_task_records_progress_and_result(tmp_path: Path) -> None:
    service = PersistentTaskService(tmp_path / "tasks.sqlite3", max_workers=1)

    task = service.submit(
        "search",
        {"query": "test"},
        lambda progress, _cancel: (progress("ranking", 80) or {"papers": ["p1"]}),
    )
    finished = _wait(service, str(task["task_id"]))

    assert finished["status"] == "SUCCEEDED"
    assert finished["stage"] == "completed"
    assert finished["progress"] == 100
    assert finished["result"] == {"papers": ["p1"]}
    service.close()


def test_persistent_task_progress_never_moves_backwards(tmp_path: Path) -> None:
    service = PersistentTaskService(tmp_path / "tasks.sqlite3", max_workers=1)
    reported = threading.Event()
    release = threading.Event()

    def operation(progress, _cancel):
        progress("formula_cards_ready", 84)
        progress("paper_card_ready", 66)
        reported.set()
        assert release.wait(timeout=1.0)
        return {}

    task = service.submit("deep_read", {}, operation)
    assert reported.wait(timeout=1.0)
    running = service.get(str(task["task_id"]))
    release.set()
    _wait(service, str(task["task_id"]))

    assert running["stage"] == "paper_card_ready"
    assert running["progress"] == 84
    service.close()


def test_persistent_task_has_machine_readable_failure(tmp_path: Path) -> None:
    service = PersistentTaskService(tmp_path / "tasks.sqlite3", max_workers=1)

    def fail(_progress, _cancel):
        raise TaskExecutionError("SOURCE_UNAVAILABLE", "No verified full text.")

    task = service.submit("deep_read", {}, fail)
    finished = _wait(service, str(task["task_id"]))

    assert finished["status"] == "FAILED"
    assert finished["error_type"] == "SOURCE_UNAVAILABLE"
    assert finished["error"] == "No verified full text."
    service.close()


def test_persistent_task_can_cancel_running_operation(tmp_path: Path) -> None:
    service = PersistentTaskService(tmp_path / "tasks.sqlite3", max_workers=1)
    started = threading.Event()

    def cancellable(_progress, cancelled):
        started.set()
        assert cancelled.wait(timeout=1.0)
        return {"stopped": True}

    task = service.submit("search", {}, cancellable)
    assert started.wait(timeout=1.0)
    service.cancel(str(task["task_id"]))
    finished = _wait(service, str(task["task_id"]))

    assert finished["status"] == "CANCELLED"
    assert finished["cancel_requested"] is True
    service.close()


def test_service_restart_marks_legacy_running_task_interrupted(tmp_path: Path) -> None:
    db_path = tmp_path / "tasks.sqlite3"
    service = PersistentTaskService(db_path, max_workers=1)
    service.close()
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            insert into background_tasks(
                task_id, kind, status, stage, progress, payload, result, error_type, error,
                cancel_requested, created_at, updated_at
            ) values('stale', 'search', 'RUNNING', 'searching', 40, '{}', '{}', '', '', 0, 'now', 'now')
            """
        )

    restarted = PersistentTaskService(db_path, max_workers=1)
    task = restarted.get("stale")

    assert task["status"] == "INTERRUPTED"
    assert task["error_type"] == "SERVICE_RESTARTED"
    restarted.close()


def test_running_owner_clears_stale_restart_error_when_operation_finishes(tmp_path: Path) -> None:
    db_path = tmp_path / "tasks.sqlite3"
    owner = PersistentTaskService(db_path, max_workers=1)
    started = threading.Event()
    release = threading.Event()

    def operation(_progress, _cancel):
        started.set()
        assert release.wait(timeout=2.0)
        return {"completed": True}

    task = owner.submit("deep_read", {}, operation)
    assert started.wait(timeout=1.0)
    observer = PersistentTaskService(db_path, max_workers=1)
    assert observer.get(str(task["task_id"]))["status"] == "INTERRUPTED"
    observer.close()

    release.set()
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        finished = owner.get(str(task["task_id"]))
        if finished["status"] == "SUCCEEDED":
            break
        time.sleep(0.01)
    else:
        raise AssertionError("task owner did not publish successful completion")

    assert finished["error_type"] == ""
    assert finished["error"] == ""
    assert finished["result"] == {"completed": True}
    owner.close()


class StubDirectionService:
    def explore(self, query: str) -> DirectionBundle:
        return DirectionBundle(
            status="SUCCESS",
            query_plan=QueryPlan(user_query=query, english_query=query),
            candidate_pool=CandidatePool(query=query),
            filtered_candidates=CandidatePool(query=query),
            reading_plan=ReadingPlan(topic=query),
        )


def test_direction_search_async_api_returns_job_and_result(tmp_path: Path) -> None:
    with TestClient(
        create_app(workspace_root=tmp_path / "workspace", direction_service=StubDirectionService())
    ) as client:
        created = client.post(
            "/api/v1/directions/jobs/search",
            json={"query": "time series anomaly detection"},
        )
        assert created.status_code == 202
        task_id = created.json()["task_id"]
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            result = client.get(f"/api/v1/directions/jobs/{task_id}").json()
            if result["status"] == "SUCCEEDED":
                break
            time.sleep(0.01)
        else:
            raise AssertionError("direction search task did not finish")

        assert result["progress"] == 100
        assert result["result"]["status"] == "SUCCESS"
        assert result["result"]["papers"] == []


def test_document_parse_and_reparse_use_persistent_tasks(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    with TestClient(create_app(workspace_root=workspace)) as client:
        created = client.post(
            "/api/v1/documents/jobs/parse",
            data={"title": "Trusted Library Title"},
            files={
                "file": (
                    "paper.md",
                    b"## Abstract\nA short paper.\n\n## Method\nA grounded method description.",
                    "text/markdown",
                )
            },
        )
        assert created.status_code == 202
        parse_task = _wait_api_task(client, created.json()["task_id"])

        assert parse_task["status"] == "SUCCEEDED"
        job_id = parse_task["result"]["job_id"]
        paper_card = json.loads(
            (workspace / "runs" / job_id / "paper_card.json").read_text(encoding="utf-8")
        )
        assert paper_card["title"] == "Trusted Library Title"

        reparse = client.post(f"/api/v1/documents/jobs/{job_id}/reparse")
        assert reparse.status_code == 202
        reparse_task = _wait_api_task(client, reparse.json()["task_id"])

        assert reparse_task["status"] == "SUCCEEDED"
        assert reparse_task["result"]["source_job_id"] == job_id
        assert reparse_task["result"]["job_id"] != job_id


def _wait_api_task(
    client: TestClient,
    task_id: str,
    timeout: float = 3.0,
) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = client.get(f"/api/v1/documents/jobs/{task_id}")
        assert response.status_code == 200
        task = response.json()
        if task["status"] in {"SUCCEEDED", "FAILED", "CANCELLED", "INTERRUPTED"}:
            return task
        time.sleep(0.01)
    raise AssertionError(f"document task {task_id} did not finish")
