from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import dotenv_values

logger = logging.getLogger(__name__)

_SENSITIVE_KEYS = frozenset({
    "DEEPSEEK_API_KEY",
    "MIMO_API_KEY",
    "OPENCODE_GO_API_KEY",
    "OPENAI_COMPATIBLE_API_KEY",
    "SEMANTIC_SCHOLAR_API_KEY",
    "S2_API_KEY",
})

_EMAIL_KEYS = frozenset({
    "UNPAYWALL_EMAIL",
    "RESEARCHSENSEI_CONTACT_EMAIL",
})

_S2_ALIASES = {
    "SEMANTIC_SCHOLAR_API_KEY": "S2_API_KEY",
    "S2_API_KEY": "SEMANTIC_SCHOLAR_API_KEY",
}

_KEY_PRESENT_LOG = frozenset({
    "UNPAYWALL_EMAIL",
    "RESEARCHSENSEI_CONTACT_EMAIL",
    "MIMO_API_KEY",
    "OPENCODE_GO_API_KEY",
    "DEEPSEEK_API_KEY",
    "SEMANTIC_SCHOLAR_API_KEY",
    "S2_API_KEY",
})


def mask_value(key: str, value: str) -> str:
    """Return a masked representation of a sensitive value.

    - Email: show first 3 chars + '***' + domain after @
    - API key: show first 3 chars + '***'
    - Empty: return 'MISSING'
    """
    if not value:
        return "MISSING"
    if key in _EMAIL_KEYS and "@" in value:
        local, domain = value.split("@", 1)
        return local[:3] + "***@" + domain
    return value[:3] + "***"


def load_runtime_env(
    *,
    env_path: str | Path = ".env",
    mask: bool = True,
    suppress_errors: bool = False,
) -> dict[str, str]:
    """Load .env file into os.environ for keys not already set.

    Also handles S2_API_KEY <-> SEMANTIC_SCHOLAR_API_KEY aliasing:
    if one is set and the other is not, the alias is populated.

    Args:
        env_path: Path to .env file (default ".env").
        mask: If True, values in returned dict are masked for logging.
        suppress_errors: If True, silently return empty on error.

    Returns:
        Dict of loaded key -> value (masked if mask=True).

    Never overwrites an already-set os.environ key.
    Never prints full keys or values to stdout/stderr (logs masked).
    """
    path = Path(env_path)
    if not path.exists():
        if suppress_errors:
            return {}
        raise FileNotFoundError(f".env file not found: {path.resolve()}")

    raw = dotenv_values(str(path))
    if not raw:
        return {}

    # Strip BOM (\ufeff) from keys — dotenv_values does not handle BOM
    normalized: dict[str, str] = {}
    for key, value in raw.items():
        clean_key = key.lstrip("\ufeff")
        if value is not None and value != "":
            normalized[clean_key] = value

    loaded: dict[str, str] = {}

    for key, value in normalized.items():
        if key in os.environ:
            continue
        os.environ[key] = value
        loaded[key] = value

    # Handle S2_API_KEY aliasing
    s2_val = os.environ.get("S2_API_KEY", "")
    sscholar_val = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")
    if s2_val and not sscholar_val:
        os.environ["SEMANTIC_SCHOLAR_API_KEY"] = s2_val
        loaded["SEMANTIC_SCHOLAR_API_KEY"] = s2_val
    if sscholar_val and not s2_val:
        os.environ["S2_API_KEY"] = sscholar_val
        loaded["S2_API_KEY"] = sscholar_val

    # Log masked key presence
    present_keys = {k for k in loaded if k in _KEY_PRESENT_LOG}
    if present_keys:
        masked_items = {k: mask_value(k, loaded[k]) for k in sorted(present_keys)}
        logger.info("Loaded from .env: %s", masked_items)

    if mask:
        return {k: mask_value(k, v) for k, v in loaded.items()}
    return loaded
