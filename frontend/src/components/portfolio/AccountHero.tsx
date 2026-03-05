import { Link } from "react-router-dom";
import { TrendingUp, TrendingDown, Loader2, AlertTriangle, CheckCircle } from "lucide-react";
import { useAccountState, useDrawdownState } from "@/hooks/usePositions";
import { cn } from "@/lib/cn";
import { pnlColor } from "@/lib/format";
import { Tooltip } from "@/components/ui/Tooltip";

const LEVEL_CONFIG: Record<number, { label: string; color: string; bg: string }> = {
  0: { label: "Normal", color: "text-(--color-positive)", bg: "bg-(--color-positive)/10" },
  1: { label: "Warning", color: "text-amber-500", bg: "bg-amber-500/10" },
  2: { label: "Halt", color: "text-(--color-negative)", bg: "bg-(--color-negative)/10" },
  3: { label: "Emergency", color: "text-(--color-negative)", bg: "bg-(--color-negative)/20" },
};

export function AccountHero() {
  const { data: account, isLoading: accountLoading } = useAccountState();
  const { data: drawdown, isLoading: drawdownLoading } = useDrawdownState();

  if (accountLoading || drawdownLoading) {
    return (
      <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-6 flex items-center justify-center min-h-[120px]">
        <Loader2 className="w-6 h-6 animate-spin text-(--color-accent)" />
      </div>
    );
  }

  const equity = account?.equity ?? 10000;
  const dailyPnl = account?.daily_pnl ?? 0;
  const dailyPct = equity > 0 ? (dailyPnl / equity) * 100 : 0;
  const openCount = account?.open_positions ?? 0;
  const maxPositions = account?.max_positions ?? 5;

  const level = drawdown?.level ?? 0;
  const cfg = LEVEL_CONFIG[Math.min(level, 3)];
  const drawdownPct = drawdown?.drawdown_pct ?? 0;

  return (
    <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-4 sm:p-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        {/* Left: Equity + Daily PnL + Positions */}
        <div className="space-y-1.5">
          <Tooltip text="Your trading account balance tracked by the SignalForge engine, including daily P&L from automated trades.">
            <p className="text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider cursor-help">
              Account Equity
            </p>
          </Tooltip>
          <p className="text-2xl sm:text-3xl font-bold font-mono text-(--color-text-primary)">
            ${equity.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
            <div className="flex items-center gap-1.5">
              {dailyPnl >= 0 ? (
                <TrendingUp className={cn("w-3.5 h-3.5", pnlColor(dailyPnl))} />
              ) : (
                <TrendingDown className={cn("w-3.5 h-3.5", pnlColor(dailyPnl))} />
              )}
              <span className={cn("text-sm font-semibold font-mono", pnlColor(dailyPnl))}>
                {dailyPnl >= 0 ? "+" : ""}${dailyPnl.toFixed(2)}
              </span>
              <span className={cn("text-xs font-mono", pnlColor(dailyPnl))}>
                ({dailyPct >= 0 ? "+" : ""}{dailyPct.toFixed(2)}%)
              </span>
              <span className="text-xs text-(--color-text-secondary)">today</span>
            </div>
            <Tooltip text="Number of currently open trading positions out of the maximum allowed by your risk settings.">
              <span className="text-xs text-(--color-text-secondary) cursor-help">
                {openCount} / {maxPositions} positions
              </span>
            </Tooltip>
          </div>
        </div>

        {/* Right: Drawdown Status */}
        <Link
          to="/risk"
          className="flex flex-col items-start sm:items-end gap-2 shrink-0 hover:opacity-80 transition-opacity"
        >
          <div className={cn("flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-full", cfg.bg, cfg.color)}>
            {level === 0 ? (
              <CheckCircle className="w-3.5 h-3.5" />
            ) : (
              <AlertTriangle className="w-3.5 h-3.5" />
            )}
            {cfg.label}
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-(--color-text-secondary)">Drawdown</span>
            <span className={cn("text-sm font-semibold font-mono", drawdownPct > 5 ? "text-(--color-negative)" : "text-(--color-text-primary)")}>
              {drawdownPct.toFixed(2)}%
            </span>
          </div>
          <div className="w-32 h-1.5 rounded-full bg-(--color-bg-elevated) overflow-hidden">
            <div
              className={cn(
                "h-full rounded-full transition-all",
                drawdownPct > 10 ? "bg-(--color-negative)" : drawdownPct > 5 ? "bg-amber-500" : "bg-(--color-positive)",
              )}
              style={{ width: `${Math.min(drawdownPct * 5, 100)}%` }}
            />
          </div>
        </Link>
      </div>
    </div>
  );
}
