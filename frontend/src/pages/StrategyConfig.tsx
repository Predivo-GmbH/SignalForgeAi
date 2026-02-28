import { useState } from "react";
import {
  Plus,
  Pencil,
  Trash2,
  Power,
  X,
  Loader2,
  Zap,
  Settings2,
} from "lucide-react";
import {
  useStrategies,
  useCreateStrategy,
  useUpdateStrategy,
  useToggleStrategy,
  useDeleteStrategy,
} from "@/hooks/useStrategies";
import type { Strategy } from "@/hooks/useStrategies";
import { cn } from "@/lib/cn";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

/* ----- Strategy Form ----- */
function StrategyForm({
  initial,
  onSubmit,
  onCancel,
  isLoading,
}: {
  initial?: { name: string; config: string };
  onSubmit: (name: string, config: Record<string, unknown>) => void;
  onCancel: () => void;
  isLoading: boolean;
}) {
  const [name, setName] = useState(initial?.name ?? "");
  const [configStr, setConfigStr] = useState(
    initial?.config ?? '{\n  "rsi_period": 14,\n  "rsi_overbought": 70,\n  "rsi_oversold": 30\n}'
  );
  const [configError, setConfigError] = useState<string | null>(null);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      const parsed = JSON.parse(configStr);
      setConfigError(null);
      onSubmit(name.trim(), parsed);
    } catch {
      setConfigError("Invalid JSON");
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="bg-(--color-bg-surface) border border-(--color-accent)/30 rounded-xl p-5 space-y-4"
    >
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-(--color-text-primary)">
          {initial ? "Edit Strategy" : "New Strategy"}
        </h3>
        <button
          type="button"
          onClick={onCancel}
          className="p-1 rounded hover:bg-(--color-bg-elevated) transition-colors"
        >
          <X className="w-4 h-4 text-(--color-text-secondary)" />
        </button>
      </div>

      <div className="space-y-1.5">
        <label className="block text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">
          Strategy Name
        </label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g., RSI Reversal"
          required
          className="w-full bg-(--color-bg-elevated) border border-(--color-border) rounded-lg px-3 py-2 text-sm text-(--color-text-primary) focus:outline-none focus:ring-2 focus:ring-(--color-accent)/50"
        />
      </div>

      <div className="space-y-1.5">
        <label className="block text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">
          Config (JSON)
        </label>
        <textarea
          value={configStr}
          onChange={(e) => {
            setConfigStr(e.target.value);
            setConfigError(null);
          }}
          rows={6}
          className="w-full bg-(--color-bg-elevated) border border-(--color-border) rounded-lg px-3 py-2 text-sm font-mono text-(--color-text-primary) focus:outline-none focus:ring-2 focus:ring-(--color-accent)/50 resize-y"
        />
        {configError && (
          <p className="text-xs text-(--color-negative)">{configError}</p>
        )}
      </div>

      <div className="flex gap-2">
        <button
          type="submit"
          disabled={isLoading || !name.trim()}
          className="flex items-center gap-2 bg-(--color-accent) hover:bg-(--color-accent)/90 text-white font-semibold py-2 px-4 rounded-lg text-sm transition-colors disabled:opacity-50"
        >
          {isLoading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
          {initial ? "Save Changes" : "Create Strategy"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="py-2 px-4 rounded-lg text-sm text-(--color-text-secondary) hover:bg-(--color-bg-elevated) transition-colors"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}

/* ----- Strategy Card ----- */
function StrategyCard({
  strategy,
  onEdit,
  onToggle,
  onDelete,
  isToggling,
  isDeleting,
}: {
  strategy: Strategy;
  onEdit: () => void;
  onToggle: () => void;
  onDelete: () => void;
  isToggling: boolean;
  isDeleting: boolean;
}) {
  const [showConfirm, setShowConfirm] = useState(false);

  return (
    <div
      className={cn(
        "bg-(--color-bg-surface) border rounded-xl p-5 transition-all",
        strategy.is_active
          ? "border-(--color-accent)/40 shadow-[0_0_12px_rgba(123,97,255,0.08)]"
          : "border-(--color-border)"
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className="text-base font-semibold text-(--color-text-primary) truncate">
              {strategy.name}
            </h3>
            <span
              className={cn(
                "inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold uppercase",
                strategy.is_active
                  ? "bg-(--color-positive)/10 text-(--color-positive)"
                  : "bg-(--color-bg-elevated) text-(--color-text-secondary)"
              )}
            >
              <span
                className={cn(
                  "w-1.5 h-1.5 rounded-full",
                  strategy.is_active
                    ? "bg-(--color-positive)"
                    : "bg-(--color-text-secondary)/40"
                )}
              />
              {strategy.is_active ? "Active" : "Inactive"}
            </span>
          </div>
          <p className="text-xs text-(--color-text-secondary) mt-1">
            Created {formatDate(strategy.created_at)}
            {strategy.updated_at !== strategy.created_at && (
              <> &middot; Updated {formatDate(strategy.updated_at)}</>
            )}
          </p>
        </div>

        <div className="flex items-center gap-1 shrink-0">
          <button
            onClick={onEdit}
            className="p-1.5 rounded-lg hover:bg-(--color-bg-elevated) transition-colors"
            title="Edit strategy"
          >
            <Pencil className="w-3.5 h-3.5 text-(--color-text-secondary)" />
          </button>
          <button
            onClick={onToggle}
            disabled={isToggling}
            className={cn(
              "p-1.5 rounded-lg transition-colors",
              strategy.is_active
                ? "hover:bg-(--color-negative)/10 text-(--color-negative)"
                : "hover:bg-(--color-positive)/10 text-(--color-positive)"
            )}
            title={strategy.is_active ? "Deactivate" : "Activate"}
          >
            <Power className="w-3.5 h-3.5" />
          </button>
          {showConfirm ? (
            <div className="flex items-center gap-1 ml-1">
              <button
                onClick={() => {
                  onDelete();
                  setShowConfirm(false);
                }}
                disabled={isDeleting}
                className="px-2 py-1 rounded text-xs bg-(--color-negative)/10 text-(--color-negative) hover:bg-(--color-negative)/20 transition-colors"
              >
                {isDeleting ? "..." : "Confirm"}
              </button>
              <button
                onClick={() => setShowConfirm(false)}
                className="px-2 py-1 rounded text-xs text-(--color-text-secondary) hover:bg-(--color-bg-elevated) transition-colors"
              >
                Cancel
              </button>
            </div>
          ) : (
            <button
              onClick={() => setShowConfirm(true)}
              className="p-1.5 rounded-lg hover:bg-(--color-negative)/10 transition-colors"
              title="Delete strategy"
            >
              <Trash2 className="w-3.5 h-3.5 text-(--color-text-secondary)" />
            </button>
          )}
        </div>
      </div>

      {/* Config preview */}
      {strategy.config && Object.keys(strategy.config).length > 0 && (
        <div className="mt-3 bg-(--color-bg-elevated)/50 rounded-lg px-3 py-2">
          <div className="flex flex-wrap gap-x-4 gap-y-1">
            {Object.entries(strategy.config)
              .slice(0, 6)
              .map(([key, val]) => (
                <span key={key} className="text-xs">
                  <span className="text-(--color-text-secondary)">{key}:</span>{" "}
                  <span className="font-mono text-(--color-text-primary)">
                    {String(val)}
                  </span>
                </span>
              ))}
            {Object.keys(strategy.config).length > 6 && (
              <span className="text-xs text-(--color-text-secondary)">
                +{Object.keys(strategy.config).length - 6} more
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/* ----- Main Page ----- */
export function StrategyConfigPage() {
  const { data, isLoading } = useStrategies();
  const createMutation = useCreateStrategy();
  const updateMutation = useUpdateStrategy();
  const toggleMutation = useToggleStrategy();
  const deleteMutation = useDeleteStrategy();

  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  const strategies = data?.strategies ?? [];

  function handleCreate(name: string, config: Record<string, unknown>) {
    createMutation.mutate(
      { name, config },
      { onSuccess: () => setShowForm(false) }
    );
  }

  function handleUpdate(name: string, config: Record<string, unknown>) {
    if (!editingId) return;
    updateMutation.mutate(
      { id: editingId, name, config },
      { onSuccess: () => setEditingId(null) }
    );
  }

  const editingStrategy = strategies.find((s) => s.id === editingId);

  return (
    <div className="p-6 space-y-6 max-w-[1200px] mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-(--color-text-primary)">
            Strategies
          </h1>
          <p className="text-sm text-(--color-text-secondary) mt-1">
            Configure and manage trading strategies
          </p>
        </div>
        {!showForm && !editingId && (
          <button
            onClick={() => setShowForm(true)}
            className="flex items-center gap-2 bg-(--color-accent) hover:bg-(--color-accent)/90 text-white font-semibold py-2 px-4 rounded-lg text-sm transition-colors"
          >
            <Plus className="w-4 h-4" />
            New Strategy
          </button>
        )}
      </div>

      {/* Create form */}
      {showForm && (
        <StrategyForm
          onSubmit={handleCreate}
          onCancel={() => setShowForm(false)}
          isLoading={createMutation.isPending}
        />
      )}

      {/* Edit form */}
      {editingId && editingStrategy && (
        <StrategyForm
          initial={{
            name: editingStrategy.name,
            config: JSON.stringify(editingStrategy.config, null, 2),
          }}
          onSubmit={handleUpdate}
          onCancel={() => setEditingId(null)}
          isLoading={updateMutation.isPending}
        />
      )}

      {/* Strategy list */}
      {isLoading ? (
        <div className="grid gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div
              key={i}
              className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-5 h-[100px] animate-pulse"
            />
          ))}
        </div>
      ) : strategies.length === 0 ? (
        <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-12 text-center">
          <Settings2 className="w-10 h-10 text-(--color-text-secondary)/40 mx-auto mb-3" />
          <p className="text-sm text-(--color-text-secondary)">
            No strategies configured yet
          </p>
          <p className="text-xs text-(--color-text-secondary)/60 mt-1">
            Create your first strategy to start automated trading
          </p>
        </div>
      ) : (
        <div className="grid gap-4">
          {/* Active strategies first */}
          {strategies
            .sort((a, b) =>
              a.is_active === b.is_active ? 0 : a.is_active ? -1 : 1
            )
            .map((strategy) => (
              <StrategyCard
                key={strategy.id}
                strategy={strategy}
                onEdit={() => {
                  setEditingId(strategy.id);
                  setShowForm(false);
                }}
                onToggle={() => toggleMutation.mutate(strategy.id)}
                onDelete={() => deleteMutation.mutate(strategy.id)}
                isToggling={
                  toggleMutation.isPending &&
                  toggleMutation.variables === strategy.id
                }
                isDeleting={
                  deleteMutation.isPending &&
                  deleteMutation.variables === strategy.id
                }
              />
            ))}
        </div>
      )}

      {/* Active strategy hint */}
      {strategies.some((s) => s.is_active) && (
        <div className="flex items-center gap-2 text-xs text-(--color-text-secondary) bg-(--color-accent-soft) rounded-lg px-4 py-2.5">
          <Zap className="w-3.5 h-3.5 text-(--color-accent)" />
          Active strategies receive live signals and execute trades automatically
        </div>
      )}
    </div>
  );
}
