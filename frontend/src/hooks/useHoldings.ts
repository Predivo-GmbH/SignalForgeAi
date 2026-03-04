import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface HoldingItem {
  id?: string;
  symbol: string;
  quantity: number;
  avg_price: number | null;
  current_price: number | null;
  value_usd: number | null;
  change_24h_pct: number | null;
  allocation_pct: number | null;
  source: string;
  notes: string | null;
  market_cap: number | null;
  market_cap_rank: number | null;
  volume_24h: number | null;
  image_url: string | null;
}

export interface HoldingsResponse {
  holdings: HoldingItem[];
  total_value_usd: number | null;
}

export interface ManualHoldingRequest {
  symbol: string;
  quantity: number;
  purchase_price?: number | null;
  notes?: string | null;
}

export function useHoldings() {
  return useQuery({
    queryKey: ["holdings"],
    queryFn: () => api.get<HoldingsResponse>("/holdings"),
    refetchInterval: 60_000,
  });
}

export function useAddHolding() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ManualHoldingRequest) =>
      api.post("/holdings/manual", data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["holdings"] }),
  });
}

export function useUpdateHolding() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...data }: ManualHoldingRequest & { id: string }) =>
      api.put(`/holdings/manual/${id}`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["holdings"] }),
  });
}

export function useDeleteHolding() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete(`/holdings/manual/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["holdings"] }),
  });
}
