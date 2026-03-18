/**
 * Multi-Timeframe Analyzer — synthesizes signals across timeframes.
 *
 * When Claude is unavailable, MTF analysis returns a reject recommendation —
 * the system does not synthesize timeframe data without AI analysis.
 *
 * Ported from backend/app/advisor/multi_tf_analyzer.py
 */

import { callClaudeJson, recordAIInsight, type ModelTier } from '../anthropic.ts'

// ---------- Types ----------

export interface PrimarySignalData {
  timeframe: string
  regime: string
  trend_direction: string
  trend_strength: number
}

export interface TimeframeSummary {
  timeframe: string
  regime: string
  trend_direction: string
  trend_strength: number | string
  source?: string
  last_price?: number
  candle_count?: number
}

export interface MtfResult {
  mtf_confidence: number
  timeframe_alignment: 'aligned' | 'mixed' | 'conflicting'
  reasoning: string
  recommendation: 'confirm' | 'caution' | 'reject'
}

// ---------- System prompt ----------

const SYSTEM_PROMPT =
  'You are a multi-timeframe analysis expert for crypto trading. ' +
  'You receive technical analysis data from multiple timeframes ' +
  'for the same symbol and must synthesize them into a unified ' +
  'confidence assessment.\n\n' +
  'Key principles:\n' +
  '- Higher timeframes carry more weight (daily > 4h > 1h)\n' +
  '- A 1h buy signal AGAINST the daily trend is high-risk\n' +
  '- Confluence across all timeframes = highest confidence\n' +
  '- Divergence between timeframes = caution / reduced size\n' +
  '- If only 1h data is available, base assessment on that\n\n' +
  'Return ONLY valid JSON with this structure:\n' +
  '{\n' +
  '  "mtf_confidence": 0-100,\n' +
  '  "timeframe_alignment": "aligned|mixed|conflicting",\n' +
  '  "reasoning": "2-3 sentence synthesis across timeframes",\n' +
  '  "recommendation": "confirm|caution|reject"\n' +
  '}\n\n' +
  'Guidelines:\n' +
  '- aligned: All available timeframes agree on direction\n' +
  '- mixed: Some agree, some neutral/undetermined\n' +
  '- conflicting: Timeframes disagree on direction\n\n' +
  'Respond ONLY with valid JSON.'

// Higher timeframes to check (in addition to the primary signal timeframe)
const HIGHER_TIMEFRAMES = ['4h', '1d']

// ---------- Helpers ----------

function buildUserMessage(symbol: string, tfSummaries: TimeframeSummary[]): string {
  const lines: string[] = [`Symbol: ${symbol}`, '', 'Timeframe analysis:']
  for (const s of tfSummaries) {
    lines.push(
      `  ${s.timeframe}: regime=${s.regime ?? 'N/A'}, ` +
        `trend=${s.trend_direction ?? 'N/A'}, ` +
        `strength=${s.trend_strength ?? 'N/A'}`,
    )
  }
  return lines.join('\n')
}

function validateResult(result: Record<string, unknown>): MtfResult {
  let confidence = Math.max(0, Math.min(100, Math.round(Number(result.mtf_confidence ?? 50))))

  let alignment = (result.timeframe_alignment as string) ?? 'mixed'
  if (!['aligned', 'mixed', 'conflicting'].includes(alignment)) {
    alignment = 'mixed'
  }

  let recommendation = (result.recommendation as string) ?? 'confirm'
  if (!['confirm', 'caution', 'reject'].includes(recommendation)) {
    recommendation = 'confirm'
  }

  return {
    mtf_confidence: confidence,
    timeframe_alignment: alignment as MtfResult['timeframe_alignment'],
    reasoning: (result.reasoning as string) ?? '',
    recommendation: recommendation as MtfResult['recommendation'],
  }
}

function singleTimeframeResult(): MtfResult {
  return {
    mtf_confidence: 50,
    timeframe_alignment: 'mixed',
    reasoning: 'Only one timeframe available — MTF analysis not applicable.',
    recommendation: 'confirm',
  }
}

function aiUnavailableReject(): MtfResult {
  return {
    mtf_confidence: 0,
    timeframe_alignment: 'mixed',
    reasoning:
      'Claude unavailable — MTF analysis rejected. ' +
      'The system does not synthesize timeframe data without AI.',
    recommendation: 'reject',
  }
}

function featureDisabledResult(): MtfResult {
  return {
    mtf_confidence: 50,
    timeframe_alignment: 'mixed',
    reasoning: 'Multi-timeframe analysis disabled by configuration.',
    recommendation: 'confirm',
  }
}

// ---------- Public API ----------

/**
 * Synthesize multi-timeframe data for a signal.
 *
 * @param symbol            Trading pair (e.g. "BTC/USDT")
 * @param primarySignalData The primary signal's timeframe analysis
 * @param higherTfSummaries Pre-computed summaries for higher timeframes (optional)
 * @param enabled           Whether the feature is enabled
 */
export async function analyzeMultiTimeframe(
  symbol: string,
  primarySignalData: PrimarySignalData,
  higherTfSummaries?: TimeframeSummary[],
  enabled = true,
): Promise<MtfResult> {
  if (!enabled) {
    return featureDisabledResult()
  }

  // Build timeframe summaries
  const tfSummaries: TimeframeSummary[] = [
    {
      timeframe: primarySignalData.timeframe,
      regime: primarySignalData.regime,
      trend_direction: primarySignalData.trend_direction,
      trend_strength: primarySignalData.trend_strength,
      source: 'primary_signal',
    },
  ]

  // Add higher timeframe summaries if provided
  if (higherTfSummaries) {
    for (const htf of higherTfSummaries) {
      if (htf.timeframe !== primarySignalData.timeframe) {
        tfSummaries.push(htf)
      }
    }
  }

  // If we only have the primary timeframe, MTF analysis isn't applicable
  if (tfSummaries.length <= 1) {
    return singleTimeframeResult()
  }

  const userMessage = buildUserMessage(symbol, tfSummaries)

  try {
    const { data, meta } = await callClaudeJson<Record<string, unknown>>(
      SYSTEM_PROMPT,
      userMessage,
      'FAST' as ModelTier,
    )

    await recordAIInsight('multi_tf_analysis', meta, {
      symbol,
      resultJson: data as Record<string, unknown>,
    })

    return validateResult(data)
  } catch (err) {
    console.warn(
      `Claude unavailable — rejecting MTF analysis for ${symbol} (no synthesis without AI):`,
      err,
    )
    return aiUnavailableReject()
  }
}

export { HIGHER_TIMEFRAMES }
