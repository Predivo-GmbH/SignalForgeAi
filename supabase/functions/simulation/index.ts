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
    const action = body.action ?? 'active'

    switch (action) {
      case 'active': {
        const { data } = await adminClient.from('paper_simulations')
          .select('*').eq('user_id', user.id).eq('status', 'running').maybeSingle()
        return jsonResponse(data)
      }

      case 'latest': {
        const { data } = await adminClient.from('paper_simulations')
          .select('*').eq('user_id', user.id)
          .order('created_at', { ascending: false }).limit(1).maybeSingle()
        return jsonResponse(data)
      }

      case 'start': {
        // Check no existing running simulation
        const { data: existing } = await adminClient.from('paper_simulations')
          .select('id').eq('user_id', user.id).eq('status', 'running').maybeSingle()
        if (existing) throw new AuthError('A simulation is already running', 400)

        const initialHoldings = body.holdings ?? []
        const initialValue = body.initial_value ?? 10000

        const { data, error } = await adminClient.from('paper_simulations').insert({
          user_id: user.id,
          strategy_id: body.strategy_id,
          initial_holdings: initialHoldings,
          initial_value_usd: initialValue,
          paper_holdings: initialHoldings,
          usdt_reserve_pct: body.reserve_pct ?? 0,
          usdt_reserve_mode: body.reserve_mode ?? 'ai',
        }).select().single()
        if (error) throw new AuthError(error.message, 500)

        // Take initial snapshot
        await adminClient.from('simulation_snapshots').insert({
          simulation_id: data.id,
          bh_value_usd: initialValue,
          sf_value_usd: initialValue,
          sf_cash_usd: 0,
          sf_positions_value: initialValue,
        })

        return jsonResponse(data, 201)
      }

      case 'stop': {
        const simId = body.simulation_id
        const { data, error } = await adminClient.from('paper_simulations')
          .update({ status: 'stopped', stopped_at: new Date().toISOString() })
          .eq('id', simId).eq('user_id', user.id).select().single()
        if (error) throw new AuthError(error.message, 500)
        return jsonResponse(data)
      }

      case 'portfolio': {
        const simId = body.simulation_id
        const { data: sim } = await adminClient.from('paper_simulations')
          .select('*').eq('id', simId).eq('user_id', user.id).single()
        if (!sim) throw new AuthError('Simulation not found', 404)

        const { data: snapshots } = await adminClient.from('simulation_snapshots')
          .select('*').eq('simulation_id', simId)
          .order('timestamp', { ascending: true })

        return jsonResponse({
          simulation: sim,
          bh_portfolio: sim.initial_holdings,
          paper_portfolio: sim.paper_holdings,
          snapshots: snapshots ?? [],
        })
      }

      case 'reserve': {
        const { simulation_id, reserve_pct, reserve_mode } = body
        const updates: Record<string, unknown> = {}
        if (reserve_pct !== undefined) updates.usdt_reserve_pct = reserve_pct
        if (reserve_mode !== undefined) updates.usdt_reserve_mode = reserve_mode

        const { data, error } = await adminClient.from('paper_simulations')
          .update(updates).eq('id', simulation_id).eq('user_id', user.id).select().single()
        if (error) throw new AuthError(error.message, 500)
        return jsonResponse(data)
      }

      case 'comparison': {
        const simId = body.simulation_id
        const { data: snapshots } = await adminClient.from('simulation_snapshots')
          .select('*').eq('simulation_id', simId)
          .order('timestamp', { ascending: true })

        return jsonResponse({
          snapshots: snapshots ?? [],
          equity_curves: {
            bh: (snapshots ?? []).map(s => ({ date: s.timestamp, value: s.bh_value_usd })),
            paper: (snapshots ?? []).map(s => ({ date: s.timestamp, value: s.sf_value_usd })),
          },
        })
      }

      default:
        throw new AuthError(`Unknown action: ${action}`, 400)
    }
  } catch (err) {
    return errorResponse(err)
  }
})
