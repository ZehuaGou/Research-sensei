from __future__ import annotations

from pydantic import Field

from researchsensei.schemas.base import SenseiModel


class ChatMessage(SenseiModel):
    role: str
    content: str


class ChatResponse(SenseiModel):
    content: str
    model: str = ""
    finish_reason: str = ""
    usage_prompt_tokens: int = 0
    usage_completion_tokens: int = 0
    usage_total_tokens: int = 0


class LLMConfig(SenseiModel):
    """Runtime LLM request parameters."""

    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1)
    json_mode: bool = False
    stream: bool = False
    timeout: float = Field(default=120.0, gt=0)
    max_retries: int = Field(default=3, ge=0)
    connect_retries: int = Field(default=1, ge=0)
    retry_delay: float = Field(default=1.0, ge=0)
    disable_thinking: bool = False
