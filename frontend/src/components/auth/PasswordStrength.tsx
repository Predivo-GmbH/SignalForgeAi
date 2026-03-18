import { getPasswordScore } from './password-utils'

export default function PasswordStrength({ password }: { password: string }) {
  if (!password) return null

  const score = getPasswordScore(password)
  const colors = [
    'bg-(--color-negative)',
    'bg-(--color-negative)',
    'bg-(--color-warning)',
    'bg-(--color-accent)',
    'bg-(--color-accent)',
    'bg-(--color-positive)',
  ]
  const labels = ['Weak', 'Weak', 'Fair', 'Good', 'Good', 'Strong']

  return (
    <div className="mt-2 space-y-2" role="status" aria-live="polite">
      <div className="flex gap-1">
        {Array.from({ length: 5 }, (_, i) => (
          <div
            key={i}
            className={`h-1 flex-1 rounded-full transition-colors ${
              i < score ? colors[score] : 'bg-(--color-border)'
            }`}
          />
        ))}
      </div>
      <p className="text-xs text-(--color-text-secondary)">
        Password strength:{' '}
        <span
          className={`font-medium ${
            score <= 1
              ? 'text-(--color-negative)'
              : score <= 2
                ? 'text-(--color-warning)'
                : score <= 4
                  ? 'text-(--color-accent)'
                  : 'text-(--color-positive)'
          }`}
        >
          {labels[score]}
        </span>
      </p>
    </div>
  )
}
