import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";

export interface PipelineLogEntry {
  id: string;
  strategy_id: string;
  symbol: string;
  timeframe: string;
  action: "BUY" | "SELL" | "NO_TRADE";
  block_reason: string | null;
  confluence_score: number | null;
  regime: string | null;
  created_at: string;
  signal_status?: string;
  signal_ai_reasoning?: string;
  signal_ai_recommendation?: string;
}

export interface PipelineLogResponse {
  items: PipelineLogEntry[];
  total: number;
  limit: number;
  offset: number;
}

export interface PipelineLogSummary {
  total_evaluations: number;
  passed: number;
  blocked: number;
  block_reasons: Record<string, number>;
  symbols_evaluated: number;
  last_run_at: string | null;
  period_start: string;
}

export interface PipelineLogParams {
  page?: number;
  per_page?: number;
  symbol?: string;
  block_reason?: string;
  action?: string;
  since?: string;
  until?: string;
}

export function usePipelineLog(params: PipelineLogParams = {}) {
  const perPage = params.per_page ?? 50;
  const page = params.page ?? 1;
  const offset = (page - 1) * perPage;

  return useQuery({
    queryKey: ["engine", "log", params],
    queryFn: async () => {
      let query = supabase
        .from("pipeline_logs")
        .select("*", { count: "exact" })
        .order("created_at", { ascending: false })
        .range(offset, offset + perPage - 1);

      if (params.symbol) query = query.eq("symbol", params.symbol);
      if (params.block_reason) query = query.eq("block_reason", params.block_reason);
      if (params.action) query = query.eq("action", params.action);
      if (params.since) query = query.gte("created_at", params.since);
      if (params.until) query = query.lte("created_at", params.until);

      const { data, error, count } = await query;
      if (error) throw error;
      return {
        items: (data ?? []) as PipelineLogEntry[],
        total: count ?? 0,
        limit: perPage,
        offset,
      } as PipelineLogResponse;
    },
    refetchInterval: 300_000,
  });
}

export function usePipelineSummary() {
  return useQuery({
    queryKey: ["engine", "log", "summary"],
    queryFn: async () => {
      // Fetch recent pipeline logs and compute summary client-side
      const { data, error } = await supabase
        .from("pipeline_logs")
        .select("action, block_reason, symbol, created_at")
        .order("created_at", { ascending: false })
        .limit(1000);
      if (error) throw error;

      const rows = data ?? [];
      const total_evaluations = rows.length;
      const passed = rows.filter((r) => r.action !== "NO_TRADE").length;
      const blocked = rows.filter((r) => r.action === "NO_TRADE").length;
      const block_reasons: Record<string, number> = {};
      for (const r of rows) {
        if (r.block_reason) {
          block_reasons[r.block_reason] = (block_reasons[r.block_reason] ?? 0) + 1;
        }
      }
      const symbols_evaluated = new Set(rows.map((r) => r.symbol)).size;
      const last_run_at = rows.length > 0 ? rows[0].created_at : null;
      const period_start = rows.length > 0 ? rows[rows.length - 1].created_at : new Date().toISOString();

      return {
        total_evaluations,
        passed,
        blocked,
        block_reasons,
        symbols_evaluated,
        last_run_at,
        period_start,
      } as PipelineLogSummary;
    },
    refetchInterval: 300_000,
  });
}
