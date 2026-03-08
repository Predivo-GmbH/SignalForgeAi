import { useState } from "react";
import {
  TrendingUp,
  TrendingDown,
  Search,
  ChevronUp,
  ChevronDown,
} from "lucide-react";
import { fmtUsd, pnlColor } from "@/lib/format";
import { CRYPTO_NAME_MAP } from "@/lib/cryptoSymbols";
import { CoinIcon } from "@/components/portfolio/CoinIcon";
import type { PortfolioHolding } from "@/hooks/useSimulation";

interface SimulationPortfolioProps {
  holdings: PortfolioHolding[];
  totalValue: number;
  initialValue: number;
  totalPnl: number;
  totalPnlPct: number;
  type: "buy_and_hold" | "paper_trading";
}

type SortKey = "value" | "pnl" | "change" | "symbol";

export function SimulationPortfolio({
  holdings,
  totalValue,
  initialValue,
  totalPnl,
  totalPnlPct,
  type,
}: SimulationPortfolioProps) {
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("value");
  const [sortAsc, setSortAsc] = useState(false);

  const filtered = holdings.filter((h) => {
    if (!search) return true;
    const q = search.toLowerCase();
    const name = CRYPTO_NAME_MAP[h.symbol]?.toLowerCase() ?? "";
    return h.symbol.toLowerCase().includes(q) || name.includes(q);
  });

  const sorted = [...filtered].sort((a, b) => {
    let cmp = 0;
    switch (sortKey) {
      case "value":
        cmp = a.value_usd - b.value_usd;
        break;
      case "pnl":
        cmp = a.pnl_usd - b.pnl_usd;
        break;
      case "change":
        cmp = (a.change_24h_pct ?? 0) - (b.change_24h_pct ?? 0);
        break;
      case "symbol":
        cmp = a.symbol.localeCompare(b.symbol);
        break;
    }
    return sortAsc ? cmp : -cmp;
  });

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortAsc(!sortAsc);
    else {
      setSortKey(key);
      setSortAsc(false);
    }
  };

  const SortIcon = ({ k }: { k: SortKey }) =>
    sortKey === k ? (
      sortAsc ? (
        <ChevronUp className="w-3 h-3 inline ml-0.5" />
      ) : (
        <ChevronDown className="w-3 h-3 inline ml-0.5" />
      )
    ) : null;

  return (
    <div className="space-y-4">
      {/* Summary header */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <SummaryCard
          label="Total Value"
          value={fmtUsd(totalValue)}
        />
        <SummaryCard
          label="Initial Value"
          value={fmtUsd(initialValue)}
        />
        <SummaryCard
          label="Total P&L"
          value={`${totalPnl >= 0 ? "+" : ""}${fmtUsd(totalPnl)}`}
          color={pnlColor(totalPnl)}
        />
        <SummaryCard
          label="Return"
          value={`${totalPnlPct >= 0 ? "+" : ""}${totalPnlPct.toFixed(2)}%`}
          color={pnlColor(totalPnlPct)}
        />
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--color-text-secondary)]" />
        <input
          type="text"
          placeholder="Search assets..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-9 pr-3 py-2 rounded-lg bg-[var(--color-bg-elevated)] border border-[var(--color-border)] text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-secondary)] focus:outline-none focus:ring-1 focus:ring-[var(--color-accent)]"
        />
      </div>

      {/* Holdings table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-[11px] text-[var(--color-text-secondary)] uppercase tracking-wider border-b border-[var(--color-border)]">
              <th
                className="text-left py-2 px-2 cursor-pointer hover:text-[var(--color-text-primary)]"
                onClick={() => toggleSort("symbol")}
              >
                Asset
                <SortIcon k="symbol" />
              </th>
              <th className="text-right py-2 px-2">Quantity</th>
              {type === "paper_trading" && (
                <th className="text-right py-2 px-2">Change</th>
              )}
              <th className="text-right py-2 px-2">Price</th>
              <th
                className="text-right py-2 px-2 cursor-pointer hover:text-[var(--color-text-primary)]"
                onClick={() => toggleSort("value")}
              >
                Value
                <SortIcon k="value" />
              </th>
              <th
                className="text-right py-2 px-2 cursor-pointer hover:text-[var(--color-text-primary)]"
                onClick={() => toggleSort("pnl")}
              >
                P&L
                <SortIcon k="pnl" />
              </th>
              <th
                className="text-right py-2 px-2 cursor-pointer hover:text-[var(--color-text-primary)]"
                onClick={() => toggleSort("change")}
              >
                24h
                <SortIcon k="change" />
              </th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((h) => (
              <HoldingRow
                key={h.symbol}
                holding={h}
                totalValue={totalValue}
                showQuantityChange={type === "paper_trading"}
              />
            ))}
          </tbody>
        </table>
        {sorted.length === 0 && (
          <p className="text-center text-sm text-[var(--color-text-secondary)] py-8">
            {search ? "No matching assets" : "No holdings"}
          </p>
        )}
      </div>
    </div>
  );
}

function SummaryCard({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color?: string;
}) {
  return (
    <div className="bg-[var(--color-bg-elevated)]/50 rounded-lg p-3">
      <span className="text-[11px] text-[var(--color-text-secondary)] uppercase tracking-wider">
        {label}
      </span>
      <p
        className="text-sm font-semibold mt-1"
        style={{ color: color ?? "var(--color-text-primary)" }}
      >
        {value}
      </p>
    </div>
  );
}

function HoldingRow({
  holding: h,
  totalValue,
  showQuantityChange,
}: {
  holding: PortfolioHolding;
  totalValue: number;
  showQuantityChange: boolean;
}) {
  const alloc = totalValue > 0 ? (h.value_usd / totalValue) * 100 : 0;
  const name = CRYPTO_NAME_MAP[h.symbol] ?? h.symbol;

  return (
    <tr className="border-b border-[var(--color-border)]/50 hover:bg-[var(--color-bg-elevated)]/30 transition-colors">
      {/* Asset */}
      <td className="py-2.5 px-2">
        <div className="flex items-center gap-2">
          <CoinIcon symbol={h.symbol} imageUrl={h.image_url} size={24} />
          <div>
            <span className="font-medium text-[var(--color-text-primary)]">
              {h.symbol}
            </span>
            <span className="text-[11px] text-[var(--color-text-secondary)] ml-1.5 hidden sm:inline">
              {name}
            </span>
          </div>
        </div>
      </td>

      {/* Quantity */}
      <td className="text-right py-2.5 px-2 text-[var(--color-text-primary)] tabular-nums">
        {h.quantity < 1 ? h.quantity.toFixed(6) : h.quantity.toLocaleString(undefined, { maximumFractionDigits: 4 })}
      </td>

      {/* Quantity change (paper only) */}
      {showQuantityChange && (
        <td className="text-right py-2.5 px-2 tabular-nums">
          {h.quantity_change != null && h.quantity_change !== 0 ? (
            <span
              className="text-xs"
              style={{ color: pnlColor(h.quantity_change) }}
            >
              {h.quantity_change > 0 ? "+" : ""}
              {h.quantity_change < 1 && h.quantity_change > -1
                ? h.quantity_change.toFixed(6)
                : h.quantity_change.toLocaleString(undefined, { maximumFractionDigits: 4 })}
            </span>
          ) : (
            <span className="text-xs text-[var(--color-text-secondary)]">—</span>
          )}
        </td>
      )}

      {/* Price */}
      <td className="text-right py-2.5 px-2 text-[var(--color-text-primary)] tabular-nums">
        {fmtUsd(h.current_price)}
      </td>

      {/* Value + allocation */}
      <td className="text-right py-2.5 px-2">
        <div className="text-[var(--color-text-primary)] tabular-nums">
          {fmtUsd(h.value_usd)}
        </div>
        <div className="text-[10px] text-[var(--color-text-secondary)]">
          {alloc.toFixed(1)}%
        </div>
      </td>

      {/* P&L */}
      <td className="text-right py-2.5 px-2 tabular-nums">
        <div style={{ color: pnlColor(h.pnl_usd) }}>
          {h.pnl_usd >= 0 ? "+" : ""}
          {fmtUsd(h.pnl_usd)}
        </div>
        <div
          className="text-[11px]"
          style={{ color: pnlColor(h.pnl_pct) }}
        >
          {h.pnl_pct >= 0 ? "+" : ""}
          {h.pnl_pct.toFixed(2)}%
        </div>
      </td>

      {/* 24h change */}
      <td className="text-right py-2.5 px-2 tabular-nums">
        {h.change_24h_pct != null ? (
          <span
            className="flex items-center justify-end gap-0.5"
            style={{ color: pnlColor(h.change_24h_pct) }}
          >
            {h.change_24h_pct >= 0 ? (
              <TrendingUp className="w-3 h-3" />
            ) : (
              <TrendingDown className="w-3 h-3" />
            )}
            {h.change_24h_pct >= 0 ? "+" : ""}
            {h.change_24h_pct.toFixed(2)}%
          </span>
        ) : (
          <span className="text-[var(--color-text-secondary)]">—</span>
        )}
      </td>
    </tr>
  );
}
