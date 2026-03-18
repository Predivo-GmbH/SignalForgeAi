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
        const { limit = 20, offset = 0, strategy_id } = body
        let query = adminClient.from('trades').select('*', { count: 'exact' })
          .eq('user_id', user.id)
          .order('created_at', { ascending: false })
          .range(offset, offset + limit - 1)

        if (strategy_id) query = query.eq('signal_id', strategy_id) // filter via signal

        const { data, error, count } = await query
        if (error) throw new AuthError(error.message, 500)

        // Enrich trades with signal data
        const signalIds = data?.filter(t => t.signal_id).map(t => t.signal_id) ?? []
        let signalMap: Record<string, Record<string, unknown>> = {}
        if (signalIds.length > 0) {
          const { data: signals } = await adminClient.from('signals')
            .select('id, regime, triggers, ai_quality_score, ai_recommendation, ai_reasoning')
            .in('id', signalIds)
          if (signals) {
            signalMap = Object.fromEntries(signals.map(s => [s.id, s]))
          }
        }

        const enriched = (data ?? []).map(t => ({
          ...t,
          ...(t.signal_id && signalMap[t.signal_id] ? {
            regime: signalMap[t.signal_id].regime,
            triggers: signalMap[t.signal_id].triggers,
            ai_quality_score: signalMap[t.signal_id].ai_quality_score,
            ai_recommendation: signalMap[t.signal_id].ai_recommendation,
            ai_reasoning: signalMap[t.signal_id].ai_reasoning,
          } : {}),
        }))

        return jsonResponse({ trades: enriched, total: count ?? 0 })
      }

      case 'stats': {
        const { data: trades } = await adminClient.from('trades')
          .select('pnl, pnl_pct').eq('user_id', user.id).not('pnl', 'is', null)

        if (!trades || trades.length === 0) {
          return jsonResponse({
            total_trades: 0, win_rate: 0, profit_factor: 0,
            total_pnl: 0, avg_pnl: 0, best_trade: 0, worst_trade: 0,
          })
        }

        const wins = trades.filter(t => (t.pnl ?? 0) > 0)
        const losses = trades.filter(t => (t.pnl ?? 0) < 0)
        const totalPnl = trades.reduce((s, t) => s + (t.pnl ?? 0), 0)
        const winSum = wins.reduce((s, t) => s + (t.pnl ?? 0), 0)
        const lossSum = Math.abs(losses.reduce((s, t) => s + (t.pnl ?? 0), 0))

        return jsonResponse({
          total_trades: trades.length,
          win_rate: trades.length > 0 ? (wins.length / trades.length) * 100 : 0,
          profit_factor: lossSum > 0 ? winSum / lossSum : 999.99,
          total_pnl: totalPnl,
          avg_pnl: totalPnl / trades.length,
          best_trade: Math.max(...trades.map(t => t.pnl ?? 0)),
          worst_trade: Math.min(...trades.map(t => t.pnl ?? 0)),
        })
      }

      case 'get': {
        const { data, error } = await adminClient.from('trades')
          .select('*').eq('id', body.id).eq('user_id', user.id).single()
        if (error) throw new AuthError('Trade not found', 404)
        return jsonResponse(data)
      }

      default:
        throw new AuthError(`Unknown action: ${action}`, 400)
    }
  } catch (err) {
    return errorResponse(err)
  }
})
