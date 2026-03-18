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
    const action = body.action ?? 'status'

    switch (action) {
      case 'status': {
        return jsonResponse({
          active: true,
          layers: ['regime', 'trend', 'zones', 'confluence', 'triggers', 'risk'],
          supported_symbols: ['BTC/USDT', 'ETH/USDT', 'SOL/USDT'],
          supported_timeframes: ['1h', '4h', '1d'],
        })
      }

      case 'log': {
        const { limit = 50, offset = 0, symbol, action: filterAction, block_reason } = body

        // Get user's strategies first
        const { data: strategies } = await adminClient.from('strategies')
          .select('id').eq('user_id', user.id)
        const strategyIds = (strategies ?? []).map(s => s.id)

        if (strategyIds.length === 0) {
          return jsonResponse({ entries: [], total: 0 })
        }

        let query = adminClient.from('pipeline_logs').select('*', { count: 'exact' })
          .in('strategy_id', strategyIds)
          .order('created_at', { ascending: false })
          .range(offset, offset + limit - 1)

        if (symbol) query = query.eq('symbol', symbol)
        if (filterAction) query = query.eq('action', filterAction)
        if (block_reason) query = query.eq('block_reason', block_reason)

        const { data, error, count } = await query
        if (error) throw new AuthError(error.message, 500)
        return jsonResponse({ entries: data, total: count ?? 0 })
      }

      case 'runs': {
        const { limit = 20 } = body

        // Get user's strategies
        const { data: strategies } = await adminClient.from('strategies')
          .select('id').eq('user_id', user.id)
        const strategyIds = (strategies ?? []).map(s => s.id)

        if (strategyIds.length === 0) {
          return jsonResponse({ runs: [] })
        }

        // Group pipeline logs into 5-min buckets
        const { data: logs } = await adminClient.from('pipeline_logs')
          .select('created_at, action, block_reason')
          .in('strategy_id', strategyIds)
          .order('created_at', { ascending: false })
          .limit(500)

        const buckets = new Map<string, { total: number; passed: number; blocked: number }>()
        for (const log of logs ?? []) {
          const time = new Date(log.created_at)
          time.setMinutes(Math.floor(time.getMinutes() / 5) * 5, 0, 0)
          const key = time.toISOString()
          const b = buckets.get(key) ?? { total: 0, passed: 0, blocked: 0 }
          b.total++
          if (log.block_reason) b.blocked++; else b.passed++
          buckets.set(key, b)
        }

        const runs = [...buckets.entries()]
          .map(([time, stats]) => ({ time, ...stats }))
          .slice(0, limit)

        return jsonResponse({ runs })
      }

      case 'summary': {
        const today = new Date().toISOString().split('T')[0] + 'T00:00:00Z'

        const { data: strategies } = await adminClient.from('strategies')
          .select('id').eq('user_id', user.id)
        const strategyIds = (strategies ?? []).map(s => s.id)

        if (strategyIds.length === 0) {
          return jsonResponse({
            total_evaluations: 0, pass_rate: 0,
            block_reasons: {},
          })
        }

        const { data: logs } = await adminClient.from('pipeline_logs')
          .select('action, block_reason')
          .in('strategy_id', strategyIds)
          .gte('created_at', today)

        const total = logs?.length ?? 0
        const passed = (logs ?? []).filter(l => !l.block_reason).length
        const blockReasons: Record<string, number> = {}
        for (const l of logs ?? []) {
          if (l.block_reason) {
            blockReasons[l.block_reason] = (blockReasons[l.block_reason] ?? 0) + 1
          }
        }

        return jsonResponse({
          total_evaluations: total,
          pass_rate: total > 0 ? (passed / total) * 100 : 0,
          block_reasons: blockReasons,
        })
      }

      default:
        throw new AuthError(`Unknown action: ${action}`, 400)
    }
  } catch (err) {
    return errorResponse(err)
  }
})
