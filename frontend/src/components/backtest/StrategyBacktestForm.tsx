import { useState, useMemo } from "react";
import { Play, Loader2, ShieldCheck, BrainCircuit } from "lucide-react";
import { useStrategies } from "@/hooks/useStrategies";
import { useAdvisorStore } from "@/stores/advisorStore";
import { Tooltip } from "@/components/ui/Tooltip";
import type { StrategyBacktestRequest } from "@/hooks/useStrategyBacktest";

type Source = "strategy" | "plan";

interface StrategyBacktestFormProps {
  onSubmit: (req: StrategyBacktestRequest) => void;
  isLoading: boolean;
  /** When true, auto-select the "plan" source on mount. */
  prefillPlan?: boolean;
  /** Pre-select a specific strategy by ID. */
  prefillStrategyId?: string;
}

export function StrategyBacktestForm({
  onSubmit,
  isLoading,
  prefillPlan,
  prefillStrategyId,
}: StrategyBacktestFormProps) {
  const { data: strategiesData } = useStrategies();
  const strategies = useMemo(
    () => strategiesData?.strategies ?? [],
    [strategiesData],
  );

  const scanHistory = useAdvisorStore((s) => s.scanHistory);
  const latestPlan = scanHistory.find((h) => h.plan)?.plan ?? null;

  const [source, setSource] = useState<Source>(
    prefillPlan && latestPlan ? "plan" : "strategy",
  );
  const [strategyId, setStrategyId] = useState(prefillStrategyId ?? "");
  const [days, setDays] = useState(90);
  const [aiEnhanced, setAiEnhanced] = useState(false);

  // If no strategyId selected yet but strategies are available, use the first one
  const effectiveStrategyId =
    strategyId || (strategies.length > 0 ? strategies[0].id : "");

  const selectedStrategy = strategies.find((s) => s.id === effectiveStrategyId);
  const activeConfig =
    source === "strategy"
      ? selectedStrategy?.config
      : latestPlan
        ? {
            symbols: latestPlan.selected_cryptos.map((c) => c.symbol),
            ...latestPlan.strategy_config,
          }
        : null;

  const canSubmit =
    !isLoading &&
    ((source === "strategy" && !!effectiveStrategyId) ||
      (source === "plan" && !!latestPlan));

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;

    if (source === "strategy") {
      onSubmit({ strategy_id: effectiveStrategyId, days, ai_enhanced: aiEnhanced });
    } else if (latestPlan) {
      onSubmit({ plan: latestPlan as unknown as Record<string, unknown>, days, ai_enhanced: aiEnhanced });
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-4 sm:p-6 space-y-5"
    >
      <Tooltip text="Test your strategy against historical data to see how it would have performed before risking real capital.">
        <h2 className="text-lg font-semibold text-(--color-text-primary) cursor-help">
          Strategy Validation
        </h2>
      </Tooltip>

      {/* Source toggle */}
      <div className="space-y-1.5">
        <label className="block text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">
          Source
        </label>
        <div className="grid grid-cols-2 gap-1.5">
          <button
            type="button"
            onClick={() => setSource("strategy")}
            className={`flex items-center justify-center gap-1.5 px-3 py-2.5 min-h-[44px] rounded-lg text-sm font-medium transition-colors ${
              source === "strategy"
                ? "bg-(--color-accent) text-white"
                : "bg-(--color-bg-elevated) text-(--color-text-secondary) hover:text-(--color-text-primary)"
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5" aria-hidden="true" />
            Deployed Strategy
          </button>
          <button
            type="button"
            onClick={() => setSource("plan")}
            className={`flex items-center justify-center gap-1.5 px-3 py-2.5 min-h-[44px] rounded-lg text-sm font-medium transition-colors ${
              source === "plan"
                ? "bg-(--color-accent) text-white"
                : "bg-(--color-bg-elevated) text-(--color-text-secondary) hover:text-(--color-text-primary)"
            }`}
          >
            <BrainCircuit className="w-3.5 h-3.5" aria-hidden="true" />
            AI Advisor Plan
          </button>
        </div>
      </div>

      {/* Strategy selector */}
      {source === "strategy" && (
        <div className="space-y-1.5">
          <label className="block text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">
            Select Strategy
          </label>
          {strategies.length === 0 ? (
            <p className="text-sm text-(--color-text-secondary)/60">
              No deployed strategies found. Deploy one from the AI Advisor first.
            </p>
          ) : (
            <select
              value={effectiveStrategyId}
              onChange={(e) => setStrategyId(e.target.value)}
              aria-label="Select strategy"
              className="w-full bg-(--color-bg-elevated) border border-(--color-border) rounded-lg px-3 py-2.5 min-h-[44px] text-base sm:text-sm text-(--color-text-primary) focus:outline-none focus:ring-2 focus:ring-(--color-accent)/50"
            >
              {strategies.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          )}
        </div>
      )}

      {/* Plan source */}
      {source === "plan" && (
        <div className="space-y-1.5">
          {latestPlan ? (
            <div className="bg-(--color-bg-elevated)/50 rounded-lg p-3 space-y-1">
              <p className="text-sm font-medium text-(--color-text-primary)">
                AI Optimal Strategy
              </p>
              <p className="text-xs text-(--color-text-secondary)">
                {latestPlan.selected_cryptos.length} symbols &middot;{" "}
                {latestPlan.summary.slice(0, 80)}
                {latestPlan.summary.length > 80 ? "..." : ""}
              </p>
            </div>
          ) : (
            <p className="text-sm text-(--color-text-secondary)/60">
              No AI Advisor plan available. Generate one from the AI Advisor
              page first.
            </p>
          )}
        </div>
      )}

      {/* Config summary */}
      {activeConfig && (
        <div className="space-y-1.5">
          <label className="block text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">
            Configuration
          </label>
          <div className="bg-(--color-bg-elevated)/50 rounded-lg p-3 space-y-2">
            {/* Symbols */}
            <div className="flex flex-wrap gap-1">
              {((activeConfig as Record<string, unknown>).symbols as string[] ?? []).map(
                (sym: string) => (
                  <span
                    key={sym}
                    className="px-2 py-0.5 bg-(--color-bg-surface) border border-(--color-border) rounded text-xs font-mono text-(--color-text-secondary)"
                  >
                    {sym}
                  </span>
                ),
              )}
            </div>
            {/* Params */}
            <div className="grid grid-cols-2 gap-x-3 sm:gap-x-4 gap-y-1 text-xs">
              <span className="text-(--color-text-secondary)">Confluence</span>
              <span className="text-(--color-text-primary) font-mono">
                {String((activeConfig as Record<string, unknown>).min_confluence ?? "—")}
              </span>
              <span className="text-(--color-text-secondary)">Risk/Trade</span>
              <span className="text-(--color-text-primary) font-mono">
                {((activeConfig as Record<string, unknown>).max_risk_per_trade as number)
                  ? `${((activeConfig as Record<string, unknown>).max_risk_per_trade as number) * 100}%`
                  : "—"}
              </span>
              <span className="text-(--color-text-secondary)">ATR SL Mult</span>
              <span className="text-(--color-text-primary) font-mono">
                {String((activeConfig as Record<string, unknown>).atr_sl_multiplier ?? "—")}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Days slider */}
      <div className="space-y-1.5">
        <Tooltip text="How far back in time to test this strategy. Uses real market data when available, synthetic data as fallback.">
          <label className="block text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider cursor-help">
            Historical Period
          </label>
        </Tooltip>
        <input
          type="range"
          min={7}
          max={365}
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          aria-label={`Historical period: ${days} days`}
          className="w-full accent-(--color-accent)"
        />
        <div className="flex items-center justify-between">
          <p className="text-xs text-(--color-text-secondary)">7 – 365 days</p>
          <span className="text-sm font-mono text-(--color-text-primary) bg-(--color-bg-elevated) px-2 py-0.5 rounded">
            {days}
          </span>
        </div>
      </div>

      {/* AI Enhancement toggle */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between">
          <Tooltip text="Runs each signal through Claude AI for quality assessment. Rejects trap signals and adjusts position sizing. Costs ~$0.05–$0.20 per backtest. Falls back to algorithmic scoring if AI is unavailable.">
            <label className="block text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider cursor-help">
              AI-Enhanced
            </label>
          </Tooltip>
          <button
            type="button"
            role="switch"
            aria-checked={aiEnhanced}
            aria-label="AI-Enhanced validation"
            onClick={() => setAiEnhanced((v) => !v)}
            className="relative min-h-[44px] min-w-[44px] flex items-center justify-center"
          >
            <span className={`block w-12 h-7 rounded-full transition-colors ${
              aiEnhanced
                ? "bg-(--color-accent)"
                : "bg-(--color-bg-elevated) border border-(--color-border)"
            }`}>
              <span
                className={`block mt-0.5 ml-0.5 w-6 h-6 rounded-full bg-white shadow transition-transform ${
                  aiEnhanced ? "translate-x-5" : ""
                }`}
              />
            </span>
          </button>
        </div>
        {aiEnhanced && (
          <p className="text-xs text-(--color-text-secondary)/60">
            Each signal is evaluated by Claude AI for quality and trap detection
          </p>
        )}
      </div>

      {/* Submit */}
      <button
        type="submit"
        disabled={!canSubmit}
        className="w-full flex items-center justify-center gap-2 bg-(--color-accent) hover:bg-(--color-accent)/90 text-white font-semibold py-2.5 px-4 min-h-[44px] rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isLoading ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
            {aiEnhanced ? "Validating with AI..." : "Validating..."}
          </>
        ) : (
          <>
            {aiEnhanced ? <BrainCircuit className="w-4 h-4" aria-hidden="true" /> : <Play className="w-4 h-4" aria-hidden="true" />}
            Validate Strategy
          </>
        )}
      </button>
    </form>
  );
}
