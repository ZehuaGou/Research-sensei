from __future__ import annotations

import json
from pathlib import Path

from researchsensei.schemas import StatusEnvelope
from researchsensei.workspace import WorkspaceStore


def test_new_run_dir_is_deterministic_when_job_id_is_given(tmp_path: Path) -> None:
    store = WorkspaceStore(tmp_path)

    run_dir = store.new_run_dir("job-123")

    assert run_dir == tmp_path / "runs" / "job-123"
    assert run_dir.exists()


def test_new_search_dir_creates_unique_directories(tmp_path: Path) -> None:
    store = WorkspaceStore(tmp_path)

    first = store.new_search_dir()
    second = store.new_search_dir()

    assert first.exists()
    assert second.exists()
    assert first != second


def test_write_json_uses_schema_safe_serialization_and_preserves_chinese(tmp_path: Path) -> None:
    store = WorkspaceStore(tmp_path)
    path = tmp_path / "runs" / "job-1" / "status.json"
    envelope = StatusEnvelope(status="ok", message="中文消息", data={"section": "摘要"})

    store.write_json(path, envelope)

    raw = path.read_text(encoding="utf-8")
    assert "中文消息" in raw
    assert json.loads(raw)["data"]["section"] == "摘要"


def test_write_text_uses_utf8(tmp_path: Path) -> None:
    store = WorkspaceStore(tmp_path)
    path = tmp_path / "runs" / "job-1" / "note.md"

    store.write_text(path, "这是一条记录")

    assert path.read_text(encoding="utf-8") == "这是一条记录"
