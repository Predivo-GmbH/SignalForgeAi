import { useEffect, useState } from "react";
import { wsManager } from "@/lib/ws";
import { useAuth } from "@/lib/auth";

export interface TradeUpdate {
  type: "order_filled" | "position_opened" | "position_closed";
  data: Record<string, unknown>;
}

const MAX_UPDATES = 50;

export function useTradeStream() {
  const [updates, setUpdates] = useState<TradeUpdate[]>([]);
  const token = useAuth((s) => s.accessToken);

  useEffect(() => {
    if (!token) return;

    wsManager.connect("trades", token);
    const unsub = wsManager.subscribe("trades", (msg: unknown) => {
      const update = msg as TradeUpdate;
      setUpdates((prev) => [update, ...prev].slice(0, MAX_UPDATES));
    });

    return () => {
      unsub();
      wsManager.disconnect("trades");
    };
  }, [token]);

  return updates;
}
