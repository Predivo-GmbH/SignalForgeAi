/**
 * Deep Pattern Analyzer — Claude-powered trade history analysis.
 *
 * When Claude is unavailable, no patterns are generated — the system does not
 * fabricate analysis without AI.
 *
 * Ported from backend/app/advisor/pattern_analyzer.py
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
  regime?: string | null
}

export interface PatternResult {
  summary: string
  performance_metrics: Record<string, unknown>
  patterns: Array<{
    pattern: string
    evidence: string
    severity: 'high' | 'medium' | 'low'
    actionable: boolean
  }>
  strengths: string[]
  weaknesses: string[]
  recommendations: Array<{
    action: string
    expected_impact: string
    priority: 'high' | 'medium' | 'low'
  }>
}

// ---------- System prompt ----------

const SYSTEM_PROMPT =
  'You are a trading performance analyst for an automated crypto ' +
  'trading platform called SignalForgeAI. You receive a batch of ' +
  'completed trades with their details and must identify deep ' +
  'patterns, behavioral tendencies, and actionable insights.\n\n' +
  'Go beyond surface-level statistics. Look for:\n' +
  '1. Symbol-specific behavior (some pairs consistently trap)\n' +
  '2. Regime correlation (which regimes produce best/worst)\n' +
  '3. Confluence score correlation with actual outcomes\n' +
  '4. Exit reason patterns (stop-loss vs target-hit distribution)\n' +
  '5. Risk/Reward patterns (cutting winners short?)\n' +
  '6. Position sizing tendencies (over/under-sizing)\n' +
  '7. Streak patterns (loss clusters, recovery patterns)\n\n' +
  'Return ONLY valid JSON with this structure:\n' +
  '{\n' +
  '  "summary": "2-3 sentence overview of trading performance",\n' +
  '  "performance_metrics": {\n' +
  '    "win_rate": 0.0-1.0,\n' +
  '    "profit_factor": number,\n' +
  '    "avg_win": number,\n' +
  '    "avg_loss": number,\n' +
  '    "best_symbol": "symbol",\n' +
  '    "worst_symbol": "symbol"\n' +
  '  },\n' +
  '  "patterns": [\n' +
  '    {\n' +
  '      "pattern": "description of the pattern",\n' +
  '      "evidence": "specific data supporting this pattern",\n' +
  '      "severity": "high|medium|low",\n' +
  '      "actionable": true/false\n' +
  '    }\n' +
  '  ],\n' +
  '  "strengths": ["strength 1", "strength 2"],\n' +
  '  "weaknesses": ["weakness 1", "weakness 2"],\n' +
  '  "recommendations": [\n' +
  '    {\n' +
  '      "action": "specific recommendation",\n' +
  '      "expected_impact": "what improvement this should bring",\n' +
  '      "priority": "high|medium|low"\n' +
  '    }\n' +
  '  ]\n' +
  '}\n\n' +
  'Respond ONLY with valid JSON.'

// ---------- Helpers ----------

function buildUserMessage(trades: TradeRow[]): string {
  const lines: string[] = [`Analyzing ${trades.length} recent closed trades:`, '']

  // Per-trade detail (cap at 50 for token efficiency)
  const capped = trades.slice(0, 50)
  for (let i = 0; i < capped.length; i++) {
    const t = capped[i]
    lines.push(
      `${i + 1}. ${t.symbol} ${t.direction} | ` +
        `PnL: ${t.pnl != null ? (t.pnl >= 0 ? '+' : '') + t.pnl.toFixed(2) : 'N/A'} | ` +
        `R:R: ${t.risk_reward ?? 'N/A'} | ` +
        `Confluence: ${t.confluence_score ?? 'N/A'} | ` +
        `Exit: ${t.exit_reason ?? 'N/A'} | ` +
        `Regime: ${t.regime ?? 'N/A'}`,
    )
  }

  // Summary stats
  const total = trades.length
  const wins = trades.filter((t) => t.pnl != null && t.pnl > 0)
  const losses = trades.filter((t) => t.pnl != null && t.pnl <= 0)

  lines.push('')
  lines.push(`Quick stats: ${total} trades, ${wins.length} wins, ${losses.length} losses`)
  lines.push(`Win rate: ${total ? ((wins.length / total) * 100).toFixed(1) : '0.0'}%`)

  if (wins.length) {
    const avgWin = wins.reduce((s, t) => s + (t.pnl ?? 0), 0) / wins.length
    lines.push(`Avg win: ${avgWin >= 0 ? '+' : ''}${avgWin.toFixed(2)}`)
  }
  if (losses.length) {
    const avgLoss = losses.reduce((s, t) => s + (t.pnl ?? 0), 0) / losses.length
    lines.push(`Avg loss: ${avgLoss >= 0 ? '+' : ''}${avgLoss.toFixed(2)}`)
  }

  // Symbol breakdown
  const symbolPnl: Record<string, number> = {}
  const symbolCount: Record<string, number> = {}
  for (const t of trades) {
    symbolPnl[t.symbol] = (symbolPnl[t.symbol] ?? 0) + (t.pnl ?? 0)
    symbolCount[t.symbol] = (symbolCount[t.symbol] ?? 0) + 1
  }

  lines.push('')
  lines.push('Per-symbol P&L:')
  const sortedSymbols = Object.keys(symbolPnl).sort(
    (a, b) => symbolPnl[b] - symbolPnl[a],
  )
  for (const sym of sortedSymbols) {
    const pnl = symbolPnl[sym]
    lines.push(
      `  ${sym}: ${pnl >= 0 ? '+' : ''}${pnl.toFixed(2)} (${symbolCount[sym]} trades)`,
    )
  }

  return lines.join('\n')
}

function validateResult(result: Record<string, unknown>): PatternResult {
  const summary = (result.summary as string) ?? ''
  const performanceMetrics = (result.performance_metrics ?? {}) as Record<string, unknown>
  const strengths = (result.strengths ?? []) as string[]
  const weaknesses = (result.weaknesses ?? []) as string[]

  // Validate patterns
  const rawPatterns = (result.patterns ?? []) as Array<Record<string, unknown>>
  const validPatterns: PatternResult['patterns'] = []
  for (const p of rawPatterns) {
    if (typeof p === 'object' && p !== null && p.pattern) {
      let severity = (p.severity as string) ?? 'medium'
      if (!['high', 'medium', 'low'].includes(severity)) severity = 'medium'
      validPatterns.push({
        pattern: p.pattern as string,
        evidence: (p.evidence as string) ?? '',
        severity: severity as 'high' | 'medium' | 'low',
        actionable: p.actionable !== false,
      })
    }
  }

  // Validate recommendations
  const rawRecs = (result.recommendations ?? []) as Array<Record<string, unknown>>
  const validRecs: PatternResult['recommendations'] = []
  for (const r of rawRecs) {
    if (typeof r === 'object' && r !== null && r.action) {
      let priority = (r.priority as string) ?? 'medium'
      if (!['high', 'medium', 'low'].includes(priority)) priority = 'medium'
      validRecs.push({
        action: r.action as string,
        expected_impact: (r.expected_impact as string) ?? '',
        priority: priority as 'high' | 'medium' | 'low',
      })
    }
  }

  return {
    summary,
    performance_metrics: performanceMetrics,
    patterns: validPatterns,
    strengths,
    weaknesses,
    recommendations: validRecs,
  }
}

function emptyResult(): PatternResult {
  return {
    summary: 'No closed trades to analyse.',
    performance_metrics: {},
    patterns: [],
    strengths: [],
    weaknesses: [],
    recommendations: [],
  }
}

// ---------- Public API ----------

/**
 * Run deep analysis on recent trade history using Claude.
 */
export async function analyzePatterns(
  userId: string,
  limit = 100,
): Promise<PatternResult> {
  const admin = getSupabaseAdmin()
  const { data: trades, error } = await admin
    .from('trades')
    .select('id, symbol, direction, pnl, risk_reward, confluence_score, exit_reason, regime')
    .eq('user_id', userId)
    .not('pnl', 'is', null)
    .order('exit_time', { ascending: false })
    .limit(limit)

  if (error || !trades || trades.length === 0) {
    return emptyResult()
  }

  const userMessage = buildUserMessage(trades as TradeRow[])

  try {
    const { data: aiResult, meta } = await callClaudeJson<Record<string, unknown>>(
      SYSTEM_PROMPT,
      userMessage,
      'DEEP' as ModelTier,
    )

    await recordAIInsight('pattern_analysis', meta, {
      userId,
      resultJson: aiResult as Record<string, unknown>,
    })

    return validateResult(aiResult)
  } catch (err) {
    console.warn('Claude unavailable — skipping pattern analysis (no analysis without AI):', err)
    return emptyResult()
  }
}
