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
    queryFn: () => {
      const p = new URLSearchParams();
      p.set("limit", String(limit));
      p.set("offset", String(offset));
      if (strategyId) p.set("strategy_id", strategyId);
      if (symbol) p.set("symbol", symbol);
      if (direction) p.set("direction", direction);
      if (status) p.set("status", status);
      if (sortBy) p.set("sort_by", sortBy);
      if (sortDir) p.set("sort_dir", sortDir);
      return api.get<SignalListResponse>(`/signals?${p.toString()}`);
    },
    refetchInterval: 30_000,
  });
}
