from __future__ import annotations

import os

from researchsensei.core.config import (
    ConfigService,
    ModelProviderConfig,
    redact_secret,
)


def test_model_provider_config_defaults() -> None:
    cfg = ModelProviderConfig(name="test")
    assert cfg.kind == "openai_compatible"
    assert cfg.auth_header == "authorization"
    assert cfg.timeout_seconds == 60


def test_model_provider_config_mimo_api_key_header() -> None:
    cfg = ModelProviderConfig(name="mimo", auth_header="api-key")
    assert cfg.auth_header == "api-key"


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
    assert config.providers["mimo"].auth_header == "api-key"
    assert config.providers["mimo"].model == "mimo-v2"


def test_config_service_default_provider_fallback() -> None:
    service = ConfigService(
        config_path="/nonexistent/path.toml",
        env_path="/nonexistent/.env",
    )
    config = service.load()
    assert config.active_provider == "deepseek"
    assert "deepseek" in config.providers
    assert config.providers["deepseek"].base_url == "https://api.deepseek.com"
