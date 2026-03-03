import { useQuery } from "@tanstack/react-query";
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
