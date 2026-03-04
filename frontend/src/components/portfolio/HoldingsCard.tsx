import { useState, useMemo, useRef, useEffect, useCallback } from "react";
import {
  Loader2,
  Plus,
  X,
  Pencil,
  Trash2,
  Wallet,
  TrendingUp,
  TrendingDown,
  ChevronDown,
  ChevronUp,
  Search,
  EyeOff,
  Eye,
} from "lucide-react";
import { cn } from "@/lib/cn";
import { pnlColor, formatPrice } from "@/lib/format";
import { CRYPTO_LIST, CRYPTO_NAME_MAP } from "@/lib/cryptoSymbols";
import type { CryptoEntry } from "@/lib/cryptoSymbols";
import {
  useHoldings,
  useAddHolding,
  useUpdateHolding,
  useDeleteHolding,
} from "@/hooks/useHoldings";
import type { HoldingItem, ManualHoldingRequest } from "@/hooks/useHoldings";
import { useBrokerConnections } from "@/hooks/useBrokerConnections";
import { AssetDetailModal } from "./AssetDetailModal";

/* ---- Constants ---- */

const DONUT_COLORS = [
  "#3b82f6", // blue
  "#f59e0b", // amber
  "#10b981", // emerald
  "#8b5cf6", // violet
  "#f43f5e", // rose
  "#06b6d4", // cyan
  "#f97316", // orange
  "#ec4899", // pink
  "#14b8a6", // teal
  "#6366f1", // indigo
];

const SOURCE_STYLE: Record<string, { label: string; cls: string; color: string }> = {
  binance: { label: "Binance", cls: "bg-amber-500/10 text-amber-500", color: "#f59e0b" },
  kucoin: { label: "KuCoin", cls: "bg-emerald-500/10 text-emerald-500", color: "#10b981" },
  mexc: { label: "MEXC", cls: "bg-blue-500/10 text-blue-500", color: "#3b82f6" },
  bitstamp: { label: "Bitstamp", cls: "bg-green-500/10 text-green-500", color: "#22c55e" },
  cryptocom: { label: "Crypto.com", cls: "bg-indigo-500/10 text-indigo-500", color: "#6366f1" },
  kraken: { label: "Kraken", cls: "bg-violet-500/10 text-violet-500", color: "#8b5cf6" },
  manual: { label: "Manual", cls: "bg-(--color-bg-elevated) text-(--color-text-secondary)", color: "#6b7280" },
  trading: { label: "Trading", cls: "bg-(--color-accent)/10 text-(--color-accent)", color: "#3b82f6" },
};

const STABLECOINS = new Set(["USDT", "USDC", "BUSD", "DAI", "TUSD", "FDUSD", "USDP", "USD"]);
const SMALL_BALANCE_THRESHOLD = 1; // $1

/* ---- Helpers ---- */

