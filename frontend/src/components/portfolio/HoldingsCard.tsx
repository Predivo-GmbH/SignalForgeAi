import { useState, useMemo, useRef, useEffect } from "react";
import {
  Loader2,
  Plus,
  X,
  Wallet,
  TrendingUp,
  TrendingDown,
  ChevronDown,
  ChevronUp,
  Search,
  EyeOff,
  Eye,
  LayoutGrid,
} from "lucide-react";
import {
  createChart,
  AreaSeries,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
  ColorType,
} from "lightweight-charts";
import { cn } from "@/lib/cn";
import { pnlColor, fmtUsd } from "@/lib/format";
import { CRYPTO_NAME_MAP } from "@/lib/cryptoSymbols";
import {
  useHoldings,
  useDeleteHolding,
} from "@/hooks/useHoldings";
import type { HoldingItem } from "@/hooks/useHoldings";
import { useBrokerConnections } from "@/hooks/useBrokerConnections";
import { AssetDetailModal } from "./AssetDetailModal";
import { Tooltip } from "@/components/ui/Tooltip";
import { CoinIcon } from "./CoinIcon";
import { DONUT_COLORS } from "./CoinIcon";
import { DonutChart } from "./DonutChart";
import type { DonutSlice } from "./DonutChart";
import { HoldingForm } from "./HoldingFormModal";
import { HoldingRow, SOURCE_STYLE } from "./HoldingRow";
import type { CombinedHolding } from "./HoldingRow";

/* ---- Constants ---- */

const STABLECOINS = new Set(["USDT", "USDC", "BUSD", "DAI", "TUSD", "FDUSD", "USDP", "USD"]);
const SMALL_BALANCE_THRESHOLD = 1; // $1
const TOP_PERFORMER_MIN_VALUE = 50; // exclude tiny positions from top performer

/* ---- Helpers ---- */

function fmtCompact(val: number): string {
  if (val >= 1e12) return `$${(val / 1e12).toFixed(2)}T`;
  if (val >= 1e9) return `$${(val / 1e9).toFixed(2)}B`;
  if (val >= 1e6) return `$${(val / 1e6).toFixed(1)}M`;
  if (val >= 1e3) return `$${(val / 1e3).toFixed(1)}K`;
  return fmtUsd(val);
}

/* ---- Source badge ---- */

function SourceBadge({ source, onClick, active }: { source: string; onClick?: () => void; active?: boolean }) {
  const style = SOURCE_STYLE[source] ?? { label: source, cls: "bg-(--color-bg-elevated) text-(--color-text-secondary)" };
  return (
    <span
      onClick={onClick}
      className={cn(
        "text-[10px] font-medium px-2 py-0.5 rounded-full whitespace-nowrap transition-all duration-150",
        style.cls,
        onClick && "cursor-pointer hover:opacity-80",
        active && "ring-2 ring-current/30 scale-110",
      )}
    >
      {style.label}
    </span>
  );
}

/* ---- Exchange Logo ---- */

function ExchangeLogo({ source, size = 18 }: { source: string; size?: number }) {
  const color = SOURCE_STYLE[source]?.color ?? "#6b7280";

  if (source === "manual") return <Wallet size={size} className="shrink-0 text-(--color-text-secondary)" />;
  if (source === "all") return <LayoutGrid size={size} className="shrink-0 text-(--color-accent)" />;

  // Inline SVG logos for each exchange
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className="shrink-0">
      {source === "binance" && (
        /* Binance diamond mark */
        <g fill={color}>
          <polygon points="12,2.5 14.5,5 12,7.5 9.5,5" />
          <polygon points="5.5,9 8,6.5 10.5,9 8,11.5" />
          <polygon points="18.5,9 16,6.5 13.5,9 16,11.5" />
          <polygon points="12,9.5 14.5,12 12,14.5 9.5,12" />
          <polygon points="5.5,15 8,12.5 10.5,15 8,17.5" />
          <polygon points="18.5,15 16,12.5 13.5,15 16,17.5" />
          <polygon points="12,16.5 14.5,19 12,21.5 9.5,19" />
        </g>
      )}
      {source === "kucoin" && (
        /* KuCoin hexagonal K mark */
        <g fill={color}>
          <circle cx="12" cy="5" r="2.5" />
          <rect x="10.5" y="7" width="3" height="10" rx="1.5" />
          <path d="M13.5 12 L19 7.5 L20 9 L15 12.5 L20 16 L19 17.5 L13.5 13Z" />
        </g>
      )}
      {source === "mexc" && (
        /* MEXC stylized M */
        <g fill={color}>
          <path d="M4 19V6l4 6.5L12 5l4 7.5L20 6v13h-3V13l-1.5 2.5L12 10l-3.5 5.5L7 13v6H4Z" />
        </g>
      )}
      {source === "kraken" && (
        /* Kraken K tentacle */
        <g fill={color}>
          <path d="M7 3v18h3.5V14l5.5 7h4.5l-6.5-8L19.5 5H15l-4.5 5.5V3H7Z" />
        </g>
      )}
      {source === "cryptocom" && (
        /* Crypto.com shield C */
        <g fill={color}>
          <path d="M12 2L3 6.5v5c0 5 3.8 9.7 9 11 5.2-1.3 9-6 9-11v-5L12 2Zm0 3l6 3.2v3.3c0 3.7-2.6 7.2-6 8.2-3.4-1-6-4.5-6-8.2V8.2L12 5Z" />
          <path d="M15 10.5h-2.5V9.2c0-.7-.5-1.2-1.2-1.2-.7 0-1.3.5-1.3 1.2v5.6c0 .7.6 1.2 1.3 1.2.7 0 1.2-.5 1.2-1.2V13.5H15v1.3c0 2-1.6 3.7-3.7 3.7-2 0-3.8-1.7-3.8-3.7V9.2c0-2 1.8-3.7 3.8-3.7 2.1 0 3.7 1.7 3.7 3.7V10.5Z" />
        </g>
      )}
      {source === "bitstamp" && (
        /* Bitstamp shield/stamp */
        <g fill={color}>
          <path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10 10-4.5 10-10S17.5 2 12 2Zm0 17.5c-4.1 0-7.5-3.4-7.5-7.5S7.9 4.5 12 4.5s7.5 3.4 7.5 7.5-3.4 7.5-7.5 7.5Z" />
          <path d="M14.5 9h-5v2h5c.6 0 1 .4 1 1s-.4 1-1 1h-5v2h5c1.7 0 3-1.3 3-3s-1.3-3-3-3Z" />
        </g>
      )}
      {/* Fallback for unknown exchanges */}
      {!["binance", "kucoin", "mexc", "kraken", "cryptocom", "bitstamp"].includes(source) && (
        <g>
          <circle cx="12" cy="12" r="9" fill={color} opacity="0.15" />
          <text x="12" y="16" textAnchor="middle" fill={color} fontSize="12" fontWeight="bold">
            {(SOURCE_STYLE[source]?.label ?? source).charAt(0).toUpperCase()}
          </text>
        </g>
      )}
    </svg>
  );
}

/* ---- Portfolio Overview Header ---- */

