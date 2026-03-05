import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Tooltip } from "@/components/ui/Tooltip";
import { useQueryClient } from "@tanstack/react-query";
import {
  Search,
  Brain,
  Rocket,
  Loader2,
  TrendingUp,
  TrendingDown,
  Minus,
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  DollarSign,
  Trash2,
  X,
  Sparkles,
  Info,
  RotateCcw,
  Power,
  ExternalLink,
  FlaskConical,
} from "lucide-react";
import { cn } from "@/lib/cn";
import { formatPrice } from "@/lib/format";
import { Badge } from "@/components/ui/Badge";
import { useGeneratePlan, useDeployPlan } from "@/hooks/useAdvisor";
import { useStrategies, useToggleStrategy } from "@/hooks/useStrategies";
import { useAdvisorStore } from "@/stores/advisorStore";
import type { ScoredCrypto, InvestmentPlan, MarketProfile } from "@/hooks/useAdvisor";
import type { ScanHistoryEntry } from "@/stores/advisorStore";

/* ---------- Helpers ---------- */

function formatVolume(vol: number): string {
  if (vol >= 1_000_000_000) return `$${(vol / 1_000_000_000).toFixed(1)}B`;
  if (vol >= 1_000_000) return `$${(vol / 1_000_000).toFixed(1)}M`;
  return `$${vol.toLocaleString()}`;
}


function formatTimestamp(ts: number): string {
  const d = new Date(ts);
  const now = new Date();
  const isToday = d.toDateString() === now.toDateString();
  const yesterday = new Date(now);
  yesterday.setDate(yesterday.getDate() - 1);
  const isYesterday = d.toDateString() === yesterday.toDateString();

  const time = d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  if (isToday) return `Today ${time}`;
  if (isYesterday) return `Yesterday ${time}`;
  return d.toLocaleDateString([], { month: "short", day: "numeric" }) + ` ${time}`;
}

function recommendationBadge(rec: string) {
  const variants: Record<string, "success" | "warning" | "neutral" | "danger"> = {
    strong_buy: "success",
    buy: "success",
    neutral: "neutral",
    avoid: "danger",
  };
  return <Badge variant={variants[rec] || "neutral"}>{rec.replace("_", " ")}</Badge>;
}

function trendIcon(trend: string) {
  if (trend === "bullish") return <TrendingUp className="w-4 h-4 text-(--color-positive)" />;
  if (trend === "bearish") return <TrendingDown className="w-4 h-4 text-(--color-negative)" />;
  return <Minus className="w-4 h-4 text-(--color-text-secondary)" />;
}

function statusBadge(status: ScanHistoryEntry["status"]) {
  const map: Record<string, { variant: "success" | "warning" | "neutral" | "danger"; label: string }> = {
    completed: { variant: "success", label: "Completed" },
    running: { variant: "warning", label: "Running" },
    failed: { variant: "danger", label: "Failed" },
    cancelled: { variant: "neutral", label: "Cancelled" },
  };
  const s = map[status] || map.cancelled;
  return <Badge variant={s.variant}>{s.label}</Badge>;
}

/* ---------- Step Indicator ---------- */
function StepIndicator({ current }: { current: number }) {
  const steps = [
    { num: 1, label: "Scan Market" },
    { num: 2, label: "Generate Plan" },
    { num: 3, label: "Deploy" },
  ];
  return (
    <div className="flex items-center gap-2">
      {steps.map((step, i) => (
        <div key={step.num} className="flex items-center gap-2">
          <div
            className={cn(
              "flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold transition-colors",
              current >= step.num
                ? "bg-(--color-accent) text-white"
                : "bg-(--color-bg-elevated) text-(--color-text-secondary)"
            )}
          >
            {current > step.num ? (
              <CheckCircle2 className="w-4 h-4" />
            ) : (
              step.num
            )}
          </div>
          <span
            className={cn(
              "text-sm font-medium",
              current >= step.num
                ? "text-(--color-text-primary)"
                : "text-(--color-text-secondary)"
            )}
          >
            {step.label}
          </span>
          {i < steps.length - 1 && (
            <ChevronRight className="w-4 h-4 text-(--color-text-secondary)/40 mx-1" />
          )}
        </div>
      ))}
    </div>
  );
}

