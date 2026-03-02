import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface ScoredCrypto {
  symbol: string;
  score: number;
  regime: string;
  trend_direction: string;
  trend_strength: number;
  rsi: number;
  adx: number;
  atr_pct: number;
  macd_histogram: number;
  volume_rank: number;
  price: number;
  volume_24h: number;
  change_pct_24h: number;
  recommendation: string;
}

export interface ScanResponse {
  pairs_scanned: number;
  pairs_scored: number;
  results: ScoredCrypto[];
}

export interface InvestmentPlan {
  summary: string;
  strategy_preset: string;
  selected_cryptos: Array<{ symbol: string; reason: string }>;
  risk_config: Record<string, number>;
  expected_behavior: string;
  warnings: string[];
}

export interface DeployResponse {
  strategy_id: string;
  strategy_name: string;
  symbols_count: number;
  message: string;
}

export function useScanMarket() {
  return useMutation({
    mutationFn: (topN: number = 30) =>
      api.post<ScanResponse>("/advisor/scan", { top_n: topN }),
  });
}

export function useGeneratePlan() {
  return useMutation({
    mutationFn: (data: {
      amount: number;
      risk_tolerance: string;
      scan_results?: ScoredCrypto[];
    }) => api.post<InvestmentPlan>("/advisor/plan", data),
  });
}

export function useDeployPlan() {
  return useMutation({
    mutationFn: (plan: InvestmentPlan) =>
      api.post<DeployResponse>("/advisor/deploy", { plan }),
  });
}
