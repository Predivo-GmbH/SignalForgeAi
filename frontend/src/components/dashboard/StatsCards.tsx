import { TrendingUp, Target, BarChart3, Activity } from "lucide-react";
import type { TradeStats } from "@/hooks/useTrades";
import { formatPnl } from "@/lib/format";

interface StatsCardsProps {
  stats: TradeStats | null | undefined;
}

interface StatCardData {
  label: string;
  value: string;
  icon: typeof TrendingUp;
  colorClass?: string;
}

export function StatsCards({ stats }: StatsCardsProps) {
  if (!stats) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }, (_, i) => (
          <div
            key={i}
            data-testid="stat-skeleton"
            className="bg-[var(--color-bg-surface)] rounded-xl border border-[var(--color-border)] p-5"
          >
            <div className="flex items-center gap-3 mb-3">
              <div className="h-10 w-10 rounded-lg bg-[var(--color-bg-elevated)] animate-pulse" />
              <div className="h-3 w-20 rounded bg-[var(--color-bg-elevated)] animate-pulse" />
            </div>
            <div className="h-7 w-24 rounded bg-[var(--color-bg-elevated)] animate-pulse" />
          </div>
        ))}
      </div>
    );
  }

  const pnlColor =
    stats.total_pnl >= 0
      ? "text-[var(--color-positive)]"
      : "text-[var(--color-negative)]";

  const cards: StatCardData[] = [
    {
      label: "Total P&L",
      value: formatPnl(stats.total_pnl),
      icon: TrendingUp,
      colorClass: pnlColor,
    },
    {
      label: "Win Rate",
      value: `${stats.win_rate}%`,
      icon: Target,
    },
    {
      label: "Profit Factor",
      value: stats.profit_factor.toFixed(2),
      icon: BarChart3,
    },
    {
      label: "Total Trades",
      value: String(stats.total_trades),
      icon: Activity,
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((card) => {
        const Icon = card.icon;
        return (
          <div
            key={card.label}
            className="bg-[var(--color-bg-surface)] rounded-xl border border-[var(--color-border)] p-5"
          >
            <div className="flex items-center gap-3 mb-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[var(--color-accent-soft)]">
                <Icon className="h-5 w-5 text-[var(--color-accent)]" />
              </div>
              <span className="text-sm text-[var(--color-text-secondary)]">
                {card.label}
              </span>
            </div>
            <span
              className={`text-2xl font-bold font-mono ${card.colorClass ?? "text-[var(--color-text-primary)]"}`}
            >
              {card.value}
            </span>
          </div>
        );
      })}
    </div>
  );
}
