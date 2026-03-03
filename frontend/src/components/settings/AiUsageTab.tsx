import { useCallback, useEffect, useRef, useState } from "react";
import {
  DollarSign,
  Activity,
  Zap,
  Clock,
  CreditCard,
  Check,
  Loader2,
  RefreshCw,
  Cloud,
  Database,
} from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { cn } from "@/lib/cn";
import { useAiUsage, useUpdateCredit } from "@/hooks/useAiUsage";
import type {
  AiUsageResponse,
  DailyCost,
  ModelBreakdown,
  TypeBreakdown,
  RecentCall,
} from "@/hooks/useAiUsage";
import { createChart, HistogramSeries, type IChartApi } from "lightweight-charts";

/* ---- Period selector ---- */

const PERIODS = [
  { label: "7d", days: 7 },
  { label: "30d", days: 30 },
  { label: "90d", days: 90 },
] as const;

/* ---- Helper: format model name ---- */

function shortModel(model: string): string {
  if (model.includes("haiku")) return "Haiku";
  if (model.includes("sonnet")) return "Sonnet";
  if (model.includes("opus")) return "Opus";
  return model;
}

/* ---- Helper: format insight type ---- */

function formatType(t: string): string {
  return t
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

/* ---- Summary card ---- */

function StatCard({
  icon: Icon,
  label,
  value,
  sub,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-4 space-y-1">
      <div className="flex items-center gap-2 text-(--color-text-secondary)">
        <Icon className="w-4 h-4" />
        <span className="text-xs font-medium uppercase tracking-wider">
          {label}
        </span>
      </div>
      <p className="text-xl font-bold text-(--color-text-primary)">{value}</p>
      {sub && (
        <p className="text-xs text-(--color-text-secondary)">{sub}</p>
      )}
    </div>
  );
}

/* ---- Daily cost chart ---- */

function DailyCostChart({ data }: { data: DailyCost[] }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!containerRef.current || data.length === 0) return;

    const chart = createChart(containerRef.current, {
      height: 200,
      layout: {
        background: { color: "transparent" },
        textColor: "rgba(255,255,255,0.5)",
        fontSize: 11,
      },
      grid: {
        vertLines: { visible: false },
        horzLines: { color: "rgba(255,255,255,0.06)" },
      },
      timeScale: { borderVisible: false },
      rightPriceScale: { borderVisible: false },
    });
    chartRef.current = chart;

    const series = chart.addSeries(HistogramSeries, {
      color: "rgba(99,102,241,0.7)",
      priceFormat: { type: "price", precision: 4, minMove: 0.0001 },
    });

    series.setData(
      data.map((d) => ({
        time: d.date,
        value: d.cost_usd,
        color:
          d.cost_usd > 1
            ? "rgba(239,68,68,0.7)"
            : "rgba(99,102,241,0.7)",
      })),
    );

    chart.timeScale().fitContent();

    const ro = new ResizeObserver((entries) => {
      const { width } = entries[0].contentRect;
      chart.applyOptions({ width });
    });
    ro.observe(containerRef.current);

    return () => {
      ro.disconnect();
      chart.remove();
    };
  }, [data]);

  if (data.length === 0) {
    return (
      <div className="h-[200px] flex items-center justify-center text-sm text-(--color-text-secondary)">
        No data for this period
      </div>
    );
  }

  return <div ref={containerRef} />;
}

/* ---- Credit section ---- */

