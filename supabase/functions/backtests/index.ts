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
        const { data, error } = await adminClient.from('backtest_results')
          .select('*').eq('user_id', user.id)
          .order('created_at', { ascending: false }).limit(50)
        if (error) throw new AuthError(error.message, 500)
        return jsonResponse(data)
      }

      case 'run': {
        const { symbol, timeframe = '1h', days = 30, strategy_id, params } = body

        // Fetch historical candles
        const { fetchCandles } = await import('../_shared/ccxt.ts')
        const since = Date.now() - days * 24 * 60 * 60 * 1000
        const candles = await fetchCandles('binance', symbol, timeframe, since, days * 24)

        if (candles.length < 50) {
          throw new AuthError('Not enough historical data for backtest', 400)
        }

        // Get strategy config or use params
        let config = params ?? {}
        if (strategy_id) {
          const { data: strategy } = await adminClient.from('strategies')
            .select('config').eq('id', strategy_id).eq('user_id', user.id).single()
          if (strategy) config = { ...strategy.config, ...config }
        }

        // Run pipeline over historical data
        const { SignalPipeline } = await import('../_shared/engine/pipeline.ts')
        const pipeline = new SignalPipeline({
          minConfluence: (config.min_confluence as number) ?? 50,
          minTriggerCount: (config.min_trigger_count as number) ?? 2,
          emaSlopeThreshold: (config.ema_slope_threshold as number) ?? 0.001,
        })

        const equity = 10000
        let balance = equity
        let peak = equity
        let maxDrawdown = 0
        let wins = 0, losses = 0
        const equityCurve: Array<{ date: string; equity: number }> = []
        const trades: Array<{ pnl: number }> = []

        // Simulate trades using sliding window
        const windowSize = 300
        for (let i = windowSize; i < candles.length; i++) {
          const window = candles.slice(Math.max(0, i - windowSize), i)
          const signal = pipeline.process(symbol, timeframe, window)

          if (signal.action !== 'NO_TRADE' && signal.stopLoss && signal.takeProfit1) {
            const entryPrice = candles[i].close
            const sl = signal.stopLoss
            const tp = signal.takeProfit1

            // Simple sim: check next candles for SL/TP hit
            for (let j = i + 1; j < Math.min(i + 50, candles.length); j++) {
              const c = candles[j]
              if (signal.action === 'BUY') {
                if (c.low <= sl) {
                  const pnl = (sl - entryPrice) * (signal.positionSize ?? 1)
                  balance += pnl
                  trades.push({ pnl })
                  if (pnl > 0) wins++; else losses++
                  break
                }
                if (c.high >= tp) {
                  const pnl = (tp - entryPrice) * (signal.positionSize ?? 1)
                  balance += pnl
                  trades.push({ pnl })
                  if (pnl > 0) wins++; else losses++
                  break
                }
              } else {
                if (c.high >= sl) {
                  const pnl = (entryPrice - sl) * (signal.positionSize ?? 1)
                  balance += pnl
                  trades.push({ pnl })
                  if (pnl > 0) wins++; else losses++
                  break
                }
                if (c.low <= tp) {
                  const pnl = (entryPrice - tp) * (signal.positionSize ?? 1)
                  balance += pnl
                  trades.push({ pnl })
                  if (pnl > 0) wins++; else losses++
                  break
                }
              }
            }

            if (balance > peak) peak = balance
            const dd = ((peak - balance) / peak) * 100
            if (dd > maxDrawdown) maxDrawdown = dd
          }

          equityCurve.push({ date: candles[i].time, equity: balance })
        }

        const totalPnl = balance - equity
        const tradeCount = wins + losses
        const winRate = tradeCount > 0 ? (wins / tradeCount) * 100 : 0

        // Persist result
        const { data: result, error } = await adminClient.from('backtest_results').insert({
          user_id: user.id, strategy_id: strategy_id ?? null,
          symbol, timeframe, days,
          metrics: { wins, losses, total_pnl: totalPnl },
          equity_curve: equityCurve,
          trade_count: tradeCount, win_rate: winRate,
          sharpe_ratio: null, max_drawdown: maxDrawdown, total_pnl: totalPnl,
        }).select().single()

        if (error) throw new AuthError(error.message, 500)
        return jsonResponse(result)
      }

      case 'walk-forward': {
        // Walk-forward optimization stub
        const { symbol, timeframe, days = 90, folds = 3, params } = body
        // Split data into folds, optimize on in-sample, test on out-of-sample
        // Return per-fold results + best parameters
        return jsonResponse({
          fold_results: [],
          best_params: params ?? {},
          overall_win_rate: 0,
          overall_pnl: 0,
        })
      }

      default:
        throw new AuthError(`Unknown action: ${action}`, 400)
    }
  } catch (err) {
    return errorResponse(err)
  }
})
