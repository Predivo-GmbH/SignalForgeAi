import { useEffect, useRef, useState } from "react";
import { wsManager } from "@/lib/ws";
import { useAuth } from "@/lib/auth";

export function useSignalStream(onSignal: (signal: unknown) => void) {
  const token = useAuth((s) => s.accessToken);
  const callbackRef = useRef(onSignal);
  useEffect(() => {
    callbackRef.current = onSignal;
  });

  useEffect(() => {
    if (!token) return;
    wsManager.connect("signals", token);
    const unsub = wsManager.subscribe("signals", (data) =>
      callbackRef.current(data),
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
      const { symbol, price } = data as { symbol: string; price: number };
      setPrices((prev) => ({ ...prev, [symbol]: price }));
    });
    return () => {
      unsub();
      wsManager.disconnect("prices");
    };
  }, []);

  return prices;
}
