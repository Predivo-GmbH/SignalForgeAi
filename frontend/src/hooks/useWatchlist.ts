import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface SymbolLastStatus {
  action: string;
  block_reason: string | null;
  regime: string | null;
  confluence_score: number | null;
  checked_at: string; // ISO 8601
}

export interface WatchlistSymbol {
  symbol: string;
  source: "ai_deploy" | "portfolio_sync" | "universe_discovery";
  in_portfolio: boolean;
  last_status: SymbolLastStatus | null;
}

export interface WatchlistData {
  strategy_symbols: WatchlistSymbol[];
  candidate_pool: string[];
  blocklist: string[];
  total_strategy_symbols: number;
  total_candidates: number;
}

const WATCHLIST_KEY = ["strategies", "watchlist"] as const;

export function useWatchlist() {
  return useQuery({
    queryKey: WATCHLIST_KEY,
    queryFn: () => api.get<WatchlistData>("/strategies/watchlist"),
    refetchInterval: 30_000,
  });
}

export function useRemoveWatchlistSymbol() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (symbol: string) =>
      api.delete<void>(`/strategies/symbols/${encodeURIComponent(symbol)}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: WATCHLIST_KEY }),
  });
}

export function useRemoveCandidate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (symbol: string) =>
      api.delete<void>(`/strategies/candidates/${encodeURIComponent(symbol)}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: WATCHLIST_KEY }),
  });
}

export function useUnblockCandidate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (symbol: string) =>
      api.post<void>(`/strategies/candidates/${encodeURIComponent(symbol)}/unblock`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: WATCHLIST_KEY }),
  });
}

export function useTriggerDiscovery() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<{ queued: boolean; message: string }>("/strategies/discover", {}),
    onSuccess: () => setTimeout(() => qc.invalidateQueries({ queryKey: WATCHLIST_KEY }), 3000),
  });
}
