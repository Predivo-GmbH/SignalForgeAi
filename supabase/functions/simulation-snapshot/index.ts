/**
 * Simulation Snapshot — runs hourly via pg_cron.
 * Snapshots B&H vs paper portfolio values for each running simulation.
 */

import { serve } from 'https://deno.land/std@0.208.0/http/server.ts'
import { verifyServiceRole, errorResponse, jsonResponse } from '../_shared/auth.ts'

serve(async (req) => {
  try {
    const admin = verifyServiceRole(req)
    const log: string[] = []

    // Get all running simulations
    const { data: simulations } = await admin.from('paper_simulations')
      .select('*').eq('status', 'running')

    for (const sim of simulations ?? []) {
      try {
        // Calculate B&H value (initial holdings at current prices)
        let bhValue = 0
        const initialHoldings = sim.initial_holdings as Array<{ symbol: string; quantity: number }>
        for (const h of initialHoldings) {
          const { data: candle } = await admin.from('candles')
            .select('close').eq('symbol', h.symbol).eq('timeframe', '1h')
            .order('time', { ascending: false }).limit(1).maybeSingle()
          bhValue += (candle?.close ?? 0) * h.quantity
        }
        if (bhValue === 0) bhValue = sim.initial_value_usd

        // Calculate paper value (paper holdings at current prices + open positions + cash)
        let sfPositionsValue = 0
        const { data: openPositions } = await admin.from('positions')
          .select('unrealized_pnl, entry_price, quantity')
          .eq('user_id', sim.user_id).eq('is_open', true)

        for (const pos of openPositions ?? []) {
          sfPositionsValue += pos.entry_price * pos.quantity + (pos.unrealized_pnl ?? 0)
        }

        // Cash = initial - reserved for positions
        const sfCash = sim.initial_value_usd * (sim.usdt_reserve_pct / 100)
        const sfValue = sfPositionsValue + sfCash
        const finalSfValue = sfValue > 0 ? sfValue : sim.initial_value_usd

        // Insert snapshot
        await admin.from('simulation_snapshots').insert({
          simulation_id: sim.id,
          bh_value_usd: bhValue,
          sf_value_usd: finalSfValue,
          sf_cash_usd: sfCash,
          sf_positions_value: sfPositionsValue,
        })

        log.push(`Sim ${sim.id}: B&H=$${bhValue.toFixed(2)}, Paper=$${finalSfValue.toFixed(2)}`)
      } catch (err) {
        log.push(`Sim ${sim.id} failed: ${err instanceof Error ? err.message : 'unknown'}`)
      }
    }

    return jsonResponse({ status: 'ok', snapshots_taken: simulations?.length ?? 0, log })
  } catch (err) {
    return errorResponse(err)
  }
})
