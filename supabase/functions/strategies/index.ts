import { serve } from 'https://deno.land/std@0.208.0/http/server.ts'
import { authenticateRequest, errorResponse, jsonResponse, AuthError } from '../_shared/auth.ts'
import { getCorsHeaders } from '../_shared/cors.ts'

const PRESETS: Record<string, { name: string; description: string; config: Record<string, unknown> }> = {
  conservative: {
    name: 'Conservative',
    description: 'Lower risk, fewer trades, higher confluence requirements',
    config: {
      min_confluence: 65, min_trigger_count: 3, max_risk_per_trade: 0.01,
      max_daily_loss: 0.02, atr_sl_multiplier: 2.0, min_risk_reward: 2.5,
      trailing_stop_enabled: true, drawdown_breaker_enabled: true,
    },
  },
  balanced: {
    name: 'Balanced',
    description: 'Moderate risk/reward balance for consistent growth',
    config: {
      min_confluence: 50, min_trigger_count: 2, max_risk_per_trade: 0.02,
      max_daily_loss: 0.04, atr_sl_multiplier: 1.5, min_risk_reward: 2.0,
      trailing_stop_enabled: true, drawdown_breaker_enabled: true,
    },
  },
  aggressive: {
    name: 'Aggressive',
    description: 'Higher risk tolerance, more trades, lower thresholds',
    config: {
      min_confluence: 40, min_trigger_count: 2, max_risk_per_trade: 0.03,
      max_daily_loss: 0.06, atr_sl_multiplier: 1.2, min_risk_reward: 1.5,
      trailing_stop_enabled: true, drawdown_breaker_enabled: false,
    },
  },
}

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
        const { data, error } = await adminClient.from('strategies')
          .select('*').eq('user_id', user.id).order('created_at', { ascending: false })
        if (error) throw new AuthError(error.message, 500)
        return jsonResponse({ strategies: data, total: data.length })
      }

      case 'get': {
        const { data, error } = await adminClient.from('strategies')
          .select('*').eq('id', body.id).eq('user_id', user.id).single()
        if (error) throw new AuthError('Strategy not found', 404)
        return jsonResponse(data)
      }

      case 'create': {
        const config = body.preset && PRESETS[body.preset]
          ? { ...PRESETS[body.preset].config }
          : (body.config ?? {})
        const { data, error } = await adminClient.from('strategies')
          .insert({ user_id: user.id, name: body.name, config }).select().single()
        if (error) throw new AuthError(error.message, 500)
        return jsonResponse(data, 201)
      }

      case 'update': {
        const updates: Record<string, unknown> = {}
        if (body.name !== undefined) updates.name = body.name
        if (body.config !== undefined) updates.config = body.config
        const { data, error } = await adminClient.from('strategies')
          .update(updates).eq('id', body.id).eq('user_id', user.id).select().single()
        if (error) throw new AuthError(error.message, 500)
        return jsonResponse(data)
      }

      case 'toggle': {
        // Toggle is_active flag
        const { data: current, error: fetchErr } = await adminClient.from('strategies')
          .select('is_active').eq('id', body.id).eq('user_id', user.id).single()
        if (fetchErr) throw new AuthError('Strategy not found', 404)

        const { data, error } = await adminClient.from('strategies')
          .update({ is_active: !current.is_active }).eq('id', body.id).select().single()
        if (error) throw new AuthError(error.message, 500)
        return jsonResponse(data)
      }

      case 'delete': {
        const { error } = await adminClient.from('strategies')
          .delete().eq('id', body.id).eq('user_id', user.id)
        if (error) throw new AuthError(error.message, 500)
        return jsonResponse({ deleted: true })
      }

      case 'presets': {
        return jsonResponse({ presets: PRESETS })
      }

      case 'exchange-availability': {
        const { fetchTopSymbols } = await import('../_shared/ccxt.ts')
        const symbols: string[] = body.symbols ?? []
        const exchanges = ['binance', 'kucoin', 'kraken']
        const availability: Record<string, string[]> = {}
        const unavailable: string[] = []

        for (const exchange of exchanges) {
          try {
            const top = await fetchTopSymbols(exchange, 'USDT', 200)
            const available = top.map(t => t.symbol)
            for (const sym of symbols) {
              if (available.includes(sym)) {
                if (!availability[sym]) availability[sym] = []
                availability[sym].push(exchange)
              }
            }
          } catch { /* exchange not available */ }
        }

        for (const sym of symbols) {
          if (!availability[sym]) unavailable.push(sym)
        }

        return jsonResponse({ availability, unavailable })
      }

      case 'feedback-rules': {
        const { data, error } = await adminClient.from('feedback_rules')
          .select('*').eq('strategy_id', body.strategy_id).eq('is_active', true)
        if (error) throw new AuthError(error.message, 500)
        return jsonResponse(data)
      }

      case 'toggle-feedback-rule': {
        const { data: rule } = await adminClient.from('feedback_rules')
          .select('is_active').eq('id', body.rule_id).single()
        if (!rule) throw new AuthError('Rule not found', 404)

        const { data, error } = await adminClient.from('feedback_rules')
          .update({ is_active: !rule.is_active }).eq('id', body.rule_id).select().single()
        if (error) throw new AuthError(error.message, 500)
        return jsonResponse(data)
      }

      default:
        throw new AuthError(`Unknown action: ${action}`, 400)
    }
  } catch (err) {
    return errorResponse(err)
  }
})
