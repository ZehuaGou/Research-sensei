from __future__ import annotations

import json
import uuid
from pathlib import Path

from backend.schemas import to_plain_data


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

    def write_json(self, path: Path, value: object) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(to_plain_data(value), ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def write_text(self, path: Path, value: str) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")
        return path
