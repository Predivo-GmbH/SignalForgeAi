import { useCallback, useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
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
    last_pipeline_run_at: string | null;
    pipeline_age_seconds: number | null;
    last_signal_at: string | null;
    signal_age_seconds: number | null;
  };
  issues: string[];
}

/**
 * System status query with support for rapid polling after a restart.
 * Normal interval: 30s.  During restart monitoring: 3s for up to 30s.
 */
export function useSystemStatus() {
  const [rapidPoll, setRapidPoll] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const query = useQuery({
    queryKey: ["system", "status"],
    queryFn: () => api.get<SystemStatus>("/system/status"),
    refetchInterval: rapidPoll ? 3_000 : 30_000,
  });

  const startRapidPoll = useCallback(() => {
    setRapidPoll(true);
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => setRapidPoll(false), 30_000);
  }, []);

  useEffect(() => () => clearTimeout(timerRef.current), []);

  return { ...query, rapidPoll, startRapidPoll };
}

export type RestartPhase = "idle" | "requesting" | "restarting" | "recovered" | "failed";

export function useRestartWorker() {
  const qc = useQueryClient();
  const [phase, setPhase] = useState<RestartPhase>("idle");
  const [statusBefore, setStatusBefore] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const mutation = useMutation({
    mutationFn: () => api.post<{ status: string; detail: string }>("/system/restart"),
    onMutate: () => {
      setPhase("requesting");
    },
    onSuccess: () => {
      setPhase("restarting");
      qc.invalidateQueries({ queryKey: ["system", "status"] });
      // Auto-reset to idle after 30s if we don't detect recovery
      clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => setPhase("idle"), 30_000);
    },
    onError: () => {
      setPhase("failed");
      clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => setPhase("idle"), 5_000);
    },
  });

  const markRecovered = useCallback(() => {
    setPhase("recovered");
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => setPhase("idle"), 5_000);
  }, []);

  useEffect(() => () => clearTimeout(timerRef.current), []);

  return {
    mutate: mutation.mutate,
    phase,
    setStatusBefore,
    statusBefore,
    markRecovered,
    isPending: mutation.isPending,
  };
}
