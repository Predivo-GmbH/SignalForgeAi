import { useState } from "react";
import {
  ArrowUpRight,
  ArrowDownRight,
  ChevronLeft,
  ChevronRight,
  TrendingUp,
  Target,
  DollarSign,
  BarChart3,
} from "lucide-react";
import { useTrades, useTradeStats } from "@/hooks/useTrades";
import type { Trade } from "@/hooks/useTrades";
import { cn } from "@/lib/cn";

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

function pnlColor(value: number | null | undefined): string {
  if (value == null) return "text-(--color-text-secondary)";
  return value >= 0 ? "text-(--color-positive)" : "text-(--color-negative)";
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
              value={stats?.profit_factor?.toFixed(2) ?? "0.00"}
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
                    colSpan={11}
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
