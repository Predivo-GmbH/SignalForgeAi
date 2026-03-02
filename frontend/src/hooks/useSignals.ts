import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface Signal {
  id: string;
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
}

interface SignalListResponse {
  signals: Signal[];
  total: number;
  limit: number;
  offset: number;
}

export function useSignals(limit = 20, offset = 0) {
  return useQuery({
    queryKey: ["signals", limit, offset],
    queryFn: () =>
      api.get<SignalListResponse>(
        `/signals?limit=${limit}&offset=${offset}`,
      ),
  });
}
