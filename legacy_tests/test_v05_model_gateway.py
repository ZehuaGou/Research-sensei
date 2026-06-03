from __future__ import annotations

from backend.config import ConfigService, ModelGateway


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"choices": [{"message": {"content": '{"ok": true}'}}]}


class FakeClient:
    def __init__(self):
        self.calls = []

    def post(self, url, headers, json):
        self.calls.append({"url": url, "headers": headers, "json": json})
        return FakeResponse()


class UnauthorizedClient:
    def post(self, url, headers, json):
        raise RuntimeError("401 Unauthorized for url https://api.xiaomimimo.com/v1/chat/completions with key sk-secret")


def write_config(tmp_path, active_provider="mimo"):
    config_path = tmp_path / "local.toml"
    config_path.write_text(
        """
active_provider = "{active_provider}"
[providers.mimo]
kind = "openai_compatible"
base_url = "https://api.xiaomimimo.com/v1"
api_key_env = "MIMO_API_KEY"
model = "mimo-v2.5-pro"
auth_header = "api-key"
[providers.deepseek]
kind = "openai_compatible"
base_url = "https://api.deepseek.com"
api_key_env = "DEEPSEEK_API_KEY"
model = "deepseek-chat"
""".replace("{active_provider}", active_provider).strip(),
        encoding="utf-8",
    )
    return config_path


def test_model_gateway_calls_openai_compatible_endpoint_with_configured_auth_header(tmp_path, monkeypatch):
    monkeypatch.setenv("MIMO_API_KEY", "sk-secret")
    config = ConfigService(write_config(tmp_path), env_path=tmp_path / ".env.missing").load()
    client = FakeClient()

    ok, message = ModelGateway(config, client=client).test_connection()

    assert ok is True
    assert "Connection OK" in message
    call = client.calls[0]
    assert call["url"] == "https://api.xiaomimimo.com/v1/chat/completions"
    assert call["headers"]["api-key"] == "sk-secret"
    assert "authorization" not in call["headers"]
    assert call["json"]["model"] == "mimo-v2.5-pro"


def test_model_gateway_redacts_key_in_unauthorized_error(tmp_path, monkeypatch):
    monkeypatch.setenv("MIMO_API_KEY", "sk-secret")
    config = ConfigService(write_config(tmp_path), env_path=tmp_path / ".env.missing").load()

    ok, message = ModelGateway(config, client=UnauthorizedClient()).test_connection()

    assert ok is False
    assert "401" in message
    assert "MiMo" in message
    assert "sk-secret" not in message
