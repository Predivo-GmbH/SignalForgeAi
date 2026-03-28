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
import { cssVar } from "@/lib/colors";
import { pnlColor, formatPrice, fmtUsd } from "@/lib/format";
import { CRYPTO_NAME_MAP } from "@/lib/cryptoSymbols";
import { invokeFunction } from "@/lib/api";
import { Modal } from "@/components/ui/Modal";
import type { HoldingItem } from "@/hooks/useHoldings";

/* ---- Source styling (mirrors HoldingsCard) ---- */

const SOURCE_STYLE: Record<string, { label: string; cls: string }> = {
  binance: { label: "Binance", cls: "bg-(--color-palette-amber)/10 text-(--color-palette-amber)" },
  kucoin: { label: "KuCoin", cls: "bg-(--color-palette-emerald)/10 text-(--color-palette-emerald)" },
  mexc: { label: "MEXC", cls: "bg-(--color-palette-blue)/10 text-(--color-palette-blue)" },
  bitstamp: { label: "Bitstamp", cls: "bg-(--color-palette-green)/10 text-(--color-palette-green)" },
  cryptocom: { label: "Crypto.com", cls: "bg-(--color-palette-indigo)/10 text-(--color-palette-indigo)" },
  kraken: { label: "Kraken", cls: "bg-(--color-palette-violet)/10 text-(--color-palette-violet)" },
  manual: { label: "Manual", cls: "bg-(--color-bg-elevated) text-(--color-text-secondary)" },
};

const DONUT_COLOR_VARS = [
  "--color-palette-blue", "--color-palette-amber", "--color-palette-emerald",
  "--color-palette-violet", "--color-palette-rose", "--color-palette-cyan",
  "--color-palette-orange", "--color-palette-pink", "--color-palette-teal",
  "--color-palette-indigo",
] as const;

function CoinIcon({ symbol, imageUrl, size = 24 }: { symbol: string; imageUrl: string | null; size?: number }) {
  const [error, setError] = useState(false);
  if (imageUrl && !error) {
    return (
      <img src={imageUrl} alt={symbol} width={size} height={size}
        className="rounded-full shrink-0" onError={() => setError(true)} loading="lazy" />
    );
  }
  const colorIndex = symbol.charCodeAt(0) % DONUT_COLOR_VARS.length;
  return (
    <div className="rounded-full shrink-0 flex items-center justify-center text-white font-bold"
      style={{ width: size, height: size, backgroundColor: cssVar(DONUT_COLOR_VARS[colorIndex]), fontSize: size * 0.45 }}>
      {symbol.charAt(0)}
    </div>
  );
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

    const bgSurface = cssVar("--color-bg-surface");
    const textSec = cssVar("--color-text-secondary");
    const border = cssVar("--color-border");
    const accent = cssVar("--color-accent");
    const positive = cssVar("--color-positive");
    const negative = cssVar("--color-negative");

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: bgSurface },
        textColor: textSec,
        attributionLogo: false,
      },
      grid: {
        vertLines: { color: border },
        horzLines: { color: border },
      },
      width: containerRef.current.clientWidth,
      height: 250,
      crosshair: {
        vertLine: { color: accent, width: 1, labelBackgroundColor: accent },
        horzLine: { color: accent, width: 1, labelBackgroundColor: accent },
      },
      timeScale: { borderColor: border },
      rightPriceScale: { borderColor: border },
    });

    chartRef.current = chart;

    const series = chart.addSeries(CandlestickSeries, {
      upColor: positive,
      downColor: negative,
      borderUpColor: positive,
      borderDownColor: negative,
      wickUpColor: positive,
      wickDownColor: negative,
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
    setLoading(true);
    setError(null);

    invokeFunction<CandleResponse>("market", { action: "candles", symbol: `${symbol}/USDT`, timeframe, limit: 500 })
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
                "px-3 py-2 min-h-[44px] min-w-[44px] text-xs font-medium rounded-md transition-colors",
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
        <div ref={containerRef} className="w-full h-[200px] sm:h-[250px]" />
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-(--color-bg-surface)/80 z-10">
            <Loader2 className="w-5 h-5 animate-spin text-(--color-accent)" />
          </div>
        )}
        {error && !loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-(--color-bg-surface)/80 z-10">
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
  const imageUrl = holdings.find((h) => h.image_url)?.image_url ?? null;
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
      <div className="space-y-5 pr-1">
        {/* Header: Icon + Price + 24h change */}
        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          <CoinIcon symbol={symbol} imageUrl={imageUrl} size={28} />
          {currentPrice != null && (
            <span className="text-lg sm:text-xl font-bold font-mono text-(--color-text-primary)">
              {formatPrice(currentPrice)}
            </span>
          )}
          {change24h != null && (
            <span
              className={cn(
                "flex items-center gap-1 text-xs sm:text-sm font-medium font-mono",
                pnlColor(change24h),
              )}
            >
              {change24h >= 0 ? (
                <TrendingUp className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
              ) : (
                <TrendingDown className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
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
              <p className="text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">
                {s.label}
              </p>
              <p className="text-sm font-bold text-(--color-text-primary) font-mono">
                {s.value}
              </p>
              {s.sub && (
                <p className={cn("text-xs font-mono", s.subColor ?? "text-(--color-text-secondary)")}>
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
          <div className="relative">
          <div className="rounded-lg border border-(--color-border) overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-(--color-border) bg-(--color-bg-elevated)/30">
                  <th className="text-left text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider py-2 px-2 sm:px-3">
                    Source
                  </th>
                  <th className="text-left text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider py-2 px-2 sm:px-3 hidden sm:table-cell">
                    Label
                  </th>
                  <th className="text-right text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider py-2 px-2 sm:px-3">
                    Quantity
                  </th>
                  <th className="text-right text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider py-2 px-2 sm:px-3">
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
                      <td className="py-2 px-2 sm:px-3">
                        <span
                          className={cn(
                            "text-xs font-medium px-2 py-0.5 rounded-full whitespace-nowrap",
                            style.cls,
                          )}
                        >
                          {style.label}
                        </span>
                      </td>
                      <td className="py-2 px-2 sm:px-3 text-xs text-(--color-text-secondary) hidden sm:table-cell">
                        {h.notes ?? "—"}
                      </td>
                      <td className="py-2 px-2 sm:px-3 text-right font-mono tabular-nums text-xs text-(--color-text-primary)">
                        {h.quantity.toLocaleString("en-US", { maximumFractionDigits: 8 })}
                      </td>
                      <td className="py-2 px-2 sm:px-3 text-right font-mono tabular-nums text-xs font-semibold text-(--color-text-primary)">
                        {h.value_usd != null ? fmtUsd(h.value_usd) : "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div className="absolute right-0 top-0 bottom-0 w-6 bg-gradient-to-l from-(--color-bg-surface) to-transparent pointer-events-none sm:hidden" />
          </div>
        </div>

        {/* Price chart */}
        <AssetPriceChart symbol={symbol} />
      </div>
    </Modal>
  );
}
