import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";
import { invokeFunction } from "@/lib/api";

export interface Trade {
  id: string;
  signal_id: string | null;
  user_id: string;
  symbol: string;
  direction: string;
  entry_price: number;
  exit_price: number | null;
  position_size: number;
  stop_loss: number;
  take_profit: number;
  pnl: number | null;
  pnl_pct: number | null;
  risk_reward: number | null;
  confluence_score: number;
  entry_time: string | null;
  exit_time: string | null;
  exit_reason: string | null;
  broker_order_id: string | null;
  metadata_json: Record<string, unknown> | null;
  created_at: string;
  // Signal reasoning (joined from signals table)
  regime: string | null;
  triggers: string[] | null;
  ai_quality_score: number | null;
  ai_recommendation: string | null;
  ai_reasoning: string | null;
}

export interface TradeStats {
  total_trades: number;
  win_rate: number;
  profit_factor: number;
  total_pnl: number;
  avg_pnl: number;
  best_trade: number;
  worst_trade: number;
}

export function useTrades(limit = 20, offset = 0, strategyId?: string) {
  return useQuery({
    queryKey: ["trades", limit, offset, strategyId],
    queryFn: async () => {
      let query = supabase
        .from("trades")
        .select("*", { count: "exact" })
        .order("created_at", { ascending: false })
        .range(offset, offset + limit - 1);

      if (strategyId) query = query.eq("strategy_id", strategyId);

      const { data, error, count } = await query;
      if (error) throw error;
      return {
        trades: (data ?? []) as Trade[],
        total: count ?? 0,
      };
    },
    refetchInterval: 60_000,
  });
}

export function useTradeStats(strategyId?: string) {
  return useQuery({
    queryKey: ["trades", "stats", strategyId],
    queryFn: () =>
      invokeFunction<TradeStats>("analytics", {
        action: "trade-stats",
        strategy_id: strategyId,
      }),
    refetchInterval: 60_000,
  });
}