function PortfolioOverviewHeader({
  totalValue,
  combined,
  onTopClick,
}: {
  totalValue: number;
  combined: CombinedHolding[];
  onTopClick: (symbol: string) => void;
}) {
  // 24h portfolio change
  const change24hUsd = combined.reduce((sum, c) => {
    if (c.change24hPct != null && c.totalValue > 0) {
      return sum + (c.totalValue * c.change24hPct) / (100 + c.change24hPct);
    }
    return sum;
  }, 0);
  const change24hPct = totalValue > 0 ? (change24hUsd / (totalValue - change24hUsd)) * 100 : 0;

  // Total P/L from avg_price where available
  const totalPnlUsd = combined.reduce((sum, c) => sum + (c.pnlUsd ?? 0), 0);
  const totalCostBasis = combined.reduce((sum, c) => {
    if (c.avgCost != null) return sum + c.avgCost * c.totalQty;
    return sum;
  }, 0);
  const totalPnlPct = totalCostBasis > 0 ? (totalPnlUsd / totalCostBasis) * 100 : null;
  const hasCostBasis = combined.some((c) => c.avgCost != null);

  // Top performer 24h (exclude small positions)
  const withChange = combined.filter((c) => c.change24hPct != null && c.totalValue >= TOP_PERFORMER_MIN_VALUE);
  // Pick by highest 24h dollar gain: value * pct / (100 + pct)
  const dollarGain = (c: (typeof withChange)[0]) => {
    const pct = c.change24hPct ?? 0;
    return (c.totalValue * pct) / (100 + pct);
  };
  const topPerformer = withChange.length > 0
    ? withChange.reduce((a, b) => (dollarGain(a) > dollarGain(b) ? a : b))
    : null;

  // 24h change value for top performer
  const topChange = topPerformer
    ? (topPerformer.totalValue * (topPerformer.change24hPct ?? 0)) / (100 + (topPerformer.change24hPct ?? 0))
    : 0;

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 sm:gap-3">
      {/* Current Balance */}
      <div className="bg-(--color-bg-elevated)/50 rounded-lg px-3 sm:px-4 py-2.5 sm:py-3 space-y-1">
        <Tooltip text="The total USD value of all your crypto holdings right now."><p className="text-[10px] font-medium text-(--color-text-secondary) uppercase tracking-normal sm:tracking-wider cursor-help">Balance</p></Tooltip>
        <p className="text-base sm:text-lg font-bold font-mono text-(--color-text-primary)">{fmtUsd(totalValue)}</p>
        <p className="text-xs text-(--color-text-secondary)">{combined.length} asset{combined.length !== 1 ? "s" : ""}</p>
      </div>

      {/* 24h Change */}
      <div className="bg-(--color-bg-elevated)/50 rounded-lg px-3 sm:px-4 py-2.5 sm:py-3 space-y-1">
        <Tooltip text="How much your total portfolio value changed in the last 24 hours."><p className="text-[10px] font-medium text-(--color-text-secondary) uppercase tracking-normal sm:tracking-wider cursor-help"><span className="sm:hidden">24h Change</span><span className="hidden sm:inline">24h Portfolio Change</span></p></Tooltip>
        <p className={cn("text-base sm:text-lg font-bold font-mono", pnlColor(change24hUsd))}>
          {change24hUsd >= 0 ? "+" : ""}{fmtUsd(Math.abs(change24hUsd))}
        </p>
        <div className="flex items-center gap-1">
          {change24hPct >= 0 ? (
            <TrendingUp className={cn("w-3 h-3", pnlColor(change24hUsd))} />
          ) : (
            <TrendingDown className={cn("w-3 h-3", pnlColor(change24hUsd))} />
          )}
          <span className={cn("text-xs font-mono", pnlColor(change24hUsd))}>
            {change24hPct >= 0 ? "+" : ""}{change24hPct.toFixed(2)}%
          </span>
        </div>
      </div>

      {/* Total P/L */}
      <div className="bg-(--color-bg-elevated)/50 rounded-lg px-3 sm:px-4 py-2.5 sm:py-3 space-y-1">
        <Tooltip text="Cumulative profit or loss based on your cost basis vs current market value."><p className="text-[10px] font-medium text-(--color-text-secondary) uppercase tracking-normal sm:tracking-wider cursor-help"><span className="sm:hidden">Total P/L</span><span className="hidden sm:inline">Total Profit / Loss</span></p></Tooltip>
        {hasCostBasis ? (
          <>
            <p className={cn("text-base sm:text-lg font-bold font-mono", pnlColor(totalPnlUsd))}>
              {totalPnlUsd >= 0 ? "+" : ""}{fmtUsd(Math.abs(totalPnlUsd))}
            </p>
            <div className="flex items-center gap-1">
              {totalPnlUsd >= 0 ? (
                <TrendingUp className={cn("w-3 h-3", pnlColor(totalPnlUsd))} />
              ) : (
                <TrendingDown className={cn("w-3 h-3", pnlColor(totalPnlUsd))} />
              )}
              <span className={cn("text-xs font-mono", pnlColor(totalPnlUsd))}>
                {totalPnlPct != null ? `${totalPnlPct >= 0 ? "+" : ""}${totalPnlPct.toFixed(2)}%` : ""}
              </span>
            </div>
          </>
        ) : (
          <>
            <p className="text-lg font-bold font-mono text-(--color-text-secondary)">--</p>
            <p className="text-xs text-(--color-text-secondary)">No cost basis</p>
          </>
        )}
      </div>

      {/* Top Performer */}
      <div
        onClick={topPerformer ? () => onTopClick(topPerformer.symbol) : undefined}
        className={cn(
          "bg-(--color-bg-elevated)/50 rounded-lg px-3 sm:px-4 py-2.5 sm:py-3 space-y-1 transition-all duration-150",
          topPerformer && "cursor-pointer hover:bg-(--color-bg-elevated)/80 hover:-translate-y-0.5",
        )}
      >
        <Tooltip text="The asset with the highest dollar gain in the last 24 hours."><p className="text-[10px] font-medium text-(--color-text-secondary) uppercase tracking-normal sm:tracking-wider cursor-help"><span className="sm:hidden">Top 24h</span><span className="hidden sm:inline">Top Performer 24h</span></p></Tooltip>
        {topPerformer ? (
          <>
            <div className="flex items-center gap-2">
              <CoinIcon symbol={topPerformer.symbol} imageUrl={topPerformer.imageUrl} size={20} />
              <span className="text-sm font-bold text-(--color-text-primary)">{topPerformer.name}</span>
              <span className="text-xs text-(--color-text-secondary) font-mono">{topPerformer.symbol}</span>
            </div>
            <p className="text-xs font-mono text-(--color-positive)">
              +{fmtUsd(Math.abs(topChange))}
            </p>
          </>
        ) : (
          <p className="text-lg font-bold font-mono text-(--color-text-secondary)">--</p>
        )}
      </div>
    </div>
  );
}

/* ---- Source Breakdown ---- */

