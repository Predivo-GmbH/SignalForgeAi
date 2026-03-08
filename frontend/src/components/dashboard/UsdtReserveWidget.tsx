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
      <CheckCircle2 className="w-3.5 h-3.5 text-[var(--color-positive)]" />
    ) : reserveStatus === "below_target" ? (
      <AlertTriangle className="w-3.5 h-3.5 text-[var(--color-warning)]" />
    ) : (
      <CheckCircle2 className="w-3.5 h-3.5 text-[var(--color-accent)]" />
    );

  const statusLabel =
    reserveStatus === "at_target"
      ? "At target"
      : reserveStatus === "below_target"
        ? "Below target"
        : "Above target";

  return (
    <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border)] rounded-xl p-4 space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Shield className="w-4 h-4 text-[var(--color-accent)]" />
          <Tooltip text="USDT reserve ensures dry powder is always available for buy signals. The AI Advisor recommends the optimal % based on market conditions.">
            <h3 className="text-sm font-semibold text-[var(--color-text-primary)] cursor-help">
              USDT Reserve
            </h3>
          </Tooltip>
        </div>
        <div className="flex items-center gap-1.5">
          {statusIcon}
          <span className="text-[11px] text-[var(--color-text-secondary)]">
            {statusLabel}
          </span>
        </div>
      </div>

      {/* Current reserve */}
      <div className="grid grid-cols-3 gap-2">
        <div className="bg-[var(--color-bg-elevated)]/50 rounded-lg p-2.5">
          <span className="text-[10px] text-[var(--color-text-secondary)] uppercase tracking-wider">
            Target
          </span>
          <p className="text-sm font-semibold text-[var(--color-text-primary)] mt-0.5">
            {(reservePct * 100).toFixed(0)}%
          </p>
        </div>
        <div className="bg-[var(--color-bg-elevated)]/50 rounded-lg p-2.5">
          <span className="text-[10px] text-[var(--color-text-secondary)] uppercase tracking-wider">
            USDT Balance
          </span>
          <p className="text-sm font-semibold text-[var(--color-text-primary)] mt-0.5">
            {fmtUsd(usdtBalance)}
          </p>
        </div>
        <div className="bg-[var(--color-bg-elevated)]/50 rounded-lg p-2.5">
          <span className="text-[10px] text-[var(--color-text-secondary)] uppercase tracking-wider">
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
          <Brain className="w-4 h-4 text-[var(--color-accent)] mt-0.5 shrink-0" />
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-[var(--color-accent)]">
                AI recommends {(aiSuggestedPct * 100).toFixed(0)}%
              </span>
              {Math.abs(aiSuggestedPct - reservePct) > 0.01 && (
                <button
                  onClick={handleAcceptAi}
                  disabled={updateReserve.isPending}
                  className="text-[11px] font-medium text-[var(--color-accent)] hover:underline"
                >
                  Apply
                </button>
              )}
            </div>
            {aiReasoning && (
              <p className="text-[11px] text-[var(--color-text-secondary)] mt-1 leading-relaxed">
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
          className="flex items-center gap-1.5 text-xs text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
        >
          <Pencil className="w-3 h-3" />
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
            className="w-20 px-2 py-1.5 rounded-lg bg-[var(--color-bg-elevated)] border border-[var(--color-border)] text-sm text-[var(--color-text-primary)] text-center focus:outline-none focus:ring-1 focus:ring-[var(--color-accent)]"
          />
          <span className="text-xs text-[var(--color-text-secondary)]">%</span>
          <button
            onClick={handleSave}
            disabled={updateReserve.isPending}
            className="p-1.5 rounded-lg bg-[var(--color-positive)]/10 text-[var(--color-positive)] hover:bg-[var(--color-positive)]/20 transition-colors"
          >
            <Check className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setEditing(false)}
            className="p-1.5 rounded-lg bg-[var(--color-bg-elevated)] text-[var(--color-text-secondary)] hover:bg-[var(--color-border)] transition-colors"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Mode indicator */}
      <div className="text-[10px] text-[var(--color-text-secondary)]">
        Mode: {reserveMode === "ai" ? "AI-managed" : reserveMode === "auto_accept" ? "Auto-accept AI" : "Manual"}
      </div>
    </div>
  );
}
