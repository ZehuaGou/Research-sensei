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


def card_max_retries(default: int = 0) -> int:
    raw = os.getenv("RESEARCHSENSEI_LLM_CARD_MAX_RETRIES", "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value >= 0 else default


def card_retry_delay_seconds(default: float = 0.5) -> float:
    raw = os.getenv("RESEARCHSENSEI_LLM_CARD_RETRY_DELAY_SECONDS", "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    return value if value >= 0 else default


def formula_card_batch_size(default: int = 10) -> int:
    raw = os.getenv("RESEARCHSENSEI_FORMULA_CARD_BATCH_SIZE", "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def formula_card_concurrency(default: int = 3) -> int:
    raw = os.getenv("RESEARCHSENSEI_FORMULA_CARD_CONCURRENCY", "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default
