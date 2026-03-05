import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface PipelineLogEntry {
  id: string;
  symbol: string;
  timeframe: string;
  action: "BUY" | "SELL" | "NO_TRADE";
  block_reason: string | null;
  confluence_score: number | null;
  regime: string | null;
  created_at: string;
}

export interface PipelineLogResponse {
  items: PipelineLogEntry[];
  total: number;
  page: number;
  per_page: number;
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
}

export function usePipelineLog(params: PipelineLogParams = {}) {
  const qs = new URLSearchParams();
  if (params.page) qs.set("page", String(params.page));
  if (params.per_page) qs.set("per_page", String(params.per_page));
  if (params.symbol) qs.set("symbol", params.symbol);
  if (params.block_reason) qs.set("block_reason", params.block_reason);
  if (params.action) qs.set("action", params.action);
  if (params.since) qs.set("since", params.since);
  const query = qs.toString();

  return useQuery({
    queryKey: ["engine", "log", params],
    queryFn: () => api.get<PipelineLogResponse>(`/engine/log${query ? `?${query}` : ""}`),
    refetchInterval: 300_000,
  });
}

export function usePipelineSummary() {
  return useQuery({
    queryKey: ["engine", "log", "summary"],
    queryFn: () => api.get<PipelineLogSummary>("/engine/log/summary"),
    refetchInterval: 300_000,
  });
}
