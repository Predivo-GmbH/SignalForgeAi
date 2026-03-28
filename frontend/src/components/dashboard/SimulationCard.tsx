import { useState } from "react";
import { Tooltip } from "@/components/ui/Tooltip";
import {
  FlaskConical,
  Play,
  Square,
  TrendingUp,
  TrendingDown,
  Clock,
  BarChart3,
  Loader2,
} from "lucide-react";
import {
  useSimulation,
  useStartSimulation,
  useStopSimulation,
} from "@/hooks/useSimulation";

export function SimulationCard() {
  const { data: sim, isLoading } = useSimulation();
  const startMutation = useStartSimulation();
  const stopMutation = useStopSimulation();
  const [confirming, setConfirming] = useState(false);

  if (isLoading) {
    return (
      <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border)] rounded-xl p-4 sm:p-5 flex items-center justify-center min-h-[100px]" role="status" aria-live="polite">
        <Loader2 className="w-5 h-5 animate-spin text-[var(--color-accent)]" aria-hidden="true" />
      </div>
    );
  }

  // No active simulation — show start button
  if (!sim) {
    return (
      <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border)] rounded-xl p-4 sm:p-5 space-y-3">
        <div className="flex items-center gap-2">
          <FlaskConical className="w-4 h-4 text-[var(--color-accent)]" aria-hidden="true" />
          <Tooltip text="Compares Buy & Hold vs SignalForgeAI performance using your real portfolio with simulated trades.">
            <h3 className="text-sm font-semibold text-[var(--color-text-primary)] cursor-help">Paper Test</h3>
          </Tooltip>
        </div>
        <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">
          Compare active trading vs buy &amp; hold using your real portfolio.
        </p>
        <button
          onClick={() => startMutation.mutate()}
          disabled={startMutation.isPending}
          className="w-full flex items-center justify-center gap-2 rounded-lg bg-[var(--color-accent)] hover:bg-[var(--color-accent)]/90 text-white text-sm font-medium py-2 px-4 min-h-[44px] transition-colors disabled:opacity-50"
        >
          {startMutation.isPending ? (
            <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
          ) : (
            <Play className="w-4 h-4" aria-hidden="true" />
          )}
          Start Paper Test
        </button>
        {startMutation.isError && (
          <p className="text-xs text-[var(--color-negative)]" role="alert">
            {(startMutation.error as Error).message}
          </p>
        )}
      </div>
    );
  }

  // Active or stopped simulation — show comparison
  const diff = sim.latest_sf_value - sim.latest_bh_value;
  const diffPct = sim.initial_value_usd > 0
    ? ((diff / sim.initial_value_usd) * 100)
    : 0;
  const sfAhead = diff >= 0;
  const running = sim.status === "running";

  // Calculate how long it's been running
  const startDate = new Date(sim.started_at);
  const elapsed = Date.now() - startDate.getTime();
  const hours = Math.floor(elapsed / 3_600_000);
  const days = Math.floor(hours / 24);
  const timeLabel = days > 0
    ? `${days}d ${hours % 24}h`
    : `${hours}h`;

  return (
    <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border)] rounded-xl p-4 sm:p-5 space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FlaskConical className="w-4 h-4 text-[var(--color-accent)]" aria-hidden="true" />
          <Tooltip text="Compares Buy & Hold vs SignalForgeAI performance using your real portfolio with simulated trades.">
            <h3 className="text-sm font-semibold text-[var(--color-text-primary)] cursor-help">Paper Test</h3>
          </Tooltip>
        </div>
        {running && (
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full bg-[var(--color-positive)] animate-pulse" />
            <span className="text-xs text-[var(--color-text-secondary)]">
              Running
            </span>
          </div>
        )}
        {!running && (
          <span className="text-xs text-[var(--color-text-secondary)] bg-[var(--color-bg-elevated)] px-2 py-0.5 rounded-full">
            Stopped
          </span>
        )}
      </div>

      {/* Duration */}
      <div className="flex items-center gap-1.5 text-xs text-[var(--color-text-secondary)]">
        <Clock className="w-3 h-3" aria-hidden="true" />
        {running ? `Running for ${timeLabel}` : `Ran for ${timeLabel}`}
      </div>

      {/* B&H vs SF values */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-[var(--color-bg-elevated)]/50 rounded-lg p-3">
          <span className="text-xs text-[var(--color-text-secondary)] uppercase tracking-wider">
            Buy &amp; Hold
          </span>
          <p className="text-sm font-semibold text-[var(--color-text-primary)] mt-1">
            ${sim.latest_bh_value.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
          </p>
          <p className={`text-xs font-medium mt-0.5 ${sim.bh_return_pct >= 0 ? "text-[var(--color-positive)]" : "text-[var(--color-negative)]"}`}>
            {sim.bh_return_pct >= 0 ? "+" : ""}{sim.bh_return_pct.toFixed(2)}%
          </p>
        </div>
        <div className="bg-[var(--color-bg-elevated)]/50 rounded-lg p-3">
          <span className="text-xs text-[var(--color-text-secondary)] uppercase tracking-wider">
            SignalForgeAI
          </span>
          <p className="text-sm font-semibold text-[var(--color-text-primary)] mt-1">
            ${sim.latest_sf_value.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
          </p>
          <p className={`text-xs font-medium mt-0.5 ${sim.sf_return_pct >= 0 ? "text-[var(--color-positive)]" : "text-[var(--color-negative)]"}`}>
            {sim.sf_return_pct >= 0 ? "+" : ""}{sim.sf_return_pct.toFixed(2)}%
          </p>
        </div>
      </div>

      {/* Difference badge */}
      <div
        className={`flex items-center justify-center gap-1.5 flex-wrap rounded-lg py-2 px-2 text-xs sm:text-sm font-semibold text-center ${
          sfAhead
            ? "bg-[var(--color-positive)]/10 text-[var(--color-positive)]"
            : "bg-[var(--color-negative)]/10 text-[var(--color-negative)]"
        }`}
      >
        {sfAhead ? (
          <TrendingUp className="w-4 h-4" aria-hidden="true" />
        ) : (
          <TrendingDown className="w-4 h-4" aria-hidden="true" />
        )}
        SF {sfAhead ? "ahead" : "behind"} by ${Math.abs(diff).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })} ({diffPct >= 0 ? "+" : ""}{diffPct.toFixed(2)}%)
      </div>

      {/* Trade stats */}
      <div className="flex items-center gap-2 sm:gap-4 flex-wrap text-xs text-[var(--color-text-secondary)]">
        <div className="flex items-center gap-1">
          <BarChart3 className="w-3 h-3" aria-hidden="true" />
          {sim.sf_trades} trades
        </div>
        {sim.sf_trades > 0 && (
          <span>
            {sim.sf_win_rate.toFixed(0)}% win rate
          </span>
        )}
        {sim.sf_open_positions > 0 && (
          <span>{sim.sf_open_positions} open</span>
        )}
      </div>

      {/* Mini sparkline from snapshots */}
      {sim.snapshots.length > 1 && (
        <MiniChart snapshots={sim.snapshots} />
      )}

      {/* Action button */}
      {running && (
        <>
          {!confirming ? (
            <button
              onClick={() => setConfirming(true)}
              className="w-full flex items-center justify-center gap-2 rounded-lg border border-[var(--color-border)] hover:border-[var(--color-negative)]/50 text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-negative)] py-2 min-h-[44px] transition-colors"
            >
              <Square className="w-3.5 h-3.5" aria-hidden="true" />
              Stop Simulation
            </button>
          ) : (
            <div className="flex gap-2">
              <button
                onClick={() => {
                  setConfirming(false);
                  stopMutation.mutate(sim.id);
                }}
                disabled={stopMutation.isPending}
                className="flex-1 flex items-center justify-center gap-1.5 rounded-lg bg-[var(--color-negative)] hover:bg-[var(--color-negative)]/90 text-white text-sm font-medium py-2 min-h-[44px] transition-colors disabled:opacity-50"
              >
                {stopMutation.isPending ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden="true" />
                ) : (
                  "Confirm"
                )}
              </button>
              <button
                onClick={() => setConfirming(false)}
                className="flex-1 rounded-lg border border-[var(--color-border)] text-sm text-[var(--color-text-secondary)] py-2 min-h-[44px] hover:bg-[var(--color-bg-elevated)] transition-colors"
              >
                Cancel
              </button>
            </div>
          )}
        </>
      )}

      {!running && (
        <button
          onClick={() => startMutation.mutate()}
          disabled={startMutation.isPending}
          className="w-full flex items-center justify-center gap-2 rounded-lg bg-[var(--color-accent)] hover:bg-[var(--color-accent)]/90 text-white text-sm font-medium py-2 px-4 min-h-[44px] transition-colors disabled:opacity-50"
        >
          {startMutation.isPending ? (
            <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
          ) : (
            <Play className="w-4 h-4" aria-hidden="true" />
          )}
          Start New Test
        </button>
      )}
    </div>
  );
}

