import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";
import { invokeFunction } from "@/lib/api";

export interface Strategy {
  id: string;
  user_id: string;
  name: string;
  is_active: boolean;
  config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface StrategyPreset {
  name: string;
  description: string;
  config: Record<string, unknown>;
}

export interface PresetsResponse {
  presets: Record<string, StrategyPreset>;
}

export function useStrategies() {
  return useQuery({
    queryKey: ["strategies"],
    queryFn: async () => {
      const { data, error, count } = await supabase
        .from("strategies")
        .select("*", { count: "exact" })
        .order("created_at", { ascending: false });
      if (error) throw error;
      return {
        strategies: (data ?? []) as Strategy[],
        total: count ?? 0,
      };
    },
  });
}

export function useStrategy(id: string) {
  return useQuery({
    queryKey: ["strategies", id],
    queryFn: async () => {
      const { data, error } = await supabase
        .from("strategies")
        .select("*")
        .eq("id", id)
        .single();
      if (error) throw error;
      return data as Strategy;
    },
    enabled: !!id,
  });
}

export function useStrategyPresets() {
  return useQuery({
    queryKey: ["strategy-presets"],
    queryFn: () =>
      invokeFunction<PresetsResponse>("strategies", { action: "presets" }),
    staleTime: 5 * 60 * 1000,
  });
}

export function useCreateStrategy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { name: string; config?: Record<string, unknown>; preset?: string }) =>
      invokeFunction<Strategy>("strategies", { action: "create", ...data }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["strategies"] }),
  });
}

export function useUpdateStrategy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      ...data
    }: {
      id: string;
      name?: string;
      config?: Record<string, unknown>;
    }) => {
      const { data: row, error } = await supabase
        .from("strategies")
        .update(data)
        .eq("id", id)
        .select()
        .single();
      if (error) throw error;
      return row as Strategy;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["strategies"] }),
  });
}

export function useToggleStrategy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id }: { id: string; totp_code?: string }) =>
      invokeFunction<Strategy>("strategies", { action: "toggle", id }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["strategies"] }),
  });
}

export function useDeleteStrategy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { error } = await supabase
        .from("strategies")
        .delete()
        .eq("id", id);
      if (error) throw error;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["strategies"] }),
  });
}

export interface ExchangeAvailability {
  availability: Record<string, string[]>;
  unavailable: string[];
}

export function useExchangeAvailability(symbols: string[]) {
  const joined = symbols.join(",");
  return useQuery({
    queryKey: ["exchange-availability", joined],
    queryFn: () =>
      invokeFunction<ExchangeAvailability>("strategies", {
        action: "exchange-availability",
        symbols,
      }),
    enabled: symbols.length > 0,
    staleTime: 60 * 60 * 1000, // 1 hour — markets don't change often
  });
}
