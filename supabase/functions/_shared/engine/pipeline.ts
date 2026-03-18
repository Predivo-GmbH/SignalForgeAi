/**
 * SignalPipeline: Orchestrates all 6 layers to produce a trade signal.
 *
 * Pipeline flow:
 *   Layer 0: RegimeDetector   -> CHAOTIC blocks
 *   Layer 1: TrendFilter      -> UNDETERMINED blocks
 *   Layer 2: ZoneIdentifier   -> no zones blocks
 *   Layer 3: ConfluenceScorer -> score < 50 blocks
 *   Layer 4: TriggerDetector  -> not confirmed blocks
 *   Layer 5: RiskManager      -> rejected blocks
 *   -> Output: Signal with action BUY/SELL/NO_TRADE
 */

import type { OHLCV } from '../indicators.ts'
import { ConfluenceScorer, type ConfluenceDetails } from './confluence.ts'
import { Regime, RegimeDetector } from './regime.ts'
import { RiskManager, type RiskConfig } from './risk.ts'
import { Trend, TrendFilter } from './trend.ts'
import { TriggerDetector } from './triggers.ts'
import { ZoneIdentifier, entryZoneToDict } from './zones.ts'

// ── Signal output ──────────────────────────────────────────────
export interface Signal {
  symbol: string
  timeframe: string
  action: 'BUY' | 'SELL' | 'NO_TRADE'
  regime: string
  trendDirection: string
  trendStrength: number
  zone: Record<string, unknown> | null
  confluenceScore: number
  triggers: string[]
  stopLoss: number | null
  takeProfit1: number | null
  takeProfit2: number | null
  positionSize: number | null
  riskReward: number | null
  blockReason: string | null
  timestamp: string
  confluenceDetails: ConfluenceDetails | null
}

// ── Pipeline options ───────────────────────────────────────────
export interface PipelineOptions {
  riskConfig?: Partial<RiskConfig>
  minConfluence?: number
  minTriggerCount?: number
  triggerLookbackCandles?: number
  emaSlopeThreshold?: number
}

// ── Signal Pipeline ────────────────────────────────────────────
export class SignalPipeline {
  private regimeDetector: RegimeDetector
  private trendFilter: TrendFilter
  private zoneIdentifier: ZoneIdentifier
  private confluenceScorer: ConfluenceScorer
  private triggerDetector: TriggerDetector
  private riskManager: RiskManager
  private minConfluence: number

  constructor(opts: PipelineOptions = {}) {
    this.regimeDetector = new RegimeDetector()
    this.trendFilter = new TrendFilter(opts.emaSlopeThreshold ?? 0.001)
    this.zoneIdentifier = new ZoneIdentifier()
    this.confluenceScorer = new ConfluenceScorer()
    this.triggerDetector = new TriggerDetector(
      opts.minTriggerCount ?? 2,
      opts.triggerLookbackCandles ?? 1,
    )
    this.riskManager = new RiskManager(opts.riskConfig)
    this.minConfluence = opts.minConfluence ?? 50
  }

  process(
    symbol: string,
    timeframe: string,
    candles: OHLCV[],
    accountEquity = 10000,
  ): Signal {
    const now = new Date().toISOString()

    // Layer 0: Regime detection
    const regime = this.regimeDetector.detect(candles)
    if (regime === Regime.CHAOTIC) {
      return this._noTrade(symbol, timeframe, regime, 'chaotic_regime', now)
    }

    // Layer 1: Trend filter
    const trend = this.trendFilter.evaluate(candles)
    if (trend.direction === Trend.UNDETERMINED) {
      return this._noTrade(
        symbol, timeframe, regime, 'no_trend', now,
        trend.direction, trend.strength,
      )
    }

    // Layer 2: Zone identification
    const zones = this.zoneIdentifier.findZones(candles, trend)
    if (zones.length === 0) {
      return this._noTrade(
        symbol, timeframe, regime, 'no_zones', now,
        trend.direction, trend.strength,
      )
    }

    // Evaluate each zone through Layers 3-5, pick the best
    let bestSignal: Signal | null = null
    let bestScore = -1
    let lastBlockReason = 'no_zones'

    for (const zone of zones) {
      // Layer 3: Confluence scoring
      const [confluenceScore, details] = this.confluenceScorer.scoreWithDetails(
        zone, candles, trend,
      )
      if (confluenceScore < this.minConfluence) {
        lastBlockReason = 'low_confluence'
        continue
      }

      // Layer 4: Trigger detection
      const trigger = this.triggerDetector.check(candles, zone, trend)
      if (!trigger.confirmed) {
        lastBlockReason = 'no_trigger'
        continue
      }

      // Layer 5: Risk management
      const risk = this.riskManager.calculate(
        candles, zone, trend, confluenceScore, accountEquity,
      )
      if (risk.rejected) {
        lastBlockReason = `risk_rejected:${risk.rejectReason}`
        continue
      }

      // Valid signal found — track the best by confluence score
      if (confluenceScore > bestScore) {
        bestScore = confluenceScore
        const action = trend.direction === Trend.BULLISH ? 'BUY' : 'SELL'
        bestSignal = {
          symbol,
          timeframe,
          action: action as 'BUY' | 'SELL',
          regime,
          trendDirection: trend.direction,
          trendStrength: trend.strength,
          zone: entryZoneToDict(zone),
          confluenceScore,
          triggers: trigger.confirmations,
          stopLoss: risk.stopLoss,
          takeProfit1: risk.takeProfit1,
          takeProfit2: risk.takeProfit2,
          positionSize: risk.positionSize,
          riskReward: risk.riskReward,
          blockReason: null,
          timestamp: now,
          confluenceDetails: details,
        }
      }
    }

    if (bestSignal !== null) {
      return bestSignal
    }

    // No zone passed all layers
    return this._noTrade(
      symbol, timeframe, regime, lastBlockReason, now,
      trend.direction, trend.strength,
    )
  }

  private _noTrade(
    symbol: string,
    timeframe: string,
    regime: string,
    blockReason: string,
    timestamp: string,
    trendDirection = 'undetermined',
    trendStrength = 0.0,
  ): Signal {
    return {
      symbol,
      timeframe,
      action: 'NO_TRADE',
      regime,
      trendDirection,
      trendStrength,
      zone: null,
      confluenceScore: 0,
      triggers: [],
      stopLoss: null,
      takeProfit1: null,
      takeProfit2: null,
      positionSize: null,
      riskReward: null,
      blockReason,
      timestamp,
      confluenceDetails: null,
    }
  }
}
