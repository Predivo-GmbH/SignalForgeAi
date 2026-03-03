import { useState } from "react";
import {
  Loader2,
  Plus,
  X,
  Pencil,
  Trash2,
  Wallet,
} from "lucide-react";
import { cn } from "@/lib/cn";
import {
  useHoldings,
  useAddHolding,
  useUpdateHolding,
  useDeleteHolding,
} from "@/hooks/useHoldings";
import type { HoldingItem, ManualHoldingRequest } from "@/hooks/useHoldings";

/* ---- Source badge ---- */

const SOURCE_STYLE: Record<string, { label: string; cls: string }> = {
  binance: { label: "Binance", cls: "bg-amber-500/10 text-amber-500" },
  manual: { label: "Manual", cls: "bg-(--color-bg-elevated) text-(--color-text-secondary)" },
  trading: { label: "Trading", cls: "bg-(--color-accent)/10 text-(--color-accent)" },
};

function SourceBadge({ source }: { source: string }) {
  const style = SOURCE_STYLE[source] ?? { label: source, cls: "bg-(--color-bg-elevated) text-(--color-text-secondary)" };
  return (
    <span className={cn("text-[10px] font-medium px-2 py-0.5 rounded-full", style.cls)}>
      {style.label}
    </span>
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

/* ---- Main Card ---- */

export function HoldingsCard() {
  const { data, isLoading } = useHoldings();
  const deleteMutation = useDeleteHolding();
  const [showForm, setShowForm] = useState(false);
  const [editItem, setEditItem] = useState<HoldingItem | null>(null);

  if (isLoading) {
    return (
      <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-5 flex items-center justify-center min-h-[120px]">
        <Loader2 className="w-6 h-6 animate-spin text-(--color-accent)" />
      </div>
    );
  }

  const holdings = data?.holdings ?? [];

  return (
    <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-5 space-y-4">
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

      {/* Add form */}
      {showForm && (
        <HoldingForm onClose={() => setShowForm(false)} />
      )}

      {/* Edit form */}
      {editItem && (
        <HoldingForm
          initial={editItem}
          onClose={() => setEditItem(null)}
        />
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
                <th className="text-left text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider py-2 pr-4">Asset</th>
                <th className="text-right text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider py-2 px-4">Quantity</th>
                <th className="text-right text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider py-2 px-4">Avg Price</th>
                <th className="text-left text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider py-2 px-4">Source</th>
                <th className="text-left text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider py-2 px-4">Notes</th>
                <th className="py-2 w-16" />
              </tr>
            </thead>
            <tbody>
              {holdings.map((h, i) => (
                <tr key={`${h.source}-${h.symbol}-${i}`} className="border-b border-(--color-border)/50 last:border-0">
                  <td className="py-2.5 pr-4">
                    <span className="font-semibold text-(--color-text-primary)">{h.symbol}</span>
                  </td>
                  <td className="py-2.5 px-4 text-right font-mono tabular-nums text-(--color-text-primary)">
                    {h.quantity.toLocaleString("en-US", { maximumFractionDigits: 8 })}
                  </td>
                  <td className="py-2.5 px-4 text-right font-mono tabular-nums text-(--color-text-secondary)">
                    {h.avg_price != null ? `$${h.avg_price.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : "—"}
                  </td>
                  <td className="py-2.5 px-4">
                    <SourceBadge source={h.source} />
                  </td>
                  <td className="py-2.5 px-4 text-xs text-(--color-text-secondary) truncate max-w-[120px]">
                    {h.notes ?? "—"}
                  </td>
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
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
