/**
 * Market Scanner — discovers and ranks top crypto pairs by volume.
 *
 * Ported from backend/app/advisor/scanner.py
 */

import { getExchange, fetchCandles, type CandleData } from '../ccxt.ts'

// ---------- Constants ----------

const EXCLUDE_BASES = new Set([
  'USDC', 'BUSD', 'TUSD', 'DAI', 'FDUSD', 'USDP', 'UST',
  'WBTC', 'WETH', 'STETH',
])

// ---------- Types ----------

export interface ScannedPair {
  symbol: string
  price: number
  volume_24h: number
  change_pct_24h: number
  rank?: number
}

// ---------- Public API ----------

/**
 * Fetch all USDT pairs, rank by 24h quote volume, return top N.
 *
 * Any pair with < $1M 24h volume is excluded to ensure sufficient
 * liquidity for buy/sell orders to fill without slippage issues.
 */
export async function scanTopPairs(
  exchangeId = 'binance',
  quote = 'USDT',
  topN = 100,
): Promise<ScannedPair[]> {
  const exchange = getExchange(exchangeId)
  console.log(`Loading markets from ${exchangeId}...`)
  await exchange.loadMarkets()

  // Build set of valid USDT spot pairs, excluding stablecoins
  const usdtSymbols = new Set<string>()
  for (const [symbol, market] of Object.entries(exchange.markets)) {
    if (
      market.quote === quote &&
      market.spot === true &&
      market.active !== false &&
      !EXCLUDE_BASES.has(market.base ?? '')
    ) {
      usdtSymbols.add(symbol)
    }
  }

  console.log(`Found ${usdtSymbols.size} ${quote} spot pairs, fetching tickers...`)

  // Fetch ALL tickers at once (single API call)
  const allTickers = await exchange.fetchTickers()

  const pairs: ScannedPair[] = []
  for (const [symbol, ticker] of Object.entries(allTickers)) {
    if (!usdtSymbols.has(symbol)) continue
    const quoteVolume = ticker.quoteVolume ?? 0
    if (quoteVolume < 1_000_000) continue // Skip pairs with < $1M daily volume
    pairs.push({
      symbol,
      price: ticker.last ?? 0,
      volume_24h: quoteVolume,
      change_pct_24h: ticker.percentage ?? 0,
    })
  }

  // Sort by volume descending
  pairs.sort((a, b) => b.volume_24h - a.volume_24h)

  // Add rank
  const result = pairs.slice(0, topN)
  for (let i = 0; i < result.length; i++) {
    result[i].rank = i + 1
  }

  console.log(
    `Top ${result.length} pairs by volume (highest: ${result[0]?.symbol ?? 'N/A'} at $${Math.round(result[0]?.volume_24h ?? 0)} vol)`,
  )
  return result
}

/**
 * Fetch candles for multiple symbols.
 * Returns record mapping symbol -> CandleData[].
 */
export async function fetchCandlesBatch(
  exchangeId: string,
  symbols: string[],
  timeframe = '1h',
  limit = 200,
): Promise<Record<string, CandleData[]>> {
  const result: Record<string, CandleData[]> = {}

  for (let i = 0; i < symbols.length; i++) {
    const symbol = symbols[i]
    try {
      const candles = await fetchCandles(exchangeId, symbol, timeframe, undefined, limit)
      if (candles.length === 0) continue
      result[symbol] = candles
      if ((i + 1) % 10 === 0) {
        console.log(`Fetched candles for ${i + 1}/${symbols.length} symbols...`)
      }
    } catch (e) {
      console.warn(`Failed to fetch candles for ${symbol}: ${e}`)
    }
  }

  console.log(`Fetched candles for ${Object.keys(result).length}/${symbols.length} symbols`)
  return result
}
