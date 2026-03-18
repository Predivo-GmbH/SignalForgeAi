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
        const { data, error } = await adminClient.from('positions')
          .select('*').eq('user_id', user.id).eq('is_open', true)
          .order('opened_at', { ascending: false })
        if (error) throw new AuthError(error.message, 500)
        return jsonResponse(data)
      }

      case 'close': {
        const { position_id, exit_price, reason = 'manual' } = body

        // Get position
        const { data: pos, error: posErr } = await adminClient.from('positions')
          .select('*').eq('id', position_id).eq('user_id', user.id).eq('is_open', true).single()
        if (posErr || !pos) throw new AuthError('Position not found', 404)

        // Calculate PnL
        const pnl = pos.direction === 'BUY'
          ? (exit_price - pos.entry_price) * pos.quantity
          : (pos.entry_price - exit_price) * pos.quantity
        const pnlPct = ((exit_price - pos.entry_price) / pos.entry_price) * 100 *
          (pos.direction === 'BUY' ? 1 : -1)

        // Close position
        await adminClient.from('positions').update({
          is_open: false, closed_at: new Date().toISOString(), current_price: exit_price,
          unrealized_pnl: pnl,
        }).eq('id', position_id)

        // Create trade record
        await adminClient.from('trades').insert({
          user_id: user.id, symbol: pos.symbol, direction: pos.direction,
          entry_price: pos.entry_price, exit_price, position_size: pos.quantity,
          stop_loss: pos.stop_loss ?? 0, take_profit: pos.take_profit ?? 0,
          pnl, pnl_pct: pnlPct, confluence_score: 0,
          entry_time: pos.opened_at, exit_time: new Date().toISOString(),
          exit_reason: reason,
        })

        return jsonResponse({ closed: true, pnl, pnl_pct: pnlPct })
      }

      case 'account': {
        // Account state: equity, daily PnL, open count
        const { data: positions } = await adminClient.from('positions')
          .select('unrealized_pnl').eq('user_id', user.id).eq('is_open', true)

        const today = new Date().toISOString().split('T')[0]
        const { data: todayTrades } = await adminClient.from('trades')
          .select('pnl').eq('user_id', user.id)
          .gte('exit_time', today + 'T00:00:00Z')

        const equity = 10000 + (positions ?? []).reduce((s, p) => s + (p.unrealized_pnl ?? 0), 0)
        const dailyPnl = (todayTrades ?? []).reduce((s, t) => s + (t.pnl ?? 0), 0)

        return jsonResponse({
          equity, daily_pnl: dailyPnl,
          open_positions: positions?.length ?? 0, max_positions: 10,
        })
      }

      case 'drawdown': {
        const { data: trades } = await adminClient.from('trades')
          .select('pnl').eq('user_id', user.id).not('pnl', 'is', null)
          .order('exit_time', { ascending: true })

        let peak = 10000, equity = 10000, maxDrawdown = 0
        for (const t of trades ?? []) {
          equity += t.pnl ?? 0
          if (equity > peak) peak = equity
          const dd = ((peak - equity) / peak) * 100
          if (dd > maxDrawdown) maxDrawdown = dd
        }

        const currentDd = peak > 0 ? ((peak - equity) / peak) * 100 : 0
        const level = currentDd < 5 ? 0 : currentDd < 10 ? 1 : currentDd < 20 ? 2 : 3
        const levelNames = ['Normal', 'Caution', 'Warning', 'Critical']

        return jsonResponse({
          peak_equity: peak, current_equity: equity,
          drawdown_pct: currentDd, level, level_name: levelNames[level],
        })
      }

      case 'dashboard-snapshot': {
        // Combined dashboard data
        const [posResult, tradeResult, simResult] = await Promise.all([
          adminClient.from('positions').select('unrealized_pnl').eq('user_id', user.id).eq('is_open', true),
          adminClient.from('trades').select('pnl').eq('user_id', user.id)
            .gte('exit_time', new Date().toISOString().split('T')[0] + 'T00:00:00Z'),
          adminClient.from('paper_simulations').select('*, simulation_snapshots(bh_value_usd, sf_value_usd)')
            .eq('user_id', user.id).eq('status', 'running').limit(1).maybeSingle(),
        ])

        const positions = posResult.data ?? []
        const equity = 10000 + positions.reduce((s, p) => s + (p.unrealized_pnl ?? 0), 0)
        const dailyPnl = (tradeResult.data ?? []).reduce((s, t) => s + (t.pnl ?? 0), 0)

        let simulation = null
        if (simResult.data) {
          const sim = simResult.data
          const snaps = sim.simulation_snapshots ?? []
          const latest = snaps[snaps.length - 1]
          simulation = {
            id: sim.id, status: sim.status, initial_value_usd: sim.initial_value_usd,
            bh_value: latest?.bh_value_usd ?? sim.initial_value_usd,
            paper_value: latest?.sf_value_usd ?? sim.initial_value_usd,
            bh_return_pct: latest ? ((latest.bh_value_usd - sim.initial_value_usd) / sim.initial_value_usd) * 100 : 0,
            paper_return_pct: latest ? ((latest.sf_value_usd - sim.initial_value_usd) / sim.initial_value_usd) * 100 : 0,
          }
        }

        return jsonResponse({
          equity, balance: equity, daily_pnl: dailyPnl,
          open_positions: positions.length, max_positions: 10, simulation,
        })
      }

      default:
        throw new AuthError(`Unknown action: ${action}`, 400)
    }
  } catch (err) {
    return errorResponse(err)
  }
})
