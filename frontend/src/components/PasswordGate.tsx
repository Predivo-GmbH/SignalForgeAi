import { useState } from "react";

const GATE_PASSWORD = "signalforge2026";
const STORAGE_KEY = "sf-unlocked";

export function PasswordGate({ children }: { children: React.ReactNode }) {
  const [unlocked, setUnlocked] = useState(
    () => sessionStorage.getItem(STORAGE_KEY) === "true"
  );
  const [input, setInput] = useState("");
  const [error, setError] = useState(false);

  if (unlocked) return <>{children}</>;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input === GATE_PASSWORD) {
      sessionStorage.setItem(STORAGE_KEY, "true");
      setUnlocked(true);
    } else {
      setError(true);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-(--color-bg-base)">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm rounded-xl bg-(--color-bg-surface) p-8 shadow-lg border border-(--color-border)"
      >
        <h1 className="mb-2 text-xl font-bold text-(--color-text-primary)">
          SignalForgeAI
        </h1>
        <p className="mb-6 text-sm text-(--color-text-secondary)">
          Enter password to continue
        </p>
        <input
          type="password"
          value={input}
          onChange={(e) => {
            setInput(e.target.value);
            setError(false);
          }}
          placeholder="Password"
          className="mb-4 w-full rounded-lg border border-(--color-border) bg-(--color-bg-elevated) px-4 py-3 text-(--color-text-primary) outline-none focus:border-(--color-accent)"
        />
        {error && (
          <p className="mb-4 text-sm text-(--color-negative)">Wrong password</p>
        )}
        <button
          type="submit"
          className="w-full rounded-lg bg-(--color-accent) py-3 font-medium text-white hover:opacity-90 transition-opacity"
        >
          Enter
        </button>
      </form>
    </div>
  );
}
