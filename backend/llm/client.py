from __future__ import annotations

import json
import os
from typing import AsyncIterator

import httpx
from httpx_sse import aconnect_sse

from backend.schemas import ModelProviderConfig


class LLMClient:
    def __init__(self, config: ModelProviderConfig, *, timeout: float = 120.0) -> None:
        self.base_url = config.base_url.rstrip("/")
        self.model = config.model
        self.api_key_env = config.api_key_env
        self.auth_header = config.auth_header or "authorization"
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        api_key = os.getenv(self.api_key_env, "")
        headers = {"content-type": "application/json"}
        if self.auth_header == "api-key":
            headers["api-key"] = api_key
        else:
            headers["authorization"] = f"Bearer {api_key}"
        return headers

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            response.raise_for_status()
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            if not content:
                raise RuntimeError(f"LLM returned empty content. Response: {data}")
            return content

    async def chat_json(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> dict:
        content = await self.chat(messages, temperature=temperature, max_tokens=max_tokens)
        if not content.strip():
            raise RuntimeError("LLM returned empty content for JSON parse")
        # Strip markdown code blocks if present
        content = content.strip()
        if content.startswith("```"):
            # Remove opening ```json or ```
            first_newline = content.find("\n")
            if first_newline != -1:
                content = content[first_newline + 1:]
            # Remove closing ```
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
        # Fix common JSON issues
        import re
        # Remove control characters (except newline and tab)
        content = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', content)
        # Replace literal backslashes that aren't valid JSON escapes
        content = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', content)
        # Try to find the first valid JSON object
        start = content.find('{')
        if start != -1:
            content = content[start:]
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Try to fix trailing commas and other issues
            content = re.sub(r',\s*([}\]])', r'\1', content)
            # Try to find a valid JSON object by counting braces
            depth = 0
            end = 0
            for i, c in enumerate(content):
                if c == '{':
                    depth += 1
                elif c == '}':
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            if end > 0:
                content = content[:end]
            return json.loads(content)

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with aconnect_sse(
                client,
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": True,
                },
            ) as event_source:
                async for event in event_source.aiter_sse():
                    if event.data == "[DONE]":
                        break
                    data = json.loads(event.data)
                    delta = data["choices"][0].get("delta", {})
                    if "content" in delta:
                        yield delta["content"]
