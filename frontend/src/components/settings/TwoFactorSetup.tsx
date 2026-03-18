import { ShieldCheck } from "lucide-react";

/**
 * TwoFactorSetup — no longer needed with Supabase OTP auth.
 * Shows a simple info card that OTP email verification is active.
 */
export function TwoFactorSetup() {
  return (
    <div className="flex items-center justify-between p-4 bg-(--color-bg-elevated) rounded-xl border border-(--color-border)">
      <div className="flex items-center gap-3">
        <ShieldCheck className="w-5 h-5 text-emerald-500" />
        <div>
          <p className="text-sm font-medium text-(--color-text-primary)">
            Email OTP Verification
          </p>
          <p className="text-xs text-(--color-text-secondary)">
            Every login is verified with a 6-digit code sent to your email
          </p>
        </div>
      </div>
      <span className="px-3 py-1.5 text-xs font-medium rounded-lg bg-emerald-500/10 text-emerald-400">
        Always Active
      </span>
    </div>
  );
}
