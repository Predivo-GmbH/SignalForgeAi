import { useQuery, useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";

interface AnalyzeResponse {
  analysis: string;
  patterns: string[];
  recommendations: string[];
}

interface PatternSummary {
  summary: string;
  top_patterns: string[];
  areas_to_improve: string[];
}

export function useAnalyzeTrade() {
  return useMutation({
    mutationFn: (data: { trade_id: string }) =>
      api.post<AnalyzeResponse>("/journal/analyze", data),
  });
}

export function usePatternSummary() {
  return useQuery({
    queryKey: ["journal", "patterns"],
    queryFn: () => api.get<PatternSummary>("/journal/patterns"),
  });
}