/** Minimal SVG sparkline showing both B&H and SF curves. */
function MiniChart({
  snapshots,
}: {
  snapshots: { bh_value_usd: number; sf_value_usd: number }[];
}) {
  const w = 320;
  const h = 48;
  const pad = 2;

  const allValues = snapshots.flatMap((s) => [s.bh_value_usd, s.sf_value_usd]);
  const min = Math.min(...allValues) * 0.998;
  const max = Math.max(...allValues) * 1.002;
  const range = max - min || 1;

  const toPath = (values: number[]) => {
    const step = (w - pad * 2) / Math.max(values.length - 1, 1);
    return values
      .map((v, i) => {
        const x = pad + i * step;
        const y = h - pad - ((v - min) / range) * (h - pad * 2);
        return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(" ");
  };

  const bhPath = toPath(snapshots.map((s) => s.bh_value_usd));
  const sfPath = toPath(snapshots.map((s) => s.sf_value_usd));

  return (
    <svg
      viewBox={`0 0 ${w} ${h}`}
      className="w-full"
      style={{ height: 48 }}
      preserveAspectRatio="none"
    >
      <path
        d={bhPath}
        fill="none"
        stroke="var(--color-text-secondary)"
        strokeWidth="1.5"
        opacity="0.4"
      />
      <path
        d={sfPath}
        fill="none"
        stroke="var(--color-accent)"
        strokeWidth="2"
      />
    </svg>
  );
}
