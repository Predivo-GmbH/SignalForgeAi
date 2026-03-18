/**
 * Layer 3: Confluence Scorer.
 *
 * Scores an entry zone 0-100 using 14 weighted factors that measure
 * alignment between technical indicators and the identified zone.
 */

import {
  calcBollingerBands, calcCCI, calcIchimoku, calcMACD, calcOBV,
  calcRSI, calcSMA, calcStochastic, calcVWAP, calcWilliamsR,
  extractArrays, type OHLCV,
} from '../indicators.ts'
import { Trend, type TrendResult } from './trend.ts'
import type { EntryZone } from './zones.ts'

// ── Types ──────────────────────────────────────────────────────
interface FactorDetail {
  hit: boolean
  weight: number
  earned: number
  [key: string]: unknown
}

export type ConfluenceDetails = Record<string, FactorDetail>

// ── Confluence Scorer ──────────────────────────────────────────
export class ConfluenceScorer {
  static readonly WEIGHTS: Record<string, number> = {
    fibonacci_alignment: 12,
    sr_overlap: 12,
    multi_tf_fib: 10,
    vwap_proximity: 8,
    volume_node: 8,
    rsi_confirmation: 8,
    macd_momentum: 8,
    candlestick_pattern: 7,
    stochastic_cross: 5,
    bollinger_position: 5,
    ichimoku_cloud: 5,
    obv_trend: 5,
    williams_r_extreme: 4,
    cci_momentum: 3,
  }

  score(zone: EntryZone, candles: OHLCV[], trend: TrendResult): number {
    const [total] = this.scoreWithDetails(zone, candles, trend)
    return total
  }

  scoreWithDetails(
    zone: EntryZone, candles: OHLCV[], trend: TrendResult,
  ): [number, ConfluenceDetails] {
    const details: ConfluenceDetails = {}
    let total = 0

    const checks: Record<string, (z: EntryZone, c: OHLCV[], t: TrendResult) => [boolean, Record<string, unknown>]> = {
      fibonacci_alignment: this._checkFibonacciAlignment.bind(this),
      sr_overlap: this._checkSrOverlap.bind(this),
      multi_tf_fib: this._checkMultiTfFib.bind(this),
      vwap_proximity: this._checkVwapProximity.bind(this),
      volume_node: this._checkVolumeNode.bind(this),
      rsi_confirmation: this._checkRsiConfirmation.bind(this),
      macd_momentum: this._checkMacdMomentum.bind(this),
      candlestick_pattern: this._checkCandlestickPattern.bind(this),
      stochastic_cross: this._checkStochasticCross.bind(this),
      bollinger_position: this._checkBollingerPosition.bind(this),
      ichimoku_cloud: this._checkIchimokuCloud.bind(this),
      obv_trend: this._checkObvTrend.bind(this),
      williams_r_extreme: this._checkWilliamsRExtreme.bind(this),
      cci_momentum: this._checkCciMomentum.bind(this),
    }

    for (const [factor, checkFn] of Object.entries(checks)) {
      const weight = ConfluenceScorer.WEIGHTS[factor]
      const [hit, info] = checkFn(zone, candles, trend)
      const earned = hit ? weight : 0
      total += earned
      details[factor] = { hit, weight, earned, ...info }
    }

    total = Math.max(0, Math.min(100, total))
    return [total, details]
  }

  // ── Factor checks ──────────────────────────────────────────

  private _checkFibonacciAlignment(
    zone: EntryZone, _candles: OHLCV[], _trend: TrendResult,
  ): [boolean, Record<string, unknown>] {
    const hit = zone.zoneType.startsWith('fibonacci')
    return [hit, { zone_type: zone.zoneType }]
  }

  private _checkSrOverlap(
    zone: EntryZone, candles: OHLCV[], _trend: TrendResult,
  ): [boolean, Record<string, unknown>] {
    const recent = candles.slice(-20)
    const zoneWidth = zone.upper - zone.lower
    if (zoneWidth === 0) return [false, { bounces: 0 }]

    let bounces = 0
    for (const c of recent) {
      if (c.close >= zone.lower && c.close <= zone.upper) bounces++
    }
    const hit = bounces >= 3
    return [hit, { bounces }]
  }

  private _checkMultiTfFib(
    zone: EntryZone, _candles: OHLCV[], _trend: TrendResult,
  ): [boolean, Record<string, unknown>] {
    const hit = zone.strength >= 0.7
    return [hit, { zone_strength: zone.strength }]
  }

  private _checkVwapProximity(
    zone: EntryZone, candles: OHLCV[], _trend: TrendResult,
  ): [boolean, Record<string, unknown>] {
    const vwap = calcVWAP(candles)
    const vwapVal = vwap[vwap.length - 1]
    const inZone = zone.lower <= vwapVal && vwapVal <= zone.upper
    return [inZone, { vwap: vwapVal, in_zone: inZone }]
  }

