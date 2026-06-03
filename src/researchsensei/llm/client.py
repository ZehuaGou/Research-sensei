from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from typing import AsyncIterator

import httpx
from httpx_sse import aconnect_sse

from researchsensei.core.config import ModelProviderConfig, redact_secret
from researchsensei.llm.types import ChatMessage, ChatResponse, LLMConfig

logger = logging.getLogger(__name__)


class LLMClientError(Exception):
    """Base exception for LLM client errors."""


class LLMTimeoutError(LLMClientError):
    """Raised when an LLM request times out."""


class LLMResponseError(LLMClientError):
    """Raised when the LLM returns an invalid or empty response."""


class LLMClient:
    """Lightweight OpenAI-compatible LLM client using httpx."""

    def __init__(
        self,
        provider: ModelProviderConfig,
        *,
        config: LLMConfig | None = None,
    ) -> None:
        self.provider = provider
        self.config = config or LLMConfig()

    def _headers(self) -> dict[str, str]:
        api_key = os.getenv(self.provider.api_key_env, "")
        headers: dict[str, str] = {"content-type": "application/json"}
        if self.provider.auth_header == "api-key":
            headers["api-key"] = api_key
        else:
            headers["authorization"] = f"Bearer {api_key}"
        return headers

    def _api_key(self) -> str:
        return os.getenv(self.provider.api_key_env, "")

    def _redact(self, message: str) -> str:
        return redact_secret(message, self._api_key())

    def _chat_payload(
        self,
        messages: list[ChatMessage],
        *,
        stream: bool = False,
        config: LLMConfig | None = None,
    ) -> dict:
        cfg = config or self.config
        payload: dict = {
            "model": self.provider.model,
            "messages": [m.model_dump() for m in messages],
            "temperature": cfg.temperature,
            "max_tokens": cfg.max_tokens,
        }
        if cfg.json_mode:
            payload["response_format"] = {"type": "json_object"}
        if stream:
            payload["stream"] = True
        return payload

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        config: LLMConfig | None = None,
    ) -> ChatResponse:
        cfg = config or self.config
        url = self.provider.chat_completions_url()
        payload = self._chat_payload(messages, config=cfg)

        for attempt in range(cfg.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=cfg.timeout) as client:
                    response = await client.post(
                        url, headers=self._headers(), json=payload
                    )
                    response.raise_for_status()
                    data = response.json()
                    return self._parse_response(data)
            except httpx.TimeoutException as exc:
                if attempt < cfg.max_retries:
                    delay = cfg.retry_delay * (2**attempt)
                    logger.warning(
                        "LLM request timed out (attempt %d/%d), retrying in %.1fs",
                        attempt + 1,
                        cfg.max_retries + 1,
                        delay,
                    )
                    await asyncio.sleep(delay)
                    continue
                raise LLMTimeoutError(
                    f"LLM request timed out after {cfg.max_retries + 1} attempts: "
                    f"{self._redact(str(exc))}"
                ) from exc
            except httpx.HTTPStatusError as exc:
                raise LLMResponseError(
                    f"LLM HTTP error {exc.response.status_code}: "
                    f"{self._redact(str(exc))}"
                ) from exc
            except Exception as exc:
                if attempt < cfg.max_retries:
                    delay = cfg.retry_delay * (2**attempt)
                    logger.warning(
                        "LLM request failed (attempt %d/%d), retrying in %.1fs: %s",
                        attempt + 1,
                        cfg.max_retries + 1,
                        delay,
                        self._redact(str(exc)),
                    )
                    await asyncio.sleep(delay)
                    continue
                raise LLMResponseError(
                    f"LLM request failed: {self._redact(str(exc))}"
                ) from exc

        raise LLMResponseError("LLM request failed after all retries")

    async def chat_json(
        self,
        messages: list[ChatMessage],
        *,
        config: LLMConfig | None = None,
    ) -> dict:
        cfg = config or self.config.model_copy(update={"json_mode": True, "temperature": 0.2})
        response = await self.chat(messages, config=cfg)
        return parse_llm_json(response.content)

    async def chat_stream(
        self,
        messages: list[ChatMessage],
        *,
        config: LLMConfig | None = None,
    ) -> AsyncIterator[str]:
        cfg = config or self.config
        url = self.provider.chat_completions_url()
        payload = self._chat_payload(messages, stream=True)

        try:
            async with httpx.AsyncClient(timeout=cfg.timeout) as client:
                async with aconnect_sse(
                    client, "POST", url, headers=self._headers(), json=payload
                ) as event_source:
                    async for event in event_source.aiter_sse():
                        if event.data == "[DONE]":
                            break
                        data = json.loads(event.data)
                        delta = data.get("choices", [{}])[0].get("delta", {})
                        if "content" in delta:
                            yield delta["content"]
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(
                f"LLM stream timed out: {self._redact(str(exc))}"
            ) from exc
        except Exception as exc:
            raise LLMResponseError(
                f"LLM stream failed: {self._redact(str(exc))}"
            ) from exc

    @staticmethod
    def _parse_response(data: dict) -> ChatResponse:
        choices = data.get("choices", [])
        if not choices:
            raise LLMResponseError("LLM returned no choices")
        message = choices[0].get("message", {})
        content = message.get("content", "")
        if not content:
            raise LLMResponseError("LLM returned empty content")
        usage = data.get("usage", {})
        return ChatResponse(
            content=content,
            model=data.get("model", ""),
            finish_reason=choices[0].get("finish_reason", ""),
            usage_prompt_tokens=usage.get("prompt_tokens", 0),
            usage_completion_tokens=usage.get("completion_tokens", 0),
            usage_total_tokens=usage.get("total_tokens", 0),
        )