function SourceBreakdown({
  holdings,
  totalValue,
  onSourceClick,
  activeSource,
}: {
  holdings: HoldingItem[];
  totalValue: number;
  onSourceClick: (source: string) => void;
  activeSource: string | null;
}) {
  const bySource = useMemo(() => {
    const map: Record<string, { value: number; count: number }> = {};
    for (const h of holdings) {
      if (!map[h.source]) map[h.source] = { value: 0, count: 0 };
      map[h.source].value += h.value_usd ?? 0;
      map[h.source].count += 1;
    }
    return Object.entries(map)
      .map(([source, { value, count }]) => ({ source, value, count, pct: totalValue > 0 ? (value / totalValue) * 100 : 0 }))
      .sort((a, b) => b.value - a.value);
  }, [holdings, totalValue]);

  if (bySource.length <= 1) return null;

  const totalCount = bySource.reduce((sum, s) => sum + s.count, 0);
  const isAllActive = activeSource === null;

  return (
    <div className="grid grid-cols-2 gap-2 sm:flex sm:overflow-x-auto sm:p-1 sm:-m-1 sm:scrollbar-thin">
      {/* "All" card — always first, selected by default */}
      <button
        onClick={() => { if (!isAllActive && activeSource) onSourceClick(activeSource); }}
        className={cn(
          "sm:shrink-0 sm:min-w-[90px] sm:flex-1 rounded-lg px-2.5 sm:px-3 py-2 sm:py-2.5 text-left transition-all duration-150 space-y-0.5",
          "hover:-translate-y-0.5",
          isAllActive
            ? "bg-(--color-accent)/10 ring-2 ring-(--color-accent)/40 ring-offset-1 ring-offset-(--color-bg-surface)"
            : "bg-(--color-bg-elevated)/50 opacity-50",
        )}
      >
        <div className="flex items-center gap-1.5">
          <ExchangeLogo source="all" size={16} />
          <span className="text-xs font-semibold text-(--color-text-primary)">All</span>
        </div>
        <p className="text-sm font-bold font-mono text-(--color-text-primary)">
          {fmtCompact(totalValue)}
        </p>
        <p className="text-[10px] font-mono text-(--color-text-secondary)">
          {totalCount} asset{totalCount !== 1 ? "s" : ""} · 100%
        </p>
      </button>

      {bySource.map((s) => {
        const style = SOURCE_STYLE[s.source];
        const isActive = activeSource === s.source;
        const color = style?.color ?? "#6b7280";
        return (
          <button
            key={s.source}
            onClick={() => onSourceClick(s.source)}
            className={cn(
              "sm:shrink-0 sm:min-w-[90px] sm:flex-1 rounded-lg px-2.5 sm:px-3 py-2 sm:py-2.5 text-left transition-all duration-150 space-y-0.5",
              "hover:-translate-y-0.5",
              isActive
                ? "ring-2 ring-offset-1 ring-offset-(--color-bg-surface)"
                : "bg-(--color-bg-elevated)/50",
              !isActive && !isAllActive && "opacity-50",
            )}
            style={isActive ? { backgroundColor: `${color}15`, boxShadow: `0 0 0 2px ${color}50` } : undefined}
          >
            <div className="flex items-center gap-1.5">
              <ExchangeLogo source={s.source} size={16} />
              <span className="text-xs font-semibold text-(--color-text-primary) truncate">
                {style?.label ?? s.source}
              </span>
            </div>
            <p className="text-sm font-bold font-mono text-(--color-text-primary)">
              {fmtCompact(s.value)}
            </p>
            <p className="text-[10px] font-mono text-(--color-text-secondary)">
              {s.count} asset{s.count !== 1 ? "s" : ""} · {s.pct.toFixed(1)}%
            </p>
          </button>
        );
      })}
    </div>
  );
}

/* ---- Portfolio Value Chart ---- */

const PERF_PERIODS = ["24H", "7D", "1M", "3M", "1Y"] as const;
type PerfPeriod = (typeof PERF_PERIODS)[number];

/**
 * Build a synthetic 24h portfolio value curve from individual holding 24h changes.
 * Returns lightweight-charts compatible data with UTCTimestamps.
 */
function build24hCurve(
  currentTotal: number,
  holdings: { value: number; change24hPct: number | null }[],
): { time: UTCTimestamp; value: number }[] {
  let prevTotal = 0;
  for (const h of holdings) {
    if (h.change24hPct != null && h.value > 0) {
      prevTotal += h.value / (1 + h.change24hPct / 100);
    } else {
      prevTotal += h.value;
    }
  }

  const points = 24;
  const result: { time: UTCTimestamp; value: number }[] = [];
  const now = new Date();

  for (let i = 0; i <= points; i++) {
    const t = i / points;
    const ease = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
    const value = prevTotal + (currentTotal - prevTotal) * ease;
    const hourDate = new Date(now.getTime() - (points - i) * 60 * 60 * 1000);
    result.push({ time: Math.floor(hourDate.getTime() / 1000) as UTCTimestamp, value });
  }

  return result;
}

