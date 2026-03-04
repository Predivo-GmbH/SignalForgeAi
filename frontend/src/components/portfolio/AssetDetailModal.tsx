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
import { TrendingUp, TrendingDown, Loader2 } from "lucide-react";
import { cn } from "@/lib/cn";
import { pnlColor, formatPrice } from "@/lib/format";
import { CRYPTO_NAME_MAP } from "@/lib/cryptoSymbols";
import { api } from "@/lib/api";
import { Modal } from "@/components/ui/Modal";
import type { HoldingItem } from "@/hooks/useHoldings";

/* ---- Source styling (mirrors HoldingsCard) ---- */

const SOURCE_STYLE: Record<string, { label: string; cls: string }> = {
  binance: { label: "Binance", cls: "bg-amber-500/10 text-amber-500" },
  kucoin: { label: "KuCoin", cls: "bg-emerald-500/10 text-emerald-500" },
  mexc: { label: "MEXC", cls: "bg-blue-500/10 text-blue-500" },
  bitstamp: { label: "Bitstamp", cls: "bg-green-500/10 text-green-500" },
  cryptocom: { label: "Crypto.com", cls: "bg-indigo-500/10 text-indigo-500" },
  kraken: { label: "Kraken", cls: "bg-violet-500/10 text-violet-500" },
  manual: { label: "Manual", cls: "bg-(--color-bg-elevated) text-(--color-text-secondary)" },
  trading: { label: "Trading", cls: "bg-(--color-accent)/10 text-(--color-accent)" },
};

