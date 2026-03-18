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
        // Manual holdings + cost basis + live prices
        const [holdingsResult, costBasisResult] = await Promise.all([
          adminClient.from('manual_holdings').select('*').eq('user_id', user.id),
          adminClient.from('cost_basis_overrides').select('*').eq('user_id', user.id),
        ])

        const holdings = holdingsResult.data ?? []
        const costBasis = Object.fromEntries(
          (costBasisResult.data ?? []).map(cb => [cb.symbol, cb.purchase_price])
        )

        // Enrich with cost basis overrides
        const enriched = holdings.map(h => ({
          ...h,
          purchase_price: h.purchase_price ?? costBasis[h.symbol] ?? null,
        }))

        return jsonResponse(enriched)
      }

      case 'add': {
        const { data, error } = await adminClient.from('manual_holdings').insert({
          user_id: user.id,
          symbol: body.symbol,
          quantity: body.quantity,
          purchase_price: body.purchase_price,
          notes: body.notes,
        }).select().single()
        if (error) throw new AuthError(error.message, 500)
        return jsonResponse(data, 201)
      }

      case 'update': {
        const updates: Record<string, unknown> = {}
        if (body.quantity !== undefined) updates.quantity = body.quantity
        if (body.purchase_price !== undefined) updates.purchase_price = body.purchase_price
        if (body.notes !== undefined) updates.notes = body.notes

        const { data, error } = await adminClient.from('manual_holdings')
          .update(updates).eq('id', body.id).eq('user_id', user.id).select().single()
        if (error) throw new AuthError(error.message, 500)
        return jsonResponse(data)
      }

      case 'delete': {
        const { error } = await adminClient.from('manual_holdings')
          .delete().eq('id', body.id).eq('user_id', user.id)
        if (error) throw new AuthError(error.message, 500)
        return jsonResponse({ deleted: true })
      }

      case 'bulk-import': {
        if (body.clear_existing) {
          await adminClient.from('manual_holdings').delete().eq('user_id', user.id)
        }
        const rows = (body.holdings as Array<{ symbol: string; quantity: number; purchase_price?: number; notes?: string }>)
          .map(h => ({ ...h, user_id: user.id }))
        const { data, error } = await adminClient.from('manual_holdings').insert(rows).select()
        if (error) throw new AuthError(error.message, 500)
        return jsonResponse(data)
      }

      case 'cost-basis': {
        const { data, error } = await adminClient.from('cost_basis_overrides')
          .select('*').eq('user_id', user.id)
        if (error) throw new AuthError(error.message, 500)
        return jsonResponse(data)
      }

      case 'upsert-cost-basis': {
        const { data, error } = await adminClient.from('cost_basis_overrides')
          .upsert({
            user_id: user.id,
            symbol: body.symbol,
            purchase_price: body.purchase_price,
            notes: body.notes,
          }, { onConflict: 'user_id,symbol' }).select().single()
        if (error) throw new AuthError(error.message, 500)
        return jsonResponse(data)
      }

      default:
        throw new AuthError(`Unknown action: ${action}`, 400)
    }
  } catch (err) {
    return errorResponse(err)
  }
})
