from __future__ import annotations

from pathlib import Path

import pytest
from starlette.testclient import TestClient

from researchsensei.core.config import ConfigService
from researchsensei.web.app import create_app


def test_settings_endpoint_returns_active_provider_without_secret(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / "local.toml"
    _write_config(config_path, active_provider="mimo")
    monkeypatch.setenv("RESEARCHSENSEI_ENABLE_API_LLM", "1")
    monkeypatch.setenv("MIMO_API_KEY", "secret-value")

    client = TestClient(create_app(
        workspace_root=tmp_path / "workspace",
        config_service=ConfigService(config_path=config_path, env_path=tmp_path / "missing.env"),
    ))

    response = client.get("/api/v1/settings")

    assert response.status_code == 200
    data = response.json()
    assert data["active_provider"] == "mimo"
    assert data["base_url"] == "https://api.xiaomimimo.com/v1"
    assert data["api_key_env"] == "MIMO_API_KEY"
    assert data["enable_env"] == "RESEARCHSENSEI_ENABLE_API_LLM"
    assert data["llm_enabled"] is True
    assert data["api_key_configured"] is True
    assert "secret-value" not in response.text


def test_settings_endpoint_uses_model_env_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / "local.toml"
    _write_config(config_path, active_provider="mimo")
    monkeypatch.setenv("RESEARCHSENSEI_LLM_MODEL", "custom-model")

    client = TestClient(create_app(
        workspace_root=tmp_path / "workspace",
        config_service=ConfigService(config_path=config_path, env_path=tmp_path / "missing.env"),
    ))

    response = client.get("/api/v1/settings")

    assert response.status_code == 200
    data = response.json()
    assert data["model"] == "custom-model"
    assert data["model_env"] == "RESEARCHSENSEI_LLM_MODEL"
    assert data["model_options"][0]["id"] == "custom-model"


def test_settings_patch_saves_model_override_to_env_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / "local.toml"
    env_path = tmp_path / ".env"
    _write_config(config_path, active_provider="mimo")
    monkeypatch.delenv("RESEARCHSENSEI_LLM_MODEL", raising=False)

    client = TestClient(create_app(
        workspace_root=tmp_path / "workspace",
        config_service=ConfigService(config_path=config_path, env_path=env_path),
    ))

    response = client.patch("/api/v1/settings", json={"model": "new-cici-model"})

    assert response.status_code == 200
    data = response.json()
    assert data["model"] == "new-cici-model"
    assert 'RESEARCHSENSEI_LLM_MODEL="new-cici-model"' in env_path.read_text(encoding="utf-8")


def test_settings_endpoint_presents_ccswitch_name_and_keeps_config_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / "local.toml"
    _write_config(config_path, active_provider="cc_switch")
    monkeypatch.setenv("RESEARCHSENSEI_LLM_PROVIDER", "ccswitch")
    monkeypatch.delenv("RESEARCHSENSEI_LLM_MODEL", raising=False)

    client = TestClient(create_app(
        workspace_root=tmp_path / "workspace",
        config_service=ConfigService(config_path=config_path, env_path=tmp_path / "missing.env"),
    ))

    response = client.get("/api/v1/settings")

    assert response.status_code == 200
    data = response.json()
    assert data["active_provider"] == "ccswitch"
    assert data["provider_display_name"] == "ccswitch"
    assert data["provider_key"] == "cc_switch"
    assert data["model_options"][0]["id"] == "claude-sonnet-4-6"


def test_settings_test_reports_disabled_llm(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / "local.toml"
    _write_config(config_path, active_provider="mimo")
    monkeypatch.delenv("RESEARCHSENSEI_ENABLE_API_LLM", raising=False)
    monkeypatch.setenv("MIMO_API_KEY", "secret-value")

    client = TestClient(create_app(
        workspace_root=tmp_path / "workspace",
        config_service=ConfigService(config_path=config_path, env_path=tmp_path / "missing.env"),
    ))

    response = client.post("/api/v1/settings/test")

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is False
    assert "disabled" in data["message"]


def _write_config(path: Path, *, active_provider: str) -> None:
    path.write_text(
        f"""
active_provider = "{active_provider}"

[providers.mimo]
kind = "openai_compatible"
base_url = "https://api.xiaomimimo.com/v1"
api_key_env = "MIMO_API_KEY"
model = "mimo-v2.5-pro"
auth_header = "api-key"
timeout_seconds = 60

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
