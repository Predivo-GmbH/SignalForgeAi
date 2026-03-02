import { useState } from "react";
import { useNavigate } from "react-router-dom";
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
} from "lucide-react";
import { cn } from "@/lib/cn";
import { Badge } from "@/components/ui/Badge";
import {
  useScanMarket,
  useGeneratePlan,
  useDeployPlan,
} from "@/hooks/useAdvisor";
import type { ScoredCrypto, InvestmentPlan } from "@/hooks/useAdvisor";

function formatVolume(vol: number): string {
  if (vol >= 1_000_000_000) return `$${(vol / 1_000_000_000).toFixed(1)}B`;
  if (vol >= 1_000_000) return `$${(vol / 1_000_000).toFixed(1)}M`;
  return `$${vol.toLocaleString()}`;
}

function formatPrice(price: number): string {
  if (price >= 1000) return `$${price.toFixed(2)}`;
  if (price >= 1) return `$${price.toFixed(4)}`;
  return `$${price.toFixed(6)}`;
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
      {/* Summary */}
      <div className="bg-(--color-bg-elevated)/50 rounded-lg p-4">
        <p className="text-sm text-(--color-text-primary) leading-relaxed">{plan.summary}</p>
      </div>

      {/* Selected Cryptos */}
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

      {/* Risk Config */}
      <div>
        <h3 className="text-sm font-semibold text-(--color-text-primary) mb-2">Strategy Configuration</h3>
        <div className="flex flex-wrap gap-3">
          {Object.entries(plan.risk_config).map(([key, val]) => (
            <span key={key} className="text-xs bg-(--color-bg-elevated) rounded px-2 py-1">
              <span className="text-(--color-text-secondary)">{key.replace(/_/g, " ")}:</span>{" "}
              <span className="font-mono font-semibold text-(--color-text-primary)">
                {typeof val === "number" && val < 1 && key !== "account_equity"
                  ? `${(val * 100).toFixed(1)}%`
                  : typeof val === "number" && key === "account_equity"
                  ? `$${val.toLocaleString()}`
                  : String(val)}
              </span>
            </span>
          ))}
        </div>
      </div>

      {/* Expected Behavior */}
      {plan.expected_behavior && (
        <div className="bg-(--color-accent-soft) rounded-lg p-3">
          <p className="text-xs text-(--color-text-primary)">{plan.expected_behavior}</p>
        </div>
      )}

      {/* Warnings */}
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
  const [amount, setAmount] = useState(10000);
  const [riskTolerance, setRiskTolerance] = useState("balanced");
  const [scanResults, setScanResults] = useState<ScoredCrypto[] | null>(null);
  const [plan, setPlan] = useState<InvestmentPlan | null>(null);
  const [deployed, setDeployed] = useState(false);

  const scanMutation = useScanMarket();
  const planMutation = useGeneratePlan();
  const deployMutation = useDeployPlan();

  const currentStep = deployed ? 3 : plan ? 2 : scanResults ? 1 : 0;

  function handleScan() {
    scanMutation.mutate(100, {
      onSuccess: (data) => {
        setScanResults(data.results);
        setPlan(null);
        setDeployed(false);
      },
    });
  }

  function handleGeneratePlan() {
    if (!scanResults) return;
    planMutation.mutate(
      { amount, risk_tolerance: riskTolerance, scan_results: scanResults },
      { onSuccess: (data) => setPlan(data) },
    );
  }

  function handleDeploy() {
    if (!plan) return;
    deployMutation.mutate(plan, {
      onSuccess: () => setDeployed(true),
    });
  }

  return (
    <div className="p-6 space-y-6 max-w-[1400px] mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-(--color-text-primary)">AI Investment Advisor</h1>
        <p className="text-sm text-(--color-text-secondary) mt-1">
          Scan the crypto market, get AI-powered recommendations, and deploy automated paper trading
        </p>
      </div>

      {/* Step Indicator */}
      <StepIndicator current={currentStep + 1} />

      {/* Investment Amount + Risk */}
      <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-5">
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
                onChange={(e) => setAmount(Number(e.target.value))}
                min={100}
                max={10000000}
                className="w-48 bg-(--color-bg-elevated) border border-(--color-border) rounded-lg pl-9 pr-3 py-2 text-sm font-mono text-(--color-text-primary) focus:outline-none focus:ring-2 focus:ring-(--color-accent)/50"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="block text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">
              Risk Tolerance
            </label>
            <div className="flex gap-2">
              {([
                { key: "conservative", label: "Conservative", desc: "1% risk per trade, confluence 70+, 4h timeframe. Fewer but higher-quality trades." },
                { key: "balanced", label: "Balanced", desc: "2% risk per trade, confluence 50+, 1h timeframe. Good starting point for most users." },
                { key: "aggressive", label: "Aggressive", desc: "3% risk per trade, confluence 35+, multi-timeframe. More trades, higher drawdowns." },
              ] as const).map((r) => (
                <button
                  key={r.key}
                  onClick={() => setRiskTolerance(r.key)}
                  className={cn(
                    "flex flex-col items-start px-3 py-2 rounded-lg transition-colors text-left",
                    riskTolerance === r.key
                      ? "bg-(--color-accent) text-white"
                      : "bg-(--color-bg-elevated) text-(--color-text-secondary) hover:text-(--color-text-primary)"
                  )}
                >
                  <span className="text-sm font-medium">{r.label}</span>
                  <span className={cn(
                    "text-[10px] leading-tight mt-0.5",
                    riskTolerance === r.key ? "text-white/70" : "text-(--color-text-secondary)/70"
                  )}>
                    {r.desc}
                  </span>
                </button>
              ))}
            </div>
          </div>

          <button
            onClick={handleScan}
            disabled={scanMutation.isPending}
            className="flex items-center gap-2 bg-(--color-accent) hover:bg-(--color-accent)/90 text-white font-semibold py-2 px-5 rounded-lg text-sm transition-colors disabled:opacity-50"
          >
            {scanMutation.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Search className="w-4 h-4" />
            )}
            {scanMutation.isPending ? "Scanning Binance..." : "Scan Market"}
          </button>
        </div>
        {scanMutation.isPending && (
          <p className="mt-3 text-xs text-(--color-text-secondary)">
            Scanning all liquid crypto pairs on Binance and running technical analysis... This may take 1-2 minutes.
          </p>
        )}
      </div>

      {/* Scan Error */}
      {scanMutation.isError && (
        <div className="rounded-lg border border-(--color-negative)/30 bg-(--color-negative)/10 px-4 py-3 text-sm text-(--color-negative)">
          Failed to scan market. Please try again.
        </div>
      )}

      {/* Scan Results */}
      {scanResults && (
        <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl overflow-hidden">
          <div className="flex items-center justify-between px-5 py-3 border-b border-(--color-border)">
            <h2 className="text-sm font-semibold text-(--color-text-primary)">
              Market Scan Results ({scanResults.length} pairs analyzed)
            </h2>
            {!plan && (
              <button
                onClick={handleGeneratePlan}
                disabled={planMutation.isPending}
                className="flex items-center gap-2 bg-(--color-accent) hover:bg-(--color-accent)/90 text-white font-semibold py-1.5 px-4 rounded-lg text-sm transition-colors disabled:opacity-50"
              >
                {planMutation.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Brain className="w-4 h-4" />
                )}
                {planMutation.isPending ? "Generating Plan..." : "Generate AI Plan"}
              </button>
            )}
          </div>
          <ScanResultsTable results={scanResults} />
        </div>
      )}

      {/* Plan Error */}
      {planMutation.isError && (
        <div className="rounded-lg border border-(--color-negative)/30 bg-(--color-negative)/10 px-4 py-3 text-sm text-(--color-negative)">
          Failed to generate plan. Please try again.
        </div>
      )}

      {/* Plan */}
      {plan && (
        <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl overflow-hidden">
          <div className="flex items-center justify-between px-5 py-3 border-b border-(--color-border)">
            <h2 className="text-sm font-semibold text-(--color-text-primary)">
              Investment Plan — {plan.strategy_preset.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())}
            </h2>
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
          <div className="p-5">
            <PlanDisplay plan={plan} />
          </div>
        </div>
      )}

      {/* Deploy Error */}
      {deployMutation.isError && (
        <div className="rounded-lg border border-(--color-negative)/30 bg-(--color-negative)/10 px-4 py-3 text-sm text-(--color-negative)">
          Failed to deploy plan. Please try again.
        </div>
      )}

      {/* Deploy Success */}
      {deployed && deployMutation.data && (
        <div className="bg-(--color-positive)/10 border border-(--color-positive)/30 rounded-xl p-5 space-y-3">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-(--color-positive)" />
            <h3 className="text-sm font-semibold text-(--color-positive)">Strategy Deployed Successfully</h3>
          </div>
          <p className="text-sm text-(--color-text-primary)">{deployMutation.data.message}</p>
          <button
            onClick={() => navigate("/")}
            className="flex items-center gap-2 bg-(--color-accent) hover:bg-(--color-accent)/90 text-white font-semibold py-2 px-4 rounded-lg text-sm transition-colors"
          >
            Go to Dashboard
          </button>
        </div>
      )}
    </div>
  );
}