  private _checkVolumeNode(
    zone: EntryZone, candles: OHLCV[], _trend: TrendResult,
  ): [boolean, Record<string, unknown>] {
    const totalVol = candles.reduce((s, c) => s + c.volume, 0)
    const avgTotalVol = totalVol / candles.length

    const inZone = candles.filter((c) => c.close >= zone.lower && c.close <= zone.upper)
    if (inZone.length === 0) {
      return [false, { avg_zone_vol: 0, avg_total_vol: avgTotalVol }]
    }

    const avgZoneVol = inZone.reduce((s, c) => s + c.volume, 0) / inZone.length
    const hit = avgZoneVol > avgTotalVol * 1.2
    return [hit, { avg_zone_vol: avgZoneVol, avg_total_vol: avgTotalVol }]
  }

  private _checkRsiConfirmation(
    zone: EntryZone, candles: OHLCV[], trend: TrendResult,
  ): [boolean, Record<string, unknown>] {
    const { closes } = extractArrays(candles)
    const rsi = calcRSI(closes, 14)
    const rsiVal = rsi.length > 0 ? rsi[rsi.length - 1] : 50.0

    let hit = false
    if (trend.direction === Trend.BULLISH) {
      hit = rsiVal >= 35 && rsiVal <= 65
    } else if (trend.direction === Trend.BEARISH) {
      hit = rsiVal >= 35 && rsiVal <= 65
    }

    return [hit, { rsi: rsiVal, trend: trend.direction }]
  }

  private _checkMacdMomentum(
    zone: EntryZone, candles: OHLCV[], trend: TrendResult,
  ): [boolean, Record<string, unknown>] {
    const { closes } = extractArrays(candles)
    const macd = calcMACD(closes)
    // Filter to entries with histogram defined
    const histValues = macd
      .map((m) => m.histogram)
      .filter((h): h is number => h !== undefined)

    if (histValues.length < 2) {
      return [false, { histogram: 0, rising: false }]
    }

    const histVal = histValues[histValues.length - 1]
    const histPrev = histValues[histValues.length - 2]
    const rising = histVal > histPrev

    let hit = false
    if (trend.direction === Trend.BULLISH) {
      hit = histVal > 0 || rising
    } else if (trend.direction === Trend.BEARISH) {
      hit = histVal < 0 || !rising
    }

    return [hit, { histogram: histVal, rising }]
  }

  private _checkCandlestickPattern(
    _zone: EntryZone, candles: OHLCV[], trend: TrendResult,
  ): [boolean, Record<string, unknown>] {
    if (candles.length < 3) return [false, { pattern: 'none' }]

    const last = candles[candles.length - 1]
    const prev = candles[candles.length - 2]
    const body = Math.abs(last.close - last.open)
    const upperWick = last.high - Math.max(last.close, last.open)
    const lowerWick = Math.min(last.close, last.open) - last.low
    const candleRange = last.high - last.low

    if (candleRange === 0) return [false, { pattern: 'none' }]

    // Hammer (bullish reversal): small body, long lower wick
    const isHammer =
      lowerWick > body * 2 &&
      upperWick < body * 0.5 &&
      trend.direction === Trend.BULLISH

    // Engulfing patterns
    const prevBody = Math.abs(prev.close - prev.open)
    const isBullishEngulfing =
      last.close > last.open &&
      prev.close < prev.open &&
      body > prevBody &&
      trend.direction === Trend.BULLISH
    const isBearishEngulfing =
      last.close < last.open &&
      prev.close > prev.open &&
      body > prevBody &&
      trend.direction === Trend.BEARISH

    if (isHammer) return [true, { pattern: 'hammer' }]
    if (isBullishEngulfing) return [true, { pattern: 'bullish_engulfing' }]
    if (isBearishEngulfing) return [true, { pattern: 'bearish_engulfing' }]

    return [false, { pattern: 'none' }]
  }

  private _checkStochasticCross(
    _zone: EntryZone, candles: OHLCV[], trend: TrendResult,
  ): [boolean, Record<string, unknown>] {
    const { highs, lows, closes } = extractArrays(candles)
    const stoch = calcStochastic(highs, lows, closes)

    if (stoch.length < 2) return [false, { slow_k: 0, slow_d: 0 }]

    const kNow = stoch[stoch.length - 1].k
    const dNow = stoch[stoch.length - 1].d
    const kPrev = stoch[stoch.length - 2].k
    const dPrev = stoch[stoch.length - 2].d

    // Bullish: %K crosses above %D, or %K rising in lower half
    const bullish =
      (kPrev < dPrev && kNow > dNow && kNow < 50) ||
      (kNow > kPrev && kNow < 50)
    // Bearish: %K crosses below %D, or %K falling in upper half
    const bearish =
      (kPrev > dPrev && kNow < dNow && kNow > 50) ||
      (kNow < kPrev && kNow > 50)

    let hit = false
    if (trend.direction === Trend.BULLISH) hit = bullish
    else if (trend.direction === Trend.BEARISH) hit = bearish

    return [hit, { slow_k: kNow, slow_d: dNow }]
  }

