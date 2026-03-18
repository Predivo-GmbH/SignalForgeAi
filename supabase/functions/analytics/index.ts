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
    const action = body.action ?? 'equity'

    switch (action) {
      case 'equity': {
        const { data: trades } = await adminClient.from('trades')
          .select('pnl, pnl_pct, exit_time').eq('user_id', user.id)
          .not('pnl', 'is', null).order('exit_time', { ascending: true })

        if (!trades || trades.length === 0) {
          return jsonResponse({
            points: [], total_return_pct: 0, max_drawdown_pct: 0,
            sharpe_ratio: null, sortino_ratio: null, calmar_ratio: null,
          })
        }

        const baseEquity = 10000
        let equity = baseEquity, peak = baseEquity, maxDrawdown = 0
        const dailyReturns: number[] = []
        const points = trades.map(t => {
          const prevEquity = equity
          equity += t.pnl ?? 0
          if (equity > peak) peak = equity
          const dd = ((peak - equity) / peak) * 100
          if (dd > maxDrawdown) maxDrawdown = dd
          dailyReturns.push((equity - prevEquity) / prevEquity)
          return {
            date: t.exit_time?.split('T')[0] ?? '',
            equity,
            drawdown_pct: dd,
          }
        })

        // Sharpe ratio (annualized)
        const avgReturn = dailyReturns.reduce((s, r) => s + r, 0) / dailyReturns.length
        const stdDev = Math.sqrt(
          dailyReturns.reduce((s, r) => s + (r - avgReturn) ** 2, 0) / dailyReturns.length
        )
        const sharpe = stdDev > 0 ? (avgReturn / stdDev) * Math.sqrt(252) : null

        // Sortino (downside deviation only)
        const downside = dailyReturns.filter(r => r < 0)
        const downsideDev = downside.length > 0
          ? Math.sqrt(downside.reduce((s, r) => s + r ** 2, 0) / downside.length)
          : 0
        const sortino = downsideDev > 0 ? (avgReturn / downsideDev) * Math.sqrt(252) : null

        // Calmar
        const totalReturn = ((equity - baseEquity) / baseEquity) * 100
        const calmar = maxDrawdown > 0 ? totalReturn / maxDrawdown : null

        return jsonResponse({
          points, total_return_pct: totalReturn,
          max_drawdown_pct: maxDrawdown, sharpe_ratio: sharpe,
          sortino_ratio: sortino, calmar_ratio: calmar,
        })
      }

      case 'compare': {
        const { data: strategies } = await adminClient.from('strategies')
          .select('id, name').eq('user_id', user.id)

        const result: Array<Record<string, unknown>> = []
        for (const s of strategies ?? []) {
          const { data: trades } = await adminClient.from('trades')
            .select('pnl, pnl_pct').eq('user_id', user.id)
            .not('pnl', 'is', null)

          const { data: signals } = await adminClient.from('signals')
            .select('id').eq('strategy_id', s.id).eq('status', 'pending')

          const wins = (trades ?? []).filter(t => (t.pnl ?? 0) > 0)
          const totalPnl = (trades ?? []).reduce((sum, t) => sum + (t.pnl ?? 0), 0)

          result.push({
            strategy_id: s.id, strategy_name: s.name,
            total_trades: trades?.length ?? 0,
            winning_trades: wins.length,
            losing_trades: (trades?.length ?? 0) - wins.length,
            win_rate: trades && trades.length > 0 ? (wins.length / trades.length) * 100 : 0,
            total_pnl: totalPnl,
            total_return_pct: totalPnl / 100,
            max_drawdown_pct: 0,
            sharpe_ratio: null,
            avg_pnl_per_trade: trades && trades.length > 0 ? totalPnl / trades.length : 0,
            profit_factor: null,
            active_signals: signals?.length ?? 0,
          })
        }

        return jsonResponse({
          strategies: result,
          best_by_return: result.sort((a, b) => (b.total_pnl as number) - (a.total_pnl as number))[0]?.strategy_id ?? null,
          best_by_sharpe: null,
          best_by_win_rate: result.sort((a, b) => (b.win_rate as number) - (a.win_rate as number))[0]?.strategy_id ?? null,
        })
      }

      case 'correlation': {
        const { symbol_a, symbol_b } = body
        const [aResult, bResult] = await Promise.all([
          adminClient.from('candles').select('close, time')
            .eq('symbol', symbol_a).eq('timeframe', '1h')
            .order('time', { ascending: true }).limit(500),
          adminClient.from('candles').select('close, time')
            .eq('symbol', symbol_b).eq('timeframe', '1h')
            .order('time', { ascending: true }).limit(500),
        ])

        const aPrices = (aResult.data ?? []).map(c => c.close)
        const bPrices = (bResult.data ?? []).map(c => c.close)
        const n = Math.min(aPrices.length, bPrices.length)

        if (n < 10) {
          return jsonResponse({ symbol_a, symbol_b, correlation: 0, data_points: 0, is_synthetic: true })
        }

        // Pearson correlation
        const aSlice = aPrices.slice(0, n), bSlice = bPrices.slice(0, n)
        const avgA = aSlice.reduce((s, v) => s + v, 0) / n
        const avgB = bSlice.reduce((s, v) => s + v, 0) / n
        let num = 0, denA = 0, denB = 0
        for (let i = 0; i < n; i++) {
          num += (aSlice[i] - avgA) * (bSlice[i] - avgB)
          denA += (aSlice[i] - avgA) ** 2
          denB += (bSlice[i] - avgB) ** 2
        }
        const correlation = Math.sqrt(denA * denB) > 0 ? num / Math.sqrt(denA * denB) : 0

        return jsonResponse({ symbol_a, symbol_b, correlation, data_points: n, is_synthetic: false })
      }

      default:
        throw new AuthError(`Unknown action: ${action}`, 400)
    }
  } catch (err) {
    return errorResponse(err)
  }
})
