import { useRef, useCallback, type ClipboardEvent, type KeyboardEvent } from 'react'

interface OtpInputProps {
  length?: number
  onComplete: (code: string) => void
  disabled?: boolean
}

export default function OtpInput({ length = 6, onComplete, disabled }: OtpInputProps) {
  const inputsRef = useRef<(HTMLInputElement | null)[]>([])

  const focusInput = useCallback((index: number) => {
    const el = inputsRef.current[index]
    if (el) {
      el.focus()
      el.select()
    }
  }, [])

  const getCode = useCallback(() => {
    return inputsRef.current.map((el) => el?.value ?? '').join('')
  }, [])

  const handleChange = useCallback(
    (index: number, value: string) => {
      const digit = value.replace(/\D/g, '').slice(-1)
      const el = inputsRef.current[index]
      if (el) el.value = digit

      if (digit && index < length - 1) {
        focusInput(index + 1)
      }

      const code = getCode()
      if (code.length === length) {
        onComplete(code)
      }
    },
    [length, onComplete, focusInput, getCode],
  )

  const handleKeyDown = useCallback(
    (index: number, e: KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Backspace') {
        const el = inputsRef.current[index]
        if (el && !el.value && index > 0) {
          e.preventDefault()
          const prev = inputsRef.current[index - 1]
          if (prev) {
            prev.value = ''
            focusInput(index - 1)
          }
        }
      } else if (e.key === 'ArrowLeft' && index > 0) {
        e.preventDefault()
        focusInput(index - 1)
      } else if (e.key === 'ArrowRight' && index < length - 1) {
        e.preventDefault()
        focusInput(index + 1)
      }
    },
    [length, focusInput],
  )

  const handlePaste = useCallback(
    (e: ClipboardEvent<HTMLInputElement>) => {
      e.preventDefault()
      const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, length)
      for (let i = 0; i < length; i++) {
        const el = inputsRef.current[i]
        if (el) el.value = pasted[i] ?? ''
      }
      const lastFilled = Math.min(pasted.length, length) - 1
      if (lastFilled >= 0) focusInput(lastFilled)

      if (pasted.length === length) {
        onComplete(pasted)
      }
    },
    [length, onComplete, focusInput],
  )

  return (
    <div className="flex justify-center gap-2.5" role="group" aria-label="Verification code">
      {Array.from({ length }, (_, i) => (
        <input
          key={i}
          ref={(el) => { inputsRef.current[i] = el }}
          type="text"
          inputMode="numeric"
          pattern="[0-9]"
          maxLength={1}
          disabled={disabled}
          autoFocus={i === 0}
          autoComplete="one-time-code"
          aria-label={`Digit ${i + 1} of ${length}`}
          onChange={(e) => handleChange(i, e.target.value)}
          onKeyDown={(e) => handleKeyDown(i, e)}
          onPaste={i === 0 ? handlePaste : undefined}
          className="h-12 sm:h-14 w-10 sm:w-12 min-h-[44px] min-w-[44px] rounded-lg border-2 border-(--color-border) bg-(--color-bg-surface) text-center text-2xl font-bold text-(--color-text-primary) transition-all focus:border-(--color-accent) focus:outline-none focus:ring-2 focus:ring-(--color-accent)/20 disabled:opacity-50"
        />
      ))}
    </div>
  )
}
