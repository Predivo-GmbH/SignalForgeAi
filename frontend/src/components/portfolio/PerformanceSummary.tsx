import { Link } from "react-router-dom";
import { TrendingUp, Target, BarChart3, Activity, DollarSign } from "lucide-react";
import { useTradeStats } from "@/hooks/useTrades";
import { pnlColor } from "@/lib/format";

interface StatCardData {
  label: string;
  value: string;
  icon: typeof TrendingUp;
  colorClass?: string;
}

function StatCard({ label, value, icon: Icon, colorClass }: StatCardData) {
  return (
    <div className="bg-(--color-bg-elevated)/50 rounded-lg p-4 space-y-1">
      <div className="flex items-center gap-2">
        <Icon className="w-4 h-4 text-(--color-text-secondary)" />
        <span className="text-xs text-(--color-text-secondary) uppercase tracking-wider">{label}</span>
      </div>
      <p className={`text-xl font-semibold font-mono ${colorClass ?? "text-(--color-text-primary)"}`}>
        {value}
      </p>
    </div>
  );
}

export function PerformanceSummary() {
  const { data: stats, isLoading } = useTradeStats();

  if (isLoading || !stats) {
    return (
      <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-5">
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          {Array.from({ length: 5 }, (_, i) => (
            <div key={i} className="bg-(--color-bg-elevated)/50 rounded-lg p-4 space-y-2">
              <div className="h-3 w-16 rounded bg-(--color-bg-elevated) animate-pulse" />
              <div className="h-6 w-20 rounded bg-(--color-bg-elevated) animate-pulse" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  const formatPnl = (v: number): string => {
    const prefix = v >= 0 ? "+$" : "-$";
    return `${prefix}${Math.abs(v).toFixed(2)}`;
  };

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
    <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-5 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-(--color-text-primary)">Trading Performance</h3>
        <Link
          to="/analytics"
          className="text-xs font-medium text-(--color-accent) hover:text-(--color-accent)/80 transition-colors"
        >
          View Analytics →
        </Link>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {cards.map((c) => (
          <StatCard key={c.label} {...c} />
        ))}
      </div>
    </div>
  );
}
