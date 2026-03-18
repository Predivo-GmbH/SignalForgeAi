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
    const action = body.action ?? 'summary'

    switch (action) {
      case 'summary': {
        const days = body.days ?? 30
        const cutoff = new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString()

        const { data: insights } = await adminClient.from('ai_insights')
          .select('model_used, insight_type, cost_usd, input_tokens, output_tokens, latency_ms, created_at')
          .eq('user_id', user.id).gte('created_at', cutoff)
          .order('created_at', { ascending: false })

        const allInsights = insights ?? []
        const totalCost = allInsights.reduce((s, i) => s + (i.cost_usd ?? 0), 0)
        const totalCalls = allInsights.length
        const avgLatency = totalCalls > 0
          ? allInsights.reduce((s, i) => s + (i.latency_ms ?? 0), 0) / totalCalls
          : 0

        // Model breakdown
        const modelMap = new Map<string, { calls: number; cost: number; tokens: number }>()
        for (const i of allInsights) {
          const m = modelMap.get(i.model_used) ?? { calls: 0, cost: 0, tokens: 0 }
          m.calls++
          m.cost += i.cost_usd ?? 0
          m.tokens += (i.input_tokens ?? 0) + (i.output_tokens ?? 0)
          modelMap.set(i.model_used, m)
        }

        // Type breakdown
        const typeMap = new Map<string, { calls: number; cost: number }>()
        for (const i of allInsights) {
          const t = typeMap.get(i.insight_type) ?? { calls: 0, cost: 0 }
          t.calls++
          t.cost += i.cost_usd ?? 0
          typeMap.set(i.insight_type, t)
        }

        // Daily costs
        const dailyMap = new Map<string, number>()
        for (const i of allInsights) {
          const day = i.created_at.split('T')[0]
          dailyMap.set(day, (dailyMap.get(day) ?? 0) + (i.cost_usd ?? 0))
        }

        // Recent calls
        const recentCalls = allInsights.slice(0, 20).map(i => ({
          model: i.model_used,
          type: i.insight_type,
          cost: i.cost_usd,
          tokens_in: i.input_tokens,
          tokens_out: i.output_tokens,
          latency_ms: i.latency_ms,
          created_at: i.created_at,
        }))

        return jsonResponse({
          total_cost_usd: totalCost,
          total_calls: totalCalls,
          avg_latency_ms: Math.round(avgLatency),
          model_breakdown: Object.fromEntries(modelMap),
          type_breakdown: Object.fromEntries(typeMap),
          daily_costs: Object.fromEntries([...dailyMap].sort()),
          recent_calls: recentCalls,
          credit: { prepaid_usd: 0, used_usd: totalCost, remaining_usd: 0 },
        })
      }

      case 'update-credit': {
        // Simple credit tracking via profile alert_config
        const { data, error } = await adminClient.from('profiles')
          .update({ alert_config: { prepaid_credit_usd: body.amount ?? 0 } })
          .eq('user_id', user.id).select().single()
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
