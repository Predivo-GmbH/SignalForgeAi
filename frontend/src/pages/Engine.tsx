import { useState } from "react";
import {
  Activity,
  Cpu,
  Circle,
  Shield,
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  ChevronLeft,
  ChevronRight,
  FlaskConical,
} from "lucide-react";
import { useSystemStatus } from "@/hooks/useSystemStatus";
import { useEngineStatus } from "@/hooks/useEngineStatus";
import { useRegimeStatus, type RegimeStatus } from "@/hooks/useRegimeStatus";
import { useSimulation } from "@/hooks/useSimulation";
import {
  usePipelineLog,
  usePipelineSummary,
  type PipelineLogParams,
} from "@/hooks/usePipelineLog";

/* ------------------------------------------------------------------ */
/*  Helpers                                                           */
/* ------------------------------------------------------------------ */

const REASON_LABELS: Record<string, string> = {
  chaotic_regime: "Chaotic Regime",
  no_trend: "No Trend",
  no_zones: "No Zones",
  low_confluence: "Low Confluence",
  no_trigger: "No Trigger",
  insufficient_candles: "Insufficient Data",
  risk_rejected: "Risk Rejected",
  feedback_filter: "Feedback Filter",
  confluence_override: "Confluence Override",
  cooldown: "Cooldown Active",
  position_filter: "Position Filter",
  mtf_filter: "MTF Conflict",
  dedup: "Duplicate Signal",
  ai_reject: "AI Rejected",
  error: "Pipeline Error",
};

function reasonLabel(reason: string | null): string {
  if (!reason) return "Passed";
  return REASON_LABELS[reason] || reason;
}

function reasonColor(reason: string | null): string {
  if (!reason) return "var(--color-positive)";
  if (reason === "error") return "var(--color-negative)";
  return "var(--color-warning)";
}

function actionColor(action: string): string {
  if (action === "BUY") return "var(--color-positive)";
  if (action === "SELL") return "var(--color-negative)";
  return "var(--color-text-secondary)";
}

function timeAgo(iso: string | null): string {
  if (!iso) return "never";
  const secs = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (secs < 60) return `${secs}s ago`;
  if (secs < 3600) return `${Math.floor(secs / 60)}m ago`;
  if (secs < 86400) return `${Math.floor(secs / 3600)}h ago`;
  return `${Math.floor(secs / 86400)}d ago`;
}

/* ------------------------------------------------------------------ */
/*  Page                                                              */
/* ------------------------------------------------------------------ */

