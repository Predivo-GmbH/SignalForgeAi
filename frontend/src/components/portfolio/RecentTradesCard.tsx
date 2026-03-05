import { Link } from "react-router-dom";
import { ArrowUpRight, ArrowDownRight, Loader2, ArrowUpDown } from "lucide-react";
import { useTrades } from "@/hooks/useTrades";
import { cn } from "@/lib/cn";
import { pnlColor } from "@/lib/format";
import { Tooltip } from "@/components/ui/Tooltip";

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

export function RecentTradesCard() {
  const { data, isLoading } = useTrades(5);

  if (isLoading) {
    return (
      <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-5 flex items-center justify-center flex-1 min-h-[160px]">
        <Loader2 className="w-5 h-5 animate-spin text-(--color-accent)" />
      </div>
    );
  }

  const trades = data?.trades ?? [];

  if (trades.length === 0) {
    return (
      <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-5 flex flex-col items-center justify-center gap-2 flex-1 min-h-[160px]">
        <ArrowUpDown className="w-6 h-6 text-(--color-text-secondary)/40" />
        <p className="text-xs text-(--color-text-secondary)">No trades yet</p>
      </div>
    );
  }

  return (
    <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-5 space-y-3 flex-1">
      <div className="flex items-center justify-between">
        <Tooltip text="The latest trades executed by your active strategies."><h3 className="text-sm font-semibold text-(--color-text-primary) cursor-help">Recent Trades</h3></Tooltip>
        <Link
          to="/trades"
          className="text-xs font-medium text-(--color-accent) hover:text-(--color-accent)/80 transition-colors"
        >
          View all →
        </Link>
      </div>

      <div className="space-y-1">
        {trades.map((t) => {
          const isLong = t.direction?.toUpperCase() === "LONG" || t.direction?.toUpperCase() === "BUY";
          const pnl = t.pnl ?? 0;
          const time = t.exit_time || t.entry_time || t.created_at;
          return (
            <div
              key={t.id}
              className="flex items-center gap-2.5 py-1.5 px-2 rounded-lg hover:bg-(--color-bg-elevated)/50 transition-colors"
            >
              <div className={cn(
                "w-6 h-6 rounded flex items-center justify-center shrink-0",
                isLong ? "bg-(--color-positive)/10" : "bg-(--color-negative)/10",
              )}>
                {isLong ? (
                  <ArrowUpRight className="w-3.5 h-3.5 text-(--color-positive)" />
                ) : (
                  <ArrowDownRight className="w-3.5 h-3.5 text-(--color-negative)" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-(--color-text-primary) truncate">
                  {t.symbol}
                </p>
              </div>
              <span className={cn("text-xs font-semibold font-mono tabular-nums", pnlColor(pnl))}>
                {pnl >= 0 ? "+" : ""}${pnl.toFixed(2)}
              </span>
              <span className="text-[10px] text-(--color-text-secondary) shrink-0 w-12 text-right">
                {timeAgo(time)}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
