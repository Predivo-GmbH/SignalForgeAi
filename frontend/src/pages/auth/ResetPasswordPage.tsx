import { useState, useEffect, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useAuth } from '@/contexts/AuthContext'
import AuthLayout from '@/components/auth/AuthLayout'
import PasswordStrength from '@/components/auth/PasswordStrength'
import { getPasswordScore } from '@/components/auth/password-utils'
import { CheckCircle } from 'lucide-react'

export default function ResetPasswordPage() {
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [done, setDone] = useState(false)
  const { user, loading: authLoading, updatePassword } = useAuth()
  const navigate = useNavigate()

  // If there's no session (e.g. user navigated here directly), redirect
  useEffect(() => {
    if (authLoading) return
    if (!user) {
      navigate('/forgot-password')
    }
  }, [user, authLoading, navigate])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)

    if (password !== confirmPassword) {
      setError('Passwords do not match')
      return
    }
    if (getPasswordScore(password) < 3) {
      setError('Please choose a stronger password')
      return
    }

    setLoading(true)
    try {
      await updatePassword(password)
      setDone(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update password')
    } finally {
      setLoading(false)
    }
  }

  if (done) {
    return (
      <AuthLayout>
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.3 }}
          className="text-center"
        >
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-(--color-positive)/10">
            <CheckCircle className="h-7 w-7 text-(--color-positive)" />
          </div>
          <h1 className="mt-5 text-2xl font-bold text-(--color-text-primary)">
            Password updated
          </h1>
          <p className="mt-2 text-sm text-(--color-text-secondary)">
            Your password has been reset successfully. You can now sign in with your new password.
          </p>
          <Link
            to="/login"
            className="mt-6 inline-block rounded-lg bg-(--color-accent) px-6 py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90"
          >
            Sign in
          </Link>
        </motion.div>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout>
      <div className="mb-6 text-center">
        <div className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-(--color-accent) text-white font-bold text-lg">
          SF
        </div>
      </div>

      <h1 className="text-center text-2xl font-bold text-(--color-text-primary)">
        Choose a new password
      </h1>
      <p className="mt-2 text-center text-sm text-(--color-text-secondary)">
        Enter your new password below.
      </p>

      <form onSubmit={handleSubmit} className="mt-8 space-y-4">
        {error && (
          <div role="alert" className="rounded-md bg-(--color-negative)/10 px-4 py-3 text-sm text-(--color-negative)">
            {error}
          </div>
        )}
        <div>
          <label htmlFor="new-password" className="block text-sm font-medium text-(--color-text-primary)">
            New password
          </label>
          <input
            id="new-password"
            type="password"
            required
            autoComplete="new-password"
            autoFocus
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 block w-full rounded-lg border border-(--color-border) bg-(--color-bg-elevated) px-3 py-2.5 text-sm text-(--color-text-primary) placeholder:text-(--color-text-secondary)/50 focus:border-(--color-accent) focus:outline-none focus:ring-2 focus:ring-(--color-accent)/20"
            placeholder="Min. 8 characters"
          />
          <PasswordStrength password={password} />
        </div>
        <div>
          <label htmlFor="confirm-password" className="block text-sm font-medium text-(--color-text-primary)">
            Confirm password
          </label>
          <input
            id="confirm-password"
            type="password"
            required
            autoComplete="new-password"
            minLength={8}
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            className="mt-1 block w-full rounded-lg border border-(--color-border) bg-(--color-bg-elevated) px-3 py-2.5 text-sm text-(--color-text-primary) placeholder:text-(--color-text-secondary)/50 focus:border-(--color-accent) focus:outline-none focus:ring-2 focus:ring-(--color-accent)/20"
            placeholder="Confirm your password"
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg bg-(--color-accent) px-4 py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {loading ? 'Updating...' : 'Update Password'}
        </button>
      </form>
    </AuthLayout>
  )
}
