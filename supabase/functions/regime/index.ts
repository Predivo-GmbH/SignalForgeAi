import { serve } from 'https://deno.land/std@0.208.0/http/server.ts'
import { authenticateRequest, errorResponse, jsonResponse, AuthError } from '../_shared/auth.ts'
import { getCorsHeaders } from '../_shared/cors.ts'

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: getCorsHeaders(req) })
  }

  try {
    const { adminClient } = await authenticateRequest(req)
    const body = req.method === 'POST' ? await req.json() : {}
    const action = body.action ?? 'status'

    switch (action) {
      case 'status': {
        const symbol = body.symbol ?? 'BTC/USDT'

        // Get latest candles and compute regime
        const { data: candles } = await adminClient.from('candles')
          .select('*').eq('symbol', symbol).eq('timeframe', '1h')
          .order('time', { ascending: true }).limit(100)

        if (!candles || candles.length < 50) {
          return jsonResponse({
            regime: 'unknown', probabilities: {},
            allocation_pct: 50, allocation_table: 'moderate',
          })
        }

        const { detectRegime } = await import('../_shared/engine/regime.ts')
        const regime = detectRegime(candles)

        const allocationMap: Record<string, number> = {
          trending: 80, ranging: 40, transitioning: 60, chaotic: 10,
        }

        return jsonResponse({
          regime: regime.regime,
          probabilities: regime.details ?? {},
          allocation_pct: allocationMap[regime.regime] ?? 50,
          allocation_table: 'moderate',
        })
      }

      default:
        throw new AuthError(`Unknown action: ${action}`, 400)
    }
  } catch (err) {
    return errorResponse(err)
  }
})
