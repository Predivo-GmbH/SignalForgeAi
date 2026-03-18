/**
 * AI Investment Planner — autonomous strategy generation.
 *
 * The AI advisor analyzes market conditions and determines ALL optimal
 * strategy parameters. No presets. No human risk selection.
 *
 * When Claude is unavailable, plan generation fails — the system does not
 * trade without AI analysis.
 *
 * Ported from backend/app/advisor/planner.py
 */

import { callClaudeJson, recordAIInsight, type ModelTier } from '../anthropic.ts'

// ---------- Types ----------

export interface ScoredCrypto {
  symbol: string
  score: number
  regime: string
  trend_direction: string
  rsi: number
  adx: number
  atr_pct: number
  recommendation: string
}

export interface MarketProfile {
  trending_pct: number
  bullish_pct: number
  avg_score: number
  avg_adx: number
  avg_volatility: number
  chaotic_pct: number
}

export interface StrategyConfig {
  min_confluence: number
  min_trigger_count: number
  trigger_lookback_candles: number
  ema_slope_threshold: number
  max_risk_per_trade: number
  max_daily_loss: number
  atr_sl_multiplier: number
  min_risk_reward: number
  timeframes: string[]
  trailing_stop_enabled: boolean
  atr_trail_multiplier: number
  drawdown_breaker_enabled: boolean
  max_drawdown_pct: number
  break_even_enabled: boolean
  break_even_r_multiple: number
  cppi_enabled: boolean
  max_hold_hours: number
  correlation_monitor_enabled: boolean
  correlation_threshold: number
  usdt_reserve_pct: number
  account_equity?: number
  [key: string]: unknown
}

export interface InvestmentPlan {
  summary: string
  selected_cryptos: Array<{ symbol: string; reason: string }>
  strategy_config: StrategyConfig
  reasoning: string
  reserve_reasoning?: string
  expected_behavior: string
  warnings: string[]
}

// ---------- System prompt ----------

const PLANNER_SYSTEM_PROMPT = `You are the autonomous AI trading advisor for SignalForgeAI.
You analyze market conditions and determine the OPTIMAL strategy parameters.
There are no presets — you decide everything based on your analysis.

The trading pipeline has 6 sequential layers. A trade is only placed when
ALL layers pass. You control the sensitivity of each gate:

PIPELINE SENSITIVITY (directly controls trade frequency):
- min_confluence (10-100): Minimum technical confluence score to accept a signal.
  14 weighted factors (Fibonacci, S/R overlap, VWAP, RSI, MACD, Bollinger, etc.)
  scored 0-100. Lower threshold = more trades but lower quality. Typical: 35-60.
- min_trigger_count (1-5): How many of 5 trigger types must confirm entry.
  Triggers: MACD crossover, RSI midline cross, stochastic exit, engulfing candle,
  zone reclaim. Each is a crossover event. Lower = more trades. Typical: 1-2.
- trigger_lookback_candles (1-10): How many candles back to check for trigger
  crossovers. 1 = must happen on the exact latest candle (very strict).
  3-5 = crossover within recent candles (much more achievable). Typical: 3-5.
- ema_slope_threshold (0.0001-0.01): Minimum EMA-200 slope for trend
  confirmation. Lower = accepts weaker/developing trends. Typical: 0.0003-0.002.

RISK MANAGEMENT:
- max_risk_per_trade (0.001-0.10): Max position risk as fraction of equity.
- max_daily_loss (0.01-0.20): Daily loss circuit breaker fraction.
- atr_sl_multiplier (0.5-5.0): Stop-loss distance in ATR multiples.
- min_risk_reward (0.5-5.0): Minimum reward:risk ratio. The pipeline uses
  Fibonacci extensions (TP1=1.618x risk), so R:R is always ~1.618. Set this
  at or below 1.618 to avoid blocking all trades.

TIMEFRAMES:
- timeframes: ["1h"] or ["4h"] or ["1h", "4h"]. 1h = more frequent signals.

RISK FEATURES (enable/disable based on conditions):
- trailing_stop_enabled (bool) + atr_trail_multiplier (0.5-5.0)
- drawdown_breaker_enabled (bool) + max_drawdown_pct (0.05-0.50)
- break_even_enabled (bool) + break_even_r_multiple (0.5-3.0)
- cppi_enabled (bool) + cppi_multiplier (1.0-10.0)
- max_hold_hours (1-168): Close position after this many hours.
- correlation_monitor_enabled (bool) + correlation_threshold (0.3-0.95)

USDT RESERVE POLICY:
You must also recommend the optimal USDT reserve percentage for the portfolio.
This controls how much of the portfolio value stays as USDT (dry powder) and is
NOT deployed into trades. The reserve ensures the system can act on buy signals.

Guidelines for usdt_reserve_pct (0.0 - 0.50):
- Strong bull market, high trending%: 0.05 - 0.10 (maximize exposure)
- Normal/mixed market: 0.10 - 0.20 (balanced)
- Weak/choppy market, low trending%: 0.15 - 0.25 (preserve capital)
- Bear market, high chaotic%: 0.25 - 0.40 (defensive, keep dry powder)
- Extreme fear/crash conditions: 0.35 - 0.50 (cash-heavy, wait for opportunities)

Include "usdt_reserve_pct" in strategy_config and "reserve_reasoning" (1 sentence
explaining your choice) in the top-level response.

CRITICAL RULES:
- Choose parameters that match current market conditions. If the market is
  not suitable for trading, strict parameters that produce zero trades is
  the correct outcome — do NOT artificially loosen settings to force trades.
- In low-trending markets (trending% < 30), adjust ema_slope_threshold and
  trigger_lookback_candles to match actual market behavior — not to force signals.
- min_risk_reward MUST be <= 1.6 (pipeline R:R is ~1.618 from Fibonacci).
- Select 3-15 cryptos with the best technical setups.

Respond ONLY with valid JSON.`

