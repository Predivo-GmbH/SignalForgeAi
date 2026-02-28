import {
  TrendingUp,
  Target,
  BarChart3,
  ArrowDown,
  Activity,
} from "lucide-react";
import type { BacktestResult } from "@/hooks/useBacktest";
import { cn } from "@/lib/cn";

function pnlColor(value: number | null | undefined): string {
  if (value == null) return "text-(--color-text-secondary)";
  return value >= 0 ? "text-(--color-positive)" : "text-(--color-negative)";
}

function MetricCard({
  label,
  value,
  icon: Icon,
  valueColor,
}: {
  label: string;
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
          <p className="text-sm text-(--color-negative) font-medium">
            Backtest failed
          </p>
          <p className="text-xs text-(--color-text-secondary)">
            {error.message}
          </p>
        </div>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-6 flex items-center justify-center min-h-[400px]">
        <div className="text-center space-y-2">
          <Activity className="w-10 h-10 text-(--color-text-secondary)/40 mx-auto" />
          <p className="text-sm text-(--color-text-secondary)">
            Run a backtest to see results
          </p>
          <p className="text-xs text-(--color-text-secondary)/60">
            Configure parameters and click "Run Backtest"
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-6 space-y-6">
      <h2 className="text-lg font-semibold text-(--color-text-primary)">
        Results
      </h2>

      {/* Metrics grid */}
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
        <MetricCard
          label="Total Return"
          value={`${result.total_return >= 0 ? "+" : ""}${result.total_return.toFixed(2)}%`}
          icon={TrendingUp}
          valueColor={pnlColor(result.total_return)}
        />
        <MetricCard
          label="Win Rate"
          value={`${result.win_rate.toFixed(1)}%`}
          icon={Target}
          valueColor={
            result.win_rate >= 50
              ? "text-(--color-positive)"
              : "text-(--color-negative)"
          }
        />
        <MetricCard
          label="Profit Factor"
          value={result.profit_factor.toFixed(2)}
          icon={BarChart3}
          valueColor={pnlColor(result.profit_factor - 1)}
        />
        <MetricCard
          label="Max Drawdown"
          value={`${result.max_drawdown.toFixed(2)}%`}
          icon={ArrowDown}
          valueColor="text-(--color-negative)"
        />
        <MetricCard
          label="Total Trades"
          value={result.total_trades.toString()}
          icon={Activity}
        />
        {result.sharpe_ratio != null && (
          <MetricCard
            label="Sharpe Ratio"
            value={result.sharpe_ratio.toFixed(2)}
            icon={TrendingUp}
            valueColor={pnlColor(result.sharpe_ratio)}
          />
        )}
      </div>

      {/* Equity curve placeholder (if data provided) */}
      {result.equity_curve && result.equity_curve.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-(--color-text-secondary) uppercase tracking-wider">
            Equity Curve
          </h3>
          <div className="bg-(--color-bg-elevated)/50 rounded-lg p-4 h-48 flex items-center justify-center">
            <p className="text-xs text-(--color-text-secondary)">
              {result.equity_curve.length} data points &mdash; chart rendering
              available in Phase 5
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
