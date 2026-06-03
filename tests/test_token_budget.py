from __future__ import annotations

from researchsensei.llm.token_budget import TokenBudget
from researchsensei.llm.types import ChatMessage


def test_token_budget_estimates_tokens_from_text() -> None:
    budget = TokenBudget()
    # 100 chars / 4 = 25 tokens
    assert budget.estimate_tokens("a" * 100) == 25


def test_token_budget_minimum_one_token() -> None:
    budget = TokenBudget()
    assert budget.estimate_tokens("") == 1
    assert budget.estimate_tokens("a") == 1


def test_token_budget_estimate_messages_within_budget() -> None:
    budget = TokenBudget(max_input_tokens=1000, max_output_tokens=100)
    messages = [
        ChatMessage(role="system", content="short"),
        ChatMessage(role="user", content="hello"),
    ]
    estimate = budget.estimate_messages(messages)
    assert estimate.input_tokens < 1000
    assert estimate.over_budget is False
    assert estimate.suggested_truncation == 0


def test_token_budget_estimate_messages_over_budget() -> None:
    budget = TokenBudget(max_input_tokens=10, max_output_tokens=10)
    messages = [
        ChatMessage(role="system", content="a" * 200),
        ChatMessage(role="user", content="b" * 200),
    ]
    estimate = budget.estimate_messages(messages)
    assert estimate.over_budget is True
    assert estimate.suggested_truncation > 0


def test_token_budget_suggest_truncation_preserves_system() -> None:
    budget = TokenBudget(max_input_tokens=10, max_output_tokens=10)
    messages = [
        ChatMessage(role="system", content="system instruction"),
        ChatMessage(role="user", content="a" * 500),
    ]
    truncated = budget.suggest_truncation(messages)
    # System message should be preserved
    assert truncated[0].content == "system instruction"
    # User message should be truncated
    assert len(truncated[1].content) < 500


def test_token_budget_suggest_truncation_noop_when_within_budget() -> None:
    budget = TokenBudget(max_input_tokens=10000)
    messages = [
        ChatMessage(role="system", content="short"),
        ChatMessage(role="user", content="hello"),
    ]
    truncated = budget.suggest_truncation(messages)
    assert truncated == messages


def test_token_budget_custom_chars_per_token() -> None:
    budget = TokenBudget(chars_per_token=2.0)
    # 100 chars / 2 = 50 tokens
    assert budget.estimate_tokens("a" * 100) == 50


def test_token_budget_total_includes_output() -> None:
    budget = TokenBudget(max_input_tokens=1000, max_output_tokens=500)
    messages = [ChatMessage(role="user", content="a" * 100)]
    estimate = budget.estimate_messages(messages)
    assert estimate.total_tokens == estimate.input_tokens + 500