/* ---------- Scan Sidebar ---------- */
function ScanSidebar({
  history,
  activeScanId,
  selectedScanId,
  onNewScan,
  onSelect,
  onDelete,
  onCancel,
  onClear,
}: {
  history: ScanHistoryEntry[];
  activeScanId: string | null;
  selectedScanId: string | null;
  onNewScan: () => void;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
  onCancel: () => void;
  onClear: () => void;
}) {
  const isScanning = activeScanId !== null;
  const nonActiveEntries = history.filter((h) => h.id !== activeScanId);
  const activeEntry = activeScanId ? history.find((h) => h.id === activeScanId) : null;

  return (
    <div className="lg:sticky lg:top-6 bg-(--color-bg-surface) border border-(--color-border) rounded-xl overflow-hidden">
      {/* New Scan button */}
      <div className="p-3 border-b border-(--color-border)">
        <button
          onClick={isScanning ? onCancel : onNewScan}
          className={cn(
            "flex items-center justify-center gap-2 w-full font-semibold py-2.5 rounded-lg text-sm transition-colors",
            isScanning
              ? "bg-(--color-negative) hover:bg-(--color-negative)/90 text-white"
              : "bg-(--color-accent) hover:bg-(--color-accent)/90 text-white"
          )}
        >
          {isScanning ? (
            <><X className="w-4 h-4" /> Cancel Scan</>
          ) : (
            <><Search className="w-4 h-4" /> New Scan</>
          )}
        </button>
      </div>

      {/* Entry list */}
      {history.length > 0 && (
        <div className="px-4 pt-3 pb-1">
          <h3 className="text-xs font-semibold text-(--color-text-secondary) uppercase tracking-wider">Recent Scans</h3>
        </div>
      )}
      <div className="max-h-48 lg:max-h-[calc(100vh-220px)] overflow-y-auto">
        {/* Active scan entry */}
        {activeEntry && (
          <div className="flex flex-col gap-1 px-4 py-3 border-b border-(--color-border)/50 bg-(--color-warning)/5">
            <div className="flex items-center justify-between">
              <span className="text-xs text-(--color-text-secondary)">
                {formatTimestamp(activeEntry.timestamp)}
              </span>
              {statusBadge(activeEntry.status)}
            </div>
            <div className="flex items-center gap-2">
              <Loader2 className="w-3 h-3 animate-spin text-(--color-accent)" />
              <span className="text-xs text-(--color-text-secondary)">Scanning...</span>
            </div>
            <div className="h-1 bg-(--color-bg-elevated) rounded-full overflow-hidden mt-0.5">
              <div className="h-full bg-(--color-accent)/60 rounded-full animate-[advisor-pulse_2s_ease-in-out_infinite] w-3/5" />
            </div>
          </div>
        )}

        {/* Completed / failed / cancelled entries */}
        {nonActiveEntries.map((entry) => (
          <div
            key={entry.id}
            className={cn(
              "group flex flex-col gap-1 px-4 py-3 border-b border-(--color-border)/50 transition-all",
              entry.status === "completed" && "cursor-pointer",
              selectedScanId === entry.id
                ? "bg-(--color-accent)/10 border-l-2 border-l-(--color-accent)"
                : entry.status === "completed" ? "hover:bg-(--color-bg-elevated)/50" : ""
            )}
            onClick={() => {
              if (entry.status !== "completed") return;
              onSelect(selectedScanId === entry.id ? "" : entry.id);
            }}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs text-(--color-text-secondary)">
                {formatTimestamp(entry.timestamp)}
              </span>
              <div className="flex items-center gap-1.5">
                {statusBadge(entry.status)}
                <button
                  onClick={(e) => { e.stopPropagation(); onDelete(entry.id); }}
                  className="text-(--color-text-secondary) hover:text-(--color-negative) transition-colors opacity-0 group-hover:opacity-100"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {entry.status === "completed" && (
                <span className="text-xs text-(--color-text-secondary)">{entry.pairs_scored} pairs</span>
              )}
              {entry.plan && !entry.deployedStrategyId && (
                <Badge variant="info" className="gap-1 text-[10px]">
                  <Brain className="w-2.5 h-2.5" /> Plan
                </Badge>
              )}
              {entry.deployedStrategyId && (
                <Badge variant="success" className="gap-1 text-[10px]">
                  <Rocket className="w-2.5 h-2.5" /> Deployed
                </Badge>
              )}
              {entry.status === "failed" && entry.error && (
                <span className="text-[10px] text-(--color-negative) truncate">{entry.error}</span>
              )}
            </div>
          </div>
        ))}

        {/* Empty state */}
        {history.length === 0 && (
          <div className="px-4 py-10 text-center">
            <Search className="w-6 h-6 text-(--color-text-secondary)/30 mx-auto mb-2" />
            <p className="text-xs text-(--color-text-secondary)">No scans yet</p>
          </div>
        )}
      </div>

      {/* Clear all footer */}
      {nonActiveEntries.length > 2 && (
        <div className="px-4 py-2 border-t border-(--color-border)">
          <button
            onClick={onClear}
            className="text-xs text-(--color-text-secondary) hover:text-(--color-negative) transition-colors"
          >
            Clear All
          </button>
        </div>
      )}
    </div>
  );
}

