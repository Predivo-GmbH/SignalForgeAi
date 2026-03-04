import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface RegimeStatus {
  regime_allocator_enabled: boolean;
  current_regime: string;
  regime_probabilities: Record<string, number>;
  target_allocation_pct: number;
  current_allocation_pct: number;
  allocation_table: string;
  smoothing_bars: number;
  cooldown_hours: number;
}

export function useRegimeStatus() {
  return useQuery({
    queryKey: ["regime", "status"],
    queryFn: () => api.get<RegimeStatus>("/regime/status"),
    refetchInterval: 30_000,
  });
}
