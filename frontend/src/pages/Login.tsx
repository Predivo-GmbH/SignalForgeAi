import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { RiskDisclaimer } from "@/components/ui/RiskDisclaimer";

interface LoginApiResponse {
  access_token?: string;
  refresh_token?: string;
  requires_2fa?: boolean;
  partial_token?: string;
}

export function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [twoFaStep, setTwoFaStep] = useState(false);
  const [partialToken, setPartialToken] = useState("");
  const [totpCode, setTotpCode] = useState("");
  const navigate = useNavigate();

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const data = await api.post<LoginApiResponse>("/auth/login", {
        email,
        password,
      });

      if (data.requires_2fa && data.partial_token) {
        setPartialToken(data.partial_token);
        setTwoFaStep(true);
      } else if (data.access_token && data.refresh_token) {
        useAuth.getState().setTokens(data.access_token, data.refresh_token);
        navigate("/");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  async function handle2FASubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const data = await api.post<{ access_token: string; refresh_token: string }>(
        "/auth/2fa/login",
        { partial_token: partialToken, code: totpCode },
      );
      useAuth.getState().setTokens(data.access_token, data.refresh_token);
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invalid code");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-(--color-bg-base)">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="mb-8 text-center">
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-(--color-accent) text-white font-bold text-lg">
            SF
          </div>
          <h1 className="mt-4 text-2xl font-bold text-(--color-text-primary)">
            {twoFaStep ? "Two-factor authentication" : "Welcome back"}
          </h1>
          <p className="mt-1 text-sm text-(--color-text-secondary)">
            {twoFaStep
              ? "Enter the code from your authenticator app"
              : "Sign in to your SignalForge account"}
          </p>
        </div>

        {/* 2FA step */}
        {twoFaStep ? (
          <form
            onSubmit={handle2FASubmit}
            className="rounded-xl bg-(--color-bg-surface) p-8 border border-(--color-border) shadow-sm"
          >
            {error && (
              <div className="mb-4 rounded-lg bg-(--color-negative)/10 px-4 py-3 text-sm text-(--color-negative)">
                {error}
              </div>
            )}

            <div className="mb-6">
              <label
                htmlFor="totp-code"
                className="mb-1.5 block text-sm font-medium text-(--color-text-secondary)"
              >
                Authentication Code
              </label>
              <input
                id="totp-code"
                type="text"
                inputMode="numeric"
                maxLength={9}
                value={totpCode}
                onChange={(e) => setTotpCode(e.target.value)}
                placeholder="Enter 6-digit code"
                autoFocus
                required
                className="w-full rounded-lg border border-(--color-border) bg-(--color-bg-elevated) px-4 py-3 text-center text-2xl font-mono tracking-[0.3em] text-(--color-text-primary) outline-none transition-colors placeholder:text-(--color-text-secondary)/50 placeholder:text-sm placeholder:tracking-normal focus:border-(--color-accent)"
              />
              <p className="mt-2 text-xs text-(--color-text-secondary)">
                You can also use a backup code
              </p>
            </div>

            <button
              type="submit"
              disabled={loading || totpCode.length < 6}
              className="w-full rounded-lg bg-(--color-accent) py-3 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
            >
              {loading ? "Verifying..." : "Verify"}
            </button>

            <button
              type="button"
              onClick={() => {
                setTwoFaStep(false);
                setTotpCode("");
                setPartialToken("");
                setError("");
              }}
              className="mt-4 w-full text-center text-sm text-(--color-text-secondary) hover:text-(--color-text-primary) transition-colors"
            >
              Back to login
            </button>
          </form>
        ) : (
          /* Normal login form */
          <form
            onSubmit={handleSubmit}
            className="rounded-xl bg-(--color-bg-surface) p-8 border border-(--color-border) shadow-sm"
          >
            {error && (
              <div className="mb-4 rounded-lg bg-(--color-negative)/10 px-4 py-3 text-sm text-(--color-negative)">
                {error}
              </div>
            )}

            <div className="mb-4">
              <label
                htmlFor="email"
                className="mb-1.5 block text-sm font-medium text-(--color-text-secondary)"
              >
                Email
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Email"
                required
                className="w-full rounded-lg border border-(--color-border) bg-(--color-bg-elevated) px-4 py-3 text-sm text-(--color-text-primary) outline-none transition-colors placeholder:text-(--color-text-secondary)/50 focus:border-(--color-accent)"
              />
            </div>

            <div className="mb-6">
              <label
                htmlFor="password"
                className="mb-1.5 block text-sm font-medium text-(--color-text-secondary)"
              >
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Password"
                required
                minLength={1}
                className="w-full rounded-lg border border-(--color-border) bg-(--color-bg-elevated) px-4 py-3 text-sm text-(--color-text-primary) outline-none transition-colors placeholder:text-(--color-text-secondary)/50 focus:border-(--color-accent)"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-lg bg-(--color-accent) py-3 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
            >
              {loading ? "Signing in..." : "Sign In"}
            </button>

            <p className="mt-6 text-center text-sm text-(--color-text-secondary)">
              Don't have an account?{" "}
              <Link
                to="/register"
                className="font-medium text-(--color-accent) hover:underline"
              >
                Create account
              </Link>
            </p>
          </form>
        )}

        <div className="mt-6">
          <RiskDisclaimer />
        </div>
      </div>
    </div>
  );
}
