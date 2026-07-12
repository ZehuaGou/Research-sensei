from __future__ import annotations

import sqlite3
from pathlib import Path
from types import TracebackType
from typing import Literal


class ManagedConnection(sqlite3.Connection):
    """sqlite3 connection whose context manager also closes the handle."""

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> Literal[False]:
        try:
            super().__exit__(exc_type, exc, traceback)
            return False
        finally:
            self.close()


def connect_sqlite(path: str | Path, *, timeout: float = 5.0) -> sqlite3.Connection:
    return sqlite3.connect(path, timeout=timeout, factory=ManagedConnection)
