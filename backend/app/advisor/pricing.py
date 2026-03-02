"""Anthropic model pricing (per million tokens, USD)."""

# Source: https://docs.anthropic.com/en/docs/about-claude/models
PRICING: dict[str, dict[str, float]] = {
    "claude-haiku-4-5-20251001": {"input": 1.00, "output": 5.00},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-opus-4-6": {"input": 5.00, "output": 25.00},
}


def compute_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Return estimated cost in USD for a single API call."""
    rates = PRICING.get(model)
    if rates is None:
        return 0.0
    return (
        input_tokens * rates["input"] / 1_000_000
        + output_tokens * rates["output"] / 1_000_000
    )
