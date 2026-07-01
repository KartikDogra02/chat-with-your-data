"""Small helpers for tracking token usage across the LLM calls in a query.

Kept deliberately tiny: a dataclass that sums, and one function to pull usage
off an OpenAI Responses API result. Cost lives in pricing.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0

    def __add__(self, other: TokenUsage) -> TokenUsage:
        return TokenUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
        )


def token_usage_from(response: Any) -> TokenUsage:
    """Extract token usage from an OpenAI Responses API response.

    Defensive about shape: if usage is missing (e.g. a mocked response in
    tests), returns an empty TokenUsage rather than raising.
    """
    usage = getattr(response, "usage", None)
    if usage is None:
        return TokenUsage()
    return TokenUsage(
        input_tokens=getattr(usage, "input_tokens", 0) or 0,
        output_tokens=getattr(usage, "output_tokens", 0) or 0,
    )
