/**
 * Signal Quality Evaluator — Claude-powered second opinion on pipeline signals.
 *
 * When Claude is unavailable, signals are REJECTED — the system does not
 * trade without AI quality analysis.
 *
 * Ported from backend/app/advisor/signal_quality.py
 */

import {
  callClaudeJson,
  recordAIInsight,
  type ModelTier,
  type AIResponse,
} from '../anthropic.ts'

// ---------- Types ----------

export interface SignalData {
  action: string
  symbol: string
  timeframe: string
  regime: string
  trend_direction: string
  trend_strength: number
  confluence_score: number
  triggers: string[]
  risk_reward?: number | string
}

export interface ConfluenceDetail {
  hit: boolean
  weight: number
  earned: number
  [key: string]: unknown
}

export interface CandleSummary {
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface MtfData {
  mtf_confidence?: number | string
  timeframe_alignment?: string
  reasoning?: string
}

export interface RiskAdjustments {
  position_size_factor: number
  reasoning: string
}

export interface QualityResult {
  quality_score: number
  recommendation: 'strong_confirm' | 'confirm' | 'caution' | 'reject'
  reasoning: string
  risk_adjustments: RiskAdjustments
}

// ---------- System prompt ----------

const SYSTEM_PROMPT =
  'You are a senior quantitative trader evaluating automated ' +
  'signals from a crypto trading system called SignalForgeAI. ' +
  'Your job is to assess the overall quality of each signal ' +
  'by weighing BOTH the strengths and the weaknesses.\n\n' +
  'You receive 14 confluence factors with hit/miss status, ' +
  'candle data, and market context. Evaluate the signal by:\n' +
  '1. Counting how many key factors support the trade\n' +
  '2. Checking if momentum indicators confirm the direction\n' +
  '3. Assessing multi-timeframe alignment (if provided)\n' +
  '4. Identifying any genuine deal-breakers (not minor gaps)\n\n' +
  'IMPORTANT: A signal does NOT need all 14 factors to be valid. ' +
  '5-7 confirming factors with the core ones aligned (trend, ' +
  'Fibonacci, RSI, MACD) is a solid setup. Missing secondary ' +
  'factors like CCI, Williams %R, or Stochastic is normal — ' +
  'do NOT reject a signal just because secondary indicators miss.\n\n' +
  'Only reject if there is a genuine structural problem:\n' +
  '- The signal direction conflicts with ALL higher timeframes\n' +
  '- Core momentum indicators (RSI + MACD) both contradict\n' +
  '- The regime is chaotic or transitioning against the signal\n\n' +
  'Return ONLY valid JSON with this structure:\n' +
  '{\n' +
  '  "quality_score": 0-100,\n' +
  '  "recommendation": "strong_confirm|confirm|caution|reject",\n' +
  '  "reasoning": "2-4 sentence balanced analysis",\n' +
  '  "risk_adjustments": {\n' +
  '    "position_size_factor": 0.0-1.5,\n' +
  '    "reasoning": "Why position size should be adjusted"\n' +
  '  }\n' +
  '}\n\n' +
  'Guidelines for recommendation:\n' +
  '- strong_confirm (>= 75): Core factors align, good conviction\n' +
  '- confirm (50-74): Reasonable setup, proceed normally\n' +
  '- caution (30-49): Weaker setup, proceed with reduced size\n' +
  '- reject (< 30): Genuine structural flaw or clear trap\n\n' +
  'Respond ONLY with valid JSON.'

// ---------- Helpers ----------

export function buildQualityUserMessage(
  signalData: SignalData,
  confluenceDetails: Record<string, ConfluenceDetail>,
  candleSummary: CandleSummary[],
  mtfData?: MtfData | null,
): string {
  const lines: string[] = [
    `Signal: ${signalData.action} ${signalData.symbol} (${signalData.timeframe})`,
    `Regime: ${signalData.regime}`,
    `Trend: ${signalData.trend_direction} (strength: ${signalData.trend_strength.toFixed(4)})`,
    `Algorithmic confluence score: ${signalData.confluence_score}/100`,
    `Triggers fired: ${signalData.triggers.join(', ')}`,
    `Risk/Reward: ${signalData.risk_reward ?? 'N/A'}`,
    '',
    'Confluence factor details (14 factors):',
  ]

  for (const [factor, info] of Object.entries(confluenceDetails)) {
    const hit = info.hit ?? false
    const weight = info.weight ?? 0
    const earned = info.earned ?? 0
    const extra: Record<string, unknown> = {}
    for (const [k, v] of Object.entries(info)) {
      if (!['hit', 'weight', 'earned'].includes(k)) extra[k] = v
    }
    lines.push(
      `  ${factor}: ${hit ? 'HIT' : 'MISS'} (${earned}/${weight}) ${JSON.stringify(extra)}`,
    )
  }

  lines.push('')
  lines.push('Last 5 candles (newest first):')
  for (const candle of candleSummary.slice(0, 5)) {
    lines.push(
      `  O=${candle.open.toFixed(2)} H=${candle.high.toFixed(2)} ` +
        `L=${candle.low.toFixed(2)} C=${candle.close.toFixed(2)} V=${Math.round(candle.volume)}`,
    )
  }

  if (mtfData) {
    lines.push('')
    lines.push('Multi-timeframe analysis:')
    lines.push(`  MTF confidence: ${mtfData.mtf_confidence ?? 'N/A'}/100`)
    lines.push(`  Alignment: ${mtfData.timeframe_alignment ?? 'N/A'}`)
    if (mtfData.reasoning) {
      lines.push(`  MTF reasoning: ${mtfData.reasoning}`)
    }
  }

  return lines.join('\n')
}

// ---------- Validation ----------

const VALID_RECOMMENDATIONS = ['strong_confirm', 'confirm', 'caution', 'reject'] as const

function validateResult(result: Record<string, unknown>, signalData: SignalData): QualityResult {
  let qualityScore = Number(result.quality_score ?? signalData.confluence_score)
  qualityScore = Math.max(0, Math.min(100, Math.round(qualityScore)))

  let recommendation = (result.recommendation as string) ?? 'confirm'
  if (!(VALID_RECOMMENDATIONS as readonly string[]).includes(recommendation)) {
    recommendation = 'confirm'
  }

  const riskAdj = (result.risk_adjustments ?? {}) as Record<string, unknown>
  let sizeFactor = Number(riskAdj.position_size_factor ?? 1.0)
  sizeFactor = Math.max(0.0, Math.min(1.5, sizeFactor))

  return {
    quality_score: qualityScore,
    recommendation: recommendation as QualityResult['recommendation'],
    reasoning: (result.reasoning as string) ?? '',
    risk_adjustments: {
      position_size_factor: sizeFactor,
      reasoning: (riskAdj.reasoning as string) ?? '',
    },
  }
}

function featureDisabledResult(signalData: SignalData): QualityResult {
  return {
    quality_score: signalData.confluence_score,
    recommendation: 'confirm',
    reasoning: 'AI signal quality evaluation disabled by configuration.',
    risk_adjustments: {
      position_size_factor: 1.0,
      reasoning: 'No adjustment — feature disabled',
    },
  }
}

function aiUnavailableReject(): QualityResult {
  return {
    quality_score: 0,
    recommendation: 'reject',
    reasoning:
      'Claude unavailable — signal rejected. ' +
      'The system does not trade without AI quality analysis.',
    risk_adjustments: {
      position_size_factor: 0.0,
      reasoning: 'Trade blocked — AI unavailable',
    },
  }
}

// ---------- Public API ----------

/**
 * Evaluate signal quality using Claude as a second opinion.
 *
 * When Claude is unavailable, signals are REJECTED — the system does not
 * trade without AI quality analysis.
 *
 * @param enabled  Whether the feature is enabled (from config)
 */
export async function evaluateSignalQuality(
  signalData: SignalData,
  confluenceDetails: Record<string, ConfluenceDetail>,
  candleSummary: CandleSummary[],
  mtfData?: MtfData | null,
  enabled = true,
): Promise<QualityResult> {
  if (!enabled) {
    return featureDisabledResult(signalData)
  }

  const userMessage = buildQualityUserMessage(
    signalData,
    confluenceDetails,
    candleSummary,
    mtfData,
  )

  try {
    const { data, meta } = await callClaudeJson<Record<string, unknown>>(
      SYSTEM_PROMPT,
      userMessage,
      'FAST' as ModelTier,
    )

    await recordAIInsight('signal_quality', meta, {
      symbol: signalData.symbol,
      resultJson: data as Record<string, unknown>,
    })

    return validateResult(data, signalData)
  } catch (err) {
    console.warn(
      `Claude unavailable — rejecting signal ${signalData.symbol} ${signalData.action} (no AI quality analysis):`,
      err,
    )
    return aiUnavailableReject()
  }
}
