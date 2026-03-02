import {
  TrendingUp,
  Target,
  BarChart3,
  ArrowDown,
  Activity,
} from "lucide-react";
import type { BacktestResult } from "@/hooks/useBacktest";
import { Tooltip } from "@/components/ui/Tooltip";
import { cn } from "@/lib/cn";

function pnlColor(value: number | null | undefined): string {
  if (value == null) return "text-(--color-text-secondary)";
  return value >= 0 ? "text-(--color-positive)" : "text-(--color-negative)";
}

function MetricCard({
  label,
  tooltip,
  value,
  icon: Icon,
  valueColor,
}: {
  label: string;
  tooltip: string;
  value: string;
  icon: React.ComponentType<{ className?: string }>;
  valueColor?: string;
}) {
  return (
    <div className="bg-(--color-bg-elevated)/50 rounded-lg p-4 space-y-1">
      <div className="flex items-center gap-2">
        <Icon className="w-4 h-4 text-(--color-text-secondary)" />
        <span className="text-xs text-(--color-text-secondary) uppercase tracking-wider">
          {label}
        </span>
        <Tooltip icon text={tooltip} />
      </div>
      <p
        className={cn(
          "text-xl font-semibold font-mono",
          valueColor ?? "text-(--color-text-primary)"
        )}
      >
        {value}
      </p>
    </div>
  );
}

interface BacktestResultsProps {
  result: BacktestResult | null;
  isLoading: boolean;
  error: Error | null;
}

export function BacktestResults({
  result,
  isLoading,
  error,
}: BacktestResultsProps) {
  if (isLoading) {
    return (
      <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-6 flex items-center justify-center min-h-[400px]">
        <div className="text-center space-y-3">
          <div className="w-8 h-8 border-2 border-(--color-accent) border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-sm text-(--color-text-secondary)">
            Running backtest simulation...
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-(--color-bg-surface) border border-(--color-negative)/30 rounded-xl p-6 flex items-center justify-center min-h-[400px]">
        <div className="text-center space-y-2">
          <p className="text-sm text-(--color-negative) font-medium">Backtest failed</p>
          <p className="text-xs text-(--color-text-secondary)">{error.message}</p>
        </div>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-6 flex items-center justify-center min-h-[400px]">
        <div className="text-center space-y-2">
          <Activity className="w-10 h-10 text-(--color-text-secondary)/40 mx-auto" />
          <p className="text-sm text-(--color-text-secondary)">Run a backtest to see results</p>
          <p className="text-xs text-(--color-text-secondary)/60">Configure parameters and click "Run Backtest"</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-6 space-y-6">
      <h2 className="text-lg font-semibold text-(--color-text-primary)">Results</h2>

      <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
        <MetricCard
          label="Total Return"
          tooltip="The overall percentage gain or loss of the portfolio over the backtest period. A positive value means the strategy was profitable."
          value={`${result.total_return >= 0 ? "+" : ""}${result.total_return.toFixed(2)}%`}
          icon={TrendingUp}
          valueColor={pnlColor(result.total_return)}
        />
        <MetricCard
          label="Win Rate"
          tooltip="Percentage of trades that were profitable. Above 50% means more winners than losers, but a low win rate can still be profitable if winners are much larger than losers."
          value={`${result.win_rate.toFixed(1)}%`}
          icon={Target}
          valueColor={result.win_rate >= 50 ? "text-(--color-positive)" : "text-(--color-negative)"}
        />
        <MetricCard
          label="Profit Factor"
          tooltip="Ratio of gross profits to gross losses. Above 1.0 means profitable. Above 1.5 is good, above 2.0 is excellent. Below 1.0 means losses exceed profits."
          value={result.profit_factor.toFixed(2)}
          icon={BarChart3}
          valueColor={pnlColor(result.profit_factor - 1)}
        />
        <MetricCard
          label="Max Drawdown"
          tooltip="The largest peak-to-trough decline in portfolio value during the backtest. Shows the worst-case loss you would have experienced. Lower is better \u2014 above 20% is considered risky."
          value={`${result.max_drawdown.toFixed(2)}%`}
          icon={ArrowDown}
          valueColor="text-(--color-negative)"
        />
        <MetricCard
          label="Total Trades"
          tooltip="Number of completed trades (entry + exit) during the backtest period. More trades give more statistical confidence. Fewer than 10 trades may not be statistically reliable."
          value={result.total_trades.toString()}
          icon={Activity}
        />
        {result.sharpe_ratio != null && (
          <MetricCard
            label="Sharpe Ratio"
            tooltip="Risk-adjusted return metric. Measures return per unit of risk (volatility). Above 1.0 is good, above 2.0 is very good. Below 0 means the strategy lost money. Higher = better risk-adjusted performance."
            value={result.sharpe_ratio.toFixed(2)}
            icon={TrendingUp}
            valueColor={pnlColor(result.sharpe_ratio)}
          />
        )}
      </div>

      {result.equity_curve && result.equity_curve.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-(--color-text-secondary) uppercase tracking-wider">Equity Curve</h3>
          <div className="bg-(--color-bg-elevated)/50 rounded-lg p-4 h-48 flex items-center justify-center">
            <p className="text-xs text-(--color-text-secondary)">
              {result.equity_curve.length} data points &mdash; chart rendering available in Phase 5
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
