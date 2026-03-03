import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface Position {
  id: string;
  symbol: string;
  direction: string;
  entry_price: number;
  quantity: number;
  stop_loss: number | null;
  take_profit: number | null;
  is_open: boolean;
  unrealized_pnl: number | null;
  current_price: number | null;
  opened_at: string | null;
  closed_at: string | null;
  broker: string;
  strategy_id: string | null;
  order_id: string | null;
  bracket_status: string | null;
  break_even_applied: boolean;
  trailing_activated: boolean;
  original_stop_loss: number | null;
}

export interface AccountState {
  equity: number;
  daily_pnl: number;
  open_positions: number;
  max_positions: number;
}

export function usePositions() {
  return useQuery({
    queryKey: ["positions"],
    queryFn: () => api.get<Position[]>("/positions"),
    refetchInterval: 15_000,
  });
}

export function useAccountState() {
  return useQuery({
    queryKey: ["positions", "account"],
    queryFn: () => api.get<AccountState>("/positions/account"),
  });
}

export interface DrawdownState {
  peak_equity: number;
  current_equity: number;
  drawdown_pct: number;
  level: number;
  level_name: string;
}

export interface CPPIState {
  floor: number;
  peak_equity: number;
  exposure_pct: number;
  cushion: number;
  multiplier: number;
  max_drawdown_pct: number;
}

export interface CorrelationAlert {
  symbol_a: string;
  symbol_b: string;
  correlation: number;
  risk_level: string;
}

export interface CorrelationState {
  matrix: Record<string, Record<string, number>>;
  alerts: CorrelationAlert[];
  max_correlation: number;
  exposure_penalty: number;
}

export function useDrawdownState() {
  return useQuery({
    queryKey: ["positions", "drawdown"],
    queryFn: () => api.get<DrawdownState>("/positions/drawdown"),
    refetchInterval: 30_000,
  });
}

export function useCPPIState() {
  return useQuery({
    queryKey: ["positions", "cppi"],
    queryFn: () => api.get<CPPIState>("/positions/cppi"),
    refetchInterval: 30_000,
  });
}

export function useCorrelationState() {
  return useQuery({
    queryKey: ["positions", "correlations"],
    queryFn: () => api.get<CorrelationState>("/positions/correlations"),
    refetchInterval: 60_000,
  });
}

export function useClosePosition() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ positionId, exitPrice }: { positionId: string; exitPrice: number }) =>
      api.post(`/positions/${positionId}/close`, { exit_price: exitPrice, reason: "manual" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["positions"] });
      queryClient.invalidateQueries({ queryKey: ["trades"] });
    },
  });
}
