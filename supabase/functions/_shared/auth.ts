/**
 * Shared auth helpers for Edge Functions.
 * Extracts and verifies the user from the Authorization header.
 */

import { createClient, SupabaseClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { corsHeaders } from './cors.ts'

interface AuthResult {
  user: { id: string; email?: string }
  userClient: SupabaseClient
  adminClient: SupabaseClient
}

/** Verify JWT and return user + both clients */
export async function authenticateRequest(req: Request): Promise<AuthResult> {
  const authHeader = req.headers.get('Authorization')
  if (!authHeader) {
    throw new AuthError('Missing authorization header', 401)
  }

  const userClient = createClient(
    Deno.env.get('SUPABASE_URL')!,
    Deno.env.get('SUPABASE_ANON_KEY')!,
    { global: { headers: { Authorization: authHeader } } }
  )

  const { data: { user }, error } = await userClient.auth.getUser()
  if (error || !user) {
    throw new AuthError('Invalid or expired session', 401)
  }

  const adminClient = createClient(
    Deno.env.get('SUPABASE_URL')!,
    Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
  )

  return { user: { id: user.id, email: user.email }, userClient, adminClient }
}

/** Verify this is a service-role call (for cron jobs) */
export function verifyServiceRole(req: Request): SupabaseClient {
  const authHeader = req.headers.get('Authorization')
  const serviceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
  if (authHeader !== `Bearer ${serviceKey}`) {
    throw new AuthError('Unauthorized: service role required', 403)
  }
  return createClient(
    Deno.env.get('SUPABASE_URL')!,
    serviceKey
  )
}

export class AuthError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

/** Standard JSON error response */
export function errorResponse(err: unknown): Response {
  if (err instanceof AuthError) {
    return new Response(
      JSON.stringify({ error: err.message }),
      { status: err.status, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
  console.error('Unexpected error:', err)
  return new Response(
    JSON.stringify({ error: 'Internal server error' }),
    { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
  )
}

/** Standard JSON success response */
export function jsonResponse(data: unknown, status = 200): Response {
  return new Response(
    JSON.stringify(data),
    { status, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
  )
}

/** SSE stream helper */
export function sseResponse(): { stream: ReadableStream; controller: ReadableStreamDefaultController<Uint8Array>; send: (event: string, data: unknown) => void } {
  let ctrl: ReadableStreamDefaultController<Uint8Array>
  const encoder = new TextEncoder()
  const stream = new ReadableStream<Uint8Array>({
    start(c) { ctrl = c },
  })
  const send = (event: string, data: unknown) => {
    ctrl.enqueue(encoder.encode(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`))
  }
  return { stream, controller: ctrl!, send }
}
