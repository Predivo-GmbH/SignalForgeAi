import { useState, useEffect, useCallback } from 'react'

interface ResendTimerProps {
  onResend: () => Promise<void>
  cooldownSeconds?: number
}

export default function ResendTimer({ onResend, cooldownSeconds = 60 }: ResendTimerProps) {
  const [seconds, setSeconds] = useState(cooldownSeconds)
  const [sending, setSending] = useState(false)

  useEffect(() => {
    if (seconds <= 0) return
    const timer = setInterval(() => setSeconds((s) => s - 1), 1000)
    return () => clearInterval(timer)
  }, [seconds])

  const handleResend = useCallback(async () => {
    setSending(true)
    try {
      await onResend()
      setSeconds(cooldownSeconds)
    } finally {
      setSending(false)
    }
  }, [onResend, cooldownSeconds])

  if (seconds > 0) {
    return (
      <p className="text-center text-sm text-(--color-text-secondary)">
        Resend code in{' '}
        <span className="font-medium text-(--color-text-primary)">{seconds}s</span>
      </p>
    )
  }

  return (
    <button
      onClick={handleResend}
      disabled={sending}
      className="mx-auto block text-sm font-medium text-(--color-accent) transition-colors hover:opacity-80 disabled:opacity-50"
    >
      {sending ? 'Sending...' : 'Resend code'}
    </button>
  )
}
