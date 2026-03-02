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

export interface MarketSummary {
  trending_pct: number;
  bullish_pct: number;
  avg_score: number;
  avg_adx: number;
  avg_volatility: number;
}

export interface MarketRecommendation {
  preset: string;
  reason: string;
  market_summary: MarketSummary;
}

export interface ScanResponse {
  pairs_scanned: number;
  pairs_scored: number;
  results: ScoredCrypto[];
  recommendation: MarketRecommendation;
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
