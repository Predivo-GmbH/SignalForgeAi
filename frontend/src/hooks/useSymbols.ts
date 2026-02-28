import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useSymbols() {
  return useQuery({
    queryKey: ["market", "symbols"],
    queryFn: () => api.get<string[]>("/market/symbols"),
    staleTime: 5 * 60 * 1000,
  });
}
