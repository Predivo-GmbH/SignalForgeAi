import { serve } from 'https://deno.land/std@0.208.0/http/server.ts'
import { authenticateRequest, errorResponse, jsonResponse, AuthError, sseResponse } from '../_shared/auth.ts'
import { getCorsHeaders, corsHeaders } from '../_shared/cors.ts'

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: getCorsHeaders(req) })
  }

  try {
    const { user, adminClient } = await authenticateRequest(req)
    const body = await req.json()
    const action = body.action ?? 'scan'

    switch (action) {
      case 'scan': {
        // SSE streaming scan
        const { stream, send } = sseResponse()

        const response = new Response(stream, {
          headers: {
            ...corsHeaders,
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
          },
        })

        // Run scan in background
        ;(async () => {
          try {
            const { fetchTopSymbols, fetchCandles } = await import('../_shared/ccxt.ts')
            const { SignalPipeline } = await import('../_shared/engine/pipeline.ts')

            send('scan_started', { status: 'scanning' })

            const topSymbols = await fetchTopSymbols('binance', 'USDT', body.limit ?? 30)
            send('symbols_found', { count: topSymbols.length })

            const pipeline = new SignalPipeline()
            const results = []

            for (let i = 0; i < topSymbols.length; i++) {
              const { symbol, volume } = topSymbols[i]
              try {
                const candles = await fetchCandles('binance', symbol, '1h', undefined, 300)
                const signal = pipeline.process(symbol, '1h', candles)

                const scored = {
                  symbol,
                  score: signal.confluenceScore,
                  regime: signal.regime,
                  trend_direction: signal.trendDirection,
                  trend_strength: signal.trendStrength,
                  rsi: 50,
                  adx: 25,
                  atr_pct: 2,
                  macd_histogram: 0,
                  volume_rank: i + 1,
                  price: candles[candles.length - 1]?.close ?? 0,
                  volume_24h: volume,
                  change_pct_24h: 0,
                  recommendation: signal.action === 'NO_TRADE' ? 'avoid' : 'consider',
                }
                results.push(scored)
                send('pair_scored', { index: i + 1, total: topSymbols.length, symbol, score: scored.score })
              } catch {
                send('pair_failed', { symbol, error: 'Could not analyze' })
              }
            }

            results.sort((a, b) => b.score - a.score)

            const trendingPct = results.filter(r => r.regime !== 'chaotic').length / results.length * 100
            const bullishPct = results.filter(r => r.trend_direction === 'bullish').length / results.length * 100

            send('scan_complete', {
              pairs_scanned: topSymbols.length,
              pairs_scored: results.length,
              results,
              market_profile: {
                trending_pct: trendingPct,
                bullish_pct: bullishPct,
                avg_score: results.reduce((s, r) => s + r.score, 0) / results.length,
                avg_adx: 25,
                avg_volatility: 2,
              },
            })
          } catch (err) {
            send('scan_error', { error: err instanceof Error ? err.message : 'Scan failed' })
          }
        })()

        return response
      }

      case 'plan': {
        const { planStrategy } = await import('../_shared/advisor/planner.ts')
        const plan = await planStrategy(body.scan_results ?? [], body.amount ?? 10000)
        return jsonResponse(plan)
      }

      case 'deploy': {
        const plan = body.plan
        if (!plan?.strategy_config) throw new AuthError('Invalid plan', 400)

        // Create strategy from plan
        const { data: strategy, error } = await adminClient.from('strategies').insert({
          user_id: user.id,
          name: `AI Strategy ${new Date().toISOString().split('T')[0]}`,
          config: {
            ...plan.strategy_config,
            symbols: plan.selected_cryptos.map((c: { symbol: string }) => c.symbol),
            symbol_sources: Object.fromEntries(
              plan.selected_cryptos.map((c: { symbol: string }) => [c.symbol, 'ai_deploy'])
            ),
          },
          is_active: true,
        }).select().single()

        if (error) throw new AuthError(error.message, 500)

        return jsonResponse({
          strategy_id: strategy.id,
          strategy_name: strategy.name,
          symbols_count: plan.selected_cryptos.length,
          message: 'Strategy deployed and activated',
        })
      }

      default:
        throw new AuthError(`Unknown action: ${action}`, 400)
    }
  } catch (err) {
    return errorResponse(err)
  }
})
