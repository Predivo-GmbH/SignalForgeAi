import { useState } from "react";
import {
  TrendingUp,
  Target,
  BarChart3,
  ArrowDown,
  Activity,
  ChevronUp,
  ChevronDown,
  ShieldCheck,
  BrainCircuit,
} from "lucide-react";
import { Tooltip } from "@/components/ui/Tooltip";
import { cn } from "@/lib/cn";
import { pnlColor } from "@/lib/format";
import type {
  StrategyBacktestResult,
  SymbolResult,
} from "@/hooks/useStrategyBacktest";

const PRESET_LABELS: Record<string, string> = {
  conservative_swing: "Conservative Swing",
  balanced_momentum: "Balanced Momentum",
  aggressive_scalper: "Aggressive Scalper",
};


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
    <div className="bg-(--color-bg-elevated)/50 rounded-lg p-3 sm:p-4 space-y-1">
      <div className="flex items-center gap-2">
        <Icon className="w-4 h-4 text-(--color-text-secondary)" aria-hidden="true" />
        <Tooltip text={tooltip}>
          <span className="text-xs text-(--color-text-secondary) uppercase tracking-wider cursor-help">
            {label}
          </span>
        </Tooltip>
      </div>
      <p
        className={cn(
          "text-xl font-semibold font-mono",
          valueColor ?? "text-(--color-text-primary)",
        )}
      >
        {value}
      </p>
    </div>
  );
}

type SortKey = keyof SymbolResult;
type SortDir = "asc" | "desc";

interface StrategyBacktestResultsProps {
  result: StrategyBacktestResult | null;
  isLoading: boolean;
  error: Error | null;
}

