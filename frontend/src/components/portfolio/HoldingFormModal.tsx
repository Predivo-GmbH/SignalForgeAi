import { useState } from "react";
import { Loader2, Plus, X } from "lucide-react";
import {
  useAddHolding,
  useUpdateHolding,
} from "@/hooks/useHoldings";
import type { HoldingItem, ManualHoldingRequest } from "@/hooks/useHoldings";
import { SymbolAutocomplete } from "./SymbolAutocomplete";

export function HoldingForm({
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
    <form onSubmit={handleSubmit} className="bg-(--color-bg-elevated)/50 rounded-lg p-3 sm:p-4 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-(--color-text-primary)">
          {isEdit ? "Edit Holding" : "Add Holding"}
        </span>
        <button type="button" onClick={onClose} aria-label="Close form" className="p-2.5 min-h-[44px] min-w-[44px] flex items-center justify-center hover:bg-(--color-bg-elevated) rounded">
          <X className="w-3.5 h-3.5 text-(--color-text-secondary)" aria-hidden="true" />
        </button>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-3">
        <div>
          <label className="block text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider mb-1">Symbol</label>
          <SymbolAutocomplete value={symbol} onChange={setSymbol} />
        </div>
        <div>
          <label htmlFor="holding-quantity" className="block text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider mb-1">Quantity</label>
          <input
            id="holding-quantity"
            type="number"
            step="any"
            min="0"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            placeholder="0.5"
            className="w-full bg-(--color-bg-surface) border border-(--color-border) rounded-lg px-2.5 py-1.5 min-h-[44px] text-base sm:text-sm font-mono text-(--color-text-primary) focus:outline-none focus:ring-2 focus:ring-(--color-accent)/50"
          />
        </div>
        <div>
          <label htmlFor="holding-cost" className="block text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider mb-1">Cost/Unit (USD)</label>
          <input
            id="holding-cost"
            type="number"
            step="any"
            min="0"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            placeholder="Optional"
            className="w-full bg-(--color-bg-surface) border border-(--color-border) rounded-lg px-2.5 py-1.5 min-h-[44px] text-base sm:text-sm font-mono text-(--color-text-primary) focus:outline-none focus:ring-2 focus:ring-(--color-accent)/50"
          />
        </div>
        <div>
          <label htmlFor="holding-label" className="block text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider mb-1">Label</label>
          <input
            id="holding-label"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="e.g. Ledger"
            className="w-full bg-(--color-bg-surface) border border-(--color-border) rounded-lg px-2.5 py-1.5 min-h-[44px] text-base sm:text-sm text-(--color-text-primary) focus:outline-none focus:ring-2 focus:ring-(--color-accent)/50"
          />
        </div>
      </div>
      {mutation.isError && (
        <p className="text-xs text-(--color-negative)" role="alert">
          {mutation.error instanceof Error ? mutation.error.message : "Failed to save"}
        </p>
      )}
      <button
        type="submit"
        disabled={!canSubmit}
        className="flex items-center gap-1.5 bg-(--color-accent) hover:bg-(--color-accent)/90 text-white text-xs font-medium rounded-lg px-3 py-1.5 min-h-[44px] transition-colors disabled:opacity-50"
      >
        {mutation.isPending ? <Loader2 className="w-3 h-3 animate-spin" aria-hidden="true" /> : <Plus className="w-3 h-3" aria-hidden="true" />}
        {isEdit ? "Update" : "Add"}
      </button>
    </form>
  );
}
