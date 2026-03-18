import { serve } from 'https://deno.land/std@0.208.0/http/server.ts'
import { authenticateRequest, errorResponse, jsonResponse, AuthError } from '../_shared/auth.ts'
import { getCorsHeaders } from '../_shared/cors.ts'

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: getCorsHeaders(req) })
  }

  try {
    await authenticateRequest(req)
    const { getSupabaseAdmin } = await import('../_shared/supabase.ts')
    const admin = getSupabaseAdmin()

    // Check DB connectivity
    let dbOk = true
    try {
      await admin.from('candles').select('time').limit(1)
    } catch {
      dbOk = false
    }

    // Check data freshness
    const { data: latestCandle } = await admin.from('candles')
      .select('time').order('time', { ascending: false }).limit(1).maybeSingle()

    const { data: latestSignal } = await admin.from('signals')
      .select('created_at').order('created_at', { ascending: false }).limit(1).maybeSingle()

    const { data: latestPipeline } = await admin.from('pipeline_logs')
      .select('created_at').order('created_at', { ascending: false }).limit(1).maybeSingle()

    const now = Date.now()
    const candleAge = latestCandle ? (now - new Date(latestCandle.time).getTime()) / 1000 : Infinity
    const signalAge = latestSignal ? (now - new Date(latestSignal.created_at).getTime()) / 1000 : Infinity
    const pipelineAge = latestPipeline ? (now - new Date(latestPipeline.created_at).getTime()) / 1000 : Infinity

    // Determine overall status
    const cronHealthy = candleAge < 300 // Candles less than 5 min old
    const pipelineHealthy = pipelineAge < 600 // Pipeline ran within 10 min

    let overall: 'healthy' | 'degraded' | 'critical' = 'healthy'
    if (!dbOk) overall = 'critical'
    else if (!cronHealthy || !pipelineHealthy) overall = 'degraded'

    return jsonResponse({
      status: overall,
      services: {
        database: { ok: dbOk },
        cron: { ok: cronHealthy, last_candle_age_s: Math.round(candleAge) },
        pipeline: { ok: pipelineHealthy, last_run_age_s: Math.round(pipelineAge) },
      },
      data_freshness: {
        last_candle: latestCandle?.time ?? null,
        last_signal: latestSignal?.created_at ?? null,
        last_pipeline_run: latestPipeline?.created_at ?? null,
      },
    })
  } catch (err) {
    return errorResponse(err)
  }
})
