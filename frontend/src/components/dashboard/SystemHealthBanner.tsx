import { AlertTriangle, CheckCircle2, XCircle } from "lucide-react";
import { useSystemStatus, type SystemStatus } from "@/hooks/useSystemStatus";

const STATUS_CONFIG: Record<
  SystemStatus["overall"],
  { icon: typeof CheckCircle2; label: string; bg: string; border: string; text: string }
> = {
  healthy: {
    icon: CheckCircle2,
    label: "All Systems Operational",
    bg: "var(--color-positive)",
    border: "var(--color-positive)",
    text: "var(--color-positive)",
  },
  degraded: {
    icon: AlertTriangle,
    label: "System Degraded",
    bg: "var(--color-warning)",
    border: "var(--color-warning)",
    text: "var(--color-warning)",
  },
  critical: {
    icon: XCircle,
    label: "System Down",
    bg: "var(--color-negative)",
    border: "var(--color-negative)",
    text: "var(--color-negative)",
  },
};

export function SystemHealthBanner() {
  const { data, isLoading, isError } = useSystemStatus();

  // Don't show anything while loading
  if (isLoading) return null;

  // Network error reaching the API itself
  if (isError || !data) {
    return (
      <div
        className="flex items-center gap-2 sm:gap-3 rounded-lg px-3 sm:px-4 py-2.5 sm:py-3 border"
        role="alert"
        style={{
          backgroundColor: "color-mix(in srgb, var(--color-negative) 8%, transparent)",
          borderColor: "color-mix(in srgb, var(--color-negative) 30%, transparent)",
        }}
      >
        <XCircle className="h-4 w-4 shrink-0" aria-hidden="true" style={{ color: "var(--color-negative)" }} />
        <span className="text-xs sm:text-sm font-medium" style={{ color: "var(--color-negative)" }}>
          Cannot reach API server
        </span>
      </div>
    );
  }

  // Everything healthy — show a minimal green indicator
  if (data.overall === "healthy") {
    return null;
  }

  const config = STATUS_CONFIG[data.overall];
  const Icon = config.icon;

  return (
    <div
      className="flex items-start gap-2 sm:gap-3 rounded-lg px-3 sm:px-4 py-2.5 sm:py-3 border"
      role="alert"
      style={{
        backgroundColor: `color-mix(in srgb, ${config.bg} 8%, transparent)`,
        borderColor: `color-mix(in srgb, ${config.border} 30%, transparent)`,
      }}
    >
      <Icon className="h-4 w-4 shrink-0 mt-0.5" aria-hidden="true" style={{ color: config.text }} />
      <div className="flex-1 min-w-0">
        <span className="text-sm font-semibold" style={{ color: config.text }}>
          {config.label}
        </span>
        {data.issues.length > 0 && (
          <ul className="mt-1 space-y-0.5">
            {data.issues.map((issue, i) => (
              <li key={i} className="text-xs text-[var(--color-text-secondary)]">
                {issue}
              </li>
            ))}
          </ul>
        )}
        <ServiceDots services={data.services} />
      </div>
    </div>
  );
}

function ServiceDots({ services }: { services: SystemStatus["services"] }) {
  const items = [
    { label: "DB", status: services.database.status },
    { label: "Redis", status: services.redis.status },
    { label: "Worker", status: services.worker.status },
    { label: "Beat", status: services.beat.status },
  ];

  return (
    <div className="flex items-center gap-3 mt-2">
      {items.map((svc) => (
        <div key={svc.label} className="flex items-center gap-1.5">
          <div
            className="h-2 w-2 rounded-full"
            style={{
              backgroundColor:
                svc.status === "ok"
                  ? "var(--color-positive)"
                  : svc.status === "stale"
                    ? "var(--color-warning)"
                    : "var(--color-negative)",
            }}
          />
          <span className="text-xs text-[var(--color-text-secondary)]">{svc.label}</span>
        </div>
      ))}
    </div>
  );
}
