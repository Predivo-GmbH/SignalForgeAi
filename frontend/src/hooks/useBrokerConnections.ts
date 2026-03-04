import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

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
    queryFn: () => api.get<BrokerConnection[]>("/broker"),
  });
}

export function useConnectBroker() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ConnectBrokerRequest) =>
      api.post<BrokerConnection>("/broker", data),
    onSuccess: () => qc.invalidateQueries({ queryKey: BROKER_KEY }),
  });
}

export function useDisconnectBroker() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete<void>(`/broker/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: BROKER_KEY }),
  });
}
