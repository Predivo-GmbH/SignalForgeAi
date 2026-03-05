import {
  TrendingUp,
  ArrowDown,
  Activity,
  Shield,
  Gauge,
  BarChart3,
} from "lucide-react";
import type { EquityHistory } from "@/hooks/useAnalytics";
import { cn } from "@/lib/cn";
import { pnlColor } from "@/lib/format";

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
    <div className="bg-(--color-bg-elevated)/50 rounded-lg p-3 sm:p-4 space-y-1">
      <div className="flex items-center gap-1.5 sm:gap-2">
        <Icon className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-(--color-text-secondary)" />
        <span className="text-[10px] sm:text-xs text-(--color-text-secondary) uppercase tracking-wider">
          {label}
        </span>
      </div>
      <p
        className={cn(
          "text-lg sm:text-xl font-semibold font-mono",
          valueColor ?? "text-(--color-text-primary)"
        )}
      >
        {value}
      </p>
    </div>
  );
}

interface MetricsGridProps {
  data: EquityHistory;
}

export function MetricsGrid({ data }: MetricsGridProps) {
  const formatRatio = (v: number | null): string =>
    v != null ? v.toFixed(2) : "N/A";

  return (
    <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-4 sm:p-6 space-y-3 sm:space-y-4">
      <h2 className="text-sm font-medium text-(--color-text-secondary) uppercase tracking-wider">
        Performance Metrics
      </h2>
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-2 sm:gap-3">
        <MetricCard
          label="Total Return"
          value={`${data.total_return_pct >= 0 ? "+" : ""}${data.total_return_pct.toFixed(2)}%`}
          icon={TrendingUp}
          valueColor={pnlColor(data.total_return_pct)}
        />
        <MetricCard
          label="Max Drawdown"
          value={`${data.max_drawdown_pct.toFixed(2)}%`}
          icon={ArrowDown}
          valueColor="text-(--color-negative)"
        />
        <MetricCard
          label="Sharpe Ratio"
          value={formatRatio(data.sharpe_ratio)}
          icon={BarChart3}
          valueColor={data.sharpe_ratio != null ? pnlColor(data.sharpe_ratio) : undefined}
        />
        <MetricCard
          label="Sortino Ratio"
          value={formatRatio(data.sortino_ratio)}
          icon={Shield}
          valueColor={data.sortino_ratio != null ? pnlColor(data.sortino_ratio) : undefined}
        />
        <MetricCard
          label="Calmar Ratio"
          value={formatRatio(data.calmar_ratio)}
          icon={Gauge}
          valueColor={data.calmar_ratio != null ? pnlColor(data.calmar_ratio) : undefined}
        />
        <MetricCard
          label="Equity Points"
          value={data.points.length.toString()}
          icon={Activity}
        />
      </div>
    </div>
  );
}
