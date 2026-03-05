import { Link } from "react-router-dom";
import { Target, Loader2, Zap } from "lucide-react";
import { useStrategies } from "@/hooks/useStrategies";
import { useEngineStatus } from "@/hooks/useEngineStatus";
import { cn } from "@/lib/cn";
import { Tooltip } from "@/components/ui/Tooltip";

export function ActiveStrategyCard() {
  const { data: strategiesData, isLoading: strategiesLoading } = useStrategies();
  const { data: engine, isLoading: engineLoading } = useEngineStatus();

  if (strategiesLoading || engineLoading) {
    return (
      <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-5 flex items-center justify-center min-h-[100px]">
        <Loader2 className="w-5 h-5 animate-spin text-(--color-accent)" />
      </div>
    );
  }

  const activeStrategies = strategiesData?.strategies?.filter((s) => s.is_active) ?? [];
  const engineActive = engine?.active ?? false;

  if (activeStrategies.length === 0) {
    return (
      <Link
        to="/advisor"
        className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-5 flex flex-col items-center justify-center gap-2 hover:border-(--color-accent)/30 transition-colors min-h-[100px]"
      >
        <Target className="w-6 h-6 text-(--color-text-secondary)/40" />
        <p className="text-xs text-(--color-text-secondary)">No active strategy</p>
        <span className="text-xs font-medium text-(--color-accent)">Set up with AI Advisor →</span>
      </Link>
    );
  }

  return (
    <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-5 space-y-3">
      <div className="flex items-center justify-between">
        <Tooltip text="The currently running trading strategy and its real-time performance."><h3 className="text-sm font-semibold text-(--color-text-primary) cursor-help">Active Strategy</h3></Tooltip>
        <Link
          to="/strategies"
          className="text-xs font-medium text-(--color-accent) hover:text-(--color-accent)/80 transition-colors"
        >
          Manage →
        </Link>
      </div>

      {activeStrategies.map((s) => {
        const symbols = Array.isArray(s.config?.symbols) ? (s.config.symbols as string[]) : [];
        return (
          <Link
            key={s.id}
            to={`/strategies/${s.id}`}
            className="flex items-center gap-3 p-3 rounded-lg bg-(--color-bg-elevated)/50 hover:bg-(--color-bg-elevated) transition-colors"
          >
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-(--color-accent)/15">
              <Target className="w-4 h-4 text-(--color-accent)" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-(--color-text-primary) truncate">{s.name}</p>
              {symbols.length > 0 && (
                <p className="text-[11px] text-(--color-text-secondary) truncate">
                  {symbols.join(", ")}
                </p>
              )}
            </div>
            <div className="flex items-center gap-1.5 shrink-0">
              <div className={cn("w-2 h-2 rounded-full", engineActive ? "bg-(--color-positive) animate-pulse" : "bg-(--color-text-secondary)/40")} />
              <span className="text-[11px] text-(--color-text-secondary)">
                {engineActive ? "Running" : "Idle"}
              </span>
            </div>
          </Link>
        );
      })}

      {engineActive && (
        <div className="flex items-center gap-1.5 text-[11px] text-(--color-text-secondary)">
          <Zap className="w-3 h-3 text-(--color-accent)" />
          Engine active — {engine?.layers?.length ?? 0} analysis layers
        </div>
      )}
    </div>
  );
}
