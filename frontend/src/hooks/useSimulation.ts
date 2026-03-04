import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface SimulationHolding {
  symbol: string;
  quantity: number;
  price_usd: number;
  value_usd: number;
}

export interface SimulationSnapshot {
  timestamp: string;
  bh_value_usd: number;
  sf_value_usd: number;
}

export interface SimulationData {
  id: string;
  status: "running" | "stopped";
  strategy_id: string | null;
  started_at: string;
  stopped_at: string | null;
  initial_value_usd: number;
  initial_holdings: SimulationHolding[];
  snapshots: SimulationSnapshot[];
  latest_bh_value: number;
  latest_sf_value: number;
  bh_return_pct: number;
  sf_return_pct: number;
  sf_trades: number;
  sf_win_rate: number;
  sf_open_positions: number;
}

export function useSimulation() {
  return useQuery({
    queryKey: ["simulation", "active"],
    queryFn: () => api.get<SimulationData | null>("/simulation/active"),
    refetchInterval: 60_000,
  });
}

export function useLatestSimulation() {
  return useQuery({
    queryKey: ["simulation", "latest"],
    queryFn: () => api.get<SimulationData | null>("/simulation/latest"),
  });
}

export function useStartSimulation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<{ id: string }>("/simulation/start"),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["simulation"] });
    },
  });
}

export function useStopSimulation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (simId: string) =>
      api.post<SimulationData>(`/simulation/${simId}/stop`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["simulation"] });
    },
  });
}