function fmtUsd(val: number): string {
  return `$${val.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

/* ---- Candle chart types ---- */

const TIMEFRAMES = ["1h", "4h", "1d"] as const;

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

/* ---- Inline Price Chart ---- */

function AssetPriceChart({ symbol }: { symbol: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const [timeframe, setTimeframe] = useState<(typeof TIMEFRAMES)[number]>("1d");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Create chart once
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
      height: 250,
      crosshair: {
        vertLine: { color: "#7B61FF", width: 1, labelBackgroundColor: "#7B61FF" },
        horzLine: { color: "#7B61FF", width: 1, labelBackgroundColor: "#7B61FF" },
      },
      timeScale: { borderColor: "#2A2A3C" },
      rightPriceScale: { borderColor: "#2A2A3C" },
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
        chart.applyOptions({ width: entry.contentRect.width });
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

  // Fetch data when symbol or timeframe changes
  useEffect(() => {
    const series = seriesRef.current;
    const chart = chartRef.current;
    if (!series || !chart) return;

    let cancelled = false;
    const urlSymbol = `${symbol}-USDT`;
    setLoading(true);
    setError(null);

    api
      .get<CandleResponse>(`/market/candles/${urlSymbol}/${timeframe}?limit=500`)
      .then((data) => {
        if (cancelled) return;
        if (data.candles.length === 0) {
          setError("No chart data available");
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
        if (!cancelled) setError(err.message || "Failed to load chart");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [symbol, timeframe]);

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">
          Price Chart
        </p>
        <div className="flex gap-1">
          {TIMEFRAMES.map((tf) => (
            <button
              key={tf}
              onClick={() => setTimeframe(tf)}
              className={cn(
                "px-2 py-0.5 text-[10px] font-medium rounded-md transition-colors",
                timeframe === tf
                  ? "bg-(--color-accent) text-white"
                  : "text-(--color-text-secondary) hover:bg-(--color-bg-elevated)",
              )}
            >
              {tf}
            </button>
          ))}
        </div>
      </div>
      <div className="relative rounded-lg overflow-hidden border border-(--color-border)">
        <div ref={containerRef} className="w-full h-[250px]" />
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-[#141420]/80 z-10">
            <Loader2 className="w-5 h-5 animate-spin text-(--color-accent)" />
          </div>
        )}
        {error && !loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-[#141420]/80 z-10">
            <span className="text-xs text-(--color-text-secondary)">{error}</span>
          </div>
        )}
      </div>
    </div>
  );
}

/* ---- Main Modal ---- */

interface AssetDetailModalProps {
  open: boolean;
  onClose: () => void;
  symbol: string;
  holdings: HoldingItem[];
  totalPortfolioValue: number;
}

export function AssetDetailModal({
  open,
  onClose,
  symbol,
  holdings,
  totalPortfolioValue,
}: AssetDetailModalProps) {
  const name = CRYPTO_NAME_MAP[symbol] ?? symbol;
  const totalQty = holdings.reduce((s, h) => s + h.quantity, 0);
  const totalValue = holdings.reduce((s, h) => s + (h.value_usd ?? 0), 0);
  const currentPrice = holdings.find((h) => h.current_price != null)?.current_price ?? null;
  const change24h = holdings.find((h) => h.change_24h_pct != null)?.change_24h_pct ?? null;
  const allocPct = totalPortfolioValue > 0 ? (totalValue / totalPortfolioValue) * 100 : 0;

  // Weighted average cost
  const withCost = holdings.filter((h) => h.avg_price != null && h.avg_price > 0);
  const avgCost =
    withCost.length > 0
      ? withCost.reduce((s, h) => s + h.quantity * (h.avg_price ?? 0), 0) /
        withCost.reduce((s, h) => s + h.quantity, 0)
      : null;

  // PnL from avg cost
  const pnl =
    avgCost != null && currentPrice != null
      ? ((currentPrice - avgCost) / avgCost) * 100
      : null;

  return (
    <Modal open={open} onClose={onClose} title={`${symbol} — ${name}`} size="lg">
      <div className="space-y-5 max-h-[75vh] overflow-y-auto pr-1">
        {/* Header: Price + 24h change */}
        <div className="flex items-center gap-3">
          {currentPrice != null && (
            <span className="text-xl font-bold font-mono text-(--color-text-primary)">
              {formatPrice(currentPrice)}
            </span>
          )}
          {change24h != null && (
            <span
              className={cn(
                "flex items-center gap-1 text-sm font-medium font-mono",
                pnlColor(change24h),
              )}
            >
              {change24h >= 0 ? (
                <TrendingUp className="w-4 h-4" />
              ) : (
                <TrendingDown className="w-4 h-4" />
              )}
              {change24h >= 0 ? "+" : ""}
              {change24h.toFixed(2)}% (24h)
            </span>
          )}
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: "Total Qty", value: totalQty.toLocaleString("en-US", { maximumFractionDigits: 8 }) },
            { label: "Total Value", value: fmtUsd(totalValue) },
            {
              label: "Avg Cost",
              value: avgCost != null ? formatPrice(avgCost) : "—",
              sub: pnl != null ? `${pnl >= 0 ? "+" : ""}${pnl.toFixed(2)}%` : undefined,
              subColor: pnl != null ? pnlColor(pnl) : undefined,
            },
            { label: "Allocation", value: `${allocPct.toFixed(1)}%` },
          ].map((s) => (
            <div
              key={s.label}
              className="bg-(--color-bg-elevated)/50 rounded-lg px-3 py-2.5 space-y-0.5"
            >
              <p className="text-[10px] font-medium text-(--color-text-secondary) uppercase tracking-wider">
                {s.label}
              </p>
              <p className="text-sm font-bold text-(--color-text-primary) font-mono">
                {s.value}
              </p>
              {s.sub && (
                <p className={cn("text-[11px] font-mono", s.subColor ?? "text-(--color-text-secondary)")}>
                  {s.sub}
                </p>
              )}
            </div>
          ))}
        </div>

        {/* Source breakdown */}
        <div className="space-y-2">
          <p className="text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">
            Stored On
          </p>
          <div className="rounded-lg border border-(--color-border) overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-(--color-border) bg-(--color-bg-elevated)/30">
                  <th className="text-left text-[10px] font-medium text-(--color-text-secondary) uppercase tracking-wider py-2 px-3">
                    Source
                  </th>
                  <th className="text-left text-[10px] font-medium text-(--color-text-secondary) uppercase tracking-wider py-2 px-3">
                    Label
                  </th>
                  <th className="text-right text-[10px] font-medium text-(--color-text-secondary) uppercase tracking-wider py-2 px-3">
                    Quantity
                  </th>
                  <th className="text-right text-[10px] font-medium text-(--color-text-secondary) uppercase tracking-wider py-2 px-3">
                    Value
                  </th>
                </tr>
              </thead>
              <tbody>
                {holdings.map((h, i) => {
                  const style = SOURCE_STYLE[h.source] ?? {
                    label: h.source,
                    cls: "bg-(--color-bg-elevated) text-(--color-text-secondary)",
                  };
                  return (
                    <tr
                      key={`${h.source}-${i}`}
                      className="border-b border-(--color-border)/50 last:border-0"
                    >
                      <td className="py-2 px-3">
                        <span
                          className={cn(
                            "text-[10px] font-medium px-2 py-0.5 rounded-full whitespace-nowrap",
                            style.cls,
                          )}
                        >
                          {style.label}
                        </span>
                      </td>
                      <td className="py-2 px-3 text-xs text-(--color-text-secondary)">
                        {h.notes ?? "—"}
                      </td>
                      <td className="py-2 px-3 text-right font-mono tabular-nums text-xs text-(--color-text-primary)">
                        {h.quantity.toLocaleString("en-US", { maximumFractionDigits: 8 })}
                      </td>
                      <td className="py-2 px-3 text-right font-mono tabular-nums text-xs font-semibold text-(--color-text-primary)">
                        {h.value_usd != null ? fmtUsd(h.value_usd) : "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Price chart */}
        <AssetPriceChart symbol={symbol} />
      </div>
    </Modal>
  );
}
