import { Activity, Award, BarChart3 } from "lucide-react";
import { cn } from "@/lib/cn";
import type { WFOResult } from "@/hooks/useWalkForward";

function pnlColor(value: number | null | undefined): string {
  if (value == null) return "text-(--color-text-secondary)";
  return value >= 0 ? "text-(--color-positive)" : "text-(--color-negative)";
}

function formatMetricValue(value: number | null): string {
  if (value == null) return "N/A";
  return value.toFixed(4);
}

interface WalkForwardResultsProps {
  result: WFOResult | null;
  isLoading: boolean;
  error: Error | null;
}

export function WalkForwardResults({
  result,
  isLoading,
  error,
}: WalkForwardResultsProps) {
  if (isLoading) {
    return (
      <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-6 flex items-center justify-center min-h-[400px]">
        <div className="text-center space-y-3">
          <div className="w-8 h-8 border-2 border-(--color-accent) border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-sm text-(--color-text-secondary)">
            Running walk-forward optimization...
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-(--color-bg-surface) border border-(--color-negative)/30 rounded-xl p-6 flex items-center justify-center min-h-[400px]">
        <div className="text-center space-y-2">
          <p className="text-sm text-(--color-negative) font-medium">
            Optimization failed
          </p>
          <p className="text-xs text-(--color-text-secondary)">
            {error.message}
          </p>
        </div>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-6 flex items-center justify-center min-h-[400px]">
        <div className="text-center space-y-2">
          <Activity className="w-10 h-10 text-(--color-text-secondary)/40 mx-auto" />
          <p className="text-sm text-(--color-text-secondary)">
            Run an optimization to see results
          </p>
          <p className="text-xs text-(--color-text-secondary)/60">
            Configure parameters and click &quot;Run Optimization&quot;
          </p>
        </div>
      </div>
    );
  }

  const bestParamEntries = Object.entries(result.best_params);
  const oosMetricEntries = Object.entries(result.out_of_sample_metrics);

  return (
    <div className="space-y-6">
      {/* Best Parameters */}
      <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-6 space-y-4">
        <div className="flex items-center gap-2">
          <Award className="w-5 h-5 text-(--color-accent)" />
          <h2 className="text-lg font-semibold text-(--color-text-primary)">
            Best Parameters
          </h2>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {bestParamEntries.map(([key, value]) => (
            <div
              key={key}
              className="bg-(--color-bg-elevated)/50 rounded-lg p-3 space-y-1"
            >
              <p className="text-xs text-(--color-text-secondary) uppercase tracking-wider">
                {key.replace(/_/g, " ")}
              </p>
              <p className="text-lg font-semibold font-mono text-(--color-text-primary)">
                {value}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Out-of-Sample Metrics */}
      <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-6 space-y-4">
        <div className="flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-(--color-accent)" />
          <h2 className="text-lg font-semibold text-(--color-text-primary)">
            Out-of-Sample Metrics
          </h2>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {oosMetricEntries.map(([key, value]) => (
            <div
              key={key}
              className="bg-(--color-bg-elevated)/50 rounded-lg p-3 space-y-1"
            >
              <p className="text-xs text-(--color-text-secondary) uppercase tracking-wider">
                {key.replace(/_/g, " ")}
              </p>
              <p
                className={cn(
                  "text-lg font-semibold font-mono",
                  pnlColor(value)
                )}
              >
                {formatMetricValue(value)}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Fold Results Table */}
      {result.fold_results.length > 0 && (
        <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-6 space-y-4">
          <h2 className="text-lg font-semibold text-(--color-text-primary)">
            Fold Results
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-(--color-border)">
                  <th className="text-left py-2 px-3 text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">
                    Fold
                  </th>
                  <th className="text-left py-2 px-3 text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">
                    Score
                  </th>
                  <th className="text-left py-2 px-3 text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">
                    Params
                  </th>
                  <th className="text-left py-2 px-3 text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">
                    Metrics
                  </th>
                </tr>
              </thead>
              <tbody>
                {result.fold_results.map((fold) => {
                  const metricsStr = Object.entries(fold.oos_metrics)
                    .map(
                      ([k, v]) =>
                        `${k}: ${v != null ? v.toFixed(3) : "N/A"}`
                    )
                    .join(", ");
                  const paramsStr = Object.entries(fold.params)
                    .map(([k, v]) => `${k}=${v}`)
                    .join(", ");

                  return (
                    <tr
                      key={fold.fold}
                      className="border-b border-(--color-border)/50 last:border-0"
                    >
                      <td className="py-2.5 px-3 font-mono text-(--color-text-primary)">
                        #{fold.fold}
                      </td>
                      <td
                        className={cn(
                          "py-2.5 px-3 font-mono font-semibold",
                          pnlColor(fold.oos_score)
                        )}
                      >
                        {fold.oos_score.toFixed(4)}
                      </td>
                      <td className="py-2.5 px-3 font-mono text-xs text-(--color-text-secondary)">
                        {paramsStr}
                      </td>
                      <td className="py-2.5 px-3 font-mono text-xs text-(--color-text-secondary)">
                        {metricsStr}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
