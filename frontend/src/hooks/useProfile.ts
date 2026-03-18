import { useQuery, useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";
import { useAuth } from "@/contexts/AuthContext";

export interface Profile {
  id: string;
  email: string;
  is_active: boolean;
  alert_config: Record<string, unknown> | null;
  created_at: string;
  updated_at: string | null;
}

export function useProfile() {
  const { user } = useAuth();

  return useQuery({
    queryKey: ["profile"],
    queryFn: async () => {
      if (!user) throw new Error("Not authenticated");
      const { data, error } = await supabase
        .from("profiles")
        .select("*")
        .eq("user_id", user.id)
        .single();
      if (error) throw error;
      // Merge auth user fields into profile
      return {
        ...data,
        id: user.id,
        email: user.email ?? "",
        is_active: true,
      } as Profile;
    },
    enabled: !!user,
    staleTime: 5 * 60_000,
  });
}

export function useChangeEmail() {
  const qc = useQueryClient();
  return {
    mutateAsync: async (data: { new_email: string }) => {
      const { error } = await supabase.auth.updateUser({ email: data.new_email });
      if (error) throw error;
      qc.invalidateQueries({ queryKey: ["profile"] });
    },
  };
}
