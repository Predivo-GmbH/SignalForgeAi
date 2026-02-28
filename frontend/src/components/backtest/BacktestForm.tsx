import { useState } from "react";
import { Play, Loader2 } from "lucide-react";
import { useSymbols } from "@/hooks/useSymbols";
import type { BacktestRequest } from "@/hooks/useBacktest";

const TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1D"] as const;
const FALLBACK_SYMBOLS = [
  "BTC/USDT",
  "ETH/USDT",
  "SOL/USDT",
  "EUR/USD",
  "GBP/USD",
  "USD/JPY",
  "SPY",
  "QQQ",
  "AAPL",
];

interface BacktestFormProps {
  onSubmit: (req: BacktestRequest) => void;
  isLoading: boolean;
}

export function BacktestForm({ onSubmit, isLoading }: BacktestFormProps) {
  const { data: apiSymbols } = useSymbols();
  const symbols = apiSymbols ?? FALLBACK_SYMBOLS;

  const [symbol, setSymbol] = useState(symbols[0] ?? "BTC/USDT");
  const [timeframe, setTimeframe] = useState<string>("1h");
  const [days, setDays] = useState(30);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onSubmit({ symbol, timeframe, days });
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-6 space-y-5"
    >
      <h2 className="text-lg font-semibold text-(--color-text-primary)">
        Configuration
      </h2>

      {/* Symbol */}
      <div className="space-y-1.5">
        <label className="block text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">
          Symbol
        </label>
        <select
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          className="w-full bg-(--color-bg-elevated) border border-(--color-border) rounded-lg px-3 py-2 text-sm text-(--color-text-primary) focus:outline-none focus:ring-2 focus:ring-(--color-accent)/50"
        >
          {symbols.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>

      {/* Timeframe */}
      <div className="space-y-1.5">
        <label className="block text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">
          Timeframe
        </label>
        <div className="grid grid-cols-3 gap-1.5">
          {TIMEFRAMES.map((tf) => (
            <button
              key={tf}
              type="button"
              onClick={() => setTimeframe(tf)}
              className={`px-3 py-1.5 rounded-lg text-sm font-mono font-medium transition-colors ${
                timeframe === tf
                  ? "bg-(--color-accent) text-white"
                  : "bg-(--color-bg-elevated) text-(--color-text-secondary) hover:text-(--color-text-primary)"
              }`}
            >
              {tf}
            </button>
          ))}
        </div>
      </div>

      {/* Days */}
      <div className="space-y-1.5">
        <label className="block text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">
          Lookback (days)
        </label>
        <input
          type="number"
          min={1}
          max={365}
          value={days}
          onChange={(e) =>
            setDays(Math.max(1, Math.min(365, Number(e.target.value))))
          }
          className="w-full bg-(--color-bg-elevated) border border-(--color-border) rounded-lg px-3 py-2 text-sm font-mono text-(--color-text-primary) focus:outline-none focus:ring-2 focus:ring-(--color-accent)/50"
        />
        <p className="text-xs text-(--color-text-secondary)">1 – 365 days</p>
      </div>

      {/* Submit */}
      <button
        type="submit"
        disabled={isLoading}
        className="w-full flex items-center justify-center gap-2 bg-(--color-accent) hover:bg-(--color-accent)/90 text-white font-semibold py-2.5 px-4 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isLoading ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            Running...
          </>
        ) : (
          <>
            <Play className="w-4 h-4" />
            Run Backtest
          </>
        )}
      </button>
    </form>
  );
}
