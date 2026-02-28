import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface EquityPoint {
  date: string;
  equity: number;
  drawdown_pct: number;
}

export interface EquityHistory {
  points: EquityPoint[];
  total_return_pct: number;
  max_drawdown_pct: number;
  sharpe_ratio: number | null;
  sortino_ratio: number | null;
  calmar_ratio: number | null;
}

export interface CorrelationResult {
  symbol_a: string;
  symbol_b: string;
  correlation: number;
  data_points: number;
}

export function useEquityHistory() {
  return useQuery({
    queryKey: ["analytics", "equity"],
    queryFn: () => api.get<EquityHistory>("/analytics/equity"),
  });
}

export function useCorrelation(symbolA: string, symbolB: string) {
  return useQuery({
    queryKey: ["analytics", "correlation", symbolA, symbolB],
    queryFn: () =>
      api.get<CorrelationResult>(
        `/analytics/correlation?symbol_a=${encodeURIComponent(symbolA)}&symbol_b=${encodeURIComponent(symbolB)}`
      ),
    enabled: !!symbolA && !!symbolB && symbolA !== symbolB,
  });
}
