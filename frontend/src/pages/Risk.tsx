import { usePageTitle } from "@/hooks/usePageTitle";
import { useNoIndex } from "@/hooks/useNoIndex";
import {
  AlertTriangle,
  TrendingDown,
  Lock,
  ArrowDown,
  CheckCircle,
} from "lucide-react";
import {
  useDrawdownState,
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
  1: { label: "Warning", color: "text-(--color-warning)", bg: "bg-(--color-warning)/10", icon: AlertTriangle },
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
    <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-4 sm:p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <TrendingDown className="h-5 w-5 text-(--color-accent)" aria-hidden="true" />
          <Tooltip text="Monitors how far your portfolio has fallen from its highest point. Automatically reduces or halts trading at 4 configurable levels to protect your capital.">
            <h2 className="text-sm font-semibold text-(--color-text-primary) cursor-help">
              Drawdown Circuit Breaker
            </h2>
          </Tooltip>
        </div>
        <Tooltip text={
          level === 0 ? "Normal: No drawdown risk. Full position sizing is allowed."
          : level === 1 ? "Warning: Drawdown is approaching the limit. New position sizes are automatically cut by 50%."
          : level === 2 ? "Halt: Drawdown at critical level. All new trades are blocked until equity recovers."
          : "Emergency: Severe drawdown detected. All open positions are being closed automatically to prevent further losses."
        }>
          <div className={cn("flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full cursor-help", cfg.bg, cfg.color)}>
            <Icon className="h-3.5 w-3.5" aria-hidden="true" />
            {cfg.label}
          </div>
        </Tooltip>
      </div>

      {/* Drawdown bar */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs">
          <Tooltip text="Percentage drop from your peak equity. Green (<5%) = safe, amber (5-10%) = caution, red (>10%) = danger. The bar fills toward 20% maximum.">
            <span className="text-(--color-text-secondary) cursor-help">Drawdown</span>
          </Tooltip>
          <span className={cn("font-mono font-semibold", drawdownPct > 10 ? "text-(--color-negative)" : drawdownPct > 5 ? "text-(--color-warning)" : "text-(--color-text-primary)")}>
            {drawdownPct.toFixed(2)}%
          </span>
        </div>
        <div className="h-2 bg-(--color-bg-elevated) rounded-full overflow-hidden">
          <div
            className={cn(
              "h-full rounded-full transition-all duration-500",
              drawdownPct > 10 ? "bg-(--color-negative)" : drawdownPct > 5 ? "bg-(--color-warning)" : "bg-(--color-positive)"
            )}
            style={{ width: `${Math.min(drawdownPct / 20 * 100, 100)}%` }}
          />
        </div>
        <div className="flex justify-between text-xs text-(--color-text-secondary)/60 font-mono">
          <span>0%</span>
          <span>20%</span>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-(--color-bg-elevated) rounded-lg p-3 space-y-0.5">
          <Tooltip text="The highest account value ever recorded. Drawdown is calculated as the percentage drop from this peak. Only resets upward when equity makes a new high.">
            <p className="text-xs uppercase tracking-wider text-(--color-text-secondary) cursor-help">Peak Equity</p>
          </Tooltip>
          <p className="text-sm font-mono font-semibold text-(--color-text-primary) truncate">
            ${peakEquity.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
        </div>
        <div className="bg-(--color-bg-elevated) rounded-lg p-3 space-y-0.5">
          <Tooltip text="Your account value right now. The gap between this and peak equity determines the drawdown percentage and which protection level is active.">
            <p className="text-xs uppercase tracking-wider text-(--color-text-secondary) cursor-help">Current Equity</p>
          </Tooltip>
          <p className="text-sm font-mono font-semibold text-(--color-text-primary) truncate">
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

/* ---------- Account Overview Card ---------- */

function AccountCard() {
  const { data, isLoading } = useAccountState();

  if (isLoading) return <SkeletonCard />;

  const equity = data?.equity ?? 10_000;
  const dailyPnl = data?.daily_pnl ?? 0;
  const openPos = data?.open_positions ?? 0;
  const maxPos = data?.max_positions ?? 5;

  return (
    <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-4 sm:p-5 space-y-4">
      <div className="flex items-center gap-2">
        <ArrowDown className="h-5 w-5 text-(--color-accent)" aria-hidden="true" />
        <Tooltip text="Real-time snapshot of your trading account. All values update automatically when positions change.">
          <h2 className="text-sm font-semibold text-(--color-text-primary) cursor-help">
            Account Overview
          </h2>
        </Tooltip>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="bg-(--color-bg-elevated) rounded-lg p-3 space-y-0.5">
          <Tooltip text="Total account value including cash balance and unrealized profit/loss from all open positions.">
            <p className="text-xs uppercase tracking-wider text-(--color-text-secondary) cursor-help">Equity</p>
          </Tooltip>
          <p className="text-sm font-mono font-semibold text-(--color-text-primary)">
            ${equity.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
        </div>
        <div className="bg-(--color-bg-elevated) rounded-lg p-3 space-y-0.5">
          <Tooltip text="Net profit or loss for today's trading session. Green = profit, red = loss. Resets at the start of each trading day.">
            <p className="text-xs uppercase tracking-wider text-(--color-text-secondary) cursor-help">Daily P&L</p>
          </Tooltip>
          <p className={cn(
            "text-sm font-mono font-semibold",
            dailyPnl > 0 ? "text-(--color-positive)" : dailyPnl < 0 ? "text-(--color-negative)" : "text-(--color-text-primary)"
          )}>
            {dailyPnl >= 0 ? "+" : ""}${dailyPnl.toFixed(2)}
          </p>
        </div>
        <div className="bg-(--color-bg-elevated) rounded-lg p-3 space-y-0.5">
          <Tooltip text="Currently open trades vs. the maximum allowed at once. The limit prevents over-exposure to market risk.">
            <p className="text-xs uppercase tracking-wider text-(--color-text-secondary) cursor-help">Positions</p>
          </Tooltip>
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
  usePageTitle("Risk");
  useNoIndex();
  return (
    <div className="max-w-[1200px] mx-auto p-4 sm:p-6 space-y-4 sm:space-y-6">
      {/* Header */}
      <div>
        <Tooltip text="Monitor and control portfolio risk with drawdown breakers and account overview.">
          <h1 className="text-2xl font-bold text-(--color-text-primary) cursor-help">Risk Management</h1>
        </Tooltip>
        <p className="text-sm text-(--color-text-secondary) mt-1">
          Portfolio protection and drawdown monitoring
        </p>
      </div>

      {/* Account overview */}
      <AccountCard />

      {/* Drawdown circuit breaker */}
      <DrawdownCard />
    </div>
  );
}
