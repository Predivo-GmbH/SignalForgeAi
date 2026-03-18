/**
 * Daily Maintenance — runs at 02:00 UTC via pg_cron.
 * Replaces Celery tasks: risk tuning, feedback synthesis, pattern analysis, cleanup.
 */

import { serve } from 'https://deno.land/std@0.208.0/http/server.ts'
import { verifyServiceRole, errorResponse, jsonResponse } from '../_shared/auth.ts'

serve(async (req) => {
  try {
    const admin = verifyServiceRole(req)
    const startTime = performance.now()
    const log: string[] = []

    // Get all active strategies with their users
    const { data: strategies } = await admin.from('strategies')
      .select('id, user_id, config').eq('is_active', true)

    for (const strategy of strategies ?? []) {
      // Get closed trades for this user
      const { data: trades } = await admin.from('trades')
        .select('*').eq('user_id', strategy.user_id)
        .not('pnl', 'is', null)
        .order('exit_time', { ascending: false }).limit(50)

      if (!trades || trades.length < 5) {
        log.push(`Strategy ${strategy.id}: <5 trades, skipping AI analysis`)
        continue
      }

      try {
        // 1. Risk Tuning — Claude analyzes trades → adjusts risk params
        const { tuneRisk } = await import('../_shared/advisor/risk-tuner.ts')
        const tuning = await tuneRisk(strategy, trades)
        if (tuning) {
          const config = strategy.config as Record<string, unknown>
          const updatedConfig = { ...config, ...tuning.adjustments }
          await admin.from('strategies').update({ config: updatedConfig }).eq('id', strategy.id)
          log.push(`Strategy ${strategy.id}: risk params tuned`)
        }
      } catch (err) {
        log.push(`Risk tuning failed for ${strategy.id}: ${err instanceof Error ? err.message : 'unknown'}`)
      }

      try {
        // 2. Feedback Synthesis — Claude analyzes losing trades → creates FeedbackRules
        const { synthesizeFeedback } = await import('../_shared/advisor/feedback-synthesizer.ts')
        const rules = await synthesizeFeedback(strategy.user_id, strategy.id, trades)
        if (rules && rules.length > 0) {
          const rows = rules.map(r => ({
            strategy_id: strategy.id,
            user_id: strategy.user_id,
            rule_type: r.ruleType,
            description: r.description,
            conditions_json: r.conditions,
            confidence: r.confidence,
            expires_at: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
          }))
          await admin.from('feedback_rules').insert(rows)
          log.push(`Strategy ${strategy.id}: ${rules.length} feedback rules created`)
        }
      } catch (err) {
        log.push(`Feedback synthesis failed for ${strategy.id}: ${err instanceof Error ? err.message : 'unknown'}`)
      }

      try {
        // 3. Pattern Analysis — Claude identifies recurring patterns
        const { analyzePatterns } = await import('../_shared/advisor/pattern-analyzer.ts')
        const analysis = await analyzePatterns(strategy.user_id, trades)
        if (analysis) {
          log.push(`Strategy ${strategy.id}: patterns analyzed`)
        }
      } catch (err) {
        log.push(`Pattern analysis failed for ${strategy.id}: ${err instanceof Error ? err.message : 'unknown'}`)
      }
    }

    // 4. Cleanup — delete old pipeline_logs and candles
    const { data: cleanupResult } = await admin.rpc('cleanup_old_data', { p_days: 90 })
    log.push(`Cleanup: ${JSON.stringify(cleanupResult)}`)

    // Expire old feedback rules
    await admin.from('feedback_rules')
      .update({ is_active: false })
      .lt('expires_at', new Date().toISOString())
      .eq('is_active', true)

    const duration = Math.round(performance.now() - startTime)
    log.push(`Total duration: ${duration}ms`)

    return jsonResponse({ status: 'ok', log, duration_ms: duration })
  } catch (err) {
    return errorResponse(err)
  }
})