function PortfolioValueChart({
  totalValue,
  change24hUsd,
  change24hPct,
  holdings,
}: {
  totalValue: number;
  change24hUsd: number;
  change24hPct: number;
  holdings: { value: number; change24hPct: number | null }[];
}) {
  const [period, setPeriod] = useState<PerfPeriod>("24H");
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Area"> | null>(null);
  const [hoverValue, setHoverValue] = useState<{ value: number; date: string; time: string; x: number; y: number } | null>(null);

  const has24hData = holdings.some((h) => h.change24hPct != null);
  const canRender = period === "24H" && has24hData && totalValue > 0;

  const chartData = useMemo(
    () => (canRender ? build24hCurve(totalValue, holdings) : []),
    [canRender, totalValue, holdings],
  );

  const isPositive = change24hUsd >= 0;
  const lineColor = isPositive ? "#10b981" : "#ef4444";
  const topColor = isPositive ? "rgba(16, 185, 129, 0.15)" : "rgba(239, 68, 68, 0.15)";
  const bottomColor = isPositive ? "rgba(16, 185, 129, 0)" : "rgba(239, 68, 68, 0)";

  // Create chart on mount
  useEffect(() => {
    if (!containerRef.current) return;

    const isDark = document.documentElement.classList.contains("dark");

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: isDark ? "#8B8BA0" : "#6B6B80",
        fontSize: 11,
      },
      grid: {
        vertLines: { visible: false },
        horzLines: { color: isDark ? "rgba(42, 42, 60, 0.4)" : "rgba(229, 226, 220, 0.6)", style: 1 },
      },
      width: containerRef.current.clientWidth,
      height: containerRef.current.clientHeight,
      crosshair: {
        vertLine: {
          color: isDark ? "rgba(139, 139, 160, 0.3)" : "rgba(107, 107, 128, 0.3)",
          width: 1,
          labelBackgroundColor: isDark ? "#1C1C2E" : "#F0EDE8",
        },
        horzLine: {
          color: isDark ? "rgba(139, 139, 160, 0.3)" : "rgba(107, 107, 128, 0.3)",
          width: 1,
          labelBackgroundColor: isDark ? "#1C1C2E" : "#F0EDE8",
        },
      },
      timeScale: {
        borderVisible: false,
        timeVisible: true,
        secondsVisible: false,
      },
      rightPriceScale: {
        borderVisible: false,
      },
      localization: {
        priceFormatter: (price: number) => fmtCompact(price),
      },
      handleScroll: false,
      handleScale: false,
    });

    chartRef.current = chart;

    chart.subscribeCrosshairMove((param) => {
      if (!param.time || !param.seriesData.size || !param.point) {
        setHoverValue(null);
        return;
      }
      const data = param.seriesData.values().next().value as { value?: number } | undefined;
      if (data?.value != null) {
        const d = new Date((param.time as number) * 1000);
        setHoverValue({
          value: data.value,
          date: d.toLocaleDateString([], { month: "short", day: "numeric", year: "numeric" }),
          time: d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          x: param.point.x,
          y: param.point.y,
        });
      }
    });

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

  // Update data when chartData or colors change
  useEffect(() => {
    if (!chartRef.current || chartData.length === 0) return;

    if (seriesRef.current) {
      chartRef.current.removeSeries(seriesRef.current);
      seriesRef.current = null;
    }

    const series = chartRef.current.addSeries(AreaSeries, {
      lineColor,
      topColor,
      bottomColor,
      lineWidth: 2,
      crosshairMarkerBackgroundColor: lineColor,
      crosshairMarkerRadius: 4,
      crosshairMarkerBorderWidth: 2,
      crosshairMarkerBorderColor: "#FFFFFF",
      lastValueVisible: false,
      priceLineVisible: false,
    });

    series.setData(chartData);
    seriesRef.current = series;
    chartRef.current.timeScale().fitContent();
  }, [chartData, lineColor, topColor, bottomColor]);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 mb-1">
        <p className="text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">
          Portfolio Value
        </p>
        <div className="flex gap-0.5 shrink-0">
          {PERF_PERIODS.map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={cn(
                "text-[10px] font-medium px-1.5 sm:px-2 py-0.5 rounded transition-colors",
                period === p
                  ? "bg-(--color-text-primary) text-(--color-bg-surface)"
                  : "text-(--color-text-secondary) hover:text-(--color-text-primary) hover:bg-(--color-bg-elevated)/60",
              )}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {/* Value + change */}
      <div className="mb-2 space-y-0.5">
        <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
          <span className="text-base sm:text-lg font-bold font-mono text-(--color-text-primary)">
            {hoverValue ? fmtUsd(hoverValue.value) : fmtUsd(totalValue)}
          </span>
          <span className={cn("text-[11px] sm:text-xs font-mono font-medium", isPositive ? "text-(--color-positive)" : "text-(--color-negative)")}>
            {isPositive ? "+" : ""}{fmtUsd(Math.abs(change24hUsd))} ({isPositive ? "+" : ""}{change24hPct.toFixed(2)}%)
          </span>
        </div>
        <p className={cn("text-[11px] font-mono text-(--color-text-secondary) h-4", !hoverValue && "invisible")}>
          {hoverValue ? `${hoverValue.date}, ${hoverValue.time}` : "\u00A0"}
        </p>
      </div>

      {/* Chart — always render container so ref is available */}
      <div className="flex-1 min-h-[200px] relative">
        <div
          ref={containerRef}
          className={cn("w-full h-full", !(canRender && chartData.length >= 2) && "invisible")}
          onMouseLeave={() => setHoverValue(null)}
        />
        {/* Floating tooltip on chart */}
        {hoverValue && canRender && (
          <div
            className="absolute pointer-events-none z-10 bg-(--color-bg-surface)/95 border border-(--color-border) rounded-lg px-3 py-2 shadow-lg backdrop-blur-sm"
            style={{
              left: Math.min(hoverValue.x, (containerRef.current?.clientWidth ?? 300) - 180),
              top: Math.max(0, hoverValue.y - 60),
            }}
          >
            <p className="text-[10px] text-(--color-text-secondary) font-mono">
              {hoverValue.date}, {hoverValue.time}
            </p>
            <p className="text-sm font-bold font-mono text-(--color-text-primary)">
              Total Balance: {fmtUsd(hoverValue.value)}
            </p>
          </div>
        )}
        {!(canRender && chartData.length >= 2) && (
          <div className="absolute inset-0 flex items-center justify-center">
            <p className="text-[11px] text-(--color-text-secondary)/50 text-center">
              {period !== "24H"
                ? "Historical tracking coming soon"
                : "Waiting for price data..."}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

/* ---- Portfolio Loading Animation ---- */

interface LoadingStep {
  label: string;
  source: string;
}

const _WAIT_MESSAGES = [
  "Resolving prices across exchanges...",
  "Checking fallback price sources...",
  "Aggregating balances...",
  "Almost there...",
];

function PortfolioLoader({ brokers }: { brokers: string[] }) {
  const [activeIdx, setActiveIdx] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const [waitMsgIdx, setWaitMsgIdx] = useState(0);

  // Build steps: connected brokers → manual → prices → finalize
  const steps = useMemo<LoadingStep[]>(() => {
    const result: LoadingStep[] = [];
    const unique = [...new Set(brokers)];
    for (const b of unique) {
      const style = SOURCE_STYLE[b];
      result.push({ label: style?.label ?? b, source: b });
    }
    result.push({ label: "Manual Holdings", source: "manual" });
    result.push({ label: "Resolving Live Prices", source: "prices" });
    result.push({ label: "Building Portfolio", source: "finalize" });
    return result;
  }, [brokers]);

  // Last step index — stays active/spinning until data arrives
  const lastIdx = steps.length - 1;

  // Cycle through steps — stop at the last step (keep it spinning)
  useEffect(() => {
    if (activeIdx >= lastIdx) return;
    const delay = activeIdx === 0 ? 600 : 1200 + Math.random() * 800;
    const timer = setTimeout(() => {
      setActiveIdx((i) => Math.min(i + 1, lastIdx));
    }, delay);
    return () => clearTimeout(timer);
  }, [activeIdx, lastIdx]);

  // Elapsed seconds timer
  useEffect(() => {
    const interval = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => clearInterval(interval);
  }, []);

  // Cycle wait messages once we reach the last step
  useEffect(() => {
    if (activeIdx < lastIdx) return;
    const interval = setInterval(() => {
      setWaitMsgIdx((i) => (i + 1) % _WAIT_MESSAGES.length);
    }, 3000);
    return () => clearInterval(interval);
  }, [activeIdx, lastIdx]);

  // Progress: steps complete fills 80%, then slow pulse from 80→95% on last step
  const stepsProgress = (Math.min(activeIdx, lastIdx) / steps.length) * 80;
  const extraProgress = activeIdx >= lastIdx ? Math.min((elapsed - lastIdx * 1.5) * 1.5, 15) : 0;
  const progressPct = Math.min(stepsProgress + Math.max(extraProgress, 0), 95);

  return (
    <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-6 space-y-5">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="relative">
          <Wallet className="w-5 h-5 text-(--color-accent)" />
          <div className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-(--color-accent) animate-ping" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-(--color-text-primary)">Loading Portfolio</h3>
            <span className="text-[10px] font-mono text-(--color-text-secondary) tabular-nums">
              {elapsed}s
            </span>
          </div>
          <p className="text-[11px] text-(--color-text-secondary)">
            {activeIdx >= lastIdx
              ? _WAIT_MESSAGES[waitMsgIdx]
              : `Fetching balances from ${steps.length - 2} source${steps.length - 2 !== 1 ? "s" : ""}...`}
          </p>
        </div>
      </div>

      {/* Progress bar */}
      <div className="w-full h-1.5 rounded-full bg-(--color-bg-elevated) overflow-hidden">
        <div
          className={cn(
            "h-full rounded-full bg-(--color-accent) transition-all ease-out",
            activeIdx >= lastIdx ? "duration-[2000ms]" : "duration-700",
          )}
          style={{ width: `${progressPct}%` }}
        />
      </div>

      {/* Step list */}
      <div className="space-y-2">
        {steps.map((step, i) => {
          const isDone = i < activeIdx;
          const isActive = i === activeIdx;
          const style = SOURCE_STYLE[step.source];

          return (
            <div
              key={step.source}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-lg transition-all duration-300",
                isDone && "bg-(--color-positive)/5",
                isActive && "bg-(--color-accent)/5",
                !isDone && !isActive && "opacity-40",
              )}
            >
              {/* Status icon */}
              <div className="w-5 h-5 flex items-center justify-center shrink-0">
                {isDone ? (
                  <svg className="w-4 h-4 text-(--color-positive)" viewBox="0 0 16 16" fill="none">
                    <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.5" />
                    <path d="M5 8l2 2 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                ) : isActive ? (
                  <Loader2 className="w-4 h-4 animate-spin text-(--color-accent)" />
                ) : (
                  <div className="w-3 h-3 rounded-full border border-(--color-border)" />
                )}
              </div>

              {/* Source badge + label */}
              <div className="flex items-center gap-2 min-w-0">
                {style && step.source !== "prices" && step.source !== "finalize" ? (
                  <span className={cn("text-[10px] font-medium px-2 py-0.5 rounded-full whitespace-nowrap", style.cls)}>
                    {step.label}
                  </span>
                ) : (
                  <span className="text-xs font-medium text-(--color-text-primary)">
                    {step.label}
                  </span>
                )}
              </div>

              {/* Status text */}
              <span className="ml-auto text-[10px] font-medium whitespace-nowrap">
                {isDone ? (
                  <span className="text-(--color-positive)">Done</span>
                ) : isActive ? (
                  <span className="text-(--color-accent) animate-pulse">
                    {step.source === "finalize" ? "Processing..." : "Fetching..."}
                  </span>
                ) : (
                  <span className="text-(--color-text-secondary)">Waiting</span>
                )}
              </span>
            </div>
          );
        })}
      </div>

      {/* Elapsed hint for long loads */}
      {elapsed >= 10 && (
        <p className="text-[10px] text-(--color-text-secondary)/60 text-center animate-pulse">
          Fetching prices from multiple exchanges can take a moment
        </p>
      )}
    </div>
  );
}

/* ---- Combined holding helpers ---- */

function combineHoldings(holdings: HoldingItem[], totalValue: number | null): CombinedHolding[] {
  const map: Record<string, CombinedHolding> = {};
  for (const h of holdings) {
    const key = h.symbol.toUpperCase();
    if (!map[key]) {
      map[key] = {
        symbol: key,
        name: CRYPTO_NAME_MAP[key] ?? key,
        totalQty: 0,
        currentPrice: h.current_price,
        totalValue: 0,
        change24hPct: h.change_24h_pct,
        allocPct: null,
        sources: [],
        marketCap: h.market_cap,
        marketCapRank: h.market_cap_rank,
        volume24h: h.volume_24h,
        imageUrl: h.image_url,
        avgCost: null,
        pnlUsd: null,
        pnlPct: null,
      };
    }
    const c = map[key];
    c.totalQty += h.quantity;
    c.totalValue += h.value_usd ?? 0;
    if (h.current_price != null) c.currentPrice = h.current_price;
    if (h.change_24h_pct != null) c.change24hPct = h.change_24h_pct;
    if (h.market_cap != null) c.marketCap = h.market_cap;
    if (h.market_cap_rank != null) c.marketCapRank = h.market_cap_rank;
    if (h.volume_24h != null) c.volume24h = h.volume_24h;
    if (h.image_url != null) c.imageUrl = h.image_url;
    c.sources.push({ source: h.source, notes: h.notes, qty: h.quantity, id: h.id, avgPrice: h.avg_price });
  }

  const result = Object.values(map);
  for (const c of result) {
    if (totalValue && totalValue > 0) {
      c.allocPct = (c.totalValue / totalValue) * 100;
    }
    // PnL from weighted average cost (no cost basis → treat today's price as purchase price → PNL = 0)
    const withCost = c.sources.filter((s) => s.avgPrice != null && s.avgPrice! > 0);
    if (withCost.length > 0) {
      const totalCostQty = withCost.reduce((sum, s) => sum + s.qty, 0);
      const weightedCost = withCost.reduce((sum, s) => sum + s.qty * (s.avgPrice ?? 0), 0);
      c.avgCost = totalCostQty > 0 ? weightedCost / totalCostQty : null;
    } else if (c.currentPrice != null) {
      // No purchase price recorded — use current price as cost basis (purchased today)
      c.avgCost = c.currentPrice;
    }
    if (c.avgCost != null && c.currentPrice != null && c.avgCost > 0) {
      c.pnlPct = ((c.currentPrice - c.avgCost) / c.avgCost) * 100;
      c.pnlUsd = (c.currentPrice - c.avgCost) * c.totalQty;
    }
  }
  return result;
}

/* ---- Sort helpers ---- */

type SortKey = "value" | "symbol" | "change" | "allocation" | "rank" | "marketCap" | "volume" | "pnl";
type SortDir = "asc" | "desc";

function sortCombined(holdings: CombinedHolding[], key: SortKey, dir: SortDir): CombinedHolding[] {
  const sorted = [...holdings];
  const m = dir === "asc" ? 1 : -1;
  sorted.sort((a, b) => {
    switch (key) {
      case "value":
        return m * (a.totalValue - b.totalValue);
      case "symbol":
        return m * a.symbol.localeCompare(b.symbol);
      case "change":
        return m * ((a.change24hPct ?? 0) - (b.change24hPct ?? 0));
      case "allocation":
        return m * ((a.allocPct ?? 0) - (b.allocPct ?? 0));
      case "rank":
        return m * ((a.marketCapRank ?? 9999) - (b.marketCapRank ?? 9999));
      case "marketCap":
        return m * ((a.marketCap ?? 0) - (b.marketCap ?? 0));
      case "volume":
        return m * ((a.volume24h ?? 0) - (b.volume24h ?? 0));
      case "pnl":
        return m * ((a.pnlPct ?? 0) - (b.pnlPct ?? 0));
      default:
        return 0;
    }
  });
  return sorted;
}

function SortHeader({
  label,
  sortKey,
  activeKey,
  activeDir,
  onSort,
  className,
}: {
  label: string;
  sortKey: SortKey;
  activeKey: SortKey;
  activeDir: SortDir;
  onSort: (key: SortKey) => void;
  className?: string;
}) {
  const isActive = sortKey === activeKey;
  return (
    <th
      className={cn(
        "text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider py-2 px-3 cursor-pointer select-none hover:text-(--color-text-primary) transition-colors",
        className,
      )}
      onClick={() => onSort(sortKey)}
    >
      <span className="inline-flex items-center gap-0.5">
        {label}
        {isActive && (activeDir === "desc" ? <ChevronDown className="w-3 h-3" /> : <ChevronUp className="w-3 h-3" />)}
      </span>
    </th>
  );
}

/* ---- Main Card ---- */

export function HoldingsCard() {
  const { data, isLoading } = useHoldings();
  const { data: brokerConns } = useBrokerConnections();
  const deleteMutation = useDeleteHolding();
  const [showForm, setShowForm] = useState(false);
  const [editItem, setEditItem] = useState<HoldingItem | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>("value");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [hideSmall, setHideSmall] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [detailSymbol, setDetailSymbol] = useState<string | null>(null);
  const [sourceFilter, setSourceFilter] = useState<string | null>(null);
  const [categoryFilter, setCategoryFilter] = useState<"stablecoins" | null>(null);

  const hasActiveFilter = sourceFilter !== null || categoryFilter !== null;

  function applyFilter(type: "source" | "category", value: string) {
    if (type === "source") {
      setSourceFilter((prev) => (prev === value ? null : value));
      setCategoryFilter(null);
    } else {
      setCategoryFilter((prev) => (prev === (value as "stablecoins") ? null : (value as "stablecoins")));
      setSourceFilter(null);
    }
  }

  function clearAllFilters() {
    setSourceFilter(null);
    setCategoryFilter(null);
    setSearchQuery("");
  }

  // Reveal animation: only triggers on loading → loaded transition
  const wasLoadingRef = useRef(isLoading);
  const [reveal, setReveal] = useState(!isLoading);

  useEffect(() => {
    if (wasLoadingRef.current && !isLoading) {
      // Small delay so the DOM renders in hidden state first
      const id = requestAnimationFrame(() => setReveal(true));
      return () => cancelAnimationFrame(id);
    }
    wasLoadingRef.current = isLoading;
  }, [isLoading]);

  const allHoldings = data?.holdings ?? [];
  const totalValue = data?.total_value_usd ?? null;

  function handleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir((d) => (d === "desc" ? "asc" : "desc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  }

  // Group holdings by symbol for detail modal
  const holdingsBySymbol = useMemo(() => {
    const map: Record<string, HoldingItem[]> = {};
    for (const h of allHoldings) {
      const key = h.symbol.toUpperCase();
      (map[key] ??= []).push(h);
    }
    return map;
  }, [allHoldings]);

  // Combined holdings (merged by symbol)
  const allCombined = useMemo(
    () => combineHoldings(allHoldings, totalValue),
    [allHoldings, totalValue],
  );

  // Counts before filtering
  const smallCount = allCombined.filter((c) => c.totalValue < SMALL_BALANCE_THRESHOLD).length;

  // Apply filters — source filter works on RAW holdings before combining
  // so that only the source-specific quantity/value is shown
  const filteredCombined = useMemo(() => {
    let base: CombinedHolding[];

    if (sourceFilter) {
      // Re-combine from only the holdings matching this source
      const sourceHoldings = allHoldings.filter((h) => h.source === sourceFilter);
      const tv = sourceHoldings.reduce((sum, h) => sum + (h.value_usd ?? 0), 0);
      base = combineHoldings(sourceHoldings, tv > 0 ? tv : null);
    } else {
      base = allCombined;
    }

    let list = base;
    if (categoryFilter === "stablecoins") {
      list = list.filter((c) => STABLECOINS.has(c.symbol.toUpperCase()));
    }
    if (hideSmall) {
      list = list.filter((c) => c.totalValue >= SMALL_BALANCE_THRESHOLD);
    }
    if (searchQuery.trim()) {
      const q = searchQuery.trim().toLowerCase();
      list = list.filter(
        (c) =>
          c.symbol.toLowerCase().includes(q) ||
          c.name.toLowerCase().includes(q) ||
          c.sources.some((s) => s.source.toLowerCase().includes(q)) ||
          c.sources.some((s) => s.notes?.toLowerCase().includes(q)),
      );
    }
    return list;
  }, [allHoldings, allCombined, sourceFilter, categoryFilter, hideSmall, searchQuery]);

  const sorted = sortCombined(filteredCombined, sortKey, sortDir);

  // Donut chart: reflects source/category filters but NOT hideSmall/search
  const donutSource = useMemo(() => {
    let base: CombinedHolding[];
    if (sourceFilter) {
      const sourceHoldings = allHoldings.filter((h) => h.source === sourceFilter);
      const tv = sourceHoldings.reduce((sum, h) => sum + (h.value_usd ?? 0), 0);
      base = combineHoldings(sourceHoldings, tv > 0 ? tv : null);
    } else {
      base = allCombined;
    }
    if (categoryFilter === "stablecoins") {
      base = base.filter((c) => STABLECOINS.has(c.symbol.toUpperCase()));
    }
    return base;
  }, [allHoldings, allCombined, sourceFilter, categoryFilter]);
  const donutTotal = donutSource.reduce((sum, c) => sum + c.totalValue, 0);

  const donutSlices: DonutSlice[] = useMemo(() => {
    // Show donut if there are any holdings, even if total value is tiny/zero
    const hasAny = donutSource.some((c) => c.totalQty > 0 || c.totalValue > 0);
    if (!hasAny) return [];
    const effectiveTotal = donutTotal > 0 ? donutTotal : donutSource.reduce((s, c) => s + Math.max(c.totalValue, 0.01), 0);
    const byValue = [...donutSource]
      .filter((c) => c.totalQty > 0 || c.totalValue > 0)
      .sort((a, b) => b.totalValue - a.totalValue);

    const topN = byValue.slice(0, 9);
    const rest = byValue.slice(9);
    const restValue = rest.reduce((sum, c) => sum + c.totalValue, 0);

    const slices: DonutSlice[] = topN.map((c, i) => ({
      label: c.symbol,
      value: c.totalValue,
      pct: (Math.max(c.totalValue, 0.01) / effectiveTotal) * 100,
      color: DONUT_COLORS[i % DONUT_COLORS.length],
    }));

    if (restValue > 0 || rest.length > 0) {
      const rv = rest.length > 0 ? Math.max(restValue, 0.01 * rest.length) : restValue;
      slices.push({
        label: `Other (${rest.length})`,
        value: restValue,
        pct: (rv / effectiveTotal) * 100,
        color: "#4b5563", // gray
      });
    }

    return slices;
  }, [donutSource, donutTotal]);

  // 24h portfolio change (computed from holdings for the chart)
  const portfolioChange = useMemo(() => {
    const changeUsd = allCombined.reduce((sum, c) => {
      if (c.change24hPct != null && c.totalValue > 0) {
        return sum + (c.totalValue * c.change24hPct) / (100 + c.change24hPct);
      }
      return sum;
    }, 0);
    const tv = totalValue ?? 0;
    const changePct = tv > 0 ? (changeUsd / (tv - changeUsd)) * 100 : 0;
    return { changeUsd, changePct };
  }, [allCombined, totalValue]);

  // Holdings data for chart (value + 24h change per holding)
  const chartHoldings = useMemo(
    () => allCombined.map((c) => ({ value: c.totalValue, change24hPct: c.change24hPct })),
    [allCombined],
  );

  if (isLoading) {
    const connectedBrokers = (brokerConns ?? [])
      .filter((c) => c.purpose === "read")
      .map((c) => c.broker);
    return <PortfolioLoader brokers={connectedBrokers} />;
  }

  if (allHoldings.length === 0) {
    return (
      <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-5 space-y-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Wallet className="w-4 h-4 text-(--color-accent)" />
            <Tooltip text="Your complete crypto portfolio aggregated from all connected exchanges and manual entries."><h3 className="text-sm font-semibold text-(--color-text-primary) cursor-help">Crypto Holdings</h3></Tooltip>
          </div>
          <button
            onClick={() => setShowForm(true)}
            className="flex items-center gap-1 text-xs font-medium text-(--color-accent) hover:text-(--color-accent)/80 transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            Add holding
          </button>
        </div>
        {showForm && <HoldingForm onClose={() => setShowForm(false)} />}
        {!showForm && (
          <div className="flex flex-col items-center justify-center py-6 gap-2">
            <Wallet className="w-8 h-8 text-(--color-text-secondary)/30" />
            <p className="text-sm text-(--color-text-secondary)">No holdings found</p>
            <p className="text-xs text-(--color-text-secondary)/60">
              Connect an exchange or add holdings manually
            </p>
            <button
              onClick={() => setShowForm(true)}
              className="text-xs font-medium text-(--color-accent) hover:underline mt-1"
            >
              Add your first holding
            </button>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* ===== Overview Card ===== */}
      <div
        className={cn(
          "bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-3 sm:p-5 space-y-4 sm:space-y-5 transition-all duration-600 ease-out",
          reveal ? "opacity-100 translate-y-0" : "opacity-0 translate-y-5",
        )}
      >
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Wallet className="w-4 h-4 text-(--color-accent)" />
            <Tooltip text="Allocation breakdown showing how your portfolio is distributed across assets."><h3 className="text-sm font-semibold text-(--color-text-primary) cursor-help">Portfolio Overview</h3></Tooltip>
          </div>
          <div className="flex items-center gap-1.5 flex-wrap w-full sm:w-auto">
            {[...new Set(allHoldings.map((h) => h.source))].map((s) => (
              <SourceBadge
                key={s}
                source={s}
                onClick={() => applyFilter("source", s)}
                active={sourceFilter === s}
              />
            ))}
          </div>
        </div>

        {/* Overview metric cards */}
        {totalValue != null && totalValue > 0 && (
          <PortfolioOverviewHeader
            totalValue={totalValue}
            combined={allCombined}
            onTopClick={(symbol) => setDetailSymbol(symbol)}
          />
        )}

        {/* Holdings donut + Portfolio value chart — CoinGecko-style */}
        <div className="grid grid-cols-1 lg:grid-cols-[2fr_3fr] gap-5">
          {/* Left: Holdings donut */}
          <div
            className={cn(
              "bg-(--color-bg-elevated)/30 rounded-lg p-3 sm:p-4 transition-all duration-700 ease-out space-y-3 overflow-hidden min-w-0",
              reveal ? "opacity-100 scale-100" : "opacity-0 scale-90",
            )}
            style={{ transitionDelay: "150ms" }}
          >
            <p className="text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">
              Holdings
            </p>
            {donutSlices.length > 0 ? (
              <DonutChart
                slices={donutSlices}
                totalValue={donutTotal}
                onSliceClick={(label) => {
                  if (!label.startsWith("Other")) setDetailSymbol(label);
                }}
              />
            ) : (
              <div className="flex flex-col items-center justify-center py-8 gap-2">
                <Wallet className="w-8 h-8 text-(--color-text-secondary)/20" />
                <p className="text-xs text-(--color-text-secondary)/60">
                  {sourceFilter
                    ? `No holdings from ${SOURCE_STYLE[sourceFilter]?.label ?? sourceFilter}`
                    : "No holdings to display"}
                </p>
              </div>
            )}
          </div>

          {/* Right: Portfolio value chart */}
          <div
            className={cn(
              "bg-(--color-bg-elevated)/30 rounded-lg p-3 sm:p-4 transition-all duration-600 ease-out min-w-0 min-h-[280px]",
              reveal ? "opacity-100 translate-y-0" : "opacity-0 translate-y-3",
            )}
            style={{ transitionDelay: "250ms" }}
          >
            <PortfolioValueChart
              totalValue={totalValue ?? 0}
              change24hUsd={portfolioChange.changeUsd}
              change24hPct={portfolioChange.changePct}
              holdings={chartHoldings}
            />
          </div>
        </div>

        {/* Source breakdown — compact row */}
        {totalValue != null && totalValue > 0 && (
          <div
            className={cn(
              "transition-all duration-600 ease-out",
              reveal ? "opacity-100 translate-y-0" : "opacity-0 translate-y-3",
            )}
            style={{ transitionDelay: "300ms" }}
          >
            <SourceBreakdown
              holdings={allHoldings}
              totalValue={totalValue}
              onSourceClick={(source) => applyFilter("source", source)}
              activeSource={sourceFilter}
            />
          </div>
        )}

      </div>

      {/* Active filter indicator */}
      {hasActiveFilter && (
        <div
          className={cn(
            "flex items-center justify-between bg-(--color-accent)/5 border border-(--color-accent)/20 rounded-lg px-3 sm:px-4 py-2 sm:py-2.5 transition-all duration-300 ease-out",
            reveal ? "opacity-100 translate-y-0" : "opacity-0 translate-y-5",
          )}
          style={{ transitionDelay: "180ms" }}
        >
          <div className="flex items-center gap-2">
            <span className="text-xs text-(--color-text-secondary)">Filtered by:</span>
            {sourceFilter && (
              <span className={cn(
                "text-xs font-semibold px-2.5 py-0.5 rounded-full",
                SOURCE_STYLE[sourceFilter]?.cls ?? "bg-(--color-bg-elevated) text-(--color-text-primary)",
              )}>
                {SOURCE_STYLE[sourceFilter]?.label ?? sourceFilter}
              </span>
            )}
            {categoryFilter === "stablecoins" && (
              <span className="text-xs font-semibold text-(--color-accent) bg-(--color-accent)/10 px-2.5 py-0.5 rounded-full">
                Stablecoins
              </span>
            )}
            <span className="text-[11px] text-(--color-text-secondary) font-mono">
              {filteredCombined.length} of {allCombined.length} assets
            </span>
          </div>
          <button
            onClick={clearAllFilters}
            className="flex items-center gap-1 text-xs font-medium text-(--color-text-secondary) hover:text-(--color-text-primary) transition-colors"
          >
            <X className="w-3 h-3" />
            Clear
          </button>
        </div>
      )}

      {/* ===== Holdings Table Card ===== */}
      <div
        className={cn(
          "bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-3 sm:p-5 space-y-4 transition-all duration-600 ease-out",
          reveal ? "opacity-100 translate-y-0" : "opacity-0 translate-y-5",
        )}
        style={{ transitionDelay: "200ms" }}
      >
        {/* Table header with controls */}
        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <Tooltip text="Detailed list of every asset you hold with live prices, 24h changes, and P&L."><h3 className="text-sm font-semibold text-(--color-text-primary) cursor-help">All Assets</h3></Tooltip>
            {!showForm && !editItem && (
              <button
                onClick={() => setShowForm(true)}
                className="flex items-center gap-1 text-xs font-medium text-(--color-accent) hover:text-(--color-accent)/80 transition-colors"
              >
                <Plus className="w-3.5 h-3.5" />
                Add
              </button>
            )}
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            {/* Search */}
            <div className="relative flex-1 min-w-[120px] max-w-[200px]">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-(--color-text-secondary)" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search assets..."
                className="w-full bg-(--color-bg-elevated) border border-(--color-border) rounded-lg pl-8 pr-3 py-1.5 text-xs text-(--color-text-primary) focus:outline-none focus:ring-2 focus:ring-(--color-accent)/50 placeholder:text-(--color-text-secondary)/50"
              />
            </div>

            {/* Stablecoins filter */}
            <button
              onClick={() => applyFilter("category", "stablecoins")}
              className={cn(
                "flex items-center gap-1.5 px-2 sm:px-2.5 py-1.5 rounded-lg text-[11px] sm:text-xs font-medium transition-colors border whitespace-nowrap",
                categoryFilter === "stablecoins"
                  ? "bg-(--color-accent)/10 border-(--color-accent)/30 text-(--color-accent)"
                  : "bg-(--color-bg-elevated) border-(--color-border) text-(--color-text-secondary) hover:text-(--color-text-primary)",
              )}
            >
              Stablecoins
            </button>

            {/* Hide small toggle */}
            {smallCount > 0 && (
              <button
                onClick={() => setHideSmall(!hideSmall)}
                className={cn(
                  "flex items-center gap-1 sm:gap-1.5 px-2 sm:px-2.5 py-1.5 rounded-lg text-[11px] sm:text-xs font-medium transition-colors border whitespace-nowrap",
                  hideSmall
                    ? "bg-(--color-accent)/10 border-(--color-accent)/30 text-(--color-accent)"
                    : "bg-(--color-bg-elevated) border-(--color-border) text-(--color-text-secondary) hover:text-(--color-text-primary)",
                )}
              >
                {hideSmall ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
                {hideSmall ? `${smallCount} hidden` : `Hide <$1`}
              </button>
            )}
          </div>
        </div>

        {/* Add form */}
        {showForm && <HoldingForm onClose={() => setShowForm(false)} />}

        {/* Edit form */}
        {editItem && (
          <HoldingForm initial={editItem} onClose={() => setEditItem(null)} />
        )}

        {/* Table */}
        {sorted.length === 0 ? (
          <p className="text-sm text-(--color-text-secondary) text-center py-4">
            {searchQuery ? "No assets match your search" : hasActiveFilter ? "No assets match this filter" : "No assets to display"}
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm table-fixed sm:table-auto">
              <thead>
                <tr className="border-b border-(--color-border)">
                  <SortHeader label="#" sortKey="rank" activeKey={sortKey} activeDir={sortDir} onSort={handleSort} className="text-left w-10 hidden sm:table-cell" />
                  <SortHeader label="Coin" sortKey="symbol" activeKey={sortKey} activeDir={sortDir} onSort={handleSort} className="text-left" />
                  <th className="text-right text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider py-2 px-3 hidden md:table-cell">Price</th>
                  <SortHeader label="24h" sortKey="change" activeKey={sortKey} activeDir={sortDir} onSort={handleSort} className="text-right hidden sm:table-cell" />
                  <SortHeader label="Mkt Cap" sortKey="marketCap" activeKey={sortKey} activeDir={sortDir} onSort={handleSort} className="text-right hidden lg:table-cell" />
                  <SortHeader label="Volume" sortKey="volume" activeKey={sortKey} activeDir={sortDir} onSort={handleSort} className="text-right hidden lg:table-cell" />
                  <SortHeader label="Holdings" sortKey="value" activeKey={sortKey} activeDir={sortDir} onSort={handleSort} className="text-right w-28 sm:w-auto min-w-[90px]" />
                  <SortHeader label="PNL" sortKey="pnl" activeKey={sortKey} activeDir={sortDir} onSort={handleSort} className="text-right hidden sm:table-cell" />
                  <th className="text-left text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider py-2 px-3 hidden md:table-cell">Source</th>
                  <th className="py-2 w-16 hidden sm:table-cell" />
                </tr>
              </thead>
              <tbody>
                {sorted.map((c, i) => (
                  <HoldingRow
                    key={c.symbol}
                    c={c}
                    index={i}
                    reveal={reveal}
                    onDetail={(symbol) => setDetailSymbol(symbol)}
                    onEdit={(holdingId) => {
                      const raw = allHoldings.find((h) => h.id === holdingId);
                      if (raw) { setShowForm(false); setEditItem(raw); }
                    }}
                    onDelete={(holdingId) => deleteMutation.mutate(holdingId)}
                    isDeletePending={deleteMutation.isPending}
                  />
                ))}
              </tbody>

              {/* Footer with total */}
              {totalValue != null && (() => {
                const footerHoldings = hasActiveFilter || hideSmall || searchQuery.trim()
                  ? filteredCombined
                  : allCombined;
                const footerTotal = hasActiveFilter || hideSmall || searchQuery.trim()
                  ? footerHoldings.reduce((sum, c) => sum + c.totalValue, 0)
                  : (totalValue ?? 0);
                const footerPnlUsd = footerHoldings.reduce((sum, c) => sum + (c.pnlUsd ?? 0), 0);
                const footerCostBasis = footerHoldings.reduce((sum, c) => {
                  if (c.avgCost != null) return sum + c.avgCost * c.totalQty;
                  return sum;
                }, 0);
                const footerPnlPct = footerCostBasis > 0
                  ? (footerPnlUsd / footerCostBasis) * 100
                  : null;
                const hasFooterPnl = footerHoldings.some((c) => c.pnlUsd != null);
                return (
                  <tfoot>
                    <tr
                      className={cn(
                        "border-t border-(--color-border) transition-all duration-500 ease-out",
                        reveal ? "opacity-100" : "opacity-0",
                      )}
                      style={{ transitionDelay: `${350 + sorted.length * 40 + 80}ms` }}
                    >
                      <td className="hidden sm:table-cell" />{/* rank spacer */}
                      <td className="py-3 px-2 sm:px-3 text-xs font-semibold text-(--color-text-secondary) uppercase tracking-wider">
                        {hasActiveFilter || hideSmall
                          ? `Showing ${filteredCombined.length} of ${allCombined.length}`
                          : "Total"}
                      </td>
                      <td className="hidden md:table-cell" />{/* price spacer */}
                      <td className="hidden sm:table-cell" />{/* 24h spacer */}
                      <td className="hidden lg:table-cell" />{/* mkt cap spacer */}
                      <td className="hidden lg:table-cell" />{/* volume spacer */}
                      <td className="py-3 px-3 text-right font-mono tabular-nums text-(--color-text-primary) font-bold text-sm">
                        {fmtUsd(footerTotal)}
                      </td>
                      <td className="py-3 px-3 text-right hidden sm:table-cell">
                        {hasFooterPnl ? (
                          <div className="font-mono tabular-nums">
                            <span className={cn("text-xs font-bold block", pnlColor(footerPnlUsd))}>
                              {footerPnlUsd >= 0 ? "+" : ""}{fmtUsd(Math.abs(footerPnlUsd))}
                            </span>
                            {footerPnlPct != null && (
                              <span className={cn("text-[10px]", pnlColor(footerPnlPct))}>
                                {footerPnlPct >= 0 ? "+" : ""}{footerPnlPct.toFixed(1)}%
                              </span>
                            )}
                          </div>
                        ) : (
                          <span className="text-xs text-(--color-text-secondary)">—</span>
                        )}
                      </td>
                      <td className="hidden md:table-cell" />{/* source spacer */}
                      <td className="hidden sm:table-cell" />{/* actions spacer */}
                    </tr>
                  </tfoot>
                );
              })()}
            </table>
          </div>
        )}
      </div>

      {/* Asset detail modal */}
      {detailSymbol && (
        <AssetDetailModal
          open={!!detailSymbol}
          onClose={() => setDetailSymbol(null)}
          symbol={detailSymbol}
          holdings={holdingsBySymbol[detailSymbol] ?? []}
          totalPortfolioValue={totalValue ?? 0}
        />
      )}
    </div>
  );
}
