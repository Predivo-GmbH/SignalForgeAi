import { useState } from "react";
import { BacktestForm } from "@/components/backtest/BacktestForm";
import { BacktestResults } from "@/components/backtest/BacktestResults";
import { WalkForwardForm } from "@/components/backtest/WalkForwardForm";
import { WalkForwardResults } from "@/components/backtest/WalkForwardResults";
import { useRunBacktest } from "@/hooks/useBacktest";
import { useRunWalkForward } from "@/hooks/useWalkForward";
import type { BacktestResult } from "@/hooks/useBacktest";
import type { WFOResult } from "@/hooks/useWalkForward";
import { cn } from "@/lib/cn";

type Tab = "backtest" | "walkforward";

const TABS: { key: Tab; label: string }[] = [
  { key: "backtest", label: "Single Backtest" },
  { key: "walkforward", label: "Walk-Forward" },
];

export function BacktestPage() {
  const [activeTab, setActiveTab] = useState<Tab>("backtest");

  const backtestMutation = useRunBacktest();
  const backtestResult: BacktestResult | null =
    (backtestMutation.data as BacktestResult) ?? null;

  const wfoMutation = useRunWalkForward();
  const wfoResult: WFOResult | null =
    (wfoMutation.data as WFOResult) ?? null;

  return (
    <div className="p-6 space-y-6 max-w-[1600px] mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-(--color-text-primary)">
          Backtest Lab
        </h1>
        <p className="text-sm text-(--color-text-secondary) mt-1">
          Simulate strategy performance on historical data
        </p>
      </div>

      {/* Tab bar */}
      <div className="border-b border-(--color-border)">
        <div className="flex gap-6">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={cn(
                "pb-2.5 text-sm font-medium transition-colors border-b-2 -mb-px",
                activeTab === tab.key
                  ? "border-(--color-accent) text-(--color-accent)"
                  : "border-transparent text-(--color-text-secondary) hover:text-(--color-text-primary)"
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab content */}
      {activeTab === "backtest" ? (
        <div className="grid grid-cols-1 lg:grid-cols-[minmax(280px,35%)_1fr] gap-6">
          <BacktestForm
            onSubmit={(req) => backtestMutation.mutate(req)}
            isLoading={backtestMutation.isPending}
          />
          <BacktestResults
            result={backtestResult}
            isLoading={backtestMutation.isPending}
            error={backtestMutation.error}
          />
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-[minmax(280px,35%)_1fr] gap-6">
          <WalkForwardForm
            onSubmit={(req) => wfoMutation.mutate(req)}
            isLoading={wfoMutation.isPending}
          />
          <WalkForwardResults
            result={wfoResult}
            isLoading={wfoMutation.isPending}
            error={wfoMutation.error}
          />
        </div>
      )}
    </div>
  );
}
