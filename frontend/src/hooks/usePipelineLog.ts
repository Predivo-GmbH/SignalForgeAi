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
  const qs = new URLSearchParams();
  // Convert page/per_page to limit/offset for backend
  const perPage = params.per_page ?? 50;
  const page = params.page ?? 1;
  qs.set("limit", String(perPage));
  qs.set("offset", String((page - 1) * perPage));
  if (params.symbol) qs.set("symbol", params.symbol);
  if (params.block_reason) qs.set("block_reason", params.block_reason);
  if (params.action) qs.set("action", params.action);
  if (params.since) qs.set("since", params.since);
  if (params.until) qs.set("until", params.until);
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
