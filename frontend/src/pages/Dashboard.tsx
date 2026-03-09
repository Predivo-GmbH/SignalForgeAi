import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Sparkles,
  FlaskConical,
  Square,
  Loader2,
  TrendingUp,
  TrendingDown,
  Clock,
  BarChart3,
  Wallet,
  Repeat2,
} from "lucide-react";
import { useStrategies } from "@/hooks/useStrategies";
import {
  useSimulation,
  useStartSimulation,
  useStopSimulation,
  useCombinedPortfolio,
} from "@/hooks/useSimulation";
import { useDashboardSnapshot } from "@/hooks/usePositions";
import { AccountHero } from "@/components/portfolio/AccountHero";
import { HoldingsCard } from "@/components/portfolio/HoldingsCard";
import { PortfolioEquitySection } from "@/components/portfolio/PortfolioEquitySection";
import { SystemHealthBanner } from "@/components/dashboard/SystemHealthBanner";
import { SimulationPortfolio } from "@/components/dashboard/SimulationPortfolio";
import { UsdtReserveWidget } from "@/components/dashboard/UsdtReserveWidget";
import { Tooltip } from "@/components/ui/Tooltip";
import { fmtUsd, pnlColor } from "@/lib/format";

type Tab = "holdings" | "bh" | "paper";

