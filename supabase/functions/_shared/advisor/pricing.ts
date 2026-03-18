/**
 * Anthropic model pricing (per million tokens, USD).
 *
 * Ported from backend/app/advisor/pricing.py
 */

// Source: https://docs.anthropic.com/en/docs/about-claude/models
export const PRICING: Record<string, { input: number; output: number }> = {
  'claude-haiku-4-5-20251001': { input: 1.0, output: 5.0 },
  'claude-sonnet-4-6': { input: 3.0, output: 15.0 },
  'claude-opus-4-6': { input: 5.0, output: 25.0 },
}

/** Return estimated cost in USD for a single API call. */
export function computeCost(
  model: string,
  inputTokens: number,
  outputTokens: number,
): number {
  const rates = PRICING[model]
  if (!rates) return 0.0
  return (
    (inputTokens * rates.input) / 1_000_000 +
    (outputTokens * rates.output) / 1_000_000
  )
}
