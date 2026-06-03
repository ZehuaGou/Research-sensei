from __future__ import annotations

from dataclasses import dataclass

from researchsensei.llm.types import ChatMessage


@dataclass
class TokenEstimate:
    """Estimated token counts for a prompt."""

    input_tokens: int
    max_output_tokens: int
    total_tokens: int
    over_budget: bool
    suggested_truncation: int = 0


class TokenBudget:
    """Lightweight token budget estimator using character-based approximation.

    Uses the rough heuristic of ~4 characters per token for English/Chinese mixed
    text. This is intentionally imprecise — for exact counts, use tiktoken or a
    provider-specific tokenizer in a later phase.
    """

    def __init__(
        self,
        *,
        max_input_tokens: int = 120_000,
        max_output_tokens: int = 4096,
        max_total_tokens: int = 128_000,
        chars_per_token: float = 4.0,
    ) -> None:
        self.max_input_tokens = max_input_tokens
        self.max_output_tokens = max_output_tokens
        self.max_total_tokens = max_total_tokens
        self.chars_per_token = chars_per_token

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count from text length."""
        return max(1, int(len(text) / self.chars_per_token))

    def estimate_messages(self, messages: list[ChatMessage]) -> TokenEstimate:
        """Estimate token budget for a list of messages."""
        total_chars = sum(len(m.content) for m in messages)
        # Add ~4 tokens overhead per message for role/formatting
        overhead = len(messages) * 4
        input_tokens = max(1, int(total_chars / self.chars_per_token)) + overhead
        total_tokens = input_tokens + self.max_output_tokens
        over_budget = input_tokens > self.max_input_tokens or total_tokens > self.max_total_tokens

        suggested = 0
        if over_budget:
            excess = input_tokens - self.max_input_tokens
            suggested = int(excess * self.chars_per_token)

        return TokenEstimate(
            input_tokens=input_tokens,
            max_output_tokens=self.max_output_tokens,
            total_tokens=total_tokens,
            over_budget=over_budget,
            suggested_truncation=suggested,
        )

    def suggest_truncation(
        self,
        messages: list[ChatMessage],
        *,
        target_input_tokens: int | None = None,
    ) -> list[ChatMessage]:
        """Suggest a truncated version of messages that fits the budget.

        Preserves the system message and truncates the longest content message.
        """
        target = target_input_tokens or self.max_input_tokens
        estimate = self.estimate_messages(messages)
        if not estimate.over_budget:
            return messages

        # Don't truncate system message
        result = list(messages)
        excess_chars = estimate.suggested_truncation

        # Find the longest non-system message and truncate it
        for i in range(len(result) - 1, -1, -1):
            if result[i].role == "system":
                continue
            if excess_chars <= 0:
                break
            content = result[i].content
            if len(content) > excess_chars:
                result[i] = ChatMessage(
                    role=result[i].role,
                    content=content[: len(content) - excess_chars] + "...[truncated]",
                )
                excess_chars = 0
            else:
                excess_chars -= len(content)
                result[i] = ChatMessage(
                    role=result[i].role, content="[content removed to fit budget]"
                )

        return result
