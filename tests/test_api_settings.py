from __future__ import annotations

from pathlib import Path

import pytest
from starlette.testclient import TestClient

from researchsensei.core.config import ConfigService
from researchsensei.web.app import create_app
from researchsensei.web.app_factory import _openai_compatible_live_models


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


def test_settings_selects_paper_vision_and_tutor_models_independently(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "local.toml"
    env_path = tmp_path / ".env"
    _write_config(config_path, active_provider="opencode_go")
    with config_path.open("a", encoding="utf-8") as handle:
        handle.write(
            '\n\n[opencode]\nenabled = true\nmodel = "qwen3.7-plus"\n'
            'tutor_model = "mimo-v2.5"\n'
        )
    monkeypatch.delenv("RESEARCHSENSEI_OPENCODE_MODEL", raising=False)
    monkeypatch.delenv("RESEARCHSENSEI_OPENCODE_TUTOR_MODEL", raising=False)

    client = TestClient(create_app(
        workspace_root=tmp_path / "workspace",
        config_service=ConfigService(config_path=config_path, env_path=env_path),
    ))

    initial = client.get("/api/v1/settings").json()
    assert initial["paper_agent_model"] == "qwen3.7-plus"
    assert initial["paper_tutor_model"] == "mimo-v2.5"

    response = client.patch(
        "/api/v1/settings",
        json={"paper_model": "mimo-v2.5", "tutor_model": "qwen3.7-plus"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["paper_agent_model"] == "mimo-v2.5"
    assert data["paper_tutor_model"] == "qwen3.7-plus"
    env_text = env_path.read_text(encoding="utf-8")
    assert 'RESEARCHSENSEI_OPENCODE_MODEL="mimo-v2.5"' in env_text
    assert 'RESEARCHSENSEI_OPENCODE_TUTOR_MODEL="qwen3.7-plus"' in env_text


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


def test_settings_endpoint_lists_live_opencode_go_models(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / "local.toml"
    _write_config(config_path, active_provider="opencode_go")
    monkeypatch.setenv("OPENCODE_GO_API_KEY", "secret-value")
    monkeypatch.setenv("RESEARCHSENSEI_LLM_MODEL", "deepseek-v4-flash")
    monkeypatch.setattr(
        "researchsensei.web.app_factory._opencode_go_live_models",
        lambda provider: [
            {"id": "deepseek-v4-pro", "label": "DeepSeek V4 Pro"},
            {"id": "kimi-k3", "label": "Kimi K3"},
        ],
    )

    client = TestClient(create_app(
        workspace_root=tmp_path / "workspace",
        config_service=ConfigService(config_path=config_path, env_path=tmp_path / "missing.env"),
    ))

    response = client.get("/api/v1/settings")

    assert response.status_code == 200
    data = response.json()
    assert data["active_provider"] == "opencode_go"
    assert [item["id"] for item in data["model_options"][:3]] == [
        "deepseek-v4-flash",
        "deepseek-v4-pro",
        "kimi-k3",
    ]
    assert data["model_options"][1]["source"] == "OpenCode Go 接口"
    assert "secret-value" not in response.text


def test_live_model_catalog_uses_bearer_key_without_returning_it(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"data": [{"id": "deepseek-v4-pro"}]}

    class FakeClient:
        def __init__(self, *, timeout: float) -> None:
            captured["timeout"] = timeout

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def get(self, url: str, *, headers: dict[str, str]) -> FakeResponse:
            captured["url"] = url
            captured["headers"] = headers
            return FakeResponse()

    monkeypatch.setattr("researchsensei.web.app_factory.httpx.Client", FakeClient)

    models = _openai_compatible_live_models(
        "https://models.example/v1",
        api_key="secret-value",
    )

    assert models == [{"id": "deepseek-v4-pro", "label": "deepseek-v4-pro"}]
    assert captured["url"] == "https://models.example/v1/models"
    assert captured["headers"] == {"authorization": "Bearer secret-value"}
    assert "secret-value" not in repr(models)


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
