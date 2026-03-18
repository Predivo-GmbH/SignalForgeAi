/**
 * Layer 2: Zone Identifier.
 *
 * Finds potential entry zones using Fibonacci retracement
 * and VWAP deviation bands.
 */

import { calcFibLevels, calcVWAP, extractArrays, type OHLCV } from '../indicators.ts'
import { Trend, type TrendResult } from './trend.ts'

// ── Entry Zone ─────────────────────────────────────────────────
export interface EntryZone {
  zoneType: string
  upper: number
  lower: number
  strength: number
  levels?: Record<string, number> | null
}

export function entryZoneToDict(zone: EntryZone): Record<string, unknown> {
  return {
    zone_type: zone.zoneType,
    upper: zone.upper,
    lower: zone.lower,
    strength: zone.strength,
  }
}

// ── Zone Identifier ────────────────────────────────────────────
export class ZoneIdentifier {
  findZones(candles: OHLCV[], trend: TrendResult): EntryZone[] {
    const zones: EntryZone[] = []
    zones.push(...this._fibonacciZones(candles, trend))
    zones.push(...this._vwapDeviationZones(candles))
    return zones
  }

  private _fibonacciZones(candles: OHLCV[], trend: TrendResult): EntryZone[] {
    const { highs, lows } = extractArrays(candles)

    // Find swing high and swing low
    let swingHigh = -Infinity
    let swingLow = Infinity
    for (const h of highs) {
      if (h > swingHigh) swingHigh = h
    }
    for (const l of lows) {
      if (l < swingLow) swingLow = l
    }

    if (swingHigh === swingLow) {
      return []
    }

    let fibLevels: Record<string, number>
    if (trend.direction === Trend.BULLISH) {
      fibLevels = calcFibLevels(swingHigh, swingLow)
    } else {
      // calcFibLevels(high, low) — for bearish, swap so retracements go the other direction
      fibLevels = calcFibLevels(swingLow, swingHigh)
    }

    let goldenUpper = fibLevels['0.382']
    let goldenLower = fibLevels['0.618']

    if (goldenUpper < goldenLower) {
      ;[goldenUpper, goldenLower] = [goldenLower, goldenUpper]
    }

    return [
      {
        zoneType: 'fibonacci_golden',
        upper: goldenUpper,
        lower: goldenLower,
        strength: 0.7,
        levels: fibLevels,
      },
    ]
  }

  private _vwapDeviationZones(candles: OHLCV[]): EntryZone[] {
    const { closes } = extractArrays(candles)
    const vwap = calcVWAP(candles)

    // Rolling 20-bar standard deviation of close
    if (closes.length < 20) {
      return []
    }

    const last20 = closes.slice(-20)
    const mean = last20.reduce((s, v) => s + v, 0) / last20.length
    const variance = last20.reduce((s, v) => s + (v - mean) ** 2, 0) / last20.length
    const stdVal = Math.sqrt(variance)

    if (isNaN(stdVal) || stdVal === 0) {
      return []
    }

    const vwapVal = vwap[vwap.length - 1]

    return [
      {
        zoneType: 'vwap_1sigma',
        upper: vwapVal + stdVal,
        lower: vwapVal - stdVal,
        strength: 0.5,
      },
      {
        zoneType: 'vwap_2sigma',
        upper: vwapVal + 2 * stdVal,
        lower: vwapVal - 2 * stdVal,
        strength: 0.8,
      },
    ]
  }
}
