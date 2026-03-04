import { useState } from "react";
import {
  Loader2,
  Plus,
  X,
  Pencil,
  Trash2,
  Wallet,
  TrendingUp,
  TrendingDown,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { cn } from "@/lib/cn";
import { pnlColor, formatPrice } from "@/lib/format";
import {
  useHoldings,
  useAddHolding,
  useUpdateHolding,
  useDeleteHolding,
} from "@/hooks/useHoldings";
import type { HoldingItem, ManualHoldingRequest } from "@/hooks/useHoldings";

/* ---- Constants ---- */

const ALLOCATION_COLORS = [
  "bg-blue-500",
  "bg-amber-500",
  "bg-emerald-500",
  "bg-violet-500",
  "bg-rose-500",
  "bg-cyan-500",
  "bg-orange-500",
  "bg-pink-500",
  "bg-teal-500",
  "bg-indigo-500",
];

const SOURCE_STYLE: Record<string, { label: string; cls: string }> = {
  binance: { label: "Binance", cls: "bg-amber-500/10 text-amber-500" },
  kucoin: { label: "KuCoin", cls: "bg-emerald-500/10 text-emerald-500" },
  mexc: { label: "MEXC", cls: "bg-blue-500/10 text-blue-500" },
  bitstamp: { label: "Bitstamp", cls: "bg-green-500/10 text-green-500" },
  cryptocom: { label: "Crypto.com", cls: "bg-indigo-500/10 text-indigo-500" },
  kraken: { label: "Kraken", cls: "bg-violet-500/10 text-violet-500" },
  manual: { label: "Manual", cls: "bg-(--color-bg-elevated) text-(--color-text-secondary)" },
  trading: { label: "Trading", cls: "bg-(--color-accent)/10 text-(--color-accent)" },
};

/* ---- Source badge ---- */

function SourceBadge({ source }: { source: string }) {
  const style = SOURCE_STYLE[source] ?? { label: source, cls: "bg-(--color-bg-elevated) text-(--color-text-secondary)" };
  return (
    <span className={cn("text-[10px] font-medium px-2 py-0.5 rounded-full whitespace-nowrap", style.cls)}>
      {style.label}
    </span>
  );
}

/* ---- Allocation Bar ---- */

function AllocationBar({ holdings }: { holdings: HoldingItem[] }) {
  const withValue = holdings.filter((h) => h.allocation_pct != null && h.allocation_pct > 0);
  if (withValue.length === 0) return null;

  return (
    <div className="space-y-2">
      {/* Stacked bar */}
      <div className="flex h-3 rounded-full overflow-hidden bg-(--color-bg-elevated)">
        {withValue.map((h, i) => (
          <div
            key={`${h.source}-${h.symbol}-${i}`}
            className={cn("h-full transition-all", ALLOCATION_COLORS[i % ALLOCATION_COLORS.length])}
            style={{ width: `${h.allocation_pct}%` }}
            title={`${h.symbol} — ${h.allocation_pct?.toFixed(1)}%`}
          />
        ))}
      </div>
      {/* Legend */}
      <div className="flex flex-wrap gap-x-4 gap-y-1">
        {withValue.slice(0, 8).map((h, i) => (
          <div key={`${h.source}-${h.symbol}-legend-${i}`} className="flex items-center gap-1.5">
            <div className={cn("w-2 h-2 rounded-full", ALLOCATION_COLORS[i % ALLOCATION_COLORS.length])} />
            <span className="text-[11px] text-(--color-text-secondary)">
              {h.symbol} <span className="font-mono">{h.allocation_pct?.toFixed(1)}%</span>
            </span>
          </div>
        ))}
        {withValue.length > 8 && (
          <span className="text-[11px] text-(--color-text-secondary)">
            +{withValue.length - 8} more
          </span>
        )}
      </div>
    </div>
  );
}

/* ---- Portfolio Summary ---- */

function PortfolioSummary({ holdings, totalValue }: { holdings: HoldingItem[]; totalValue: number | null }) {
  const assetCount = new Set(holdings.map((h) => h.symbol.toUpperCase())).size;
  const sourceCount = new Set(holdings.map((h) => h.source)).size;
  const sources = [...new Set(holdings.map((h) => h.source))];

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
        <div className="space-y-1">
          <p className="text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">
            Portfolio Value
          </p>
          <p className="text-3xl font-bold font-mono text-(--color-text-primary)">
            {totalValue != null
              ? `$${totalValue.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
              : "—"}
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-center">
            <p className="text-lg font-bold font-mono text-(--color-text-primary)">{assetCount}</p>
            <p className="text-[10px] font-medium text-(--color-text-secondary) uppercase tracking-wider">Assets</p>
          </div>
          <div className="w-px h-8 bg-(--color-border)" />
          <div className="text-center">
            <p className="text-lg font-bold font-mono text-(--color-text-primary)">{sourceCount}</p>
            <p className="text-[10px] font-medium text-(--color-text-secondary) uppercase tracking-wider">Sources</p>
          </div>
          <div className="w-px h-8 bg-(--color-border)" />
          <div className="flex gap-1.5">
            {sources.map((s) => (
              <SourceBadge key={s} source={s} />
            ))}
          </div>
        </div>
      </div>

      <AllocationBar holdings={holdings} />
    </div>
  );
}

/* ---- Add/Edit Form ---- */

function HoldingForm({
  initial,
  onClose,
}: {
  initial?: HoldingItem;
  onClose: () => void;
}) {
  const addMutation = useAddHolding();
  const updateMutation = useUpdateHolding();

  const [symbol, setSymbol] = useState(initial?.symbol ?? "");
  const [quantity, setQuantity] = useState(initial?.quantity?.toString() ?? "");
  const [price, setPrice] = useState(initial?.avg_price?.toString() ?? "");
  const [notes, setNotes] = useState(initial?.notes ?? "");

  const isEdit = !!initial?.id;
  const mutation = isEdit ? updateMutation : addMutation;
  const canSubmit = symbol.trim() && parseFloat(quantity) > 0 && !mutation.isPending;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const data: ManualHoldingRequest = {
      symbol: symbol.trim().toUpperCase(),
      quantity: parseFloat(quantity),
      purchase_price: price ? parseFloat(price) : null,
      notes: notes.trim() || null,
    };
    if (isEdit && initial?.id) {
      updateMutation.mutate({ id: initial.id, ...data }, { onSuccess: onClose });
    } else {
      addMutation.mutate(data, { onSuccess: onClose });
    }
  }

  return (
    <form onSubmit={handleSubmit} className="bg-(--color-bg-elevated)/50 rounded-lg p-4 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-(--color-text-primary)">
          {isEdit ? "Edit Holding" : "Add Holding"}
        </span>
        <button type="button" onClick={onClose} className="p-1 hover:bg-(--color-bg-elevated) rounded">
          <X className="w-3.5 h-3.5 text-(--color-text-secondary)" />
        </button>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div>
          <label className="block text-[10px] font-medium text-(--color-text-secondary) uppercase tracking-wider mb-1">Symbol</label>
          <input
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            placeholder="BTC"
            className="w-full bg-(--color-bg-surface) border border-(--color-border) rounded-lg px-2.5 py-1.5 text-sm text-(--color-text-primary) focus:outline-none focus:ring-2 focus:ring-(--color-accent)/50"
          />
        </div>
        <div>
          <label className="block text-[10px] font-medium text-(--color-text-secondary) uppercase tracking-wider mb-1">Quantity</label>
          <input
            type="number"
            step="any"
            min="0"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            placeholder="0.5"
            className="w-full bg-(--color-bg-surface) border border-(--color-border) rounded-lg px-2.5 py-1.5 text-sm font-mono text-(--color-text-primary) focus:outline-none focus:ring-2 focus:ring-(--color-accent)/50"
          />
        </div>
        <div>
          <label className="block text-[10px] font-medium text-(--color-text-secondary) uppercase tracking-wider mb-1">Cost/Unit (USD)</label>
          <input
            type="number"
            step="any"
            min="0"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            placeholder="Optional"
            className="w-full bg-(--color-bg-surface) border border-(--color-border) rounded-lg px-2.5 py-1.5 text-sm font-mono text-(--color-text-primary) focus:outline-none focus:ring-2 focus:ring-(--color-accent)/50"
          />
        </div>
        <div>
          <label className="block text-[10px] font-medium text-(--color-text-secondary) uppercase tracking-wider mb-1">Label</label>
          <input
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="e.g. Ledger"
            className="w-full bg-(--color-bg-surface) border border-(--color-border) rounded-lg px-2.5 py-1.5 text-sm text-(--color-text-primary) focus:outline-none focus:ring-2 focus:ring-(--color-accent)/50"
          />
        </div>
      </div>
      {mutation.isError && (
        <p className="text-xs text-(--color-negative)">
          {mutation.error instanceof Error ? mutation.error.message : "Failed to save"}
        </p>
      )}
      <button
        type="submit"
        disabled={!canSubmit}
        className="flex items-center gap-1.5 bg-(--color-accent) hover:bg-(--color-accent)/90 text-white text-xs font-medium rounded-lg px-3 py-1.5 transition-colors disabled:opacity-50"
      >
        {mutation.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : <Plus className="w-3 h-3" />}
        {isEdit ? "Update" : "Add"}
      </button>
    </form>
  );
}

/* ---- Sort helpers ---- */

type SortKey = "value" | "symbol" | "change" | "allocation";
type SortDir = "asc" | "desc";

function sortHoldings(holdings: HoldingItem[], key: SortKey, dir: SortDir): HoldingItem[] {
  const sorted = [...holdings];
  const m = dir === "asc" ? 1 : -1;
  sorted.sort((a, b) => {
    switch (key) {
      case "value":
        return m * ((a.value_usd ?? -1) - (b.value_usd ?? -1));
      case "symbol":
        return m * a.symbol.localeCompare(b.symbol);
      case "change":
        return m * ((a.change_24h_pct ?? 0) - (b.change_24h_pct ?? 0));
      case "allocation":
        return m * ((a.allocation_pct ?? 0) - (b.allocation_pct ?? 0));
      default:
        return 0;
    }
  });
  return sorted;
}

function SortHeader({
  label,
  sortKey,
  activeKey,
  activeDir,
  onSort,
  className,
}: {
  label: string;
  sortKey: SortKey;
  activeKey: SortKey;
  activeDir: SortDir;
  onSort: (key: SortKey) => void;
  className?: string;
}) {
  const isActive = sortKey === activeKey;
  return (
    <th
      className={cn(
        "text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider py-2 px-3 cursor-pointer select-none hover:text-(--color-text-primary) transition-colors",
        className,
      )}
      onClick={() => onSort(sortKey)}
    >
      <span className="inline-flex items-center gap-0.5">
        {label}
        {isActive && (activeDir === "desc" ? <ChevronDown className="w-3 h-3" /> : <ChevronUp className="w-3 h-3" />)}
      </span>
    </th>
  );
}

/* ---- Main Card ---- */

export function HoldingsCard() {
  const { data, isLoading } = useHoldings();
  const deleteMutation = useDeleteHolding();
  const [showForm, setShowForm] = useState(false);
  const [editItem, setEditItem] = useState<HoldingItem | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>("value");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  function handleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir((d) => (d === "desc" ? "asc" : "desc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  }

  if (isLoading) {
    return (
      <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-5 flex items-center justify-center min-h-[120px]">
        <Loader2 className="w-6 h-6 animate-spin text-(--color-accent)" />
      </div>
    );
  }

  const holdings = data?.holdings ?? [];
  const totalValue = data?.total_value_usd ?? null;
  const sorted = sortHoldings(holdings, sortKey, sortDir);

  return (
    <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-5 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Wallet className="w-4 h-4 text-(--color-accent)" />
          <h3 className="text-sm font-semibold text-(--color-text-primary)">Crypto Holdings</h3>
          {holdings.length > 0 && (
            <span className="text-[10px] font-medium text-(--color-text-secondary) bg-(--color-bg-elevated) px-2 py-0.5 rounded-full">
              {holdings.length}
            </span>
          )}
        </div>
        {!showForm && !editItem && (
          <button
            onClick={() => setShowForm(true)}
            className="flex items-center gap-1 text-xs font-medium text-(--color-accent) hover:text-(--color-accent)/80 transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            Add holding
          </button>
        )}
      </div>

      {/* Portfolio summary + allocation bar */}
      {holdings.length > 0 && (
        <PortfolioSummary holdings={sorted} totalValue={totalValue} />
      )}

      {/* Add form */}
      {showForm && <HoldingForm onClose={() => setShowForm(false)} />}

      {/* Edit form */}
      {editItem && (
        <HoldingForm initial={editItem} onClose={() => setEditItem(null)} />
      )}

      {/* Holdings table */}
      {holdings.length === 0 && !showForm ? (
        <div className="flex flex-col items-center justify-center py-6 gap-2">
          <Wallet className="w-8 h-8 text-(--color-text-secondary)/30" />
          <p className="text-sm text-(--color-text-secondary)">No holdings found</p>
          <p className="text-xs text-(--color-text-secondary)/60">
            Connect an exchange or add holdings manually
          </p>
          <button
            onClick={() => setShowForm(true)}
            className="text-xs font-medium text-(--color-accent) hover:underline mt-1"
          >
            Add your first holding
          </button>
        </div>
      ) : holdings.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-(--color-border)">
                <SortHeader label="Asset" sortKey="symbol" activeKey={sortKey} activeDir={sortDir} onSort={handleSort} className="text-left" />
                <th className="text-right text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider py-2 px-3">Qty</th>
                <th className="text-right text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider py-2 px-3">Price</th>
                <SortHeader label="Value" sortKey="value" activeKey={sortKey} activeDir={sortDir} onSort={handleSort} className="text-right" />
                <SortHeader label="Alloc" sortKey="allocation" activeKey={sortKey} activeDir={sortDir} onSort={handleSort} className="text-right" />
                <SortHeader label="24h" sortKey="change" activeKey={sortKey} activeDir={sortDir} onSort={handleSort} className="text-right" />
                <th className="text-left text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider py-2 px-3">Source</th>
                <th className="py-2 w-16" />
              </tr>
            </thead>
            <tbody>
              {sorted.map((h, i) => {
                return (
                  <tr
                    key={`${h.source}-${h.symbol}-${i}`}
                    className="border-b border-(--color-border)/50 last:border-0 hover:bg-(--color-bg-elevated)/30 transition-colors"
                  >
                    {/* Asset */}
                    <td className="py-2.5 px-3">
                      <div className="flex items-center gap-2">
                        <div
                          className={cn("w-2 h-2 rounded-full shrink-0", ALLOCATION_COLORS[i % ALLOCATION_COLORS.length])}
                        />
                        <div>
                          <span className="font-semibold text-(--color-text-primary)">{h.symbol}</span>
                          {h.notes && (
                            <span className="ml-1.5 text-[10px] text-(--color-text-secondary)">{h.notes}</span>
                          )}
                        </div>
                      </div>
                    </td>

                    {/* Quantity */}
                    <td className="py-2.5 px-3 text-right font-mono tabular-nums text-(--color-text-primary) text-xs">
                      {h.quantity.toLocaleString("en-US", { maximumFractionDigits: 8 })}
                    </td>

                    {/* Current Price */}
                    <td className="py-2.5 px-3 text-right font-mono tabular-nums text-(--color-text-secondary) text-xs">
                      {h.current_price != null ? formatPrice(h.current_price) : "—"}
                    </td>

                    {/* Value */}
                    <td className="py-2.5 px-3 text-right font-mono tabular-nums text-(--color-text-primary) text-xs font-semibold">
                      {h.value_usd != null
                        ? `$${h.value_usd.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                        : "—"}
                    </td>

                    {/* Allocation */}
                    <td className="py-2.5 px-3 text-right">
                      {h.allocation_pct != null ? (
                        <div className="flex items-center justify-end gap-2">
                          <div className="w-12 h-1.5 rounded-full bg-(--color-bg-elevated) overflow-hidden">
                            <div
                              className={cn("h-full rounded-full", ALLOCATION_COLORS[i % ALLOCATION_COLORS.length])}
                              style={{ width: `${Math.min(h.allocation_pct, 100)}%` }}
                            />
                          </div>
                          <span className="text-xs font-mono tabular-nums text-(--color-text-secondary) w-12 text-right">
                            {h.allocation_pct.toFixed(1)}%
                          </span>
                        </div>
                      ) : (
                        <span className="text-xs text-(--color-text-secondary)">—</span>
                      )}
                    </td>

                    {/* 24h Change */}
                    <td className="py-2.5 px-3 text-right">
                      {h.change_24h_pct != null ? (
                        <div className="flex items-center justify-end gap-1">
                          {h.change_24h_pct >= 0 ? (
                            <TrendingUp className={cn("w-3 h-3", pnlColor(h.change_24h_pct))} />
                          ) : (
                            <TrendingDown className={cn("w-3 h-3", pnlColor(h.change_24h_pct))} />
                          )}
                          <span className={cn("text-xs font-mono tabular-nums font-medium", pnlColor(h.change_24h_pct))}>
                            {h.change_24h_pct >= 0 ? "+" : ""}{h.change_24h_pct.toFixed(2)}%
                          </span>
                        </div>
                      ) : (
                        <span className="text-xs text-(--color-text-secondary)">—</span>
                      )}
                    </td>

                    {/* Source */}
                    <td className="py-2.5 px-3">
                      <SourceBadge source={h.source} />
                    </td>

                    {/* Actions */}
                    <td className="py-2.5">
                      {h.source === "manual" && h.id && (
                        <div className="flex items-center gap-1 justify-end">
                          <button
                            onClick={() => { setShowForm(false); setEditItem(h); }}
                            className="p-1 rounded hover:bg-(--color-bg-elevated) text-(--color-text-secondary) hover:text-(--color-text-primary) transition-colors"
                          >
                            <Pencil className="w-3 h-3" />
                          </button>
                          <button
                            onClick={() => h.id && deleteMutation.mutate(h.id)}
                            disabled={deleteMutation.isPending}
                            className="p-1 rounded hover:bg-(--color-negative)/10 text-(--color-text-secondary) hover:text-(--color-negative) transition-colors"
                          >
                            <Trash2 className="w-3 h-3" />
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>

            {/* Footer with total */}
            {totalValue != null && (
              <tfoot>
                <tr className="border-t border-(--color-border)">
                  <td colSpan={3} className="py-3 px-3 text-xs font-semibold text-(--color-text-secondary) uppercase tracking-wider">
                    Total
                  </td>
                  <td className="py-3 px-3 text-right font-mono tabular-nums text-(--color-text-primary) font-bold text-sm">
                    ${totalValue.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </td>
                  <td colSpan={4} />
                </tr>
              </tfoot>
            )}
          </table>
        </div>
      )}
    </div>
  );
}
