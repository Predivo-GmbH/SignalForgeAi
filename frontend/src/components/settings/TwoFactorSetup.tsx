import { useState } from "react";
import { Shield, ShieldCheck, Copy, Check } from "lucide-react";
import { Modal } from "@/components/ui/Modal";
import {
  useProfile,
  useSetup2FA,
  useVerify2FA,
  useDisable2FA,
} from "@/hooks/useProfile";

type SetupStep = "idle" | "qr" | "verify" | "backup" | "disable";

export function TwoFactorSetup() {
  const { data: profile } = useProfile();
  const setup2FA = useSetup2FA();
  const verify2FA = useVerify2FA();
  const disable2FA = useDisable2FA();

  const [step, setStep] = useState<SetupStep>("idle");
  const [qrData, setQrData] = useState<{ qr_code: string; secret: string } | null>(null);
  const [code, setCode] = useState("");
  const [backupCodes, setBackupCodes] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [password, setPassword] = useState("");
  const [copied, setCopied] = useState(false);

  const isEnabled = profile?.totp_enabled ?? false;

  const handleSetup = async () => {
    setError("");
    try {
      const data = await setup2FA.mutateAsync();
      setQrData(data);
      setStep("qr");
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Setup failed";
      setError(msg);
    }
  };

  const handleVerify = async () => {
    setError("");
    try {
      const data = await verify2FA.mutateAsync({ code });
      setBackupCodes(data.backup_codes);
      setCode("");
      setStep("backup");
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Verification failed";
      setError(msg);
    }
  };

  const handleDisable = async () => {
    setError("");
    try {
      await disable2FA.mutateAsync({ password, code });
      setStep("idle");
      setCode("");
      setPassword("");
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Failed to disable 2FA";
      setError(msg);
    }
  };

  const copyBackupCodes = () => {
    navigator.clipboard.writeText(backupCodes.join("\n"));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <>
      <div className="flex items-center justify-between p-4 bg-(--color-bg-elevated) rounded-xl border border-(--color-border)">
        <div className="flex items-center gap-3">
          {isEnabled ? (
            <ShieldCheck className="w-5 h-5 text-emerald-500" />
          ) : (
            <Shield className="w-5 h-5 text-(--color-text-secondary)" />
          )}
          <div>
            <p className="text-sm font-medium text-(--color-text-primary)">
              Two-Factor Authentication
            </p>
            <p className="text-xs text-(--color-text-secondary)">
              {isEnabled
                ? "Enabled — your account is protected"
                : "Add an extra layer of security to your account"}
            </p>
          </div>
        </div>
        {isEnabled ? (
          <button
            onClick={() => { setStep("disable"); setError(""); setCode(""); setPassword(""); }}
            className="px-3 py-1.5 text-xs font-medium rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-colors"
          >
            Disable
          </button>
        ) : (
          <button
            onClick={handleSetup}
            disabled={setup2FA.isPending}
            className="px-3 py-1.5 text-xs font-medium rounded-lg bg-(--color-accent)/10 text-(--color-accent) hover:bg-(--color-accent)/20 transition-colors disabled:opacity-50"
          >
            {setup2FA.isPending ? "Setting up..." : "Enable"}
          </button>
        )}
      </div>

      {/* QR Code Step */}
      <Modal open={step === "qr"} onClose={() => setStep("idle")} title="Set up authenticator">
        <div className="space-y-4">
          <p className="text-sm text-(--color-text-secondary)">
            Scan this QR code with your authenticator app (Google Authenticator, Authy, etc.)
          </p>
          {qrData && (
            <>
              <div className="flex justify-center p-4 bg-white rounded-lg">
                <img src={qrData.qr_code} alt="QR Code" className="w-48 h-48" />
              </div>
              <div className="p-3 bg-(--color-bg-elevated) rounded-lg">
                <p className="text-xs text-(--color-text-secondary) mb-1">
                  Can't scan? Enter this code manually:
                </p>
                <code className="text-xs font-mono text-(--color-text-primary) break-all">
                  {qrData.secret}
                </code>
              </div>
            </>
          )}
          <button
            onClick={() => { setStep("verify"); setError(""); }}
            className="w-full py-2 text-sm font-medium rounded-lg bg-(--color-accent) text-white hover:bg-(--color-accent)/90 transition-colors"
          >
            I've scanned the code
          </button>
        </div>
      </Modal>

      {/* Verify Code Step */}
      <Modal open={step === "verify"} onClose={() => setStep("idle")} title="Verify setup">
        <div className="space-y-4">
          <p className="text-sm text-(--color-text-secondary)">
            Enter the 6-digit code from your authenticator app to confirm setup.
          </p>
          <input
            type="text"
            inputMode="numeric"
            maxLength={6}
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
            placeholder="000000"
            className="w-full px-4 py-3 text-center text-2xl font-mono tracking-[0.5em] bg-(--color-bg-elevated) border border-(--color-border) rounded-lg text-(--color-text-primary) placeholder:text-(--color-text-secondary)/30 focus:outline-none focus:border-(--color-accent)"
          />
          {error && <p className="text-xs text-red-400">{error}</p>}
          <button
            onClick={handleVerify}
            disabled={code.length !== 6 || verify2FA.isPending}
            className="w-full py-2 text-sm font-medium rounded-lg bg-(--color-accent) text-white hover:bg-(--color-accent)/90 transition-colors disabled:opacity-50"
          >
            {verify2FA.isPending ? "Verifying..." : "Verify & Enable"}
          </button>
        </div>
      </Modal>

      {/* Backup Codes Step */}
      <Modal
        open={step === "backup"}
        onClose={() => setStep("idle")}
        title="Save your backup codes"
      >
        <div className="space-y-4">
          <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg">
            <p className="text-xs text-amber-400 font-medium">
              Save these codes in a secure place. Each code can only be used once.
              You won't be able to see them again.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-2 p-4 bg-(--color-bg-elevated) rounded-lg">
            {backupCodes.map((c) => (
              <code key={c} className="text-sm font-mono text-(--color-text-primary) text-center">
                {c}
              </code>
            ))}
          </div>
          <button
            onClick={copyBackupCodes}
            className="w-full flex items-center justify-center gap-2 py-2 text-sm font-medium rounded-lg bg-(--color-bg-elevated) border border-(--color-border) text-(--color-text-primary) hover:bg-(--color-bg-surface) transition-colors"
          >
            {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
            {copied ? "Copied!" : "Copy all codes"}
          </button>
          <button
            onClick={() => setStep("idle")}
            className="w-full py-2 text-sm font-medium rounded-lg bg-(--color-accent) text-white hover:bg-(--color-accent)/90 transition-colors"
          >
            I've saved my codes
          </button>
        </div>
      </Modal>

      {/* Disable 2FA Step */}
      <Modal open={step === "disable"} onClose={() => setStep("idle")} title="Disable 2FA">
        <div className="space-y-4">
          <p className="text-sm text-(--color-text-secondary)">
            Enter your password and a 2FA code to disable two-factor authentication.
          </p>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Your password"
            className="w-full px-3 py-2 text-sm bg-(--color-bg-elevated) border border-(--color-border) rounded-lg text-(--color-text-primary) placeholder:text-(--color-text-secondary)/50 focus:outline-none focus:border-(--color-accent)"
          />
          <input
            type="text"
            inputMode="numeric"
            maxLength={9}
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="2FA code or backup code"
            className="w-full px-3 py-2 text-sm bg-(--color-bg-elevated) border border-(--color-border) rounded-lg text-(--color-text-primary) placeholder:text-(--color-text-secondary)/50 focus:outline-none focus:border-(--color-accent)"
          />
          {error && <p className="text-xs text-red-400">{error}</p>}
          <button
            onClick={handleDisable}
            disabled={!password || !code || disable2FA.isPending}
            className="w-full py-2 text-sm font-medium rounded-lg bg-red-500 text-white hover:bg-red-600 transition-colors disabled:opacity-50"
          >
            {disable2FA.isPending ? "Disabling..." : "Disable 2FA"}
          </button>
        </div>
      </Modal>
    </>
  );
}