/* ---------- Market Profile Panel ---------- */
function MarketRecommendationPanel({
  marketProfile,
  scanResults,
  amount,
  onAmountChange,
  onGeneratePlan,
  isPlanPending,
}: {
  marketProfile: MarketProfile;
  scanResults: ScoredCrypto[];
  amount: number;
  onAmountChange: (val: number) => void;
  onGeneratePlan: () => void;
  isPlanPending: boolean;
}) {
  // Compute signal breakdown from scan results
  const strongBuys = scanResults.filter((c) => c.recommendation === "strong_buy");
  const buys = scanResults.filter((c) => c.recommendation === "buy");
  const neutrals = scanResults.filter((c) => c.recommendation === "neutral");
  const avoids = scanResults.filter((c) => c.recommendation === "avoid");
  // The AI planner will pick score >= 30, not "avoid", max 15
  const tradeable = scanResults.filter((c) => c.score >= 30 && c.recommendation !== "avoid");

  return (
    <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-5 space-y-5">
      {/* AI Market Profile */}
      <div className="bg-(--color-accent)/5 border border-(--color-accent)/20 rounded-xl p-4 space-y-4">
        <div className="flex items-start gap-2">
          <Sparkles className="w-4 h-4 text-(--color-accent) shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-(--color-text-primary) mb-1">AI Market Profile</p>
            <p className="text-sm text-(--color-text-secondary) leading-relaxed">
              The AI advisor will analyze these market conditions and autonomously determine the optimal strategy parameters.
            </p>
          </div>
        </div>

        {/* Market stats */}
        <div className="flex flex-wrap gap-2">
          {[
            { label: "Avg Score", value: marketProfile.avg_score.toFixed(1) },
            { label: "Trending", value: `${marketProfile.trending_pct}%` },
            { label: "Bullish", value: `${marketProfile.bullish_pct}%` },
            { label: "Avg ADX", value: marketProfile.avg_adx.toFixed(1) },
            { label: "Avg Volatility", value: `${marketProfile.avg_volatility}%` },
            ...(marketProfile.chaotic_pct != null ? [{ label: "Chaotic", value: `${marketProfile.chaotic_pct}%` }] : []),
          ].map((chip) => (
            <span
              key={chip.label}
              className="text-xs bg-(--color-bg-elevated) rounded-lg px-2.5 py-1"
            >
              <span className="text-(--color-text-secondary)">{chip.label}: </span>
              <span className="font-mono font-semibold text-(--color-text-primary)">{chip.value}</span>
            </span>
          ))}
        </div>

        {/* Signal breakdown */}
        <div className="border-t border-(--color-accent)/15 pt-4 space-y-3">
          <p className="text-xs font-semibold text-(--color-text-secondary) uppercase tracking-wider">Signal Breakdown</p>
          <div className="flex flex-wrap gap-3">
            <span className="flex items-center gap-1.5 text-xs">
              <span className="w-2 h-2 rounded-full bg-(--color-positive)" />
              <span className="font-semibold text-(--color-positive)">{strongBuys.length}</span>
              <span className="text-(--color-text-secondary)">Strong Buy</span>
            </span>
            <span className="flex items-center gap-1.5 text-xs">
              <span className="w-2 h-2 rounded-full bg-(--color-positive)/60" />
              <span className="font-semibold text-(--color-text-primary)">{buys.length}</span>
              <span className="text-(--color-text-secondary)">Buy</span>
            </span>
            <span className="flex items-center gap-1.5 text-xs">
              <span className="w-2 h-2 rounded-full bg-(--color-text-secondary)/40" />
              <span className="font-semibold text-(--color-text-primary)">{neutrals.length}</span>
              <span className="text-(--color-text-secondary)">Neutral</span>
            </span>
            <span className="flex items-center gap-1.5 text-xs">
              <span className="w-2 h-2 rounded-full bg-(--color-negative)" />
              <span className="font-semibold text-(--color-negative)">{avoids.length}</span>
              <span className="text-(--color-text-secondary)">Avoid</span>
            </span>
          </div>

          {/* Trading plan preview */}
          <div className="bg-(--color-bg-elevated)/50 rounded-lg p-3 space-y-2">
            <p className="text-xs font-semibold text-(--color-text-primary)">
              Trading Plan Preview
            </p>
            <p className="text-xs text-(--color-text-secondary) leading-relaxed">
              The AI will select up to <span className="font-semibold text-(--color-text-primary)">15 pairs</span> from
              the <span className="font-semibold text-(--color-text-primary)">{tradeable.length} tradeable candidates</span> (score
              {" "}40+ with buy/strong buy signals). These pairs will be monitored through a 6-layer signal pipeline that
              requires regime confirmation, trend alignment, and minimum confluence before placing any trade.
            </p>
            {tradeable.length > 0 && (
              <div className="flex flex-wrap gap-1.5 pt-1">
                {tradeable.slice(0, 15).map((c) => (
                  <span
                    key={c.symbol}
                    className={cn(
                      "text-xs font-mono px-2 py-0.5 rounded",
                      c.recommendation === "strong_buy"
                        ? "bg-(--color-positive)/10 text-(--color-positive) font-semibold"
                        : "bg-(--color-bg-elevated) text-(--color-text-primary)"
                    )}
                  >
                    {c.symbol.replace("/USDT", "")}
                    <span className="ml-1 text-[10px] opacity-70">{c.score}</span>
                  </span>
                ))}
                {tradeable.length > 15 && (
                  <span className="text-xs text-(--color-text-secondary) self-center">
                    +{tradeable.length - 15} more
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Amount + Generate Plan */}
      <div className="flex flex-wrap items-end gap-4">
        <div className="space-y-1.5">
          <label className="block text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">
            Investment Amount
          </label>
          <div className="relative">
            <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-(--color-text-secondary)" />
            <input
              type="number"
              value={amount}
              onChange={(e) => onAmountChange(Number(e.target.value))}
              min={100}
              max={10000000}
              className="w-48 bg-(--color-bg-elevated) border border-(--color-border) rounded-lg pl-9 pr-3 py-2 text-sm font-mono text-(--color-text-primary) focus:outline-none focus:ring-2 focus:ring-(--color-accent)/50"
            />
          </div>
        </div>

        <button
          onClick={onGeneratePlan}
          disabled={isPlanPending}
          className="flex items-center gap-2 bg-(--color-accent) hover:bg-(--color-accent)/90 text-white font-semibold py-2 px-5 rounded-lg text-sm transition-colors disabled:opacity-50"
        >
          {isPlanPending ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Brain className="w-4 h-4" />
          )}
          {isPlanPending ? "Generating Optimal Strategy..." : "Generate Optimal Strategy"}
        </button>
      </div>
    </div>
  );
}

/* ---------- Scan Results Table ---------- */
function ScanResultsTable({ results }: { results: ScoredCrypto[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-(--color-border)">
            <th className="text-left py-2 px-3 text-xs font-medium text-(--color-text-secondary) uppercase">#</th>
            <th className="text-left py-2 px-3 text-xs font-medium text-(--color-text-secondary) uppercase">Symbol</th>
            <th className="text-right py-2 px-3 text-xs font-medium text-(--color-text-secondary) uppercase">Price</th>
            <th className="text-right py-2 px-3 text-xs font-medium text-(--color-text-secondary) uppercase">24h</th>
            <th className="text-right py-2 px-3 text-xs font-medium text-(--color-text-secondary) uppercase">Volume</th>
            <th className="text-center py-2 px-3 text-xs font-medium text-(--color-text-secondary) uppercase">Score</th>
            <th className="text-center py-2 px-3 text-xs font-medium text-(--color-text-secondary) uppercase">Regime</th>
            <th className="text-center py-2 px-3 text-xs font-medium text-(--color-text-secondary) uppercase">Trend</th>
            <th className="text-right py-2 px-3 text-xs font-medium text-(--color-text-secondary) uppercase">RSI</th>
            <th className="text-right py-2 px-3 text-xs font-medium text-(--color-text-secondary) uppercase">ADX</th>
            <th className="text-center py-2 px-3 text-xs font-medium text-(--color-text-secondary) uppercase">Signal</th>
          </tr>
        </thead>
        <tbody>
          {results.map((crypto, i) => (
            <tr
              key={crypto.symbol}
              className={cn(
                "border-b border-(--color-border)/50 hover:bg-(--color-bg-elevated)/50 transition-colors",
                crypto.recommendation === "strong_buy" && "bg-(--color-positive)/5"
              )}
            >
              <td className="py-2.5 px-3 text-(--color-text-secondary)">{i + 1}</td>
              <td className="py-2.5 px-3 font-semibold text-(--color-text-primary)">{crypto.symbol}</td>
              <td className="py-2.5 px-3 text-right font-mono">{formatPrice(crypto.price)}</td>
              <td className={cn(
                "py-2.5 px-3 text-right font-mono",
                crypto.change_pct_24h >= 0 ? "text-(--color-positive)" : "text-(--color-negative)"
              )}>
                {crypto.change_pct_24h >= 0 ? "+" : ""}{crypto.change_pct_24h?.toFixed(2) ?? "0.00"}%
              </td>
              <td className="py-2.5 px-3 text-right text-(--color-text-secondary)">{formatVolume(crypto.volume_24h || 0)}</td>
              <td className="py-2.5 px-3 text-center">
                <span className={cn(
                  "inline-block w-10 text-center font-bold rounded px-1.5 py-0.5 text-xs",
                  crypto.score >= 70 ? "bg-(--color-positive)/10 text-(--color-positive)" :
                  crypto.score >= 50 ? "bg-(--color-warning)/10 text-(--color-warning)" :
                  crypto.score >= 30 ? "bg-(--color-bg-elevated) text-(--color-text-secondary)" :
                  "bg-(--color-negative)/10 text-(--color-negative)"
                )}>
                  {crypto.score}
                </span>
              </td>
              <td className="py-2.5 px-3 text-center">
                <Badge variant={crypto.regime === "trending" ? "success" : crypto.regime === "chaotic" ? "danger" : "neutral"}>
                  {crypto.regime}
                </Badge>
              </td>
              <td className="py-2.5 px-3 text-center">{trendIcon(crypto.trend_direction)}</td>
              <td className="py-2.5 px-3 text-right font-mono text-(--color-text-secondary)">{crypto.rsi?.toFixed(0) ?? "--"}</td>
              <td className="py-2.5 px-3 text-right font-mono text-(--color-text-secondary)">{crypto.adx?.toFixed(0) ?? "--"}</td>
              <td className="py-2.5 px-3 text-center">{recommendationBadge(crypto.recommendation)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ---------- Plan Display ---------- */
function PlanDisplay({ plan }: { plan: InvestmentPlan }) {
  return (
    <div className="space-y-4">
      <div className="bg-(--color-bg-elevated)/50 rounded-lg p-4">
        <p className="text-sm text-(--color-text-primary) leading-relaxed">{plan.summary}</p>
      </div>

      <div>
        <h3 className="text-sm font-semibold text-(--color-text-primary) mb-2">Selected Assets ({plan.selected_cryptos.length})</h3>
        <div className="grid gap-2">
          {plan.selected_cryptos.map((c) => (
            <div key={c.symbol} className="flex items-start gap-3 bg-(--color-bg-elevated)/30 rounded-lg px-3 py-2">
              <span className="font-semibold text-sm text-(--color-accent) shrink-0">{c.symbol}</span>
              <span className="text-xs text-(--color-text-secondary)">{c.reason}</span>
            </div>
          ))}
        </div>
      </div>

      {plan.reasoning && (
        <div className="bg-(--color-accent)/5 border border-(--color-accent)/20 rounded-lg p-3">
          <p className="text-xs font-semibold text-(--color-text-secondary) uppercase tracking-wider mb-1">AI Reasoning</p>
          <p className="text-sm text-(--color-text-primary) leading-relaxed">{plan.reasoning}</p>
        </div>
      )}

      <div>
        <h3 className="text-sm font-semibold text-(--color-text-primary) mb-2">Strategy Configuration</h3>
        <div className="flex flex-wrap gap-3">
          {Object.entries(plan.strategy_config).map(([key, val]) => (
            <span key={key} className="text-xs bg-(--color-bg-elevated) rounded px-2 py-1">
              <span className="text-(--color-text-secondary)">{key.replace(/_/g, " ")}:</span>{" "}
              <span className="font-mono font-semibold text-(--color-text-primary)">
                {typeof val === "number" && val < 1 && key !== "account_equity"
                  ? `${(val * 100).toFixed(1)}%`
                  : typeof val === "number" && key === "account_equity"
                  ? `$${(val as number).toLocaleString()}`
                  : typeof val === "boolean"
                  ? val ? "Yes" : "No"
                  : Array.isArray(val)
                  ? val.join(", ")
                  : String(val)}
              </span>
            </span>
          ))}
        </div>
      </div>

      {plan.expected_behavior && (
        <div className="bg-(--color-accent-soft) rounded-lg p-3">
          <p className="text-xs text-(--color-text-primary)">{plan.expected_behavior}</p>
        </div>
      )}

      {plan.warnings.length > 0 && (
        <div className="space-y-1.5">
          {plan.warnings.map((w, i) => (
            <div key={i} className="flex items-start gap-2 text-xs text-(--color-warning)">
              <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
              {w}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ---------- Main Advisor Page ---------- */
export function AdvisorPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // Zustand store — persists across navigation
  const scanHistory = useAdvisorStore((s) => s.scanHistory);
  const activeScanId = useAdvisorStore((s) => s.activeScanId);
  const startScan = useAdvisorStore((s) => s.startScan);
  const cancelScan = useAdvisorStore((s) => s.cancelScan);
  const deleteScan = useAdvisorStore((s) => s.deleteScan);
  const clearHistory = useAdvisorStore((s) => s.clearHistory);
  const storePlan = useAdvisorStore((s) => s.setPlan);
  const storeDeployed = useAdvisorStore((s) => s.setDeployed);
  const storeClearPlan = useAdvisorStore((s) => s.clearPlan);

  // Local state — nothing selected by default (clean slate on page load)
  const [selectedScanId, setSelectedScanId] = useState<string | null>(null);
  const [amount, setAmount] = useState(10000);

  const planMutation = useGeneratePlan();
  const deployMutation = useDeployPlan();
  const toggleMutation = useToggleStrategy();

  // Auto-select a scan only when a NEW scan we initiated completes
  const prevActiveScanId = useRef(activeScanId);
  useEffect(() => {
    if (prevActiveScanId.current && !activeScanId) {
      const justCompleted = scanHistory.find(
        (h) => h.id === prevActiveScanId.current && h.status === "completed",
      );
      if (justCompleted) {
        setSelectedScanId(justCompleted.id);
      }
    }
    prevActiveScanId.current = activeScanId;
  }, [activeScanId, scanHistory]);

  // Active strategies count
  const { data: strategiesData } = useStrategies();
  const activeCount = strategiesData?.strategies?.filter((s) => s.is_active).length ?? 0;

  // Derive state from store (plan & deploy are persisted per-scan)
  const selectedScan = scanHistory.find((h) => h.id === selectedScanId);
  const scanResults = selectedScan?.status === "completed" ? selectedScan.results : null;
  const marketProfile = selectedScan?.status === "completed" ? selectedScan.market_profile : null;
  const plan = selectedScan?.plan ?? null;
  const deployed = !!selectedScan?.deployedStrategyId;
  const deployedMessage = selectedScan?.deployedMessage ?? null;
  const deployedStrategy = deployed
    ? strategiesData?.strategies?.find((s) => s.id === selectedScan?.deployedStrategyId)
    : null;
  const isStrategyActive = deployedStrategy?.is_active ?? false;

  const handleSelectScan = (id: string) => {
    setSelectedScanId(id || null);
    planMutation.reset();
    deployMutation.reset();
    if (id) {
      const scan = scanHistory.find((h) => h.id === id);
      if (scan?.planAmount) setAmount(scan.planAmount);
    }
  };

  const isScanning = activeScanId !== null;
  const currentStep = deployed ? 3 : plan ? 2 : scanResults ? 1 : 0;

  function handleScan() {
    startScan(100);
    setSelectedScanId(null);
    planMutation.reset();
    deployMutation.reset();
  }

  function handleGeneratePlan() {
    if (!scanResults || !selectedScanId) return;
    planMutation.mutate(
      { amount, scan_results: scanResults },
      { onSuccess: (data) => storePlan(selectedScanId, data, amount) },
    );
  }

  function handleDeploy() {
    if (!plan || !selectedScanId) return;
    deployMutation.mutate(plan, {
      onSuccess: (data) => {
        storeDeployed(selectedScanId, data.strategy_id, data.message);
        queryClient.invalidateQueries({ queryKey: ["strategies"] });
      },
    });
  }

  function handleRegeneratePlan() {
    if (!selectedScanId) return;
    storeClearPlan(selectedScanId);
    planMutation.reset();
    deployMutation.reset();
  }

  function handleDeployAnother() {
    setSelectedScanId(null);
    deployMutation.reset();
    planMutation.reset();
  }

  return (
    <div className="p-6 max-w-[1400px] mx-auto space-y-5">
      {/* Header */}
      <div>
        <Tooltip text="AI-powered market scanner that analyzes coins and recommends optimal strategy parameters.">
          <h1 className="text-2xl font-bold text-(--color-text-primary) cursor-help">AI Investment Advisor</h1>
        </Tooltip>
        <p className="text-sm text-(--color-text-secondary) mt-1">
          Scan the crypto market, get AI-powered recommendations, and deploy automated paper trading
        </p>
      </div>

      {/* Master-Detail Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-6 items-start">
        {/* Left: Sidebar */}
        <ScanSidebar
          history={scanHistory}
          activeScanId={activeScanId}
          selectedScanId={selectedScanId}
          onNewScan={handleScan}
          onSelect={handleSelectScan}
          onDelete={deleteScan}
          onCancel={cancelScan}
          onClear={clearHistory}
        />

        {/* Right: Content Panel */}
        <div>
          {/* State 1: Nothing selected AND not scanning → empty prompt */}
          {!selectedScan && !isScanning && (
            <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl flex flex-col items-center justify-center py-20 px-8">
              <Search className="w-10 h-10 text-(--color-text-secondary)/30 mb-4" />
              <h3 className="text-sm font-semibold text-(--color-text-primary) mb-1">Scan the market to get started</h3>
              <p className="text-xs text-(--color-text-secondary) text-center max-w-sm">
                Click "New Scan" to analyze all liquid crypto pairs on Binance using 11 technical indicators and get AI-powered trading recommendations.
              </p>
            </div>
          )}

          {/* State 2: Scanning, nothing selected → loading animation */}
          {isScanning && !selectedScan && (
            <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-8">
              <div className="flex items-center gap-4 mb-4">
                <div className="relative shrink-0">
                  <Search className="w-8 h-8 text-(--color-accent)" />
                  <Loader2 className="w-4 h-4 text-(--color-accent) animate-spin absolute -right-1 -bottom-1" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-(--color-text-primary)">Scanning Market...</h3>
                  <p className="text-xs text-(--color-text-secondary) mt-0.5">
                    Analyzing all liquid crypto pairs on Binance and running technical analysis. This may take 1-2 minutes.
                  </p>
                </div>
              </div>
              <div className="h-1.5 bg-(--color-bg-elevated) rounded-full overflow-hidden">
                <div className="h-full bg-(--color-accent)/60 rounded-full animate-[advisor-pulse_2s_ease-in-out_infinite] w-3/5" />
              </div>
            </div>
          )}

          {/* State 3: Completed scan selected → full content */}
          {selectedScan && scanResults && (
            <div className="space-y-5">
              {/* Step Indicator */}
              <StepIndicator current={currentStep + 1} />

              {/* Active Strategies Banner */}
              {activeCount > 0 && !deployed && (
                <div className="flex items-center gap-3 bg-(--color-accent)/5 border border-(--color-accent)/20 rounded-xl px-5 py-3">
                  <Info className="w-4 h-4 text-(--color-accent) shrink-0" />
                  <p className="text-sm text-(--color-text-primary)">
                    You have <span className="font-semibold">{activeCount} active {activeCount === 1 ? "strategy" : "strategies"}</span>.
                    Deploying will add a new one alongside them.
                  </p>
                </div>
              )}

              {/* AI Market Profile — only if no plan exists for this scan */}
              {marketProfile && !plan && !planMutation.isPending && (
                <MarketRecommendationPanel
                  marketProfile={marketProfile}
                  scanResults={scanResults}
                  amount={amount}
                  onAmountChange={setAmount}
                  onGeneratePlan={handleGeneratePlan}
                  isPlanPending={planMutation.isPending}
                />
              )}

              {/* Plan Generation Loading */}
              {planMutation.isPending && (
                <div className="bg-(--color-bg-surface) border border-(--color-accent)/30 rounded-xl p-6">
                  <div className="flex items-center gap-4">
                    <div className="relative shrink-0">
                      <Brain className="w-8 h-8 text-(--color-accent)" />
                      <Loader2 className="w-4 h-4 text-(--color-accent) animate-spin absolute -right-1 -bottom-1" />
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold text-(--color-text-primary)">Generating Investment Plan...</h3>
                      <p className="text-xs text-(--color-text-secondary) mt-0.5">
                        AI is analyzing {scanResults.length} pairs and creating a personalized trading strategy. This may take a few seconds.
                      </p>
                    </div>
                  </div>
                  <div className="mt-4 h-1.5 bg-(--color-bg-elevated) rounded-full overflow-hidden">
                    <div className="h-full bg-(--color-accent)/60 rounded-full animate-[advisor-pulse_2s_ease-in-out_infinite] w-3/5" />
                  </div>
                </div>
              )}

              {/* Plan Error */}
              {planMutation.isError && (
                <div className="rounded-xl border border-(--color-negative)/30 bg-(--color-negative)/10 px-5 py-4 space-y-2">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-(--color-negative) shrink-0" />
                    <p className="text-sm font-semibold text-(--color-negative)">Plan Generation Failed</p>
                  </div>
                  <p className="text-xs text-(--color-text-secondary)">
                    {(planMutation.error as Error)?.message || "An unexpected error occurred. Please try again."}
                  </p>
                  <button
                    onClick={handleGeneratePlan}
                    className="flex items-center gap-2 text-xs font-semibold text-(--color-accent) hover:text-(--color-accent)/80 transition-colors mt-1"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    Retry
                  </button>
                </div>
              )}

              {/* Deploy Error */}
              {deployMutation.isError && (
                <div className="rounded-lg border border-(--color-negative)/30 bg-(--color-negative)/10 px-4 py-3 text-sm text-(--color-negative)">
                  Failed to deploy plan. Please try again.
                </div>
              )}

              {/* Deploy Success */}
              {deployed && (
                <div className={cn(
                  "rounded-xl p-5 space-y-4 border",
                  isStrategyActive
                    ? "bg-(--color-positive)/10 border-(--color-positive)/30"
                    : "bg-(--color-bg-surface) border-(--color-border)"
                )}>
                  {/* Header with live status */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className={cn("w-5 h-5", isStrategyActive ? "text-(--color-positive)" : "text-(--color-text-secondary)")} />
                      <h3 className="text-sm font-semibold text-(--color-text-primary)">Strategy Deployed</h3>
                    </div>
                    <span className={cn(
                      "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold",
                      isStrategyActive
                        ? "bg-(--color-positive)/15 text-(--color-positive)"
                        : "bg-(--color-bg-elevated) text-(--color-text-secondary)"
                    )}>
                      <span className={cn(
                        "w-1.5 h-1.5 rounded-full",
                        isStrategyActive ? "bg-(--color-positive) animate-pulse" : "bg-(--color-text-secondary)/40"
                      )} />
                      {isStrategyActive ? "Active" : "Inactive"}
                    </span>
                  </div>

                  {deployedMessage && (
                    <p className="text-sm text-(--color-text-secondary)">{deployedMessage}</p>
                  )}

                  {/* Actions */}
                  <div className="flex flex-wrap items-center gap-3">
                    <button
                      onClick={() => {
                        if (selectedScan?.deployedStrategyId) {
                          toggleMutation.mutate({ id: selectedScan.deployedStrategyId });
                        }
                      }}
                      disabled={toggleMutation.isPending}
                      className={cn(
                        "flex items-center gap-2 font-semibold py-2 px-4 rounded-lg text-sm transition-colors disabled:opacity-50",
                        isStrategyActive
                          ? "bg-(--color-negative)/10 text-(--color-negative) hover:bg-(--color-negative)/20 border border-(--color-negative)/30"
                          : "bg-(--color-positive)/10 text-(--color-positive) hover:bg-(--color-positive)/20 border border-(--color-positive)/30"
                      )}
                    >
                      <Power className="w-4 h-4" />
                      {toggleMutation.isPending
                        ? (isStrategyActive ? "Deactivating..." : "Activating...")
                        : (isStrategyActive ? "Deactivate Strategy" : "Activate Strategy")
                      }
                    </button>
                    <button
                      onClick={() => navigate("/")}
                      className="flex items-center gap-2 bg-(--color-accent) hover:bg-(--color-accent)/90 text-white font-semibold py-2 px-4 rounded-lg text-sm transition-colors"
                    >
                      Go to Dashboard
                    </button>
                    <button
                      onClick={() => navigate("/strategies")}
                      className="flex items-center gap-2 text-sm font-medium text-(--color-text-secondary) hover:text-(--color-accent) transition-colors"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                      Manage Strategies
                    </button>
                    <button
                      onClick={handleDeployAnother}
                      className="flex items-center gap-2 text-sm font-medium text-(--color-text-secondary) hover:text-(--color-text-primary) transition-colors"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                      Deploy Another
                    </button>
                  </div>
                </div>
              )}

              {/* Plan display (persisted from store) */}
              {plan && (
                <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl overflow-hidden">
                  <div className="flex items-center justify-between px-5 py-3 border-b border-(--color-border)">
                    <h2 className="text-sm font-semibold text-(--color-text-primary)">
                      Investment Plan — AI Optimal Strategy
                    </h2>
                    <div className="flex items-center gap-3">
                      {!deployed && (
                        <button
                          onClick={handleRegeneratePlan}
                          className="flex items-center gap-1.5 text-xs text-(--color-text-secondary) hover:text-(--color-accent) transition-colors"
                        >
                          <RotateCcw className="w-3.5 h-3.5" />
                          Regenerate
                        </button>
                      )}
                      {!deployed && (
                        <button
                          onClick={() => navigate("/backtest?validate=plan")}
                          className="flex items-center gap-1.5 text-xs text-(--color-text-secondary) hover:text-(--color-accent) transition-colors"
                        >
                          <FlaskConical className="w-3.5 h-3.5" />
                          Validate Historically
                        </button>
                      )}
                      {!deployed && (
                        <button
                          onClick={handleDeploy}
                          disabled={deployMutation.isPending}
                          className="flex items-center gap-2 bg-(--color-positive) hover:bg-(--color-positive)/90 text-white font-semibold py-1.5 px-4 rounded-lg text-sm transition-colors disabled:opacity-50"
                        >
                          {deployMutation.isPending ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <Rocket className="w-4 h-4" />
                          )}
                          {deployMutation.isPending ? "Deploying..." : "Deploy & Start Trading"}
                        </button>
                      )}
                    </div>
                  </div>
                  <div className="p-5">
                    <PlanDisplay plan={plan} />
                  </div>
                </div>
              )}

              {/* Scan Results Table */}
              <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl overflow-hidden">
                <div className="flex items-center gap-3 px-5 py-3 border-b border-(--color-border)">
                  <h2 className="text-sm font-semibold text-(--color-text-primary)">
                    Market Scan Results ({scanResults.length} pairs analyzed)
                  </h2>
                </div>
                <ScanResultsTable results={scanResults} />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Keyframes for progress animations */}
      <style>{`
        @keyframes advisor-pulse {
          0%, 100% { width: 30%; opacity: 0.5; }
          50% { width: 80%; opacity: 1; }
        }
      `}</style>
    </div>
  );
}
