import { Cpu, Circle, TrendingUp, Shield, AlertTriangle } from "lucide-react";
import { Tooltip } from "@/components/ui/Tooltip";
import { useEngineStatus } from "@/hooks/useEngineStatus";
import { useRegimeStatus, type RegimeStatus } from "@/hooks/useRegimeStatus";

const REGIME_CONFIG: Record<string, { label: string; color: string; icon: typeof TrendingUp }> = {
  low_vol: { label: "Low Volatility", color: "var(--color-positive)", icon: Shield },
  trending: { label: "Trending", color: "var(--color-accent)", icon: TrendingUp },
  high_vol: { label: "High Volatility", color: "var(--color-negative)", icon: AlertTriangle },
  unknown: { label: "Unknown", color: "var(--color-text-secondary)", icon: Cpu },
};

export function RegimeWidget() {
  const { data: engineData, isLoading: engineLoading } = useEngineStatus();
  const { data: regimeData, isLoading: regimeLoading } = useRegimeStatus();

  const isLoading = engineLoading || regimeLoading;

  if (isLoading) {
    return (
      <div className="bg-[var(--color-bg-surface)] rounded-xl border border-[var(--color-border)] p-4">
        <div className="flex items-center gap-2 mb-3">
          <div className="h-4 w-4 rounded bg-[var(--color-bg-elevated)] animate-pulse" />
          <div className="h-4 w-24 rounded bg-[var(--color-bg-elevated)] animate-pulse" />
        </div>
        <div className="space-y-2">
          <div className="h-3 w-32 rounded bg-[var(--color-bg-elevated)] animate-pulse" />
          <div className="flex gap-1.5">
            {Array.from({ length: 3 }, (_, i) => (
              <div
                key={i}
                className="h-5 w-16 rounded-full bg-[var(--color-bg-elevated)] animate-pulse"
              />
            ))}
          </div>
        </div>
      </div>
    );
  }

  const isActive = engineData?.active ?? false;
  const regimeEnabled = regimeData?.regime_allocator_enabled ?? false;

  return (
    <div className="bg-[var(--color-bg-surface)] rounded-xl border border-[var(--color-border)] p-4">
      <div className="flex items-center gap-2 mb-4">
        <Cpu className="h-4 w-4 text-[var(--color-accent)]" />
        <Tooltip text="Current state of the trading engine and market regime detected by the HMM model.">
          <h3 className="text-sm font-semibold text-[var(--color-text-primary)] cursor-help">Engine Status</h3>
        </Tooltip>
      </div>

      <div className="flex items-center gap-2 mb-4">
        <Circle
          className={`h-2.5 w-2.5 fill-current ${
            isActive
              ? "text-[var(--color-positive)]"
              : "text-[var(--color-negative)]"
          }`}
        />
        <span className="text-sm font-medium text-[var(--color-text-primary)]">
          {isActive ? "Engine Active" : "Engine Inactive"}
        </span>
      </div>

      {engineData?.layers && engineData.layers.length > 0 && (
        <div className={regimeEnabled ? "mb-4" : ""}>
          <span className="text-xs text-[var(--color-text-secondary)] uppercase tracking-wider font-semibold">
            Layers
          </span>
          <div className="flex flex-wrap gap-1.5 mt-2">
            {engineData.layers.map((layer) => (
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

      {regimeEnabled && regimeData && (
        <RegimeSection data={regimeData} />
      )}
    </div>
  );
}

function RegimeSection({ data }: { data: RegimeStatus }) {
  const regime = data.current_regime || "unknown";
  const config = REGIME_CONFIG[regime] || REGIME_CONFIG.unknown;
  const Icon = config.icon;
  const allocationPct = data.current_allocation_pct;

  return (
    <div className="border-t border-[var(--color-border)] pt-4">
      <span className="text-xs text-[var(--color-text-secondary)] uppercase tracking-wider font-semibold">
        Market Regime
      </span>

      {/* Regime badge */}
      <div className="flex items-center gap-2 mt-2 mb-3">
        <Icon className="h-4 w-4" style={{ color: config.color }} />
        <span className="text-sm font-semibold" style={{ color: config.color }}>
          {config.label}
        </span>
        <span className="ml-auto text-xs text-[var(--color-text-secondary)] capitalize">
          {data.allocation_table}
        </span>
      </div>

      {/* Allocation bar */}
      <div className="mb-2">
        <div className="flex justify-between text-xs text-[var(--color-text-secondary)] mb-1">
          <span>Allocation</span>
          <span>{allocationPct.toFixed(0)}%</span>
        </div>
        <div className="h-2 rounded-full bg-[var(--color-bg-elevated)] overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${allocationPct}%`,
              backgroundColor: config.color,
            }}
          />
        </div>
        {data.target_allocation_pct !== allocationPct && (
          <div className="text-xs text-[var(--color-text-secondary)] mt-1">
            Target: {data.target_allocation_pct.toFixed(0)}%
            <span className="ml-1 opacity-60">(smoothing {data.smoothing_bars} bars)</span>
          </div>
        )}
      </div>

      {/* Cooldown indicator */}
      {data.cooldown_hours > 0 && (
        <div className="flex items-center gap-1.5 mt-2">
          <div className="h-1.5 w-1.5 rounded-full bg-[var(--color-warning)]" />
          <span className="text-xs text-[var(--color-text-secondary)]">
            {data.cooldown_hours}h cooldown after trades
          </span>
        </div>
      )}
    </div>
  );
}
