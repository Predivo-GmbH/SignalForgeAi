import { serve } from 'https://deno.land/std@0.208.0/http/server.ts'
import { authenticateRequest, errorResponse, jsonResponse, AuthError } from '../_shared/auth.ts'
import { getCorsHeaders } from '../_shared/cors.ts'

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: getCorsHeaders(req) })
  }

  try {
    const { user, adminClient } = await authenticateRequest(req)
    const body = req.method === 'POST' ? await req.json() : {}
    const action = body.action ?? 'list'

    switch (action) {
      case 'list': {
        const { limit = 20, offset = 0, strategy_id, symbol, direction, status, sort_by, sort_dir } = body
        let query = adminClient.from('signals').select('*', { count: 'exact' })
          .eq('user_id', user.id)
          .order(sort_by ?? 'created_at', { ascending: sort_dir === 'asc' })
          .range(offset, offset + limit - 1)

        if (strategy_id) query = query.eq('strategy_id', strategy_id)
        if (symbol) query = query.eq('symbol', symbol)
        if (direction) query = query.eq('direction', direction)
        if (status) query = query.eq('status', status)

        const { data, error, count } = await query
        if (error) throw new AuthError(error.message, 500)
        return jsonResponse({ signals: data, total: count ?? 0, limit, offset })
      }

      case 'get': {
        const { data, error } = await adminClient.from('signals')
          .select('*').eq('id', body.id).eq('user_id', user.id).single()
        if (error) throw new AuthError('Signal not found', 404)
        return jsonResponse(data)
      }

      case 'generate': {
        // Import engine pipeline dynamically
        const { SignalPipeline } = await import('../_shared/engine/pipeline.ts')
        const { fetchCandles } = await import('../_shared/ccxt.ts')

        const { symbol, timeframe = '1h', exchange = 'binance' } = body

        // Fetch candles — try DB first, then CCXT
        let candles: Array<{ time: string; open: number; high: number; low: number; close: number; volume: number }>
        const { data: dbCandles } = await adminClient.from('candles')
          .select('*').eq('symbol', symbol).eq('timeframe', timeframe)
          .order('time', { ascending: true }).limit(300)

        if (dbCandles && dbCandles.length >= 100) {
          candles = dbCandles
        } else {
          candles = await fetchCandles(exchange, symbol, timeframe, undefined, 300)
        }

        const pipeline = new SignalPipeline({
          minConfluence: body.min_confluence ?? 50,
          minTriggerCount: body.min_trigger_count ?? 2,
        })
        const signal = pipeline.process(symbol, timeframe, candles)
        return jsonResponse(signal)
      }

      default:
        throw new AuthError(`Unknown action: ${action}`, 400)
    }
  } catch (err) {
    return errorResponse(err)
  }
})
