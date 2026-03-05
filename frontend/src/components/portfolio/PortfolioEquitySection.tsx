import { Link } from "react-router-dom";
import { TrendingUp, ArrowDown, BarChart3, Loader2, Activity } from "lucide-react";
import { useEquityHistory } from "@/hooks/useAnalytics";
import { EquityCurve } from "@/components/analytics/EquityCurve";
import { cn } from "@/lib/cn";
import { pnlColor } from "@/lib/format";
import { Tooltip } from "@/components/ui/Tooltip";

export function PortfolioEquitySection() {
  const { data, isLoading } = useEquityHistory();

  if (isLoading) {
    return (
      <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-5 flex items-center justify-center min-h-[380px]">
        <Loader2 className="w-6 h-6 animate-spin text-(--color-accent)" />
      </div>
    );
  }

  if (!data || data.points.length === 0) {
    return (
      <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-5 flex flex-col items-center justify-center min-h-[380px] gap-3">
        <Activity className="w-10 h-10 text-(--color-text-secondary)/40" />
        <p className="text-sm text-(--color-text-secondary)">No equity data yet</p>
        <p className="text-xs text-(--color-text-secondary)/60">
          Start trading to see your portfolio performance over time
        </p>
      </div>
    );
  }

  const formatRatio = (v: number | null): string => (v != null ? v.toFixed(2) : "N/A");

  return (
    <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-3 sm:p-5 space-y-3 sm:space-y-4 overflow-hidden">
      <div className="flex items-center justify-between">
        <Tooltip text="Historical growth of your trading account over time, showing returns and drawdowns."><h3 className="text-sm font-semibold text-(--color-text-primary) cursor-help">Equity Curve</h3></Tooltip>
        <Link
          to="/analytics"
          className="text-xs font-medium text-(--color-accent) hover:text-(--color-accent)/80 transition-colors"
        >
          View Analytics →
        </Link>
      </div>

      <div className="h-[200px] sm:h-[280px]">
        <EquityCurve points={data.points} />
      </div>

      {/* Inline metrics row */}
      <div className="grid grid-cols-3 gap-1.5 sm:gap-3">
        <div className="bg-(--color-bg-elevated)/50 rounded-lg p-2 sm:p-3 space-y-0.5">
          <div className="flex items-center gap-1 sm:gap-1.5">
            <TrendingUp className="w-3 h-3 sm:w-3.5 sm:h-3.5 text-(--color-text-secondary)" />
            <span className="text-[9px] sm:text-[10px] text-(--color-text-secondary) uppercase tracking-wider">Return</span>
          </div>
          <p className={cn("text-sm sm:text-base font-semibold font-mono", pnlColor(data.total_return_pct))}>
            {data.total_return_pct >= 0 ? "+" : ""}{data.total_return_pct.toFixed(2)}%
          </p>
        </div>
        <div className="bg-(--color-bg-elevated)/50 rounded-lg p-2 sm:p-3 space-y-0.5">
          <div className="flex items-center gap-1 sm:gap-1.5">
            <ArrowDown className="w-3 h-3 sm:w-3.5 sm:h-3.5 text-(--color-text-secondary)" />
            <span className="text-[9px] sm:text-[10px] text-(--color-text-secondary) uppercase tracking-wider">Max DD</span>
          </div>
          <p className="text-sm sm:text-base font-semibold font-mono text-(--color-negative)">
            {data.max_drawdown_pct.toFixed(2)}%
          </p>
        </div>
        <div className="bg-(--color-bg-elevated)/50 rounded-lg p-2 sm:p-3 space-y-0.5">
          <div className="flex items-center gap-1 sm:gap-1.5">
            <BarChart3 className="w-3 h-3 sm:w-3.5 sm:h-3.5 text-(--color-text-secondary)" />
            <span className="text-[9px] sm:text-[10px] text-(--color-text-secondary) uppercase tracking-wider">Sharpe</span>
          </div>
          <p className={cn("text-sm sm:text-base font-semibold font-mono", pnlColor(data.sharpe_ratio))}>
            {formatRatio(data.sharpe_ratio)}
          </p>
        </div>
      </div>
    </div>
  );
}
