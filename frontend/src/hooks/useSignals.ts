import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";

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
  triggers: string[] | null;
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

export interface SignalQueryParams {
  limit?: number;
  offset?: number;
  strategyId?: string;
  symbol?: string;
  direction?: string;
  status?: string;
  sortBy?: string;
  sortDir?: "asc" | "desc";
}

export function useSignals(params: SignalQueryParams = {}) {
  const {
    limit = 20,
    offset = 0,
    strategyId,
    symbol,
    direction,
    status,
    sortBy,
    sortDir,
  } = params;

  return useQuery({
    queryKey: ["signals", limit, offset, strategyId, symbol, direction, status, sortBy, sortDir],
    queryFn: async () => {
      let query = supabase
        .from("signals")
        .select("*", { count: "exact" })
        .range(offset, offset + limit - 1);

      if (strategyId) query = query.eq("strategy_id", strategyId);
      if (symbol) query = query.eq("symbol", symbol);
      if (direction) query = query.eq("direction", direction);
      if (status) query = query.eq("status", status);

      if (sortBy) {
        query = query.order(sortBy, { ascending: sortDir === "asc" });
      } else {
        query = query.order("created_at", { ascending: false });
      }

      const { data, error, count } = await query;
      if (error) throw error;
      return {
        signals: (data ?? []) as Signal[],
        total: count ?? 0,
        limit,
        offset,
      } as SignalListResponse;
    },
    refetchInterval: 30_000,
  });
}
