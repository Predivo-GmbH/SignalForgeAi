/**
 * Engine Cron — runs every minute via pg_cron.
 * Replaces Celery workers: candle ingestion → signal pipeline → order execution → position management.
 *
 * Uses pg_advisory_lock to prevent overlapping runs.
 */

import { serve } from 'https://deno.land/std@0.208.0/http/server.ts'
import { verifyServiceRole, errorResponse, jsonResponse } from '../_shared/auth.ts'

const LOCK_ID = 12345 // Advisory lock ID for engine cron

serve(async (req) => {
  try {
    const admin = verifyServiceRole(req)

    // Acquire advisory lock — prevents overlapping runs
    const { data: lockResult } = await admin.rpc('pg_try_advisory_lock', { key: LOCK_ID })
    if (!lockResult) {
      return jsonResponse({ status: 'skipped', reason: 'Previous run still executing' })
    }

    const startTime = performance.now()
    const log: string[] = []

    try {
      // ====== Step 1: Candle Ingestion (~30s budget) ======
      const { data: activeStrategies } = await admin.from('strategies')
        .select('id, user_id, config').eq('is_active', true)

      if (!activeStrategies || activeStrategies.length === 0) {
        log.push('No active strategies')
        return jsonResponse({ status: 'ok', log, duration_ms: Math.round(performance.now() - startTime) })
      }

      // Collect unique (exchange, symbol, timeframe) pairs
      const pairs = new Set<string>()
      for (const s of activeStrategies) {
        const config = s.config as Record<string, unknown>
        const symbols = (config.symbols as string[]) ?? ['BTC/USDT']
        const timeframes = (config.timeframes as string[]) ?? ['1h']
        const exchange = (config.exchange as string) ?? 'binance'
        for (const sym of symbols) {
          for (const tf of timeframes) {
            pairs.add(`${exchange}:${sym}:${tf}`)
          }
        }
      }

      const { fetchCandles } = await import('../_shared/ccxt.ts')
      let candlesIngested = 0

      for (const pair of pairs) {
        const [exchange, symbol, timeframe] = pair.split(':')
        try {
          const candles = await fetchCandles(exchange, symbol, timeframe, undefined, 5)
          if (candles.length > 0) {
            await admin.from('candles').upsert(candles, {
              onConflict: 'time,symbol,exchange,timeframe',
            })
            candlesIngested += candles.length
          }
        } catch (err) {
          log.push(`Candle fetch failed: ${symbol} — ${err instanceof Error ? err.message : 'unknown'}`)
        }
      }
      log.push(`Candles ingested: ${candlesIngested}`)

      // Broadcast latest prices via Realtime
      const priceUpdates: Record<string, number> = {}
      for (const pair of pairs) {
        const [, symbol, timeframe] = pair.split(':')
        if (timeframe === '1h') {
          const { data } = await admin.from('candles')
            .select('close').eq('symbol', symbol).eq('timeframe', '1h')
            .order('time', { ascending: false }).limit(1).maybeSingle()
          if (data) priceUpdates[symbol] = data.close
        }
      }
      if (Object.keys(priceUpdates).length > 0) {
        await admin.channel('prices').send({
          type: 'broadcast',
          event: 'price_update',
          payload: priceUpdates,
        })
      }

      // ====== Step 2: Signal Pipeline (~60s budget) ======
      const { SignalPipeline } = await import('../_shared/engine/pipeline.ts')
      let signalsGenerated = 0

      for (const strategy of activeStrategies) {
        const config = strategy.config as Record<string, unknown>
        const symbols = (config.symbols as string[]) ?? ['BTC/USDT']
        const timeframes = (config.timeframes as string[]) ?? ['1h']

        const pipeline = new SignalPipeline({
          minConfluence: (config.min_confluence as number) ?? 50,
          minTriggerCount: (config.min_trigger_count as number) ?? 2,
          emaSlopeThreshold: (config.ema_slope_threshold as number) ?? 0.001,
        })

        for (const symbol of symbols) {
          for (const timeframe of timeframes) {
            try {
              // Load 300 candles
              const { data: candles } = await admin.from('candles')
                .select('*').eq('symbol', symbol).eq('timeframe', timeframe)
                .order('time', { ascending: true }).limit(300)

              if (!candles || candles.length < 100) continue

              const signal = pipeline.process(symbol, timeframe, candles)

              // Log pipeline decision
              await admin.from('pipeline_logs').insert({
                strategy_id: strategy.id,
                symbol, timeframe,
                action: signal.action,
                block_reason: signal.blockReason,
                confluence_score: signal.confluenceScore,
                regime: signal.regime,
              })

              // If actionable signal, check for dedup and persist
              if (signal.action !== 'NO_TRADE') {
                // Dedup check
                const { data: existing } = await admin.from('signals')
                  .select('id').eq('strategy_id', strategy.id)
                  .eq('symbol', symbol).eq('timeframe', timeframe)
                  .eq('direction', signal.action).eq('status', 'pending').maybeSingle()

                if (!existing) {
                  await admin.from('signals').insert({
                    user_id: strategy.user_id,
                    strategy_id: strategy.id,
                    symbol, timeframe,
                    direction: signal.action,
                    entry_price: candles[candles.length - 1].close,
                    stop_loss: signal.stopLoss ?? 0,
                    take_profit_1: signal.takeProfit1 ?? 0,
                    take_profit_2: signal.takeProfit2,
                    position_size: signal.positionSize,
                    confluence_score: signal.confluenceScore,
                    regime: signal.regime,
                    triggers: signal.triggers,
                    status: 'pending',
                  })
                  signalsGenerated++
                }
              }
            } catch (err) {
              log.push(`Pipeline failed: ${symbol}/${timeframe} — ${err instanceof Error ? err.message : 'unknown'}`)
            }
          }
        }
      }
      log.push(`Signals generated: ${signalsGenerated}`)

      // ====== Step 3: Order Execution (~20s budget) ======
      const { data: pendingSignals } = await admin.from('signals')
        .select('*').eq('status', 'pending')
        .order('created_at', { ascending: true }).limit(10)

      let ordersExecuted = 0
      for (const signal of pendingSignals ?? []) {
        try {
          // Check if user has broker connection
          const { data: broker } = await admin.from('broker_connections')
            .select('*').eq('user_id', signal.user_id)
            .eq('purpose', 'trade').limit(1).maybeSingle()

          if (!broker) {
            // Paper trade — create order and position directly
            await admin.from('orders').insert({
              user_id: signal.user_id,
              signal_id: signal.id,
              symbol: signal.symbol,
              direction: signal.direction,
              order_type: 'market',
              quantity: signal.position_size ?? 1,
              price: signal.entry_price,
              filled_quantity: signal.position_size ?? 1,
              average_fill_price: signal.entry_price,
              stop_loss: signal.stop_loss,
              take_profit: signal.take_profit_1,
              status: 'filled',
              broker: 'paper',
            })

            await admin.from('positions').insert({
              user_id: signal.user_id,
              strategy_id: signal.strategy_id,
              symbol: signal.symbol,
              direction: signal.direction,
              quantity: signal.position_size ?? 1,
              entry_price: signal.entry_price,
              current_price: signal.entry_price,
              stop_loss: signal.stop_loss,
              take_profit: signal.take_profit_1,
              original_stop_loss: signal.stop_loss,
              broker: 'paper',
              is_open: true,
            })

            await admin.from('signals').update({ status: 'active' }).eq('id', signal.id)
            ordersExecuted++
          }
          // Live trading via CCXT would go here
        } catch (err) {
          log.push(`Order failed: ${signal.symbol} — ${err instanceof Error ? err.message : 'unknown'}`)
          await admin.from('signals').update({ status: 'failed' }).eq('id', signal.id)
        }
      }
      log.push(`Orders executed: ${ordersExecuted}`)

      // ====== Step 4: Position Management (~20s budget) ======
      const { data: openPositions } = await admin.from('positions')
        .select('*').eq('is_open', true)

      let positionsClosed = 0
      for (const pos of openPositions ?? []) {
        // Check cooldown
        if (pos.cooldown_until && new Date(pos.cooldown_until) > new Date()) continue

        // Update current price from latest candle
        const { data: latest } = await admin.from('candles')
          .select('close').eq('symbol', pos.symbol).eq('timeframe', '1h')
          .order('time', { ascending: false }).limit(1).maybeSingle()

        if (!latest) continue
        const currentPrice = latest.close

        // Check stop loss / take profit
        let shouldClose = false
        let exitReason = ''

        if (pos.direction === 'BUY') {
          if (pos.stop_loss && currentPrice <= pos.stop_loss) {
            shouldClose = true
            exitReason = 'stop_loss'
          }
          if (pos.take_profit && currentPrice >= pos.take_profit) {
            shouldClose = true
            exitReason = 'take_profit'
          }
        } else {
          if (pos.stop_loss && currentPrice >= pos.stop_loss) {
            shouldClose = true
            exitReason = 'stop_loss'
          }
          if (pos.take_profit && currentPrice <= pos.take_profit) {
            shouldClose = true
            exitReason = 'take_profit'
          }
        }

        // Update position price
        const pnl = pos.direction === 'BUY'
          ? (currentPrice - pos.entry_price) * pos.quantity
          : (pos.entry_price - currentPrice) * pos.quantity

        await admin.from('positions').update({
          current_price: currentPrice,
          unrealized_pnl: pnl,
        }).eq('id', pos.id)

        if (shouldClose) {
          const pnlPct = ((currentPrice - pos.entry_price) / pos.entry_price) * 100 *
            (pos.direction === 'BUY' ? 1 : -1)

          // Close position
          await admin.from('positions').update({
            is_open: false,
            closed_at: new Date().toISOString(),
            current_price: currentPrice,
            unrealized_pnl: pnl,
          }).eq('id', pos.id)

          // Create trade record
          await admin.from('trades').insert({
            user_id: pos.user_id,
            symbol: pos.symbol,
            direction: pos.direction,
            entry_price: pos.entry_price,
            exit_price: currentPrice,
            position_size: pos.quantity,
            stop_loss: pos.stop_loss ?? 0,
            take_profit: pos.take_profit ?? 0,
            pnl,
            pnl_pct: pnlPct,
            confluence_score: 0,
            entry_time: pos.opened_at,
            exit_time: new Date().toISOString(),
            exit_reason: exitReason,
          })

          positionsClosed++
        }
      }
      log.push(`Positions closed: ${positionsClosed}`)

      const duration = Math.round(performance.now() - startTime)
      log.push(`Total duration: ${duration}ms`)

      return jsonResponse({ status: 'ok', log, duration_ms: duration })
    } finally {
      // Release advisory lock
      await admin.rpc('pg_advisory_unlock', { key: LOCK_ID }).catch(() => {})
    }
  } catch (err) {
    return errorResponse(err)
  }
})