function CreditSection({
  credit,
}: {
  credit: AiUsageResponse["credit"];
}) {
  const [editing, setEditing] = useState(false);
  const [amount, setAmount] = useState("");
  const updateCredit = useUpdateCredit();

  function handleSave() {
    const val = parseFloat(amount);
    if (isNaN(val) || val < 0) return;
    updateCredit.mutate(val, {
      onSuccess: () => {
        setEditing(false);
        setAmount("");
      },
    });
  }

  const pct =
    credit.prepaid_usd > 0
      ? Math.min((credit.spent_usd / credit.prepaid_usd) * 100, 100)
      : 0;

  return (
    <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <CreditCard className="w-4 h-4 text-(--color-text-secondary)" />
          <h3 className="text-sm font-semibold text-(--color-text-primary)">
            Prepaid Credit
          </h3>
        </div>
        {!editing && (
          <button
            onClick={() => {
              setAmount(credit.prepaid_usd.toString());
              setEditing(true);
            }}
            className="text-xs font-medium text-(--color-accent) hover:underline"
          >
            Update
          </button>
        )}
      </div>

      {credit.prepaid_usd > 0 ? (
        <>
          <div className="flex items-baseline justify-between">
            <span className="text-2xl font-bold text-(--color-text-primary)">
              ${credit.remaining_usd.toFixed(2)}
            </span>
            <span className="text-xs text-(--color-text-secondary)">
              of ${credit.prepaid_usd.toFixed(2)} remaining
            </span>
          </div>
          <div className="w-full h-2 bg-(--color-bg-elevated) rounded-full overflow-hidden">
            <div
              className={cn(
                "h-full rounded-full transition-all",
                pct > 80
                  ? "bg-(--color-negative)"
                  : pct > 50
                    ? "bg-(--color-warning)"
                    : "bg-(--color-positive)",
              )}
              style={{ width: `${pct}%` }}
            />
          </div>
          <p className="text-xs text-(--color-text-secondary)">
            ${credit.spent_usd.toFixed(4)} spent ({pct.toFixed(1)}%)
          </p>
        </>
      ) : (
        <p className="text-sm text-(--color-text-secondary)">
          No prepaid credit configured. Enter your Anthropic prepaid balance to
          track remaining credit.
        </p>
      )}

      {editing && (
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-(--color-text-secondary)">
              $
            </span>
            <input
              type="number"
              min={0}
              step={0.01}
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="0.00"
              className="w-full pl-7 pr-3 py-2 bg-(--color-bg-elevated) border border-(--color-border) rounded-lg text-sm font-mono text-(--color-text-primary) focus:outline-none focus:ring-2 focus:ring-(--color-accent)/50"
            />
          </div>
          <button
            onClick={handleSave}
            disabled={updateCredit.isPending}
            className="px-4 py-2 bg-(--color-accent) hover:bg-(--color-accent)/90 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50"
          >
            {updateCredit.isPending ? "..." : "Save"}
          </button>
          <button
            onClick={() => setEditing(false)}
            className="px-3 py-2 text-sm text-(--color-text-secondary) hover:text-(--color-text-primary)"
          >
            Cancel
          </button>
        </div>
      )}
    </div>
  );
}

/* ---- Main Tab ---- */

