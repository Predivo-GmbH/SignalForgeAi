import { useSearchParams } from "react-router-dom";
import { useRunStrategyBacktest } from "@/hooks/useStrategyBacktest";
import { StrategyBacktestForm } from "@/components/backtest/StrategyBacktestForm";
import { StrategyBacktestResults } from "@/components/backtest/StrategyBacktestResults";
import type { StrategyBacktestResult } from "@/hooks/useStrategyBacktest";

export function BacktestPage() {
  const [searchParams] = useSearchParams();
  const validatePlan = searchParams.get("validate") === "plan";

  const strategyBtMutation = useRunStrategyBacktest();
  const strategyBtResult = (strategyBtMutation.data as StrategyBacktestResult) ?? null;

  return (
    <div className="p-4 sm:p-6 space-y-4 sm:space-y-6 max-w-[1600px] mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-(--color-text-primary)">
          Strategy Validation
        </h1>
        <p className="text-sm text-(--color-text-secondary) mt-1">
          Test how a strategy or AI Advisor plan would have performed on historical data
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[minmax(280px,35%)_1fr] gap-6">
        <StrategyBacktestForm
          onSubmit={(req) => strategyBtMutation.mutate(req)}
          isLoading={strategyBtMutation.isPending}
          prefillPlan={validatePlan}
        />
        <StrategyBacktestResults
          result={strategyBtResult}
          isLoading={strategyBtMutation.isPending}
          error={strategyBtMutation.error}
        />
      </div>
    </div>
  );
}
