/** Return a Tailwind text color class based on PnL value. */
export function pnlColor(val: number | null | undefined): string {
  if (val == null) return "text-(--color-text-secondary)";
  if (val > 0) return "text-(--color-positive)";
  if (val < 0) return "text-(--color-negative)";
  return "text-(--color-text-secondary)";
}

/** Format a price with appropriate decimal precision. */
export function formatPrice(val: number): string {
  if (val >= 1000) return `$${val.toFixed(2)}`;
  if (val >= 1) return `$${val.toFixed(4)}`;
  return `$${val.toFixed(6)}`;
}
