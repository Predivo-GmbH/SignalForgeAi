import {
  Shield,
  AlertTriangle,
  TrendingDown,
  Activity,
  Lock,
  Unlock,
  ArrowDown,
  CheckCircle,
} from "lucide-react";
import {
  useDrawdownState,
  useCPPIState,
  useCorrelationState,
  useAccountState,
} from "@/hooks/usePositions";
import { cn } from "@/lib/cn";
import { Tooltip } from "@/components/ui/Tooltip";

/* ---------- Drawdown Breaker Card ---------- */

const LEVEL_CONFIG: Record<
  number,
  { label: string; color: string; bg: string; icon: typeof CheckCircle }
> = {
  0: { label: "Normal", color: "text-(--color-positive)", bg: "bg-(--color-positive)/10", icon: CheckCircle },
  1: { label: "Warning", color: "text-amber-500", bg: "bg-amber-500/10", icon: AlertTriangle },
  2: { label: "Halt", color: "text-(--color-negative)", bg: "bg-(--color-negative)/10", icon: Lock },
  3: { label: "Emergency", color: "text-(--color-negative)", bg: "bg-(--color-negative)/20", icon: AlertTriangle },
};

function DrawdownCard() {
  const { data, isLoading } = useDrawdownState();

  if (isLoading) return <SkeletonCard />;

  const level = data?.level ?? 0;
  const cfg = LEVEL_CONFIG[Math.min(level, 3)];
  const Icon = cfg.icon;
  const drawdownPct = data?.drawdown_pct ?? 0;
  const peakEquity = data?.peak_equity ?? 0;
  const currentEquity = data?.current_equity ?? 0;

  return (
    <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <TrendingDown className="h-5 w-5 text-(--color-accent)" />
          <h3 className="text-sm font-semibold text-(--color-text-primary)">
            Drawdown Circuit Breaker
          </h3>
          <Tooltip text="Monitors portfolio drawdown from peak equity. Reduces or halts trading at configurable thresholds." />
        </div>
        <div className={cn("flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full", cfg.bg, cfg.color)}>
          <Icon className="h-3.5 w-3.5" />
          {cfg.label}
        </div>
      </div>

      {/* Drawdown bar */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs">
          <span className="text-(--color-text-secondary)">Drawdown</span>
          <span className={cn("font-mono font-semibold", drawdownPct > 10 ? "text-(--color-negative)" : drawdownPct > 5 ? "text-amber-500" : "text-(--color-text-primary)")}>
            {drawdownPct.toFixed(2)}%
          </span>
        </div>
        <div className="h-2 bg-(--color-bg-elevated) rounded-full overflow-hidden">
          <div
            className={cn(
              "h-full rounded-full transition-all duration-500",
              drawdownPct > 10 ? "bg-(--color-negative)" : drawdownPct > 5 ? "bg-amber-500" : "bg-(--color-positive)"
            )}
            style={{ width: `${Math.min(drawdownPct / 20 * 100, 100)}%` }}
          />
        </div>
        <div className="flex justify-between text-[10px] text-(--color-text-secondary)/60 font-mono">
          <span>0%</span>
          <span>20%</span>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-(--color-bg-elevated) rounded-lg p-3 space-y-0.5">
          <p className="text-[10px] uppercase tracking-wider text-(--color-text-secondary)">Peak Equity</p>
          <p className="text-sm font-mono font-semibold text-(--color-text-primary)">
            ${peakEquity.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
        </div>
        <div className="bg-(--color-bg-elevated) rounded-lg p-3 space-y-0.5">
          <p className="text-[10px] uppercase tracking-wider text-(--color-text-secondary)">Current Equity</p>
          <p className="text-sm font-mono font-semibold text-(--color-text-primary)">
            ${currentEquity.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
        </div>
      </div>

      {/* Level description */}
      <div className="text-xs text-(--color-text-secondary) leading-relaxed">
        {level === 0 && "All systems normal. Full position sizing allowed."}
        {level === 1 && "Drawdown approaching limit. New position sizes reduced by 50%."}
        {level === 2 && "Drawdown at limit. All new trades blocked until recovery."}
        {level === 3 && "Emergency drawdown. All positions being closed automatically."}
      </div>
    </div>
  );
}

/* ---------- CPPI Card ---------- */

function CPPICard() {
  const { data, isLoading } = useCPPIState();

  if (isLoading) return <SkeletonCard />;

  const exposure = data?.exposure_pct ?? 100;
  const floor = data?.floor ?? 0;
  const peakEquity = data?.peak_equity ?? 0;
  const cushion = data?.cushion ?? 0;
  const multiplier = data?.multiplier ?? 3.0;

  const isReduced = exposure < 100;

  return (
    <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Shield className="h-5 w-5 text-(--color-accent)" />
          <h3 className="text-sm font-semibold text-(--color-text-primary)">
            Portfolio Insurance (CPPI)
          </h3>
          <Tooltip text="Constant Proportion Portfolio Insurance. Dynamically adjusts risky exposure based on cushion above floor value." />
        </div>
        <div className={cn(
          "flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full",
          isReduced ? "bg-amber-500/10 text-amber-500" : "bg-(--color-positive)/10 text-(--color-positive)"
        )}>
          {isReduced ? <Unlock className="h-3.5 w-3.5" /> : <Lock className="h-3.5 w-3.5" />}
          {exposure.toFixed(0)}% Exposed
        </div>
      </div>

      {/* Exposure bar */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs">
          <span className="text-(--color-text-secondary)">Risk Exposure</span>
          <span className={cn("font-mono font-semibold", exposure < 50 ? "text-(--color-negative)" : exposure < 80 ? "text-amber-500" : "text-(--color-positive)")}>
            {exposure.toFixed(1)}%
          </span>
        </div>
        <div className="h-2 bg-(--color-bg-elevated) rounded-full overflow-hidden">
          <div
            className={cn(
              "h-full rounded-full transition-all duration-500",
              exposure < 50 ? "bg-(--color-negative)" : exposure < 80 ? "bg-amber-500" : "bg-(--color-positive)"
            )}
            style={{ width: `${exposure}%` }}
          />
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-2">
        <div className="bg-(--color-bg-elevated) rounded-lg p-3 space-y-0.5">
          <p className="text-[10px] uppercase tracking-wider text-(--color-text-secondary)">Floor</p>
          <p className="text-sm font-mono font-semibold text-(--color-text-primary)">
            ${floor.toLocaleString(undefined, { maximumFractionDigits: 0 })}
          </p>
        </div>
        <div className="bg-(--color-bg-elevated) rounded-lg p-3 space-y-0.5">
          <p className="text-[10px] uppercase tracking-wider text-(--color-text-secondary)">Cushion</p>
          <p className="text-sm font-mono font-semibold text-(--color-positive)">
            ${cushion.toLocaleString(undefined, { maximumFractionDigits: 0 })}
          </p>
        </div>
        <div className="bg-(--color-bg-elevated) rounded-lg p-3 space-y-0.5">
          <p className="text-[10px] uppercase tracking-wider text-(--color-text-secondary)">Multiplier</p>
          <p className="text-sm font-mono font-semibold text-(--color-text-primary)">
            {multiplier.toFixed(1)}x
          </p>
        </div>
      </div>

      <div className="text-xs text-(--color-text-secondary) leading-relaxed">
        Peak equity: ${peakEquity.toLocaleString(undefined, { maximumFractionDigits: 0 })}.
        {cushion > 0
          ? ` Cushion of $${cushion.toLocaleString(undefined, { maximumFractionDigits: 0 })} above floor allows ${exposure.toFixed(0)}% exposure.`
          : " No cushion — maximum protection active."}
      </div>
    </div>
  );
}

/* ---------- Correlation Card ---------- */

function CorrelationCard() {
  const { data, isLoading } = useCorrelationState();

  if (isLoading) return <SkeletonCard />;

  const alerts = data?.alerts ?? [];
  const maxCorr = data?.max_correlation ?? 0;
  const penalty = data?.exposure_penalty ?? 1.0;
  const matrix = data?.matrix ?? {};
  const symbols = Object.keys(matrix);

  const hasAlerts = alerts.length > 0;

  return (
    <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className="h-5 w-5 text-(--color-accent)" />
          <h3 className="text-sm font-semibold text-(--color-text-primary)">
            Correlation Monitor
          </h3>
          <Tooltip text="Tracks pairwise correlation between open positions. Reduces sizing when high correlation detected to prevent concentrated risk." />
        </div>
        <div className={cn(
          "flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full",
          hasAlerts ? "bg-amber-500/10 text-amber-500" : "bg-(--color-positive)/10 text-(--color-positive)"
        )}>
          {hasAlerts ? <AlertTriangle className="h-3.5 w-3.5" /> : <CheckCircle className="h-3.5 w-3.5" />}
          {hasAlerts ? `${alerts.length} Alert${alerts.length > 1 ? "s" : ""}` : "Clear"}
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-(--color-bg-elevated) rounded-lg p-3 space-y-0.5">
          <p className="text-[10px] uppercase tracking-wider text-(--color-text-secondary)">Max Correlation</p>
          <p className={cn(
            "text-sm font-mono font-semibold",
            maxCorr > 0.85 ? "text-(--color-negative)" : maxCorr > 0.7 ? "text-amber-500" : "text-(--color-positive)"
          )}>
            {maxCorr.toFixed(3)}
          </p>
        </div>
        <div className="bg-(--color-bg-elevated) rounded-lg p-3 space-y-0.5">
          <p className="text-[10px] uppercase tracking-wider text-(--color-text-secondary)">Sizing Penalty</p>
          <p className={cn(
            "text-sm font-mono font-semibold",
            penalty < 0.7 ? "text-(--color-negative)" : penalty < 1.0 ? "text-amber-500" : "text-(--color-positive)"
          )}>
            {(penalty * 100).toFixed(0)}%
          </p>
        </div>
      </div>

      {/* Alerts list */}
      {alerts.length > 0 ? (
        <div className="space-y-2">
          <p className="text-xs font-medium text-(--color-text-secondary)">Correlation Alerts</p>
          <div className="space-y-1.5">
            {alerts.map((alert, i) => (
              <div
                key={i}
                className={cn(
                  "flex items-center justify-between rounded-lg px-3 py-2 text-xs",
                  alert.risk_level === "critical"
                    ? "bg-(--color-negative)/10 border border-(--color-negative)/20"
                    : "bg-amber-500/10 border border-amber-500/20"
                )}
              >
                <span className="font-medium text-(--color-text-primary)">
                  {alert.symbol_a} / {alert.symbol_b}
                </span>
                <div className="flex items-center gap-2">
                  <span className="font-mono">{alert.correlation.toFixed(3)}</span>
                  <span className={cn(
                    "uppercase text-[10px] font-semibold",
                    alert.risk_level === "critical" ? "text-(--color-negative)" : "text-amber-500"
                  )}>
                    {alert.risk_level}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : symbols.length > 0 ? (
        <div className="text-xs text-(--color-text-secondary) leading-relaxed">
          Monitoring {symbols.length} symbol{symbols.length !== 1 ? "s" : ""}. No high-correlation pairs detected.
        </div>
      ) : (
        <div className="text-xs text-(--color-text-secondary) leading-relaxed">
          No open positions to monitor. Correlation data will appear when positions are opened.
        </div>
      )}
    </div>
  );
}

/* ---------- Account Overview Card ---------- */

function AccountCard() {
  const { data, isLoading } = useAccountState();

  if (isLoading) return <SkeletonCard />;

  const equity = data?.equity ?? 10_000;
  const dailyPnl = data?.daily_pnl ?? 0;
  const openPos = data?.open_positions ?? 0;
  const maxPos = data?.max_positions ?? 5;

  return (
    <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-5 space-y-4">
      <div className="flex items-center gap-2">
        <ArrowDown className="h-5 w-5 text-(--color-accent)" />
        <h3 className="text-sm font-semibold text-(--color-text-primary)">
          Account Overview
        </h3>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div className="bg-(--color-bg-elevated) rounded-lg p-3 space-y-0.5">
          <p className="text-[10px] uppercase tracking-wider text-(--color-text-secondary)">Equity</p>
          <p className="text-sm font-mono font-semibold text-(--color-text-primary)">
            ${equity.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
        </div>
        <div className="bg-(--color-bg-elevated) rounded-lg p-3 space-y-0.5">
          <p className="text-[10px] uppercase tracking-wider text-(--color-text-secondary)">Daily P&L</p>
          <p className={cn(
            "text-sm font-mono font-semibold",
            dailyPnl > 0 ? "text-(--color-positive)" : dailyPnl < 0 ? "text-(--color-negative)" : "text-(--color-text-primary)"
          )}>
            {dailyPnl >= 0 ? "+" : ""}${dailyPnl.toFixed(2)}
          </p>
        </div>
        <div className="bg-(--color-bg-elevated) rounded-lg p-3 space-y-0.5">
          <p className="text-[10px] uppercase tracking-wider text-(--color-text-secondary)">Positions</p>
          <p className="text-sm font-mono font-semibold text-(--color-text-primary)">
            {openPos} / {maxPos}
          </p>
        </div>
      </div>
    </div>
  );
}

/* ---------- Skeleton ---------- */

function SkeletonCard() {
  return (
    <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-5 space-y-4">
      <div className="flex items-center gap-2">
        <div className="w-5 h-5 rounded bg-(--color-bg-elevated) animate-pulse" />
        <div className="h-4 w-40 rounded bg-(--color-bg-elevated) animate-pulse" />
      </div>
      <div className="h-2 rounded-full bg-(--color-bg-elevated) animate-pulse" />
      <div className="grid grid-cols-2 gap-3">
        <div className="h-16 rounded-lg bg-(--color-bg-elevated) animate-pulse" />
        <div className="h-16 rounded-lg bg-(--color-bg-elevated) animate-pulse" />
      </div>
    </div>
  );
}

/* ---------- Page ---------- */

export function RiskPage() {
  return (
    <div className="max-w-[1200px] mx-auto p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-(--color-text-primary)">Risk Management</h1>
        <p className="text-sm text-(--color-text-secondary) mt-1">
          Portfolio protection, drawdown monitoring, and correlation analysis
        </p>
      </div>

      {/* Account overview (full width) */}
      <AccountCard />

      {/* Risk cards grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <DrawdownCard />
        <CPPICard />
      </div>

      {/* Correlation (full width) */}
      <CorrelationCard />
    </div>
  );
}
