import { useQuery } from "@tanstack/react-query";
import { invokeFunction } from "@/lib/api";

export function useSymbols() {
  return useQuery({
    queryKey: ["market", "symbols"],
    queryFn: () =>
      invokeFunction<string[]>("market", { action: "symbols" }),
    staleTime: 5 * 60 * 1000,
  });
}
