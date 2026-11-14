"""Provider-agnostic LLM interface.

Keeping the interface this small (one method, four options) is intentional:
swapping OpenCode Go for another provider, or for the mock, must not require
touching the letter or scoring code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol, Sequence

Role = Literal["system", "user", "assistant"]


@dataclass(frozen=True)
class LLMMessage:
    role: Role
    content: str


@dataclass(frozen=True)
class LLMResult:
    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    duration_ms: int
    finish_reason: str | None = None


class LLMClient(Protocol):
    def complete(
        self,
        messages: Sequence[LLMMessage],
        *,
        model: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> LLMResult:
        """Send a chat completion request and return the parsed result."""
        ...
