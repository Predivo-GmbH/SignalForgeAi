import { useState } from "react";
import { Briefcase, X } from "lucide-react";
import { Tooltip } from "@/components/ui/Tooltip";
import { formatPrice } from "@/lib/format";
import type { Position } from "@/hooks/usePositions";
import { useClosePosition } from "@/hooks/usePositions";

interface PositionsTableProps {
  positions: Position[] | undefined;
  loading?: boolean;
}

function SkeletonRow() {
  return (
    <tr>
      {Array.from({ length: 5 }, (_, i) => (
        <td key={i} className="px-3 sm:px-4 py-3">
          <div className="h-4 rounded bg-[var(--color-bg-elevated)] animate-pulse" />
        </td>
      ))}
    </tr>
  );
}

function CloseButton({ position }: { position: Position }) {
  const [confirming, setConfirming] = useState(false);
  const closePosition = useClosePosition();

  const handleClose = () => {
    if (!confirming) {
      setConfirming(true);
      return;
    }
    const exitPrice = position.current_price ?? position.entry_price;
    closePosition.mutate(
      { positionId: position.id, exitPrice },
      { onSettled: () => setConfirming(false) },
    );
  };

  return (
    <div className="flex items-center gap-1">
      {confirming && (
        <button
          onClick={() => setConfirming(false)}
          className="text-xs text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
        >
          Cancel
        </button>
      )}
      <button
        onClick={handleClose}
        disabled={closePosition.isPending}
        className={`flex items-center justify-center h-6 rounded transition-colors ${
          confirming
            ? "bg-[var(--color-negative)] text-white px-2 text-xs font-medium hover:bg-[var(--color-negative)]/80"
            : "w-6 text-[var(--color-text-secondary)] hover:text-[var(--color-negative)] hover:bg-[var(--color-negative)]/10"
        }`}
        title={confirming ? "Confirm close" : "Close position"}
      >
        {closePosition.isPending ? (
          <div className="w-3 h-3 border border-current border-t-transparent rounded-full animate-spin" />
        ) : confirming ? (
          "Close"
        ) : (
          <X className="h-3.5 w-3.5" />
        )}
      </button>
    </div>
  );
}

export function PositionsTable({ positions, loading }: PositionsTableProps) {
  const openPositions = positions?.filter((p) => p.is_open) ?? [];

  return (
    <div className="bg-[var(--color-bg-surface)] rounded-xl border border-[var(--color-border)] overflow-hidden">
      <div className="flex items-center gap-2 px-3 sm:px-4 py-3 border-b border-[var(--color-border)]">
        <Briefcase className="h-4 w-4 text-[var(--color-accent)]" />
        <Tooltip text="Currently active trading positions managed by the engine with live P&L.">
          <h3 className="text-sm font-semibold text-[var(--color-text-primary)] cursor-help">Open Positions</h3>
        </Tooltip>
        {!loading && (
          <span className="ml-auto text-xs font-mono text-[var(--color-text-secondary)]">
            {openPositions.length} open
          </span>
        )}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-[var(--color-bg-elevated)]">
              <th className="px-3 sm:px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-[var(--color-text-secondary)]">
                Symbol
              </th>
              <th className="px-3 sm:px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-[var(--color-text-secondary)]">
                Dir
              </th>
              <th className="px-3 sm:px-4 py-2.5 text-right text-xs font-semibold uppercase tracking-wider text-[var(--color-text-secondary)] hidden sm:table-cell">
                Entry
              </th>
              <th className="px-3 sm:px-4 py-2.5 text-right text-xs font-semibold uppercase tracking-wider text-[var(--color-text-secondary)] hidden md:table-cell">
                Qty
              </th>
              <th className="px-3 sm:px-4 py-2.5 text-right text-xs font-semibold uppercase tracking-wider text-[var(--color-text-secondary)] hidden lg:table-cell">
                SL
              </th>
              <th className="px-3 sm:px-4 py-2.5 text-right text-xs font-semibold uppercase tracking-wider text-[var(--color-text-secondary)] hidden lg:table-cell">
                TP
              </th>
              <th className="px-3 sm:px-4 py-2.5 text-right text-xs font-semibold uppercase tracking-wider text-[var(--color-text-secondary)]">
                P&L
              </th>
              <th className="px-3 sm:px-4 py-2.5 text-center text-xs font-semibold uppercase tracking-wider text-[var(--color-text-secondary)]">
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--color-border)]">
            {loading ? (
              Array.from({ length: 3 }, (_, i) => <SkeletonRow key={i} />)
            ) : openPositions.length === 0 ? (
              <tr>
                <td
                  colSpan={8}
                  className="px-3 sm:px-4 py-8 text-center text-sm text-[var(--color-text-secondary)]"
                >
                  No open positions
                </td>
              </tr>
            ) : (
              openPositions.map((pos) => {
                const pnl = pos.unrealized_pnl ?? 0;
                const pnlColor =
                  pnl >= 0
                    ? "text-[var(--color-positive)]"
                    : "text-[var(--color-negative)]";
                const isLong = pos.direction.toUpperCase() === "LONG";
                const dirColor = isLong
                  ? "text-[var(--color-positive)]"
                  : "text-[var(--color-negative)]";

                return (
                  <tr
                    key={pos.id}
                    className="hover:bg-[var(--color-bg-elevated)]/30 transition-colors"
                  >
                    <td className="px-3 sm:px-4 py-3 font-semibold text-[var(--color-text-primary)] text-xs sm:text-sm">
                      {pos.symbol}
                    </td>
                    <td className={`px-3 sm:px-4 py-3 font-medium text-xs sm:text-sm ${dirColor}`}>
                      {pos.direction.toUpperCase()}
                    </td>
                    <td className="px-3 sm:px-4 py-3 text-right font-mono text-[var(--color-text-primary)] hidden sm:table-cell">
                      {formatPrice(pos.entry_price)}
                    </td>
                    <td className="px-3 sm:px-4 py-3 text-right font-mono text-[var(--color-text-primary)] hidden md:table-cell">
                      {pos.quantity}
                    </td>
                    <td className="px-3 sm:px-4 py-3 text-right font-mono text-[var(--color-text-secondary)] hidden lg:table-cell">
                      {pos.stop_loss != null ? formatPrice(pos.stop_loss) : "--"}
                    </td>
                    <td className="px-3 sm:px-4 py-3 text-right font-mono text-[var(--color-text-secondary)] hidden lg:table-cell">
                      {pos.take_profit != null ? formatPrice(pos.take_profit) : "--"}
                    </td>
                    <td
                      className={`px-3 sm:px-4 py-3 text-right font-mono font-semibold text-xs sm:text-sm ${pnlColor}`}
                    >
                      {pnl >= 0 ? "+" : ""}${pnl.toFixed(2)}
                    </td>
                    <td className="px-3 sm:px-4 py-3 text-center">
                      <CloseButton position={pos} />
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
