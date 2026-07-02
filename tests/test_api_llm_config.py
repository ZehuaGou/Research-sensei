from __future__ import annotations

from pathlib import Path

import pytest

from researchsensei.core.config import ConfigService
from researchsensei.web.app import _configured_llm_client


def _write_config(path: Path, *, active_provider: str = "deepseek") -> None:
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

[providers.opencode_go]
kind = "openai_compatible"
base_url = "https://opencode.ai/zen/go/v1"
api_key_env = "OPENCODE_GO_API_KEY"
model = "deepseek-v4-flash"
timeout_seconds = 120

[providers.cc_switch]
kind = "anthropic_compatible"
base_url = "http://127.0.0.1:15721/v1"
api_key_env = ""
model = "claude-sonnet-4-6"
auth_header = "none"
timeout_seconds = 120
""".strip(),
        encoding="utf-8",
    )


def _clear_api_llm_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "RESEARCHSENSEI_ENABLE_API_LLM",
        "RESEARCHSENSEI_LLM_PROVIDER",
        "MIMO_API_KEY",
        "OPENCODE_GO_API_KEY",
        "DEEPSEEK_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)


def test_env_file_enable_flag_is_loaded_before_api_llm_check(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_api_llm_env(monkeypatch)
    config_path = tmp_path / "local.toml"
    env_path = tmp_path / ".env"
    _write_config(config_path, active_provider="opencode_go")
    env_path.write_text(
        "RESEARCHSENSEI_ENABLE_API_LLM=1\n"
        "OPENCODE_GO_API_KEY=test-key\n",
        encoding="utf-8",
    )

    client = _configured_llm_client(
        enable_configured_llm=None,
        provider_name="",
        llm_config=None,
        config_service=ConfigService(config_path=config_path, env_path=env_path),
    )

    assert client is not None
    assert client.provider.name == "opencode_go"
    assert client.provider.api_key_env == "OPENCODE_GO_API_KEY"
    assert client.config.max_retries == 2
    assert client.config.retry_delay == 1.0


def test_env_file_provider_override_selects_mimo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_api_llm_env(monkeypatch)
    config_path = tmp_path / "local.toml"
    env_path = tmp_path / ".env"
    _write_config(config_path, active_provider="deepseek")
    env_path.write_text(
        "RESEARCHSENSEI_ENABLE_API_LLM=1\n"
        "RESEARCHSENSEI_LLM_PROVIDER=mimo\n"
        "MIMO_API_KEY=test-key\n",
        encoding="utf-8",
    )

    client = _configured_llm_client(
        enable_configured_llm=None,
        provider_name="",
        llm_config=None,
        config_service=ConfigService(config_path=config_path, env_path=env_path),
    )

    assert client is not None
    assert client.provider.name == "mimo"
    assert client.provider.auth_header == "api-key"


def test_anthropic_compatible_provider_gets_reasoning_budget(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_api_llm_env(monkeypatch)
    config_path = tmp_path / "local.toml"
    env_path = tmp_path / ".env"
    _write_config(config_path, active_provider="cc_switch")
    env_path.write_text("RESEARCHSENSEI_ENABLE_API_LLM=1\n", encoding="utf-8")

    client = _configured_llm_client(
        enable_configured_llm=None,
        provider_name="",
        llm_config=None,
        config_service=ConfigService(config_path=config_path, env_path=env_path),
    )

    assert client is not None
    assert client.provider.name == "cc_switch"
    assert client.config.max_tokens == 12000
    assert client.config.timeout == 300.0
    assert client.config.disable_thinking is True


def test_missing_mimo_key_fails_without_secret_value(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_api_llm_env(monkeypatch)
    config_path = tmp_path / "local.toml"
    env_path = tmp_path / ".env"
    _write_config(config_path, active_provider="deepseek")
    env_path.write_text(
        "RESEARCHSENSEI_ENABLE_API_LLM=1\n"
        "RESEARCHSENSEI_LLM_PROVIDER=mimo\n",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError) as excinfo:
        _configured_llm_client(
            enable_configured_llm=None,
            provider_name="",
            llm_config=None,
            config_service=ConfigService(config_path=config_path, env_path=env_path),
        )

    message = str(excinfo.value)
    assert message == "Missing API key. Set environment variable MIMO_API_KEY."
    assert "test-key" not in message


def test_api_llm_not_enabled_still_returns_none(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_api_llm_env(monkeypatch)
    config_path = tmp_path / "local.toml"
    env_path = tmp_path / ".env"
    _write_config(config_path, active_provider="mimo")
    env_path.write_text(
        "RESEARCHSENSEI_LLM_PROVIDER=mimo\n"
        "MIMO_API_KEY=test-key\n",
        encoding="utf-8",
    )

    client = _configured_llm_client(
        enable_configured_llm=None,
        provider_name="",
        llm_config=None,
        config_service=ConfigService(config_path=config_path, env_path=env_path),
    )

    assert client is None
