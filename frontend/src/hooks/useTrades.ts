import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

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
    queryFn: () => {
      let url = `/trades?limit=${limit}&offset=${offset}`;
      if (strategyId) url += `&strategy_id=${strategyId}`;
      return api.get<{ trades: Trade[]; total: number }>(url);
    },
  });
}

export function useTradeStats(strategyId?: string) {
  return useQuery({
    queryKey: ["trades", "stats", strategyId],
    queryFn: () => {
      let url = "/trades/stats";
      if (strategyId) url += `?strategy_id=${strategyId}`;
      return api.get<TradeStats>(url);
    },
  });
}
