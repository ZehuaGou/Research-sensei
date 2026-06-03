from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class WorkspaceStore:
    def __init__(self, root: str | Path = "workspace") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def new_run_dir(self, job_id: str | None = None) -> Path:
        run_id = job_id or uuid.uuid4().hex[:12]
        path = self.root / "runs" / run_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def new_search_dir(self) -> Path:
        path = self.root / "searches" / uuid.uuid4().hex[:12]
        path.mkdir(parents=True, exist_ok=True)
        return path

    def write_json(self, path: str | Path, value: object) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(to_plain_data(value), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return target

    def write_text(self, path: str | Path, value: str) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(value, encoding="utf-8")
        return target


def to_plain_data(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [to_plain_data(item) for item in value]
    if isinstance(value, dict):
        return {key: to_plain_data(item) for key, item in value.items()}
    return value
