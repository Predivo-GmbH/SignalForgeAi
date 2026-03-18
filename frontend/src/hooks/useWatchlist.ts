import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { invokeFunction } from "@/lib/api";

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
    queryFn: () =>
      invokeFunction<WatchlistData>("market", { action: "watchlist" }),
    refetchInterval: 30_000,
  });
}

export function useRemoveWatchlistSymbol() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (symbol: string) =>
      invokeFunction<void>("market", {
        action: "remove-watchlist-symbol",
        symbol,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: WATCHLIST_KEY }),
  });
}

export function useRemoveCandidate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (symbol: string) =>
      invokeFunction<void>("market", {
        action: "remove-candidate",
        symbol,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: WATCHLIST_KEY }),
  });
}

export function useUnblockCandidate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (symbol: string) =>
      invokeFunction<void>("market", {
        action: "unblock-candidate",
        symbol,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: WATCHLIST_KEY }),
  });
}

export function useTriggerDiscovery() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      invokeFunction<{ queued: boolean; message: string }>("market", {
        action: "discover",
      }),
    onSuccess: () => setTimeout(() => qc.invalidateQueries({ queryKey: WATCHLIST_KEY }), 3000),
  });
}
