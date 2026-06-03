from __future__ import annotations

import json

import pytest

from researchsensei.core.config import ModelProviderConfig
from researchsensei.llm.client import (
    LLMClient,
    LLMResponseError,
    LLMTimeoutError,
    MockLLMClient,
    parse_llm_json,
)
from researchsensei.llm.types import ChatMessage, ChatResponse, LLMConfig


# ---------------------------------------------------------------------------
# Provider config and auth tests
# ---------------------------------------------------------------------------


def test_provider_config_builds_chat_completions_url() -> None:
    provider = ModelProviderConfig(
        name="test",
        base_url="https://api.example.com",
        model="test-model",
        api_key_env="TEST_API_KEY",
    )
    assert provider.chat_completions_url() == "https://api.example.com/chat/completions"


def test_provider_config_strips_trailing_slash() -> None:
    provider = ModelProviderConfig(
        name="test",
        base_url="https://api.example.com/",
        model="test-model",
    )
    assert provider.chat_completions_url() == "https://api.example.com/chat/completions"


def test_llm_client_uses_bearer_auth_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_KEY", "sk-test-123")
    provider = ModelProviderConfig(
        name="test", base_url="https://api.example.com", model="m", api_key_env="TEST_KEY"
    )
    client = LLMClient(provider)
    headers = client._headers()
    assert headers["authorization"] == "Bearer sk-test-123"


def test_llm_client_uses_api_key_header_for_mimo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MIMO_KEY", "mimo-secret")
    provider = ModelProviderConfig(
        name="mimo", base_url="https://api.mimo.com", model="m", api_key_env="MIMO_KEY", auth_header="api-key"
    )
    client = LLMClient(provider)
    headers = client._headers()
    assert headers["api-key"] == "mimo-secret"
    assert "authorization" not in headers


def test_llm_client_redacts_api_key_in_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRET_KEY", "sk-super-secret-value")
    provider = ModelProviderConfig(
        name="test", base_url="https://api.example.com", model="m", api_key_env="SECRET_KEY"
    )
    client = LLMClient(provider)
    redacted = client._redact("Error with sk-super-secret-value in message")
    assert "sk-super-secret-value" not in redacted
    assert "[REDACTED]" in redacted


# ---------------------------------------------------------------------------
# LLMConfig tests
# ---------------------------------------------------------------------------


def test_llm_config_defaults() -> None:
    cfg = LLMConfig()
    assert cfg.temperature == 0.7
    assert cfg.max_tokens == 4096
    assert cfg.json_mode is False
    assert cfg.stream is False
    assert cfg.timeout == 120.0
    assert cfg.max_retries == 3
    assert cfg.retry_delay == 1.0


def test_llm_config_rejects_invalid_temperature() -> None:
    with pytest.raises(Exception):
        LLMConfig(temperature=3.0)


def test_llm_config_rejects_invalid_max_tokens() -> None:
    with pytest.raises(Exception):
        LLMConfig(max_tokens=0)


# ---------------------------------------------------------------------------
# Mock LLM client tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mock_client_returns_configured_response() -> None:
    mock = MockLLMClient(response='{"result": "ok"}')
    response = await mock.chat([ChatMessage(role="user", content="hello")])
    assert response.content == '{"result": "ok"}'
    assert response.model == "mock-model"
    assert response.finish_reason == "stop"


@pytest.mark.asyncio
async def test_mock_client_tracks_calls() -> None:
    mock = MockLLMClient(response="hi")
    await mock.chat([ChatMessage(role="user", content="first")])
    await mock.chat([ChatMessage(role="user", content="second")])
    assert len(mock.calls) == 2
    assert mock.calls[0][0].content == "first"
    assert mock.calls[1][0].content == "second"


