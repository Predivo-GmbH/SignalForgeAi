type MessageHandler = (data: unknown) => void;

export class WebSocketManager {
  private baseUrl: string;
  private connections = new Map<string, WebSocket>();
  private handlers = new Map<string, Set<MessageHandler>>();
  private reconnectTimers = new Map<string, ReturnType<typeof setTimeout>>();

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
    ws.onmessage = (event: MessageEvent) => {
      const data: unknown = JSON.parse(event.data as string);
      this.handlers.get(channel)?.forEach((fn) => fn(data));
    };
    ws.onclose = () => {
      this.connections.delete(channel);
      const timer = setTimeout(() => this.connect(channel, token), 3000);
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
    this.connections.get(channel)?.close();
    this.connections.delete(channel);
    const timer = this.reconnectTimers.get(channel);
    if (timer) clearTimeout(timer);
    this.reconnectTimers.delete(channel);
  }

  disconnectAll(): void {
    for (const channel of this.connections.keys()) {
      this.disconnect(channel);
    }
  }
}

export const wsManager = new WebSocketManager();
