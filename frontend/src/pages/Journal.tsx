import { useState } from "react";
import {
  Brain,
  Loader2,
  TrendingUp,
  TrendingDown,
  Lightbulb,
  AlertTriangle,
  Sparkles,
} from "lucide-react";
import { cn } from "@/lib/cn";
import { useTrades } from "@/hooks/useTrades";
import { useAnalyzeTrade, usePatternSummary } from "@/hooks/useJournal";
import type { Trade } from "@/hooks/useTrades";

/* ---------- Trade Card ---------- */

interface TradeCardProps {
  trade: Trade;
  analysis: {
    analysis: string;
    patterns: string[];
    recommendations: string[];
  } | null;
  isAnalyzing: boolean;
  onAnalyze: () => void;
}

function TradeCard({ trade, analysis, isAnalyzing, onAnalyze }: TradeCardProps) {
  const isLong = trade.direction?.toUpperCase() === "LONG";
  const pnlValue = trade.pnl ?? 0;
  const isProfitable = pnlValue >= 0;

  return (
    <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-5 space-y-4">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-base font-semibold font-mono text-(--color-text-primary)">
            {trade.symbol}
          </span>
          <span
            className={cn(
              "px-2 py-0.5 rounded-md text-xs font-semibold uppercase",
              isLong
                ? "bg-(--color-positive)/15 text-(--color-positive)"
                : "bg-(--color-negative)/15 text-(--color-negative)"
            )}
          >
            {isLong ? "Long" : "Short"}
          </span>
        </div>

        <button
          onClick={onAnalyze}
          disabled={isAnalyzing}
          className="flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg bg-(--color-accent-soft) text-(--color-accent) hover:bg-(--color-accent)/15 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isAnalyzing ? (
            <>
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              Analyzing...
            </>
          ) : (
            <>
              <Brain className="w-3.5 h-3.5" />
              Analyze
            </>
          )}
        </button>
      </div>

      {/* Metrics row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div>
          <p className="text-xs text-(--color-text-secondary) mb-0.5">Entry</p>
          <p className="text-sm font-mono text-(--color-text-primary)">
            {trade.entry_price.toFixed(2)}
          </p>
        </div>
        <div>
          <p className="text-xs text-(--color-text-secondary) mb-0.5">Exit</p>
          <p className="text-sm font-mono text-(--color-text-primary)">
            {trade.exit_price != null ? trade.exit_price.toFixed(2) : "—"}
          </p>
        </div>
        <div>
          <p className="text-xs text-(--color-text-secondary) mb-0.5">P&L</p>
          <p
            className={cn(
              "text-sm font-mono font-semibold flex items-center gap-1",
              isProfitable ? "text-(--color-positive)" : "text-(--color-negative)"
            )}
          >
            {isProfitable ? (
              <TrendingUp className="w-3.5 h-3.5" />
            ) : (
              <TrendingDown className="w-3.5 h-3.5" />
            )}
            {isProfitable ? "+" : ""}
            {pnlValue.toFixed(2)}
          </p>
        </div>
        <div>
          <p className="text-xs text-(--color-text-secondary) mb-0.5">
            Confluence
          </p>
          <p className="text-sm font-mono text-(--color-text-primary)">
            {trade.confluence_score}/10
          </p>
        </div>
      </div>

      {/* Analysis result */}
      {analysis && (
        <div className="border-t border-(--color-border) pt-4 space-y-3">
          <div className="flex items-center gap-2 mb-2">
            <Sparkles className="w-4 h-4 text-(--color-accent)" />
            <span className="text-sm font-semibold text-(--color-text-primary)">
              AI Analysis
            </span>
          </div>

          <p className="text-sm text-(--color-text-secondary) leading-relaxed">
            {analysis.analysis}
          </p>

          {analysis.patterns.length > 0 && (
            <div>
              <p className="text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider mb-1.5">
                Patterns
              </p>
              <div className="flex flex-wrap gap-1.5">
                {analysis.patterns.map((pattern) => (
                  <span
                    key={pattern}
                    className="px-2 py-0.5 rounded-md text-xs font-medium bg-(--color-accent-soft) text-(--color-accent)"
                  >
                    {pattern}
                  </span>
                ))}
              </div>
            </div>
          )}

          {analysis.recommendations.length > 0 && (
            <div>
              <p className="text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider mb-1.5">
                Recommendations
              </p>
              <ul className="space-y-1">
                {analysis.recommendations.map((rec) => (
                  <li
                    key={rec}
                    className="text-sm text-(--color-text-secondary) flex items-start gap-2"
                  >
                    <Lightbulb className="w-3.5 h-3.5 mt-0.5 shrink-0 text-(--color-warning)" />
                    {rec}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ---------- Journal Page ---------- */

export function JournalPage() {
  const { data: tradesData, isLoading: tradesLoading } = useTrades(20, 0);
  const { data: patternData, isLoading: patternsLoading } = usePatternSummary();
  const analyzeMutation = useAnalyzeTrade();

  const [analyses, setAnalyses] = useState<
    Record<string, { analysis: string; patterns: string[]; recommendations: string[] }>
  >({});
  const [analyzingId, setAnalyzingId] = useState<string | null>(null);

  function handleAnalyze(trade: Trade) {
    setAnalyzingId(trade.id);
    analyzeMutation.mutate(
      { trade_id: trade.id },
      {
        onSuccess: (data) => {
          setAnalyses((prev) => ({ ...prev, [trade.id]: data }));
          setAnalyzingId(null);
        },
        onError: () => {
          setAnalyzingId(null);
        },
      }
    );
  }

  const trades = tradesData?.trades ?? [];

  return (
    <div className="p-6 space-y-6 max-w-[900px] mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-(--color-text-primary)">
          Trade Journal
        </h1>
        <p className="text-sm text-(--color-text-secondary) mt-1">
          AI-powered trade analysis and review
        </p>
      </div>

      {/* Pattern Summary */}
      <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-6 space-y-4">
        <div className="flex items-center gap-2">
          <Brain className="w-5 h-5 text-(--color-accent)" />
          <h2 className="text-lg font-semibold text-(--color-text-primary)">
            Pattern Summary
          </h2>
        </div>

        {patternsLoading ? (
          <div className="flex items-center gap-2 text-sm text-(--color-text-secondary)">
            <Loader2 className="w-4 h-4 animate-spin" />
            Loading patterns...
          </div>
        ) : patternData ? (
          <div className="space-y-4">
            <p className="text-sm text-(--color-text-secondary) leading-relaxed">
              {patternData.summary}
            </p>

            {patternData.top_patterns.length > 0 && (
              <div>
                <p className="text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider mb-1.5">
                  Top Patterns
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {patternData.top_patterns.map((pattern) => (
                    <span
                      key={pattern}
                      className="px-2.5 py-1 rounded-lg text-xs font-medium bg-(--color-accent-soft) text-(--color-accent)"
                    >
                      {pattern}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {patternData.areas_to_improve.length > 0 && (
              <div>
                <p className="text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider mb-1.5">
                  Areas to Improve
                </p>
                <ul className="space-y-1.5">
                  {patternData.areas_to_improve.map((area) => (
                    <li
                      key={area}
                      className="text-sm text-(--color-text-secondary) flex items-start gap-2"
                    >
                      <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0 text-(--color-warning)" />
                      {area}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ) : (
          <p className="text-sm text-(--color-text-secondary)">
            Complete more trades to unlock pattern insights.
          </p>
        )}
      </div>

      {/* Recent Trades */}
      <div className="space-y-4">
        <h2 className="text-lg font-semibold text-(--color-text-primary)">
          Recent Trades
        </h2>

        {tradesLoading ? (
          <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-12 flex items-center justify-center">
            <div className="flex items-center gap-2 text-sm text-(--color-text-secondary)">
              <Loader2 className="w-4 h-4 animate-spin" />
              Loading trades...
            </div>
          </div>
        ) : trades.length === 0 ? (
          <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-12 text-center">
            <p className="text-sm text-(--color-text-secondary)">
              No trades recorded yet. Execute some trades to start your journal.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {trades.map((trade) => (
              <TradeCard
                key={trade.id}
                trade={trade}
                analysis={analyses[trade.id] ?? null}
                isAnalyzing={analyzingId === trade.id}
                onAnalyze={() => handleAnalyze(trade)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
