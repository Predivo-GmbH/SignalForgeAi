import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Zap, Loader2, TrendingUp, TrendingDown, Minus, AlertTriangle, X, Info } from "lucide-react";
import { api } from "@/lib/api";
import { useSignals } from "@/hooks/useSignals";
import { useSymbols } from "@/hooks/useSymbols";
import type { Signal } from "@/hooks/useSignals";
import { Badge } from "@/components/ui/Badge";
import { DataTable } from "@/components/ui/DataTable";
import type { Column } from "@/components/ui/DataTable";
import { Pagination } from "@/components/ui/Pagination";
import { cn } from "@/lib/cn";

const PAGE_SIZE = 20;

const TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1D"] as const;
const FALLBACK_SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "BNB/USDT", "DOGE/USDT", "AVAX/USDT", "LINK/USDT"];

interface GenerateResult {
  symbol: string;
  timeframe: string;
  action: string;
  regime: string;
  trend_direction: string;
  trend_strength: number;
  confluence_score: number;
  triggers: string[];
  stop_loss: number | null;
  take_profit_1: number | null;
  take_profit_2: number | null;
  position_size: number | null;
  risk_reward: number | null;
  block_reason: string | null;
  timestamp: string;
}

function formatPrice(val: number): string {
  if (val >= 1000) return `$${val.toFixed(2)}`;
  if (val >= 1) return `$${val.toFixed(4)}`;
  return `$${val.toFixed(6)}`;
}

function formatTime(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

function ConfluenceBar({ score }: { score: number }) {
  const pct = Math.min(100, Math.max(0, score));
  let color = "bg-[var(--color-negative)]";
  if (pct >= 60) color = "bg-[var(--color-positive)]";
  else if (pct >= 30) color = "bg-[var(--color-warning)]";

  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 rounded-full bg-[var(--color-bg-elevated)] overflow-hidden">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-mono text-[var(--color-text-secondary)]">{score}</span>
    </div>
  );
}

function directionBadge(dir: string) {
  const upper = dir.toUpperCase();
  return <Badge variant={upper === "LONG" ? "success" : "danger"}>{upper}</Badge>;
}

function regimeBadge(regime: string) {
  const r = regime.toLowerCase();
  let variant: "success" | "danger" | "warning" | "info" | "neutral" = "neutral";
  if (r === "trending" || r === "bullish") variant = "success";
  else if (r === "bearish" || r === "crisis") variant = "danger";
  else if (r === "volatile" || r === "mixed") variant = "warning";
  else if (r === "mean_reverting") variant = "info";
  return <Badge variant={variant}>{regime}</Badge>;
}

function statusBadge(status: string) {
  const s = status.toLowerCase();
  let variant: "success" | "danger" | "warning" | "info" | "neutral" = "neutral";
  if (s === "active" || s === "filled") variant = "success";
  else if (s === "cancelled" || s === "expired" || s === "rejected") variant = "danger";
  else if (s === "pending") variant = "warning";
  return <Badge variant={variant}>{status}</Badge>;
}

