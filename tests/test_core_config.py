from __future__ import annotations

import os
from pathlib import Path

import pytest

from researchsensei.core.config import ConfigService, redact_secret


def _write_config(path: Path, *, active_provider: str = "mimo", port: int = 18765) -> None:
    path.write_text(
        f"""
active_provider = "{active_provider}"

[providers.deepseek]
kind = "openai_compatible"
base_url = "https://api.deepseek.com"
api_key_env = "DEEPSEEK_API_KEY"
model = "deepseek-chat"
timeout_seconds = 60

[providers.mimo]
kind = "openai_compatible"
base_url = "https://token-plan-cn.xiaomimimo.com/v1"
api_key_env = "MIMO_API_KEY"
model = "mimo-v2.5-pro"
auth_header = "api-key"
timeout_seconds = 60

[app]
workspace_dir = "workspace"
default_learning_mode = "reproducible_2h"
max_upload_mb = 80
parser_backend = "pymupdf"

[server]
host = "127.0.0.1"
port = {port}
reload = false

[search]
execution = "uvx"
command = "paper-search"
sources = ["arxiv", "openalex"]
max_results = 15
timeout_seconds = 30
""".strip(),
        encoding="utf-8",
    )


def test_config_service_loads_local_toml_and_preserves_mimo_auth_header(tmp_path: Path) -> None:
    config_path = tmp_path / "local.toml"
    _write_config(config_path)

    config = ConfigService(config_path=config_path, env_path=tmp_path / ".env").load()

    provider = config.active_model_provider()
    assert config.active_provider == "mimo"
    assert provider.name == "mimo"
    assert provider.auth_header == "api-key"
    assert provider.chat_completions_url() == "https://token-plan-cn.xiaomimimo.com/v1/chat/completions"
    assert config.server.port == 18765


def test_config_service_falls_back_to_example_when_local_missing(tmp_path: Path) -> None:
    example_path = tmp_path / "sensei.example.toml"
    _write_config(example_path, active_provider="deepseek", port=8765)

    config = ConfigService(
        config_path=tmp_path / "missing-local.toml",
        example_path=example_path,
        env_path=tmp_path / ".env",
    ).load()

    assert config.active_provider == "deepseek"
    assert config.server.port == 8765


def test_config_service_loads_env_without_overwriting_existing_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = tmp_path / "local.toml"
    env_path = tmp_path / ".env"
    _write_config(config_path)
    env_path.write_text("MIMO_API_KEY=from-env-file\n", encoding="utf-8")
    monkeypatch.setenv("MIMO_API_KEY", "already-set")

    ConfigService(config_path=config_path, env_path=env_path).load()

    assert os.environ["MIMO_API_KEY"] == "already-set"


def test_missing_api_key_message_is_clear_and_does_not_crash(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / "local.toml"
    _write_config(config_path)
    monkeypatch.delenv("MIMO_API_KEY", raising=False)

    config = ConfigService(config_path=config_path, env_path=tmp_path / ".env").load()

    assert config.active_model_provider().missing_api_key_message() == (
        "Missing API key. Set environment variable MIMO_API_KEY."
    )


def test_redact_secret_removes_raw_secret_value() -> None:
    message = "401 Unauthorized for key secret-token-value"

    redacted = redact_secret(message, "secret-token-value")

    assert "secret-token-value" not in redacted
    assert "[REDACTED]" in redacted
