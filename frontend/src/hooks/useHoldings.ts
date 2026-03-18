import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";

export interface HoldingItem {
  id?: string;
  symbol: string;
  quantity: number;
  avg_price: number | null;
  current_price: number | null;
  value_usd: number | null;
  change_24h_pct: number | null;
  allocation_pct: number | null;
  source: string;
  notes: string | null;
  market_cap: number | null;
  market_cap_rank: number | null;
  volume_24h: number | null;
  image_url: string | null;
}

export interface HoldingsResponse {
  holdings: HoldingItem[];
  total_value_usd: number | null;
}

export interface ManualHoldingRequest {
  symbol: string;
  quantity: number;
  purchase_price?: number | null;
  notes?: string | null;
}

export function useHoldings() {
  return useQuery({
    queryKey: ["holdings"],
    queryFn: async () => {
      const { data, error } = await supabase
        .from("manual_holdings")
        .select("*")
        .order("created_at", { ascending: false });
      if (error) throw error;
      // Wrap in HoldingsResponse shape for backward compatibility
      const holdings = (data ?? []) as HoldingItem[];
      const total_value_usd = holdings.reduce(
        (sum, h) => sum + (h.value_usd ?? 0),
        0,
      );
      return { holdings, total_value_usd } as HoldingsResponse;
    },
    refetchInterval: 60_000,
  });
}

export function useAddHolding() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: ManualHoldingRequest) => {
      const { data: row, error } = await supabase
        .from("manual_holdings")
        .insert({
          symbol: data.symbol,
          quantity: data.quantity,
          avg_price: data.purchase_price ?? null,
          notes: data.notes ?? null,
          source: "manual",
        })
        .select()
        .single();
      if (error) throw error;
      return row;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["holdings"] }),
  });
}

export function useUpdateHolding() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...data }: ManualHoldingRequest & { id: string }) => {
      const { data: row, error } = await supabase
        .from("manual_holdings")
        .update({
          symbol: data.symbol,
          quantity: data.quantity,
          avg_price: data.purchase_price ?? null,
          notes: data.notes ?? null,
        })
        .eq("id", id)
        .select()
        .single();
      if (error) throw error;
      return row;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["holdings"] }),
  });
}

export function useDeleteHolding() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { error } = await supabase
        .from("manual_holdings")
        .delete()
        .eq("id", id);
      if (error) throw error;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["holdings"] }),
  });
}

export interface BulkImportRequest {
  holdings: ManualHoldingRequest[];
  clear_existing?: boolean;
}

export function useBulkImportHoldings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: BulkImportRequest) => {
      if (data.clear_existing) {
        const { error: delErr } = await supabase
          .from("manual_holdings")
          .delete()
          .neq("id", "00000000-0000-0000-0000-000000000000"); // delete all rows
        if (delErr) throw delErr;
      }
      const rows = data.holdings.map((h) => ({
        symbol: h.symbol,
        quantity: h.quantity,
        avg_price: h.purchase_price ?? null,
        notes: h.notes ?? null,
        source: "manual",
      }));
      const { error } = await supabase
        .from("manual_holdings")
        .insert(rows);
      if (error) throw error;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["holdings"] }),
  });
}
