import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface AlertConfig {
  email_on_signal: boolean;
  email_daily_summary: boolean;
  min_confluence_alert: number;
  alert_email: string;
}

export function useAlertConfig() {
  return useQuery({
    queryKey: ["alerts", "config"],
    queryFn: () => api.get<AlertConfig>("/alerts/config"),
  });
}

export function useUpdateAlertConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: AlertConfig) =>
      api.put<AlertConfig>("/alerts/config", data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts", "config"] }),
  });
}
