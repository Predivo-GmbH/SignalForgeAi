import { useNavigate } from "react-router-dom";
import { Sparkles } from "lucide-react";
import { useStrategies } from "@/hooks/useStrategies";
import { usePositions } from "@/hooks/usePositions";
import { AccountHero } from "@/components/portfolio/AccountHero";
import { HoldingsCard } from "@/components/portfolio/HoldingsCard";
import { PortfolioEquitySection } from "@/components/portfolio/PortfolioEquitySection";
import { ActiveStrategyCard } from "@/components/portfolio/ActiveStrategyCard";
import { RecentTradesCard } from "@/components/portfolio/RecentTradesCard";
import { PerformanceSummary } from "@/components/portfolio/PerformanceSummary";
import { PositionsTable } from "@/components/dashboard/PositionsTable";
import { RegimeWidget } from "@/components/dashboard/RegimeWidget";
import { SimulationCard } from "@/components/dashboard/SimulationCard";
import { SystemHealthBanner } from "@/components/dashboard/SystemHealthBanner";

export function PortfolioPage() {
  const navigate = useNavigate();
  const { data: strategiesData, isLoading: strategiesLoading } = useStrategies();
  const { data: positions, isLoading: positionsLoading } = usePositions();

  const hasActiveStrategy = strategiesData?.strategies?.some((s) => s.is_active) ?? false;
  const showOnboarding = !strategiesLoading && !hasActiveStrategy;

  return (
    <div className="flex flex-col gap-6 p-6">
      {/* System health — warns when services are down */}
      <SystemHealthBanner />

      {/* Onboarding banner when no active strategy */}
      {showOnboarding && (
        <button
          onClick={() => navigate("/advisor")}
          className="flex items-center gap-4 bg-gradient-to-r from-(--color-accent)/10 to-(--color-accent)/5 border border-(--color-accent)/30 rounded-xl px-6 py-4 text-left hover:border-(--color-accent)/50 transition-all group"
        >
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-(--color-accent)/15">
            <Sparkles className="w-5 h-5 text-(--color-accent)" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-(--color-text-primary) group-hover:text-(--color-accent) transition-colors">
              Get started with the AI Advisor
            </p>
            <p className="text-xs text-(--color-text-secondary) mt-0.5">
              Scan the market, pick the best trading pairs, and deploy an optimized strategy — all automated.
            </p>
          </div>
          <span className="shrink-0 text-xs font-medium text-(--color-accent) bg-(--color-accent)/10 rounded-lg px-3 py-1.5">
            Start scanning
          </span>
        </button>
      )}

      {/* Account Hero — equity, daily P&L, drawdown (only when trading) */}
      {hasActiveStrategy && <AccountHero />}

      {/* Crypto Holdings — exchange + manual + trading */}
      <HoldingsCard />

      {/* Middle grid: Equity curve + sidebar cards */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_380px] gap-6">
        <PortfolioEquitySection />
        <div className="flex flex-col gap-4">
          <RegimeWidget />
          <SimulationCard />
          <ActiveStrategyCard />
          <RecentTradesCard />
        </div>
      </div>

      {/* Performance Summary — 5-metric row */}
      <PerformanceSummary />

      {/* Open Positions */}
      <PositionsTable positions={positions} loading={positionsLoading} />
    </div>
  );
}

/** @deprecated Use PortfolioPage instead */
export const DashboardPage = PortfolioPage;
