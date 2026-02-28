import { Activity } from "lucide-react";
import { useEquityHistory } from "@/hooks/useAnalytics";
import { MetricsGrid } from "@/components/analytics/MetricsGrid";
import { EquityCurve } from "@/components/analytics/EquityCurve";
import { CorrelationMatrix } from "@/components/analytics/CorrelationMatrix";

export function AnalyticsPage() {
  const { data, isLoading, error } = useEquityHistory();

  return (
    <div className="max-w-[1200px] mx-auto p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-(--color-text-primary)">
          Analytics
        </h1>
        <p className="text-sm text-(--color-text-secondary) mt-1">
          Portfolio performance and risk metrics
        </p>
      </div>

      {/* Metrics section */}
      {isLoading && (
        <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-6 flex items-center justify-center min-h-[200px]">
          <div className="text-center space-y-3">
            <div className="w-8 h-8 border-2 border-(--color-accent) border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="text-sm text-(--color-text-secondary)">
              Loading analytics...
            </p>
          </div>
        </div>
      )}

      {error && (
        <div className="bg-(--color-bg-surface) border border-(--color-negative)/30 rounded-xl p-6 flex items-center justify-center min-h-[200px]">
          <div className="text-center space-y-2">
            <p className="text-sm text-(--color-negative) font-medium">
              Failed to load analytics
            </p>
            <p className="text-xs text-(--color-text-secondary)">
              {error.message}
            </p>
          </div>
        </div>
      )}

      {data && (
        <>
          <MetricsGrid data={data} />
          <EquityCurve points={data.points} />
        </>
      )}

      {!isLoading && !error && !data && (
        <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-6 flex items-center justify-center min-h-[200px]">
          <div className="text-center space-y-2">
            <Activity className="w-10 h-10 text-(--color-text-secondary)/40 mx-auto" />
            <p className="text-sm text-(--color-text-secondary)">
              No analytics data available yet
            </p>
            <p className="text-xs text-(--color-text-secondary)/60">
              Start trading to generate performance metrics
            </p>
          </div>
        </div>
      )}

      {/* Correlation section */}
      <CorrelationMatrix />
    </div>
  );
}
