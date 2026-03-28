import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { supabase } from '@/lib/supabase'
import { usePageTitle } from '@/hooks/usePageTitle'
import { useNoIndex } from '@/hooks/useNoIndex'

/**
 * Handles Supabase auth redirects (magic links, password resets, email confirmations).
 * Tokens arrive as URL hash fragments (#access_token=...&type=...).
 */
export default function AuthCallbackPage() {
  usePageTitle('Redirecting')
  useNoIndex()
  const navigate = useNavigate()
  const [status] = useState('Processing...')

  useEffect(() => {
    handleAuthCallback()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function handleAuthCallback() {
    const { data: { session }, error } = await supabase.auth.getSession()

    if (error) {
      if (import.meta.env.DEV) console.error('Auth callback error:', error)
      navigate('/login')
      return
    }

    const hash = window.location.hash
    const params = new URLSearchParams(hash.replace('#', ''))
    const type = params.get('type')

    if (type === 'recovery') {
      navigate('/reset-password')
    } else if (session) {
      const isNewUser = !session.user?.user_metadata?.profile_complete
      navigate(isNewUser ? '/signup' : '/')
    } else {
      navigate('/login')
    }
  }

  return (
    <div className="flex h-screen items-center justify-center bg-(--color-bg-base)">
      <div className="text-center">
        <div className="mx-auto h-6 w-6 animate-spin rounded-full border-2 border-(--color-accent) border-t-transparent" />
        <p className="mt-4 text-sm text-(--color-text-secondary)">{status}</p>
      </div>
    </div>
  )
}
