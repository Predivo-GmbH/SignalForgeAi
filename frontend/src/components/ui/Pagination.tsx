import { ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "@/lib/cn";

interface PaginationProps {
  total: number;
  limit: number;
  offset: number;
  onChange: (offset: number) => void;
}

export function Pagination({ total, limit, offset, onChange }: PaginationProps) {
  const isFirst = offset === 0;
  const isLast = offset + limit >= total;
  const from = total === 0 ? 0 : offset + 1;
  const to = Math.min(offset + limit, total);

  return (
    <div className="flex items-center justify-between px-1 py-3">
      <span className="text-sm text-[var(--color-text-secondary)]">
        Showing{" "}
        <span className="font-mono font-medium text-[var(--color-text-primary)]">
          {from}
        </span>
        {" - "}
        <span className="font-mono font-medium text-[var(--color-text-primary)]">
          {to}
        </span>
        {" of "}
        <span className="font-mono font-medium text-[var(--color-text-primary)]">
          {total}
        </span>
      </span>
      <div className="flex gap-2">
        <button
          onClick={() => onChange(Math.max(0, offset - limit))}
          disabled={isFirst}
          className={cn(
            "inline-flex items-center gap-1 rounded-lg border border-[var(--color-border)] px-3 py-1.5 text-sm font-medium transition-colors",
            isFirst
              ? "opacity-40 cursor-not-allowed"
              : "hover:bg-[var(--color-bg-elevated)] text-[var(--color-text-primary)]",
          )}
        >
          <ChevronLeft className="h-4 w-4" />
          Previous
        </button>
        <button
          onClick={() => onChange(offset + limit)}
          disabled={isLast}
          className={cn(
            "inline-flex items-center gap-1 rounded-lg border border-[var(--color-border)] px-3 py-1.5 text-sm font-medium transition-colors",
            isLast
              ? "opacity-40 cursor-not-allowed"
              : "hover:bg-[var(--color-bg-elevated)] text-[var(--color-text-primary)]",
          )}
        >
          Next
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
