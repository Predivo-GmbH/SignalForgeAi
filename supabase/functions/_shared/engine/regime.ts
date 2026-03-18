/**
 * Layer 0: Regime Detector.
 *
 * Determines current market regime using ADX (trend strength)
 * and ATR percentile (volatility context).
 * Output: TRENDING, RANGING, TRANSITIONING, or CHAOTIC.
 *
 * Note: HMM regime detection is dropped — rule-based only.
 */

import { calcADX, calcATR, extractArrays, type OHLCV } from '../indicators.ts'

// ── Regime enum ────────────────────────────────────────────────
export const Regime = {
  TRENDING: 'trending',
  TRENDING_BULL: 'trending_bull',
  TRENDING_BEAR: 'trending_bear',
  RANGING: 'ranging',
  TRANSITIONING: 'transitioning',
  CHAOTIC: 'chaotic',
} as const

export type Regime = (typeof Regime)[keyof typeof Regime]

// ── Regime Detector ────────────────────────────────────────────
export class RegimeDetector {
  detect(candles: OHLCV[]): Regime {
    return this._detectRuleBased(candles)
  }

  private _detectRuleBased(candles: OHLCV[]): Regime {
    const { highs, lows, closes } = extractArrays(candles)

    // ADX
    const adxResults = calcADX(highs, lows, closes, 14)
    const adxVal = adxResults.length > 0 ? adxResults[adxResults.length - 1].adx : 0
    const adxRegime = this._adxRegime(adxVal)

    // ATR percentile
    const atrPct = this._atrPercentile(candles, 100)

    // Chaotic: extreme volatility — requires both high ATR percentile
    // AND high ATR relative to price (normalized ATR > 3%).
    const atrValues = calcATR(highs, lows, closes, 14)
    const price = closes[closes.length - 1]
    let normalizedAtr = 0.0
    if (atrValues.length > 0 && price > 0) {
      normalizedAtr = atrValues[atrValues.length - 1] / price
    }

    if (atrPct > 90 && normalizedAtr > 0.03) {
      return Regime.CHAOTIC
    }

    // Consensus between ADX and ATR
    if (adxRegime === Regime.TRENDING) {
      if (atrPct < 20) {
        return Regime.TRANSITIONING
      }
      return Regime.TRENDING
    } else if (adxRegime === Regime.RANGING) {
      return Regime.RANGING
    } else {
      return Regime.TRANSITIONING
    }
  }

  private _adxRegime(adxValue: number): Regime {
    if (adxValue > 25) {
      return Regime.TRENDING
    } else if (adxValue < 20) {
      return Regime.RANGING
    } else {
      return Regime.TRANSITIONING
    }
  }

  private _atrPercentile(candles: OHLCV[], lookback = 100): number {
    const { highs, lows, closes } = extractArrays(candles)
    const atrValues = calcATR(highs, lows, closes, 14)

    if (atrValues.length < 2) {
      return 50.0
    }

    const tail = atrValues.slice(-lookback)
    const current = tail[tail.length - 1]
    const belowCount = tail.filter((v) => v < current).length
    return (belowCount / tail.length) * 100
  }
}
