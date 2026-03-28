import { useState, type ReactNode } from 'react'

const GATE_PASSWORD_HASH = '3bd8037a8ed38a35825983767f94e6cf3b18c3deee1601daee71faec0d83565f'
const STORAGE_KEY = 'signalforge-unlocked'

async function sha256(message: string): Promise<string> {
  const msgBuffer = new TextEncoder().encode(message)
  const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer)
  const hashArray = Array.from(new Uint8Array(hashBuffer))
  return hashArray.map((b) => b.toString(16).padStart(2, '0')).join('')
}

export function PasswordGate({ children }: { children: ReactNode }) {
  const [unlocked, setUnlocked] = useState(
    () => sessionStorage.getItem(STORAGE_KEY) === 'true'
  )
  const [password, setPassword] = useState('')
  const [error, setError] = useState(false)

  if (unlocked) return <>{children}</>

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const inputHash = await sha256(password)
    if (inputHash === GATE_PASSWORD_HASH) {
      sessionStorage.setItem(STORAGE_KEY, 'true')
      setUnlocked(true)
    } else {
      setError(true)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-(--color-bg-base) p-4">
      <div className="w-full max-w-sm rounded-xl border border-(--color-border) bg-(--color-bg-surface) p-5 sm:p-8">
        <div className="mb-6 text-center">
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-(--color-accent) text-white font-bold text-lg">
            SF
          </div>
        </div>
        <h1 className="text-center text-2xl font-bold text-(--color-text-primary)">
          SignalForge AI
        </h1>
        <p className="mt-2 text-center text-sm text-(--color-text-secondary)">
          This app is in private beta.
        </p>
        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <input
            type="password"
            placeholder="Enter access code"
            aria-label="Access code"
            value={password}
            onChange={(e) => { setPassword(e.target.value); setError(false) }}
            autoFocus
            className="block w-full rounded-lg border border-(--color-border) bg-(--color-bg-elevated) px-3 py-2.5 min-h-[44px] text-base sm:text-sm text-(--color-text-primary) placeholder:text-(--color-text-secondary)/50 focus:border-(--color-accent) focus:outline-none focus:ring-2 focus:ring-(--color-accent)/20"
          />
          {error && (
            <p className="text-sm text-(--color-negative)" role="alert">Incorrect access code.</p>
          )}
          <button
            type="submit"
            className="w-full rounded-lg bg-(--color-accent) px-4 py-2.5 min-h-[44px] text-sm font-medium text-white transition-opacity hover:opacity-90"
          >
            Enter
          </button>
        </form>
      </div>
    </div>
  )
}
