import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Trash2,
  Power,
  Zap,
  Sparkles,
  TrendingUp,
  TrendingDown,
  BarChart3,
  Target,
  Activity,
  ChevronRight,
} from "lucide-react";
import {
  useStrategies,
  useToggleStrategy,
  useDeleteStrategy,
} from "@/hooks/useStrategies";
import { useStrategyComparison } from "@/hooks/useAnalytics";
import type { Strategy } from "@/hooks/useStrategies";
import type { StrategyMetrics } from "@/hooks/useAnalytics";
import { cn } from "@/lib/cn";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

/* ----- Strategy Card ----- */
function StrategyCard({
  strategy,
  metrics,
  onToggle,
  onDelete,
  onClick,
  isToggling,
  isDeleting,
}: {
  strategy: Strategy;
  metrics?: StrategyMetrics;
  onToggle: () => void;
  onDelete: () => void;
  onClick: () => void;
  isToggling: boolean;
  isDeleting: boolean;
}) {
  const [showConfirm, setShowConfirm] = useState(false);
  const config = (strategy.config ?? {}) as Record<string, unknown>;
  const symbols = (config.symbols as string[]) ?? [];
  const equity = (config.account_equity as number) ?? 0;

  return (
    <div
      className={cn(
        "bg-(--color-bg-surface) border rounded-xl p-5 transition-all cursor-pointer hover:border-(--color-accent)/60",
        strategy.is_active
          ? "border-(--color-accent)/40 shadow-[0_0_12px_rgba(123,97,255,0.08)]"
          : "border-(--color-border)"
      )}
      onClick={onClick}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className="text-base font-semibold text-(--color-text-primary) truncate">
              {strategy.name}
            </h3>
            <span
              className={cn(
                "inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold uppercase",
                strategy.is_active
                  ? "bg-(--color-positive)/10 text-(--color-positive)"
                  : "bg-(--color-bg-elevated) text-(--color-text-secondary)"
              )}
            >
              <span
                className={cn(
                  "w-1.5 h-1.5 rounded-full",
                  strategy.is_active
                    ? "bg-(--color-positive)"
                    : "bg-(--color-text-secondary)/40"
                )}
              />
              {strategy.is_active ? "Active" : "Inactive"}
            </span>
          </div>
          <p className="text-xs text-(--color-text-secondary) mt-1">
            Created {formatDate(strategy.created_at)}
            {strategy.updated_at !== strategy.created_at && (
              <> &middot; Updated {formatDate(strategy.updated_at)}</>
            )}
          </p>
        </div>

        <div className="flex items-center gap-1 shrink-0">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onToggle();
            }}
            disabled={isToggling}
            className={cn(
              "p-1.5 rounded-lg transition-colors",
              strategy.is_active
                ? "hover:bg-(--color-negative)/10 text-(--color-negative)"
                : "hover:bg-(--color-positive)/10 text-(--color-positive)"
            )}
            title={strategy.is_active ? "Deactivate" : "Activate"}
          >
            <Power className="w-3.5 h-3.5" />
          </button>
          {showConfirm ? (
            <div
              className="flex items-center gap-1 ml-1"
              onClick={(e) => e.stopPropagation()}
            >
              <button
                onClick={() => {
                  onDelete();
                  setShowConfirm(false);
                }}
                disabled={isDeleting}
                className="px-2 py-1 rounded text-xs bg-(--color-negative)/10 text-(--color-negative) hover:bg-(--color-negative)/20 transition-colors"
              >
                {isDeleting ? "..." : "Confirm"}
              </button>
              <button
                onClick={() => setShowConfirm(false)}
                className="px-2 py-1 rounded text-xs text-(--color-text-secondary) hover:bg-(--color-bg-elevated) transition-colors"
              >
                Cancel
              </button>
            </div>
          ) : (
            <button
              onClick={(e) => {
                e.stopPropagation();
                setShowConfirm(true);
              }}
              className="p-1.5 rounded-lg hover:bg-(--color-negative)/10 transition-colors"
              title="Delete strategy"
            >
              <Trash2 className="w-3.5 h-3.5 text-(--color-text-secondary)" />
            </button>
          )}
          <ChevronRight className="w-4 h-4 text-(--color-text-secondary)/50 ml-1" />
        </div>
      </div>

      {/* Symbols being traded */}
      {symbols.length > 0 && (
        <div className="mt-3">
          <p className="text-[10px] font-semibold text-(--color-text-secondary) uppercase tracking-wider mb-1.5">
            Trading Pairs ({symbols.length})
          </p>
          <div className="flex flex-wrap gap-1.5">
            {symbols.map((s) => (
              <span
                key={s}
                className="text-[11px] bg-(--color-accent-soft) text-(--color-accent) rounded-md px-2 py-0.5 font-medium"
              >
                {s}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Performance metrics */}
      {metrics && metrics.total_trades > 0 ? (
        <div className="mt-3 border-t border-(--color-border)/50 pt-3 space-y-2">
          <p className="text-[10px] font-semibold text-(--color-text-secondary) uppercase tracking-wider flex items-center gap-1.5">
            <BarChart3 className="w-3 h-3" />
            Performance
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            <div className="bg-(--color-bg-elevated)/50 rounded-lg px-3 py-2">
              <p className="text-[10px] text-(--color-text-secondary)">Total P&L</p>
              <p
                className={cn(
                  "text-sm font-semibold font-mono",
                  metrics.total_pnl >= 0
                    ? "text-(--color-positive)"
                    : "text-(--color-negative)"
                )}
              >
                {metrics.total_pnl >= 0 ? "+" : ""}
                {metrics.total_pnl < 1000
                  ? `$${metrics.total_pnl.toFixed(2)}`
                  : `$${(metrics.total_pnl / 1000).toFixed(1)}k`}
              </p>
            </div>
            <div className="bg-(--color-bg-elevated)/50 rounded-lg px-3 py-2">
              <p className="text-[10px] text-(--color-text-secondary)">Return</p>
              <div className="flex items-center gap-1">
                {metrics.total_return_pct >= 0 ? (
                  <TrendingUp className="w-3 h-3 text-(--color-positive)" />
                ) : (
                  <TrendingDown className="w-3 h-3 text-(--color-negative)" />
                )}
                <p
                  className={cn(
                    "text-sm font-semibold font-mono",
                    metrics.total_return_pct >= 0
                      ? "text-(--color-positive)"
                      : "text-(--color-negative)"
                  )}
                >
                  {metrics.total_return_pct >= 0 ? "+" : ""}
                  {metrics.total_return_pct.toFixed(1)}%
                </p>
              </div>
            </div>
            <div className="bg-(--color-bg-elevated)/50 rounded-lg px-3 py-2">
              <p className="text-[10px] text-(--color-text-secondary)">Win Rate</p>
              <div className="flex items-center gap-1">
                <Target className="w-3 h-3 text-(--color-accent)" />
                <p className="text-sm font-semibold font-mono text-(--color-text-primary)">
                  {metrics.win_rate.toFixed(0)}%
                </p>
              </div>
            </div>
            <div className="bg-(--color-bg-elevated)/50 rounded-lg px-3 py-2">
              <p className="text-[10px] text-(--color-text-secondary)">Trades</p>
              <p className="text-sm font-semibold font-mono text-(--color-text-primary)">
                {metrics.total_trades}
                <span className="text-[10px] font-normal text-(--color-text-secondary) ml-1">
                  ({metrics.winning_trades}W / {metrics.losing_trades}L)
                </span>
              </p>
            </div>
          </div>
          <div className="flex flex-wrap gap-3 text-xs">
            {equity > 0 && (
              <span className="text-(--color-text-secondary)">
                Capital:{" "}
                <span className="font-mono font-semibold text-(--color-text-primary)">
                  ${equity.toLocaleString()}
                </span>
              </span>
            )}
            {metrics.profit_factor != null && (
              <span className="text-(--color-text-secondary)">
                Profit Factor:{" "}
                <span className="font-mono font-semibold text-(--color-text-primary)">
                  {Number.isFinite(metrics.profit_factor) ? metrics.profit_factor.toFixed(2) : "\u221E"}
                </span>
              </span>
            )}
            {metrics.sharpe_ratio != null && (
              <span className="text-(--color-text-secondary)">
                Sharpe:{" "}
                <span className="font-mono font-semibold text-(--color-text-primary)">
                  {metrics.sharpe_ratio.toFixed(2)}
                </span>
              </span>
            )}
            {metrics.max_drawdown_pct > 0 && (
              <span className="text-(--color-text-secondary)">
                Max DD:{" "}
                <span className="font-mono font-semibold text-(--color-negative)">
                  {metrics.max_drawdown_pct.toFixed(1)}%
                </span>
              </span>
            )}
            {metrics.active_signals > 0 && (
              <span className="flex items-center gap-1 text-(--color-text-secondary)">
                <Activity className="w-3 h-3 text-(--color-warning)" />
                {metrics.active_signals} active signal
                {metrics.active_signals > 1 ? "s" : ""}
              </span>
            )}
          </div>
        </div>
      ) : metrics && metrics.total_trades === 0 ? (
        <div className="mt-3 border-t border-(--color-border)/50 pt-3">
          <p className="text-xs text-(--color-text-secondary) italic">
            No trades executed yet
            {metrics.active_signals > 0
              ? ` — ${metrics.active_signals} signal${metrics.active_signals > 1 ? "s" : ""} pending`
              : ""}
          </p>
        </div>
      ) : null}
    </div>
  );
}

/* ----- Main Page ----- */
export function StrategiesPage() {
  const navigate = useNavigate();
  const { data, isLoading } = useStrategies();
  const { data: comparison } = useStrategyComparison();
  const toggleMutation = useToggleStrategy();
  const deleteMutation = useDeleteStrategy();

  const strategies = data?.strategies ?? [];
  const metricsMap = new Map(
    (comparison?.strategies ?? []).map((m) => [m.strategy_id, m]),
  );

  return (
    <div className="p-6 space-y-6 max-w-[1200px] mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-(--color-text-primary)">
          Strategies
        </h1>
        <p className="text-sm text-(--color-text-secondary) mt-1">
          Monitor and manage your active trading strategies
        </p>
      </div>

      {/* Strategy list */}
      {isLoading ? (
        <div className="grid gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div
              key={i}
              className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-5 h-[100px] animate-pulse"
            />
          ))}
        </div>
      ) : strategies.length === 0 ? (
        <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-12 text-center">
          <Sparkles className="w-10 h-10 text-(--color-accent)/40 mx-auto mb-3" />
          <p className="text-sm font-medium text-(--color-text-primary)">
            No strategies yet
          </p>
          <p className="text-xs text-(--color-text-secondary) mt-1 mb-4 max-w-sm mx-auto">
            Use the AI Advisor to scan the market, pick the best trading pairs,
            and deploy an optimized strategy automatically.
          </p>
          <button
            onClick={() => navigate("/advisor")}
            className="inline-flex items-center gap-2 bg-(--color-accent) hover:bg-(--color-accent)/90 text-white font-semibold py-2.5 px-5 rounded-lg text-sm transition-colors"
          >
            <Sparkles className="w-4 h-4" />
            Go to AI Advisor
          </button>
        </div>
      ) : (
        <div className="grid gap-4">
          {strategies
            .sort((a, b) =>
              a.is_active === b.is_active ? 0 : a.is_active ? -1 : 1,
            )
            .map((strategy) => (
              <StrategyCard
                key={strategy.id}
                strategy={strategy}
                metrics={metricsMap.get(strategy.id)}
                onClick={() => navigate(`/strategies/${strategy.id}`)}
                onToggle={() => toggleMutation.mutate(strategy.id)}
                onDelete={() => deleteMutation.mutate(strategy.id)}
                isToggling={
                  toggleMutation.isPending &&
                  toggleMutation.variables === strategy.id
                }
                isDeleting={
                  deleteMutation.isPending &&
                  deleteMutation.variables === strategy.id
                }
              />
            ))}
        </div>
      )}

      {/* Active strategy hint */}
      {strategies.some((s) => s.is_active) && (
        <div className="flex items-center gap-2 text-xs text-(--color-text-secondary) bg-(--color-accent-soft) rounded-lg px-4 py-2.5">
          <Zap className="w-3.5 h-3.5 text-(--color-accent)" />
          Active strategies receive live signals and execute trades automatically
        </div>
      )}
    </div>
  );
}
