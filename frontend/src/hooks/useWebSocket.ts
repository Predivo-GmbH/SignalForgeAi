import { useEffect, useRef, useState } from "react";
import { subscribeBroadcast, subscribeTable } from "@/lib/ws";
import { useAuth } from "@/contexts/AuthContext";

export interface SignalMessage {
  symbol: string;
  action: string;
  confluence_score: number;
  price: number;
  timestamp: string;
  timeframe?: string;
  strategy_id?: string;
}

export interface PriceMessage {
  symbol: string;
  price: number;
  timestamp?: string;
}

export interface TradeMessage {
  symbol: string;
  side: string;
  qty: number;
  price: number;
  timestamp: string;
  type?: string;
}

export function useSignalStream(onSignal: (signal: SignalMessage) => void) {
  const { user } = useAuth();
  const callbackRef = useRef(onSignal);
  useEffect(() => {
    callbackRef.current = onSignal;
  });

  useEffect(() => {
    if (!user) return;

    const unsub = subscribeTable(
      "signal-stream",
      "signals",
      "INSERT",
      user.id,
      (payload) => callbackRef.current(payload as SignalMessage),
    );

    return unsub;
  }, [user]);
}

export function usePriceStream() {
  const [prices, setPrices] = useState<Record<string, number>>({});

  useEffect(() => {
    const unsub = subscribeBroadcast(
      "price-stream",
      "price-update",
      (data: unknown) => {
        const { symbol, price } = data as PriceMessage;
        setPrices((prev) => ({ ...prev, [symbol]: price }));
      },
    );

    return unsub;
  }, []);

  return prices;
}
