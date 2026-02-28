import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface BacktestRequest {
  symbol: string;
  timeframe: string;
  days: number;
  params?: Record<string, unknown>;
}

export interface BacktestResult {
  total_return: number;
  win_rate: number;
  profit_factor: number;
  max_drawdown: number;
  total_trades: number;
  sharpe_ratio?: number;
  equity_curve?: { time: string; value: number }[];
  [key: string]: unknown;
}

export function useRunBacktest() {
  return useMutation({
    mutationFn: (req: BacktestRequest) =>
      api.post<BacktestResult>("/backtests", req),
  });
}

export function useBacktests() {
  return useQuery({
    queryKey: ["backtests"],
    queryFn: () => api.get<BacktestResult[]>("/backtests"),
  });
}