export function AiUsageTab() {
  const [days, setDays] = useState(30);
  const { data, isLoading, isError, error } = useAiUsage(days);
  const queryClient = useQueryClient();
  const [refreshState, setRefreshState] = useState<"idle" | "loading" | "done">("idle");

  const handleRefresh = useCallback(async () => {
    if (refreshState === "loading") return;
    setRefreshState("loading");
    const start = Date.now();
    try {
      await queryClient.invalidateQueries({ queryKey: ["ai-usage"] });
    } finally {
      // Guarantee spinner is visible for at least 600ms
      const elapsed = Date.now() - start;
      const remaining = Math.max(600 - elapsed, 0);
      setTimeout(() => {
        setRefreshState("done");
        setTimeout(() => setRefreshState("idle"), 1200);
      }, remaining);
    }
  }, [queryClient, refreshState]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-(--color-accent)" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="bg-(--color-negative)/10 border border-(--color-negative)/20 rounded-xl p-4 text-center">
        <p className="text-sm text-(--color-negative)">
          {error instanceof Error ? error.message : "Failed to load AI usage data"}
        </p>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-(--color-text-primary)">
            AI Usage & Costs
          </h2>
          <div className="flex items-center gap-2 mt-0.5">
            <p className="text-sm text-(--color-text-secondary)">
              Track Claude API usage, costs, and prepaid credit
            </p>
            {data.source === "anthropic_api" ? (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <Cloud className="w-3 h-3" /> Anthropic API
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20">
                <Database className="w-3 h-3" /> Local
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-3">
          {/* Period selector */}
          <div className="flex bg-(--color-bg-elevated) rounded-lg p-0.5">
            {PERIODS.map((p) => (
              <button
                key={p.days}
                onClick={() => setDays(p.days)}
                className={cn(
                  "px-3 py-1 text-xs font-medium rounded-md transition-colors",
                  days === p.days
                    ? "bg-(--color-accent) text-white"
                    : "text-(--color-text-secondary) hover:text-(--color-text-primary)",
                )}
              >
                {p.label}
              </button>
            ))}
          </div>
          <button
            onClick={handleRefresh}
            disabled={refreshState === "loading"}
            className={cn(
              "p-2 rounded-lg hover:bg-(--color-bg-elevated) transition-colors",
              refreshState === "loading" && "opacity-50 cursor-not-allowed",
            )}
            title="Refresh"
          >
            {refreshState === "done" ? (
              <Check className="w-4 h-4 text-emerald-400" />
            ) : (
              <RefreshCw
                className={cn(
                  "w-4 h-4 text-(--color-text-secondary)",
                  refreshState === "loading" && "animate-spin",
                )}
              />
            )}
          </button>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={DollarSign}
          label="Total Cost"
          value={`$${data.summary.total_cost_usd.toFixed(4)}`}
          sub={`Last ${days} days`}
        />
        <StatCard
          icon={Activity}
          label="Total Calls"
          value={data.summary.total_calls.toLocaleString()}
          sub={`Last ${days} days`}
        />
        <StatCard
          icon={Zap}
          label="Avg Cost / Call"
          value={`$${data.summary.avg_cost_per_call.toFixed(4)}`}
        />
        <StatCard
          icon={Clock}
          label="Avg Latency"
          value={`${data.summary.avg_latency_ms.toFixed(0)}ms`}
        />
      </div>

      {/* Credit */}
      <CreditSection credit={data.credit} />

      {/* Daily cost chart */}
      <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-5 space-y-3">
        <h3 className="text-sm font-semibold text-(--color-text-primary)">
          Daily Costs
        </h3>
        <DailyCostChart data={data.daily_costs} />
      </div>

      {/* Model breakdown + Type breakdown side by side */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* By model */}
        <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-5 space-y-3">
          <h3 className="text-sm font-semibold text-(--color-text-primary)">
            By Model
          </h3>
          {data.by_model.length === 0 ? (
            <p className="text-sm text-(--color-text-secondary)">No data</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-(--color-text-secondary) uppercase tracking-wider">
                  <th className="text-left pb-2">Model</th>
                  <th className="text-right pb-2">Calls</th>
                  <th className="text-right pb-2">Cost</th>
                  <th className="text-right pb-2">Latency</th>
                </tr>
              </thead>
              <tbody>
                {data.by_model.map((m: ModelBreakdown) => (
                  <tr
                    key={m.model}
                    className="border-t border-(--color-border)"
                  >
                    <td className="py-2 text-(--color-text-primary) font-medium">
                      {shortModel(m.model)}
                    </td>
                    <td className="py-2 text-right text-(--color-text-secondary)">
                      {m.calls}
                    </td>
                    <td className="py-2 text-right font-mono text-(--color-text-primary)">
                      ${m.cost_usd.toFixed(4)}
                    </td>
                    <td className="py-2 text-right text-(--color-text-secondary)">
                      {m.avg_latency_ms.toFixed(0)}ms
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* By type */}
        <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-5 space-y-3">
          <h3 className="text-sm font-semibold text-(--color-text-primary)">
            By Feature
          </h3>
          {data.by_type.length === 0 ? (
            <p className="text-sm text-(--color-text-secondary)">No data</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-(--color-text-secondary) uppercase tracking-wider">
                  <th className="text-left pb-2">Feature</th>
                  <th className="text-right pb-2">Calls</th>
                  <th className="text-right pb-2">Cost</th>
                </tr>
              </thead>
              <tbody>
                {data.by_type.map((t: TypeBreakdown) => (
                  <tr
                    key={t.insight_type}
                    className="border-t border-(--color-border)"
                  >
                    <td className="py-2 text-(--color-text-primary) font-medium">
                      {formatType(t.insight_type)}
                    </td>
                    <td className="py-2 text-right text-(--color-text-secondary)">
                      {t.calls}
                    </td>
                    <td className="py-2 text-right font-mono text-(--color-text-primary)">
                      ${t.cost_usd.toFixed(4)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Recent calls */}
      <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-5 space-y-3">
        <h3 className="text-sm font-semibold text-(--color-text-primary)">
          Recent API Calls
        </h3>
        {data.recent_calls.length === 0 ? (
          <p className="text-sm text-(--color-text-secondary)">No recent calls</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-(--color-text-secondary) uppercase tracking-wider">
                  <th className="text-left pb-2">Time</th>
                  <th className="text-left pb-2">Feature</th>
                  <th className="text-left pb-2">Model</th>
                  <th className="text-right pb-2">Tokens</th>
                  <th className="text-right pb-2">Cost</th>
                  <th className="text-right pb-2">Latency</th>
                </tr>
              </thead>
              <tbody>
                {data.recent_calls.map((c: RecentCall) => (
                  <tr
                    key={c.id}
                    className="border-t border-(--color-border)"
                  >
                    <td className="py-2 text-(--color-text-secondary) whitespace-nowrap">
                      {new Date(c.created_at).toLocaleString(undefined, {
                        month: "short",
                        day: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </td>
                    <td className="py-2 text-(--color-text-primary)">
                      {formatType(c.insight_type)}
                    </td>
                    <td className="py-2 text-(--color-text-secondary)">
                      {shortModel(c.model_used)}
                    </td>
                    <td className="py-2 text-right font-mono text-(--color-text-secondary)">
                      {c.input_tokens + c.output_tokens}
                    </td>
                    <td className="py-2 text-right font-mono text-(--color-text-primary)">
                      ${c.cost_usd.toFixed(4)}
                    </td>
                    <td className="py-2 text-right text-(--color-text-secondary)">
                      {c.latency_ms}ms
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
