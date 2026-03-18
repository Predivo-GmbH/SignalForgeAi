import { useEffect, useState } from "react";
import { subscribeTable } from "@/lib/ws";
import { useAuth } from "@/contexts/AuthContext";
import type { TradeMessage } from "@/hooks/useWebSocket";

export interface TradeUpdate {
  type: "order_filled" | "position_opened" | "position_closed";
  data: TradeMessage;
}

const MAX_UPDATES = 50;

export function useTradeStream() {
  const [updates, setUpdates] = useState<TradeUpdate[]>([]);
  const { user } = useAuth();

  useEffect(() => {
    if (!user) return;

    // Subscribe to new trades via Supabase Realtime
    const unsubTrades = subscribeTable(
      "trade-stream-trades",
      "trades",
      "INSERT",
      user.id,
      (payload) => {
        const row = payload as Record<string, unknown>;
        const update: TradeUpdate = {
          type: "order_filled",
          data: {
            symbol: row.symbol as string,
            side: row.direction as string,
            qty: row.position_size as number,
            price: row.entry_price as number,
            timestamp: row.created_at as string,
          },
        };
        setUpdates((prev) => [update, ...prev].slice(0, MAX_UPDATES));
      },
    );

    // Subscribe to position changes via Supabase Realtime
    const unsubPositions = subscribeTable(
      "trade-stream-positions",
      "positions",
      "*",
      user.id,
      (payload) => {
        const row = payload as Record<string, unknown>;
        const update: TradeUpdate = {
          type: row.is_open ? "position_opened" : "position_closed",
          data: {
            symbol: row.symbol as string,
            side: row.direction as string,
            qty: row.quantity as number,
            price: row.entry_price as number,
            timestamp: (row.opened_at ?? row.closed_at ?? new Date().toISOString()) as string,
          },
        };
        setUpdates((prev) => [update, ...prev].slice(0, MAX_UPDATES));
      },
    );

    return () => {
      unsubTrades();
      unsubPositions();
    };
  }, [user]);

  return updates;
}