// ---------- Helpers ----------

function buildAdvisorUserMessage(
  scoredCryptos: ScoredCrypto[],
  investmentAmount: number,
  marketProfile: MarketProfile,
): string {
  const cryptoTable = scoredCryptos
    .slice(0, 30)
    .map(
      (c) =>
        `  ${c.symbol}: score=${c.score}, regime=${c.regime}, ` +
        `trend=${c.trend_direction}, RSI=${c.rsi}, ADX=${c.adx}, ` +
        `volatility=${c.atr_pct}%, recommendation=${c.recommendation}`,
    )
    .join('\n')

  const profileLines = Object.entries(marketProfile)
    .map(([k, v]) => `  ${k}: ${v}`)
    .join('\n')

  return `Market scan results — top-scored cryptocurrencies:
${cryptoTable}

Market profile:
${profileLines}

Investment amount: $${investmentAmount.toLocaleString('en-US', { maximumFractionDigits: 0 })}

Analyze these market conditions and generate the OPTIMAL strategy.
Return ONLY valid JSON:
{
  "summary": "2-3 sentence market analysis and strategy rationale",
  "selected_cryptos": [
    {"symbol": "BTC/USDT", "reason": "Why selected (1 sentence)"},
    ...
  ],
  "strategy_config": {
    "min_confluence": 45,
    "min_trigger_count": 2,
    "trigger_lookback_candles": 3,
    "ema_slope_threshold": 0.0005,
    "max_risk_per_trade": 0.02,
    "max_daily_loss": 0.06,
    "atr_sl_multiplier": 2.0,
    "min_risk_reward": 1.5,
    "timeframes": ["1h"],
    "trailing_stop_enabled": false,
    "atr_trail_multiplier": 2.0,
    "drawdown_breaker_enabled": true,
    "max_drawdown_pct": 0.15,
    "break_even_enabled": true,
    "break_even_r_multiple": 1.0,
    "cppi_enabled": false,
    "max_hold_hours": 24,
    "correlation_monitor_enabled": true,
    "correlation_threshold": 0.7,
    "usdt_reserve_pct": 0.15
  },
  "reasoning": "Detailed explanation of why these parameters are optimal",
  "reserve_reasoning": "Why this USDT reserve % is optimal for current conditions",
  "expected_behavior": "What to expect over 1 week (2-3 sentences)",
  "warnings": ["risk warning 1", "risk warning 2"]
}`
}

export function computeBasicProfile(scoredCryptos: ScoredCrypto[]): MarketProfile {
  if (!scoredCryptos.length) {
    return {
      trending_pct: 0,
      bullish_pct: 0,
      avg_score: 0,
      avg_adx: 0,
      avg_volatility: 0,
      chaotic_pct: 0,
    }
  }

  const total = scoredCryptos.length
  const trending = scoredCryptos.filter((c) =>
    (c.regime ?? '').startsWith('trending'),
  ).length
  const bullish = scoredCryptos.filter((c) => c.trend_direction === 'bullish').length
  const chaotic = scoredCryptos.filter((c) => c.regime === 'chaotic').length

  const mean = (arr: number[]) => arr.reduce((s, v) => s + v, 0) / arr.length

  return {
    trending_pct: Math.round((trending / total) * 1000) / 10,
    bullish_pct: Math.round((bullish / total) * 1000) / 10,
    avg_score: Math.round(mean(scoredCryptos.map((c) => c.score ?? 0)) * 10) / 10,
    avg_adx: Math.round(mean(scoredCryptos.map((c) => c.adx ?? 0)) * 10) / 10,
    avg_volatility:
      Math.round(mean(scoredCryptos.map((c) => c.atr_pct ?? 0)) * 100) / 100,
    chaotic_pct: Math.round((chaotic / total) * 1000) / 10,
  }
}

// ---------- Public API ----------

/**
 * Generate an autonomous investment plan.
 *
 * The AI determines ALL strategy parameters — no presets, no human
 * risk selection. Returns null if Claude is unavailable.
 */
export async function generatePlan(
  scoredCryptos: ScoredCrypto[],
  investmentAmount: number,
  marketProfile?: MarketProfile | null,
): Promise<InvestmentPlan | null> {
  const profile = marketProfile ?? computeBasicProfile(scoredCryptos)

  const userMessage = buildAdvisorUserMessage(
    scoredCryptos,
    investmentAmount,
    profile,
  )

  try {
    const { data: plan, meta } = await callClaudeJson<Record<string, unknown>>(
      PLANNER_SYSTEM_PROMPT,
      userMessage,
      'DEEP' as ModelTier,
      2500,
    )

    await recordAIInsight('investment_plan', meta, {
      resultJson: plan as Record<string, unknown>,
    })

    // Apply defaults
    const result: InvestmentPlan = {
      summary: (plan.summary as string) ?? 'AI-generated optimal strategy',
      selected_cryptos: (plan.selected_cryptos as InvestmentPlan['selected_cryptos']) ?? [],
      strategy_config: (plan.strategy_config ?? {}) as StrategyConfig,
      reasoning: (plan.reasoning as string) ?? '',
      reserve_reasoning: plan.reserve_reasoning as string | undefined,
      expected_behavior: (plan.expected_behavior as string) ?? '',
      warnings: (plan.warnings as string[]) ?? [],
    }
    result.strategy_config.account_equity = investmentAmount

    return result
  } catch (err) {
    console.warn(
      'Claude unavailable — cannot generate investment plan without AI analysis:',
      err,
    )
    return null
  }
}
