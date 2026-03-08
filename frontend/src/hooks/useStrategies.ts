import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface Strategy {
  id: string;
  user_id: string;
  name: string;
  is_active: boolean;
  config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface StrategyPreset {
  name: string;
  description: string;
  config: Record<string, unknown>;
}

export interface PresetsResponse {
  presets: Record<string, StrategyPreset>;
}

export function useStrategies() {
  return useQuery({
    queryKey: ["strategies"],
    queryFn: () =>
      api.get<{ strategies: Strategy[]; total: number }>("/strategies"),
  });
}

export function useStrategy(id: string) {
  return useQuery({
    queryKey: ["strategies", id],
    queryFn: () => api.get<Strategy>(`/strategies/${id}`),
    enabled: !!id,
  });
}

export function useStrategyPresets() {
  return useQuery({
    queryKey: ["strategy-presets"],
    queryFn: () => api.get<PresetsResponse>("/strategies/presets"),
    staleTime: 5 * 60 * 1000,
  });
}

export function useCreateStrategy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { name: string; config?: Record<string, unknown>; preset?: string }) =>
      api.post<Strategy>("/strategies", data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["strategies"] }),
  });
}

export function useUpdateStrategy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      ...data
    }: {
      id: string;
      name?: string;
      config?: Record<string, unknown>;
    }) => api.put<Strategy>(`/strategies/${id}`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["strategies"] }),
  });
}

export function useToggleStrategy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, totp_code }: { id: string; totp_code?: string }) =>
      api.post<Strategy>(`/strategies/${id}/activate`, totp_code ? { totp_code } : {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["strategies"] }),
  });
}

export function useDeleteStrategy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete(`/strategies/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["strategies"] }),
  });
}

export interface ExchangeAvailability {
  availability: Record<string, string[]>;
  unavailable: string[];
}

export function useExchangeAvailability(symbols: string[]) {
  const joined = symbols.join(",");
  return useQuery({
    queryKey: ["exchange-availability", joined],
    queryFn: () =>
      api.get<ExchangeAvailability>(
        `/strategies/exchange-availability?symbols=${encodeURIComponent(joined)}`,
      ),
    enabled: symbols.length > 0,
    staleTime: 60 * 60 * 1000, // 1 hour — markets don't change often
  });
}
