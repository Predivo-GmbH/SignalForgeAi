import { useQuery } from "@tanstack/react-query";
import { invokeFunction } from "@/lib/api";

export interface EngineStatus {
  active: boolean;
  layers: string[];
  supported_symbols: string[];
  supported_timeframes: string[];
}

export function useEngineStatus() {
  return useQuery({
    queryKey: ["engine", "status"],
    queryFn: () =>
      invokeFunction<EngineStatus>("engine-monitor", { action: "status" }),
  });
}
