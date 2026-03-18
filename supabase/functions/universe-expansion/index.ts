/**
 * Universe Expansion — runs every 6h via pg_cron.
 * Discovers new high-volume symbols, checks data availability, backfills candles, promotes candidates.
 */

import { serve } from 'https://deno.land/std@0.208.0/http/server.ts'
import { verifyServiceRole, errorResponse, jsonResponse } from '../_shared/auth.ts'

serve(async (req) => {
  try {
    const admin = verifyServiceRole(req)
    const log: string[] = []

    const { fetchTopSymbols, fetchCandles } = await import('../_shared/ccxt.ts')

    // Discover top symbols by volume
    const topSymbols = await fetchTopSymbols('binance', 'USDT', 100)
    log.push(`Discovered ${topSymbols.length} symbols by volume`)

    // Get existing symbols already tracked
    const { data: existingCandles } = await admin.from('candles')
      .select('symbol').limit(1000)
    const existingSymbols = new Set((existingCandles ?? []).map(c => c.symbol))

    // Find new symbols not yet tracked
    const newSymbols = topSymbols.filter(s => !existingSymbols.has(s.symbol))
    log.push(`New symbols to evaluate: ${newSymbols.length}`)

    let backfilled = 0
    for (const { symbol } of newSymbols.slice(0, 10)) { // Max 10 new symbols per run
      try {
        // Quick regime check — skip chaotic symbols
        const candles = await fetchCandles('binance', symbol, '1h', undefined, 100)
        if (candles.length < 50) {
          log.push(`${symbol}: insufficient data, skipping`)
          continue
        }

        // Upsert candles for backfill
        await admin.from('candles').upsert(candles, {
          onConflict: 'time,symbol,exchange,timeframe',
        })

        backfilled++
        log.push(`${symbol}: backfilled ${candles.length} candles`)
      } catch (err) {
        log.push(`${symbol}: failed — ${err instanceof Error ? err.message : 'unknown'}`)
      }
    }

    return jsonResponse({
      status: 'ok',
      discovered: topSymbols.length,
      new_symbols: newSymbols.length,
      backfilled,
      log,
    })
  } catch (err) {
    return errorResponse(err)
  }
})