export function PortfolioPage() {
  const navigate = useNavigate();
  const { data: strategiesData, isLoading: strategiesLoading } = useStrategies();
  const { data: sim, isLoading: simLoading } = useSimulation();
  const { data: snapshot } = useDashboardSnapshot();
  const startMutation = useStartSimulation();
  const stopMutation = useStopSimulation();

  const hasActiveStrategy = strategiesData?.strategies?.some((s) => s.is_active) ?? false;
  const showOnboarding = !strategiesLoading && !hasActiveStrategy;
  const hasSimulation = !!sim;

  const [activeTab, setActiveTab] = useState<Tab>("holdings");
  const [stopConfirming, setStopConfirming] = useState(false);

  // Fetch both portfolios from a single price fetch when simulation active
  const { data: combined, isLoading: portfolioLoading } = useCombinedPortfolio(
    hasSimulation && (activeTab === "bh" || activeTab === "paper") ? sim?.id : undefined
  );
  const bhPortfolio = combined?.bh;
  const paperPortfolio = combined?.paper;

  return (
    <div className="flex flex-col gap-4 sm:gap-6 p-4 sm:p-6 max-w-[1600px] mx-auto w-full overflow-x-hidden">
      {/* System health */}
      <SystemHealthBanner />

      {/* Onboarding banner */}
      {showOnboarding && (
        <button
          onClick={() => navigate("/advisor")}
          className="flex items-center gap-3 sm:gap-4 bg-gradient-to-r from-(--color-accent)/10 to-(--color-accent)/5 border border-(--color-accent)/30 rounded-xl px-4 sm:px-6 py-3 sm:py-4 text-left hover:border-(--color-accent)/50 transition-all group"
        >
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-(--color-accent)/15">
            <Sparkles className="w-5 h-5 text-(--color-accent)" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-(--color-text-primary) group-hover:text-(--color-accent) transition-colors">
              Get started with the AI Advisor
            </p>
            <p className="text-xs text-(--color-text-secondary) mt-0.5 truncate">
              Scan the market, pick the best trading pairs, and deploy an optimized strategy — all automated.
            </p>
          </div>
          <span className="shrink-0 text-xs font-medium text-(--color-accent) bg-(--color-accent)/10 rounded-lg px-3 py-1.5 hidden sm:inline">
            Start scanning
          </span>
        </button>
      )}

      {/* Account Hero */}
      {hasActiveStrategy && snapshot && (
        <AccountHero
          equity={snapshot.equity}
          dailyPnl={snapshot.daily_pnl}
          openPositions={snapshot.open_positions}
          maxPositions={snapshot.max_positions}
        />
      )}

      {/* Tab bar + Simulation controls */}
      <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border)] rounded-xl">
        {/* Tab header */}
        <div className="flex items-center justify-between border-b border-[var(--color-border)] px-4 py-2">
          <div className="flex items-center gap-1">
            <TabButton
              active={activeTab === "holdings"}
              onClick={() => setActiveTab("holdings")}
              icon={<Wallet className="w-3.5 h-3.5" />}
              label="Holdings"
            />
            {hasSimulation && (
              <>
                <TabButton
                  active={activeTab === "bh"}
                  onClick={() => setActiveTab("bh")}
                  icon={<TrendingUp className="w-3.5 h-3.5" />}
                  label="Buy & Hold"
                />
                <TabButton
                  active={activeTab === "paper"}
                  onClick={() => setActiveTab("paper")}
                  icon={<Repeat2 className="w-3.5 h-3.5" />}
                  label="Paper Trading"
                />
              </>
            )}
          </div>

          {/* Simulation controls */}
          <div className="flex items-center gap-2">
            {hasSimulation && sim.status === "running" && (
              <SimulationStatus sim={sim} />
            )}
            <SimulationButton
              sim={sim}
              simLoading={simLoading}
              startMutation={startMutation}
              stopMutation={stopMutation}
              stopConfirming={stopConfirming}
              setStopConfirming={setStopConfirming}
            />
          </div>
        </div>

        {/* Comparison bar (when simulation active) */}
        {hasSimulation && (activeTab === "bh" || activeTab === "paper") && (
          <ComparisonBar sim={sim} snapshot={snapshot ?? null} />
        )}

        {/* Tab content */}
        <div className="p-4 sm:p-5">
          {activeTab === "holdings" && <HoldingsCard overrideTotal={snapshot?.balance} />}

          {activeTab === "bh" && hasSimulation && (
            portfolioLoading ? (
              <LoadingSpinner />
            ) : bhPortfolio ? (
              <SimulationPortfolio
                holdings={bhPortfolio.holdings}
                totalValue={bhPortfolio.total_value_usd}
                initialValue={bhPortfolio.initial_value_usd}
                totalPnl={bhPortfolio.total_pnl_usd}
                totalPnlPct={bhPortfolio.total_pnl_pct}
                type="buy_and_hold"
              />
            ) : (
              <EmptyState message="No simulation data available" />
            )
          )}

          {activeTab === "paper" && hasSimulation && (
            portfolioLoading ? (
              <LoadingSpinner />
            ) : paperPortfolio ? (
              <div className="space-y-4">
                <SimulationPortfolio
                  holdings={paperPortfolio.holdings}
                  totalValue={paperPortfolio.total_value_usd}
                  initialValue={paperPortfolio.initial_value_usd}
                  totalPnl={paperPortfolio.total_pnl_usd}
                  totalPnlPct={paperPortfolio.total_pnl_pct}
                  type="paper_trading"
                />
                {/* Open positions */}
                {paperPortfolio.open_positions.length > 0 && (
                  <OpenPositionsSection
                    positions={paperPortfolio.open_positions}
                  />
                )}
              </div>
            ) : (
              <EmptyState message="No simulation data available" />
            )
          )}
        </div>
      </div>

      {/* USDT Reserve widget (paper tab only) */}
      {activeTab === "paper" && hasSimulation && paperPortfolio && (
        <UsdtReserveWidget
          simId={sim.id}
          reservePct={paperPortfolio.usdt_reserve_pct}
          reserveMode={paperPortfolio.usdt_reserve_mode}
          usdtBalance={paperPortfolio.usdt_balance}
          reserveTargetUsd={paperPortfolio.usdt_reserve_target_usd}
          reserveStatus={paperPortfolio.usdt_reserve_status}
          aiSuggestedPct={paperPortfolio.ai_suggested_reserve_pct}
          aiReasoning={paperPortfolio.ai_reserve_reasoning}
        />
      )}

      {/* Equity curve + sparkline comparison */}
      {hasSimulation && sim.snapshots.length > 1 && (
        <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border)] rounded-xl p-4 sm:p-5">
          <div className="flex items-center gap-2 mb-3">
            <BarChart3 className="w-4 h-4 text-[var(--color-accent)]" />
            <Tooltip text="Comparison of Buy & Hold vs SignalForge paper trading performance over time.">
              <h3 className="text-sm font-semibold text-[var(--color-text-primary)] cursor-help">
                Performance Comparison
              </h3>
            </Tooltip>
          </div>
          <SimulationChart snapshots={sim.snapshots} />
          <div className="flex items-center gap-4 mt-2 text-[11px] text-[var(--color-text-secondary)]">
            <span className="flex items-center gap-1.5">
              <svg width="12" height="2" className="opacity-70"><line x1="0" y1="1" x2="12" y2="1" stroke="var(--color-text-secondary)" strokeWidth="1.5" strokeDasharray="3 2" /></svg>
              Buy & Hold
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-0.5 rounded bg-[var(--color-accent)]" />
              SignalForge
            </span>
          </div>
        </div>
      )}

      {/* Equity curve from closed trades */}
      <PortfolioEquitySection />
    </div>
  );
}

