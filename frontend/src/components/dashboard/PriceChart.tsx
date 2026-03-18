import { useEffect, useRef, useState } from "react";
import {
  createChart,
  CandlestickSeries,
  type IChartApi,
  type ISeriesApi,
  type CandlestickData,
  type Time,
  ColorType,
} from "lightweight-charts";
import { cn } from "@/lib/cn";
import { invokeFunction } from "@/lib/api";

const TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d"] as const;

const SYMBOLS = [
  "BTC/USDT",
  "ETH/USDT",
  "SOL/USDT",
];

interface CandleResponse {
  symbol: string;
  timeframe: string;
  candles: Array<{
    time: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
  }>;
  count: number;
}

export function PriceChart() {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const [symbol, setSymbol] = useState(SYMBOLS[0]);
  const [timeframe, setTimeframe] = useState<(typeof TIMEFRAMES)[number]>("1h");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Chart creation — runs once on mount
  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "#141420" },
        textColor: "#8B8BA0",
        attributionLogo: false,
      },
      grid: {
        vertLines: { color: "#2A2A3C" },
        horzLines: { color: "#2A2A3C" },
      },
      width: containerRef.current.clientWidth,
      height: containerRef.current.clientHeight,
      crosshair: {
        vertLine: { color: "#7B61FF", width: 1, labelBackgroundColor: "#7B61FF" },
        horzLine: { color: "#7B61FF", width: 1, labelBackgroundColor: "#7B61FF" },
      },
      timeScale: {
        borderColor: "#2A2A3C",
      },
      rightPriceScale: {
        borderColor: "#2A2A3C",
      },
    });

    chartRef.current = chart;

    const series = chart.addSeries(CandlestickSeries, {
      upColor: "#00D68F",
      downColor: "#FF4D6A",
      borderUpColor: "#00D68F",
      borderDownColor: "#FF4D6A",
      wickUpColor: "#00D68F",
      wickDownColor: "#FF4D6A",
    });
    seriesRef.current = series;

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        chart.applyOptions({ width, height });
      }
    });
    observer.observe(containerRef.current);

    return () => {
      observer.disconnect();
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  // Data fetching — runs when symbol or timeframe changes
  useEffect(() => {
    const series = seriesRef.current;
    const chart = chartRef.current;
    if (!series || !chart) return;

    let cancelled = false;
    const urlSymbol = symbol.replace("/", "-");
    setLoading(true);
    setError(null);

    invokeFunction<CandleResponse>("market", { action: "candles", symbol: urlSymbol.replace("-", "/"), timeframe, limit: 500 })
      .then((data) => {
        if (cancelled) return;
        if (data.candles.length === 0) {
          setError("No candle data available");
          return;
        }
        const mapped: CandlestickData<Time>[] = data.candles.map((c) => ({
          time: (new Date(c.time).getTime() / 1000) as Time,
          open: c.open,
          high: c.high,
          low: c.low,
          close: c.close,
        }));
        series.setData(mapped);
        chart.timeScale().fitContent();
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || "Failed to load candles");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [symbol, timeframe]);

  return (
    <div className="bg-[var(--color-bg-surface)] rounded-xl border border-[var(--color-border)] flex flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-border)]">
        <div className="flex items-center gap-3">
          <select
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            className="bg-[var(--color-bg-elevated)] text-[var(--color-text-primary)] text-sm font-semibold rounded-lg border border-[var(--color-border)] px-3 py-1.5 outline-none focus:ring-1 focus:ring-[var(--color-accent)]"
          >
            {SYMBOLS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
        <div className="flex gap-1">
          {TIMEFRAMES.map((tf) => (
            <button
              key={tf}
              onClick={() => setTimeframe(tf)}
              className={cn(
                "px-2.5 py-1 text-xs font-medium rounded-md transition-colors",
                timeframe === tf
                  ? "bg-[var(--color-accent)] text-white"
                  : "text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-elevated)]",
              )}
            >
              {tf}
            </button>
          ))}
        </div>
      </div>
      {/* Chart Area */}
      <div className="relative flex-1 min-h-[300px]">
        <div ref={containerRef} className="absolute inset-0" />
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-[#141420]/80 z-10">
            <span className="text-sm text-[var(--color-text-secondary)]">Loading candles...</span>
          </div>
        )}
        {error && !loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-[#141420]/80 z-10">
            <span className="text-sm text-[var(--color-text-secondary)]">{error}</span>
          </div>
        )}
      </div>
    </div>
  );
}
