import { useState } from "react";
import {
  Shield,
  Brain,
  Pencil,
  Check,
  X,
  AlertTriangle,
  CheckCircle2,
} from "lucide-react";
import { Tooltip } from "@/components/ui/Tooltip";
import { fmtUsd } from "@/lib/format";
import { useUpdateReserve } from "@/hooks/useSimulation";

interface UsdtReserveWidgetProps {
  simId: string;
  reservePct: number;
  reserveMode: string;
  usdtBalance: number;
  reserveTargetUsd: number;
  reserveStatus: "at_target" | "below_target" | "above_target";
  aiSuggestedPct: number | null;
  aiReasoning: string | null;
}

export function UsdtReserveWidget({
  simId,
  reservePct,
  reserveMode,
  usdtBalance,
  reserveTargetUsd,
  reserveStatus,
  aiSuggestedPct,
  aiReasoning,
}: UsdtReserveWidgetProps) {
  const [editing, setEditing] = useState(false);
  const [editValue, setEditValue] = useState(Math.round(reservePct * 100));
  const updateReserve = useUpdateReserve();

  const handleSave = () => {
    const pct = Math.max(0, Math.min(50, editValue)) / 100;
    updateReserve.mutate({ simId, usdt_reserve_pct: pct, mode: "manual" });
    setEditing(false);
  };

  const handleAcceptAi = () => {
    if (aiSuggestedPct != null) {
      updateReserve.mutate({
        simId,
        usdt_reserve_pct: aiSuggestedPct,
        mode: "ai",
      });
    }
  };

  const statusIcon =
    reserveStatus === "at_target" ? (
      <CheckCircle2 className="w-3.5 h-3.5 text-[var(--color-positive)]" aria-hidden="true" />
    ) : reserveStatus === "below_target" ? (
      <AlertTriangle className="w-3.5 h-3.5 text-[var(--color-warning)]" aria-hidden="true" />
    ) : (
      <CheckCircle2 className="w-3.5 h-3.5 text-[var(--color-accent)]" aria-hidden="true" />
    );

  const statusLabel =
    reserveStatus === "at_target"
      ? "At target"
      : reserveStatus === "below_target"
        ? "Below target"
        : "Above target";

  return (
    <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border)] rounded-xl p-3 sm:p-4 space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Shield className="w-4 h-4 text-[var(--color-accent)]" aria-hidden="true" />
          <Tooltip text="USDT reserve ensures dry powder is always available for buy signals. The AI Advisor recommends the optimal % based on market conditions.">
            <h3 className="text-sm font-semibold text-[var(--color-text-primary)] cursor-help">
              USDT Reserve
            </h3>
          </Tooltip>
        </div>
        <div className="flex items-center gap-1.5">
          {statusIcon}
          <span className="text-xs text-[var(--color-text-secondary)]">
            {statusLabel}
          </span>
        </div>
      </div>

      {/* Current reserve */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
        <div className="bg-[var(--color-bg-elevated)]/50 rounded-lg p-2.5">
          <span className="text-xs text-[var(--color-text-secondary)] uppercase tracking-wider">
            Target
          </span>
          <p className="text-sm font-semibold text-[var(--color-text-primary)] mt-0.5">
            {(reservePct * 100).toFixed(0)}%
          </p>
        </div>
        <div className="bg-[var(--color-bg-elevated)]/50 rounded-lg p-2.5">
          <span className="text-xs text-[var(--color-text-secondary)] uppercase tracking-wider">
            USDT Balance
          </span>
          <p className="text-sm font-semibold text-[var(--color-text-primary)] mt-0.5">
            {fmtUsd(usdtBalance)}
          </p>
        </div>
        <div className="bg-[var(--color-bg-elevated)]/50 rounded-lg p-2.5">
          <span className="text-xs text-[var(--color-text-secondary)] uppercase tracking-wider">
            Target USD
          </span>
          <p className="text-sm font-semibold text-[var(--color-text-primary)] mt-0.5">
            {fmtUsd(reserveTargetUsd)}
          </p>
        </div>
      </div>

      {/* AI suggestion */}
      {aiSuggestedPct != null && reserveMode !== "manual" && (
        <div className="flex items-start gap-2 bg-[var(--color-accent)]/5 border border-[var(--color-accent)]/20 rounded-lg p-3">
          <Brain className="w-4 h-4 text-[var(--color-accent)] mt-0.5 shrink-0" aria-hidden="true" />
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-[var(--color-accent)]">
                AI recommends {(aiSuggestedPct * 100).toFixed(0)}%
              </span>
              {Math.abs(aiSuggestedPct - reservePct) > 0.01 && (
                <button
                  onClick={handleAcceptAi}
                  disabled={updateReserve.isPending}
                  className="text-xs font-medium text-[var(--color-accent)] hover:underline min-h-[44px]"
                >
                  Apply
                </button>
              )}
            </div>
            {aiReasoning && (
              <p className="text-xs text-[var(--color-text-secondary)] mt-1 leading-relaxed">
                {aiReasoning}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Edit reserve */}
      {!editing ? (
        <button
          onClick={() => {
            setEditValue(Math.round(reservePct * 100));
            setEditing(true);
          }}
          className="flex items-center gap-1.5 text-xs text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors min-h-[44px]"
        >
          <Pencil className="w-3 h-3" aria-hidden="true" />
          Set manually
        </button>
      ) : (
        <div className="flex items-center gap-2">
          <input
            type="number"
            min={0}
            max={50}
            value={editValue}
            onChange={(e) => setEditValue(Number(e.target.value))}
            aria-label="Reserve percentage"
            className="w-20 px-2 py-1.5 min-h-[44px] rounded-lg bg-[var(--color-bg-elevated)] border border-[var(--color-border)] text-base sm:text-sm text-[var(--color-text-primary)] text-center focus:outline-none focus:ring-1 focus:ring-[var(--color-accent)]"
          />
          <span className="text-xs text-[var(--color-text-secondary)]">%</span>
          <button
            onClick={handleSave}
            disabled={updateReserve.isPending}
            aria-label="Save reserve percentage"
            className="p-2.5 min-h-[44px] min-w-[44px] flex items-center justify-center rounded-lg bg-[var(--color-positive)]/10 text-[var(--color-positive)] hover:bg-[var(--color-positive)]/20 transition-colors"
          >
            <Check className="w-3.5 h-3.5" aria-hidden="true" />
          </button>
          <button
            onClick={() => setEditing(false)}
            aria-label="Cancel editing"
            className="p-2.5 min-h-[44px] min-w-[44px] flex items-center justify-center rounded-lg bg-[var(--color-bg-elevated)] text-[var(--color-text-secondary)] hover:bg-[var(--color-border)] transition-colors"
          >
            <X className="w-3.5 h-3.5" aria-hidden="true" />
          </button>
        </div>
      )}

      {/* Mode indicator */}
      <div className="text-xs text-[var(--color-text-secondary)]">
        Mode: {reserveMode === "ai" ? "AI-managed" : reserveMode === "auto_accept" ? "Auto-accept AI" : "Manual"}
      </div>
    </div>
  );
}
