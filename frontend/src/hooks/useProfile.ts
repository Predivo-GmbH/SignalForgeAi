import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface Profile {
  id: string;
  email: string;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
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
