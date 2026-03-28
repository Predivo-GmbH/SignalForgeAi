import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

export interface Column<T> {
  key: string;
  header: string;
  render?: (row: T) => ReactNode;
  align?: "left" | "center" | "right";
}

interface DataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  onRowClick?: (row: T) => void;
  loading?: boolean;
  emptyMessage?: string;
}

function SkeletonRow({ cols }: { cols: number }) {
  return (
    <tr>
      {Array.from({ length: cols }, (_, i) => (
        <td key={i} className="px-2 sm:px-4 py-2 sm:py-3">
          <div className="h-4 rounded bg-[var(--color-bg-elevated)] animate-pulse" />
        </td>
      ))}
    </tr>
  );
}

export function DataTable<T extends Record<string, unknown>>({
  data,
  columns,
  onRowClick,
  loading = false,
  emptyMessage = "No data available",
}: DataTableProps<T>) {
  const alignClass = (align?: "left" | "center" | "right") => {
    if (align === "center") return "text-center";
    if (align === "right") return "text-right";
    return "text-left";
  };

  return (
    <div className="bg-[var(--color-bg-surface)] rounded-xl border border-[var(--color-border)] overflow-hidden">
      <div className="relative">
      <div className="overflow-x-auto">

        <table className="w-full text-sm">
          <thead>
            <tr className="bg-[var(--color-bg-elevated)]">
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={cn(
                    "px-2 sm:px-4 py-2 sm:py-3 text-xs font-semibold uppercase tracking-wider text-[var(--color-text-secondary)]",
                    alignClass(col.align),
                  )}
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--color-border)]">
            {loading ? (
              Array.from({ length: 5 }, (_, i) => (
                <SkeletonRow key={i} cols={columns.length} />
              ))
            ) : data.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length}
                  className="px-4 py-12 text-center text-[var(--color-text-secondary)]"
                >
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              data.map((row, idx) => (
                <tr
                  key={(row.id as string) ?? idx}
                  onClick={() => onRowClick?.(row)}
                  className={cn(
                    "transition-colors",
                    onRowClick
                      ? "cursor-pointer hover:bg-[var(--color-bg-elevated)]/50"
                      : "",
                  )}
                >
                  {columns.map((col) => (
                    <td
                      key={col.key}
                      className={cn(
                        "px-2 sm:px-4 py-2 sm:py-3 text-[var(--color-text-primary)]",
                        alignClass(col.align),
                      )}
                    >
                      {col.render
                        ? col.render(row)
                        : String(row[col.key] ?? "")}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      <div className="pointer-events-none absolute right-0 top-0 h-full w-6 bg-gradient-to-l from-[var(--color-bg-surface)] to-transparent sm:hidden" />
      </div>
    </div>
  );
}
