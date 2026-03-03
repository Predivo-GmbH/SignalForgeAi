import { Briefcase } from "lucide-react";
import { formatPrice } from "@/lib/format";
import type { Position } from "@/hooks/usePositions";

interface PositionsTableProps {
  positions: Position[] | undefined;
  loading?: boolean;
}



function SkeletonRow() {
  return (
    <tr>
      {Array.from({ length: 7 }, (_, i) => (
        <td key={i} className="px-4 py-3">
          <div className="h-4 rounded bg-[var(--color-bg-elevated)] animate-pulse" />
        </td>
      ))}
    </tr>
  );
}

export function PositionsTable({ positions, loading }: PositionsTableProps) {
  const openPositions = positions?.filter((p) => p.is_open) ?? [];

  return (
    <div className="bg-[var(--color-bg-surface)] rounded-xl border border-[var(--color-border)] overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-[var(--color-border)]">
        <Briefcase className="h-4 w-4 text-[var(--color-accent)]" />
        <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">
          Open Positions
        </h3>
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
              <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-[var(--color-text-secondary)]">
                Symbol
              </th>
              <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-[var(--color-text-secondary)]">
                Dir
              </th>
              <th className="px-4 py-2.5 text-right text-xs font-semibold uppercase tracking-wider text-[var(--color-text-secondary)]">
                Entry
              </th>
              <th className="px-4 py-2.5 text-right text-xs font-semibold uppercase tracking-wider text-[var(--color-text-secondary)]">
                Qty
              </th>
              <th className="px-4 py-2.5 text-right text-xs font-semibold uppercase tracking-wider text-[var(--color-text-secondary)]">
                SL
              </th>
              <th className="px-4 py-2.5 text-right text-xs font-semibold uppercase tracking-wider text-[var(--color-text-secondary)]">
                TP
              </th>
              <th className="px-4 py-2.5 text-right text-xs font-semibold uppercase tracking-wider text-[var(--color-text-secondary)]">
                P&L
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--color-border)]">
            {loading ? (
              Array.from({ length: 3 }, (_, i) => <SkeletonRow key={i} />)
            ) : openPositions.length === 0 ? (
              <tr>
                <td
                  colSpan={7}
                  className="px-4 py-8 text-center text-sm text-[var(--color-text-secondary)]"
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
                    <td className="px-4 py-3 font-semibold text-[var(--color-text-primary)]">
                      {pos.symbol}
                    </td>
                    <td className={`px-4 py-3 font-medium ${dirColor}`}>
                      {pos.direction.toUpperCase()}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-[var(--color-text-primary)]">
                      {formatPrice(pos.entry_price)}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-[var(--color-text-primary)]">
                      {pos.quantity}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-[var(--color-text-secondary)]">
                      {formatPrice(pos.stop_loss)}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-[var(--color-text-secondary)]">
                      {formatPrice(pos.take_profit)}
                    </td>
                    <td
                      className={`px-4 py-3 text-right font-mono font-semibold ${pnlColor}`}
                    >
                      {pnl >= 0 ? "+" : ""}${pnl.toFixed(2)}
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
