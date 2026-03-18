/**
 * Layer 1: Trend Filter.
 *
 * Determines dominant trend direction using EMA alignment (50/100/200)
 * and slope of the 200 EMA.
 */

import { calcEMA, calcVWAP, extractArrays, type OHLCV } from '../indicators.ts'

// ── Trend enum ─────────────────────────────────────────────────
export const Trend = {
  BULLISH: 'bullish',
  BEARISH: 'bearish',
  UNDETERMINED: 'undetermined',
} as const

export type Trend = (typeof Trend)[keyof typeof Trend]

// ── Trend result ───────────────────────────────────────────────
export interface TrendResult {
  direction: Trend
  strength: number
  vwapAligned: boolean | null
}

// ── Trend Filter ───────────────────────────────────────────────
export class TrendFilter {
  private slopeThreshold: number

  constructor(slopeThreshold = 0.001) {
    this.slopeThreshold = slopeThreshold
  }

  evaluate(candles: OHLCV[]): TrendResult {
    const { closes } = extractArrays(candles)

    if (closes.length < 200) {
      return { direction: Trend.UNDETERMINED, strength: 0, vwapAligned: null }
    }

    const ema200 = calcEMA(closes, 200)
    const ema100 = calcEMA(closes, 100)
    const ema50 = calcEMA(closes, 50)

    const ema50Last = ema50[ema50.length - 1]
    const ema100Last = ema100[ema100.length - 1]
    const ema200Last = ema200[ema200.length - 1]

    const emaAlignedBull = ema50Last > ema100Last && ema100Last > ema200Last
    const emaAlignedBear = ema50Last < ema100Last && ema100Last < ema200Last

    // Trend strength via slope of 200 EMA (last 20 bars)
    const ema200Prev20 = ema200.length >= 20 ? ema200[ema200.length - 20] : ema200Last
    let emaSlope = 0
    if (ema200Prev20 !== 0) {
      emaSlope = (ema200Last - ema200Prev20) / Math.abs(ema200Prev20)
    }

    // VWAP alignment
    const vwap = calcVWAP(candles)
    const aboveVwap = closes[closes.length - 1] > vwap[vwap.length - 1]

    if (emaAlignedBull && emaSlope > this.slopeThreshold) {
      return {
        direction: Trend.BULLISH,
        strength: Math.abs(emaSlope),
        vwapAligned: aboveVwap,
      }
    } else if (emaAlignedBear && emaSlope < -this.slopeThreshold) {
      return {
        direction: Trend.BEARISH,
        strength: Math.abs(emaSlope),
        vwapAligned: !aboveVwap,
      }
    } else {
      return {
        direction: Trend.UNDETERMINED,
        strength: 0,
        vwapAligned: null,
      }
    }
  }
}
