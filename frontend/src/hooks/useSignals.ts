import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface Signal {
  id: string;
  strategy_id: string | null;
  symbol: string;
  timeframe: string;
  direction: string;
  entry_price: number;
  stop_loss: number;
  take_profit_1: number;
  take_profit_2: number | null;
  confluence_score: number;
  regime: string;
  triggers: Record<string, unknown> | null;
  position_size: number | null;
  status: string;
  created_at: string;
  ai_quality_score: number | null;
  ai_reasoning: string | null;
  ai_recommendation: string | null;
  mtf_confidence: number | null;
  mtf_alignment: string | null;
}

interface SignalListResponse {
  signals: Signal[];
  total: number;
  limit: number;
  offset: number;
}

export function useSignals(limit = 20, offset = 0, strategyId?: string) {
  return useQuery({
    queryKey: ["signals", limit, offset, strategyId],
    queryFn: () => {
      let url = `/signals?limit=${limit}&offset=${offset}`;
      if (strategyId) url += `&strategy_id=${strategyId}`;
      return api.get<SignalListResponse>(url);
    },
    refetchInterval: 30_000,
  });
}