export function StrategyBacktestResults({
  result,
  isLoading,
  error,
}: StrategyBacktestResultsProps) {
  const [sortKey, setSortKey] = useState<SortKey>("total_return");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  if (isLoading) {
    return (
      <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-4 sm:p-6 flex items-center justify-center min-h-[400px]" role="status" aria-live="polite">
        <div className="text-center space-y-3">
          <div className="w-8 h-8 border-2 border-(--color-accent) border-t-transparent rounded-full animate-spin mx-auto" aria-hidden="true" />
          <p className="text-sm text-(--color-text-secondary)">
            Validating strategy across all symbols...
          </p>
          <p className="text-xs text-(--color-text-secondary)/60">
            This may take a minute for multi-symbol strategies
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-(--color-bg-surface) border border-(--color-negative)/30 rounded-xl p-4 sm:p-6 flex items-center justify-center min-h-[400px]" role="alert">
        <div className="text-center space-y-2">
          <p className="text-sm text-(--color-negative) font-medium">
            Strategy validation failed
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
      <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-4 sm:p-6 flex items-center justify-center min-h-[400px]">
        <div className="text-center space-y-2">
          <ShieldCheck className="w-10 h-10 text-(--color-text-secondary)/40 mx-auto" aria-hidden="true" />
          <p className="text-sm text-(--color-text-secondary)">
            Select a strategy and run validation
          </p>
          <p className="text-xs text-(--color-text-secondary)/60">
            Test if an AI Advisor strategy would have worked historically
          </p>
        </div>
      </div>
    );
  }

  const { portfolio, per_symbol, config_summary } = result;

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  }

  const sorted = [...per_symbol].sort((a, b) => {
    const aVal = a[sortKey] ?? 0;
    const bVal = b[sortKey] ?? 0;
    if (typeof aVal === "string" && typeof bVal === "string") {
      return sortDir === "asc"
        ? aVal.localeCompare(bVal)
        : bVal.localeCompare(aVal);
    }
    return sortDir === "asc"
      ? (aVal as number) - (bVal as number)
      : (bVal as number) - (aVal as number);
  });

  const SortIcon = sortDir === "asc" ? ChevronUp : ChevronDown;

  return (
    <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-4 sm:p-6 space-y-6">
      {/* Strategy header */}
      <div className="space-y-2">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold text-(--color-text-primary)">
            {result.strategy_name}
          </h2>
          <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-(--color-accent)/10 text-(--color-accent)">
            {PRESET_LABELS[result.preset] ?? result.preset}
          </span>
          {result.ai_enhanced && (
            <span className="flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full bg-(--color-palette-violet)/10 text-(--color-palette-violet)">
              <BrainCircuit className="w-3 h-3" aria-hidden="true" />
              AI Enhanced
            </span>
          )}
        </div>
        <p className="text-xs text-(--color-text-secondary)">
          {result.symbols_count} symbols &middot; {result.days} days &middot;
          Confluence {config_summary.min_confluence} &middot; Risk{" "}
          {(config_summary.max_risk_per_trade * 100).toFixed(0)}%/trade &middot;
          ATR &times;{config_summary.atr_sl_multiplier}
        </p>
      </div>

      {/* Portfolio metrics */}
      <div>
        <Tooltip text="Aggregated performance across all symbols in this backtest. Shows how the strategy would have performed as a complete portfolio.">
          <h3 className="text-sm font-medium text-(--color-text-secondary) uppercase tracking-wider mb-3 cursor-help">
            Portfolio Performance
          </h3>
        </Tooltip>
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
          <MetricCard
            label="Total Return"
            tooltip="Overall portfolio return across all symbols combined, over the backtest period."
            value={`${portfolio.total_return >= 0 ? "+" : ""}${portfolio.total_return.toFixed(2)}%`}
            icon={TrendingUp}
            valueColor={pnlColor(portfolio.total_return)}
          />
          <MetricCard
            label="Win Rate"
            tooltip="Percentage of profitable trades across all symbols. Weighted by trade count per symbol."
            value={`${portfolio.win_rate.toFixed(1)}%`}
            icon={Target}
            valueColor={
              portfolio.win_rate >= 50
                ? "text-(--color-positive)"
                : "text-(--color-negative)"
            }
          />
          <MetricCard
            label="Profit Factor"
            tooltip="Average ratio of gross profits to gross losses across symbols. Above 1.5 is good."
            value={portfolio.profit_factor.toFixed(2)}
            icon={BarChart3}
            valueColor={pnlColor(portfolio.profit_factor - 1)}
          />
          <MetricCard
            label="Max Drawdown"
            tooltip="Largest peak-to-trough decline in the combined portfolio value."
            value={`${portfolio.max_drawdown.toFixed(2)}%`}
            icon={ArrowDown}
            valueColor="text-(--color-negative)"
          />
          <MetricCard
            label="Total Trades"
            tooltip="Total number of completed trades across all symbols."
            value={portfolio.total_trades.toString()}
            icon={Activity}
          />
          {portfolio.sharpe_ratio != null && (
            <MetricCard
              label="Sharpe Ratio"
              tooltip="Portfolio-level risk-adjusted return. Above 1.0 is good, above 2.0 is excellent."
              value={portfolio.sharpe_ratio.toFixed(2)}
              icon={TrendingUp}
              valueColor={pnlColor(portfolio.sharpe_ratio)}
            />
          )}
        </div>
      </div>

      {/* AI Enhancement metrics */}
      {result.ai_enhanced && portfolio.ai_calls != null && portfolio.ai_calls > 0 && (
        <div className="flex items-center gap-4 px-1">
          <div className="flex items-center gap-1.5 text-xs">
            <BrainCircuit className="w-3.5 h-3.5 text-(--color-palette-violet)" aria-hidden="true" />
            <span className="text-(--color-text-secondary)">AI Quality Assessment</span>
          </div>
          <span className="text-xs font-mono text-(--color-text-primary)">
            {portfolio.ai_calls} signals evaluated
          </span>
          {portfolio.ai_rejections != null && portfolio.ai_rejections > 0 && (
            <span className="text-xs font-mono text-(--color-negative)">
              {portfolio.ai_rejections} rejected as traps
            </span>
          )}
        </div>
      )}

      {/* Per-symbol breakdown */}
      {sorted.length > 0 && (
        <div>
          <Tooltip text="Individual performance for each symbol tested. Sort columns to find the best and worst performers.">
            <h3 className="text-sm font-medium text-(--color-text-secondary) uppercase tracking-wider mb-3 cursor-help">
              Per-Symbol Breakdown
            </h3>
          </Tooltip>
          <div className="overflow-x-auto relative">
            <div className="absolute right-0 top-0 bottom-0 w-8 bg-gradient-to-l from-(--color-bg-surface) pointer-events-none z-10" />
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-(--color-border)">
                  {(
                    [
                      ["symbol", "Symbol"],
                      ["total_return", "Return %"],
                      ["win_rate", "Win Rate"],
                      ["total_trades", "Trades"],
                      ["profit_factor", "PF"],
                      ["max_drawdown", "Drawdown"],
                      ["sharpe_ratio", "Sharpe"],
                    ] as [SortKey, string][]
                  ).map(([key, label]) => (
                    <th
                      key={key}
                      onClick={() => toggleSort(key)}
                      className={cn(
                        "px-3 py-2 min-h-[44px] text-left text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider cursor-pointer hover:text-(--color-text-primary) select-none",
                        key === "profit_factor" && "hidden sm:table-cell",
                        key === "max_drawdown" && "hidden sm:table-cell",
                        key === "sharpe_ratio" && "hidden md:table-cell",
                      )}
                    >
                      <span className="inline-flex items-center gap-1">
                        {label}
                        {sortKey === key && (
                          <SortIcon className="w-3 h-3" />
                        )}
                      </span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sorted.map((sym) => (
                  <tr
                    key={sym.symbol}
                    className="border-b border-(--color-border)/50 hover:bg-(--color-bg-elevated)/30"
                  >
                    <td className="px-3 py-2 font-mono font-medium text-(--color-text-primary)">
                      {sym.symbol}
                    </td>
                    <td
                      className={cn(
                        "px-3 py-2 font-mono",
                        pnlColor(sym.total_return),
                      )}
                    >
                      {sym.total_return >= 0 ? "+" : ""}
                      {sym.total_return.toFixed(2)}%
                    </td>
                    <td
                      className={cn(
                        "px-3 py-2 font-mono",
                        sym.win_rate >= 50
                          ? "text-(--color-positive)"
                          : "text-(--color-negative)",
                      )}
                    >
                      {sym.win_rate.toFixed(1)}%
                    </td>
                    <td className="px-3 py-2 font-mono text-(--color-text-primary)">
                      {sym.total_trades}
                    </td>
                    <td
                      className={cn(
                        "px-3 py-2 font-mono hidden sm:table-cell",
                        pnlColor((sym.profit_factor ?? 0) - 1),
                      )}
                    >
                      {sym.profit_factor?.toFixed(2) ?? "—"}
                    </td>
                    <td className="px-3 py-2 font-mono text-(--color-negative) hidden sm:table-cell">
                      {sym.max_drawdown.toFixed(2)}%
                    </td>
                    <td
                      className={cn(
                        "px-3 py-2 font-mono hidden md:table-cell",
                        pnlColor(sym.sharpe_ratio),
                      )}
                    >
                      {sym.sharpe_ratio?.toFixed(2) ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Equity curve placeholder */}
      {portfolio.equity_curve && portfolio.equity_curve.length > 0 && (
        <div className="space-y-2">
          <Tooltip text="Visual timeline of how portfolio value changed throughout the backtest period. Shows the growth trajectory and drawdown events.">
            <h3 className="text-sm font-medium text-(--color-text-secondary) uppercase tracking-wider cursor-help">
              Combined Equity Curve
            </h3>
          </Tooltip>
          <div className="bg-(--color-bg-elevated)/50 rounded-lg p-4 h-48 flex items-center justify-center">
            <p className="text-xs text-(--color-text-secondary)">
              {portfolio.equity_curve.length} data points &mdash; chart
              rendering available in Phase 5
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
