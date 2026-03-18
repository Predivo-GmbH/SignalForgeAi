/**
 * Layer 6: Reversal Monitor.
 *
 * Monitors open positions for trend-reversal signals and recommends
 * exit actions (hold, partial close, tighten stop, or full close)
 * based on aggregated severity of reversal indicators.
 *
 * Indicators checked:
 *   - EMA 10/20 crossover against position direction
 *   - Volume divergence (declining volume against trend)
 *   - MACD histogram divergence (weakening momentum)
 *
 * Severity aggregation:
 *   - max severity >= 0.8  -> CLOSE_POSITION
 *   - max severity >= 0.6  -> TIGHTEN_STOP
 *   - max severity >= 0.4 AND 2+ alerts -> PARTIAL_CLOSE
 *   - else -> HOLD
 */

import { calcEMA, calcMACD, extractArrays, type OHLCV } from '../indicators.ts'

// ── Reversal Action ────────────────────────────────────────────
export const ReversalAction = {
  HOLD: 'hold',
  PARTIAL_CLOSE: 'partial_close',
  TIGHTEN_STOP: 'tighten_stop',
  CLOSE_POSITION: 'close_position',
} as const

export type ReversalAction = (typeof ReversalAction)[keyof typeof ReversalAction]

// ── Reversal Monitor ───────────────────────────────────────────
export class ReversalMonitor {
  checkPosition(candles: OHLCV[], direction: 'LONG' | 'SHORT'): ReversalAction {
    const alerts: Array<[string, number]> = []

    const emaSeverity = this._checkEmaCross(candles, direction)
    if (emaSeverity > 0) alerts.push(['ema_cross', emaSeverity])

    const volSeverity = this._checkVolumeDivergence(candles, direction)
    if (volSeverity > 0) alerts.push(['volume_divergence', volSeverity])

    const macdSeverity = this._checkMacdDivergence(candles, direction)
    if (macdSeverity > 0) alerts.push(['macd_divergence', macdSeverity])

    return this._aggregate(alerts)
  }

  private _checkEmaCross(candles: OHLCV[], direction: string): number {
    const { closes } = extractArrays(candles)
    if (closes.length < 20) return 0.0

    const ema10 = calcEMA(closes, 10)
    const ema20 = calcEMA(closes, 20)

    const fast = ema10[ema10.length - 1]
    const slow = ema20[ema20.length - 1]

    if (direction === 'LONG' && fast < slow) return 0.5
    if (direction === 'SHORT' && fast > slow) return 0.5

    return 0.0
  }

  private _checkVolumeDivergence(candles: OHLCV[], direction: string): number {
    if (candles.length < 30) return 0.0

    const recentVols = candles.slice(-10).map((c) => c.volume)
    const priorVols = candles.slice(-30, -10).map((c) => c.volume)

    const recentVol = recentVols.reduce((s, v) => s + v, 0) / recentVols.length
    const priorVol = priorVols.reduce((s, v) => s + v, 0) / priorVols.length

    if (priorVol === 0) return 0.0

    const volRatio = recentVol / priorVol

    // Check if price is still moving in position direction
    const recentPriceChange =
      candles[candles.length - 1].close - candles[candles.length - 10].close

    if (direction === 'LONG' && recentPriceChange > 0 && volRatio < 0.6) {
      return 0.4
    }
    if (direction === 'SHORT' && recentPriceChange < 0 && volRatio < 0.6) {
      return 0.4
    }

    return 0.0
  }

  private _checkMacdDivergence(candles: OHLCV[], direction: string): number {
    const { closes } = extractArrays(candles)
    if (closes.length < 35) return 0.0

    const macd = calcMACD(closes)
    const histValues = macd
      .map((m) => m.histogram)
      .filter((h): h is number => h !== undefined)

    if (histValues.length < 5) return 0.0

    const currentHist = histValues[histValues.length - 1]

    // Normalize histogram against price to avoid false signals from noise
    const price = closes[closes.length - 1]
    const normalizedHist = price > 0 ? Math.abs(currentHist) / price : 0.0

    // Require histogram to be at least 0.05% of price to be meaningful
    const significanceThreshold = 0.0005

    if (direction === 'LONG' && currentHist < 0 && normalizedHist > significanceThreshold) {
      return 0.7
    }
    if (direction === 'SHORT' && currentHist > 0 && normalizedHist > significanceThreshold) {
      return 0.7
    }

    // Check for declining histogram momentum (weakening trend)
    const recentHist = histValues.slice(-5)
    const histSlope = recentHist[recentHist.length - 1] - recentHist[0]

    if (direction === 'LONG' && histSlope < 0 && currentHist > 0) {
      const decliningRatio = Math.abs(histSlope) / Math.max(Math.abs(currentHist), 1e-10)
      if (decliningRatio > 1.0) return 0.4
    } else if (direction === 'SHORT' && histSlope > 0 && currentHist < 0) {
      const decliningRatio = Math.abs(histSlope) / Math.max(Math.abs(currentHist), 1e-10)
      if (decliningRatio > 1.0) return 0.4
    }

    return 0.0
  }

  private _aggregate(alerts: Array<[string, number]>): ReversalAction {
    if (alerts.length === 0) return ReversalAction.HOLD

    const maxSeverity = Math.max(...alerts.map(([, s]) => s))
    const alertCount = alerts.length

    if (maxSeverity >= 0.8) return ReversalAction.CLOSE_POSITION
    if (maxSeverity >= 0.6) return ReversalAction.TIGHTEN_STOP
    if (maxSeverity >= 0.4 && alertCount >= 2) return ReversalAction.PARTIAL_CLOSE

    return ReversalAction.HOLD
  }
}
