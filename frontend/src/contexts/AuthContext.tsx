import { createContext, useState, useEffect, useCallback, useContext, type ReactNode } from 'react'
import { supabase } from '@/lib/supabase'
import type { User as SupabaseUser } from '@supabase/supabase-js'

export interface AuthContextValue {
  user: SupabaseUser | null
  loading: boolean
  /** Traditional email+password sign in */
  signInWithPassword: (email: string, password: string) => Promise<void>
  /** Send OTP code for signup (creates user if not exists) */
  sendOtp: (email: string) => Promise<void>
  /** Send OTP code for login only (does NOT create user — fails silently if no account) */
  sendLoginOtp: (email: string) => Promise<void>
  /** Verify an OTP code — returns whether user is new (needs profile setup) */
  verifyOtp: (email: string, token: string) => Promise<{ isNewUser: boolean }>
  /** Check if user has completed profile (password set) */
  hasCompletedProfile: () => boolean
  /** Set password on authenticated user (post-OTP signup) */
  completeProfile: (password: string) => Promise<void>
  /** Send password reset email */
  resetPassword: (email: string) => Promise<void>
  /** Update password (used on /reset-password with active session) */
  updatePassword: (password: string) => Promise<void>
  /** Delete the current user's account */
  deleteAccount: () => Promise<void>
  /** Sign out */
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<SupabaseUser | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null)
      setLoading(false)
    })

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(async (event, session) => {
      setUser(session?.user ?? null)
      if (event === 'SIGNED_IN' && session?.user) {
        // Ensure profile row exists (upsert, ignore if already there)
        await supabase.from('profiles').upsert(
          { user_id: session.user.id },
          { onConflict: 'user_id', ignoreDuplicates: true }
        )
      }
    })

    return () => subscription.unsubscribe()
  }, [])

  const signInWithPassword = useCallback(async (email: string, password: string) => {
    const { error } = await supabase.auth.signInWithPassword({ email, password })
    if (error) throw error
  }, [])

  const sendOtp = useCallback(async (email: string) => {
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: { shouldCreateUser: true },
    })
    if (error) throw error
  }, [])

  const sendLoginOtp = useCallback(async (email: string) => {
    // shouldCreateUser: false — only sends OTP if account exists
    // Supabase returns 200 regardless (prevents email enumeration),
    // so we can't distinguish "sent" from "no account" at this level.
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: { shouldCreateUser: false },
    })
    if (error) throw error
  }, [])

  const verifyOtp = useCallback(async (email: string, token: string) => {
    const { data, error } = await supabase.auth.verifyOtp({
      email,
      token,
      type: 'email',
    })
    if (error) throw error
    const isNewUser = !data.user?.user_metadata?.profile_complete
    return { isNewUser }
  }, [])

  const completeProfile = useCallback(async (password: string) => {
    const { error } = await supabase.auth.updateUser({
      password,
      data: { profile_complete: true },
    })
    if (error) throw error
  }, [])

  const resetPassword = useCallback(async (email: string) => {
    const redirectTo = `${window.location.origin}/reset-password`
    const { error } = await supabase.auth.resetPasswordForEmail(email, { redirectTo })
    if (error) throw error
  }, [])

  const updatePassword = useCallback(async (password: string) => {
    const { error } = await supabase.auth.updateUser({ password })
    if (error) throw error
  }, [])

  const hasCompletedProfile = useCallback(() => {
    if (!user) return false
    return !!user.user_metadata?.profile_complete
  }, [user])

  const deleteAccount = useCallback(async () => {
    const { error: fnError } = await supabase.functions.invoke('delete-account', {
      method: 'POST',
    })

    if (fnError) {
      throw new Error(fnError.message || 'Failed to delete account')
    }

    await supabase.auth.signOut()
  }, [])

  const signOut = useCallback(async () => {
    const { error } = await supabase.auth.signOut()
    if (error) throw error
  }, [])

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        signInWithPassword,
        sendOtp,
        sendLoginOtp,
        verifyOtp,
        hasCompletedProfile,
        completeProfile,
        resetPassword,
        updatePassword,
        deleteAccount,
        signOut,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
