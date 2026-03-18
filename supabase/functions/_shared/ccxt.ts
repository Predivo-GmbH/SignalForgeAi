/**
 * CCXT wrapper for exchange data fetching.
 * Uses npm:ccxt in Deno for the same library as Python version.
 */

import ccxt, { type Exchange, type OHLCV } from 'npm:ccxt@4'

const exchangeCache = new Map<string, Exchange>()

export interface CandleData {
  time: string
  symbol: string
  exchange: string
  timeframe: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface TickerData {
  symbol: string
  last: number
  bid: number
  ask: number
  volume: number
  change24h: number
}

/** Get or create an exchange instance */
export function getExchange(
  exchangeId: string,
  apiKey?: string,
  secret?: string,
  passphrase?: string,
  sandbox = false
): Exchange {
  const cacheKey = `${exchangeId}:${apiKey ?? 'public'}:${sandbox}`
  if (exchangeCache.has(cacheKey)) return exchangeCache.get(cacheKey)!

  const ExchangeClass = (ccxt as Record<string, new (config: Record<string, unknown>) => Exchange>)[exchangeId]
  if (!ExchangeClass) throw new Error(`Exchange ${exchangeId} not supported`)

  const config: Record<string, unknown> = {
    enableRateLimit: true,
    timeout: 30000,
  }

  if (apiKey) {
    config.apiKey = apiKey
    config.secret = secret
    if (passphrase) config.password = passphrase
  }

  const exchange = new ExchangeClass(config)
  if (sandbox) exchange.setSandboxMode(true)

  exchangeCache.set(cacheKey, exchange)
  return exchange
}

/** Fetch OHLCV candles from exchange */
export async function fetchCandles(
  exchangeId: string,
  symbol: string,
  timeframe: string,
  since?: number,
  limit = 300
): Promise<CandleData[]> {
  const exchange = getExchange(exchangeId)
  const ohlcv: OHLCV[] = await exchange.fetchOHLCV(symbol, timeframe, since, limit)

  return ohlcv.map((c) => ({
    time: new Date(c[0]!).toISOString(),
    symbol,
    exchange: exchangeId,
    timeframe,
    open: c[1]!,
    high: c[2]!,
    low: c[3]!,
    close: c[4]!,
    volume: c[5]!,
  }))
}

/** Fetch current ticker for a symbol */
export async function fetchTicker(exchangeId: string, symbol: string): Promise<TickerData> {
  const exchange = getExchange(exchangeId)
  const ticker = await exchange.fetchTicker(symbol)
  return {
    symbol,
    last: ticker.last ?? 0,
    bid: ticker.bid ?? 0,
    ask: ticker.ask ?? 0,
    volume: ticker.quoteVolume ?? ticker.baseVolume ?? 0,
    change24h: ticker.percentage ?? 0,
  }
}

/** Fetch top symbols by volume from an exchange */
export async function fetchTopSymbols(
  exchangeId: string,
  quoteAsset = 'USDT',
  limit = 50
): Promise<Array<{ symbol: string; volume: number }>> {
  const exchange = getExchange(exchangeId)
  const tickers = await exchange.fetchTickers()

  return Object.values(tickers)
    .filter((t) => t.symbol.endsWith(`/${quoteAsset}`) && (t.quoteVolume ?? 0) > 0)
    .sort((a, b) => (b.quoteVolume ?? 0) - (a.quoteVolume ?? 0))
    .slice(0, limit)
    .map((t) => ({ symbol: t.symbol, volume: t.quoteVolume ?? 0 }))
}

/** Create a market order via exchange */
export async function createOrder(
  exchangeId: string,
  symbol: string,
  side: 'buy' | 'sell',
  amount: number,
  apiKey: string,
  secret: string,
  passphrase?: string,
  sandbox = false
): Promise<{ orderId: string; filled: number; averagePrice: number; status: string }> {
  const exchange = getExchange(exchangeId, apiKey, secret, passphrase, sandbox)
  const order = await exchange.createMarketOrder(symbol, side, amount)
  return {
    orderId: order.id,
    filled: order.filled ?? 0,
    averagePrice: order.average ?? order.price ?? 0,
    status: order.status ?? 'unknown',
  }
}

/** Fetch order status */
export async function fetchOrderStatus(
  exchangeId: string,
  orderId: string,
  symbol: string,
  apiKey: string,
  secret: string,
  passphrase?: string,
  sandbox = false
): Promise<{ status: string; filled: number; averagePrice: number }> {
  const exchange = getExchange(exchangeId, apiKey, secret, passphrase, sandbox)
  const order = await exchange.fetchOrder(orderId, symbol)
  return {
    status: order.status ?? 'unknown',
    filled: order.filled ?? 0,
    averagePrice: order.average ?? order.price ?? 0,
  }
}