function fmtUsd(val: number): string {
  return `$${val.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function fmtCompact(val: number): string {
  if (val >= 1e12) return `$${(val / 1e12).toFixed(2)}T`;
  if (val >= 1e9) return `$${(val / 1e9).toFixed(2)}B`;
  if (val >= 1e6) return `$${(val / 1e6).toFixed(1)}M`;
  if (val >= 1e3) return `$${(val / 1e3).toFixed(1)}K`;
  return fmtUsd(val);
}

/* ---- Coin Icon ---- */

function CoinIcon({ symbol, imageUrl, size = 24 }: { symbol: string; imageUrl: string | null; size?: number }) {
  const [error, setError] = useState(false);

  if (imageUrl && !error) {
    return (
      <img
        src={imageUrl}
        alt={symbol}
        width={size}
        height={size}
        className="rounded-full shrink-0"
        onError={() => setError(true)}
        loading="lazy"
      />
    );
  }

  const colorIndex = symbol.charCodeAt(0) % DONUT_COLORS.length;
  return (
    <div
      className="rounded-full shrink-0 flex items-center justify-center text-white font-bold"
      style={{ width: size, height: size, backgroundColor: DONUT_COLORS[colorIndex], fontSize: size * 0.45 }}
    >
      {symbol.charAt(0)}
    </div>
  );
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

/* ---- SVG Donut Chart ---- */

interface DonutSlice {
  label: string;
  value: number;
  pct: number;
  color: string;
}

function DonutChart({
  slices,
  totalValue,
  onSliceClick,
}: {
  slices: DonutSlice[];
  totalValue: number;
  onSliceClick?: (label: string) => void;
}) {
  const size = 200;
  const cx = size / 2;
  const cy = size / 2;
  const outerR = 88;
  const innerR = 62;
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  // Build arcs
  let cumAngle = -90; // start at top
  const arcs = slices.map((s, i) => {
    const angle = (s.pct / 100) * 360;
    const startAngle = cumAngle;
    cumAngle += angle;
    const endAngle = cumAngle;
    const largeArc = angle > 180 ? 1 : 0;

    const r = outerR;
    const ir = innerR;

    const toRad = (a: number) => (a * Math.PI) / 180;
    const x1o = cx + r * Math.cos(toRad(startAngle));
    const y1o = cy + r * Math.sin(toRad(startAngle));
    const x2o = cx + r * Math.cos(toRad(endAngle));
    const y2o = cy + r * Math.sin(toRad(endAngle));
    const x1i = cx + ir * Math.cos(toRad(endAngle));
    const y1i = cy + ir * Math.sin(toRad(endAngle));
    const x2i = cx + ir * Math.cos(toRad(startAngle));
    const y2i = cy + ir * Math.sin(toRad(startAngle));

    const d = [
      `M ${x1o} ${y1o}`,
      `A ${r} ${r} 0 ${largeArc} 1 ${x2o} ${y2o}`,
      `L ${x1i} ${y1i}`,
      `A ${ir} ${ir} 0 ${largeArc} 0 ${x2i} ${y2i}`,
      "Z",
    ].join(" ");

    return { d, color: s.color, label: s.label, pct: s.pct, value: s.value, idx: i };
  });

  return (
    <div className="flex flex-col items-center gap-3">
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        className="shrink-0"
      >
        {arcs.map((arc) => (
          <path
            key={arc.idx}
            d={arc.d}
            fill={arc.color}
            opacity={hoveredIdx != null && hoveredIdx !== arc.idx ? 0.4 : 1}
            className="transition-opacity duration-150"
            onMouseEnter={() => setHoveredIdx(arc.idx)}
            onMouseLeave={() => setHoveredIdx(null)}
            onClick={() => onSliceClick?.(arc.label)}
            style={{ cursor: "pointer" }}
          />
        ))}
        {/* Center text */}
        <text x={cx} y={cy - 8} textAnchor="middle" className="fill-(--color-text-secondary) text-[10px]" fontSize="10">
          Total Value
        </text>
        <text x={cx} y={cy + 12} textAnchor="middle" className="fill-(--color-text-primary) font-bold" fontSize="16">
          {fmtUsd(totalValue)}
        </text>
      </svg>

      {/* Hover tooltip text — fixed height to prevent layout shift */}
      <div className={cn("text-center h-5 -mt-1 transition-opacity duration-150", hoveredIdx != null ? "opacity-100" : "opacity-0")}>
        {hoveredIdx != null && slices[hoveredIdx] && (
          <>
            <span className="text-xs font-semibold text-(--color-text-primary)">
              {slices[hoveredIdx].label}
            </span>
            <span className="text-xs text-(--color-text-secondary) ml-1.5">
              {fmtUsd(slices[hoveredIdx].value)} ({slices[hoveredIdx].pct.toFixed(1)}%)
            </span>
          </>
        )}
      </div>

      {/* Legend */}
      <div className="grid grid-cols-2 gap-x-5 gap-y-1.5 w-full">
        {slices.map((s, i) => (
          <div
            key={`${s.label}-${i}`}
            className="flex items-center gap-2 cursor-pointer"
            onMouseEnter={() => setHoveredIdx(i)}
            onMouseLeave={() => setHoveredIdx(null)}
            onClick={() => onSliceClick?.(s.label)}
          >
            <div className="w-2.5 h-2.5 rounded-sm shrink-0" style={{ backgroundColor: s.color }} />
            <span className="text-[11px] text-(--color-text-secondary) truncate">{s.label}</span>
            <span className="text-[11px] font-mono font-medium text-(--color-text-primary) ml-auto">
              {s.pct.toFixed(1)}%
            </span>
          </div>
        ))}
      </div>
    </div>
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

  // Top performer 24h
  const withChange = combined.filter((c) => c.change24hPct != null);
  const topPerformer = withChange.length > 0
    ? withChange.reduce((a, b) => ((a.change24hPct ?? 0) > (b.change24hPct ?? 0) ? a : b))
    : null;

  // 24h change value for top performer
  const topChange = topPerformer
    ? (topPerformer.totalValue * (topPerformer.change24hPct ?? 0)) / (100 + (topPerformer.change24hPct ?? 0))
    : 0;

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      {/* Current Balance */}
      <div className="bg-(--color-bg-elevated)/50 rounded-lg px-4 py-3 space-y-1">
        <p className="text-[10px] font-medium text-(--color-text-secondary) uppercase tracking-wider">Current Balance</p>
        <p className="text-lg font-bold font-mono text-(--color-text-primary)">{fmtUsd(totalValue)}</p>
        <p className="text-xs text-(--color-text-secondary)">{combined.length} asset{combined.length !== 1 ? "s" : ""}</p>
      </div>

      {/* 24h Change */}
      <div className="bg-(--color-bg-elevated)/50 rounded-lg px-4 py-3 space-y-1">
        <p className="text-[10px] font-medium text-(--color-text-secondary) uppercase tracking-wider">24h Portfolio Change</p>
        <p className={cn("text-lg font-bold font-mono", pnlColor(change24hUsd))}>
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
      <div className="bg-(--color-bg-elevated)/50 rounded-lg px-4 py-3 space-y-1">
        <p className="text-[10px] font-medium text-(--color-text-secondary) uppercase tracking-wider">Total Profit / Loss</p>
        {hasCostBasis ? (
          <>
            <p className={cn("text-lg font-bold font-mono", pnlColor(totalPnlUsd))}>
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
          "bg-(--color-bg-elevated)/50 rounded-lg px-4 py-3 space-y-1 transition-all duration-150",
          topPerformer && "cursor-pointer hover:bg-(--color-bg-elevated)/80 hover:-translate-y-0.5",
        )}
      >
        <p className="text-[10px] font-medium text-(--color-text-secondary) uppercase tracking-wider">Top Performer 24h</p>
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

  return (
    <div className="space-y-2.5">
      <p className="text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">
        By Source
      </p>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
        {bySource.map((s) => {
          const style = SOURCE_STYLE[s.source];
          const isActive = activeSource === s.source;
          return (
            <div
              key={s.source}
              onClick={() => onSourceClick(s.source)}
              className={cn(
                "bg-(--color-bg-elevated)/50 rounded-lg px-3 py-2.5 space-y-1 transition-all duration-150 cursor-pointer",
                "hover:bg-(--color-bg-elevated)/80 hover:-translate-y-0.5",
                isActive && "ring-2 ring-offset-1 ring-offset-(--color-bg-surface)",
              )}
              style={isActive ? { boxShadow: `0 0 0 2px ${style?.color ?? "#6b7280"}40` } : undefined}
            >
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: style?.color ?? "#6b7280" }} />
                <span className="text-xs font-semibold text-(--color-text-primary)">
                  {style?.label ?? s.source}
                </span>
              </div>
              <p className="text-sm font-bold font-mono text-(--color-text-primary)">
                {fmtUsd(s.value)}
              </p>
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-(--color-text-secondary)">
                  {s.count} asset{s.count !== 1 ? "s" : ""}
                </span>
                <span className="text-[10px] font-mono text-(--color-text-secondary)">
                  {s.pct.toFixed(1)}%
                </span>
              </div>
              {/* Mini progress bar */}
              <div className="w-full h-1 rounded-full bg-(--color-bg-surface) overflow-hidden">
                <div
                  className="h-full rounded-full transition-all"
                  style={{ width: `${Math.min(s.pct, 100)}%`, backgroundColor: style?.color ?? "#6b7280" }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ---- Symbol Autocomplete ---- */

function SymbolAutocomplete({
  value,
  onChange,
}: {
  value: string;
  onChange: (val: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [highlightIdx, setHighlightIdx] = useState(-1);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const query = value.trim().toUpperCase();

  const suggestions: CryptoEntry[] = useMemo(() => {
    if (!query) return [];
    return CRYPTO_LIST.filter(
      (c) =>
        c.symbol.includes(query) ||
        c.name.toUpperCase().includes(query),
    ).slice(0, 8);
  }, [query]);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  // Scroll highlighted item into view
  useEffect(() => {
    if (highlightIdx >= 0 && listRef.current) {
      const el = listRef.current.children[highlightIdx] as HTMLElement | undefined;
      el?.scrollIntoView({ block: "nearest" });
    }
  }, [highlightIdx]);

  const selectItem = useCallback(
    (entry: CryptoEntry) => {
      onChange(entry.symbol);
      setOpen(false);
      setHighlightIdx(-1);
    },
    [onChange],
  );

  function handleKeyDown(e: React.KeyboardEvent) {
    if (!open || suggestions.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlightIdx((i) => (i + 1) % suggestions.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlightIdx((i) => (i <= 0 ? suggestions.length - 1 : i - 1));
    } else if (e.key === "Enter" && highlightIdx >= 0) {
      e.preventDefault();
      selectItem(suggestions[highlightIdx]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  const showDropdown = open && query.length > 0 && suggestions.length > 0;
  // Check for exact match to hide dropdown when symbol is already selected
  const exactMatch = suggestions.length === 1 && suggestions[0].symbol === query;

  return (
    <div ref={wrapperRef} className="relative">
      <input
        value={value}
        onChange={(e) => {
          onChange(e.target.value);
          setOpen(true);
          setHighlightIdx(-1);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={handleKeyDown}
        placeholder="BTC"
        autoComplete="off"
        className="w-full bg-(--color-bg-surface) border border-(--color-border) rounded-lg px-2.5 py-1.5 text-sm text-(--color-text-primary) focus:outline-none focus:ring-2 focus:ring-(--color-accent)/50"
      />
      {showDropdown && !exactMatch && (
        <div
          ref={listRef}
          className="absolute z-50 left-0 right-0 top-full mt-1 max-h-48 overflow-y-auto bg-(--color-bg-surface) border border-(--color-border) rounded-lg shadow-lg py-1"
        >
          {suggestions.map((entry, i) => (
            <button
              key={entry.symbol}
              type="button"
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => selectItem(entry)}
              onMouseEnter={() => setHighlightIdx(i)}
              className={cn(
                "w-full flex items-center gap-2 px-2.5 py-1.5 text-left transition-colors",
                i === highlightIdx
                  ? "bg-(--color-accent)/10"
                  : "hover:bg-(--color-bg-elevated)",
              )}
            >
              <span className="text-xs font-bold font-mono text-(--color-text-primary) w-14 shrink-0">
                {entry.symbol}
              </span>
              <span className="text-xs text-(--color-text-secondary) truncate">
                {entry.name}
              </span>
            </button>
          ))}
        </div>
      )}
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

/* ---- Add/Edit Form ---- */

function HoldingForm({
  initial,
  onClose,
}: {
  initial?: HoldingItem;
  onClose: () => void;
}) {
  const addMutation = useAddHolding();
  const updateMutation = useUpdateHolding();

  const [symbol, setSymbol] = useState(initial?.symbol ?? "");
  const [quantity, setQuantity] = useState(initial?.quantity?.toString() ?? "");
  const [price, setPrice] = useState(initial?.avg_price?.toString() ?? "");
  const [notes, setNotes] = useState(initial?.notes ?? "");

  const isEdit = !!initial?.id;
  const mutation = isEdit ? updateMutation : addMutation;
  const canSubmit = symbol.trim() && parseFloat(quantity) > 0 && !mutation.isPending;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const data: ManualHoldingRequest = {
      symbol: symbol.trim().toUpperCase(),
      quantity: parseFloat(quantity),
      purchase_price: price ? parseFloat(price) : null,
      notes: notes.trim() || null,
    };
    if (isEdit && initial?.id) {
      updateMutation.mutate({ id: initial.id, ...data }, { onSuccess: onClose });
    } else {
      addMutation.mutate(data, { onSuccess: onClose });
    }
  }

  return (
    <form onSubmit={handleSubmit} className="bg-(--color-bg-elevated)/50 rounded-lg p-4 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-(--color-text-primary)">
          {isEdit ? "Edit Holding" : "Add Holding"}
        </span>
        <button type="button" onClick={onClose} className="p-1 hover:bg-(--color-bg-elevated) rounded">
          <X className="w-3.5 h-3.5 text-(--color-text-secondary)" />
        </button>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div>
          <label className="block text-[10px] font-medium text-(--color-text-secondary) uppercase tracking-wider mb-1">Symbol</label>
          <SymbolAutocomplete value={symbol} onChange={setSymbol} />
        </div>
        <div>
          <label className="block text-[10px] font-medium text-(--color-text-secondary) uppercase tracking-wider mb-1">Quantity</label>
          <input
            type="number"
            step="any"
            min="0"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            placeholder="0.5"
            className="w-full bg-(--color-bg-surface) border border-(--color-border) rounded-lg px-2.5 py-1.5 text-sm font-mono text-(--color-text-primary) focus:outline-none focus:ring-2 focus:ring-(--color-accent)/50"
          />
        </div>
        <div>
          <label className="block text-[10px] font-medium text-(--color-text-secondary) uppercase tracking-wider mb-1">Cost/Unit (USD)</label>
          <input
            type="number"
            step="any"
            min="0"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            placeholder="Optional"
            className="w-full bg-(--color-bg-surface) border border-(--color-border) rounded-lg px-2.5 py-1.5 text-sm font-mono text-(--color-text-primary) focus:outline-none focus:ring-2 focus:ring-(--color-accent)/50"
          />
        </div>
        <div>
          <label className="block text-[10px] font-medium text-(--color-text-secondary) uppercase tracking-wider mb-1">Label</label>
          <input
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="e.g. Ledger"
            className="w-full bg-(--color-bg-surface) border border-(--color-border) rounded-lg px-2.5 py-1.5 text-sm text-(--color-text-primary) focus:outline-none focus:ring-2 focus:ring-(--color-accent)/50"
          />
        </div>
      </div>
      {mutation.isError && (
        <p className="text-xs text-(--color-negative)">
          {mutation.error instanceof Error ? mutation.error.message : "Failed to save"}
        </p>
      )}
      <button
        type="submit"
        disabled={!canSubmit}
        className="flex items-center gap-1.5 bg-(--color-accent) hover:bg-(--color-accent)/90 text-white text-xs font-medium rounded-lg px-3 py-1.5 transition-colors disabled:opacity-50"
      >
        {mutation.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : <Plus className="w-3 h-3" />}
        {isEdit ? "Update" : "Add"}
      </button>
    </form>
  );
}

/* ---- Combined holding (merged by symbol) ---- */

interface CombinedHolding {
  symbol: string;
  name: string;
  totalQty: number;
  currentPrice: number | null;
  totalValue: number;
  change24hPct: number | null;
  allocPct: number | null;
  sources: { source: string; notes: string | null; qty: number; id?: string; avgPrice?: number | null }[];
  marketCap: number | null;
  marketCapRank: number | null;
  volume24h: number | null;
  imageUrl: string | null;
  avgCost: number | null;
  pnlUsd: number | null;
  pnlPct: number | null;
}

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
    // PnL from weighted average cost
    const withCost = c.sources.filter((s) => s.avgPrice != null && s.avgPrice! > 0);
    if (withCost.length > 0) {
      const totalCostQty = withCost.reduce((sum, s) => sum + s.qty, 0);
      const weightedCost = withCost.reduce((sum, s) => sum + s.qty * (s.avgPrice ?? 0), 0);
      c.avgCost = totalCostQty > 0 ? weightedCost / totalCostQty : null;
      if (c.avgCost != null && c.currentPrice != null) {
        c.pnlPct = ((c.currentPrice - c.avgCost) / c.avgCost) * 100;
        c.pnlUsd = (c.currentPrice - c.avgCost) * c.totalQty;
      }
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
  const [hideSmall, setHideSmall] = useState(false);
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
    if (!donutTotal || donutTotal <= 0) return [];
    const byValue = [...donutSource]
      .filter((c) => c.totalValue > 0)
      .sort((a, b) => b.totalValue - a.totalValue);

    const topN = byValue.slice(0, 9);
    const rest = byValue.slice(9);
    const restValue = rest.reduce((sum, c) => sum + c.totalValue, 0);

    const slices: DonutSlice[] = topN.map((c, i) => ({
      label: c.symbol,
      value: c.totalValue,
      pct: (c.totalValue / donutTotal) * 100,
      color: DONUT_COLORS[i % DONUT_COLORS.length],
    }));

    if (restValue > 0) {
      slices.push({
        label: `Other (${rest.length})`,
        value: restValue,
        pct: (restValue / donutTotal) * 100,
        color: "#4b5563", // gray
      });
    }

    return slices;
  }, [donutSource, donutTotal]);

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
            <h3 className="text-sm font-semibold text-(--color-text-primary)">Crypto Holdings</h3>
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
          "bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-5 space-y-5 transition-all duration-600 ease-out",
          reveal ? "opacity-100 translate-y-0" : "opacity-0 translate-y-5",
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Wallet className="w-4 h-4 text-(--color-accent)" />
            <h3 className="text-sm font-semibold text-(--color-text-primary)">Portfolio Overview</h3>
          </div>
          <div className="flex items-center gap-2">
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

        {/* Donut + Source breakdown side by side */}
        <div className="flex flex-col lg:flex-row gap-6">
          {/* Donut chart */}
          {donutSlices.length > 0 && donutTotal > 0 && (
            <div
              className={cn(
                "shrink-0 transition-all duration-700 ease-out",
                reveal ? "opacity-100 scale-100" : "opacity-0 scale-90",
              )}
              style={{ transitionDelay: "150ms" }}
            >
              <DonutChart
                slices={donutSlices}
                totalValue={donutTotal}
                onSliceClick={(label) => {
                  if (!label.startsWith("Other")) setDetailSymbol(label);
                }}
              />
            </div>
          )}

          {/* Right side: source breakdown */}
          <div
            className={cn(
              "flex-1 space-y-5 min-w-0 transition-all duration-600 ease-out",
              reveal ? "opacity-100 translate-y-0" : "opacity-0 translate-y-3",
            )}
            style={{ transitionDelay: "250ms" }}
          >
            {totalValue != null && totalValue > 0 && (
              <SourceBreakdown
                holdings={allHoldings}
                totalValue={totalValue}
                onSourceClick={(source) => applyFilter("source", source)}
                activeSource={sourceFilter}
              />
            )}
          </div>
        </div>

      </div>

      {/* Active filter indicator */}
      {hasActiveFilter && (
        <div
          className={cn(
            "flex items-center justify-between bg-(--color-accent)/5 border border-(--color-accent)/20 rounded-lg px-4 py-2.5 transition-all duration-300 ease-out",
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
          "bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-5 space-y-4 transition-all duration-600 ease-out",
          reveal ? "opacity-100 translate-y-0" : "opacity-0 translate-y-5",
        )}
        style={{ transitionDelay: "200ms" }}
      >
        {/* Table header with controls */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <h3 className="text-sm font-semibold text-(--color-text-primary)">All Assets</h3>

          <div className="flex items-center gap-3">
            {/* Search */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-(--color-text-secondary)" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search assets..."
                className="w-40 bg-(--color-bg-elevated) border border-(--color-border) rounded-lg pl-8 pr-3 py-1.5 text-xs text-(--color-text-primary) focus:outline-none focus:ring-2 focus:ring-(--color-accent)/50 placeholder:text-(--color-text-secondary)/50"
              />
            </div>

            {/* Stablecoins filter */}
            <button
              onClick={() => applyFilter("category", "stablecoins")}
              className={cn(
                "flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors border",
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
                  "flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors border",
                  hideSmall
                    ? "bg-(--color-accent)/10 border-(--color-accent)/30 text-(--color-accent)"
                    : "bg-(--color-bg-elevated) border-(--color-border) text-(--color-text-secondary) hover:text-(--color-text-primary)",
                )}
              >
                {hideSmall ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
                {hideSmall ? `${smallCount} hidden` : `Hide small (<$1)`}
              </button>
            )}

            {/* Add holding */}
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
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-(--color-border)">
                  <SortHeader label="#" sortKey="rank" activeKey={sortKey} activeDir={sortDir} onSort={handleSort} className="text-left w-10" />
                  <SortHeader label="Coin" sortKey="symbol" activeKey={sortKey} activeDir={sortDir} onSort={handleSort} className="text-left" />
                  <th className="text-right text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider py-2 px-3">Price</th>
                  <SortHeader label="24h" sortKey="change" activeKey={sortKey} activeDir={sortDir} onSort={handleSort} className="text-right" />
                  <SortHeader label="Mkt Cap" sortKey="marketCap" activeKey={sortKey} activeDir={sortDir} onSort={handleSort} className="text-right hidden lg:table-cell" />
                  <SortHeader label="Volume" sortKey="volume" activeKey={sortKey} activeDir={sortDir} onSort={handleSort} className="text-right hidden lg:table-cell" />
                  <SortHeader label="Holdings" sortKey="value" activeKey={sortKey} activeDir={sortDir} onSort={handleSort} className="text-right" />
                  <SortHeader label="PNL" sortKey="pnl" activeKey={sortKey} activeDir={sortDir} onSort={handleSort} className="text-right" />
                  <th className="text-left text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider py-2 px-3">Source</th>
                  <th className="py-2 w-16" />
                </tr>
              </thead>
              <tbody>
                {sorted.map((c, i) => {
                  const manualSources = c.sources.filter((s) => s.source === "manual" && s.id);
                  return (
                    <tr
                      key={c.symbol}
                      className={cn(
                        "border-b border-(--color-border)/50 last:border-0 hover:bg-(--color-bg-elevated)/30 cursor-pointer",
                        "transition-all duration-500 ease-out",
                        reveal ? "opacity-100 translate-y-0" : "opacity-0 translate-y-2",
                      )}
                      style={{ transitionDelay: `${350 + i * 40}ms` }}
                      onClick={() => setDetailSymbol(c.symbol)}
                    >
                      {/* Rank */}
                      <td className="py-2.5 px-2 text-xs font-mono text-(--color-text-secondary) w-10">
                        {c.marketCapRank ?? "—"}
                      </td>

                      {/* Coin: icon + name + symbol */}
                      <td className="py-2.5 px-3">
                        <div className="flex items-center gap-2.5">
                          <CoinIcon symbol={c.symbol} imageUrl={c.imageUrl} size={28} />
                          <div className="min-w-0">
                            <span className="font-semibold text-(--color-text-primary) text-sm block truncate">
                              {c.name}
                            </span>
                            <span className="text-[11px] text-(--color-text-secondary) font-mono">
                              {c.symbol}
                            </span>
                          </div>
                        </div>
                      </td>

                      {/* Price */}
                      <td className="py-2.5 px-3 text-right font-mono tabular-nums text-(--color-text-primary) text-xs">
                        {c.currentPrice != null ? formatPrice(c.currentPrice) : "—"}
                      </td>

                      {/* 24h Change */}
                      <td className="py-2.5 px-3 text-right">
                        {c.change24hPct != null ? (
                          <div className="flex items-center justify-end gap-1">
                            {c.change24hPct >= 0 ? (
                              <TrendingUp className={cn("w-3 h-3", pnlColor(c.change24hPct))} />
                            ) : (
                              <TrendingDown className={cn("w-3 h-3", pnlColor(c.change24hPct))} />
                            )}
                            <span className={cn("text-xs font-mono tabular-nums font-medium", pnlColor(c.change24hPct))}>
                              {c.change24hPct >= 0 ? "+" : ""}{c.change24hPct.toFixed(2)}%
                            </span>
                          </div>
                        ) : (
                          <span className="text-xs text-(--color-text-secondary)">—</span>
                        )}
                      </td>

                      {/* Market Cap */}
                      <td className="py-2.5 px-3 text-right hidden lg:table-cell">
                        <span className="text-xs font-mono tabular-nums text-(--color-text-secondary)">
                          {c.marketCap ? fmtCompact(c.marketCap) : "—"}
                        </span>
                      </td>

                      {/* Volume */}
                      <td className="py-2.5 px-3 text-right hidden lg:table-cell">
                        <span className="text-xs font-mono tabular-nums text-(--color-text-secondary)">
                          {c.volume24h ? fmtCompact(c.volume24h) : "—"}
                        </span>
                      </td>

                      {/* Holdings: value + qty stacked */}
                      <td className="py-2.5 px-3 text-right">
                        <div className="font-mono tabular-nums">
                          <span className="text-xs font-semibold text-(--color-text-primary) block">
                            {fmtUsd(c.totalValue)}
                          </span>
                          <span className="text-[10px] text-(--color-text-secondary)">
                            {c.totalQty.toLocaleString("en-US", { maximumFractionDigits: 6 })} {c.symbol}
                          </span>
                        </div>
                      </td>

                      {/* PNL */}
                      <td className="py-2.5 px-3 text-right">
                        {c.pnlUsd != null ? (
                          <div className="font-mono tabular-nums">
                            <span className={cn("text-xs font-semibold block", pnlColor(c.pnlUsd))}>
                              {c.pnlUsd >= 0 ? "+" : ""}{fmtUsd(Math.abs(c.pnlUsd))}
                            </span>
                            <span className={cn("text-[10px]", pnlColor(c.pnlPct ?? 0))}>
                              {(c.pnlPct ?? 0) >= 0 ? "+" : ""}{(c.pnlPct ?? 0).toFixed(1)}%
                            </span>
                          </div>
                        ) : (
                          <span className="text-xs text-(--color-text-secondary)">—</span>
                        )}
                      </td>

                      {/* Sources */}
                      <td className="py-2.5 px-3">
                        <div className="flex items-center gap-1 flex-wrap">
                          {c.sources.map((s, si) => {
                            const style = SOURCE_STYLE[s.source] ?? { label: s.source, cls: "bg-(--color-bg-elevated) text-(--color-text-secondary)" };
                            const label = s.notes && s.source === "manual" ? s.notes : style.label;
                            return (
                              <span
                                key={`${s.source}-${si}`}
                                className={cn("text-[10px] font-medium px-2 py-0.5 rounded-full whitespace-nowrap", style.cls)}
                              >
                                {label}
                              </span>
                            );
                          })}
                        </div>
                      </td>

                      {/* Actions */}
                      <td className="py-2.5" onClick={(e) => e.stopPropagation()}>
                        {manualSources.length === 1 && c.sources.length === 1 && (
                          <div className="flex items-center gap-1 justify-end">
                            <button
                              onClick={() => {
                                const raw = allHoldings.find((h) => h.id === manualSources[0].id);
                                if (raw) { setShowForm(false); setEditItem(raw); }
                              }}
                              className="p-1 rounded hover:bg-(--color-bg-elevated) text-(--color-text-secondary) hover:text-(--color-text-primary) transition-colors"
                            >
                              <Pencil className="w-3 h-3" />
                            </button>
                            <button
                              onClick={() => manualSources[0].id && deleteMutation.mutate(manualSources[0].id)}
                              disabled={deleteMutation.isPending}
                              className="p-1 rounded hover:bg-(--color-negative)/10 text-(--color-text-secondary) hover:text-(--color-negative) transition-colors"
                            >
                              <Trash2 className="w-3 h-3" />
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>

              {/* Footer with total */}
              {totalValue != null && (
                <tfoot>
                  <tr
                    className={cn(
                      "border-t border-(--color-border) transition-all duration-500 ease-out",
                      reveal ? "opacity-100" : "opacity-0",
                    )}
                    style={{ transitionDelay: `${350 + sorted.length * 40 + 80}ms` }}
                  >
                    <td colSpan={4} className="py-3 px-3 text-xs font-semibold text-(--color-text-secondary) uppercase tracking-wider">
                      {hasActiveFilter || hideSmall
                        ? `Showing ${filteredCombined.length} of ${allCombined.length}`
                        : "Total"}
                    </td>
                    <td colSpan={2} className="py-3 px-3 text-right hidden lg:table-cell" />
                    <td className="py-3 px-3 text-right font-mono tabular-nums text-(--color-text-primary) font-bold text-sm">
                      {fmtUsd(
                        hasActiveFilter || hideSmall || searchQuery.trim()
                          ? filteredCombined.reduce((sum, c) => sum + c.totalValue, 0)
                          : (totalValue ?? 0),
                      )}
                    </td>
                    <td colSpan={3} />
                  </tr>
                </tfoot>
              )}
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
