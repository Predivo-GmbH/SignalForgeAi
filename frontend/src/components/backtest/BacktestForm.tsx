import { useState } from "react";
import { Play, Loader2 } from "lucide-react";
import { useSymbols } from "@/hooks/useSymbols";
import { Tooltip } from "@/components/ui/Tooltip";
import type { BacktestRequest } from "@/hooks/useBacktest";

const TIMEFRAMES: { key: string; label: string; tip: string }[] = [
  { key: "1m", label: "1m", tip: "1-minute candles. Very short-term scalping. Generates many signals but more noise. Best for 1-7 day backtests." },
  { key: "5m", label: "5m", tip: "5-minute candles. Short-term day trading. Good for intraday patterns. Best for 7-30 day backtests." },
  { key: "15m", label: "15m", tip: "15-minute candles. Intraday swing trades. Balances signal frequency with reliability. Best for 14-60 day backtests." },
  { key: "1h", label: "1h", tip: "1-hour candles. The default and most balanced timeframe. Good for swing trades lasting hours to days. Best for 30-90 day backtests." },
  { key: "4h", label: "4h", tip: "4-hour candles. Medium-term swing trading. Higher quality signals but fewer trades. Best for 60-180 day backtests." },
  { key: "1D", label: "1D", tip: "Daily candles. Long-term position trading. Very reliable signals but very few trades. Best for 90-365 day backtests." },
];

const FALLBACK_SYMBOLS = [
  "BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "BNB/USDT",
  "DOGE/USDT", "AVAX/USDT", "LINK/USDT",
];

interface BacktestFormProps {
  onSubmit: (req: BacktestRequest) => void;
  isLoading: boolean;
  initialSymbol?: string;
}

export function BacktestForm({ onSubmit, isLoading, initialSymbol }: BacktestFormProps) {
  const { data: apiSymbols } = useSymbols();
  const symbols = apiSymbols ?? FALLBACK_SYMBOLS;

  const [symbol, setSymbol] = useState(initialSymbol ?? symbols[0] ?? "BTC/USDT");
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
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      {/* Timeframe */}
      <div className="space-y-1.5">
        <div className="flex items-center gap-1.5">
          <label className="block text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">
            Timeframe
          </label>
          <Tooltip icon text="How often each candle/bar is formed. Shorter timeframes give more data points but more noise. Longer timeframes are more reliable but produce fewer trading signals." />
        </div>
        <div className="grid grid-cols-3 gap-1.5">
          {TIMEFRAMES.map((tf) => (
            <Tooltip key={tf.key} text={tf.tip}>
              <button
                type="button"
                onClick={() => setTimeframe(tf.key)}
                className={`w-full px-3 py-1.5 rounded-lg text-sm font-mono font-medium transition-colors ${
                  timeframe === tf.key
                    ? "bg-(--color-accent) text-white"
                    : "bg-(--color-bg-elevated) text-(--color-text-secondary) hover:text-(--color-text-primary)"
                }`}
              >
                {tf.label}
              </button>
            </Tooltip>
          ))}
        </div>
      </div>

      {/* Days */}
      <div className="space-y-1.5">
        <div className="flex items-center gap-1.5">
          <label className="block text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">
            Lookback (days)
          </label>
          <Tooltip icon text="How far back in history to simulate. More days = more data and trades, but takes longer to compute. Use at least 30 days for statistically meaningful results." />
        </div>
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
