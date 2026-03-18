import { useQuery } from "@tanstack/react-query";
import { invokeFunction } from "@/lib/api";

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
  const perPage = params.per_page ?? 20;
  const page = params.page ?? 1;

  return useQuery({
    queryKey: ["engine", "log", "runs", params],
    queryFn: () =>
      invokeFunction<PipelineRunsResponse>("engine-monitor", {
        action: "runs",
        limit: perPage,
        offset: (page - 1) * perPage,
        since: params.since,
      }),
    refetchInterval: 300_000,
  });
}
