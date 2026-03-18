import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";
import { invokeFunction } from "@/lib/api";

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
    queryFn: async () => {
      const { data, error } = await supabase
        .from("positions")
        .select("*")
        .eq("is_open", true)
        .order("opened_at", { ascending: false });
      if (error) throw error;
      return (data ?? []) as Position[];
    },
    refetchInterval: 15_000,
  });
}

export function useAccountState() {
  return useQuery({
    queryKey: ["positions", "account"],
    queryFn: () =>
      invokeFunction<AccountState>("simulation", { action: "account" }),
  });
}

export interface DrawdownState {
  peak_equity: number;
  current_equity: number;
  drawdown_pct: number;
  level: number;
  level_name: string;
}

export function useDrawdownState() {
  return useQuery({
    queryKey: ["positions", "drawdown"],
    queryFn: () =>
      invokeFunction<DrawdownState>("simulation", { action: "drawdown" }),
    refetchInterval: 30_000,
  });
}

export interface DashboardSimulation {
  id: string;
  status: string;
  initial_value_usd: number;
  bh_value: number;
  paper_value: number;
  bh_return_pct: number;
  paper_return_pct: number;
}

export interface DashboardSnapshot {
  equity: number;
  balance: number;
  daily_pnl: number;
  open_positions: number;
  max_positions: number;
  simulation: DashboardSimulation | null;
}

export function useDashboardSnapshot() {
  return useQuery({
    queryKey: ["dashboard-snapshot"],
    queryFn: () =>
      invokeFunction<DashboardSnapshot>("simulation", {
        action: "dashboard-snapshot",
      }),
    refetchInterval: 30_000,
  });
}

export function useClosePosition() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ positionId, exitPrice }: { positionId: string; exitPrice: number }) =>
      invokeFunction("simulation", {
        action: "close-position",
        position_id: positionId,
        exit_price: exitPrice,
        reason: "manual",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["positions"] });
      queryClient.invalidateQueries({ queryKey: ["trades"] });
    },
  });
}
