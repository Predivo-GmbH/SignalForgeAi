import { useState, useEffect, useRef } from "react";
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
  RotateCcw,
  MinusCircle,
} from "lucide-react";
import { useSystemStatus, useRestartWorker, type RestartPhase } from "@/hooks/useSystemStatus";
import { useEngineStatus } from "@/hooks/useEngineStatus";
import { useRegimeStatus, type RegimeStatus } from "@/hooks/useRegimeStatus";
import { useSimulation } from "@/hooks/useSimulation";
import { usePipelineLog, usePipelineSummary } from "@/hooks/usePipelineLog";
import { usePipelineRuns, type PipelineRun } from "@/hooks/usePipelineRuns";
import { Tooltip } from "@/components/ui/Tooltip";

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

const REASON_DESCRIPTIONS: Record<string, string> = {
  chaotic_regime:
    "The market regime detector classified conditions as chaotic (high ADX + high ATR). Trading is blocked to avoid unpredictable price action.",
  no_trend:
    "The multi-timeframe trend filter found no clear directional trend. The system requires EMA alignment, ADX confirmation, or Ichimoku support before considering a trade.",
  no_zones:
    "No valid entry zones were identified. The zone identifier looks for Fibonacci retracements, support/resistance levels, and VWAP zones to define optimal entry areas.",
  low_confluence:
    "The confluence score (0–100) fell below the strategy's minimum threshold (default: 50). The scorer combines 14 weighted technical factors: Fibonacci alignment (12pts), S/R overlap (12pts), multi-TF zone strength (10pts), VWAP proximity (8pts), volume node (8pts), RSI confirmation (8pts), MACD momentum (8pts), candlestick patterns (7pts), Stochastic cross (5pts), Bollinger position (5pts), Ichimoku cloud (5pts), OBV trend (5pts), Williams %R (4pts), and CCI momentum (3pts). Each factor is either fully earned or zero — the signal didn't accumulate enough points.",
  no_trigger:
    "No entry trigger fired. The trigger detector requires at least 2 confirmations from 5 trigger types (e.g., candlestick patterns, momentum crossovers, zone bounces).",
  insufficient_candles:
    "Not enough candle data loaded yet (minimum 100, ideally 200+ for the 200-EMA trend filter). On first run, the ingestion task backfills 500 historical candles from the configured exchange. This block should clear after the first successful ingestion cycle (~60s). If it persists, check that the worker and beat services are running and that the symbol is listed on your exchange.",
  risk_rejected:
    "The risk manager rejected this trade. Possible causes: position size exceeded max risk per trade, ATR-based stop loss was too wide, or Kelly criterion sizing was unfavorable.",
  feedback_filter:
    "The self-learning feedback filter blocked this signal based on learned patterns from past trades. FeedbackRules are generated nightly by analyzing trade outcomes.",
  confluence_override:
    "The learned confluence threshold (from the feedback system) is higher than the signal's score. Past trades showed that signals below this threshold tend to lose.",
  cooldown:
    "A cooldown period is active for this symbol. After closing a position, the system waits a configurable number of hours before allowing re-entry to avoid overtrading.",
  position_filter:
    "Blocked by the position-aware safety filter. For BUY: an open position already exists for this symbol. For SELL: no open position exists to close.",
  mtf_filter:
    "Multi-timeframe conflict detected. A BUY was blocked because the higher timeframe is bearish, or a SELL was blocked because the higher timeframe is bullish.",
  dedup:
    "An identical pending signal already exists for this symbol, timeframe, and direction. Duplicate signals are skipped to prevent double entries.",
  ai_reject:
    "Claude AI analyzed this signal and recommended rejection. The AI quality gate scores signals 0–100 and provides a recommendation based on market context analysis.",
  error:
    "An unexpected error occurred during pipeline evaluation for this symbol. Check the API logs for details.",
};

function reasonLabel(reason: string | null): string {
  if (!reason) return "Passed";
  return REASON_LABELS[reason] || reason;
}

