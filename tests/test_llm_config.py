from __future__ import annotations

import httpx

import pytest

from researchsensei.core.config import (
    ConfigService,
    ModelProviderConfig,
    redact_secret,
)
from researchsensei.llm.client import LLMClient
from researchsensei.llm.types import ChatMessage, ChatResponse, LLMConfig


def test_model_provider_config_defaults() -> None:
    cfg = ModelProviderConfig(name="test")
    assert cfg.kind == "openai_compatible"
    assert cfg.auth_header == "authorization"
    assert cfg.timeout_seconds == 60


def test_model_provider_config_mimo_api_key_header() -> None:
    cfg = ModelProviderConfig(name="mimo", auth_header="api-key")
    assert cfg.auth_header == "api-key"


def test_llm_client_auth_header_none_omits_authorization() -> None:
    cfg = ModelProviderConfig(
        name="cc_switch",
        base_url="http://127.0.0.1:15721/v1",
        model="deepseek-v4-flash",
        auth_header="none",
    )

    headers = LLMClient(cfg)._headers()

    assert headers == {"content-type": "application/json"}


def test_llm_client_anthropic_provider_headers_and_payload() -> None:
    cfg = ModelProviderConfig(
        name="cc_switch",
        kind="anthropic_compatible",
        base_url="http://127.0.0.1:15721/v1",
        model="claude-sonnet-4-6",
        auth_header="none",
    )
    client = LLMClient(cfg)

    headers = client._headers()
    payload = client._anthropic_payload(
        [
            ChatMessage(role="system", content="Be concise."),
            ChatMessage(role="user", content="Say OK."),
        ],
        config=LLMConfig(max_tokens=128, temperature=0),
    )

    assert headers == {
        "content-type": "application/json",
        "anthropic-version": "2023-06-01",
    }
    assert payload["model"] == "claude-sonnet-4-6"
    assert payload["system"] == "Be concise."
    assert payload["messages"] == [{"role": "user", "content": "Say OK."}]


def test_llm_client_anthropic_payload_can_disable_thinking() -> None:
    cfg = ModelProviderConfig(
        name="cc_switch",
        kind="anthropic_compatible",
        base_url="http://127.0.0.1:15721/v1",
        model="claude-sonnet-4-6",
        auth_header="none",
    )
    client = LLMClient(cfg)

    payload = client._anthropic_payload(
        [ChatMessage(role="user", content="Return JSON.")],
        config=LLMConfig(max_tokens=512, temperature=0, disable_thinking=True),
    )

    assert payload["thinking"] == {"type": "disabled"}


def test_llm_client_openai_payload_can_disable_thinking() -> None:
    cfg = ModelProviderConfig(
        name="opencode_go",
        kind="openai_compatible",
        base_url="https://opencode.ai/zen/go/v1",
        model="deepseek-v4-flash",
    )
    client = LLMClient(cfg)

    payload = client._chat_payload(
        [ChatMessage(role="user", content="Return JSON.")],
        config=LLMConfig(max_tokens=512, temperature=0, disable_thinking=True),
    )

    assert payload["thinking"] == {"type": "disabled"}


def test_parse_anthropic_response_uses_text_blocks_only() -> None:
    response = LLMClient._parse_anthropic_response({
        "model": "deepseek-v4-pro",
        "stop_reason": "end_turn",
        "content": [
            {"type": "thinking", "thinking": "hidden reasoning"},
            {"type": "text", "text": "OK"},
        ],
        "usage": {"input_tokens": 3, "output_tokens": 2},
    })

    assert response.content == "OK"
    assert response.model == "deepseek-v4-pro"
    assert response.finish_reason == "end_turn"
    assert response.usage_total_tokens == 5


def test_parse_openai_response_accepts_content_parts() -> None:
    response = LLMClient._parse_response({
        "model": "local-switch",
        "choices": [{
            "message": {
                "content": [
                    {"type": "text", "text": '{"ok": '},
                    {"type": "text", "text": "true}"},
                ],
            },
            "finish_reason": "stop",
        }],
        "usage": {"prompt_tokens": 3, "completion_tokens": 4, "total_tokens": 7},
    })

    assert response.content == '{"ok": true}'
    assert response.finish_reason == "stop"
    assert response.usage_total_tokens == 7


def test_anthropic_parser_accepts_openai_compatible_shape_from_switch() -> None:
    response = LLMClient._parse_anthropic_response({
        "model": "local-switch",
        "choices": [{
            "message": {"content": '{"ok": true}'},
            "finish_reason": "stop",
        }],
    })

    assert response.content == '{"ok": true}'
    assert response.finish_reason == "stop"


