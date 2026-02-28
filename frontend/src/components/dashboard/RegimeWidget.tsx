import { Cpu, Circle } from "lucide-react";
import { useEngineStatus } from "@/hooks/useEngineStatus";

export function RegimeWidget() {
  const { data, isLoading } = useEngineStatus();

  if (isLoading) {
    return (
      <div className="bg-[var(--color-bg-surface)] rounded-xl border border-[var(--color-border)] p-4">
        <div className="flex items-center gap-2 mb-3">
          <div className="h-4 w-4 rounded bg-[var(--color-bg-elevated)] animate-pulse" />
          <div className="h-4 w-24 rounded bg-[var(--color-bg-elevated)] animate-pulse" />
        </div>
        <div className="space-y-2">
          <div className="h-3 w-32 rounded bg-[var(--color-bg-elevated)] animate-pulse" />
          <div className="flex gap-1.5">
            {Array.from({ length: 3 }, (_, i) => (
              <div
                key={i}
                className="h-5 w-16 rounded-full bg-[var(--color-bg-elevated)] animate-pulse"
              />
            ))}
          </div>
        </div>
      </div>
    );
  }

  const isActive = data?.active ?? false;

  return (
    <div className="bg-[var(--color-bg-surface)] rounded-xl border border-[var(--color-border)] p-4">
      <div className="flex items-center gap-2 mb-4">
        <Cpu className="h-4 w-4 text-[var(--color-accent)]" />
        <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">
          Engine Status
        </h3>
      </div>

      <div className="flex items-center gap-2 mb-4">
        <Circle
          className={`h-2.5 w-2.5 fill-current ${
            isActive
              ? "text-[var(--color-positive)]"
              : "text-[var(--color-negative)]"
          }`}
        />
        <span className="text-sm font-medium text-[var(--color-text-primary)]">
          {isActive ? "Engine Active" : "Engine Inactive"}
        </span>
      </div>

      {data?.layers && data.layers.length > 0 && (
        <div>
          <span className="text-xs text-[var(--color-text-secondary)] uppercase tracking-wider font-semibold">
            Layers
          </span>
          <div className="flex flex-wrap gap-1.5 mt-2">
            {data.layers.map((layer) => (
              <span
                key={layer}
                className="inline-flex items-center rounded-full bg-[var(--color-bg-elevated)] px-2.5 py-0.5 text-xs font-medium text-[var(--color-text-secondary)]"
              >
                {layer}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
