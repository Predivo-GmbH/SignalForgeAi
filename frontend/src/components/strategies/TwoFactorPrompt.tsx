import { useState } from "react";
import { Modal } from "@/components/ui/Modal";

interface TwoFactorPromptProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (code: string) => void;
  isPending: boolean;
  error?: string;
}

export function TwoFactorPrompt({
  open,
  onClose,
  onSubmit,
  isPending,
  error,
}: TwoFactorPromptProps) {
  const [code, setCode] = useState("");

  const handleSubmit = () => {
    if (code.length >= 6) onSubmit(code);
  };

  return (
    <Modal open={open} onClose={onClose} title="Verify identity">
      <div className="space-y-4">
        <p className="text-sm text-(--color-text-secondary)">
          Enter your 2FA code to activate live trading.
        </p>
        <input
          type="text"
          inputMode="numeric"
          maxLength={9}
          value={code}
          onChange={(e) => setCode(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") handleSubmit(); }}
          placeholder="6-digit code or backup code"
          autoFocus
          className="w-full px-4 py-3 text-center text-2xl font-mono tracking-[0.5em] bg-(--color-bg-elevated) border border-(--color-border) rounded-lg text-(--color-text-primary) placeholder:text-(--color-text-secondary)/30 placeholder:text-sm placeholder:tracking-normal focus:outline-none focus:border-(--color-accent)"
        />
        {error && <p className="text-xs text-red-400">{error}</p>}
        <button
          onClick={handleSubmit}
          disabled={code.length < 6 || isPending}
          className="w-full py-2 text-sm font-medium rounded-lg bg-(--color-accent) text-white hover:bg-(--color-accent)/90 transition-colors disabled:opacity-50"
        >
          {isPending ? "Verifying..." : "Activate"}
        </button>
      </div>
    </Modal>
  );
}
