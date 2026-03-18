import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useAuth } from '@/contexts/AuthContext'
import AuthLayout from '@/components/auth/AuthLayout'
import { Mail } from 'lucide-react'

type Step = 'form' | 'sent'

export default function ForgotPasswordPage() {
  const [step, setStep] = useState<Step>('form')
  const [email, setEmail] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const { resetPassword } = useAuth()

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await resetPassword(email)
      setStep('sent')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send reset email')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout>
      <AnimatePresence mode="wait">
        {step === 'form' && (
          <motion.div
            key="form"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            transition={{ duration: 0.2 }}
          >
            <div className="mb-6 text-center">
              <div className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-(--color-accent) text-white font-bold text-lg">
                SF
              </div>
            </div>

            <h1 className="text-center text-2xl font-bold text-(--color-text-primary)">
              Reset your password
            </h1>
            <p className="mt-2 text-center text-sm text-(--color-text-secondary)">
              Enter your email and we'll send you a link to reset your password.
            </p>

            <form onSubmit={handleSubmit} className="mt-8 space-y-4">
              {error && (
                <div role="alert" className="rounded-md bg-(--color-negative)/10 px-4 py-3 text-sm text-(--color-negative)">
                  {error}
                </div>
              )}
              <div>
                <label htmlFor="reset-email" className="block text-sm font-medium text-(--color-text-primary)">
                  Email
                </label>
                <input
                  id="reset-email"
                  type="email"
                  required
                  autoComplete="email"
                  autoFocus
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="mt-1 block w-full rounded-lg border border-(--color-border) bg-(--color-bg-elevated) px-3 py-2.5 text-sm text-(--color-text-primary) placeholder:text-(--color-text-secondary)/50 focus:border-(--color-accent) focus:outline-none focus:ring-2 focus:ring-(--color-accent)/20"
                  placeholder="you@example.com"
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full rounded-lg bg-(--color-accent) px-4 py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
              >
                {loading ? 'Sending...' : 'Send Reset Link'}
              </button>
            </form>

            <p className="mt-6 text-center text-sm text-(--color-text-secondary)">
              <Link to="/login" className="font-medium text-(--color-accent) hover:underline">
                &larr; Back to sign in
              </Link>
            </p>
          </motion.div>
        )}

        {step === 'sent' && (
          <motion.div
            key="sent"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2 }}
            className="text-center"
          >
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-(--color-accent)/10">
              <Mail className="h-7 w-7 text-(--color-accent)" />
            </div>
            <h1 className="mt-5 text-2xl font-bold text-(--color-text-primary)">Check your email</h1>
            <p className="mt-2 text-sm text-(--color-text-secondary)">
              We sent a password reset link to{' '}
              <span className="font-medium text-(--color-text-primary)">{email}</span>. Click the link in the
              email to choose a new password.
            </p>
            <p className="mt-4 text-xs text-(--color-text-secondary)">
              Didn't receive the email? Check your spam folder or{' '}
              <button
                onClick={() => setStep('form')}
                className="font-medium text-(--color-accent) hover:underline"
              >
                try again
              </button>
              .
            </p>
            <Link
              to="/login"
              className="mt-8 inline-block text-sm font-medium text-(--color-accent) hover:underline"
            >
              &larr; Back to sign in
            </Link>
          </motion.div>
        )}
      </AnimatePresence>
    </AuthLayout>
  )
}
