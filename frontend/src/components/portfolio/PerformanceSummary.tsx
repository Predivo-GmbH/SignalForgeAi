import { Link } from "react-router-dom";
import { TrendingUp, Target, BarChart3, Activity, DollarSign } from "lucide-react";
import { useTradeStats } from "@/hooks/useTrades";
import { pnlColor, formatPnl } from "@/lib/format";
import { Tooltip } from "@/components/ui/Tooltip";

interface StatCardData {
  label: string;
  value: string;
  icon: typeof TrendingUp;
  colorClass?: string;
}

function StatCard({ label, value, icon: Icon, colorClass }: StatCardData) {
  return (
    <div className="bg-(--color-bg-elevated)/50 rounded-lg p-3 sm:p-4 space-y-1">
      <div className="flex items-center gap-1.5 sm:gap-2">
        <Icon className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-(--color-text-secondary)" />
        <span className="text-[10px] sm:text-xs text-(--color-text-secondary) uppercase tracking-normal sm:tracking-wider">{label}</span>
      </div>
      <p className={`text-base sm:text-xl font-semibold font-mono ${colorClass ?? "text-(--color-text-primary)"}`}>
        {value}
      </p>
    </div>
  );
}

export function PerformanceSummary() {
  const { data: stats, isLoading } = useTradeStats();

  if (isLoading || !stats) {
    return (
      <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-3 sm:p-5">
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2 sm:gap-3">
          {Array.from({ length: 5 }, (_, i) => (
            <div key={i} className="bg-(--color-bg-elevated)/50 rounded-lg p-3 sm:p-4 space-y-2">
              <div className="h-3 w-16 rounded bg-(--color-bg-elevated) animate-pulse" />
              <div className="h-6 w-20 rounded bg-(--color-bg-elevated) animate-pulse" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  const cards: StatCardData[] = [
    {
      label: "Total P&L",
      value: formatPnl(stats.total_pnl),
      icon: TrendingUp,
      colorClass: pnlColor(stats.total_pnl),
    },
    { label: "Win Rate", value: `${stats.win_rate}%`, icon: Target },
    { label: "Profit Factor", value: stats.profit_factor.toFixed(2), icon: BarChart3 },
    { label: "Total Trades", value: String(stats.total_trades), icon: Activity },
    {
      label: "Avg P&L",
      value: formatPnl(stats.avg_pnl),
      icon: DollarSign,
      colorClass: pnlColor(stats.avg_pnl),
    },
  ];

  return (
    <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-3 sm:p-5 space-y-3 sm:space-y-4">
      <div className="flex items-center justify-between">
        <Tooltip text="Key trading metrics including win rate, profit factor, and total P&L."><h3 className="text-sm font-semibold text-(--color-text-primary) cursor-help">Trading Performance</h3></Tooltip>
        <Link
          to="/analytics"
          className="text-xs font-medium text-(--color-accent) hover:text-(--color-accent)/80 transition-colors"
        >
          View Analytics →
        </Link>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2 sm:gap-3">
        {cards.map((c) => (
          <StatCard key={c.label} {...c} />
        ))}
      </div>
    </div>
  );
}
