/**
 * SymbolScout — AI-driven evaluation of new symbol candidates.
 *
 * Called by the universe expansion task every 6 hours (and on-demand) to decide
 * which high-volume USDT pairs are worth adding to the candidate pool.
 *
 * This is strategic selection, not signal evaluation:
 *   - Signal evaluation (SignalQualityEvaluator) happens per-signal during live trading.
 *   - Symbol selection (SymbolScout) decides which symbols the pipeline should watch at all.
 *
 * No AI -> no candidates added (No AI, No Trading principle).
 *
 * Ported from backend/app/advisor/symbol_scout.py
 */

import { callClaudeJson, recordAIInsight, type ModelTier } from '../anthropic.ts'

// ---------- Types ----------

export interface SymbolCandidate {
  symbol: string
  quoteVolume: number
}

// ---------- System prompt ----------

const SYSTEM_PROMPT = `You are a systematic cryptocurrency trading analyst evaluating
new symbol candidates for a watchlist.

Given a list of new USDT trading pairs (with 24h volume) and the
active strategy parameters, select which symbols are worth monitoring.

Criteria for inclusion:
- Sufficient market structure for technical analysis
  (not pure speculation with no trend history)
- Volume consistent enough to produce reliable candle data
- Avoid symbols that heavily duplicate existing watchlist coverage
  (same sector, near-perfect correlation with already-watched tokens)
- Prefer symbols with observable trend/range regimes over purely
  random price action

Do NOT try to predict price direction. You are deciding which symbols
deserve pipeline attention, not which to buy.

Respond with JSON only:
{
  "approved": ["SYM1/USDT", "SYM2/USDT"],
  "rejected_count": 12,
  "reasoning": "One or two sentences explaining the selection logic."
}

If you have no candidates to evaluate, return:
{"approved": [], "rejected_count": 0, "reasoning": "No candidates."}`

// ---------- Helpers ----------

function buildUserMessage(
  candidates: SymbolCandidate[],
  strategyConfig: Record<string, unknown>,
  currentWatchlist: Set<string>,
): string {
  const timeframes = (strategyConfig.timeframes as string[]) ?? ['4h']
  const minConfluence = strategyConfig.min_confluence ?? 70

  const watchlistArr = [...currentWatchlist].sort().slice(0, 20)
  let watchlistStr = watchlistArr.join(', ')
  if (currentWatchlist.size > 20) {
    watchlistStr += ` \u2026 and ${currentWatchlist.size - 20} more`
  }

  const candidateLines = candidates
    .map((c) => `  ${c.symbol}  vol=$${c.quoteVolume.toLocaleString('en-US', { maximumFractionDigits: 0 })}`)
    .join('\n')

  return `Strategy context:
- Timeframes: ${timeframes.join(', ')}
- Min confluence required: ${minConfluence}
- Current watchlist (${currentWatchlist.size} symbols): ${watchlistStr}

New candidates to evaluate (${candidates.length} symbols, sorted by 24h volume):
${candidateLines}

Which of these candidates are worth adding to the watchlist for pipeline evaluation?`
}

// ---------- Public API ----------

/**
 * Ask Claude which candidates are worth adding to the watchlist.
 *
 * Returns list of approved symbol strings. Empty list if Claude unavailable.
 */
export async function evaluateCandidates(
  candidates: SymbolCandidate[],
  strategyConfig: Record<string, unknown>,
  currentWatchlist: Set<string>,
): Promise<string[]> {
  if (!candidates.length) return []

  // Cap at 100 candidates per call
  const capped = candidates.slice(0, 100)

  const userMessage = buildUserMessage(capped, strategyConfig, currentWatchlist)

  try {
    const { data: result, meta } = await callClaudeJson<Record<string, unknown>>(
      SYSTEM_PROMPT,
      userMessage,
      'DEEP' as ModelTier,
      1024,
    )

    await recordAIInsight('symbol_scout', meta, {
      resultJson: result as Record<string, unknown>,
    })

    const approved = (result.approved ?? []) as string[]
    const reasoning = (result.reasoning as string) ?? ''
    const rejected = (result.rejected_count as number) ?? capped.length - approved.length

    console.log(
      `SymbolScout: ${approved.length}/${approved.length + rejected} candidates approved. Reasoning: ${reasoning}`,
    )

    // Validate: only return symbols that were actually in our candidate list
    const candidateSymbols = new Set(capped.map((c) => c.symbol))
    return approved.filter((s) => candidateSymbols.has(s))
  } catch (err) {
    console.warn('SymbolScout: Claude unavailable — no candidates approved:', err)
    return []
  }
}
