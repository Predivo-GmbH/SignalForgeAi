import {
  Pencil,
  Trash2,
  TrendingUp,
  TrendingDown,
} from "lucide-react";
import { cn } from "@/lib/cn";
import { pnlColor, formatPrice, fmtUsd } from "@/lib/format";
import { CoinIcon } from "./CoinIcon";

/* ---- Shared constants ---- */

export const SOURCE_STYLE: Record<string, { label: string; cls: string; color: string }> = {
  binance: { label: "Binance", cls: "bg-amber-500/10 text-amber-500", color: "#f59e0b" },
  kucoin: { label: "KuCoin", cls: "bg-emerald-500/10 text-emerald-500", color: "#10b981" },
  mexc: { label: "MEXC", cls: "bg-blue-500/10 text-blue-500", color: "#3b82f6" },
  bitstamp: { label: "Bitstamp", cls: "bg-green-500/10 text-green-500", color: "#22c55e" },
  cryptocom: { label: "Crypto.com", cls: "bg-indigo-500/10 text-indigo-500", color: "#6366f1" },
  kraken: { label: "Kraken", cls: "bg-violet-500/10 text-violet-500", color: "#8b5cf6" },
  manual: { label: "Manual", cls: "bg-(--color-bg-elevated) text-(--color-text-secondary)", color: "#6b7280" },
};

/* ---- Shared types ---- */

export interface CombinedHolding {
  symbol: string;
  name: string;
  totalQty: number;
  currentPrice: number | null;
  totalValue: number;
  change24hPct: number | null;
  allocPct: number | null;
  sources: { source: string; notes: string | null; qty: number; id?: string; avgPrice?: number | null }[];
  marketCap: number | null;
  marketCapRank: number | null;
  volume24h: number | null;
  imageUrl: string | null;
  avgCost: number | null;
  pnlUsd: number | null;
  pnlPct: number | null;
}

/* ---- Helpers ---- */

function fmtCompact(val: number): string {
  if (val >= 1e12) return `$${(val / 1e12).toFixed(2)}T`;
  if (val >= 1e9) return `$${(val / 1e9).toFixed(2)}B`;
  if (val >= 1e6) return `$${(val / 1e6).toFixed(1)}M`;
  if (val >= 1e3) return `$${(val / 1e3).toFixed(1)}K`;
  return fmtUsd(val);
}

/* ---- Component ---- */

