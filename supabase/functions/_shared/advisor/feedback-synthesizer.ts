/**
 * Feedback Synthesizer — converts trade patterns into actionable rules.
 *
 * When Claude is unavailable, no rules are generated — the system does not
 * create feedback rules without AI analysis.
 *
 * Ported from backend/app/advisor/feedback_synthesizer.py
 */

import { callClaudeJson, recordAIInsight, type ModelTier } from '../anthropic.ts'
import { getSupabaseAdmin } from '../supabase.ts'

// ---------- Types ----------

export interface TradeRow {
  id: string
  symbol: string
  direction: string
  pnl: number | null
  risk_reward: number | null
  confluence_score: number | null
  exit_reason: string | null
}

export interface FeedbackRuleResult {
  rule_type: string
  description: string
  conditions: Record<string, unknown>
  confidence: number
}

// ---------- System prompt ----------

const SYSTEM_PROMPT =
  'You are a trading systems engineer for an automated crypto trading ' +
  'platform called SignalForgeAI. You analyze batches of completed trades ' +
  'to identify recurring patterns that should be encoded as rules for ' +
  'the system.\n\n' +
  'Rules must be specific and actionable. Each rule should have:\n' +
  '1. A clear condition (what market state or signal characteristic ' +
  'triggers this rule)\n' +
  '2. A clear action (skip signal, adjust parameter, require extra ' +
  'confirmation)\n' +
  '3. A confidence level (0.0-1.0) based on how consistent the ' +
  'pattern is\n\n' +
  'Only propose rules backed by 3+ trades showing the same pattern.\n\n' +
  'Return ONLY valid JSON with this structure:\n' +
  '{\n' +
  '  "rules": [\n' +
  '    {\n' +
  '      "rule_type": ' +
  '"avoid_pattern|prefer_pattern|adjust_param|filter_condition",\n' +
  '      "description": "Human-readable description of the rule",\n' +
  '      "conditions": {\n' +
  '        "symbol": "BTC/USDT or null for any",\n' +
  '        "regime": "trending|ranging|chaotic or null for any",\n' +
  '        "min_confluence": null or number,\n' +
  '        "action": "skip|reduce_size|require_confirmation"\n' +
  '      },\n' +
  '      "confidence": 0.0-1.0,\n' +
  '      "evidence": "What trades support this rule"\n' +
  '    }\n' +
  '  ],\n' +
  '  "summary": "1-2 sentence summary of findings"\n' +
  '}\n\n' +
  'Respond ONLY with valid JSON.'

// ---------- Helpers ----------

const VALID_RULE_TYPES = [
  'avoid_pattern',
  'prefer_pattern',
  'adjust_param',
  'filter_condition',
] as const

function validateRule(ruleData: Record<string, unknown>): boolean {
  if (typeof ruleData !== 'object' || ruleData === null) return false
  if (!ruleData.description) return false
  const ruleType = ruleData.rule_type as string
  return (VALID_RULE_TYPES as readonly string[]).includes(ruleType)
}

function buildUserMessage(trades: TradeRow[]): string {
  const lines: string[] = [
    `Analyzing ${trades.length} recent trades for pattern-based rules:`,
    '',
  ]

  for (let i = 0; i < trades.length; i++) {
    const t = trades[i]
    lines.push(
      `${i + 1}. ${t.symbol} ${t.direction} | ` +
        `PnL: ${t.pnl != null ? (t.pnl >= 0 ? '+' : '') + t.pnl.toFixed(2) : 'N/A'} | ` +
        `Confluence: ${t.confluence_score ?? 'N/A'} | ` +
        `Exit: ${t.exit_reason ?? 'N/A'} | R:R: ${t.risk_reward ?? 'N/A'}`,
    )
  }

  return lines.join('\n')
}

// ---------- Public API ----------

/**
 * Analyze recent trades and produce feedback rules.
 * Returns list of newly created FeedbackRule dicts.
 */
export async function synthesizeFeedback(
  strategyId: string,
  userId: string,
): Promise<FeedbackRuleResult[]> {
  const admin = getSupabaseAdmin()

  // Load signal IDs for this strategy
  const { data: signalRows } = await admin
    .from('signals')
    .select('id')
    .eq('strategy_id', strategyId)

  const signalIds = (signalRows ?? []).map((s: { id: string }) => s.id)
  if (signalIds.length === 0) return []

  // Load closed trades for these signals
  const { data: trades, error } = await admin
    .from('trades')
    .select('id, symbol, direction, pnl, risk_reward, confluence_score, exit_reason')
    .in('signal_id', signalIds)
    .not('pnl', 'is', null)
    .order('exit_time', { ascending: false })
    .limit(50)

  if (error || !trades) {
    console.error('Failed to load trades for feedback synthesis:', error?.message)
    return []
  }

  if (trades.length < 10) {
    return []
  }

  const userMessage = buildUserMessage(trades as TradeRow[])

  try {
    const { data: aiResult, meta } = await callClaudeJson<Record<string, unknown>>(
      SYSTEM_PROMPT,
      userMessage,
      'DEEP' as ModelTier,
    )

    await recordAIInsight('feedback_synthesis', meta, {
      strategyId,
      userId,
      resultJson: aiResult as Record<string, unknown>,
    })

    const newRules: FeedbackRuleResult[] = []
    const rawRules = (aiResult.rules ?? []) as Array<Record<string, unknown>>

    for (const ruleData of rawRules) {
      if (!validateRule(ruleData)) continue

      const confidence = Math.min(1.0, Math.max(0.0, Number(ruleData.confidence ?? 0.5)))
      const expiresAt = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString()

      // Insert rule into database
      await admin.from('feedback_rules').insert({
        strategy_id: strategyId,
        user_id: userId,
        rule_type: ruleData.rule_type,
        description: ruleData.description,
        conditions_json: ruleData.conditions ?? {},
        confidence,
        is_active: true,
        expires_at: expiresAt,
      })

      newRules.push({
        rule_type: ruleData.rule_type as string,
        description: ruleData.description as string,
        conditions: (ruleData.conditions ?? {}) as Record<string, unknown>,
        confidence,
      })
    }

    return newRules
  } catch (err) {
    console.warn('Claude unavailable — skipping feedback synthesis (no rules without AI):', err)
    return []
  }
}
