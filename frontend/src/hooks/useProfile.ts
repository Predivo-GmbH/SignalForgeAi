import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface Profile {
  id: string;
  email: string;
  is_active: boolean;
  totp_enabled: boolean;
  created_at: string;
  updated_at: string | null;
}

interface TwoFactorSetupResponse {
  qr_code: string;
  secret: string;
  provisioning_uri: string;
}

interface TwoFactorEnableResponse {
  message: string;
  backup_codes: string[];
}

export function useProfile() {
  return useQuery({
    queryKey: ["profile"],
    queryFn: () => api.get<Profile>("/auth/me"),
    staleTime: 5 * 60_000,
  });
}

export function useChangePassword() {
  return useMutation({
    mutationFn: (data: { current_password: string; new_password: string }) =>
      api.put<{ message: string }>("/auth/password", data),
  });
}

export function useChangeEmail() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { new_email: string; password: string }) =>
      api.put<Profile>("/auth/email", data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["profile"] }),
  });
}

export function useSetup2FA() {
  return useMutation({
    mutationFn: () => api.post<TwoFactorSetupResponse>("/auth/2fa/setup"),
  });
}

export function useVerify2FA() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { code: string }) =>
      api.post<TwoFactorEnableResponse>("/auth/2fa/verify", data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["profile"] }),
  });
}

export function useDisable2FA() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { password: string; code: string }) =>
      api.post<{ message: string }>("/auth/2fa/disable", data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["profile"] }),
  });
}

export function useValidate2FA() {
  return useMutation({
    mutationFn: (data: { code: string }) =>
      api.post<{ message: string }>("/auth/2fa/validate", data),
  });
}