export function HoldingRow({
  c,
  index,
  reveal,
  onDetail,
  onEdit,
  onDelete,
  isDeletePending,
}: {
  c: CombinedHolding;
  index: number;
  reveal: boolean;
  onDetail: (symbol: string) => void;
  onEdit: (holdingId: string) => void;
  onDelete: (holdingId: string) => void;
  isDeletePending: boolean;
}) {
  const manualSources = c.sources.filter((s) => s.source === "manual" && s.id);

  return (
    <tr
      className={cn(
        "border-b border-(--color-border)/50 last:border-0 hover:bg-(--color-bg-elevated)/30 cursor-pointer",
        "transition-all duration-500 ease-out",
        reveal ? "opacity-100 translate-y-0" : "opacity-0 translate-y-2",
      )}
      style={{ transitionDelay: `${350 + index * 40}ms` }}
      onClick={() => onDetail(c.symbol)}
    >
      {/* Rank */}
      <td className="py-2.5 px-2 text-xs font-mono text-(--color-text-secondary) w-10 hidden sm:table-cell">
        {c.marketCapRank ?? "\u2014"}
      </td>

      {/* Coin: icon + name + symbol inline */}
      <td className="py-2.5 px-2 sm:px-3 overflow-hidden">
        <div className="flex items-center gap-2 sm:gap-2.5 min-w-0">
          <CoinIcon symbol={c.symbol} imageUrl={c.imageUrl} size={28} />
          <div className="min-w-0 flex items-baseline gap-1.5">
            <span className="font-semibold text-(--color-text-primary) text-sm truncate">
              {c.name}
            </span>
            <span className="text-[11px] text-(--color-text-secondary) font-mono shrink-0">
              {c.symbol}
            </span>
          </div>
        </div>
      </td>

      {/* Price */}
      <td className="py-2.5 px-3 text-right font-mono tabular-nums text-(--color-text-primary) text-xs hidden md:table-cell">
        {c.currentPrice != null ? formatPrice(c.currentPrice) : "\u2014"}
      </td>

      {/* 24h Change */}
      <td className="py-2.5 px-3 text-right hidden sm:table-cell">
        {c.change24hPct != null ? (
          <div className="flex items-center justify-end gap-1">
            {c.change24hPct >= 0 ? (
              <TrendingUp className={cn("w-3 h-3", pnlColor(c.change24hPct))} />
            ) : (
              <TrendingDown className={cn("w-3 h-3", pnlColor(c.change24hPct))} />
            )}
            <span className={cn("text-xs font-mono tabular-nums font-medium", pnlColor(c.change24hPct))}>
              {c.change24hPct >= 0 ? "+" : ""}{c.change24hPct.toFixed(2)}%
            </span>
          </div>
        ) : (
          <span className="text-xs text-(--color-text-secondary)">\u2014</span>
        )}
      </td>

      {/* Market Cap */}
      <td className="py-2.5 px-3 text-right hidden lg:table-cell">
        <span className="text-xs font-mono tabular-nums text-(--color-text-secondary)">
          {c.marketCap ? fmtCompact(c.marketCap) : "\u2014"}
        </span>
      </td>

      {/* Volume */}
      <td className="py-2.5 px-3 text-right hidden lg:table-cell">
        <span className="text-xs font-mono tabular-nums text-(--color-text-secondary)">
          {c.volume24h ? fmtCompact(c.volume24h) : "\u2014"}
        </span>
      </td>

      {/* Holdings: value + qty stacked */}
      <td className="py-2.5 px-2 sm:px-3 text-right">
        <div className="font-mono tabular-nums truncate sm:overflow-visible">
          <span className="text-xs font-semibold text-(--color-text-primary) block">
            {fmtUsd(c.totalValue)}
          </span>
          <span className="text-[10px] text-(--color-text-secondary) hidden sm:inline">
            {c.totalQty.toLocaleString("en-US", { maximumFractionDigits: 6 })} {c.symbol}
          </span>
        </div>
      </td>

      {/* PNL */}
      <td className="py-2.5 px-3 text-right hidden sm:table-cell">
        {c.pnlUsd != null ? (
          <div className="font-mono tabular-nums">
            <span className={cn("text-xs font-semibold block", pnlColor(c.pnlUsd))}>
              {c.pnlUsd >= 0 ? "+" : ""}{fmtUsd(Math.abs(c.pnlUsd))}
            </span>
            <span className={cn("text-[10px]", pnlColor(c.pnlPct ?? 0))}>
              {(c.pnlPct ?? 0) >= 0 ? "+" : ""}{(c.pnlPct ?? 0).toFixed(1)}%
            </span>
          </div>
        ) : (
          <span className="text-xs text-(--color-text-secondary)">\u2014</span>
        )}
      </td>

      {/* Sources */}
      <td className="py-2.5 px-3 hidden md:table-cell">
        <div className="flex items-center gap-1 flex-wrap">
          {c.sources.map((s, si) => {
            const style = SOURCE_STYLE[s.source] ?? { label: s.source, cls: "bg-(--color-bg-elevated) text-(--color-text-secondary)" };
            const label = s.notes && s.source === "manual" ? s.notes : style.label;
            return (
              <span
                key={`${s.source}-${si}`}
                className={cn("text-[10px] font-medium px-2 py-0.5 rounded-full whitespace-nowrap", style.cls)}
              >
                {label}
              </span>
            );
          })}
        </div>
      </td>

      {/* Actions */}
      <td className="py-2.5 hidden sm:table-cell" onClick={(e) => e.stopPropagation()}>
        {manualSources.length === 1 && c.sources.length === 1 && (
          <div className="flex items-center gap-1 justify-end">
            <button
              onClick={() => {
                if (manualSources[0].id) onEdit(manualSources[0].id);
              }}
              className="p-1 rounded hover:bg-(--color-bg-elevated) text-(--color-text-secondary) hover:text-(--color-text-primary) transition-colors"
            >
              <Pencil className="w-3 h-3" />
            </button>
            <button
              onClick={() => manualSources[0].id && onDelete(manualSources[0].id)}
              disabled={isDeletePending}
              className="p-1 rounded hover:bg-(--color-negative)/10 text-(--color-text-secondary) hover:text-(--color-negative) transition-colors"
            >
              <Trash2 className="w-3 h-3" />
            </button>
          </div>
        )}
      </td>
    </tr>
  );
}
