/**
 * Claude AI client wrapper with cost tracking.
 * Ports backend/app/advisor/claude_client.py to TypeScript.
 */

import Anthropic from 'npm:@anthropic-ai/sdk@0.39'
import { getSupabaseAdmin } from './supabase.ts'

// Model tiers matching Python implementation
export const MODELS = {
  FAST: 'claude-haiku-4-5-20251001',
  DEEP: 'claude-sonnet-4-6-20250514',
  EXPERT: 'claude-opus-4-6-20250514',
} as const

// Pricing per million tokens (input/output)
const PRICING: Record<string, { input: number; output: number }> = {
  [MODELS.FAST]: { input: 1.0, output: 5.0 },
  [MODELS.DEEP]: { input: 3.0, output: 15.0 },
  [MODELS.EXPERT]: { input: 15.0, output: 75.0 },
}

export type ModelTier = keyof typeof MODELS

export interface AIResponse {
  content: string
  model: string
  inputTokens: number
  outputTokens: number
  costUsd: number
  latencyMs: number
}

/** Call Claude API with cost tracking */
export async function callClaude(
  systemPrompt: string,
  userPrompt: string,
  tier: ModelTier = 'DEEP',
  maxTokens = 4096,
  temperature = 0.3
): Promise<AIResponse> {
  const apiKey = Deno.env.get('ANTHROPIC_API_KEY')
  if (!apiKey) throw new Error('ANTHROPIC_API_KEY not set')

  const client = new Anthropic({ apiKey })
  const model = MODELS[tier]
  const start = performance.now()

  const response = await client.messages.create({
    model,
    max_tokens: maxTokens,
    temperature,
    system: systemPrompt,
    messages: [{ role: 'user', content: userPrompt }],
  })

  const latencyMs = Math.round(performance.now() - start)
  const inputTokens = response.usage.input_tokens
  const outputTokens = response.usage.output_tokens
  const pricing = PRICING[model] ?? { input: 3.0, output: 15.0 }
  const costUsd = (inputTokens * pricing.input + outputTokens * pricing.output) / 1_000_000

  const content = response.content
    .filter((b) => b.type === 'text')
    .map((b) => b.text)
    .join('')

  return { content, model, inputTokens, outputTokens, costUsd, latencyMs }
}

/** Call Claude and parse JSON response */
export async function callClaudeJson<T>(
  systemPrompt: string,
  userPrompt: string,
  tier: ModelTier = 'DEEP',
  maxTokens = 4096
): Promise<{ data: T; meta: AIResponse }> {
  const result = await callClaude(systemPrompt, userPrompt, tier, maxTokens)
  // Extract JSON from response (handles markdown code blocks)
  let jsonStr = result.content
  const match = jsonStr.match(/```(?:json)?\s*([\s\S]*?)```/)
  if (match) jsonStr = match[1]
  const data = JSON.parse(jsonStr.trim()) as T
  return { data, meta: result }
}

/** Record AI usage to database */
export async function recordAIInsight(
  insightType: string,
  aiResponse: AIResponse,
  context: {
    userId?: string
    signalId?: string
    strategyId?: string
    symbol?: string
    resultJson?: Record<string, unknown>
  }
): Promise<void> {
  const admin = getSupabaseAdmin()
  await admin.from('ai_insights').insert({
    insight_type: insightType,
    user_id: context.userId,
    signal_id: context.signalId,
    strategy_id: context.strategyId,
    symbol: context.symbol,
    model_used: aiResponse.model,
    reasoning: aiResponse.content,
    result_json: context.resultJson ?? {},
    confidence: null,
    input_tokens: aiResponse.inputTokens,
    output_tokens: aiResponse.outputTokens,
    latency_ms: aiResponse.latencyMs,
    cost_usd: aiResponse.costUsd,
  })
}
