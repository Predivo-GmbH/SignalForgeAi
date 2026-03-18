/**
 * Technical indicators wrapper.
 * Uses npm:technicalindicators for standard indicators + custom math for VWAP/Fibonacci.
 * Ports backend/app/engine/indicators.py to TypeScript.
 */

import {
  RSI, MACD, BollingerBands, Stochastic, EMA, SMA, ADX, ATR,
  OBV, WilliamsR, CCI, IchimokuCloud,
} from 'npm:technicalindicators@3'

export interface OHLCV {
  time: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

/** Calculate RSI */
export function calcRSI(closes: number[], period = 14): number[] {
  return RSI.calculate({ values: closes, period })
}

/** Calculate MACD */
export function calcMACD(closes: number[], fast = 12, slow = 26, signal = 9): Array<{
  MACD: number | undefined
  signal: number | undefined
  histogram: number | undefined
}> {
  return MACD.calculate({
    values: closes,
    fastPeriod: fast,
    slowPeriod: slow,
    signalPeriod: signal,
    SimpleMAOscillator: false,
    SimpleMASignal: false,
  })
}

/** Calculate Bollinger Bands */
export function calcBollingerBands(closes: number[], period = 20, stdDev = 2): Array<{
  upper: number
  middle: number
  lower: number
  pb: number
}> {
  return BollingerBands.calculate({ values: closes, period, stdDev })
}

/** Calculate Stochastic Oscillator */
export function calcStochastic(
  highs: number[], lows: number[], closes: number[], period = 14, signalPeriod = 3
): Array<{ k: number; d: number }> {
  return Stochastic.calculate({
    high: highs, low: lows, close: closes,
    period, signalPeriod,
  })
}

/** Calculate EMA */
export function calcEMA(values: number[], period: number): number[] {
  return EMA.calculate({ values, period })
}

/** Calculate SMA */
export function calcSMA(values: number[], period: number): number[] {
  return SMA.calculate({ values, period })
}

/** Calculate ADX */
export function calcADX(highs: number[], lows: number[], closes: number[], period = 14): Array<{
  adx: number
  ppiDI: number
  mdi: number
}> {
  return ADX.calculate({ high: highs, low: lows, close: closes, period })
}

/** Calculate ATR */
export function calcATR(highs: number[], lows: number[], closes: number[], period = 14): number[] {
  return ATR.calculate({ high: highs, low: lows, close: closes, period })
}

/** Calculate OBV */
export function calcOBV(closes: number[], volumes: number[]): number[] {
  return OBV.calculate({ close: closes, volume: volumes })
}

/** Calculate Williams %R */
export function calcWilliamsR(highs: number[], lows: number[], closes: number[], period = 14): number[] {
  return WilliamsR.calculate({ high: highs, low: lows, close: closes, period })
}

/** Calculate CCI */
export function calcCCI(highs: number[], lows: number[], closes: number[], period = 20): number[] {
  return CCI.calculate({ high: highs, low: lows, close: closes, period })
}

/** Calculate Ichimoku Cloud */
export function calcIchimoku(
  highs: number[], lows: number[], closes: number[],
  conversionPeriod = 9, basePeriod = 26, spanPeriod = 52, displacement = 26
): Array<{
  conversion: number
  base: number
  spanA: number
  spanB: number
}> {
  return IchimokuCloud.calculate({
    high: highs, low: lows, close: closes,
    conversionPeriod, basePeriod, spanPeriod, displacement,
  })
}

/** Calculate VWAP (custom implementation — not in technicalindicators) */
export function calcVWAP(candles: OHLCV[]): number[] {
  let cumulativeTPV = 0
  let cumulativeVolume = 0
  return candles.map((c) => {
    const tp = (c.high + c.low + c.close) / 3
    cumulativeTPV += tp * c.volume
    cumulativeVolume += c.volume
    return cumulativeVolume > 0 ? cumulativeTPV / cumulativeVolume : tp
  })
}

/** Calculate Fibonacci retracement levels */
export function calcFibLevels(high: number, low: number): Record<string, number> {
  const diff = high - low
  return {
    '0.0': high,
    '0.236': high - diff * 0.236,
    '0.382': high - diff * 0.382,
    '0.5': high - diff * 0.5,
    '0.618': high - diff * 0.618,
    '0.786': high - diff * 0.786,
    '1.0': low,
  }
}

/** Calculate Fibonacci extension levels for take profit */
export function calcFibExtensions(high: number, low: number, direction: 'BUY' | 'SELL'): Record<string, number> {
  const diff = high - low
  if (direction === 'BUY') {
    return {
      '1.272': high + diff * 0.272,
      '1.618': high + diff * 0.618,
      '2.0': high + diff,
      '2.618': high + diff * 1.618,
    }
  }
  return {
    '1.272': low - diff * 0.272,
    '1.618': low - diff * 0.618,
    '2.0': low - diff,
    '2.618': low - diff * 1.618,
  }
}

/** Extract arrays from OHLCV candle data */
export function extractArrays(candles: OHLCV[]): {
  opens: number[]; highs: number[]; lows: number[]; closes: number[]; volumes: number[]
} {
  return {
    opens: candles.map((c) => c.open),
    highs: candles.map((c) => c.high),
    lows: candles.map((c) => c.low),
    closes: candles.map((c) => c.close),
    volumes: candles.map((c) => c.volume),
  }
}
