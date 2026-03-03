import { useState, useRef, useEffect } from "react";
import {
  ArrowUpRight,
  ArrowDownRight,
  ChevronLeft,
  ChevronRight,
  TrendingUp,
  Target,
  DollarSign,
  BarChart3,
  Info,
} from "lucide-react";
import { useTrades, useTradeStats } from "@/hooks/useTrades";
import type { Trade } from "@/hooks/useTrades";
import { cn } from "@/lib/cn";
import { pnlColor } from "@/lib/format";

const PAGE_SIZE = 20;

function formatPrice(value: number | null | undefined): string {
  if (value == null) return "--";
  return `$${value.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatPct(value: number | null | undefined): string {
  if (value == null) return "--";
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
}

function formatPnl(value: number | null | undefined): string {
  if (value == null) return "--";
  const sign = value >= 0 ? "+" : "";
  return `${sign}$${Math.abs(value).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatTime(iso: string | null | undefined): string {
  if (!iso) return "--";
  const d = new Date(iso);
  return d.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}


/* ----- Stat Card ----- */
function StatCard({
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
    <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-4 flex items-center gap-3">
      <div className="w-10 h-10 rounded-lg bg-(--color-accent-soft) flex items-center justify-center shrink-0">
        <Icon className="w-5 h-5 text-(--color-accent)" />
      </div>
      <div className="min-w-0">
        <p className="text-xs text-(--color-text-secondary) uppercase tracking-wider">
          {label}
        </p>
        <p className={cn("text-lg font-semibold font-mono", valueColor ?? "text-(--color-text-primary)")}>
          {value}
        </p>
      </div>
    </div>
  );
}

/* ----- Skeleton Row ----- */
function SkeletonRow() {
  return (
    <tr className="border-b border-(--color-border)/50">
      {Array.from({ length: 12 }).map((_, i) => (
        <td key={i} className="px-3 py-3">
          <div className="h-4 bg-(--color-bg-elevated) rounded animate-pulse" />
        </td>
      ))}
    </tr>
  );
}

/* ----- Reasoning Tooltip ----- */
function ReasoningTooltip({ trade }: { trade: Trade }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, [open]);

  const hasReasoning = trade.ai_reasoning || trade.triggers?.length || trade.regime;
  if (!hasReasoning) {
    return <span className="text-(--color-text-secondary)/40"><Info className="w-3.5 h-3.5" /></span>;
  }

  const triggerLabels: Record<string, string> = {
    macd_crossover: "MACD crossover",
    rsi_midline_cross: "RSI midline cross",
    engulfing_candle: "Engulfing candle",
    zone_reclaim: "Zone reclaim",
    stochastic_exit_extreme: "Stochastic extreme exit",
    bollinger_squeeze: "Bollinger squeeze",
    volume_spike: "Volume spike",
  };

  return (
    <div ref={ref} className="relative inline-flex">
      <button
        onClick={() => setOpen(!open)}
        className={cn(
          "p-0.5 rounded transition-colors",
          trade.ai_recommendation === "confirm"
            ? "text-(--color-positive) hover:bg-(--color-positive)/10"
            : trade.ai_recommendation === "caution"
              ? "text-(--color-warning) hover:bg-(--color-warning)/10"
              : "text-(--color-text-secondary) hover:bg-(--color-bg-elevated)",
        )}
        aria-label="Trade reasoning"
      >
        <Info className="w-3.5 h-3.5" />
      </button>
      {open && (
        <div className="absolute z-50 right-0 top-full mt-1 w-80 bg-(--color-bg-surface) border border-(--color-border) rounded-lg shadow-lg p-3 text-xs space-y-2">
          {/* Entry reasoning */}
          <div>
            <p className="font-semibold text-(--color-text-primary) mb-1">
              Entry: {trade.direction.toUpperCase()} {trade.symbol}
            </p>
            {trade.regime && (
              <p className="text-(--color-text-secondary)">
                <span className="font-medium">Regime:</span>{" "}
                <span className="capitalize">{trade.regime}</span>
              </p>
            )}
            {trade.triggers && trade.triggers.length > 0 && (
              <p className="text-(--color-text-secondary)">
                <span className="font-medium">Triggers:</span>{" "}
                {trade.triggers.map((t) => triggerLabels[t] || t).join(", ")}
              </p>
            )}
            {trade.confluence_score > 0 && (
              <p className="text-(--color-text-secondary)">
                <span className="font-medium">Confluence:</span> {trade.confluence_score}/100
              </p>
            )}
          </div>

          {/* AI assessment */}
          {(trade.ai_quality_score != null || trade.ai_reasoning) && (
            <div className="border-t border-(--color-border) pt-2">
              <p className="font-semibold text-(--color-text-primary) mb-1 flex items-center gap-1.5">
                AI Assessment
                {trade.ai_recommendation && (
                  <span
                    className={cn(
                      "px-1.5 py-0.5 rounded text-[10px] font-bold uppercase",
                      trade.ai_recommendation === "confirm"
                        ? "bg-(--color-positive)/15 text-(--color-positive)"
                        : trade.ai_recommendation === "caution"
                          ? "bg-(--color-warning)/15 text-(--color-warning)"
                          : "bg-(--color-negative)/15 text-(--color-negative)",
                    )}
                  >
                    {trade.ai_recommendation}
                  </span>
                )}
                {trade.ai_quality_score != null && (
                  <span className="text-(--color-text-secondary) font-normal">
                    (score: {trade.ai_quality_score})
                  </span>
                )}
              </p>
              {trade.ai_reasoning && (
                <p className="text-(--color-text-secondary) leading-relaxed">
                  {trade.ai_reasoning}
                </p>
              )}
            </div>
          )}

          {/* Exit reasoning */}
          {trade.exit_reason && (
            <div className="border-t border-(--color-border) pt-2">
              <p className="font-semibold text-(--color-text-primary) mb-1">Exit Reason</p>
              <p className="text-(--color-text-secondary)">
                {trade.exit_reason === "sell_signal"
                  ? "Pipeline generated a SELL signal — higher timeframe trend turned bearish, closing the position."
                  : trade.exit_reason === "stop_loss"
                    ? `Price hit the stop-loss at ${formatPrice(trade.stop_loss)}, limiting the downside risk.`
                    : trade.exit_reason === "take_profit"
                      ? `Price reached the take-profit target at ${formatPrice(trade.take_profit)}.`
                      : trade.exit_reason}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ----- Trade Row ----- */
function TradeRow({ trade }: { trade: Trade }) {
  const isLong = trade.direction === "long";
  return (
    <tr className="border-b border-(--color-border)/50 hover:bg-(--color-bg-elevated)/50 transition-colors">
      <td className="px-3 py-2.5 text-sm text-(--color-text-secondary) whitespace-nowrap">
        {formatTime(trade.exit_time ?? trade.entry_time)}
      </td>
      <td className="px-3 py-2.5 text-sm font-medium text-(--color-text-primary)">
        {trade.symbol}
      </td>
      <td className="px-3 py-2.5">
        <span
          className={cn(
            "inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold uppercase",
            isLong
              ? "bg-(--color-positive)/10 text-(--color-positive)"
              : "bg-(--color-negative)/10 text-(--color-negative)",
          )}
        >
          {isLong ? (
            <ArrowUpRight className="w-3 h-3" />
          ) : (
            <ArrowDownRight className="w-3 h-3" />
          )}
          {trade.direction}
        </span>
      </td>
      <td className="px-3 py-2.5 text-sm font-mono text-(--color-text-primary) text-right">
        {formatPrice(trade.entry_price)}
      </td>
      <td className="px-3 py-2.5 text-sm font-mono text-(--color-text-primary) text-right">
        {formatPrice(trade.exit_price)}
      </td>
      <td className="px-3 py-2.5 text-sm font-mono text-(--color-text-secondary) text-right">
        {trade.position_size?.toFixed(4) ?? "--"}
      </td>
      <td className={cn("px-3 py-2.5 text-sm font-mono text-right font-semibold", pnlColor(trade.pnl))}>
        {formatPnl(trade.pnl)}
      </td>
      <td className={cn("px-3 py-2.5 text-sm font-mono text-right", pnlColor(trade.pnl_pct))}>
        {formatPct(trade.pnl_pct)}
      </td>
      <td className="px-3 py-2.5 text-sm font-mono text-(--color-text-secondary) text-right">
        {trade.risk_reward != null ? trade.risk_reward.toFixed(2) : "--"}
      </td>
      <td className="px-3 py-2.5 text-sm font-mono text-right">
        {trade.confluence_score != null ? (
          <span
            className={cn(
              trade.confluence_score >= 7
                ? "text-(--color-positive)"
                : trade.confluence_score >= 4
                  ? "text-(--color-warning)"
                  : "text-(--color-text-secondary)",
            )}
          >
            {trade.confluence_score}
          </span>
        ) : (
          <span className="text-(--color-text-secondary)">--</span>
        )}
      </td>
      <td className="px-3 py-2.5 text-xs text-(--color-text-secondary) whitespace-nowrap">
        {trade.exit_reason ?? "--"}
      </td>
      <td className="px-3 py-2.5 text-center">
        <ReasoningTooltip trade={trade} />
      </td>
    </tr>
  );
}

/* ----- Main Page ----- */
export function TradesPage() {
  const [page, setPage] = useState(0);
  const offset = page * PAGE_SIZE;

  const { data: statsData, isLoading: statsLoading } = useTradeStats();
  const { data: tradesData, isLoading: tradesLoading } = useTrades(PAGE_SIZE, offset);

  const stats = statsData;
  const trades = tradesData?.trades ?? [];
  const total = tradesData?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="p-6 space-y-6 max-w-[1600px] mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-(--color-text-primary)">
          Trades
        </h1>
        <p className="text-sm text-(--color-text-secondary) mt-1">
          Execution log and performance metrics
        </p>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {statsLoading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-4 h-[72px] animate-pulse"
            />
          ))
        ) : (
          <>
            <StatCard
              label="Total Trades"
              value={stats?.total_trades?.toString() ?? "0"}
              icon={BarChart3}
            />
            <StatCard
              label="Win Rate"
              value={stats ? `${stats.win_rate.toFixed(1)}%` : "0%"}
              icon={Target}
              valueColor={
                stats && stats.win_rate >= 50
                  ? "text-(--color-positive)"
                  : "text-(--color-negative)"
              }
            />
            <StatCard
              label="Profit Factor"
              value={stats?.profit_factor != null ? (Number.isFinite(stats.profit_factor) ? stats.profit_factor.toFixed(2) : "\u221E") : "0.00"}
              icon={TrendingUp}
              valueColor={
                stats && stats.profit_factor >= 1
                  ? "text-(--color-positive)"
                  : "text-(--color-negative)"
              }
            />
            <StatCard
              label="Total P&L"
              value={formatPnl(stats?.total_pnl)}
              icon={DollarSign}
              valueColor={pnlColor(stats?.total_pnl)}
            />
          </>
        )}
      </div>

      {/* Trade table */}
      <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-(--color-border) bg-(--color-bg-elevated)/50">
                {[
                  "Time",
                  "Symbol",
                  "Dir",
                  "Entry",
                  "Exit",
                  "Size",
                  "P&L",
                  "P&L %",
                  "R:R",
                  "Score",
                  "Exit Reason",
                  "Info",
                ].map((h, i) => (
                  <th
                    key={i}
                    className="px-3 py-2.5 text-xs font-semibold text-(--color-text-secondary) uppercase tracking-wider whitespace-nowrap"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {tradesLoading ? (
                Array.from({ length: 8 }).map((_, i) => (
                  <SkeletonRow key={i} />
                ))
              ) : trades.length === 0 ? (
                <tr>
                  <td
                    colSpan={12}
                    className="px-3 py-16 text-center text-(--color-text-secondary)"
                  >
                    No trades recorded yet
                  </td>
                </tr>
              ) : (
                trades.map((trade) => (
                  <TradeRow key={trade.id} trade={trade} />
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {total > PAGE_SIZE && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-(--color-border)">
            <span className="text-sm text-(--color-text-secondary)">
              Showing {offset + 1}–{Math.min(offset + PAGE_SIZE, total)} of{" "}
              {total}
            </span>
            <div className="flex gap-1">
              <button
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                className="p-1.5 rounded-lg hover:bg-(--color-bg-elevated) disabled:opacity-30 transition-colors"
                aria-label="Previous page"
              >
                <ChevronLeft className="w-4 h-4 text-(--color-text-secondary)" />
              </button>
              <span className="flex items-center px-3 text-sm font-mono text-(--color-text-secondary)">
                {page + 1} / {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
                className="p-1.5 rounded-lg hover:bg-(--color-bg-elevated) disabled:opacity-30 transition-colors"
                aria-label="Next page"
              >
                <ChevronRight className="w-4 h-4 text-(--color-text-secondary)" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
