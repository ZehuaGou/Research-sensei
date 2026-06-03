from __future__ import annotations

import os
import json
import tomllib
from pathlib import Path

import httpx
from dotenv import dotenv_values

from backend.schemas import AppConfig, AppRuntimeConfig, ModelProviderConfig, SearchConfig, ServerConfig


class ConfigService:
    def __init__(self, config_path: str | Path = "config/local.toml", env_path: str | Path = ".env") -> None:
        self.config_path = Path(config_path)
        self.env_path = Path(env_path)

    def load(self) -> AppConfig:
        if self.env_path.exists():
            for key, value in dotenv_values(self.env_path).items():
                if value is not None and key not in os.environ:
                    os.environ[key] = value
        data = self._read_toml()
        providers = {
            name: ModelProviderConfig(name=name, **value)
            for name, value in (data.get("providers") or {}).items()
        }
        if not providers:
            providers["deepseek"] = ModelProviderConfig(
                name="deepseek",
                base_url="https://api.deepseek.com",
                api_key_env="DEEPSEEK_API_KEY",
                model="deepseek-chat",
            )
        return AppConfig(
            active_provider=data.get("active_provider", "deepseek"),
            providers=providers,
            app=AppRuntimeConfig(**(data.get("app") or {})),
            server=ServerConfig(**(data.get("server") or {})),
            search=SearchConfig(**(data.get("search") or {})),
        )

    def _read_toml(self) -> dict:
        path = self.config_path
        if not path.exists():
            fallback = Path("config/sensei.example.toml")
            path = fallback if fallback.exists() else path
        if not path.exists():
            return {}
        return tomllib.loads(path.read_text(encoding="utf-8"))


class ModelGateway:
    def __init__(self, config: AppConfig, client: object | None = None) -> None:
        self.config = config
        self.client = client

    def test_connection(self) -> tuple[bool, str]:
        provider = self.config.active_model_provider()
        api_key = os.getenv(provider.api_key_env)
        if not api_key:
            return False, f"Missing API key. Set environment variable {provider.api_key_env}."
        try:
            self.chat_json([{"role": "user", "content": 'Return exactly this JSON: {"ok": true}'}])
        except Exception as error:
            return False, self._friendly_error(provider.name, self._redact(str(error), api_key))
        return True, "Connection OK."

    def chat_json(self, messages: list[dict[str, str]], temperature: float = 0.2) -> dict:
        provider = self.config.active_model_provider()
        api_key = os.getenv(provider.api_key_env)
        if not api_key:
            raise RuntimeError(f"Missing API key. Set environment variable {provider.api_key_env}.")
        headers = {"content-type": "application/json"}
        if provider.auth_header == "api-key":
            headers["api-key"] = api_key
        else:
            headers["authorization"] = f"Bearer {api_key}"
        client = self.client or httpx.Client(timeout=provider.timeout_seconds)
        response = client.post(
            provider.chat_completions_url(),
            headers=headers,
            json={
                "model": provider.model,
                "messages": messages,
                "temperature": temperature,
                "response_format": {"type": "json_object"},
            },
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return json.loads(content)

    def _friendly_error(self, provider_name: str, message: str) -> str:
        if provider_name == "mimo" and "401" in message:
            return (
                f"{message}\n\n"
                "MiMo 401 usually means authentication was rejected. Check that MIMO_API_KEY is active, "
                "that token-plan and pay-as-you-go keys are not mixed, and that config/local.toml uses the exact "
                "Base URL shown on the MiMo subscription/API page."
            )
        return message

    def _redact(self, message: str, api_key: str) -> str:
        return message.replace(api_key, "[REDACTED]")
