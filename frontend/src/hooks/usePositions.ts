import { useQuery } from "@tanstack/react-query";
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
