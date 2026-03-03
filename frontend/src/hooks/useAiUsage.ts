import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface UsageSummary {
  total_cost_usd: number;
  total_calls: number;
  avg_cost_per_call: number;
  avg_latency_ms: number;
}

export interface ModelBreakdown {
  model: string;
  calls: number;
  cost_usd: number;
  avg_latency_ms: number;
}

export interface TypeBreakdown {
  insight_type: string;
  calls: number;
  cost_usd: number;
}

export interface DailyCost {
  date: string;
  cost_usd: number;
  calls: number;
}

export interface RecentCall {
  id: string;
  created_at: string;
  insight_type: string;
  model_used: string;
  cost_usd: number;
  latency_ms: number;
  input_tokens: number;
  output_tokens: number;
}

export interface CreditInfo {
  prepaid_usd: number;
  spent_usd: number;
  remaining_usd: number;
}

export interface AiUsageResponse {
  source: "anthropic_api" | "local";
  summary: UsageSummary;
  by_model: ModelBreakdown[];
  by_type: TypeBreakdown[];
  daily_costs: DailyCost[];
  recent_calls: RecentCall[];
  credit: CreditInfo;
}

export function useAiUsage(days = 30) {
  return useQuery({
    queryKey: ["ai-usage", days],
    queryFn: () => api.get<AiUsageResponse>(`/ai-usage?days=${days}`),
    staleTime: 60_000,
    refetchInterval: 60_000,
  });
}

export function useUpdateCredit() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (prepaid_usd: number) =>
      api.put<{ prepaid_usd: number }>("/ai-usage/credit", { prepaid_usd }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ai-usage"] }),
  });
}
