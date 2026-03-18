import { useMutation } from "@tanstack/react-query";
import { invokeFunction } from "@/lib/api";

export interface StrategyBacktestRequest {
  strategy_id?: string;
  plan?: Record<string, unknown>;
  days: number;
  ai_enhanced?: boolean;
}

export interface SymbolResult {
  symbol: string;
  total_return: number;
  win_rate: number;
  profit_factor: number;
  max_drawdown: number;
  total_trades: number;
  sharpe_ratio: number | null;
  sortino_ratio: number | null;
}

export interface StrategyBacktestResult {
  strategy_name: string;
  preset: string;
  symbols_count: number;
  days: number;
  ai_enhanced?: boolean;
  config_summary: {
    min_confluence: number;
    max_risk_per_trade: number;
    atr_sl_multiplier: number;
    timeframes: string[];
    account_equity: number;
  };
  portfolio: {
    total_return: number;
    win_rate: number;
    profit_factor: number;
    max_drawdown: number;
    total_trades: number;
    sharpe_ratio: number | null;
    sortino_ratio: number | null;
    equity_curve: { time: string; value: number }[];
    ai_calls?: number;
    ai_rejections?: number;
  };
  per_symbol: SymbolResult[];
}

export function useRunStrategyBacktest() {
  return useMutation({
    mutationFn: (req: StrategyBacktestRequest) =>
      invokeFunction<StrategyBacktestResult>("backtests", {
        action: "run",
        ...req,
      }),
  });
}
