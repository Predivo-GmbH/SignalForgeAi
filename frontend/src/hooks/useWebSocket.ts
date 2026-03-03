import { useEffect, useRef, useState } from "react";
import { wsManager } from "@/lib/ws";
import { useAuth } from "@/lib/auth";

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
  const token = useAuth((s) => s.accessToken);
  const callbackRef = useRef(onSignal);
  useEffect(() => {
    callbackRef.current = onSignal;
  });

  useEffect(() => {
    if (!token) return;
    wsManager.connect("signals", token);
    const unsub = wsManager.subscribe("signals", (data) =>
      callbackRef.current(data as SignalMessage),
    );
    return () => {
      unsub();
      wsManager.disconnect("signals");
    };
  }, [token]);
}

export function usePriceStream() {
  const [prices, setPrices] = useState<Record<string, number>>({});

  useEffect(() => {
    wsManager.connect("prices");
    const unsub = wsManager.subscribe("prices", (data: unknown) => {
      const { symbol, price } = data as PriceMessage;
      setPrices((prev) => ({ ...prev, [symbol]: price }));
    });
    return () => {
      unsub();
      wsManager.disconnect("prices");
    };
  }, []);

  return prices;
}