  private _checkBollingerPosition(
    _zone: EntryZone, candles: OHLCV[], trend: TrendResult,
  ): [boolean, Record<string, unknown>] {
    const { closes } = extractArrays(candles)
    const bb = calcBollingerBands(closes)

    if (bb.length === 0) return [false, { bb_position: 'unknown' }]

    const price = closes[closes.length - 1]
    const upperVal = bb[bb.length - 1].upper
    const lowerVal = bb[bb.length - 1].lower
    const bandWidth = upperVal - lowerVal

    if (bandWidth === 0) return [false, { bb_position: 'flat' }]

    const bbPct = (price - lowerVal) / bandWidth

    let hit = false
    if (trend.direction === Trend.BULLISH) {
      hit = bbPct < 0.3
    } else if (trend.direction === Trend.BEARISH) {
      hit = bbPct > 0.7
    }

    return [hit, { bb_pct: Math.round(bbPct * 1000) / 1000, upper: upperVal, lower: lowerVal }]
  }

  private _checkIchimokuCloud(
    _zone: EntryZone, candles: OHLCV[], trend: TrendResult,
  ): [boolean, Record<string, unknown>] {
    const { highs, lows, closes } = extractArrays(candles)
    const ichi = calcIchimoku(highs, lows, closes)

    if (ichi.length === 0) {
      return [false, { cloud_position: 'insufficient_data' }]
    }

    const price = closes[closes.length - 1]
    const lastIchi = ichi[ichi.length - 1]
    const cloudTop = Math.max(lastIchi.spanA, lastIchi.spanB)
    const cloudBottom = Math.min(lastIchi.spanA, lastIchi.spanB)

    let hit = false
    let pos = 'inside'
    if (trend.direction === Trend.BULLISH) {
      hit = price > cloudTop
      pos = 'above'
    } else if (trend.direction === Trend.BEARISH) {
      hit = price < cloudBottom
      pos = 'below'
    } else {
      pos = cloudBottom <= price && price <= cloudTop ? 'inside' : 'outside'
    }

    return [hit, { cloud_position: pos, cloud_top: cloudTop, cloud_bottom: cloudBottom }]
  }

  private _checkObvTrend(
    _zone: EntryZone, candles: OHLCV[], trend: TrendResult,
  ): [boolean, Record<string, unknown>] {
    const { closes, volumes } = extractArrays(candles)
    const obv = calcOBV(closes, volumes)

    if (obv.length < 20) return [false, { obv_slope: 0 }]

    // OBV 20-period moving average
    const obvMa = calcSMA(obv, 20)
    if (obvMa.length < 5) return [false, { obv_slope: 0 }]

    const obvSlope = obvMa[obvMa.length - 1] - obvMa[obvMa.length - 5]

    let hit = false
    if (trend.direction === Trend.BULLISH) {
      hit = obvSlope > 0
    } else if (trend.direction === Trend.BEARISH) {
      hit = obvSlope < 0
    }

    return [hit, { obv_slope: Math.round(obvSlope * 100) / 100 }]
  }

  private _checkWilliamsRExtreme(
    _zone: EntryZone, candles: OHLCV[], trend: TrendResult,
  ): [boolean, Record<string, unknown>] {
    const { highs, lows, closes } = extractArrays(candles)
    const wr = calcWilliamsR(highs, lows, closes)

    if (wr.length === 0) return [false, { williams_r: -50 }]

    const wrVal = wr[wr.length - 1]

    let hit = false
    if (trend.direction === Trend.BULLISH) {
      hit = wrVal < -30
    } else if (trend.direction === Trend.BEARISH) {
      hit = wrVal > -70
    }

    return [hit, { williams_r: Math.round(wrVal * 100) / 100 }]
  }

  private _checkCciMomentum(
    _zone: EntryZone, candles: OHLCV[], trend: TrendResult,
  ): [boolean, Record<string, unknown>] {
    const { highs, lows, closes } = extractArrays(candles)
    const cci = calcCCI(highs, lows, closes)

    if (cci.length === 0) return [false, { cci: 0 }]

    const cciVal = cci[cci.length - 1]

    let hit = false
    if (trend.direction === Trend.BULLISH) {
      hit = cciVal > -50
    } else if (trend.direction === Trend.BEARISH) {
      hit = cciVal < 50
    }

    return [hit, { cci: Math.round(cciVal * 100) / 100 }]
  }
}