/** @deprecated Use PortfolioPage instead */
export const DashboardPage = PortfolioPage;

/* ---- Sub-components ---- */

function TabButton({
  active,
  onClick,
  icon,
  label,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
        active
          ? "bg-[var(--color-accent)]/10 text-[var(--color-accent)]"
          : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-elevated)]/50"
      }`}
    >
      {icon}
      {label}
    </button>
  );
}

function SimulationStatus({ sim }: { sim: NonNullable<ReturnType<typeof useSimulation>["data"]> }) {
  const startDate = new Date(sim.started_at);
  const elapsed = Date.now() - startDate.getTime();
  const hours = Math.floor(elapsed / 3_600_000);
  const days = Math.floor(hours / 24);
  const timeLabel = days > 0 ? `${days}d ${hours % 24}h` : `${hours}h`;

  return (
    <div className="flex items-center gap-1.5 text-[11px] text-[var(--color-text-secondary)]">
      <div className="w-2 h-2 rounded-full bg-[var(--color-positive)] animate-pulse" />
      <Clock className="w-3 h-3" />
      {timeLabel}
    </div>
  );
}

function SimulationButton({
  sim,
  simLoading,
  startMutation,
  stopMutation,
  stopConfirming,
  setStopConfirming,
}: {
  sim: ReturnType<typeof useSimulation>["data"];
  simLoading: boolean;
  startMutation: ReturnType<typeof useStartSimulation>;
  stopMutation: ReturnType<typeof useStopSimulation>;
  stopConfirming: boolean;
  setStopConfirming: (v: boolean) => void;
}) {
  if (simLoading) return null;

  if (!sim || sim.status !== "running") {
    return (
      <button
        onClick={() => startMutation.mutate()}
        disabled={startMutation.isPending}
        className="flex items-center gap-1.5 rounded-lg bg-[var(--color-accent)] hover:bg-[var(--color-accent)]/90 text-white text-xs font-medium py-1.5 px-3 transition-colors disabled:opacity-50"
      >
        {startMutation.isPending ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
        ) : (
          <FlaskConical className="w-3.5 h-3.5" />
        )}
        Start Paper Test
      </button>
    );
  }

  if (!stopConfirming) {
    return (
      <button
        onClick={() => setStopConfirming(true)}
        className="flex items-center gap-1.5 rounded-lg border border-[var(--color-border)] hover:border-[var(--color-negative)]/50 text-xs text-[var(--color-text-secondary)] hover:text-[var(--color-negative)] py-1.5 px-3 transition-colors"
      >
        <Square className="w-3 h-3" />
        Stop
      </button>
    );
  }

  return (
    <div className="flex gap-1.5">
      <button
        onClick={() => {
          setStopConfirming(false);
          stopMutation.mutate(sim.id);
        }}
        disabled={stopMutation.isPending}
        className="rounded-lg bg-[var(--color-negative)] hover:bg-[var(--color-negative)]/90 text-white text-xs font-medium py-1.5 px-3 transition-colors disabled:opacity-50"
      >
        {stopMutation.isPending ? (
          <Loader2 className="w-3 h-3 animate-spin" />
        ) : (
          "Confirm"
        )}
      </button>
      <button
        onClick={() => setStopConfirming(false)}
        className="rounded-lg border border-[var(--color-border)] text-xs text-[var(--color-text-secondary)] py-1.5 px-3 hover:bg-[var(--color-bg-elevated)] transition-colors"
      >
        Cancel
      </button>
    </div>
  );
}

function ComparisonBar({ sim, snapshot }: {
  sim: NonNullable<ReturnType<typeof useSimulation>["data"]>;
  snapshot: import("@/hooks/usePositions").DashboardSnapshot | null;
}) {
  // Use snapshot values (single price fetch) when available, fallback to sim
  const bhValue = snapshot?.simulation?.bh_value ?? sim.latest_bh_value;
  const sfValue = snapshot?.simulation?.paper_value ?? sim.latest_sf_value;
  const bhReturnPct = snapshot?.simulation?.bh_return_pct ?? sim.bh_return_pct;
  const sfReturnPct = snapshot?.simulation?.paper_return_pct ?? sim.sf_return_pct;
  const initialValue = snapshot?.simulation?.initial_value_usd ?? sim.initial_value_usd;

  const diff = sfValue - bhValue;
  const diffPct = initialValue > 0 ? (diff / initialValue) * 100 : 0;
  const sfAhead = diff >= 0;

  return (
    <div className="flex items-center justify-between px-4 py-2.5 border-b border-[var(--color-border)] bg-[var(--color-bg-elevated)]/30">
      {/* B&H value */}
      <div className="flex items-center gap-3">
        <div>
          <span className="text-[10px] text-[var(--color-text-secondary)] uppercase tracking-wider">
            Buy & Hold
          </span>
          <p className="text-sm font-semibold text-[var(--color-text-primary)]">
            {fmtUsd(bhValue)}
            <span
              className="text-[11px] font-medium ml-1.5"
              style={{ color: pnlColor(bhReturnPct) }}
            >
              {bhReturnPct >= 0 ? "+" : ""}
              {bhReturnPct.toFixed(2)}%
            </span>
          </p>
        </div>
      </div>

      {/* Difference badge */}
      <div
        className={`flex items-center gap-1 rounded-full py-1 px-3 text-xs font-semibold ${
          sfAhead
            ? "bg-[var(--color-positive)]/10 text-[var(--color-positive)]"
            : "bg-[var(--color-negative)]/10 text-[var(--color-negative)]"
        }`}
      >
        {sfAhead ? (
          <TrendingUp className="w-3.5 h-3.5" />
        ) : (
          <TrendingDown className="w-3.5 h-3.5" />
        )}
        SF {sfAhead ? "+" : ""}
        {fmtUsd(diff)} ({diffPct >= 0 ? "+" : ""}
        {diffPct.toFixed(2)}%)
      </div>

      {/* SF value */}
      <div className="text-right">
        <span className="text-[10px] text-[var(--color-text-secondary)] uppercase tracking-wider">
          SignalForge
        </span>
        <p className="text-sm font-semibold text-[var(--color-text-primary)]">
          {fmtUsd(sfValue)}
          <span
            className="text-[11px] font-medium ml-1.5"
            style={{ color: pnlColor(sfReturnPct) }}
          >
            {sfReturnPct >= 0 ? "+" : ""}
            {sfReturnPct.toFixed(2)}%
          </span>
        </p>
      </div>

      {/* Trade stats */}
      <div className="hidden sm:flex items-center gap-3 text-[11px] text-[var(--color-text-secondary)]">
        <span>{sim.sf_trades} trades</span>
        {sim.sf_trades > 0 && <span>{sim.sf_win_rate.toFixed(0)}% WR</span>}
        {sim.sf_open_positions > 0 && <span>{sim.sf_open_positions} open</span>}
      </div>
    </div>
  );
}

function SimulationChart({
  snapshots,
}: {
  snapshots: { timestamp: string; bh_value_usd: number; sf_value_usd: number }[];
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });

  // Layout — wide viewBox so the chart fills the container
  const w = 900;
  const h = 200;
  const marginLeft = 60;
  const marginRight = 12;
  const marginTop = 12;
  const marginBottom = 32;
  const plotW = w - marginLeft - marginRight;
  const plotH = h - marginTop - marginBottom;

  const allValues = snapshots.flatMap((s) => [s.bh_value_usd, s.sf_value_usd]);
  const minVal = Math.min(...allValues) * 0.998;
  const maxVal = Math.max(...allValues) * 1.002;
  const valRange = maxVal - minVal || 1;

  const toX = (i: number) =>
    marginLeft + (i / Math.max(snapshots.length - 1, 1)) * plotW;
  const toY = (v: number) =>
    marginTop + plotH - ((v - minVal) / valRange) * plotH;

  const toPath = (values: number[]) =>
    values
      .map((v, i) => `${i === 0 ? "M" : "L"}${toX(i).toFixed(1)},${toY(v).toFixed(1)}`)
      .join(" ");

  // Y-axis ticks (4-5 ticks)
  const yTickCount = 4;
  const yTicks: number[] = [];
  for (let i = 0; i <= yTickCount; i++) {
    yTicks.push(minVal + (valRange * i) / yTickCount);
  }

  // X-axis ticks — pick ~5 evenly spaced labels
  const xTickCount = Math.min(5, snapshots.length);
  const xTicks: number[] = [];
  for (let i = 0; i < xTickCount; i++) {
    xTicks.push(Math.round((i / Math.max(xTickCount - 1, 1)) * (snapshots.length - 1)));
  }

  const fmtAxisVal = (v: number) => {
    if (v >= 100_000) return `$${(v / 1000).toFixed(0)}k`;
    if (v >= 10_000) return `$${(v / 1000).toFixed(1)}k`;
    if (v >= 1_000) return `$${v.toLocaleString("en-US", { maximumFractionDigits: 0 })}`;
    return `$${v.toFixed(0)}`;
  };

  // Determine if snapshots span multiple days
  const firstDate = new Date(snapshots[0].timestamp);
  const lastDate = new Date(snapshots[snapshots.length - 1].timestamp);
  const spansDays =
    firstDate.toDateString() !== lastDate.toDateString();

  const fmtDate = (ts: string, short?: boolean) => {
    const d = new Date(ts);
    if (short) {
      if (spansDays) {
        return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
      }
      // Same day — show time only
      return d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
    }
    return d.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;
    const relX = (e.clientX - rect.left) / rect.width;
    const svgX = relX * w;
    // Find closest snapshot index
    let closest = 0;
    let closestDist = Infinity;
    for (let i = 0; i < snapshots.length; i++) {
      const dist = Math.abs(toX(i) - svgX);
      if (dist < closestDist) {
        closestDist = dist;
        closest = i;
      }
    }
    setHoverIdx(closest);
    setTooltipPos({ x: e.clientX - rect.left, y: e.clientY - rect.top });
  };

  const snap = hoverIdx != null ? snapshots[hoverIdx] : null;
  const diff = snap ? snap.sf_value_usd - snap.bh_value_usd : 0;

  return (
    <div ref={containerRef} className="relative" onMouseLeave={() => setHoverIdx(null)}>
      <svg
        viewBox={`0 0 ${w} ${h}`}
        className="w-full cursor-crosshair"
        style={{ height: 200 }}
        preserveAspectRatio="xMidYMid meet"
        onMouseMove={handleMouseMove}
      >
        {/* Grid lines */}
        {yTicks.map((v, i) => (
          <line
            key={`grid-${i}`}
            x1={marginLeft}
            x2={w - marginRight}
            y1={toY(v)}
            y2={toY(v)}
            stroke="var(--color-border)"
            strokeWidth="0.5"
            strokeDasharray="4 3"
          />
        ))}

        {/* Y-axis labels */}
        {yTicks.map((v, i) => (
          <text
            key={`y-${i}`}
            x={marginLeft - 6}
            y={toY(v) + 3}
            textAnchor="end"
            fill="var(--color-text-secondary)"
            fontSize="10"
          >
            {fmtAxisVal(v)}
          </text>
        ))}

        {/* X-axis labels */}
        {xTicks.map((idx) => (
          <text
            key={`x-${idx}`}
            x={toX(idx)}
            y={h - 6}
            textAnchor="middle"
            fill="var(--color-text-secondary)"
            fontSize="10"
          >
            {fmtDate(snapshots[idx].timestamp, true)}
          </text>
        ))}

        {/* SF line (drawn first = behind) */}
        <path
          d={toPath(snapshots.map((s) => s.sf_value_usd))}
          fill="none"
          stroke="var(--color-accent)"
          strokeWidth="2"
        />
        {/* B&H line — dashed so it's visible even when overlapping SF */}
        <path
          d={toPath(snapshots.map((s) => s.bh_value_usd))}
          fill="none"
          stroke="var(--color-text-secondary)"
          strokeWidth="1.5"
          strokeDasharray="6 3"
          opacity="0.7"
        />

        {/* Hover crosshair + dots */}
        {hoverIdx != null && snap && (
          <>
            <line
              x1={toX(hoverIdx)}
              x2={toX(hoverIdx)}
              y1={marginTop}
              y2={marginTop + plotH}
              stroke="var(--color-text-secondary)"
              strokeWidth="0.75"
              strokeDasharray="3 2"
              opacity="0.5"
            />
            <circle
              cx={toX(hoverIdx)}
              cy={toY(snap.bh_value_usd)}
              r="3.5"
              fill="var(--color-bg-surface)"
              stroke="var(--color-text-secondary)"
              strokeWidth="1.5"
            />
            <circle
              cx={toX(hoverIdx)}
              cy={toY(snap.sf_value_usd)}
              r="3.5"
              fill="var(--color-bg-surface)"
              stroke="var(--color-accent)"
              strokeWidth="1.5"
            />
          </>
        )}
      </svg>

      {/* Tooltip */}
      {hoverIdx != null && snap && (
        <div
          className="absolute z-50 pointer-events-none bg-[var(--color-bg-elevated)] border border-[var(--color-border)] rounded-lg shadow-lg px-3 py-2 text-xs"
          style={{
            left: Math.min(tooltipPos.x + 12, (containerRef.current?.clientWidth ?? 300) - 200),
            top: Math.max(tooltipPos.y - 80, 0),
            minWidth: 180,
          }}
        >
          <div className="text-[var(--color-text-secondary)] mb-1.5 font-medium">
            {fmtDate(snap.timestamp)}
          </div>
          <div className="flex justify-between gap-4 mb-0.5">
            <span className="text-[var(--color-text-secondary)] opacity-60">Buy & Hold</span>
            <span className="text-[var(--color-text-primary)] tabular-nums font-medium">
              {fmtUsd(snap.bh_value_usd)}
            </span>
          </div>
          <div className="flex justify-between gap-4 mb-1">
            <span className="text-[var(--color-accent)]">SignalForge</span>
            <span className="text-[var(--color-text-primary)] tabular-nums font-medium">
              {fmtUsd(snap.sf_value_usd)}
            </span>
          </div>
          <div className="border-t border-[var(--color-border)] pt-1 flex justify-between gap-4">
            <span className="text-[var(--color-text-secondary)]">Difference</span>
            <span
              className="tabular-nums font-medium"
              style={{ color: diff >= 0 ? "var(--color-success)" : "var(--color-danger)" }}
            >
              {diff >= 0 ? "+" : ""}{fmtUsd(diff)}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

function OpenPositionsSection({
  positions,
}: {
  positions: {
    symbol: string;
    direction: string;
    quantity: number;
    entry_price: number;
    current_price: number | null;
    unrealized_pnl: number | null;
  }[];
}) {
  return (
    <div>
      <h4 className="text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider mb-2">
        Open Positions
      </h4>
      <div className="space-y-1.5">
        {positions.map((p) => (
          <div
            key={p.symbol}
            className="flex items-center justify-between bg-[var(--color-bg-elevated)]/50 rounded-lg px-3 py-2 text-sm"
          >
            <span className="font-medium text-[var(--color-text-primary)]">
              {p.symbol}
            </span>
            <span className="text-[var(--color-text-secondary)] tabular-nums">
              {p.quantity.toFixed(6)} @ {fmtUsd(p.entry_price)}
            </span>
            {p.unrealized_pnl != null && (
              <span
                className="font-medium tabular-nums"
                style={{ color: pnlColor(p.unrealized_pnl) }}
              >
                {p.unrealized_pnl >= 0 ? "+" : ""}
                {fmtUsd(p.unrealized_pnl)}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center py-12">
      <Loader2 className="w-6 h-6 animate-spin text-[var(--color-accent)]" />
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <p className="text-center text-sm text-[var(--color-text-secondary)] py-12">
      {message}
    </p>
  );
}