@pytest.mark.asyncio
async def test_llm_client_retries_empty_content(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict] = []

    class FakeResponse:
        def __init__(self, payload: dict) -> None:
            self.payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return self.payload

    class FakeAsyncClient:
        def __init__(self, *, timeout: float) -> None:
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, url: str, *, headers: dict, json: dict) -> FakeResponse:
            calls.append({"url": url, "headers": headers, "json": json})
            if len(calls) == 1:
                return FakeResponse({
                    "choices": [{"message": {"content": ""}, "finish_reason": "stop"}],
                })
            return FakeResponse({
                "choices": [{"message": {"content": '{"ok": true}'}, "finish_reason": "stop"}],
            })

    monkeypatch.setattr("researchsensei.llm.client.httpx.AsyncClient", FakeAsyncClient)
    provider = ModelProviderConfig(
        name="switch",
        base_url="http://127.0.0.1:15721/v1",
        model="test-model",
        auth_header="none",
    )
    client = LLMClient(provider, config=LLMConfig(max_retries=1, retry_delay=0))

    response = await client.chat([ChatMessage(role="user", content="Return JSON.")])

    assert response.content == '{"ok": true}'
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_structured_repair_uses_a_bounded_timeout() -> None:
    configs: list[LLMConfig] = []

    class RepairCapturingClient(LLMClient):
        async def chat(self, messages, *, config=None):
            configs.append(config)
            content = "not json" if len(configs) == 1 else '{"ok": true}'
            return ChatResponse(content=content)

    provider = ModelProviderConfig(name="switch", auth_header="none")
    client = RepairCapturingClient(provider)

    result = await client.chat_json_with_repair(
        [ChatMessage(role="user", content="Return JSON.")],
        config=LLMConfig(timeout=80, max_retries=0),
    )

    assert result == {"ok": True}
    assert [config.timeout for config in configs] == [80, 25.0]
    assert configs[1].max_retries == 0


@pytest.mark.asyncio
async def test_connect_error_gets_one_fast_retry_when_request_retries_are_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "choices": [{"message": {"content": "OK"}, "finish_reason": "stop"}],
            }

    class FakeAsyncClient:
        def __init__(self, *, timeout: float) -> None:
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, url: str, *, headers: dict, json: dict) -> FakeResponse:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise httpx.ConnectError("temporary proxy connection failure")
            return FakeResponse()

    monkeypatch.setattr("researchsensei.llm.client.httpx.AsyncClient", FakeAsyncClient)
    provider = ModelProviderConfig(
        name="opencode_go",
        base_url="https://opencode.ai/zen/go/v1",
        model="deepseek-v4-flash",
        auth_header="none",
    )
    client = LLMClient(
        provider,
        config=LLMConfig(max_retries=0, connect_retries=1, retry_delay=0),
    )

    response = await client.chat([ChatMessage(role="user", content="Reply OK.")])

    assert response.content == "OK"
    assert calls == 2


def test_redact_secret_removes_key() -> None:
    result = redact_secret("Error: sk-abc123 failed", "sk-abc123")
    assert "sk-abc123" not in result
    assert "[REDACTED]" in result


def test_redact_secret_with_none_secret() -> None:
    result = redact_secret("Error occurred", None)
    assert result == "Error occurred"


def test_redact_secret_with_empty_secret() -> None:
    result = redact_secret("Error occurred", "")
    assert result == "Error occurred"


def test_config_service_loads_providers(tmp_path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    toml_content = """
active_provider = "deepseek"

[providers.deepseek]
kind = "openai_compatible"
base_url = "https://api.deepseek.com"
api_key_env = "DEEPSEEK_API_KEY"
model = "deepseek-chat"

[providers.mimo]
kind = "openai_compatible"
base_url = "https://api.mimo.com"
api_key_env = "MIMO_API_KEY"
model = "mimo-v2"
auth_header = "api-key"

[providers.opencode_go]
kind = "openai_compatible"
base_url = "https://opencode.ai/zen/go/v1"
api_key_env = "OPENCODE_GO_API_KEY"
model = "deepseek-v4-flash"
"""
    toml_path = config_dir / "test.toml"
    toml_path.write_text(toml_content, encoding="utf-8")

    env_path = tmp_path / ".env"
    env_path.write_text("", encoding="utf-8")

    service = ConfigService(config_path=toml_path, env_path=env_path)
    config = service.load()

    assert config.active_provider == "deepseek"
    assert "deepseek" in config.providers
    assert "mimo" in config.providers
    assert "opencode_go" in config.providers
    assert config.providers["mimo"].auth_header == "api-key"
    assert config.providers["mimo"].model == "mimo-v2"
    assert config.providers["opencode_go"].chat_completions_url() == "https://opencode.ai/zen/go/v1/chat/completions"


def test_config_service_default_provider_fallback() -> None:
    service = ConfigService(
        config_path="/nonexistent/path.toml",
        env_path="/nonexistent/.env",
    )
    config = service.load()
    assert config.active_provider == "cc_switch"
    assert "cc_switch" in config.providers
    assert config.providers["cc_switch"].base_url == "http://127.0.0.1:15721/v1"
