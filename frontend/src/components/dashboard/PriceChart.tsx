import { useEffect, useRef, useState } from "react";
import {
  createChart,
  CandlestickSeries,
  type IChartApi,
  type CandlestickData,
  type Time,
  ColorType,
} from "lightweight-charts";
import { cn } from "@/lib/cn";

const TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1D"] as const;

const SYMBOLS = [
  "AAPL",
  "MSFT",
  "NVDA",
  "TSLA",
  "AMZN",
  "META",
  "SPY",
  "QQQ",
  "BTC-USD",
];

/** Generate demo candlestick data for visual preview. */
function generateDemoCandles(count: number): CandlestickData<Time>[] {
  const candles: CandlestickData<Time>[] = [];
  let date = new Date("2026-02-01");
  let price = 150 + Math.random() * 50;

  for (let i = 0; i < count; i++) {
    const open = price;
    const volatility = price * 0.015;
    const close = open + (Math.random() - 0.48) * volatility;
    const high = Math.max(open, close) + Math.random() * volatility * 0.5;
    const low = Math.min(open, close) - Math.random() * volatility * 0.5;

    candles.push({
      time: (date.getTime() / 1000) as Time,
      open: +open.toFixed(2),
      high: +high.toFixed(2),
      low: +low.toFixed(2),
      close: +close.toFixed(2),
    });

    price = close;
    date = new Date(date.getTime() + 86400000);
  }

  return candles;
}

export function PriceChart() {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const [symbol, setSymbol] = useState(SYMBOLS[0]);
  const [timeframe, setTimeframe] = useState<(typeof TIMEFRAMES)[number]>("1h");

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "#141420" },
        textColor: "#8B8BA0",
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

    series.setData(generateDemoCandles(60));
    chart.timeScale().fitContent();

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
      <div ref={containerRef} className="flex-1 min-h-[300px]" />
    </div>
  );
}
