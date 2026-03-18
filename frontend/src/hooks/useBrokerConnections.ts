import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { invokeFunction } from "@/lib/api";

export interface BrokerConnection {
  id: string;
  broker: string;
  api_key_masked: string;
  is_paper: boolean;
  purpose: "read" | "trade";
  created_at: string;
}

export interface ConnectBrokerRequest {
  broker: string;
  api_key?: string;
  api_secret?: string;
  api_passphrase?: string;
  is_paper: boolean;
  purpose: "read" | "trade";
}

const BROKER_KEY = ["broker-connections"] as const;

export function useBrokerConnections() {
  return useQuery({
    queryKey: BROKER_KEY,
    queryFn: () =>
      invokeFunction<BrokerConnection[]>("broker", { action: "list" }),
  });
}

export function useConnectBroker() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ConnectBrokerRequest) =>
      invokeFunction<BrokerConnection>("broker", {
        action: "connect",
        ...data,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: BROKER_KEY }),
  });
}

export function useDisconnectBroker() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      invokeFunction<void>("broker", { action: "disconnect", id }),
    onSuccess: () => qc.invalidateQueries({ queryKey: BROKER_KEY }),
  });
}

export interface BrokerHealth {
  id: string;
  broker: string;
  ok: boolean;
  error: string | null;
  /** Last result from the background portfolio sync task (worker container). null if never run. */
  sync_ok: boolean | null;
  sync_error: string | null;
}

export function useBrokerHealth(connectionId: string | null) {
  return useQuery({
    queryKey: ["broker-health", connectionId],
    queryFn: () =>
      invokeFunction<BrokerHealth>("broker", {
        action: "health",
        id: connectionId,
      }),
    enabled: !!connectionId,
    staleTime: 5 * 60_000, // cache for 5 minutes
    retry: false,
  });
}