@pytest.mark.asyncio
async def test_mock_client_cycles_through_responses() -> None:
    mock = MockLLMClient(responses=["a", "b", "c"])
    r1 = await mock.chat([ChatMessage(role="user", content="1")])
    r2 = await mock.chat([ChatMessage(role="user", content="2")])
    r3 = await mock.chat([ChatMessage(role="user", content="3")])
    r4 = await mock.chat([ChatMessage(role="user", content="4")])
    assert r1.content == "a"
    assert r2.content == "b"
    assert r3.content == "c"
    assert r4.content == "a"  # cycles


@pytest.mark.asyncio
async def test_mock_client_chat_json_parses_response() -> None:
    mock = MockLLMClient(response='{"key": "value"}')
    result = await mock.chat_json([ChatMessage(role="user", content="test")])
    assert result == {"key": "value"}


@pytest.mark.asyncio
async def test_mock_client_stream_yields_chunks() -> None:
    mock = MockLLMClient(response="hello world this is streaming")
    chunks = []
    async for chunk in mock.chat_stream([ChatMessage(role="user", content="test")]):
        chunks.append(chunk)
    full = "".join(chunks)
    assert full == "hello world this is streaming"
    assert len(chunks) > 1  # should be chunked


# ---------------------------------------------------------------------------
# JSON parsing tests
# ---------------------------------------------------------------------------


def test_parse_llm_json_handles_plain_json() -> None:
    result = parse_llm_json('{"key": "value"}')
    assert result == {"key": "value"}


def test_parse_llm_json_strips_markdown_fences() -> None:
    result = parse_llm_json('```json\n{"key": "value"}\n```')
    assert result == {"key": "value"}


def test_parse_llm_json_strips_plain_fences() -> None:
    result = parse_llm_json('```\n{"key": "value"}\n```')
    assert result == {"key": "value"}


def test_parse_llm_json_finds_json_in_text() -> None:
    result = parse_llm_json('Here is the result: {"key": "value"} done.')
    assert result == {"key": "value"}


def test_parse_llm_json_fixes_trailing_commas() -> None:
    result = parse_llm_json('{"key": "value", "list": [1, 2, 3,],}')
    assert result == {"key": "value", "list": [1, 2, 3]}


def test_parse_llm_json_removes_control_characters() -> None:
    result = parse_llm_json('{\x00"key":\x01 "value"}')
    assert result == {"key": "value"}


def test_parse_llm_json_raises_on_empty_input() -> None:
    with pytest.raises(LLMResponseError, match="empty"):
        parse_llm_json("")


def test_parse_llm_json_raises_on_invalid_json() -> None:
    with pytest.raises(LLMResponseError, match="Failed to parse"):
        parse_llm_json("this is not json at all")


# ---------------------------------------------------------------------------
# ChatResponse parsing tests
# ---------------------------------------------------------------------------


def test_parse_response_extracts_content_and_usage() -> None:
    data = {
        "model": "deepseek-chat",
        "choices": [
            {"message": {"content": "Hello!"}, "finish_reason": "stop"}
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }
    resp = LLMClient._parse_response(data)
    assert resp.content == "Hello!"
    assert resp.model == "deepseek-chat"
    assert resp.finish_reason == "stop"
    assert resp.usage_prompt_tokens == 10
    assert resp.usage_completion_tokens == 5
    assert resp.usage_total_tokens == 15


def test_parse_response_raises_on_no_choices() -> None:
    with pytest.raises(LLMResponseError, match="no choices"):
        LLMClient._parse_response({"choices": []})


def test_parse_response_raises_on_empty_content() -> None:
    with pytest.raises(LLMResponseError, match="empty content"):
        LLMClient._parse_response(
            {"choices": [{"message": {"content": ""}, "finish_reason": "stop"}]}
        )


# ---------------------------------------------------------------------------
# Config integration tests
# ---------------------------------------------------------------------------


def test_llm_config_from_model_copy() -> None:
    base = LLMConfig(temperature=0.7, max_tokens=4096)
    modified = base.model_copy(update={"temperature": 0.2, "json_mode": True})
    assert modified.temperature == 0.2
    assert modified.json_mode is True
    assert modified.max_tokens == 4096