function reasonDescription(reason: string | null): string {
  if (!reason) return "This signal passed all pipeline gates and was accepted for execution.";
  return REASON_DESCRIPTIONS[reason] || `Blocked by: ${reason}`;
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

function formatRunTime(iso: string): string {
  const d = new Date(iso);
  const now = new Date();
  const isToday =
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate();
  if (isToday) {
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }
  return (
    d.toLocaleDateString([], { month: "short", day: "numeric" }) +
    " " +
    d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
  );
}

/* ------------------------------------------------------------------ */
/*  Page                                                              */
/* ------------------------------------------------------------------ */

export function EnginePage() {
  return (
    <div className="max-w-[1200px] mx-auto p-6 space-y-6">
      <div>
        <Tooltip text="Real-time status of the trading engine, signal pipeline, and background workers.">
          <h1 className="text-xl font-bold text-[var(--color-text-primary)] cursor-help">Engine Monitor</h1>
        </Tooltip>
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
      <PipelineRunList />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  System Health                                                     */
/* ------------------------------------------------------------------ */

function SystemHealthCard() {
  const { data, isLoading, rapidPoll, startRapidPoll } = useSystemStatus();
  const restart = useRestartWorker();
  const prevWorkerStatus = useRef<string | null>(null);

  // Detect worker recovery during rapid polling
  useEffect(() => {
    if (restart.phase !== "restarting") return;
    const workerNow = data?.services?.worker?.status;
    if (!workerNow) return;

    // Worker went down then came back, or stayed ok throughout
    if (workerNow === "ok" && prevWorkerStatus.current && prevWorkerStatus.current !== "ok") {
      restart.markRecovered();
    }
    prevWorkerStatus.current = workerNow;
  }, [data?.services?.worker?.status, restart.phase, restart.markRecovered]);

  const handleRestart = () => {
    prevWorkerStatus.current = data?.services?.worker?.status ?? null;
    restart.mutate();
    startRapidPoll();
  };

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
        <Tooltip text="Live status of all backend services — database, Redis, worker, and scheduler.">
          <h3 className="text-sm font-semibold text-[var(--color-text-primary)] cursor-help">System Health</h3>
        </Tooltip>
        {rapidPoll && (
          <span className="ml-auto flex items-center gap-1.5 text-[10px] text-[var(--color-accent)]">
            <span className="h-1.5 w-1.5 rounded-full bg-[var(--color-accent)] animate-pulse" />
            Live monitoring
          </span>
        )}
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
            const isRestarting = restart.phase === "restarting" && svc === "worker";
            return (
              <div key={svc} className="flex items-center gap-2 bg-[var(--color-bg-elevated)] rounded-lg px-3 py-2">
                <div
                  className={`h-2 w-2 rounded-full shrink-0 ${isRestarting ? "animate-pulse" : ""}`}
                  style={{
                    backgroundColor: isRestarting
                      ? "var(--color-accent)"
                      : ok
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
                  {isRestarting ? "restarting…" : s.status}
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
            <span>Last pipeline run</span>
            <span className="font-mono">{timeAgo(data.data.last_pipeline_run_at ?? null)}</span>
          </div>
          <div className="flex justify-between text-xs text-[var(--color-text-secondary)]">
            <span>Last signal passed</span>
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

      {/* Restart worker */}
      <div className="border-t border-[var(--color-border)] pt-3">
        <RestartButton phase={restart.phase} onRestart={handleRestart} />
      </div>
    </div>
  );
}

function RestartButton({ phase, onRestart }: { phase: RestartPhase; onRestart: () => void }) {
  const config: Record<RestartPhase, { label: string; color: string; spin: boolean; disabled: boolean }> = {
    idle:       { label: "Restart Worker", color: "var(--color-text-secondary)", spin: false, disabled: false },
    requesting: { label: "Sending restart…", color: "var(--color-accent)", spin: true, disabled: true },
    restarting: { label: "Worker restarting…", color: "var(--color-accent)", spin: true, disabled: true },
    recovered:  { label: "Worker recovered", color: "var(--color-positive)", spin: false, disabled: true },
    failed:     { label: "Restart failed", color: "var(--color-negative)", spin: false, disabled: true },
  };
  const c = config[phase];

  return (
    <div className="flex items-center gap-3">
      <button
        onClick={onRestart}
        disabled={c.disabled}
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[var(--color-bg-elevated)] text-xs font-medium hover:bg-[var(--color-bg-base)] disabled:opacity-60 transition-colors"
        style={{ color: c.color }}
      >
        {phase === "recovered" ? (
          <CheckCircle2 className="h-3.5 w-3.5" />
        ) : (
          <RotateCcw className={`h-3.5 w-3.5 ${c.spin ? "animate-spin" : ""}`} />
        )}
        {c.label}
      </button>
      {phase === "restarting" && (
        <span className="text-[10px] text-[var(--color-text-secondary)]">
          Polling every 3s…
        </span>
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
        <Tooltip text="Current state of the trading engine and whether it's actively processing signals.">
          <h3 className="text-sm font-semibold text-[var(--color-text-primary)] cursor-help">
            Engine Status
          </h3>
        </Tooltip>
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
          <Tooltip text="Buy & Hold vs SignalForge comparison running on your real portfolio data.">
            <h3 className="text-sm font-semibold text-[var(--color-text-primary)] cursor-help">
              Paper Simulation
            </h3>
          </Tooltip>
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
        <Tooltip text="Buy & Hold vs SignalForge comparison running on your real portfolio data.">
          <h3 className="text-sm font-semibold text-[var(--color-text-primary)] cursor-help">
            Paper Simulation
          </h3>
        </Tooltip>
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
        <Tooltip text="Overview of today's signal pipeline runs — how many symbols were evaluated and passed.">
          <h3 className="text-sm font-semibold text-[var(--color-text-primary)] cursor-help">
            Pipeline Summary (Today)
          </h3>
        </Tooltip>
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
                  <Tooltip text={reasonDescription(reason)}>
                    <span className="text-[var(--color-text-secondary)] cursor-help border-b border-dotted border-[var(--color-text-secondary)]/30">
                      {reasonLabel(reason)}
                    </span>
                  </Tooltip>
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
/*  Pipeline Run History                                              */
/* ------------------------------------------------------------------ */

function PipelineRunList() {
  const [page, setPage] = useState(1);
  const [expandedRun, setExpandedRun] = useState<string | null>(null);

  const { data, isLoading } = usePipelineRuns({ page, per_page: 20 });
  const runs = data?.runs ?? [];
  const totalRuns = data?.total_runs ?? 0;
  const totalPages = Math.ceil(totalRuns / 20);

  return (
    <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border)] rounded-xl overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-[var(--color-border)]">
        <div className="flex items-center gap-2">
          <Activity className="h-5 w-5 text-[var(--color-accent)]" />
          <Tooltip text="Log of recent pipeline executions with timestamps and results.">
            <h3 className="text-sm font-semibold text-[var(--color-text-primary)] cursor-help">
              Pipeline Run History
            </h3>
          </Tooltip>
          <span className="ml-auto text-xs text-[var(--color-text-secondary)]">
            {totalRuns} runs
          </span>
        </div>
        <p className="text-xs text-[var(--color-text-secondary)] mt-1">
          Click a run to see individual symbol decisions
        </p>
      </div>

      {/* Run cards */}
      <div className="divide-y divide-[var(--color-border)]">
        {isLoading &&
          Array.from({ length: 5 }, (_, i) => (
            <div key={i} className="px-5 py-3 flex items-center gap-3">
              <div className="h-4 w-4 rounded-full bg-[var(--color-bg-elevated)] animate-pulse" />
              <div className="h-3 w-12 rounded bg-[var(--color-bg-elevated)] animate-pulse" />
              <div className="h-3 w-32 rounded bg-[var(--color-bg-elevated)] animate-pulse" />
              <div className="ml-auto h-3 w-20 rounded bg-[var(--color-bg-elevated)] animate-pulse" />
            </div>
          ))}

        {!isLoading && runs.length === 0 && (
          <div className="px-5 py-8 text-center text-sm text-[var(--color-text-secondary)]">
            No pipeline runs found. The pipeline runs every 5 minutes.
          </div>
        )}

        {runs.map((run) => (
          <PipelineRunCard
            key={run.run_time}
            run={run}
            isExpanded={expandedRun === run.run_time}
            onToggle={() =>
              setExpandedRun(expandedRun === run.run_time ? null : run.run_time)
            }
          />
        ))}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between px-5 py-3 border-t border-[var(--color-border)]">
          <span className="text-xs text-[var(--color-text-secondary)]">
            Page {page} of {totalPages}
          </span>
          <div className="flex gap-1">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="p-1.5 rounded-lg bg-[var(--color-bg-elevated)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] disabled:opacity-30 transition-colors"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
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
/*  Pipeline Run Card                                                 */
/* ------------------------------------------------------------------ */

function PipelineRunCard({
  run,
  isExpanded,
  onToggle,
}: {
  run: PipelineRun;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const StatusIcon = run.has_trades ? CheckCircle2 : MinusCircle;
  const statusColor = run.has_trades
    ? "var(--color-positive)"
    : "var(--color-warning)";

  return (
    <div>
      {/* Summary row — always visible */}
      <button
        onClick={onToggle}
        className="w-full px-5 py-3 flex items-center gap-3 hover:bg-[var(--color-bg-elevated)] transition-colors text-left"
      >
        {/* Status icon */}
        <StatusIcon className="h-4 w-4 shrink-0" style={{ color: statusColor }} />

        {/* Timestamp */}
        <span className="text-xs font-mono text-[var(--color-text-secondary)] whitespace-nowrap w-28 shrink-0">
          {formatRunTime(run.run_time)}
        </span>

        {/* Quick summary */}
        <span className="text-xs text-[var(--color-text-primary)]">
          {run.passed > 0 ? (
            <>
              <span style={{ color: "var(--color-positive)" }}>{run.passed} passed</span>
              {", "}
              {run.blocked} blocked
            </>
          ) : (
            `All ${run.total} blocked`
          )}
        </span>

        {/* Top block reason badges */}
        <div className="hidden sm:flex gap-1 ml-auto mr-2">
          {run.top_block_reasons.slice(0, 2).map((r) => (
            <Tooltip key={r.reason} text={reasonDescription(r.reason)}>
              <span
                className="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium whitespace-nowrap cursor-help"
                style={{
                  backgroundColor: `color-mix(in srgb, ${reasonColor(r.reason)} 12%, transparent)`,
                  color: reasonColor(r.reason),
                }}
              >
                {reasonLabel(r.reason)} ({r.count})
              </span>
            </Tooltip>
          ))}
        </div>

        {/* Chevron */}
        <ChevronRight
          className={`h-4 w-4 shrink-0 text-[var(--color-text-secondary)] transition-transform duration-150 ${
            isExpanded ? "rotate-90" : ""
          }`}
        />
      </button>

      {/* Detail panel — shown when expanded */}
      {isExpanded && <PipelineRunDetail runTime={run.run_time} />}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Pipeline Run Detail (expanded)                                    */
/* ------------------------------------------------------------------ */

function PipelineRunDetail({ runTime }: { runTime: string }) {
  const since = runTime;
  const untilDate = new Date(new Date(runTime).getTime() + 5 * 60 * 1000);
  const until = untilDate.toISOString();

  const { data, isLoading } = usePipelineLog({ since, until, per_page: 200 });
  const items = data?.items ?? [];

  if (isLoading) {
    return (
      <div className="px-5 py-4 bg-[var(--color-bg-elevated)]">
        <div className="space-y-2">
          {Array.from({ length: 3 }, (_, i) => (
            <div key={i} className="h-3 w-48 rounded bg-[var(--color-bg-surface)] animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="px-5 py-4 bg-[var(--color-bg-elevated)] text-xs text-[var(--color-text-secondary)]">
        No entries found for this run.
      </div>
    );
  }

  return (
    <div className="bg-[var(--color-bg-elevated)] border-t border-[var(--color-border)]">
      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <thead>
            <tr>
              <th className="px-5 py-2 text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-secondary)]">
                Symbol
              </th>
              <th className="px-4 py-2 text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-secondary)]">
                TF
              </th>
              <th className="px-4 py-2 text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-secondary)]">
                Action
              </th>
              <th className="px-4 py-2 text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-secondary)]">
                Result
              </th>
              <th className="px-4 py-2 text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-secondary)] text-right">
                Confluence
              </th>
              <th className="px-4 py-2 text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-secondary)]">
                Regime
              </th>
            </tr>
          </thead>
          <tbody>
            {items.map((entry) => (
              <tr
                key={entry.id}
                className="border-t border-[var(--color-border)]"
                style={{
                  backgroundColor: !entry.block_reason
                    ? "color-mix(in srgb, var(--color-positive) 6%, transparent)"
                    : undefined,
                }}
              >
                <td className="px-5 py-2 text-xs font-medium text-[var(--color-text-primary)]">
                  {entry.symbol}
                </td>
                <td className="px-4 py-2 text-xs text-[var(--color-text-secondary)]">
                  {entry.timeframe}
                </td>
                <td className="px-4 py-2">
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
                <td className="px-4 py-2">
                  <Tooltip text={reasonDescription(entry.block_reason)}>
                    <span
                      className="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold cursor-help"
                      style={{
                        backgroundColor: `color-mix(in srgb, ${reasonColor(entry.block_reason)} 15%, transparent)`,
                        color: reasonColor(entry.block_reason),
                      }}
                    >
                      {reasonLabel(entry.block_reason)}
                    </span>
                  </Tooltip>
                </td>
                <td className="px-4 py-2 text-xs font-mono text-right text-[var(--color-text-primary)]">
                  {entry.confluence_score ?? "—"}
                </td>
                <td className="px-4 py-2 text-xs text-[var(--color-text-secondary)] capitalize">
                  {entry.regime?.replace("_", " ") ?? "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
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
