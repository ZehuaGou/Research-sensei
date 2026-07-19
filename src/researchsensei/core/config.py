from __future__ import annotations

import os
import shlex
try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised by the Python 3.10 CI lane
    import tomli as tomllib
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from researchsensei.core.env_loader import load_runtime_env


DEFAULT_PAPER_SEARCH_SOURCES = ("openalex", "semantic", "crossref", "dblp", "arxiv", "core")
DEFAULT_SEARCH_MAX_RESULTS = 80
DEFAULT_SEARCH_TIMEOUT_SECONDS = 90


class ConfigModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ModelProviderConfig(ConfigModel):
    name: str
    kind: str = "openai_compatible"
    base_url: str = ""
    api_key_env: str = ""
    model: str = ""
    auth_header: str = "authorization"
    timeout_seconds: int = Field(default=60, gt=0, le=600)

    def chat_completions_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/chat/completions"

    def messages_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/messages"

    def missing_api_key_message(self) -> str:
        return f"Missing API key. Set environment variable {self.api_key_env}."


class AppRuntimeConfig(ConfigModel):
    workspace_dir: str = "workspace"
    default_learning_mode: str = "reproducible_2h"
    max_upload_mb: int = Field(default=80, gt=0, le=1024)
    parser_backend: Literal["pymupdf", "lightweight"] = "pymupdf"

    @field_validator("parser_backend", mode="before")
    @classmethod
    def migrate_legacy_parser_backend(cls, value: object) -> object:
        # Older local configs advertised Docling although the web ingestion
        # path never instantiated it. Migrate that ineffective value to the
        # maintained PyMuPDF-backed lightweight parser.
        if str(value or "").strip().lower() == "docling":
            return "pymupdf"
        return value

    @field_validator("workspace_dir")
    @classmethod
    def workspace_must_not_be_empty(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("workspace_dir must not be empty")
        return cleaned


class ServerConfig(ConfigModel):
    host: str = "127.0.0.1"
    port: int = Field(default=8765, ge=1, le=65535)
    reload: bool = False


class SearchConfig(ConfigModel):
    execution: Literal["auto", "direct", "uvx"] = "auto"
    command: str = "paper-search"
    sources: list[str] = Field(
        default_factory=lambda: list(DEFAULT_PAPER_SEARCH_SOURCES)
    )
    max_results: int = Field(default=DEFAULT_SEARCH_MAX_RESULTS, ge=1, le=500)
    timeout_seconds: int = Field(default=DEFAULT_SEARCH_TIMEOUT_SECONDS, gt=0, le=600)
    min_citation_count: int = Field(default=0, ge=0)
    # 0 means no arbitrary count cap: every candidate that passes the strict
    # relevance gate is attempted. Positive values are explicit user safety
    # caps and preserve relevance order.
    max_download_candidates: int = Field(default=0, ge=0, le=500)
    browser_download_enabled: bool = False
    browser_session_state: str = ""
    browser_headless: bool = True

    @field_validator("command")
    @classmethod
    def command_must_not_be_empty(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("paper-search command must not be empty")
        return cleaned

    @field_validator("sources")
    @classmethod
    def validate_sources(cls, values: list[str]) -> list[str]:
        allowed = {
            "arxiv",
            "base",
            "biorxiv",
            "citeseerx",
            "core",
            "crossref",
            "dblp",
            "doaj",
            "europepmc",
            "google_scholar",
            "hal",
            "iacr",
            "medrxiv",
            "openaire",
            "openalex",
            "pmc",
            "pubmed",
            "semantic",
            "ssrn",
            "unpaywall",
            "zenodo",
        }
        normalized: list[str] = []
        for raw in values:
            value = str(raw).strip().lower()
            if not value:
                continue
            if value not in allowed:
                raise ValueError(f"unsupported paper-search source: {value}")
            if value not in normalized:
                normalized.append(value)
        if not normalized:
            raise ValueError("at least one paper-search source is required")
        return normalized

    def command_args(self) -> list[str] | None:
        if self.execution == "auto":
            return None
        command = shlex.split(self.command, posix=False)
        if self.execution == "uvx":
            return ["uvx", "--from", "paper-search-mcp", *command]
        return command


class AppConfig(ConfigModel):
    active_provider: str = "cc_switch"
    providers: dict[str, ModelProviderConfig] = Field(default_factory=dict)
    app: AppRuntimeConfig = Field(default_factory=AppRuntimeConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)

    @model_validator(mode="after")
    def active_provider_must_exist(self) -> "AppConfig":
        if self.active_provider not in self.providers:
            raise ValueError(f"Unknown provider: {self.active_provider}")
        return self

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
        data = _apply_environment_overrides(data)
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
        """Merge example defaults with machine-local overrides.

        Runtime precedence is environment > local TOML > example TOML > code
        defaults. Explicit ``create_app`` arguments are applied by the app
        factory after this method returns.
        """

        data: dict[str, Any] = {}
        if self.example_path.exists():
            data = tomllib.loads(self.example_path.read_text(encoding="utf-8"))
        if self.config_path.exists() and self.config_path.resolve() != self.example_path.resolve():
            local = tomllib.loads(self.config_path.read_text(encoding="utf-8"))
            data = _deep_merge(data, local)
        return data

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


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        current = merged.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            merged[key] = _deep_merge(current, value)
        else:
            merged[key] = value
    return merged


def _apply_environment_overrides(data: dict[str, Any]) -> dict[str, Any]:
    merged = _deep_merge({}, data)
    app = dict(merged.get("app") or {})
    server = dict(merged.get("server") or {})
    search = dict(merged.get("search") or {})

    _set_if_present(app, "workspace_dir", "RESEARCHSENSEI_WORKSPACE_DIR")
    _set_if_present(app, "parser_backend", "RESEARCHSENSEI_PARSER_BACKEND")
    _set_if_present(app, "max_upload_mb", "RESEARCHSENSEI_MAX_UPLOAD_MB", cast=int)
    _set_if_present(server, "host", "RESEARCHSENSEI_SERVER_HOST")
    _set_if_present(server, "port", "RESEARCHSENSEI_SERVER_PORT", cast=int)
    _set_if_present(server, "reload", "RESEARCHSENSEI_SERVER_RELOAD", cast=_as_bool)
    _set_if_present(search, "execution", "RESEARCHSENSEI_PAPER_SEARCH_EXECUTION")
    _set_if_present(search, "command", "RESEARCHSENSEI_PAPER_SEARCH_COMMAND")
    _set_if_present(
        search,
        "sources",
        "RESEARCHSENSEI_PAPER_SEARCH_SOURCES",
        cast=lambda value: [item.strip() for item in value.split(",") if item.strip()],
    )
    _set_if_present(search, "max_results", "RESEARCHSENSEI_SEARCH_MAX_RESULTS", cast=int)
    _set_if_present(search, "timeout_seconds", "RESEARCHSENSEI_SEARCH_TIMEOUT_SECONDS", cast=int)
    _set_if_present(search, "min_citation_count", "RESEARCHSENSEI_SEARCH_MIN_CITATIONS", cast=int)
    _set_if_present(
        search,
        "max_download_candidates",
        "RESEARCHSENSEI_SEARCH_MAX_DOWNLOAD_CANDIDATES",
        cast=int,
    )
    _set_if_present(
        search,
        "browser_download_enabled",
        "RESEARCHSENSEI_BROWSER_DOWNLOAD_ENABLED",
        cast=_as_bool,
    )
    _set_if_present(
        search,
        "browser_session_state",
        "RESEARCHSENSEI_BROWSER_SESSION_STATE",
    )
    _set_if_present(
        search,
        "browser_headless",
        "RESEARCHSENSEI_BROWSER_HEADLESS",
        cast=_as_bool,
    )

    merged["app"] = app
    merged["server"] = server
    merged["search"] = search
    return merged


def _set_if_present(
    target: dict[str, Any],
    key: str,
    env_name: str,
    *,
    cast: Any | None = None,
) -> None:
    raw = os.getenv(env_name)
    if raw is None or not raw.strip():
        return
    target[key] = cast(raw.strip()) if cast is not None else raw.strip()


def _as_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"invalid boolean value: {value}")


def redact_secret(message: str, secret: str | None) -> str:
    if not secret:
        return message
    return message.replace(secret, "[REDACTED]")
