const ALLOWED_ORIGINS = [
  'https://signalforgeai.predivo.ch',
  'http://localhost:5173',
]

/** Build CORS headers with validated origin */
export function getCorsHeaders(req?: Request): Record<string, string> {
  const origin = req?.headers.get('Origin') ?? ''
  const allowedOrigin = ALLOWED_ORIGINS.includes(origin) ? origin : ALLOWED_ORIGINS[0]
  return {
    'Access-Control-Allow-Origin': allowedOrigin,
    'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
  }
}

/** Default CORS headers (production origin) */
export const corsHeaders = {
  'Access-Control-Allow-Origin': 'https://signalforgeai.predivo.ch',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
}
