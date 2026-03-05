import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface PipelineRunBlockReason {
  reason: string;
  count: number;
}

export interface PipelineRun {
  run_time: string;
  total: number;
  passed: number;
  blocked: number;
  has_trades: boolean;
  symbols: string[];
  top_block_reasons: PipelineRunBlockReason[];
}

export interface PipelineRunsResponse {
  runs: PipelineRun[];
  total_runs: number;
  limit: number;
  offset: number;
}

export interface PipelineRunsParams {
  page?: number;
  per_page?: number;
  since?: string;
}

export function usePipelineRuns(params: PipelineRunsParams = {}) {
  const qs = new URLSearchParams();
  // Convert page/per_page to limit/offset for backend
  const perPage = params.per_page ?? 20;
  const page = params.page ?? 1;
  qs.set("limit", String(perPage));
  qs.set("offset", String((page - 1) * perPage));
  if (params.since) qs.set("since", params.since);
  const query = qs.toString();

  return useQuery({
    queryKey: ["engine", "log", "runs", params],
    queryFn: () =>
      api.get<PipelineRunsResponse>(`/engine/log/runs${query ? `?${query}` : ""}`),
    refetchInterval: 300_000,
  });
}
