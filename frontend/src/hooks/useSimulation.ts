import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { invokeFunction } from "@/lib/api";

export interface SimulationHolding {
  symbol: string;
  quantity: number;
  price_usd: number;
  value_usd: number;
}

export interface SimulationSnapshot {
  timestamp: string;
  bh_value_usd: number;
  sf_value_usd: number;
}

export interface SimulationData {
  id: string;
  status: "running" | "stopped";
  strategy_id: string | null;
  started_at: string;
  stopped_at: string | null;
  initial_value_usd: number;
  initial_holdings: SimulationHolding[];
  paper_holdings: SimulationHolding[];
  snapshots: SimulationSnapshot[];
  latest_bh_value: number;
  latest_sf_value: number;
  bh_return_pct: number;
  sf_return_pct: number;
  sf_trades: number;
  sf_win_rate: number;
  sf_open_positions: number;
  // Reserve info
  usdt_reserve_pct: number;
  usdt_reserve_mode: "ai" | "manual" | "auto_accept";
  usdt_balance: number;
  ai_suggested_reserve_pct: number | null;
  ai_reserve_reasoning: string | null;
}

export interface PortfolioHolding {
  symbol: string;
  quantity: number;
  initial_quantity?: number;
  quantity_change?: number;
  initial_price?: number;
  current_price: number;
  value_usd: number;
  initial_value_usd: number;
  pnl_usd: number;
  pnl_pct: number;
  change_24h_pct: number | null;
  image_url: string | null;
  market_cap: number | null;
  market_cap_rank: number | null;
}

export interface BHPortfolioData {
  type: "buy_and_hold";
  total_value_usd: number;
  initial_value_usd: number;
  total_pnl_usd: number;
  total_pnl_pct: number;
  holdings: PortfolioHolding[];
}

export interface PaperPortfolioData {
  type: "paper_trading";
  total_value_usd: number;
  initial_value_usd: number;
  total_pnl_usd: number;
  total_pnl_pct: number;
  holdings: PortfolioHolding[];
  usdt_balance: number;
  usdt_reserve_pct: number;
  usdt_reserve_target_usd: number;
  usdt_reserve_status: "at_target" | "below_target" | "above_target";
  usdt_reserve_mode: string;
  ai_suggested_reserve_pct: number | null;
  ai_reserve_reasoning: string | null;
  open_positions: {
    symbol: string;
    direction: string;
    quantity: number;
    entry_price: number;
    current_price: number | null;
    unrealized_pnl: number | null;
  }[];
}

export function useSimulation() {
  return useQuery({
    queryKey: ["simulation", "active"],
    queryFn: () =>
      invokeFunction<SimulationData | null>("simulation", { action: "get" }),
    refetchInterval: 60_000,
  });
}

export function useLatestSimulation() {
  return useQuery({
    queryKey: ["simulation", "latest"],
    queryFn: () =>
      invokeFunction<SimulationData | null>("simulation", { action: "latest" }),
  });
}

export function useStartSimulation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      invokeFunction<{ id: string }>("simulation", { action: "start" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["simulation"] });
    },
  });
}

export function useStopSimulation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (simId: string) =>
      invokeFunction<SimulationData>("simulation", {
        action: "stop",
        id: simId,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["simulation"] });
    },
  });
}

interface CombinedPortfolio {
  bh: BHPortfolioData;
  paper: PaperPortfolioData;
}

/** Fetches both B&H and Paper portfolios from a single price fetch. */
export function useCombinedPortfolio(simId: string | undefined) {
  return useQuery({
    queryKey: ["simulation", simId, "portfolio"],
    queryFn: () =>
      invokeFunction<CombinedPortfolio>("simulation", {
        action: "portfolio",
        id: simId,
      }),
    enabled: !!simId,
    refetchInterval: 60_000,
  });
}

/** @deprecated Use useCombinedPortfolio instead */
export function useBHPortfolio(simId: string | undefined) {
  const { data, ...rest } = useCombinedPortfolio(simId);
  return { data: data?.bh, ...rest };
}

/** @deprecated Use useCombinedPortfolio instead */
export function usePaperPortfolio(simId: string | undefined) {
  const { data, ...rest } = useCombinedPortfolio(simId);
  return { data: data?.paper, ...rest };
}

export function useUpdateReserve() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      simId,
      usdt_reserve_pct,
      mode,
    }: {
      simId: string;
      usdt_reserve_pct: number;
      mode: string;
    }) =>
      invokeFunction("simulation", {
        action: "reserve",
        id: simId,
        usdt_reserve_pct,
        mode,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["simulation"] });
    },
  });
}
