/**
 * Layer 4: Trigger Detector.
 *
 * Checks for actionable entry triggers using multiple confirmation signals.
 * Requires a configurable number of trigger types to fire within a lookback
 * window for a confirmed entry.
 *
 * Trigger types:
 *   A. MACD crossover in trend direction
 *   B. RSI crossing midline (50)
 *   C. Stochastic leaving overbought/oversold
 *   D. Engulfing candlestick pattern
 *   E. Price reclaiming zone
 */

import {
  calcMACD, calcRSI, calcStochastic, extractArrays, type OHLCV,
} from '../indicators.ts'
import { Trend, type TrendResult } from './trend.ts'
import type { EntryZone } from './zones.ts'

// ── Trigger result ─────────────────────────────────────────────
export interface TriggerResult {
  confirmed: boolean
  price: number
  confirmations: string[]
}

// ── Trigger Detector ───────────────────────────────────────────
export class TriggerDetector {
  private minConfirmations: number
  private lookback: number

  constructor(minConfirmations = 2, lookback = 1) {
    this.minConfirmations = minConfirmations
    this.lookback = lookback
  }

  check(candles: OHLCV[], zone: EntryZone, trend: TrendResult): TriggerResult {
    const confirmations: string[] = []
    const price = candles[candles.length - 1].close

    if (this._checkMacdCrossover(candles, trend, this.lookback)) {
      confirmations.push('macd_crossover')
    }
    if (this._checkRsiMidline(candles, trend, this.lookback)) {
      confirmations.push('rsi_midline_cross')
    }
    if (this._checkStochasticExit(candles, trend, this.lookback)) {
      confirmations.push('stochastic_exit_extreme')
    }
    if (this._checkEngulfing(candles, trend, this.lookback)) {
      confirmations.push('engulfing_candle')
    }
    if (this._checkZoneReclaim(candles, zone, trend, this.lookback)) {
      confirmations.push('zone_reclaim')
    }

    return {
      confirmed: confirmations.length >= this.minConfirmations,
      price,
      confirmations,
    }
  }

  // ── Trigger A: MACD crossover ────────────────────────────────
  private _checkMacdCrossover(
    candles: OHLCV[], trend: TrendResult, lookback: number,
  ): boolean {
    if (candles.length < 35) return false

    const { closes } = extractArrays(candles)
    const macd = calcMACD(closes)

    for (let offset = 0; offset < lookback; offset++) {
      const idx = macd.length - 1 - offset
      const prevIdx = idx - 1
      if (prevIdx < 0) break

      const curMacd = macd[idx].MACD
      const prevMacd = macd[prevIdx].MACD
      const curSignal = macd[idx].signal
      const prevSignal = macd[prevIdx].signal

      if (
        curMacd === undefined || prevMacd === undefined ||
        curSignal === undefined || prevSignal === undefined
      ) continue

      if (trend.direction === Trend.BULLISH) {
        if (prevMacd <= prevSignal && curMacd > curSignal) return true
      } else if (trend.direction === Trend.BEARISH) {
        if (prevMacd >= prevSignal && curMacd < curSignal) return true
      }
    }
    return false
  }

  // ── Trigger B: RSI crossing midline (50) ─────────────────────
  private _checkRsiMidline(
    candles: OHLCV[], trend: TrendResult, lookback: number,
  ): boolean {
    if (candles.length < 20) return false

    const { closes } = extractArrays(candles)
    const rsi = calcRSI(closes, 14)

    for (let offset = 0; offset < lookback; offset++) {
      const idx = rsi.length - 1 - offset
      const prevIdx = idx - 1
      if (prevIdx < 0) break

      const curRsi = rsi[idx]
      const prevRsi = rsi[prevIdx]

      if (curRsi === undefined || prevRsi === undefined) continue
      if (isNaN(curRsi) || isNaN(prevRsi)) continue

      if (trend.direction === Trend.BULLISH) {
        if (prevRsi <= 50 && curRsi > 50) return true
      } else if (trend.direction === Trend.BEARISH) {
        if (prevRsi >= 50 && curRsi < 50) return true
      }
    }
    return false
  }

  // ── Trigger C: Stochastic leaving overbought/oversold ────────
  private _checkStochasticExit(
    candles: OHLCV[], trend: TrendResult, lookback: number,
  ): boolean {
    if (candles.length < 20) return false

    const { highs, lows, closes } = extractArrays(candles)
    const stoch = calcStochastic(highs, lows, closes)

    for (let offset = 0; offset < lookback; offset++) {
      const idx = stoch.length - 1 - offset
      const prevIdx = idx - 1
      if (prevIdx < 0) break

      const curK = stoch[idx].k
      const prevK = stoch[prevIdx].k

      if (curK === undefined || prevK === undefined) continue

      if (trend.direction === Trend.BULLISH) {
        if (prevK <= 20 && curK > 20) return true
      } else if (trend.direction === Trend.BEARISH) {
        if (prevK >= 80 && curK < 80) return true
      }
    }
    return false
  }

  // ── Trigger D: Engulfing candlestick pattern ─────────────────
  private _checkEngulfing(
    candles: OHLCV[], trend: TrendResult, lookback: number,
  ): boolean {
    if (candles.length < 2) return false

    for (let offset = 0; offset < lookback; offset++) {
      const idx = candles.length - 1 - offset
      const prevIdx = idx - 1
      if (prevIdx < 0) break

      const prev = candles[prevIdx]
      const cur = candles[idx]

      if (trend.direction === Trend.BULLISH) {
        const prevBearish = prev.close < prev.open
        const curBullish = cur.close > cur.open
        const engulfs = cur.open <= prev.close && cur.close >= prev.open
        if (prevBearish && curBullish && engulfs) return true
      } else if (trend.direction === Trend.BEARISH) {
        const prevBullish = prev.close > prev.open
        const curBearish = cur.close < cur.open
        const engulfs = cur.open >= prev.close && cur.close <= prev.open
        if (prevBullish && curBearish && engulfs) return true
      }
    }
    return false
  }

  // ── Trigger E: Price reclaiming zone ─────────────────────────
  private _checkZoneReclaim(
    candles: OHLCV[], zone: EntryZone, trend: TrendResult, lookback: number,
  ): boolean {
    if (candles.length < 2) return false

    for (let offset = 0; offset < lookback; offset++) {
      const idx = candles.length - 1 - offset
      const prevIdx = idx - 1
      if (prevIdx < 0) break

      const prevClose = candles[prevIdx].close
      const curClose = candles[idx].close

      if (trend.direction === Trend.BULLISH) {
        if (prevClose < zone.lower && curClose >= zone.lower) return true
      } else if (trend.direction === Trend.BEARISH) {
        if (prevClose > zone.upper && curClose <= zone.upper) return true
      }
    }
    return false
  }
}
