import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

interface LoginResponse {
  access_token: string;
  refresh_token: string;
}

export function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const data = await api.post<LoginResponse>("/auth/login", {
        email,
        password,
      });
      useAuth.getState().setTokens(data.access_token, data.refresh_token);
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
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
            Welcome back
          </h1>
          <p className="mt-1 text-sm text-(--color-text-secondary)">
            Sign in to your SignalForge account
          </p>
        </div>

        {/* Form card */}
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
      </div>
    </div>
  );
}
