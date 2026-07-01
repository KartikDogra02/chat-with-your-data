"""Rough token-cost estimates for the models we run evals against.

Prices are USD per 1,000,000 tokens, taken from OpenAI's public pricing
(https://platform.openai.com/docs/pricing) as of 2026-07. They are a snapshot
and will drift — treat the derived costs as ballpark, not billing.
"""

# USD per 1M tokens: {model: {"input": ..., "output": ...}}
PRICES: dict[str, dict[str, float]] = {
    "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
}


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float | None:
    """Estimate the USD cost of a call, or None if the model isn't priced."""
    price = PRICES.get(model)
    if price is None:
        return None
    return input_tokens / 1e6 * price["input"] + output_tokens / 1e6 * price["output"]
