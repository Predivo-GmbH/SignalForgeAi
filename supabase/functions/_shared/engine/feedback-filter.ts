/**
 * Feedback Filter — applies learned rules to signal decisions.
 *
 * Not a pipeline layer. Acts as a pre-filter and post-filter wrapping
 * the pipeline execution.
 *
 * Uses Supabase client instead of SQLAlchemy.
 */

import { type SupabaseClient } from 'https://esm.sh/@supabase/supabase-js@2'

// ── Types ──────────────────────────────────────────────────────
interface FeedbackRuleRow {
  id: string
  strategy_id: string
  rule_type: string
  description: string | null
  conditions_json: Record<string, unknown> | null
  confidence: number | null
  is_active: boolean
  expires_at: string | null
}

// ── Feedback Filter ────────────────────────────────────────────
export class FeedbackFilter {
  /**
   * Check if any active rules say to skip this symbol/condition.
   * Returns [shouldSkip, ruleDescription].
   */
  async shouldSkip(
    symbol: string,
    regime: string | null,
    supabase: SupabaseClient,
    strategyId: string,
  ): Promise<[boolean, string | null]> {
    const rules = await this._loadActiveRules(supabase, strategyId)

    for (const rule of rules) {
      // Skip low-confidence rules
      if (rule.confidence !== null && rule.confidence < 0.5) continue

      const conditions = rule.conditions_json ?? {}

      // Check symbol match
      const condSymbol = conditions.symbol as string | undefined
      if (condSymbol && condSymbol !== symbol) continue

      // Check regime match
      const condRegime = conditions.regime as string | undefined
      if (condRegime && regime && condRegime !== regime) continue

      // Check action
      const action = conditions.action as string | undefined
      if (action === 'skip' && rule.rule_type === 'avoid_pattern') {
        return [true, rule.description]
      }
    }

    return [false, null]
  }

  /**
   * Check if any rules override the min_confluence for this context.
   * Returns the override value, or null if no override.
   */
  async getConfluenceOverride(
    symbol: string,
    regime: string | null,
    supabase: SupabaseClient,
    strategyId: string,
  ): Promise<number | null> {
    const rules = await this._loadActiveRules(supabase, strategyId)

    for (const rule of rules) {
      if (rule.rule_type !== 'adjust_param') continue

      const conditions = rule.conditions_json ?? {}

      const condSymbol = conditions.symbol as string | undefined
      if (condSymbol && condSymbol !== symbol) continue

      const condRegime = conditions.regime as string | undefined
      if (condRegime && regime && condRegime !== regime) continue

      const override = conditions.min_confluence as number | undefined
      if (override !== undefined && override !== null) {
        return Math.floor(override)
      }
    }

    return null
  }

  /**
   * Load active, non-expired feedback rules for a strategy.
   */
  private async _loadActiveRules(
    supabase: SupabaseClient,
    strategyId: string,
  ): Promise<FeedbackRuleRow[]> {
    const now = new Date().toISOString()

    const { data, error } = await supabase
      .from('feedback_rules')
      .select('*')
      .eq('strategy_id', strategyId)
      .eq('is_active', true)
      .or(`expires_at.is.null,expires_at.gt.${now}`)
      .order('confidence', { ascending: false })
      .limit(100)

    if (error) {
      console.error('Failed to load feedback rules:', error.message)
      return []
    }

    return (data ?? []) as FeedbackRuleRow[]
  }
}
