import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface Position {
  id: string;
  symbol: string;
  direction: string;
  entry_price: number;
  quantity: number;
  stop_loss: number;
  take_profit: number;
  is_open: boolean;
  pnl: number | null;
  exit_price: number | null;
  exit_reason: string | null;
  order_id: string;
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
  });
}

export function useAccountState() {
  return useQuery({
    queryKey: ["positions", "account"],
    queryFn: () => api.get<AccountState>("/positions/account"),
  });
}
