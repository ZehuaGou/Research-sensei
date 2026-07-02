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
    """Lightweight OpenAI/Anthropic-compatible LLM client using httpx."""

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
        if self.provider.kind == "anthropic_compatible":
            headers["anthropic-version"] = "2023-06-01"
        if self.provider.auth_header == "none":
            return headers
        if self.provider.auth_header == "api-key":
            headers["api-key"] = api_key
        elif self.provider.auth_header == "x-api-key":
            headers["x-api-key"] = api_key
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
        if self.provider.kind == "anthropic_compatible":
            return await self._chat_anthropic(messages, config=cfg)

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

    async def _chat_anthropic(
        self,
        messages: list[ChatMessage],
        *,
        config: LLMConfig,
    ) -> ChatResponse:
        url = self.provider.messages_url()
        payload = self._anthropic_payload(messages, config=config)

        for attempt in range(config.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=config.timeout) as client:
                    response = await client.post(
                        url, headers=self._headers(), json=payload
                    )
                    response.raise_for_status()
                    data = response.json()
                    return self._parse_anthropic_response(data)
            except httpx.TimeoutException as exc:
                if attempt < config.max_retries:
                    delay = config.retry_delay * (2**attempt)
                    logger.warning(
                        "LLM request timed out (attempt %d/%d), retrying in %.1fs",
                        attempt + 1,
                        config.max_retries + 1,
                        delay,
                    )
                    await asyncio.sleep(delay)
                    continue
                raise LLMTimeoutError(
                    f"LLM request timed out after {config.max_retries + 1} attempts: "
                    f"{self._redact(str(exc))}"
                ) from exc
            except httpx.HTTPStatusError as exc:
                raise LLMResponseError(
                    f"LLM HTTP error {exc.response.status_code}: "
                    f"{self._redact(str(exc))}"
                ) from exc
            except Exception as exc:
                if attempt < config.max_retries:
                    delay = config.retry_delay * (2**attempt)
                    logger.warning(
                        "LLM request failed (attempt %d/%d), retrying in %.1fs: %s",
                        attempt + 1,
                        config.max_retries + 1,
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
        if self.provider.kind == "anthropic_compatible":
            raise LLMResponseError("Streaming is not implemented for anthropic_compatible providers")
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
        finish_reason = choices[0].get("finish_reason", "")
        content = LLMClient._content_to_text(message.get("content")).strip()
        if not content:
            content = LLMClient._content_to_text(message.get("text")).strip()
        if not content:
            content = LLMClient._content_to_text(choices[0].get("text")).strip()
        if not content:
            content = LLMClient._content_to_text(data.get("output_text")).strip()
        if not content:
            suffix = f" (finish_reason={finish_reason})" if finish_reason else ""
            raise LLMResponseError(f"LLM returned empty content{suffix}")
        usage = data.get("usage", {})
        return ChatResponse(
            content=content,
            model=data.get("model", ""),
            finish_reason=finish_reason,
            usage_prompt_tokens=usage.get("prompt_tokens", 0),
            usage_completion_tokens=usage.get("completion_tokens", 0),
            usage_total_tokens=usage.get("total_tokens", 0),
        )

    @staticmethod
    def _content_to_text(value: object) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            parts = [LLMClient._content_to_text(item) for item in value]
            return "".join(part for part in parts if part)
        if isinstance(value, dict):
            for key in ("text", "content", "output_text"):
                text = LLMClient._content_to_text(value.get(key))
                if text:
                    return text
        return ""

    def _anthropic_payload(
        self,
        messages: list[ChatMessage],
        *,
        config: LLMConfig,
    ) -> dict:
        user_messages: list[dict[str, str]] = []
        system_parts: list[str] = []
        for message in messages:
            if message.role == "system":
                system_parts.append(message.content)
                continue
            role = "assistant" if message.role == "assistant" else "user"
            user_messages.append({"role": role, "content": message.content})
        payload: dict = {
            "model": self.provider.model,
            "messages": user_messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
        }
        if config.disable_thinking:
            payload["thinking"] = {"type": "disabled"}
        if system_parts:
            payload["system"] = "\n\n".join(system_parts)
        return payload

    @staticmethod
    def _parse_anthropic_response(data: dict) -> ChatResponse:
        if "choices" in data and not data.get("content"):
            return LLMClient._parse_response(data)
        content_blocks = data.get("content") or []
        content = LLMClient._content_to_text([
            block
            for block in content_blocks
            if isinstance(block, str)
            or (isinstance(block, dict) and block.get("type") in {None, "text", "output_text"})
        ]).strip()
        if not content:
            stop_reason = str(data.get("stop_reason") or "")
            block_types = [
                str(block.get("type"))
                for block in content_blocks
                if isinstance(block, dict) and block.get("type")
            ]
            suffix_parts: list[str] = []
            if stop_reason:
                suffix_parts.append(f"stop_reason={stop_reason}")
            if block_types:
                suffix_parts.append(f"content_block_types={','.join(block_types[:5])}")
            suffix = f" ({'; '.join(suffix_parts)})" if suffix_parts else ""
            raise LLMResponseError(f"LLM returned empty content{suffix}")
        usage = data.get("usage", {})
        prompt_tokens = usage.get("input_tokens", 0)
        completion_tokens = usage.get("output_tokens", 0)
        return ChatResponse(
            content=content,
            model=data.get("model", ""),
            finish_reason=data.get("stop_reason", ""),
            usage_prompt_tokens=prompt_tokens,
            usage_completion_tokens=completion_tokens,
            usage_total_tokens=prompt_tokens + completion_tokens,
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
