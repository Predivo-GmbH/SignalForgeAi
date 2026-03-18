/**
 * Adaptive Risk Tuner — Claude-powered strategy parameter optimization.
 *
 * When Claude is unavailable, no adjustments are made — the system does not
 * modify strategy parameters without AI analysis.
 *
 * Ported from backend/app/advisor/risk_tuner.py
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
  exit_time: string | null
  created_at: string
}

export interface TuneResult {
  adjustments: Record<string, number>
  reasoning: string
  metrics_snapshot: Record<string, number>
}

// ---------- Constants ----------

const SYSTEM_PROMPT = `You are a risk management specialist for SignalForgeAI, an automated crypto
trading platform. You analyze recent trading performance and recommend
risk parameter adjustments to optimize the strategy.

Recommend CONSERVATIVE adjustments — never change any parameter by more
than 20% from its current value in a single adjustment.

You may ONLY adjust these RISK MANAGEMENT parameters:
- min_confluence: 10-100 (higher = fewer but better trades)
- max_risk_per_trade: 0.005-0.10 (fraction of equity per trade)
- max_daily_loss: 0.01-0.20 (daily loss circuit breaker)
- atr_sl_multiplier: 0.5-5.0 (wider = fewer stop-outs)
- min_risk_reward: 0.5-5.0 (must be <= 1.6 — pipeline R:R is ~1.618)

Do NOT adjust pipeline sensitivity parameters (min_trigger_count,
trigger_lookback_candles, ema_slope_threshold). Those are part of the
strategy identity set by the AI Advisor and must not be changed.

Return ONLY valid JSON:
{
  "adjustments": {
    "param_name": new_value
  },
  "reasoning": "2-3 sentence explanation",
  "metrics_snapshot": {
    "win_rate": 0.0-1.0,
    "avg_pnl": number,
    "avg_risk_reward": number,
    "total_trades": number,
    "max_drawdown_pct": number
  }
}

Only include parameters that need changing in "adjustments".
If no changes are needed, return an empty adjustments object.
Respond ONLY with valid JSON.`

const PARAM_BOUNDS: Record<string, [number, number]> = {
  min_confluence: [10, 100],
  max_risk_per_trade: [0.005, 0.10],
  max_daily_loss: [0.01, 0.20],
  atr_sl_multiplier: [0.5, 5.0],
  min_risk_reward: [0.5, 5.0],
}

const MAX_CHANGE_PCT = 0.20

// ---------- Helpers ----------

function computeMetrics(trades: TradeRow[]): Record<string, number> {
  const total = trades.length
  const wins = trades.filter((t) => t.pnl != null && t.pnl > 0)
  const losses = trades.filter((t) => t.pnl != null && t.pnl <= 0)

  const winRate = total ? wins.length / total : 0
  const avgPnl = total
    ? trades.reduce((s, t) => s + (t.pnl ?? 0), 0) / total
    : 0

  const rrTrades = trades.filter((t) => t.risk_reward != null)
  const avgRr = rrTrades.length
    ? rrTrades.reduce((s, t) => s + (t.risk_reward ?? 0), 0) / rrTrades.length
    : 0

  // Max drawdown from cumulative PnL
  const sorted = [...trades].sort(
    (a, b) =>
      new Date(a.exit_time ?? a.created_at).getTime() -
      new Date(b.exit_time ?? b.created_at).getTime(),
  )
  let cumulative = 0
  let peak = 0
  let maxDd = 0
  for (const t of sorted) {
    cumulative += t.pnl ?? 0
    peak = Math.max(peak, cumulative)
    const dd = (peak - cumulative) / Math.max(peak, 1)
    maxDd = Math.max(maxDd, dd)
  }

  const slCount = losses.filter((t) => t.exit_reason === 'stop_loss').length
  const slRate = losses.length ? slCount / losses.length : 0

  const avgConfWins =
    wins.length > 0
      ? wins.reduce((s, t) => s + (t.confluence_score ?? 0), 0) / wins.length
      : 0
  const avgConfLosses =
    losses.length > 0
      ? losses.reduce((s, t) => s + (t.confluence_score ?? 0), 0) / losses.length
      : 0

  return {
    win_rate: Math.round(winRate * 1000) / 1000,
    avg_pnl: Math.round(avgPnl * 100) / 100,
    avg_risk_reward: Math.round(avgRr * 100) / 100,
    total_trades: total,
    max_drawdown_pct: Math.round(maxDd * 1000) / 1000,
    stop_loss_hit_rate: Math.round(slRate * 1000) / 1000,
    avg_confluence_wins: Math.round(avgConfWins * 10) / 10,
    avg_confluence_losses: Math.round(avgConfLosses * 10) / 10,
  }
}

function buildUserMessage(
  currentParams: Record<string, number>,
  metrics: Record<string, number>,
  patternContext?: Record<string, unknown> | null,
): string {
  const lines: string[] = ['Current risk parameters:']
  for (const [k, v] of Object.entries(currentParams)) {
    lines.push(`  ${k}: ${v}`)
  }

  lines.push('')
  lines.push('Recent performance metrics (last 50 trades):')
  for (const [k, v] of Object.entries(metrics)) {
    lines.push(`  ${k}: ${v}`)
  }

  if (patternContext) {
    const patterns = (patternContext.patterns as Array<Record<string, string>>) ?? []
    const recs = (patternContext.recommendations as Array<Record<string, string>>) ?? []
    if (patterns.length || recs.length) {
      lines.push('')
      lines.push('Deep pattern analysis insights:')
      for (const p of patterns.slice(0, 5)) {
        lines.push(`  [${p.severity ?? 'medium'}] ${p.pattern ?? ''}`)
      }
      for (const r of recs.slice(0, 3)) {
        lines.push(`  Recommendation: ${r.action ?? ''}`)
      }
    }
  }

  return lines.join('\n')
}

function validateAdjustments(
  adjustments: Record<string, unknown>,
  currentParams: Record<string, number>,
): Record<string, number> {
  const validated: Record<string, number> = {}

  for (const [param, rawVal] of Object.entries(adjustments)) {
    if (!(param in PARAM_BOUNDS)) continue
    const [lo, hi] = PARAM_BOUNDS[param]
    const current = currentParams[param]
    if (current == null) continue

    let newVal = Number(rawVal)
    // Clamp to valid range
    newVal = Math.max(lo, Math.min(hi, newVal))
    // Enforce max 20% change
    const maxChange = Math.abs(current) * MAX_CHANGE_PCT
    if (Math.abs(newVal - current) > maxChange) {
      newVal = newVal > current ? current + maxChange : current - maxChange
      newVal = Math.max(lo, Math.min(hi, newVal))
    }
    // Only include if actually changed
    if (Math.abs(newVal - current) > 1e-6) {
      validated[param] = Math.round(newVal * 10000) / 10000
    }
  }

  return validated
}

// ---------- Public API ----------

/**
 * Analyze recent trades and return risk parameter adjustments.
 *
 * Loads the last 50 closed trades for the given strategy, computes metrics,
 * and asks Claude for conservative risk parameter adjustments.
 */
