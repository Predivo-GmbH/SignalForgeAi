import { useAuth } from "@/lib/auth";
import { queryClient } from "@/lib/query";

type MessageHandler = (data: unknown) => void;

export class WebSocketManager {
  private baseUrl: string;
  private connections = new Map<string, WebSocket>();
  private handlers = new Map<string, Set<MessageHandler>>();
  private reconnectTimers = new Map<string, ReturnType<typeof setTimeout>>();
  private retryCount = new Map<string, number>();
  private isReconnecting = new Set<string>();
  private readonly MAX_RETRIES = 5;

  constructor(baseUrl?: string) {
    this.baseUrl =
      baseUrl || (import.meta.env.VITE_WS_URL as string) || "ws://localhost:8000";
  }

  getUrl(channel: string, token?: string): string {
    const url = `${this.baseUrl}/ws/${channel}`;
    return token ? `${url}?token=${token}` : url;
  }

  connect(channel: string, token?: string): void {
    if (this.connections.has(channel)) return;
    const url = this.getUrl(channel, token);
    const ws = new WebSocket(url);
    const wasReconnecting = this.isReconnecting.has(channel);
    ws.onopen = () => {
      this.retryCount.set(channel, 0);
      this.isReconnecting.delete(channel);
      // After a successful reconnect, invalidate relevant React Query caches
      // so components refetch fresh data
      if (wasReconnecting) {
        queryClient.invalidateQueries({ queryKey: ["signals"] });
        queryClient.invalidateQueries({ queryKey: ["trades"] });
        queryClient.invalidateQueries({ queryKey: ["positions"] });
        queryClient.invalidateQueries({ queryKey: ["prices"] });
      }
    };
    ws.onmessage = (event: MessageEvent) => {
      let data: unknown;
      try {
        data = JSON.parse(event.data as string);
      } catch (err) {
        console.warn(`[ws] malformed JSON on channel "${channel}":`, event.data, err);
        return;
      }
      this.handlers.get(channel)?.forEach((fn) => fn(data));
    };
    ws.onerror = (event: Event) => {
      console.error(`[ws] error on channel "${channel}"`, event);
    };
    ws.onclose = () => {
      this.connections.delete(channel);
      const count = (this.retryCount.get(channel) ?? 0) + 1;
      this.retryCount.set(channel, count);
      if (count > this.MAX_RETRIES) {
        console.warn(`[ws] channel "${channel}" exceeded ${this.MAX_RETRIES} retries, giving up`);
        this.isReconnecting.delete(channel);
        return;
      }
      this.isReconnecting.add(channel);
      const delay = Math.min(3000 * 2 ** (count - 1), 30000);
      // Re-fetch token from auth store at reconnection time instead of using stale closure value
      const timer = setTimeout(() => {
        const freshToken = useAuth.getState().accessToken ?? undefined;
        this.connect(channel, freshToken);
      }, delay);
      this.reconnectTimers.set(channel, timer);
    };
    this.connections.set(channel, ws);
  }

  subscribe(channel: string, handler: MessageHandler): () => void {
    if (!this.handlers.has(channel)) {
      this.handlers.set(channel, new Set());
    }
    this.handlers.get(channel)!.add(handler);
    return () => {
      this.handlers.get(channel)?.delete(handler);
    };
  }

  disconnect(channel: string): void {
    // If the channel is reconnecting, don't clear timers — only remove the handler
    if (this.isReconnecting.has(channel)) {
      return;
    }
    this.connections.get(channel)?.close();
    this.connections.delete(channel);
    const timer = this.reconnectTimers.get(channel);
    if (timer) clearTimeout(timer);
    this.reconnectTimers.delete(channel);
    this.retryCount.delete(channel);
  }

  /** Force-disconnect a channel, clearing reconnect state even if reconnecting. */
  forceDisconnect(channel: string): void {
    this.isReconnecting.delete(channel);
    this.connections.get(channel)?.close();
    this.connections.delete(channel);
    const timer = this.reconnectTimers.get(channel);
    if (timer) clearTimeout(timer);
    this.reconnectTimers.delete(channel);
    this.retryCount.delete(channel);
  }

  disconnectAll(): void {
    // Snapshot keys before iterating to avoid mutating the Map during iteration
    for (const channel of [...this.connections.keys(), ...this.isReconnecting]) {
      this.forceDisconnect(channel);
    }
  }
}

export const wsManager = new WebSocketManager();