export function EnginePage() {
  return (
    <div className="max-w-[1200px] mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-xl font-bold text-[var(--color-text-primary)]">
          Engine Monitor
        </h1>
        <p className="text-sm text-[var(--color-text-secondary)] mt-1">
          System health, pipeline decisions, and simulation status — updated every 5 minutes
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <SystemHealthCard />
        <EngineStatusCard />
      </div>

      <SimulationStatusCard />
      <PipelineSummaryCard />
      <PipelineLogTable />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  System Health                                                     */
/* ------------------------------------------------------------------ */

function SystemHealthCard() {
  const { data, isLoading } = useSystemStatus();

  if (isLoading) return <SkeletonCard title="System Health" />;

  const overall = data?.overall ?? "unknown";
  const services = data?.services;
  const statusColor =
    overall === "healthy"
      ? "var(--color-positive)"
      : overall === "degraded"
        ? "var(--color-warning)"
        : "var(--color-negative)";

  const StatusIcon =
    overall === "healthy" ? CheckCircle2 : overall === "degraded" ? AlertTriangle : XCircle;

  return (
    <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border)] rounded-xl p-5 space-y-4">
      <div className="flex items-center gap-2">
        <Activity className="h-5 w-5 text-[var(--color-accent)]" />
        <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">
          System Health
        </h3>
      </div>

      <div className="flex items-center gap-2">
        <StatusIcon className="h-4 w-4" style={{ color: statusColor }} />
        <span className="text-sm font-semibold capitalize" style={{ color: statusColor }}>
          {overall}
        </span>
        {data?.checked_at && (
          <span className="ml-auto text-xs text-[var(--color-text-secondary)]">
            checked {timeAgo(data.checked_at)}
          </span>
        )}
      </div>

      {/* Service status grid */}
      {services && (
        <div className="grid grid-cols-2 gap-3">
          {(["database", "redis", "worker", "beat"] as const).map((svc) => {
            const s = services[svc];
            const ok = s.status === "ok";
            return (
              <div key={svc} className="flex items-center gap-2 bg-[var(--color-bg-elevated)] rounded-lg px-3 py-2">
                <div
                  className="h-2 w-2 rounded-full shrink-0"
                  style={{
                    backgroundColor: ok
                      ? "var(--color-positive)"
                      : s.status === "stale"
                        ? "var(--color-warning)"
                        : "var(--color-negative)",
                  }}
                />
                <span className="text-xs font-medium text-[var(--color-text-primary)] capitalize">
                  {svc}
                </span>
                <span className="ml-auto text-[10px] text-[var(--color-text-secondary)]">
                  {s.status}
                </span>
              </div>
            );
          })}
        </div>
      )}

      {/* Data freshness */}
      {data?.data && (
        <div className="border-t border-[var(--color-border)] pt-3 space-y-1">
          <div className="flex justify-between text-xs text-[var(--color-text-secondary)]">
            <span>Last candle</span>
            <span className="font-mono">{timeAgo(data.data.last_candle_at)}</span>
          </div>
          <div className="flex justify-between text-xs text-[var(--color-text-secondary)]">
            <span>Last signal</span>
            <span className="font-mono">{timeAgo(data.data.last_signal_at)}</span>
          </div>
        </div>
      )}

      {/* Issues */}
      {data?.issues && data.issues.length > 0 && (
        <div className="border-t border-[var(--color-border)] pt-3">
          {data.issues.map((issue, i) => (
            <div key={i} className="flex items-start gap-2 text-xs text-[var(--color-warning)]">
              <AlertTriangle className="h-3 w-3 shrink-0 mt-0.5" />
              {issue}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Engine Status                                                     */
/* ------------------------------------------------------------------ */

const REGIME_CONFIG: Record<string, { label: string; color: string; icon: typeof TrendingUp }> = {
  low_vol: { label: "Low Volatility", color: "var(--color-positive)", icon: Shield },
  trending: { label: "Trending", color: "var(--color-accent)", icon: TrendingUp },
  high_vol: { label: "High Volatility", color: "var(--color-negative)", icon: AlertTriangle },
  unknown: { label: "Unknown", color: "var(--color-text-secondary)", icon: Cpu },
};

function EngineStatusCard() {
  const { data: engine, isLoading: el } = useEngineStatus();
  const { data: regime, isLoading: rl } = useRegimeStatus();

  if (el || rl) return <SkeletonCard title="Engine Status" />;

  const isActive = engine?.active ?? false;
  const regimeEnabled = regime?.regime_allocator_enabled ?? false;

  return (
    <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border)] rounded-xl p-5 space-y-4">
      <div className="flex items-center gap-2">
        <Cpu className="h-5 w-5 text-[var(--color-accent)]" />
        <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">
          Engine Status
        </h3>
      </div>

      <div className="flex items-center gap-2">
        <Circle
          className={`h-2.5 w-2.5 fill-current ${isActive ? "text-[var(--color-positive)]" : "text-[var(--color-negative)]"}`}
        />
        <span className="text-sm font-medium text-[var(--color-text-primary)]">
          {isActive ? "Engine Active" : "Engine Inactive"}
        </span>
      </div>

      {engine?.layers && engine.layers.length > 0 && (
        <div>
          <span className="text-[10px] uppercase tracking-wider text-[var(--color-text-secondary)] font-semibold">
            Active Layers
          </span>
          <div className="flex flex-wrap gap-1.5 mt-2">
            {engine.layers.map((layer) => (
              <span
                key={layer}
                className="inline-flex items-center rounded-full bg-[var(--color-bg-elevated)] px-2.5 py-0.5 text-xs font-medium text-[var(--color-text-secondary)]"
              >
                {layer}
              </span>
            ))}
          </div>
        </div>
      )}

      {regimeEnabled && regime && <RegimeInfo data={regime} />}
    </div>
  );
}

function RegimeInfo({ data }: { data: RegimeStatus }) {
  const regime = data.current_regime || "unknown";
  const config = REGIME_CONFIG[regime] || REGIME_CONFIG.unknown;
  const Icon = config.icon;
  const alloc = data.current_allocation_pct;

  return (
    <div className="border-t border-[var(--color-border)] pt-4 space-y-3">
      <div className="flex items-center gap-2">
        <Icon className="h-4 w-4" style={{ color: config.color }} />
        <span className="text-sm font-semibold" style={{ color: config.color }}>
          {config.label}
        </span>
        <span className="ml-auto text-xs text-[var(--color-text-secondary)] capitalize">
          {data.allocation_table}
        </span>
      </div>
      <div>
        <div className="flex justify-between text-xs text-[var(--color-text-secondary)] mb-1">
          <span>Allocation</span>
          <span>{alloc.toFixed(0)}%</span>
        </div>
        <div className="h-2 rounded-full bg-[var(--color-bg-elevated)] overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{ width: `${alloc}%`, backgroundColor: config.color }}
          />
        </div>
      </div>
      {data.cooldown_hours > 0 && (
        <div className="flex items-center gap-1.5">
          <div className="h-1.5 w-1.5 rounded-full bg-[var(--color-warning)]" />
          <span className="text-xs text-[var(--color-text-secondary)]">
            {data.cooldown_hours}h cooldown after trades
          </span>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Simulation Status                                                 */
/* ------------------------------------------------------------------ */

function SimulationStatusCard() {
  const { data: sim, isLoading } = useSimulation();

  if (isLoading) return <SkeletonCard title="Paper Simulation" />;
  if (!sim) {
    return (
      <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border)] rounded-xl p-5">
        <div className="flex items-center gap-2 mb-2">
          <FlaskConical className="h-5 w-5 text-[var(--color-accent)]" />
          <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">
            Paper Simulation
          </h3>
        </div>
        <p className="text-sm text-[var(--color-text-secondary)]">
          No simulation running. Start one from the Portfolio page.
        </p>
      </div>
    );
  }

  const isRunning = sim.status === "running";
  const bhReturn = sim.bh_return_pct ?? 0;
  const sfReturn = sim.sf_return_pct ?? 0;
  const diff = sfReturn - bhReturn;

  return (
    <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border)] rounded-xl p-5 space-y-4">
      <div className="flex items-center gap-2">
        <FlaskConical className="h-5 w-5 text-[var(--color-accent)]" />
        <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">
          Paper Simulation
        </h3>
        <span
          className="ml-auto flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full"
          style={{
            backgroundColor: isRunning
              ? "color-mix(in srgb, var(--color-positive) 15%, transparent)"
              : "var(--color-bg-elevated)",
            color: isRunning ? "var(--color-positive)" : "var(--color-text-secondary)",
          }}
        >
          <Circle className="h-1.5 w-1.5 fill-current" />
          {isRunning ? "Running" : "Stopped"}
        </span>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatBox label="Initial Value" value={`$${(sim.initial_value_usd ?? 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}`} />
        <StatBox label="Buy & Hold" value={`${bhReturn >= 0 ? "+" : ""}${bhReturn.toFixed(2)}%`} color={bhReturn >= 0 ? "var(--color-positive)" : "var(--color-negative)"} />
        <StatBox label="SignalForge" value={`${sfReturn >= 0 ? "+" : ""}${sfReturn.toFixed(2)}%`} color={sfReturn >= 0 ? "var(--color-positive)" : "var(--color-negative)"} />
        <StatBox
          label="SF vs B&H"
          value={`${diff >= 0 ? "+" : ""}${diff.toFixed(2)}%`}
          color={diff >= 0 ? "var(--color-positive)" : "var(--color-negative)"}
        />
      </div>

      <div className="grid grid-cols-3 gap-3">
        <StatBox label="Trades" value={String(sim.sf_trades ?? 0)} />
        <StatBox label="Win Rate" value={sim.sf_win_rate != null ? `${(sim.sf_win_rate * 100).toFixed(0)}%` : "—"} />
        <StatBox label="Open Positions" value={String(sim.sf_open_positions ?? 0)} />
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Pipeline Summary                                                  */
/* ------------------------------------------------------------------ */

function PipelineSummaryCard() {
  const { data, isLoading } = usePipelineSummary();

  if (isLoading) return <SkeletonCard title="Pipeline Summary (Today)" />;

  const total = data?.total_evaluations ?? 0;
  const passed = data?.passed ?? 0;
  const blocked = data?.blocked ?? 0;
  const reasons = data?.block_reasons ?? {};
  const maxCount = Math.max(...Object.values(reasons), 1);

  return (
    <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border)] rounded-xl p-5 space-y-4">
      <div className="flex items-center gap-2">
        <Activity className="h-5 w-5 text-[var(--color-accent)]" />
        <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">
          Pipeline Summary (Today)
        </h3>
        {data?.last_run_at && (
          <span className="ml-auto text-xs text-[var(--color-text-secondary)]">
            Last run: {timeAgo(data.last_run_at)}
          </span>
        )}
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatBox label="Total Evaluations" value={String(total)} />
        <StatBox label="Passed" value={String(passed)} color="var(--color-positive)" />
        <StatBox label="Blocked" value={String(blocked)} color="var(--color-warning)" />
        <StatBox label="Symbols" value={String(data?.symbols_evaluated ?? 0)} />
      </div>

      {/* Block reason bars */}
      {Object.keys(reasons).length > 0 && (
        <div>
          <span className="text-[10px] uppercase tracking-wider text-[var(--color-text-secondary)] font-semibold">
            Block Reasons
          </span>
          <div className="mt-2 space-y-2">
            {Object.entries(reasons).map(([reason, count]) => (
              <div key={reason}>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-[var(--color-text-secondary)]">{reasonLabel(reason)}</span>
                  <span className="font-mono text-[var(--color-text-primary)]">{count}</span>
                </div>
                <div className="h-1.5 rounded-full bg-[var(--color-bg-elevated)] overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      width: `${(count / maxCount) * 100}%`,
                      backgroundColor: "var(--color-warning)",
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {total === 0 && (
        <p className="text-sm text-[var(--color-text-secondary)]">
          No pipeline evaluations yet today. The pipeline runs every 5 minutes.
        </p>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Pipeline Decision Log                                             */
/* ------------------------------------------------------------------ */

function PipelineLogTable() {
  const [params, setParams] = useState<PipelineLogParams>({
    page: 1,
    per_page: 25,
  });

  const { data, isLoading } = usePipelineLog(params);
  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / (params.per_page || 25));

  return (
    <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border)] rounded-xl overflow-hidden">
      {/* Header + filters */}
      <div className="px-5 py-4 border-b border-[var(--color-border)] space-y-3">
        <div className="flex items-center gap-2">
          <Activity className="h-5 w-5 text-[var(--color-accent)]" />
          <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">
            Pipeline Decision History
          </h3>
          <span className="ml-auto text-xs text-[var(--color-text-secondary)]">
            {total} entries
          </span>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-2">
          <FilterSelect
            value={params.symbol || ""}
            onChange={(v) => setParams((p) => ({ ...p, symbol: v || undefined, page: 1 }))}
            placeholder="All Symbols"
            options={[
              "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT",
              "LTC/USDT", "DASH/USDT", "INJ/USDT", "ONT/USDT", "LUNC/USDT",
              "TAO/USDT", "RENDER/USDT", "XMR/USDT",
            ]}
          />
          <FilterSelect
            value={params.action || ""}
            onChange={(v) => setParams((p) => ({ ...p, action: v || undefined, page: 1 }))}
            placeholder="All Actions"
            options={["NO_TRADE", "BUY", "SELL"]}
          />
          <FilterSelect
            value={params.block_reason || ""}
            onChange={(v) => setParams((p) => ({ ...p, block_reason: v || undefined, page: 1 }))}
            placeholder="All Reasons"
            options={[
              "passed", "chaotic_regime", "no_trend", "no_zones", "low_confluence",
              "no_trigger", "insufficient_candles", "cooldown", "feedback_filter",
              "confluence_override", "position_filter", "mtf_filter", "dedup",
              "ai_reject", "error",
            ]}
          />
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <thead>
            <tr className="bg-[var(--color-bg-elevated)]">
              <th className="px-4 py-2.5 text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-secondary)]">
                Time
              </th>
              <th className="px-4 py-2.5 text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-secondary)]">
                Symbol
              </th>
              <th className="px-4 py-2.5 text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-secondary)]">
                TF
              </th>
              <th className="px-4 py-2.5 text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-secondary)]">
                Action
              </th>
              <th className="px-4 py-2.5 text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-secondary)]">
                Result
              </th>
              <th className="px-4 py-2.5 text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-secondary)] text-right">
                Confluence
              </th>
              <th className="px-4 py-2.5 text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-secondary)]">
                Regime
              </th>
            </tr>
          </thead>
          <tbody>
            {isLoading &&
              Array.from({ length: 5 }, (_, i) => (
                <tr key={i} className="border-t border-[var(--color-border)]">
                  {Array.from({ length: 7 }, (_, j) => (
                    <td key={j} className="px-4 py-3">
                      <div className="h-3 w-16 rounded bg-[var(--color-bg-elevated)] animate-pulse" />
                    </td>
                  ))}
                </tr>
              ))}

            {!isLoading && items.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-sm text-[var(--color-text-secondary)]">
                  No pipeline decisions found. The pipeline runs every 5 minutes.
                </td>
              </tr>
            )}

            {items.map((entry) => (
              <tr
                key={entry.id}
                className="border-t border-[var(--color-border)] hover:bg-[var(--color-bg-elevated)] transition-colors"
              >
                <td className="px-4 py-2.5 text-xs text-[var(--color-text-secondary)] font-mono whitespace-nowrap">
                  {entry.created_at
                    ? new Date(entry.created_at).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                        second: "2-digit",
                      })
                    : "—"}
                </td>
                <td className="px-4 py-2.5 text-xs font-medium text-[var(--color-text-primary)]">
                  {entry.symbol}
                </td>
                <td className="px-4 py-2.5 text-xs text-[var(--color-text-secondary)]">
                  {entry.timeframe}
                </td>
                <td className="px-4 py-2.5">
                  <span
                    className="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold"
                    style={{
                      backgroundColor: `color-mix(in srgb, ${actionColor(entry.action)} 15%, transparent)`,
                      color: actionColor(entry.action),
                    }}
                  >
                    {entry.action}
                  </span>
                </td>
                <td className="px-4 py-2.5">
                  <span
                    className="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold"
                    style={{
                      backgroundColor: `color-mix(in srgb, ${reasonColor(entry.block_reason)} 15%, transparent)`,
                      color: reasonColor(entry.block_reason),
                    }}
                  >
                    {reasonLabel(entry.block_reason)}
                  </span>
                </td>
                <td className="px-4 py-2.5 text-xs font-mono text-right text-[var(--color-text-primary)]">
                  {entry.confluence_score ?? "—"}
                </td>
                <td className="px-4 py-2.5 text-xs text-[var(--color-text-secondary)] capitalize">
                  {entry.regime?.replace("_", " ") ?? "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between px-5 py-3 border-t border-[var(--color-border)]">
          <span className="text-xs text-[var(--color-text-secondary)]">
            Page {params.page ?? 1} of {totalPages}
          </span>
          <div className="flex gap-1">
            <button
              onClick={() => setParams((p) => ({ ...p, page: Math.max(1, (p.page ?? 1) - 1) }))}
              disabled={(params.page ?? 1) <= 1}
              className="p-1.5 rounded-lg bg-[var(--color-bg-elevated)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] disabled:opacity-30 transition-colors"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <button
              onClick={() => setParams((p) => ({ ...p, page: Math.min(totalPages, (p.page ?? 1) + 1) }))}
              disabled={(params.page ?? 1) >= totalPages}
              className="p-1.5 rounded-lg bg-[var(--color-bg-elevated)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] disabled:opacity-30 transition-colors"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Shared Components                                                 */
/* ------------------------------------------------------------------ */

function StatBox({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="bg-[var(--color-bg-elevated)] rounded-lg p-3 space-y-0.5">
      <p className="text-[10px] uppercase tracking-wider text-[var(--color-text-secondary)]">
        {label}
      </p>
      <p
        className="text-sm font-mono font-semibold"
        style={{ color: color ?? "var(--color-text-primary)" }}
      >
        {value}
      </p>
    </div>
  );
}

function FilterSelect({
  value,
  onChange,
  placeholder,
  options,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  options: string[];
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="bg-[var(--color-bg-elevated)] border border-[var(--color-border)] text-xs text-[var(--color-text-primary)] rounded-lg px-2.5 py-1.5 outline-none focus:border-[var(--color-accent)]"
    >
      <option value="">{placeholder}</option>
      {options.map((opt) => (
        <option key={opt} value={opt}>
          {REASON_LABELS[opt] || opt}
        </option>
      ))}
    </select>
  );
}

function SkeletonCard({ title }: { title: string }) {
  return (
    <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border)] rounded-xl p-5 space-y-4">
      <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">{title}</h3>
      <div className="space-y-2">
        <div className="h-4 w-40 rounded bg-[var(--color-bg-elevated)] animate-pulse" />
        <div className="h-4 w-32 rounded bg-[var(--color-bg-elevated)] animate-pulse" />
        <div className="h-4 w-48 rounded bg-[var(--color-bg-elevated)] animate-pulse" />
      </div>
    </div>
  );
}
