/**
 * Layer 5: Risk Manager.
 *
 * Calculates position sizing, stop-loss, and take-profit levels
 * based on ATR, Fibonacci extensions, and confluence scoring.
 *
 * Key rules:
 *   - ATR-based stop loss: entry +/- ATR x multiplier
 *   - Fibonacci extension take profits: 161.8% and 261.8%
 *   - Minimum risk:reward check — reject if below threshold
 *   - Position sizing scaled by confluence score (50->0.5x, 100->1.0x)
 */

import { calcATR, extractArrays, type OHLCV } from '../indicators.ts'
import { Trend, type TrendResult } from './trend.ts'
import type { EntryZone } from './zones.ts'

// ── Risk config ────────────────────────────────────────────────
export interface RiskConfig {
  maxRiskPerTrade: number   // fraction of equity (default 0.02 = 2%)
  maxDailyLoss: number      // fraction of equity (default 0.06 = 6%)
  atrSlMultiplier: number   // ATR multiplier for stop-loss distance (default 2.0)
  minRiskReward: number     // minimum risk:reward ratio (default 1.5)
}

export const DEFAULT_RISK_CONFIG: RiskConfig = {
  maxRiskPerTrade: 0.02,
  maxDailyLoss: 0.06,
  atrSlMultiplier: 2.0,
  minRiskReward: 1.5,
}

// ── Risk calculation result ────────────────────────────────────
export interface RiskCalc {
  stopLoss: number
  takeProfit1: number
  takeProfit2: number
  positionSize: number
  riskAmount: number
  riskReward: number
  atrValue: number
  rejected: boolean
  rejectReason: string | null
}

// ── Risk Manager ───────────────────────────────────────────────
export class RiskManager {
  private config: RiskConfig

  constructor(config?: Partial<RiskConfig>) {
    this.config = { ...DEFAULT_RISK_CONFIG, ...config }
  }

  calculate(
    candles: OHLCV[],
    zone: EntryZone,
    trend: TrendResult,
    confluenceScore: number,
    accountEquity: number,
  ): RiskCalc {
    const entry = candles[candles.length - 1].close

    // ATR for volatility-based stop distance
    const { highs, lows, closes } = extractArrays(candles)
    const atrValues = calcATR(highs, lows, closes, 14)
    const atrValue = atrValues.length > 0 ? atrValues[atrValues.length - 1] : 0

    if (isNaN(atrValue) || atrValue <= 0) {
      return this._rejected('ATR is invalid or zero', entry, atrValue)
    }

    const slDistance = atrValue * this.config.atrSlMultiplier

    // Direction-specific levels
    // TP uses Fibonacci extension ratios applied to risk distance:
    //   TP1 = 1.618x risk distance (R:R = 1.618)
    //   TP2 = 2.618x risk distance (R:R = 2.618)
    let stopLoss: number
    let takeProfit1: number
    let takeProfit2: number

    if (trend.direction === Trend.BEARISH) {
      stopLoss = entry + slDistance
      takeProfit1 = entry - slDistance * 1.618
      takeProfit2 = entry - slDistance * 2.618
    } else {
      // Default to bullish for UNDETERMINED as well
      stopLoss = entry - slDistance
      takeProfit1 = entry + slDistance * 1.618
      takeProfit2 = entry + slDistance * 2.618
    }

    // Risk distance (always positive)
    const riskDistance = Math.abs(entry - stopLoss)
    if (riskDistance === 0) {
      return this._rejected('Risk distance is zero', entry, atrValue)
    }

    // Risk:reward ratio
    const rewardDistance = Math.abs(takeProfit1 - entry)
    const riskReward = rewardDistance / riskDistance

    // Reject if below minimum R:R
    if (riskReward < this.config.minRiskReward) {
      return {
        stopLoss,
        takeProfit1,
        takeProfit2,
        positionSize: 0,
        riskAmount: 0,
        riskReward,
        atrValue,
        rejected: true,
        rejectReason: `R:R ${riskReward.toFixed(2)} below minimum ${this.config.minRiskReward}`,
      }
    }

    // Confluence score multiplier: 50 -> 0.5x, 100 -> 1.0x (linear)
    const scoreMultiplier = Math.max(0.1, Math.min(1.0, confluenceScore / 100.0))

    // Position sizing: (equity * risk_pct * score_multiplier) / risk_distance
    const riskAmount = accountEquity * this.config.maxRiskPerTrade * scoreMultiplier
    const positionSize = riskAmount / riskDistance

    return {
      stopLoss,
      takeProfit1,
      takeProfit2,
      positionSize,
      riskAmount,
      riskReward,
      atrValue,
      rejected: false,
      rejectReason: null,
    }
  }

  private _rejected(reason: string, _entry: number, atrValue: number): RiskCalc {
    return {
      stopLoss: 0,
      takeProfit1: 0,
      takeProfit2: 0,
      positionSize: 0,
      riskAmount: 0,
      riskReward: 0,
      atrValue: isNaN(atrValue) ? 0 : atrValue,
      rejected: true,
      rejectReason: reason,
    }
  }
}
