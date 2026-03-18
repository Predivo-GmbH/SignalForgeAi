import { useMutation } from "@tanstack/react-query";
import { invokeFunction } from "@/lib/api";

interface WFORequest {
  symbol: string;
  timeframe: string;
  days: number;
  n_folds: number;
  train_pct: number;
  param_grid: Record<string, number[]>;
}

interface WFOResult {
  best_params: Record<string, number>;
  out_of_sample_metrics: Record<string, number | null>;
  fold_results: Array<{
    fold: number;
    params: Record<string, number>;
    oos_metrics: Record<string, number | null>;
    oos_score: number;
  }>;
}

export type { WFORequest, WFOResult };

export function useRunWalkForward() {
  return useMutation({
    mutationFn: (req: WFORequest) =>
      invokeFunction<WFOResult>("backtests", {
        action: "walk-forward",
        ...req,
      }),
  });
}
