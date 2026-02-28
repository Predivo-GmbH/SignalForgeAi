import { StatsCards } from "@/components/dashboard/StatsCards";
import { PriceChart } from "@/components/dashboard/PriceChart";
import { SignalFeed } from "@/components/dashboard/SignalFeed";
import { PositionsTable } from "@/components/dashboard/PositionsTable";
import { RegimeWidget } from "@/components/dashboard/RegimeWidget";
import { useTradeStats } from "@/hooks/useTrades";
import { useSignals } from "@/hooks/useSignals";
import { usePositions } from "@/hooks/usePositions";

export function DashboardPage() {
  const { data: stats, isLoading: statsLoading } = useTradeStats();
  const { data: signalsData, isLoading: signalsLoading } = useSignals(10, 0);
  const { data: positions, isLoading: positionsLoading } = usePositions();

  return (
    <div className="flex flex-col gap-6 p-6">
      {/* Top row: Stats cards */}
      <StatsCards stats={statsLoading ? null : (stats ?? null)} />

      {/* Middle: Chart + sidebar */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_380px] gap-6 min-h-[420px]">
        <PriceChart />
        <div className="flex flex-col gap-4">
          <RegimeWidget />
          <div className="flex-1 min-h-0">
            <SignalFeed
              signals={signalsData?.signals}
              loading={signalsLoading}
            />
          </div>
        </div>
      </div>

      {/* Bottom: Positions table */}
      <PositionsTable positions={positions} loading={positionsLoading} />
    </div>
  );
}