export async function tuneRiskParams(
  strategyId: string,
  strategyConfig: Record<string, unknown>,
  patternContext?: Record<string, unknown> | null,
): Promise<TuneResult> {
  const currentParams: Record<string, number> = {
    min_confluence: Number(strategyConfig.min_confluence ?? 50),
    max_risk_per_trade: Number(strategyConfig.max_risk_per_trade ?? 0.02),
    max_daily_loss: Number(strategyConfig.max_daily_loss ?? 0.06),
    atr_sl_multiplier: Number(strategyConfig.atr_sl_multiplier ?? 2.0),
    min_risk_reward: Number(strategyConfig.min_risk_reward ?? 1.5),
  }

  // Load recent trades for this strategy
  const admin = getSupabaseAdmin()
  const { data: trades, error } = await admin
    .from('trades')
    .select('id, symbol, direction, pnl, risk_reward, confluence_score, exit_reason, exit_time, created_at, signal_id')
    .not('pnl', 'is', null)
    .order('exit_time', { ascending: false })
    .limit(50)

  if (error) {
    console.error('Failed to load trades for risk tuning:', error.message)
    return {
      adjustments: {},
      reasoning: 'Failed to load trade history.',
      metrics_snapshot: { total_trades: 0 },
    }
  }

  // Filter to trades belonging to this strategy via signal join
  const { data: signalIds } = await admin
    .from('signals')
    .select('id')
    .eq('strategy_id', strategyId)

  const strategySignalIds = new Set((signalIds ?? []).map((s: { id: string }) => s.id))
  const strategyTrades = (trades ?? []).filter(
    (t: Record<string, unknown>) => strategySignalIds.has(t.signal_id as string),
  ) as TradeRow[]

  if (strategyTrades.length < 5) {
    return {
      adjustments: {},
      reasoning: 'Insufficient trade history (need at least 5 closed trades).',
      metrics_snapshot: { total_trades: strategyTrades.length },
    }
  }

  const metrics = computeMetrics(strategyTrades)
  const userMessage = buildUserMessage(currentParams, metrics, patternContext)

  try {
    const { data: aiResult, meta } = await callClaudeJson<Record<string, unknown>>(
      SYSTEM_PROMPT,
      userMessage,
      'DEEP' as ModelTier,
    )

    await recordAIInsight('risk_tuning', meta, {
      strategyId,
      resultJson: aiResult as Record<string, unknown>,
    })

    const validated = validateAdjustments(
      (aiResult.adjustments ?? {}) as Record<string, unknown>,
      currentParams,
    )

    return {
      adjustments: validated,
      reasoning: (aiResult.reasoning as string) ?? '',
      metrics_snapshot: (aiResult.metrics_snapshot as Record<string, number>) ?? metrics,
    }
  } catch (err) {
    console.warn('Claude unavailable — skipping risk tuning (no adjustments without AI):', err)
    return {
      adjustments: {},
      reasoning:
        'Claude unavailable — no adjustments made. ' +
        'The system does not modify strategy parameters without AI analysis.',
      metrics_snapshot: metrics,
    }
  }
}
