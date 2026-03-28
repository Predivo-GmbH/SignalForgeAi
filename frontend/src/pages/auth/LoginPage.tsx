import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useAuth } from '@/contexts/AuthContext'
import { usePageTitle } from '@/hooks/usePageTitle'
import AuthLayout from '@/components/auth/AuthLayout'
import OtpInput from '@/components/auth/OtpInput'
import ResendTimer from '@/components/auth/ResendTimer'
import { friendlyAuthError } from '@/lib/utils'
import { RiskDisclaimer } from '@/components/ui/RiskDisclaimer'

type Tab = 'password' | 'code'
type CodeStep = 'email' | 'verify'

const fadeVariants = {
  enter: { opacity: 0, y: 12 },
  center: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -12 },
}

export default function LoginPage() {
  usePageTitle('Log In')
  const [tab, setTab] = useState<Tab>('password')
  const [codeStep, setCodeStep] = useState<CodeStep>('email')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const { signInWithPassword, sendLoginOtp, verifyOtp } = useAuth()
  const navigate = useNavigate()

  async function handlePasswordLogin(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await signInWithPassword(email, password)
      navigate('/')
    } catch (err) {
      setError(friendlyAuthError(err, 'Login failed'))
    } finally {
      setLoading(false)
    }
  }

  async function handleSendCode(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await sendLoginOtp(email)
      setCodeStep('verify')
    } catch (err) {
      setError(friendlyAuthError(err, 'Failed to send login code'))
    } finally {
      setLoading(false)
    }
  }

  async function handleVerifyCode(code: string) {
    setError(null)
    setLoading(true)
    try {
      await verifyOtp(email, code)
      navigate('/')
    } catch (err) {
      setError(friendlyAuthError(err, 'Invalid verification code'))
    } finally {
      setLoading(false)
    }
  }

  async function handleResend() {
    await sendLoginOtp(email)
  }

  function switchTab(t: Tab) {
    setTab(t)
    setError(null)
    setCodeStep('email')
  }

  return (
    <AuthLayout>
      <div className="mb-6 text-center">
        <div className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-(--color-accent) text-white font-bold text-lg">
          SF
        </div>
      </div>

      <h1 className="text-center text-2xl font-bold text-(--color-text-primary)">
        Sign in to SignalForgeAI
      </h1>

      {/* Tabs */}
      <div className="mt-6 flex rounded-lg border border-(--color-border) bg-(--color-bg-elevated) p-1">
        <button
          onClick={() => switchTab('password')}
          className={`flex-1 rounded-md py-2 min-h-[44px] text-sm font-medium transition-all ${
            tab === 'password'
              ? 'bg-(--color-bg-surface) text-(--color-text-primary) shadow-sm'
              : 'text-(--color-text-secondary) hover:text-(--color-text-primary)'
          }`}
        >
          Password
        </button>
        <button
          onClick={() => switchTab('code')}
          className={`flex-1 rounded-md py-2 min-h-[44px] text-sm font-medium transition-all ${
            tab === 'code'
              ? 'bg-(--color-bg-surface) text-(--color-text-primary) shadow-sm'
              : 'text-(--color-text-secondary) hover:text-(--color-text-primary)'
          }`}
        >
          Email Code
        </button>
      </div>

      <AnimatePresence mode="wait">
        {/* Password Tab */}
        {tab === 'password' && (
          <motion.form
            key="password"
            variants={fadeVariants}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{ duration: 0.2 }}
            onSubmit={handlePasswordLogin}
            className="mt-6 space-y-4"
          >
            {error && (
              <div role="alert" className="rounded-md bg-(--color-negative)/10 px-4 py-3 text-sm text-(--color-negative)">
                {error}
              </div>
            )}
            <div>
              <label htmlFor="login-email" className="block text-sm font-medium text-(--color-text-primary)">
                Email
              </label>
              <input
                id="login-email"
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-(--color-border) bg-(--color-bg-elevated) px-3 py-2.5 min-h-[44px] text-base sm:text-sm text-(--color-text-primary) placeholder:text-(--color-text-secondary)/50 focus:border-(--color-accent) focus:outline-none focus:ring-2 focus:ring-(--color-accent)/20"
                placeholder="you@example.com"
              />
            </div>
            <div>
              <div className="flex items-center justify-between">
                <label htmlFor="login-password" className="block text-sm font-medium text-(--color-text-primary)">
                  Password
                </label>
                <Link
                  to="/forgot-password"
                  className="text-sm font-medium text-(--color-accent) hover:underline"
                >
                  Forgot password?
                </Link>
              </div>
              <input
                id="login-password"
                type="password"
                required
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-(--color-border) bg-(--color-bg-elevated) px-3 py-2.5 min-h-[44px] text-base sm:text-sm text-(--color-text-primary) placeholder:text-(--color-text-secondary)/50 focus:border-(--color-accent) focus:outline-none focus:ring-2 focus:ring-(--color-accent)/20"
                placeholder="Enter your password"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-lg bg-(--color-accent) px-4 py-2.5 min-h-[44px] text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
            >
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </motion.form>
        )}

        {/* Email Code Tab */}
        {tab === 'code' && codeStep === 'email' && (
          <motion.form
            key="code-email"
            variants={fadeVariants}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{ duration: 0.2 }}
            onSubmit={handleSendCode}
            className="mt-6 space-y-4"
          >
            {error && (
              <div role="alert" className="rounded-md bg-(--color-negative)/10 px-4 py-3 text-sm text-(--color-negative)">
                {error}
              </div>
            )}
            <p className="text-center text-sm text-(--color-text-secondary)">
              We'll send a sign-in code to your email if you have an account.
            </p>
            <div>
              <label htmlFor="code-email" className="block text-sm font-medium text-(--color-text-primary)">
                Email
              </label>
              <input
                id="code-email"
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-(--color-border) bg-(--color-bg-elevated) px-3 py-2.5 min-h-[44px] text-base sm:text-sm text-(--color-text-primary) placeholder:text-(--color-text-secondary)/50 focus:border-(--color-accent) focus:outline-none focus:ring-2 focus:ring-(--color-accent)/20"
                placeholder="you@example.com"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-lg bg-(--color-accent) px-4 py-2.5 min-h-[44px] text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
            >
              {loading ? 'Sending code...' : 'Send Sign-In Code'}
            </button>
          </motion.form>
        )}

        {tab === 'code' && codeStep === 'verify' && (
          <motion.div
            key="code-verify"
            variants={fadeVariants}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{ duration: 0.2 }}
            className="mt-6 space-y-5"
          >
            <p className="text-center text-sm text-(--color-text-secondary)">
              Enter the 6-digit code sent to{' '}
              <span className="font-medium text-(--color-text-primary)">{email}</span>
            </p>
            {error && (
              <div role="alert" className="rounded-md bg-(--color-negative)/10 px-4 py-3 text-sm text-(--color-negative)">
                {error}
              </div>
            )}
            <OtpInput onComplete={handleVerifyCode} disabled={loading} />
            {loading && <p className="text-center text-sm text-(--color-text-secondary)">Verifying...</p>}
            <ResendTimer onResend={handleResend} />
            <p className="text-center text-xs text-(--color-text-secondary)">
              Didn't receive a code? Make sure you have an account or{' '}
              <Link to="/signup" className="text-(--color-accent) hover:underline">sign up</Link>.
            </p>
            <button
              onClick={() => { setCodeStep('email'); setError(null) }}
              className="block w-full min-h-[44px] text-center text-sm font-medium text-(--color-text-secondary) hover:text-(--color-text-primary)"
            >
              &larr; Use a different email
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      <p className="mt-6 text-center text-sm text-(--color-text-secondary)">
        Don&apos;t have an account?{' '}
        <Link to="/signup" className="font-medium text-(--color-accent) hover:underline">
          Sign up
        </Link>
      </p>

      <div className="mt-6">
        <RiskDisclaimer />
      </div>
    </AuthLayout>
  )
}

export { LoginPage }
