import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Zap, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { useSignals } from "@/hooks/useSignals";
import type { Signal } from "@/hooks/useSignals";
import { Badge } from "@/components/ui/Badge";
import { DataTable } from "@/components/ui/DataTable";
import type { Column } from "@/components/ui/DataTable";
import { Pagination } from "@/components/ui/Pagination";

const PAGE_SIZE = 20;

function formatPrice(val: number): string {
  return `$${val.toFixed(2)}`;
}

function formatTime(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

function ConfluenceBar({ score }: { score: number }) {
  const pct = Math.min(100, Math.max(0, score));
  let color = "bg-[var(--color-negative)]";
  if (pct >= 60) color = "bg-[var(--color-positive)]";
  else if (pct >= 30) color = "bg-[var(--color-warning)]";

  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 rounded-full bg-[var(--color-bg-elevated)] overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs font-mono text-[var(--color-text-secondary)]">
        {score}
      </span>
    </div>
  );
}

function directionBadge(dir: string) {
  const upper = dir.toUpperCase();
  return (
    <Badge variant={upper === "LONG" ? "success" : "danger"}>
      {upper}
    </Badge>
  );
}

function regimeBadge(regime: string) {
  const r = regime.toLowerCase();
  let variant: "success" | "danger" | "warning" | "info" | "neutral" = "neutral";
  if (r === "trending" || r === "bullish") variant = "success";
  else if (r === "bearish" || r === "crisis") variant = "danger";
  else if (r === "volatile" || r === "mixed") variant = "warning";
  else if (r === "mean_reverting") variant = "info";

  return <Badge variant={variant}>{regime}</Badge>;
}

function statusBadge(status: string) {
  const s = status.toLowerCase();
  let variant: "success" | "danger" | "warning" | "info" | "neutral" = "neutral";
  if (s === "active" || s === "filled") variant = "success";
  else if (s === "cancelled" || s === "expired" || s === "rejected") variant = "danger";
  else if (s === "pending") variant = "warning";

  return <Badge variant={variant}>{status}</Badge>;
}

// Type adapter: Signal -> Record<string, unknown> for DataTable
type SignalRow = Signal & Record<string, unknown>;

const columns: Column<SignalRow>[] = [
  {
    key: "created_at",
    header: "Time",
    render: (row) => (
      <span className="text-xs text-[var(--color-text-secondary)] whitespace-nowrap">
        {formatTime(row.created_at)}
      </span>
    ),
  },
  {
    key: "symbol",
    header: "Symbol",
    render: (row) => (
      <span className="font-semibold text-[var(--color-text-primary)]">
        {row.symbol}
      </span>
    ),
  },
  {
    key: "direction",
    header: "Direction",
    render: (row) => directionBadge(row.direction),
  },
  {
    key: "entry_price",
    header: "Entry",
    align: "right",
    render: (row) => (
      <span className="font-mono">{formatPrice(row.entry_price)}</span>
    ),
  },
  {
    key: "stop_loss",
    header: "SL",
    align: "right",
    render: (row) => (
      <span className="font-mono text-[var(--color-text-secondary)]">
        {formatPrice(row.stop_loss)}
      </span>
    ),
  },
  {
    key: "take_profit_1",
    header: "TP1",
    align: "right",
    render: (row) => (
      <span className="font-mono text-[var(--color-text-secondary)]">
        {formatPrice(row.take_profit_1)}
      </span>
    ),
  },
  {
    key: "position_size",
    header: "Size",
    align: "right" as const,
    render: (row: SignalRow) => (
      <span className="font-mono text-[var(--color-text-secondary)]">
        {row.position_size != null ? row.position_size.toFixed(4) : "--"}
      </span>
    ),
  },
  {
    key: "confluence_score",
    header: "Confluence",
    render: (row) => <ConfluenceBar score={row.confluence_score} />,
  },
  {
    key: "regime",
    header: "Regime",
    render: (row) => regimeBadge(row.regime),
  },
  {
    key: "status",
    header: "Status",
    render: (row) => statusBadge(row.status),
  },
];

export function SignalsPage() {
  const queryClient = useQueryClient();
  const [offset, setOffset] = useState(0);
  const { data, isLoading } = useSignals(PAGE_SIZE, offset);

  const generateMutation = useMutation({
    mutationFn: () => api.post("/signals/generate"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["signals"] });
    },
  });

  const signals = (data?.signals ?? []) as SignalRow[];
  const total = data?.total ?? 0;

  return (
    <div className="flex flex-col gap-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">
          Signals
        </h1>
        <button
          onClick={() => generateMutation.mutate()}
          disabled={generateMutation.isPending}
          className="inline-flex items-center gap-2 rounded-lg bg-[var(--color-accent)] px-4 py-2 text-sm font-semibold text-white transition-colors hover:opacity-90 disabled:opacity-50"
        >
          {generateMutation.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Zap className="h-4 w-4" />
          )}
          Generate Signal
        </button>
      </div>

      {/* Error */}
      {generateMutation.isError && (
        <div className="rounded-lg border border-[var(--color-negative)]/30 bg-[var(--color-negative)]/10 px-4 py-3 text-sm text-[var(--color-negative)]">
          Failed to generate signal. Please try again.
        </div>
      )}

      {/* Table */}
      <DataTable
        data={signals}
        columns={columns}
        loading={isLoading}
        emptyMessage="No signals generated yet. Click 'Generate Signal' to create one."
      />

      {/* Pagination */}
      {total > PAGE_SIZE && (
        <Pagination
          total={total}
          limit={PAGE_SIZE}
          offset={offset}
          onChange={setOffset}
        />
      )}
    </div>
  );
}