def parse_llm_json(content: str) -> dict:
    """Parse JSON from LLM output, handling markdown fences and common issues."""
    text = content.strip()
    if not text:
        raise LLMResponseError("LLM returned empty content for JSON parse")

    # Strip markdown code fences
    if text.startswith("```"):
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1 :]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    # Remove control characters except newline and tab
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)

    # Try to find the first valid JSON object
    start = text.find("{")
    if start != -1:
        text = text[start:]

    # First attempt
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Fix trailing commas
    fixed = re.sub(r",\s*([}\]])", r"\1", text)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # Try to find balanced braces
    depth = 0
    end = 0
    for i, c in enumerate(text):
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end > 0:
        try:
            return json.loads(text[:end])
        except json.JSONDecodeError:
            pass

    raise LLMResponseError(f"Failed to parse JSON from LLM output: {text[:200]}...")


class MockLLMClient:
    """Mock LLM client for testing. Returns configurable responses."""

    def __init__(
        self,
        *,
        response: str = '{"ok": true}',
        responses: list[str] | None = None,
        delay: float = 0.0,
    ) -> None:
        self._response = response
        self._responses = responses or []
        self._call_count = 0
        self._delay = delay
        self.calls: list[list[ChatMessage]] = []

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        config: LLMConfig | None = None,
    ) -> ChatResponse:
        self.calls.append(messages)
        if self._delay > 0:
            await asyncio.sleep(self._delay)
        content = self._next_response()
        return ChatResponse(
            content=content,
            model="mock-model",
            finish_reason="stop",
            usage_prompt_tokens=100,
            usage_completion_tokens=50,
            usage_total_tokens=150,
        )

    async def chat_json(
        self,
        messages: list[ChatMessage],
        *,
        config: LLMConfig | None = None,
    ) -> dict:
        response = await self.chat(messages, config=config)
        return parse_llm_json(response.content)

    async def chat_stream(
        self,
        messages: list[ChatMessage],
        *,
        config: LLMConfig | None = None,
    ) -> AsyncIterator[str]:
        self.calls.append(messages)
        content = self._next_response()
        # Simulate streaming by yielding chunks
        chunk_size = 10
        for i in range(0, len(content), chunk_size):
            yield content[i : i + chunk_size]

    def _next_response(self) -> str:
        if self._responses:
            idx = self._call_count % len(self._responses)
            self._call_count += 1
            return self._responses[idx]
        self._call_count += 1
        return self._response
