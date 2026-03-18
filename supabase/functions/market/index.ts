import { serve } from 'https://deno.land/std@0.208.0/http/server.ts'
import { authenticateRequest, errorResponse, jsonResponse, AuthError } from '../_shared/auth.ts'
import { getCorsHeaders } from '../_shared/cors.ts'

const SUPPORTED_SYMBOLS = [
  'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT',
  'ADA/USDT', 'DOGE/USDT', 'AVAX/USDT', 'DOT/USDT', 'LINK/USDT',
  'MATIC/USDT', 'UNI/USDT', 'ATOM/USDT', 'LTC/USDT', 'FIL/USDT',
  'NEAR/USDT', 'APT/USDT', 'ARB/USDT', 'OP/USDT', 'SUI/USDT',
]

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: getCorsHeaders(req) })
  }

  try {
    const { adminClient } = await authenticateRequest(req)
    const body = req.method === 'POST' ? await req.json() : {}
    const action = body.action ?? 'symbols'

    switch (action) {
      case 'symbols': {
        return jsonResponse(SUPPORTED_SYMBOLS)
      }

      case 'candles': {
        const { symbol, timeframe = '1h', exchange = 'binance', limit = 300 } = body

        // Try DB first
        const { data: dbCandles } = await adminClient.from('candles')
          .select('*').eq('symbol', symbol).eq('timeframe', timeframe)
          .order('time', { ascending: true }).limit(limit)

        if (dbCandles && dbCandles.length >= 50) {
          return jsonResponse({ symbol, timeframe, candles: dbCandles })
        }

        // Fallback to CCXT
        const { fetchCandles } = await import('../_shared/ccxt.ts')
        const candles = await fetchCandles(exchange, symbol, timeframe, undefined, limit)
        return jsonResponse({ symbol, timeframe, candles })
      }

      case 'watchlist': {
        // Get symbols from active strategies
        const { data: strategies } = await adminClient.from('strategies')
          .select('config').eq('is_active', true)

        const symbols = new Set<string>()
        for (const s of strategies ?? []) {
          const syms = (s.config as Record<string, unknown>)?.symbols
          if (Array.isArray(syms)) syms.forEach((sym: string) => symbols.add(sym))
        }

        return jsonResponse({ symbols: [...symbols] })
      }

      default:
        throw new AuthError(`Unknown action: ${action}`, 400)
    }
  } catch (err) {
    return errorResponse(err)
  }
})
