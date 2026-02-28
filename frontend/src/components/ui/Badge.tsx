import { cn } from "@/lib/cn";
import type { ReactNode } from "react";

type BadgeVariant = "success" | "danger" | "warning" | "info" | "neutral";

interface BadgeProps {
  variant?: BadgeVariant;
  children: ReactNode;
  className?: string;
}

const variantStyles: Record<BadgeVariant, string> = {
  success:
    "bg-[var(--color-positive)]/15 text-[var(--color-positive)]",
  danger:
    "bg-[var(--color-negative)]/15 text-[var(--color-negative)]",
  warning:
    "bg-[var(--color-warning)]/15 text-[var(--color-warning)]",
  info: "bg-[var(--color-accent)]/15 text-[var(--color-accent)]",
  neutral:
    "bg-[var(--color-bg-elevated)] text-[var(--color-text-secondary)]",
};

export function Badge({
  variant = "neutral",
  children,
  className,
}: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        variantStyles[variant],
        className,
      )}
    >
      {children}
    </span>
  );
}
