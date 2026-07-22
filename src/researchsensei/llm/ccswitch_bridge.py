from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from urllib.parse import urlsplit

from researchsensei.core.config import ModelProviderConfig


def resolve_ccswitch_api_key(
    provider: ModelProviderConfig,
    *,
    db_path: str | Path | None = None,
) -> str:
    """Resolve an OpenCode Go key from the user's active CC Switch provider.

    The bridge is deliberately narrow: it only returns a credential when the
    configured ResearchSensei endpoint and CC Switch's active Claude endpoint
    identify the same HTTPS upstream. The credential remains in memory and is
    never copied into ResearchSensei configuration or logs.
    """

    if provider.api_key_env:
        configured = os.getenv(provider.api_key_env, "").strip()
        if configured:
            return configured
    if not _bridge_enabled() or provider.kind != "openai_compatible":
        return ""

    path = Path(
        db_path
        or os.getenv("RESEARCHSENSEI_CCSWITCH_DB_PATH", "").strip()
        or (Path.home() / ".cc-switch" / "cc-switch.db")
    )
    if not path.is_file():
        return ""

    try:
        uri = f"file:{path.resolve().as_posix()}?mode=ro"
        with sqlite3.connect(uri, uri=True, timeout=1.0) as connection:
            row = connection.execute(
                """
                SELECT settings_config, meta
                FROM providers
                WHERE app_type = 'claude' AND is_current = 1
                ORDER BY created_at DESC
                LIMIT 1
                """
            ).fetchone()
    except (OSError, sqlite3.Error):
        return ""
    if row is None:
        return ""

    try:
        settings = json.loads(row[0] or "{}")
        meta = json.loads(row[1] or "{}")
    except (TypeError, ValueError, json.JSONDecodeError):
        return ""
    if str(meta.get("apiFormat") or meta.get("api_format") or "").lower() != "openai_chat":
        return ""

    env = settings.get("env")
    if not isinstance(env, dict):
        return ""
    stored_base_url = str(env.get("ANTHROPIC_BASE_URL") or "").strip()
    if not _same_openai_upstream(provider.base_url, stored_base_url):
        return ""
    return str(
        env.get("ANTHROPIC_AUTH_TOKEN")
        or env.get("ANTHROPIC_API_KEY")
        or ""
    ).strip()


def _bridge_enabled() -> bool:
    value = os.getenv("RESEARCHSENSEI_CCSWITCH_CREDENTIAL_BRIDGE", "auto").strip().lower()
    return value not in {"0", "false", "no", "off", "disabled"}


def _same_openai_upstream(configured_url: str, stored_url: str) -> bool:
    configured = _normalized_upstream(configured_url)
    stored = _normalized_upstream(stored_url)
    return bool(configured and stored and configured == stored)


def _normalized_upstream(value: str) -> tuple[str, str, int | None, str] | None:
    parsed = urlsplit(str(value or "").strip())
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        return None
    path = parsed.path.rstrip("/")
    if path.endswith("/v1"):
        path = path[:-3].rstrip("/")
    return parsed.scheme.lower(), parsed.hostname.lower(), parsed.port, path
