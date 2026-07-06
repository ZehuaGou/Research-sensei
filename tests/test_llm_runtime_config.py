from __future__ import annotations

from researchsensei.llm.runtime_config import (
    card_max_retries,
    card_retry_delay_seconds,
    card_timeout_seconds,
)


def test_card_timeout_uses_default_without_env(monkeypatch) -> None:
    monkeypatch.delenv("RESEARCHSENSEI_LLM_CARD_TIMEOUT_SECONDS", raising=False)

    assert card_timeout_seconds(300.0) == 300.0


def test_card_timeout_can_be_overridden_by_env(monkeypatch) -> None:
    monkeypatch.setenv("RESEARCHSENSEI_LLM_CARD_TIMEOUT_SECONDS", "12.5")

    assert card_timeout_seconds(300.0) == 12.5


def test_card_timeout_ignores_invalid_env(monkeypatch) -> None:
    monkeypatch.setenv("RESEARCHSENSEI_LLM_CARD_TIMEOUT_SECONDS", "fast")

    assert card_timeout_seconds(300.0) == 300.0


def test_card_max_retries_defaults_to_fast_fail(monkeypatch) -> None:
    monkeypatch.delenv("RESEARCHSENSEI_LLM_CARD_MAX_RETRIES", raising=False)

    assert card_max_retries() == 0


def test_card_max_retries_can_be_overridden(monkeypatch) -> None:
    monkeypatch.setenv("RESEARCHSENSEI_LLM_CARD_MAX_RETRIES", "2")

    assert card_max_retries() == 2


def test_card_retry_delay_can_be_overridden(monkeypatch) -> None:
    monkeypatch.setenv("RESEARCHSENSEI_LLM_CARD_RETRY_DELAY_SECONDS", "1.25")

    assert card_retry_delay_seconds() == 1.25
