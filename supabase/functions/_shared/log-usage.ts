/**
 * Fire-and-forget logger for Anthropic API usage.
 * Call after every Anthropic API response to track per-project costs.
 *
 * Usage (non-streaming):
 *   const result = await fetch('https://api.anthropic.com/v1/messages', ...)
 *   const json = await result.json()
 *   logAnthropicUsage('BackOffice', 'process-bill', json)
 *
 * Usage (streaming — pass tokens manually):
 *   logAnthropicUsage('BenchmarkSignal', 'ai-chat', { model: 'claude-sonnet-4-6', usage: { input_tokens: 500, output_tokens: 200 } })
 */

// Per-million-token pricing (USD) — update when pricing changes
const MODEL_PRICING: Record<string, { input: number; output: number }> = {
  'claude-opus-4-6': { input: 15, output: 75 },
  'claude-sonnet-4-6': { input: 3, output: 15 },
  'claude-haiku-4-5-20251001': { input: 1, output: 5 },
  // Fallback for unknown models
  'default': { input: 3, output: 15 },
}

const BACKOFFICE_URL = 'https://xoecpzfsskalvjrtcbbl.supabase.co/functions/v1/log-api-usage'
const CRON_SECRET = 'sync-usage-cron-1b101455280a2e66341baf24b4cfe7e3'

interface AnthropicResponse {
  model?: string
  usage?: {
    input_tokens?: number
    output_tokens?: number
  }
}

export function logAnthropicUsage(
  projectName: string,
  edgeFunction: string,
  response: AnthropicResponse
): Promise<void> {
  const model = response.model ?? 'unknown'
  const inputTokens = response.usage?.input_tokens ?? 0
  const outputTokens = response.usage?.output_tokens ?? 0

  const pricing = MODEL_PRICING[model] ?? MODEL_PRICING['default']
  const cost = (inputTokens * pricing.input + outputTokens * pricing.output) / 1_000_000

  // IMPORTANT: Supabase kills pending fetches when the edge function returns.
  // Callers MUST await this before returning their response.
  return fetch(BACKOFFICE_URL, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${CRON_SECRET}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      project_name: projectName,
      edge_function: edgeFunction,
      provider: 'anthropic',
      model,
      input_tokens: inputTokens,
      output_tokens: outputTokens,
      estimated_cost_usd: Math.round(cost * 1_000_000) / 1_000_000,
    }),
  }).then(() => {}).catch(() => {
    // Silently ignore — logging should never break the main function
  })
}
