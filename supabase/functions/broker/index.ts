import { serve } from 'https://deno.land/std@0.208.0/http/server.ts'
import { authenticateRequest, errorResponse, jsonResponse, AuthError } from '../_shared/auth.ts'
import { getCorsHeaders } from '../_shared/cors.ts'

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: getCorsHeaders(req) })
  }

  try {
    const { user, adminClient } = await authenticateRequest(req)
    const body = req.method === 'POST' ? await req.json() : {}
    const action = body.action ?? 'list'

    switch (action) {
      case 'list': {
        const { data, error } = await adminClient.from('broker_connections')
          .select('id, broker, is_paper, purpose, created_at')
          .eq('user_id', user.id).order('created_at', { ascending: false })
        if (error) throw new AuthError(error.message, 500)
        return jsonResponse(data)
      }

      case 'connect': {
        const { broker, api_key, api_secret, api_passphrase, is_paper = true, purpose = 'read' } = body

        // For paper mode, no credentials needed
        if (!is_paper && (!api_key || !api_secret)) {
          throw new AuthError('API key and secret required for live trading', 400)
        }

        // Store credentials in Supabase Vault
        let vaultKeyId = null, vaultSecretId = null, vaultPassphraseId = null

        if (api_key) {
          const { data: keyVault } = await adminClient.rpc('vault.create_secret', {
            secret: api_key, name: `broker_key_${user.id}_${broker}`,
          })
          vaultKeyId = keyVault
        }
        if (api_secret) {
          const { data: secretVault } = await adminClient.rpc('vault.create_secret', {
            secret: api_secret, name: `broker_secret_${user.id}_${broker}`,
          })
          vaultSecretId = secretVault
        }
        if (api_passphrase) {
          const { data: passVault } = await adminClient.rpc('vault.create_secret', {
            secret: api_passphrase, name: `broker_pass_${user.id}_${broker}`,
          })
          vaultPassphraseId = passVault
        }

        const { data, error } = await adminClient.from('broker_connections').insert({
          user_id: user.id,
          broker,
          is_paper,
          purpose,
          vault_key_id: vaultKeyId,
          vault_secret_id: vaultSecretId,
          vault_passphrase_id: vaultPassphraseId,
        }).select('id, broker, is_paper, purpose, created_at').single()

        if (error) throw new AuthError(error.message, 500)
        return jsonResponse(data, 201)
      }

      case 'disconnect': {
        // Delete vault secrets first
        const { data: conn } = await adminClient.from('broker_connections')
          .select('vault_key_id, vault_secret_id, vault_passphrase_id')
          .eq('id', body.id).eq('user_id', user.id).single()

        if (conn) {
          for (const vaultId of [conn.vault_key_id, conn.vault_secret_id, conn.vault_passphrase_id]) {
            if (vaultId) {
              await adminClient.rpc('vault.delete_secret', { secret_id: vaultId }).catch(() => {})
            }
          }
        }

        const { error } = await adminClient.from('broker_connections')
          .delete().eq('id', body.id).eq('user_id', user.id)
        if (error) throw new AuthError(error.message, 500)
        return jsonResponse({ deleted: true })
      }

      case 'health': {
        const { data: conn, error } = await adminClient.from('broker_connections')
          .select('*').eq('id', body.id).eq('user_id', user.id).single()
        if (error || !conn) throw new AuthError('Connection not found', 404)

        // Test connection via CCXT
        let ok = true, errorMsg: string | null = null
        if (!conn.is_paper && conn.vault_key_id) {
          try {
            const { getExchange } = await import('../_shared/ccxt.ts')

            // Retrieve secrets from vault
            const { data: keySecret } = await adminClient.rpc('vault.read_secret', {
              secret_id: conn.vault_key_id,
            })
            const { data: apiSecret } = await adminClient.rpc('vault.read_secret', {
              secret_id: conn.vault_secret_id,
            })

            const exchange = getExchange(conn.broker, keySecret, apiSecret)
            await exchange.fetchBalance()
          } catch (e) {
            ok = false
            errorMsg = e instanceof Error ? e.message : 'Connection test failed'
          }
        }

        return jsonResponse({
          id: conn.id,
          broker: conn.broker,
          ok,
          error: errorMsg,
          sync_ok: null,
          sync_error: null,
        })
      }

      default:
        throw new AuthError(`Unknown action: ${action}`, 400)
    }
  } catch (err) {
    return errorResponse(err)
  }
})
