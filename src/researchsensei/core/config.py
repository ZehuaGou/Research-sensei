from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from researchsensei.core.env_loader import load_runtime_env


class ConfigModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ModelProviderConfig(ConfigModel):
    name: str
    kind: str = "openai_compatible"
    base_url: str = ""
    api_key_env: str = ""
    model: str = ""
    auth_header: str = "authorization"
    timeout_seconds: int = 60

    def chat_completions_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/chat/completions"

    def messages_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/messages"

    def missing_api_key_message(self) -> str:
        return f"Missing API key. Set environment variable {self.api_key_env}."


class AppRuntimeConfig(ConfigModel):
    workspace_dir: str = "workspace"
    default_learning_mode: str = "reproducible_2h"
    max_upload_mb: int = 80
    parser_backend: str = "pymupdf"


class ServerConfig(ConfigModel):
    host: str = "127.0.0.1"
    port: int = 8765
    reload: bool = False


class SearchConfig(ConfigModel):
    execution: str = "uvx"
    command: str = "paper-search"
    sources: list[str] = Field(default_factory=lambda: ["arxiv", "openalex"])
    max_results: int = 10
    timeout_seconds: int = 30
    min_citation_count: int = 0


class AppConfig(ConfigModel):
    active_provider: str = "cc_switch"
    providers: dict[str, ModelProviderConfig] = Field(default_factory=dict)
    app: AppRuntimeConfig = Field(default_factory=AppRuntimeConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)

    def active_model_provider(self) -> ModelProviderConfig:
        if self.active_provider not in self.providers:
            raise KeyError(f"Unknown provider: {self.active_provider}")
        return self.providers[self.active_provider]


class ConfigService:
    def __init__(
        self,
        config_path: str | Path = "config/local.toml",
        env_path: str | Path = ".env",
        example_path: str | Path = "config/sensei.example.toml",
    ) -> None:
        self.config_path = Path(config_path)
        self.env_path = Path(env_path)
        self.example_path = Path(example_path)

    def load(self) -> AppConfig:
        self._load_env()
        data = self._read_toml()
        providers = self._build_providers(data.get("providers") or {})
        active_provider = _canonical_provider_name(
            os.getenv("RESEARCHSENSEI_LLM_PROVIDER", "") or data.get("active_provider", "cc_switch"),
            providers,
        )
        model_override = os.getenv("RESEARCHSENSEI_LLM_MODEL", "").strip()
        if model_override and active_provider in providers:
            providers[active_provider] = providers[active_provider].model_copy(update={"model": model_override})
        return AppConfig(
            active_provider=active_provider,
            providers=providers,
            app=AppRuntimeConfig(**(data.get("app") or {})),
            server=ServerConfig(**(data.get("server") or {})),
            search=SearchConfig(**(data.get("search") or {})),
        )

    def _load_env(self) -> None:
        load_runtime_env(env_path=self.env_path, suppress_errors=True)

    def _read_toml(self) -> dict[str, Any]:
        path = self.config_path if self.config_path.exists() else self.example_path
        if not path.exists():
            return {}
        return tomllib.loads(path.read_text(encoding="utf-8"))

    def _build_providers(self, data: dict[str, Any]) -> dict[str, ModelProviderConfig]:
        if not data:
            data = {
                "cc_switch": {
                    "kind": "anthropic_compatible",
                    "base_url": "http://127.0.0.1:15721/v1",
                    "api_key_env": "",
                    "model": "claude-sonnet-4-6",
                    "auth_header": "none",
                    "timeout_seconds": 120,
                }
            }
        return {
            name: ModelProviderConfig(name=name, **value)
            for name, value in data.items()
        }


def _canonical_provider_name(name: str, providers: dict[str, ModelProviderConfig]) -> str:
    if name == "ccswitch" and "cc_switch" in providers:
        return "cc_switch"
    return name


def redact_secret(message: str, secret: str | None) -> str:
    if not secret:
        return message
    return message.replace(secret, "[REDACTED]")
