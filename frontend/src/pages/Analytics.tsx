import { Activity, Trophy, TrendingUp, Target, Shield } from "lucide-react";
import { useEquityHistory, useStrategyComparison } from "@/hooks/useAnalytics";
import type { StrategyMetrics } from "@/hooks/useAnalytics";
import { MetricsGrid } from "@/components/analytics/MetricsGrid";
import { EquityCurve } from "@/components/analytics/EquityCurve";
import { CorrelationMatrix } from "@/components/analytics/CorrelationMatrix";
import { Tooltip } from "@/components/ui/Tooltip";
import { cn } from "@/lib/cn";
import { pnlColor } from "@/lib/format";

function StrategyComparisonSection() {
  const { data, isLoading, error } = useStrategyComparison();

  if (isLoading) {
    return (
      <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-6">
        <div className="flex items-center justify-center min-h-[200px]">
          <div className="text-center space-y-3">
            <div className="w-8 h-8 border-2 border-(--color-accent) border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="text-sm text-(--color-text-secondary)">Loading strategy comparison...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-(--color-bg-surface) border border-(--color-negative)/30 rounded-xl p-6">
        <div className="text-center space-y-2">
          <p className="text-sm text-(--color-negative) font-medium">Failed to load comparison</p>
          <p className="text-xs text-(--color-text-secondary)">{error.message}</p>
        </div>
      </div>
    );
  }

  if (!data || data.strategies.length === 0) {
    return (
      <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-6">
        <div className="text-center space-y-2 py-8">
          <Activity className="w-10 h-10 text-(--color-text-secondary)/40 mx-auto" />
          <p className="text-sm text-(--color-text-secondary)">No strategies to compare</p>
          <p className="text-xs text-(--color-text-secondary)/60">
            Create multiple strategies with different configs to compare their performance
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-(--color-text-primary)">Strategy Comparison</h2>
          <p className="text-xs text-(--color-text-secondary) mt-0.5">
            Side-by-side performance of all strategies
          </p>
        </div>
        <Tooltip icon text="All active strategies run in parallel on their configured symbols and timeframes. Compare metrics to find the best-performing configuration." />
      </div>

      {/* Winner badges */}
      {(data.best_by_return || data.best_by_sharpe || data.best_by_win_rate) && (
        <div className="flex flex-wrap gap-3">
          {data.best_by_return && (
            <div className="flex items-center gap-1.5 bg-(--color-positive)/10 text-(--color-positive) text-xs font-medium px-3 py-1.5 rounded-full">
              <TrendingUp className="w-3.5 h-3.5" />
              Best Return: {data.best_by_return}
            </div>
          )}
          {data.best_by_sharpe && (
            <div className="flex items-center gap-1.5 bg-(--color-accent)/10 text-(--color-accent) text-xs font-medium px-3 py-1.5 rounded-full">
              <Shield className="w-3.5 h-3.5" />
              Best Sharpe: {data.best_by_sharpe}
            </div>
          )}
          {data.best_by_win_rate && (
            <div className="flex items-center gap-1.5 bg-amber-500/10 text-amber-500 text-xs font-medium px-3 py-1.5 rounded-full">
              <Target className="w-3.5 h-3.5" />
              Best Win Rate: {data.best_by_win_rate}
            </div>
          )}
        </div>
      )}

      {/* Comparison table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-(--color-border)">
              <th className="text-left py-2.5 px-3 text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">Strategy</th>
              <th className="text-right py-2.5 px-3 text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">
                <Tooltip text="Total number of completed trades (entry + exit).">Trades</Tooltip>
              </th>
              <th className="text-right py-2.5 px-3 text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">
                <Tooltip text="Percentage of trades that were profitable.">Win Rate</Tooltip>
              </th>
              <th className="text-right py-2.5 px-3 text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">
                <Tooltip text="Total profit/loss in dollar terms.">P&L</Tooltip>
              </th>
              <th className="text-right py-2.5 px-3 text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">
                <Tooltip text="Percentage return on initial equity ($10,000).">Return %</Tooltip>
              </th>
              <th className="text-right py-2.5 px-3 text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">
                <Tooltip text="Largest peak-to-trough decline. Lower is better.">Max DD</Tooltip>
              </th>
              <th className="text-right py-2.5 px-3 text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">
                <Tooltip text="Risk-adjusted return. Above 1.0 is good, above 2.0 is excellent.">Sharpe</Tooltip>
              </th>
              <th className="text-right py-2.5 px-3 text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">
                <Tooltip text="Ratio of gross profits to gross losses. Above 1.0 = profitable.">PF</Tooltip>
              </th>
              <th className="text-right py-2.5 px-3 text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">
                <Tooltip text="Signals currently pending or active for this strategy.">Signals</Tooltip>
              </th>
            </tr>
          </thead>
          <tbody>
            {data.strategies.map((s: StrategyMetrics) => {
              const isBestReturn = s.strategy_name === data.best_by_return;
              const isBestSharpe = s.strategy_name === data.best_by_sharpe;
              const isBestWR = s.strategy_name === data.best_by_win_rate;
              return (
                <tr key={s.strategy_id} className="border-b border-(--color-border)/50 hover:bg-(--color-bg-elevated)/30 transition-colors">
                  <td className="py-3 px-3">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-(--color-text-primary)">{s.strategy_name}</span>
                      {(isBestReturn || isBestSharpe || isBestWR) && (
                        <Trophy className="w-3.5 h-3.5 text-amber-500" />
                      )}
                    </div>
                  </td>
                  <td className="text-right py-3 px-3 font-mono text-(--color-text-primary)">
                    {s.total_trades}
                    <span className="text-(--color-text-secondary) text-xs ml-1">
                      ({s.winning_trades}W/{s.losing_trades}L)
                    </span>
                  </td>
                  <td className={cn("text-right py-3 px-3 font-mono", s.win_rate >= 50 ? "text-(--color-positive)" : "text-(--color-negative)")}>
                    {s.win_rate.toFixed(1)}%
                  </td>
                  <td className={cn("text-right py-3 px-3 font-mono font-medium", pnlColor(s.total_pnl))}>
                    {s.total_pnl >= 0 ? "+" : ""}{s.total_pnl.toFixed(2)}
                  </td>
                  <td className={cn("text-right py-3 px-3 font-mono", pnlColor(s.total_return_pct))}>
                    {s.total_return_pct >= 0 ? "+" : ""}{s.total_return_pct.toFixed(2)}%
                  </td>
                  <td className="text-right py-3 px-3 font-mono text-(--color-negative)">
                    {s.max_drawdown_pct.toFixed(2)}%
                  </td>
                  <td className={cn("text-right py-3 px-3 font-mono", s.sharpe_ratio != null ? pnlColor(s.sharpe_ratio) : "text-(--color-text-secondary)")}>
                    {s.sharpe_ratio != null ? s.sharpe_ratio.toFixed(2) : "—"}
                  </td>
                  <td className={cn("text-right py-3 px-3 font-mono", s.profit_factor != null ? pnlColor(s.profit_factor - 1) : "text-(--color-text-secondary)")}>
                    {s.profit_factor != null ? s.profit_factor.toFixed(2) : "—"}
                  </td>
                  <td className="text-right py-3 px-3 font-mono text-(--color-text-primary)">
                    {s.active_signals}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function AnalyticsPage() {
  const { data, isLoading, error } = useEquityHistory();

  return (
    <div className="max-w-[1200px] mx-auto p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-(--color-text-primary)">
          Analytics
        </h1>
        <p className="text-sm text-(--color-text-secondary) mt-1">
          Portfolio performance, risk metrics, and strategy comparison
        </p>
      </div>

      {/* Strategy Comparison section */}
      <StrategyComparisonSection />

      {/* Metrics section */}
      {isLoading && (
        <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-6 flex items-center justify-center min-h-[200px]">
          <div className="text-center space-y-3">
            <div className="w-8 h-8 border-2 border-(--color-accent) border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="text-sm text-(--color-text-secondary)">
              Loading analytics...
            </p>
          </div>
        </div>
      )}

      {error && (
        <div className="bg-(--color-bg-surface) border border-(--color-negative)/30 rounded-xl p-6 flex items-center justify-center min-h-[200px]">
          <div className="text-center space-y-2">
            <p className="text-sm text-(--color-negative) font-medium">
              Failed to load analytics
            </p>
            <p className="text-xs text-(--color-text-secondary)">
              {error.message}
            </p>
          </div>
        </div>
      )}

      {data && (
        <>
          <MetricsGrid data={data} />
          <EquityCurve points={data.points} />
        </>
      )}

      {!isLoading && !error && !data && (
        <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-6 flex items-center justify-center min-h-[200px]">
          <div className="text-center space-y-2">
            <Activity className="w-10 h-10 text-(--color-text-secondary)/40 mx-auto" />
            <p className="text-sm text-(--color-text-secondary)">
              No analytics data available yet
            </p>
            <p className="text-xs text-(--color-text-secondary)/60">
              Start trading to generate performance metrics
            </p>
          </div>
        </div>
      )}

      {/* Correlation section */}
      <CorrelationMatrix />
    </div>
  );
}
