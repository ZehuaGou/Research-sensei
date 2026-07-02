from __future__ import annotations

import os


def card_timeout_seconds(default: float = 300.0) -> float:
    raw = os.getenv("RESEARCHSENSEI_LLM_CARD_TIMEOUT_SECONDS", "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    return value if value > 0 else default
