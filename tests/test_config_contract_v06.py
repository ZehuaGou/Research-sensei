from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from researchsensei.core.config import ConfigService
from researchsensei.web.app import create_app


def _write_config(
    path: Path,
    *,
    sources: str = '"openalex", "semantic"',
    max_results: int = 17,
    timeout_seconds: int = 23,
    max_upload_mb: int = 12,
    workspace_dir: str = "configured-workspace",
) -> None:
    path.write_text(
        f"""
active_provider = "cc_switch"

[providers.cc_switch]
kind = "anthropic_compatible"
base_url = "http://127.0.0.1:15721/v1"
api_key_env = ""
model = "test-model"
auth_header = "none"
timeout_seconds = 30

[app]
workspace_dir = "{workspace_dir}"
default_learning_mode = "reproducible_2h"
max_upload_mb = {max_upload_mb}
parser_backend = "pymupdf"

[server]
host = "127.0.0.1"
port = 8765
reload = false

[search]
execution = "auto"
command = "paper-search"
sources = [{sources}]
max_results = {max_results}
timeout_seconds = {timeout_seconds}
min_citation_count = 0
""".strip(),
        encoding="utf-8",
    )


def _clear_search_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "RESEARCHSENSEI_WORKSPACE_DIR",
        "RESEARCHSENSEI_MAX_UPLOAD_MB",
        "RESEARCHSENSEI_PARSER_BACKEND",
        "RESEARCHSENSEI_PAPER_SEARCH_SOURCES",
        "RESEARCHSENSEI_SEARCH_MAX_RESULTS",
        "RESEARCHSENSEI_SEARCH_TIMEOUT_SECONDS",
    ):
        monkeypatch.delenv(name, raising=False)


def test_toml_search_settings_reach_real_adapter_and_services(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _clear_search_env(monkeypatch)
    config_path = tmp_path / "local.toml"
    _write_config(config_path)
    explicit_workspace = tmp_path / "explicit-workspace"

    app = create_app(
        workspace_root=explicit_workspace,
        config_service=ConfigService(config_path=config_path, env_path=tmp_path / "missing.env"),
    )
    deps = app.state.dependencies
    adapter = deps.direction_service.adapters["paper_search"]

    assert deps.workspace.root == explicit_workspace
    assert adapter.sources == ["openalex", "semantic"]
    assert adapter.timeout_seconds == 23
    assert deps.direction_service.max_results_per_source == 17
    assert deps.seed_expansion_service.max_results_per_source == 17
    assert app.state.runtime_config.app.max_upload_mb == 12
    assert deps.runner.ingestion.__class__.__name__ == "LightweightIngestionService"
    deps.background_tasks.close()


def test_environment_overrides_toml_search_settings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _clear_search_env(monkeypatch)
    config_path = tmp_path / "local.toml"
    _write_config(config_path)
    monkeypatch.setenv("RESEARCHSENSEI_PAPER_SEARCH_SOURCES", "arxiv,dblp")
    monkeypatch.setenv("RESEARCHSENSEI_SEARCH_MAX_RESULTS", "31")
    monkeypatch.setenv("RESEARCHSENSEI_SEARCH_TIMEOUT_SECONDS", "41")

    config = ConfigService(config_path=config_path, env_path=tmp_path / "missing.env").load()

    assert config.search.sources == ["arxiv", "dblp"]
    assert config.search.max_results == 31
    assert config.search.timeout_seconds == 41


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"sources": '"made_up_source"'}, "sources"),
        ({"timeout_seconds": -1}, "timeout_seconds"),
        ({"max_results": 501}, "max_results"),
        ({"max_upload_mb": 2048}, "max_upload_mb"),
    ],
)
def test_invalid_runtime_configuration_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    overrides: dict[str, object],
    field: str,
) -> None:
    _clear_search_env(monkeypatch)
    config_path = tmp_path / "local.toml"
    _write_config(config_path, **overrides)

    with pytest.raises(ValidationError) as excinfo:
        ConfigService(config_path=config_path, env_path=tmp_path / "missing.env").load()

    assert field in str(excinfo.value)


def test_legacy_docling_value_migrates_to_real_parser(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_search_env(monkeypatch)
    config_path = tmp_path / "local.toml"
    _write_config(config_path)
    text = config_path.read_text(encoding="utf-8").replace('parser_backend = "pymupdf"', 'parser_backend = "docling"')
    config_path.write_text(text, encoding="utf-8")

    config = ConfigService(config_path=config_path, env_path=tmp_path / "missing.env").load()

    assert config.app.parser_backend == "pymupdf"
