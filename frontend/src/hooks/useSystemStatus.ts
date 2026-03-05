import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface ServiceStatus {
  status: "ok" | "down" | "error" | "stale" | "unknown";
  detail?: string;
  last_candle_age_s?: number;
}

export interface SystemStatus {
  overall: "healthy" | "degraded" | "critical";
  checked_at: string;
  services: {
    database: ServiceStatus;
    redis: ServiceStatus;
    worker: ServiceStatus;
    beat: ServiceStatus;
  };
  data: {
    candles_fresh: boolean;
    last_candle_at: string | null;
    candle_age_seconds: number | null;
    pipeline_fresh: boolean;
    last_signal_at: string | null;
    signal_age_seconds: number | null;
  };
  issues: string[];
}

export function useSystemStatus() {
  return useQuery({
    queryKey: ["system", "status"],
    queryFn: () => api.get<SystemStatus>("/system/status"),
    refetchInterval: 30_000,
  });
}