/* ---------- Generated Signal Result Card ---------- */
function GeneratedSignalCard({ result, onDismiss }: { result: GenerateResult; onDismiss: () => void }) {
  const isBuy = result.action.toUpperCase() === "BUY" || result.action.toUpperCase() === "LONG";
  const isHold = result.action.toUpperCase() === "HOLD" || result.action.toUpperCase() === "NO_TRADE";

  const blockMessages: Record<string, string> = {
    no_trend: "No clear trend detected. EMA 50/100/200 are not aligned in a consistent direction.",
    chaotic_regime: "Market is in a chaotic regime (extreme volatility). Too risky to enter.",
    low_confluence: "Confluence score too low. Not enough technical factors are aligned.",
    no_trigger: "No trigger confirmation. Need at least 2 trigger patterns (RSI cross, MACD cross, stochastic, etc).",
    no_zones: "No valid support/resistance zones found in current price range.",
  };

  return (
    <div className={cn(
      "rounded-xl border p-5 space-y-4",
      isHold ? "border-[var(--color-border)] bg-[var(--color-bg-surface)]"
        : isBuy ? "border-[var(--color-positive)]/30 bg-[var(--color-positive)]/5"
        : "border-[var(--color-negative)]/30 bg-[var(--color-negative)]/5"
    )}>
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className={cn(
            "flex items-center justify-center w-10 h-10 rounded-lg",
            isHold ? "bg-[var(--color-bg-elevated)]" : isBuy ? "bg-[var(--color-positive)]/10" : "bg-[var(--color-negative)]/10"
          )}>
            {isHold ? <Minus className="w-5 h-5 text-[var(--color-text-secondary)]" />
              : isBuy ? <TrendingUp className="w-5 h-5 text-[var(--color-positive)]" />
              : <TrendingDown className="w-5 h-5 text-[var(--color-negative)]" />}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-lg font-bold text-[var(--color-text-primary)]">{result.symbol}</span>
              <Badge variant={isHold ? "neutral" : isBuy ? "success" : "danger"}>{result.action.toUpperCase()}</Badge>
            </div>
            <span className="text-xs text-[var(--color-text-secondary)]">{result.timeframe} &middot; {formatTime(result.timestamp)}</span>
          </div>
        </div>
        <button onClick={onDismiss} className="text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] p-1">
          <X className="w-4 h-4" />
        </button>
      </div>

      {result.block_reason && (
        <div className="flex items-start gap-2 bg-[var(--color-warning)]/10 border border-[var(--color-warning)]/30 rounded-lg px-3 py-2">
          <AlertTriangle className="w-4 h-4 text-[var(--color-warning)] shrink-0 mt-0.5" />
          <span className="text-xs text-[var(--color-text-secondary)]">
            {blockMessages[result.block_reason] || result.block_reason}
          </span>
        </div>
      )}

      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
        <MetricCell label="Regime" value={result.regime} badge />
        <MetricCell label="Trend" value={result.trend_direction} badge />
        <MetricCell label="Confluence" value={`${result.confluence_score}/100`} />
        <MetricCell label="Trend Strength" value={`${(result.trend_strength * 100).toFixed(1)}%`} />
        {result.stop_loss != null && <MetricCell label="Stop Loss" value={formatPrice(result.stop_loss)} />}
        {result.take_profit_1 != null && <MetricCell label="Take Profit 1" value={formatPrice(result.take_profit_1)} />}
        {result.take_profit_2 != null && <MetricCell label="Take Profit 2" value={formatPrice(result.take_profit_2)} />}
        {result.position_size != null && <MetricCell label="Position Size" value={result.position_size.toFixed(4)} />}
        {result.risk_reward != null && <MetricCell label="Risk:Reward" value={`1:${result.risk_reward.toFixed(2)}`} />}
      </div>

      {result.triggers.length > 0 && (
        <div>
          <span className="text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wider">Triggers</span>
          <div className="flex flex-wrap gap-1.5 mt-1">
            {result.triggers.map((t, i) => (
              <span key={i} className="text-xs bg-[var(--color-bg-elevated)] text-[var(--color-text-primary)] rounded px-2 py-0.5">{t}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function MetricCell({ label, value, badge }: { label: string; value: string; badge?: boolean }) {
  return (
    <div className="space-y-0.5">
      <span className="text-[10px] font-medium text-[var(--color-text-secondary)] uppercase tracking-wider">{label}</span>
      {badge ? <div>{regimeBadge(value)}</div> : <p className="text-sm font-mono font-semibold text-[var(--color-text-primary)]">{value}</p>}
    </div>
  );
}

type SignalRow = Signal & Record<string, unknown>;

const columns: Column<SignalRow>[] = [
  { key: "created_at", header: "Time", render: (row) => <span className="text-xs text-[var(--color-text-secondary)] whitespace-nowrap">{formatTime(row.created_at)}</span> },
  { key: "symbol", header: "Symbol", render: (row) => <span className="font-semibold text-[var(--color-text-primary)]">{row.symbol}</span> },
  { key: "direction", header: "Direction", render: (row) => directionBadge(row.direction) },
  { key: "entry_price", header: "Entry", align: "right", render: (row) => <span className="font-mono">{formatPrice(row.entry_price)}</span> },
  { key: "stop_loss", header: "SL", align: "right", render: (row) => <span className="font-mono text-[var(--color-text-secondary)]">{formatPrice(row.stop_loss)}</span> },
  { key: "take_profit_1", header: "TP1", align: "right", render: (row) => <span className="font-mono text-[var(--color-text-secondary)]">{formatPrice(row.take_profit_1)}</span> },
  { key: "position_size", header: "Size", align: "right" as const, render: (row: SignalRow) => <span className="font-mono text-[var(--color-text-secondary)]">{row.position_size != null ? row.position_size.toFixed(4) : "--"}</span> },
  { key: "confluence_score", header: "Confluence", render: (row) => <ConfluenceBar score={row.confluence_score} /> },
  { key: "regime", header: "Regime", render: (row) => regimeBadge(row.regime) },
  { key: "status", header: "Status", render: (row) => statusBadge(row.status) },
];

export function SignalsPage() {
  const queryClient = useQueryClient();
  const [offset, setOffset] = useState(0);
  const { data, isLoading } = useSignals(PAGE_SIZE, offset);
  const { data: apiSymbols } = useSymbols();
  const symbols = apiSymbols ?? FALLBACK_SYMBOLS;
  const [lastResult, setLastResult] = useState<GenerateResult | null>(null);

  const [symbol, setSymbol] = useState("BTC/USDT");
  const [timeframe, setTimeframe] = useState("1h");
  const [equity, setEquity] = useState(10000);

  const generateMutation = useMutation({
    mutationFn: () =>
      api.post<GenerateResult>("/signals/generate", {
        symbol,
        timeframe,
        account_equity: equity,
      }),
    onSuccess: (result) => {
      setLastResult(result);
      queryClient.invalidateQueries({ queryKey: ["signals"] });
    },
  });

  const signals = (data?.signals ?? []) as SignalRow[];
  const total = data?.total ?? 0;

  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">Signals</h1>
        <p className="text-sm text-[var(--color-text-secondary)] mt-1">
          Generate on-demand signals for any trading pair, or view automated pipeline signals below
        </p>
      </div>

      {/* Signal Generator */}
      <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border)] rounded-xl p-5 space-y-4">
        <div className="flex items-center gap-2">
          <Zap className="w-4 h-4 text-[var(--color-accent)]" />
          <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">Generate Signal</h2>
        </div>

        <div className="flex flex-wrap items-end gap-4">
          <div className="space-y-1.5">
            <label className="block text-[10px] font-medium text-[var(--color-text-secondary)] uppercase tracking-wider">Symbol</label>
            <select
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              className="w-44 bg-[var(--color-bg-elevated)] border border-[var(--color-border)] rounded-lg px-3 py-2 text-sm text-[var(--color-text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]/50"
            >
              {symbols.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>

          <div className="space-y-1.5">
            <label className="block text-[10px] font-medium text-[var(--color-text-secondary)] uppercase tracking-wider">Timeframe</label>
            <div className="flex gap-1">
              {TIMEFRAMES.map((tf) => (
                <button
                  key={tf}
                  type="button"
                  onClick={() => setTimeframe(tf)}
                  className={cn(
                    "px-2.5 py-2 rounded-lg text-xs font-mono font-medium transition-colors",
                    timeframe === tf
                      ? "bg-[var(--color-accent)] text-white"
                      : "bg-[var(--color-bg-elevated)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
                  )}
                >
                  {tf}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="block text-[10px] font-medium text-[var(--color-text-secondary)] uppercase tracking-wider">Account Equity</label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-[var(--color-text-secondary)]">$</span>
              <input
                type="number"
                value={equity}
                onChange={(e) => setEquity(Math.max(100, Number(e.target.value)))}
                className="w-32 bg-[var(--color-bg-elevated)] border border-[var(--color-border)] rounded-lg pl-7 pr-3 py-2 text-sm font-mono text-[var(--color-text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]/50"
              />
            </div>
          </div>

          <button
            onClick={() => generateMutation.mutate()}
            disabled={generateMutation.isPending}
            className="flex items-center gap-2 bg-[var(--color-accent)] hover:bg-[var(--color-accent)]/90 text-white font-semibold py-2 px-5 rounded-lg text-sm transition-colors disabled:opacity-50"
          >
            {generateMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Zap className="h-4 w-4" />}
            Analyze
          </button>
        </div>

        <div className="flex items-start gap-2 text-[10px] text-[var(--color-text-secondary)]/70">
          <Info className="w-3 h-3 shrink-0 mt-0.5" />
          Runs the full 6-layer signal pipeline (regime, trend, zones, confluence, triggers, risk) on the latest candle data for your selected pair and timeframe.
        </div>
      </div>

      {generateMutation.isError && (
        <div className="rounded-lg border border-[var(--color-negative)]/30 bg-[var(--color-negative)]/10 px-4 py-3 space-y-1">
          <p className="text-sm font-semibold text-[var(--color-negative)]">Signal generation failed</p>
          <p className="text-xs text-[var(--color-text-secondary)]">{(generateMutation.error as any)?.message || "Please try again."}</p>
        </div>
      )}

      {lastResult && <GeneratedSignalCard result={lastResult} onDismiss={() => setLastResult(null)} />}

      <div>
        <h2 className="text-sm font-semibold text-[var(--color-text-primary)] mb-3">
          Pipeline Signals {total > 0 && <span className="text-[var(--color-text-secondary)] font-normal">({total})</span>}
        </h2>
        <DataTable
          data={signals}
          columns={columns}
          loading={isLoading}
          emptyMessage="No automated signals yet. Signals appear here when the pipeline detects trading opportunities."
        />
      </div>

      {total > PAGE_SIZE && <Pagination total={total} limit={PAGE_SIZE} offset={offset} onChange={setOffset} />}
    </div>
  );
}
