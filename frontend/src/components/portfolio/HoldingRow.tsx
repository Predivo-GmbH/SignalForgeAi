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

export const SOURCE_STYLE: Record<string, { label: string; cls: string; colorVar: string }> = {
  binance: { label: "Binance", cls: "bg-(--color-palette-amber)/10 text-(--color-palette-amber)", colorVar: "--color-palette-amber" },
  kucoin: { label: "KuCoin", cls: "bg-(--color-palette-emerald)/10 text-(--color-palette-emerald)", colorVar: "--color-palette-emerald" },
  mexc: { label: "MEXC", cls: "bg-(--color-palette-blue)/10 text-(--color-palette-blue)", colorVar: "--color-palette-blue" },
  bitstamp: { label: "Bitstamp", cls: "bg-(--color-palette-green)/10 text-(--color-palette-green)", colorVar: "--color-palette-green" },
  cryptocom: { label: "Crypto.com", cls: "bg-(--color-palette-indigo)/10 text-(--color-palette-indigo)", colorVar: "--color-palette-indigo" },
  kraken: { label: "Kraken", cls: "bg-(--color-palette-violet)/10 text-(--color-palette-violet)", colorVar: "--color-palette-violet" },
  manual: { label: "Manual", cls: "bg-(--color-bg-elevated) text-(--color-text-secondary)", colorVar: "--color-muted" },
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
        "border-b border-(--color-border)/50 last:border-0 hover:bg-(--color-bg-elevated)/30 cursor-pointer min-h-[44px]",
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
            <span className="text-xs text-(--color-text-secondary) font-mono shrink-0">
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
          <span className="text-xs text-(--color-text-secondary) hidden sm:inline">
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
            <span className={cn("text-xs", pnlColor(c.pnlPct ?? 0))}>
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
                className={cn("text-xs font-medium px-2 py-0.5 rounded-full whitespace-nowrap", style.cls)}
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
              className="p-2.5 min-h-[44px] min-w-[44px] flex items-center justify-center rounded hover:bg-(--color-bg-elevated) text-(--color-text-secondary) hover:text-(--color-text-primary) transition-colors"
            >
              <Pencil className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => manualSources[0].id && onDelete(manualSources[0].id)}
              disabled={isDeletePending}
              className="p-2.5 min-h-[44px] min-w-[44px] flex items-center justify-center rounded hover:bg-(--color-negative)/10 text-(--color-text-secondary) hover:text-(--color-negative) transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </td>
    </tr>
  );
}
