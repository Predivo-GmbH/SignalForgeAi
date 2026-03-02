import { useAuth } from "./auth";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

let isRefreshing = false;
let refreshQueue: Array<{
  resolve: (value: boolean) => void;
  reject: (reason?: unknown) => void;
}> = [];

function processQueue(success: boolean): void {
  refreshQueue.forEach(({ resolve }) => resolve(success));
  refreshQueue = [];
}

async function refreshAccessToken(): Promise<boolean> {
  const { refreshToken, setTokens, logout } = useAuth.getState();
  if (!refreshToken) {
    logout();
    return false;
  }

  // If already refreshing, queue this request and wait for the result
  if (isRefreshing) {
    return new Promise<boolean>((resolve, reject) => {
      refreshQueue.push({ resolve, reject });
    });
  }

  isRefreshing = true;
  try {
    const res = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) {
      processQueue(false);
      logout();
      return false;
    }
    const data = await res.json();
    setTokens(data.access_token, data.refresh_token ?? refreshToken);
    processQueue(true);
    return true;
  } catch {
    processQueue(false);
    useAuth.getState().logout();
    return false;
  } finally {
    isRefreshing = false;
  }
}

async function request<T>(path: string, options: RequestInit = {}, _retry = false): Promise<T> {
  const { accessToken } = useAuth.getState();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options.headers as Record<string, string>) || {}),
  };
  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`;
  }
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (res.status === 401 && !_retry) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      return request<T>(path, options, true);
    }
    throw new Error("Unauthorized");
  }
  if (res.status === 401) {
    useAuth.getState().logout();
    throw new Error("Unauthorized");
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  get: <T>(path: string, opts?: { signal?: AbortSignal }) =>
    request<T>(path, opts),
  post: <T>(path: string, body?: unknown, opts?: { signal?: AbortSignal }) =>
    request<T>(path, {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
      ...opts,
    }),
  put: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PUT", body: JSON.stringify(body) }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};
