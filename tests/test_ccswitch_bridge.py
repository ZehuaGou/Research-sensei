from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from researchsensei.core.config import ModelProviderConfig
from researchsensei.llm.ccswitch_bridge import resolve_ccswitch_api_key


def _write_ccswitch_db(
    path: Path,
    *,
    base_url: str = "https://opencode.ai/zen/go",
    api_format: str = "openai_chat",
) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE providers (
                app_type TEXT,
                is_current INTEGER,
                created_at TEXT,
                settings_config TEXT,
                meta TEXT
            )
            """
        )
        connection.execute(
            "INSERT INTO providers VALUES (?, ?, ?, ?, ?)",
            (
                "claude",
                1,
                "2026-07-22T00:00:00Z",
                json.dumps(
                    {
                        "env": {
                            "ANTHROPIC_BASE_URL": base_url,
                            "ANTHROPIC_AUTH_TOKEN": "bridge-secret",
                        }
                    }
                ),
                json.dumps({"apiFormat": api_format}),
            ),
        )


def _provider() -> ModelProviderConfig:
    return ModelProviderConfig(
        name="opencode_go",
        kind="openai_compatible",
        base_url="https://opencode.ai/zen/go/v1",
        api_key_env="OPENCODE_GO_API_KEY",
        model="deepseek-v4-flash",
    )


def test_bridge_reads_matching_active_ccswitch_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENCODE_GO_API_KEY", raising=False)
    monkeypatch.delenv("RESEARCHSENSEI_CCSWITCH_CREDENTIAL_BRIDGE", raising=False)
    db_path = tmp_path / "cc-switch.db"
    _write_ccswitch_db(db_path)

    assert resolve_ccswitch_api_key(_provider(), db_path=db_path) == "bridge-secret"


def test_bridge_refuses_mismatched_upstream(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENCODE_GO_API_KEY", raising=False)
    db_path = tmp_path / "cc-switch.db"
    _write_ccswitch_db(db_path, base_url="https://example.invalid/other")

    assert resolve_ccswitch_api_key(_provider(), db_path=db_path) == ""


def test_bridge_can_be_disabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENCODE_GO_API_KEY", raising=False)
    monkeypatch.setenv("RESEARCHSENSEI_CCSWITCH_CREDENTIAL_BRIDGE", "0")
    db_path = tmp_path / "cc-switch.db"
    _write_ccswitch_db(db_path)

    assert resolve_ccswitch_api_key(_provider(), db_path=db_path) == ""
