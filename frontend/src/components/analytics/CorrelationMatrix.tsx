import { useState } from "react";
import { Activity, AlertTriangle, CheckCircle } from "lucide-react";
import { useSymbols } from "@/hooks/useSymbols";
import { useCorrelation } from "@/hooks/useAnalytics";
import { cn } from "@/lib/cn";

const FALLBACK_SYMBOLS = ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "META", "SPY", "QQQ"];

function interpretCorrelation(corr: number): {
  label: string;
  colorClass: string;
} {
  const abs = Math.abs(corr);
  if (abs > 0.7) {
    return { label: "Strong correlation", colorClass: "text-(--color-warning)" };
  }
  if (abs > 0.4) {
    return { label: "Moderate correlation", colorClass: "text-(--color-text-secondary)" };
  }
  return { label: "Weak correlation", colorClass: "text-(--color-positive)" };
}

export function CorrelationMatrix() {
  const { data: symbols } = useSymbols();
  const symbolList = symbols && symbols.length > 0 ? symbols : FALLBACK_SYMBOLS;

  const [symbolA, setSymbolA] = useState("");
  const [symbolB, setSymbolB] = useState("");

  const { data, isLoading, error } = useCorrelation(symbolA, symbolB);

  return (
    <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-6 space-y-5">
      <h2 className="text-sm font-medium text-(--color-text-secondary) uppercase tracking-wider">
        Correlation Analysis
      </h2>

      {/* Symbol selectors */}
      <div className="flex flex-wrap items-center gap-3">
        <select
          value={symbolA}
          onChange={(e) => setSymbolA(e.target.value)}
          className="bg-(--color-bg-elevated) text-(--color-text-primary) text-sm rounded-lg border border-(--color-border) px-3 py-2 outline-none focus:ring-1 focus:ring-(--color-accent)"
        >
          <option value="">Select symbol A</option>
          {symbolList.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>

        <span className="text-sm text-(--color-text-secondary)">vs</span>

        <select
          value={symbolB}
          onChange={(e) => setSymbolB(e.target.value)}
          className="bg-(--color-bg-elevated) text-(--color-text-primary) text-sm rounded-lg border border-(--color-border) px-3 py-2 outline-none focus:ring-1 focus:ring-(--color-accent)"
        >
          <option value="">Select symbol B</option>
          {symbolList.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>

      {/* Same symbol warning */}
      {symbolA && symbolB && symbolA === symbolB && (
        <div className="flex items-center gap-2 text-sm text-(--color-warning)">
          <AlertTriangle className="w-4 h-4" />
          <span>Select two different symbols to compute correlation</span>
        </div>
      )}

      {/* Loading state */}
      {isLoading && (
        <div className="flex items-center justify-center py-8">
          <div className="w-6 h-6 border-2 border-(--color-accent) border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="text-sm text-(--color-negative)">
          Failed to load correlation: {error.message}
        </div>
      )}

      {/* Result */}
      {data && !isLoading && (
        <div className="bg-(--color-bg-elevated)/50 rounded-lg p-5 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-(--color-text-secondary)">
              {data.symbol_a} / {data.symbol_b}
            </span>
            <span className="text-xs text-(--color-text-secondary)">
              {data.data_points} data points
            </span>
          </div>
          <p className="text-3xl font-bold font-mono text-(--color-text-primary)">
            {data.correlation.toFixed(4)}
          </p>
          {(() => {
            const { label, colorClass } = interpretCorrelation(
              data.correlation
            );
            const Icon =
              Math.abs(data.correlation) > 0.7 ? AlertTriangle : CheckCircle;
            return (
              <div className={cn("flex items-center gap-2 text-sm", colorClass)}>
                <Icon className="w-4 h-4" />
                <span>{label}</span>
              </div>
            );
          })()}
        </div>
      )}

      {/* Empty state */}
      {!data && !isLoading && !error && !symbolA && !symbolB && (
        <div className="flex flex-col items-center justify-center py-8 space-y-2">
          <Activity className="w-8 h-8 text-(--color-text-secondary)/40" />
          <p className="text-sm text-(--color-text-secondary)">
            Select two symbols to analyze their correlation
          </p>
        </div>
      )}
    </div>
  );
}
