import { BacktestForm } from "@/components/backtest/BacktestForm";
import { BacktestResults } from "@/components/backtest/BacktestResults";
import { useRunBacktest } from "@/hooks/useBacktest";
import type { BacktestResult } from "@/hooks/useBacktest";

export function BacktestPage() {
  const mutation = useRunBacktest();
  const result: BacktestResult | null = (mutation.data as BacktestResult) ?? null;

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

      {/* Split layout */}
      <div className="grid grid-cols-1 lg:grid-cols-[minmax(280px,35%)_1fr] gap-6">
        <BacktestForm
          onSubmit={(req) => mutation.mutate(req)}
          isLoading={mutation.isPending}
        />
        <BacktestResults
          result={result}
          isLoading={mutation.isPending}
          error={mutation.error}
        />
      </div>
    </div>
  );
}
