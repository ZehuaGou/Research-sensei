from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _disable_api_llm_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep unit tests independent from a developer's local .env LLM switch.

    Tests that verify .env loading explicitly delete this variable before
    constructing ConfigService.
    """

    monkeypatch.setenv("RESEARCHSENSEI_ENABLE_API_LLM", "0")
