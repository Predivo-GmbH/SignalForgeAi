/** Return a Tailwind text color class based on PnL value. */
export function pnlColor(val: number | null | undefined): string {
  if (val == null) return "text-(--color-text-secondary)";
  if (val > 0) return "text-(--color-positive)";
  if (val < 0) return "text-(--color-negative)";
  return "text-(--color-text-secondary)";
}

/** Format a price with appropriate decimal precision (for crypto). */
export function formatPrice(val: number): string {
  if (val >= 1000) return `$${val.toFixed(2)}`;
  if (val >= 1) return `$${val.toFixed(4)}`;
  return `$${val.toFixed(6)}`;
}

/** Format a USD value with 2 decimal places and thousand separators. */
export function fmtUsd(val: number | null | undefined): string {
  if (val == null) return "--";
  return `$${val.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

/** Format a date string as short date (e.g. "Mar 5, 2026"). */
export function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

/** Format a date/time string as short date + time (e.g. "Mar 5, 14:30"). */
export function formatTime(dateStr: string | null | undefined): string {
  if (!dateStr) return "--";
  return new Date(dateStr).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

/** Format P&L as signed dollar amount (e.g. "+$1,234.56" or "-$50.00"). */
export function formatPnl(value: number | null | undefined): string {
  if (value == null) return "--";
  const prefix = value >= 0 ? "+$" : "-$";
  return `${prefix}${Math.abs(value).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

/** Format P&L as signed percentage (e.g. "+1.23%" or "-0.50%"). */
export function formatPnlPercent(value: number | null | undefined): string {
  if (value == null) return "--";
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
}
