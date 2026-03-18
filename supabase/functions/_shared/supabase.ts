import { createClient, type SupabaseClient } from 'https://esm.sh/@supabase/supabase-js@2'

let _adminClient: SupabaseClient | null = null

/** Singleton service-role client for background jobs */
export function getSupabaseAdmin(): SupabaseClient {
  if (_adminClient) return _adminClient

  const url = Deno.env.get('SUPABASE_URL')
  const serviceRoleKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')

  if (!url || !serviceRoleKey) {
    throw new Error('Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY')
  }

  _adminClient = createClient(url, serviceRoleKey, {
    auth: { autoRefreshToken: false, persistSession: false },
  })

  return _adminClient
}
