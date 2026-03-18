import { useState, useEffect, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useAuth } from '@/contexts/AuthContext'
import AuthLayout from '@/components/auth/AuthLayout'
import OtpInput from '@/components/auth/OtpInput'
import ResendTimer from '@/components/auth/ResendTimer'
import PasswordStrength from '@/components/auth/PasswordStrength'
import { getPasswordScore } from '@/components/auth/password-utils'
import { friendlyAuthError } from '@/lib/utils'
import { RiskDisclaimer } from '@/components/ui/RiskDisclaimer'

type Step = 'email' | 'verify' | 'profile'

const slideVariants = {
  enter: { opacity: 0, x: 40 },
  center: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: -40 },
}

export default function SignUpPage() {
  const [searchParams] = useSearchParams()
  const [step, setStep] = useState<Step>('email')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const { sendOtp, verifyOtp, completeProfile, hasCompletedProfile } = useAuth()
  const navigate = useNavigate()

  // Handle redirect from /auth/verify (OTP deep link from email)
  useEffect(() => {
    if (searchParams.get('verified') === 'true') {
      if (hasCompletedProfile()) {
        navigate('/')
        return
      }
      setStep('profile')
    }
  }, [searchParams, hasCompletedProfile, navigate])

  async function handleSendCode(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await sendOtp(email)
      setStep('verify')
    } catch (err) {
      setError(friendlyAuthError(err, 'Failed to send verification code'))
    } finally {
      setLoading(false)
    }
  }

  async function handleVerify(code: string) {
    setError(null)
    setLoading(true)
    try {
      const { isNewUser } = await verifyOtp(email, code)
      if (isNewUser) {
        setStep('profile')
      } else {
        navigate('/')
        return
      }
    } catch (err) {
      setError(friendlyAuthError(err, 'Invalid verification code'))
    } finally {
      setLoading(false)
    }
  }

  async function handleCompleteProfile(e: FormEvent) {
    e.preventDefault()
    if (getPasswordScore(password) < 3) {
      setError('Please choose a stronger password')
      return
    }
    setError(null)
    setLoading(true)
    try {
      await completeProfile(password)
      navigate('/')
    } catch (err) {
      setError(friendlyAuthError(err, 'Failed to create account'))
    } finally {
      setLoading(false)
    }
  }

  async function handleResend() {
    await sendOtp(email)
  }

  return (
    <AuthLayout>
      <AnimatePresence mode="wait">
        {/* Step 1: Email */}
        {step === 'email' && (
          <motion.div
            key="email"
            variants={slideVariants}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{ duration: 0.25, ease: 'easeInOut' }}
          >
            <div className="mb-6 text-center">
              <div className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-(--color-accent) text-white font-bold text-lg">
                SF
              </div>
            </div>

            <h1 className="text-center text-2xl font-bold text-(--color-text-primary)">
              Create your account
            </h1>
            <p className="mt-2 text-center text-sm text-(--color-text-secondary)">
              Get started with SignalForgeAI
            </p>

            {/* Step dots */}
            <div className="mt-5 flex justify-center gap-2">
              <div className="h-2 w-8 rounded-full bg-(--color-accent)" />
              <div className="h-2 w-8 rounded-full bg-(--color-border)" />
              <div className="h-2 w-8 rounded-full bg-(--color-border)" />
            </div>

            <form onSubmit={handleSendCode} className="mt-8 space-y-4">
              {error && (
                <div role="alert" className="rounded-md bg-(--color-negative)/10 px-4 py-3 text-sm text-(--color-negative)">
                  {error}
                </div>
              )}
              <div>
                <label htmlFor="signup-email" className="block text-sm font-medium text-(--color-text-primary)">
                  Email
                </label>
                <input
                  id="signup-email"
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
                {loading ? 'Sending code...' : 'Continue'}
              </button>
            </form>
            <p className="mt-4 text-center text-xs text-(--color-text-secondary)">
              By signing up, you agree to our{' '}
              <Link to="/terms" className="text-(--color-accent) hover:underline">Terms of Service</Link>
              {' '}and{' '}
              <Link to="/privacy" className="text-(--color-accent) hover:underline">Privacy Policy</Link>.
            </p>
            <p className="mt-6 text-center text-sm text-(--color-text-secondary)">
              Already have an account?{' '}
              <Link to="/login" className="font-medium text-(--color-accent) hover:underline">
                Sign in
              </Link>
            </p>

            <div className="mt-6">
              <RiskDisclaimer />
            </div>
          </motion.div>
        )}

        {/* Step 2: Verify OTP */}
        {step === 'verify' && (
          <motion.div
            key="verify"
            variants={slideVariants}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{ duration: 0.25, ease: 'easeInOut' }}
          >
            <h1 className="text-center text-2xl font-bold text-(--color-text-primary)">
              Check your email
            </h1>
            <p className="mt-2 text-center text-sm text-(--color-text-secondary)">
              We sent a 6-digit code to{' '}
              <span className="font-medium text-(--color-text-primary)">{email}</span>
            </p>

            {/* Step dots */}
            <div className="mt-5 flex justify-center gap-2">
              <div className="h-2 w-8 rounded-full bg-(--color-accent)" />
              <div className="h-2 w-8 rounded-full bg-(--color-accent)" />
              <div className="h-2 w-8 rounded-full bg-(--color-border)" />
            </div>

            <div className="mt-8 space-y-5">
              {error && (
                <div role="alert" className="rounded-md bg-(--color-negative)/10 px-4 py-3 text-sm text-(--color-negative)">
                  {error}
                </div>
              )}
              <OtpInput onComplete={handleVerify} disabled={loading} />
              {loading && (
                <p className="text-center text-sm text-(--color-text-secondary)">Verifying...</p>
              )}
              <ResendTimer onResend={handleResend} />
            </div>

            <button
              onClick={() => { setStep('email'); setError(null) }}
              className="mt-6 block w-full text-center text-sm font-medium text-(--color-text-secondary) hover:text-(--color-text-primary)"
            >
              &larr; Use a different email
            </button>
          </motion.div>
        )}

        {/* Step 3: Set Password */}
        {step === 'profile' && (
          <motion.div
            key="profile"
            variants={slideVariants}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{ duration: 0.25, ease: 'easeInOut' }}
          >
            <h1 className="text-center text-2xl font-bold text-(--color-text-primary)">
              Set your password
            </h1>
            <p className="mt-2 text-center text-sm text-(--color-text-secondary)">
              Choose a password for future sign-ins.
            </p>

            {/* Step dots */}
            <div className="mt-5 flex justify-center gap-2">
              <div className="h-2 w-8 rounded-full bg-(--color-accent)" />
              <div className="h-2 w-8 rounded-full bg-(--color-accent)" />
              <div className="h-2 w-8 rounded-full bg-(--color-accent)" />
            </div>

            <form onSubmit={handleCompleteProfile} className="mt-8 space-y-4">
              {error && (
                <div role="alert" className="rounded-md bg-(--color-negative)/10 px-4 py-3 text-sm text-(--color-negative)">
                  {error}
                </div>
              )}
              <div>
                <label htmlFor="signup-password" className="block text-sm font-medium text-(--color-text-primary)">
                  Password
                </label>
                <input
                  id="signup-password"
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
              <button
                type="submit"
                disabled={loading}
                className="w-full rounded-lg bg-(--color-accent) px-4 py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
              >
                {loading ? 'Creating account...' : 'Create Account'}
              </button>
            </form>
          </motion.div>
        )}
      </AnimatePresence>
    </AuthLayout>
  )
}
