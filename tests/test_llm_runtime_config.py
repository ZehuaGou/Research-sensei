from __future__ import annotations

from researchsensei.llm.runtime_config import card_timeout_seconds


def test_card_timeout_uses_default_without_env(monkeypatch) -> None:
    monkeypatch.delenv("RESEARCHSENSEI_LLM_CARD_TIMEOUT_SECONDS", raising=False)

    assert card_timeout_seconds(300.0) == 300.0


def test_card_timeout_can_be_overridden_by_env(monkeypatch) -> None:
    monkeypatch.setenv("RESEARCHSENSEI_LLM_CARD_TIMEOUT_SECONDS", "12.5")

    assert card_timeout_seconds(300.0) == 12.5


def test_card_timeout_ignores_invalid_env(monkeypatch) -> None:
    monkeypatch.setenv("RESEARCHSENSEI_LLM_CARD_TIMEOUT_SECONDS", "fast")

    assert card_timeout_seconds(300.0) == 300.0
