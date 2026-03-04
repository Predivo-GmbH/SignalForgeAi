import { create } from "zustand";
import { persist } from "zustand/middleware";
import { api } from "@/lib/api";
import type { ScoredCrypto, MarketProfile, InvestmentPlan } from "@/hooks/useAdvisor";

export interface ScanHistoryEntry {
  id: string;
  timestamp: number;
  status: "running" | "completed" | "failed" | "cancelled";
  pairs_scanned: number;
  pairs_scored: number;
  results: ScoredCrypto[];
  market_profile: MarketProfile | null;
  error?: string;
  plan?: InvestmentPlan;
  planAmount?: number;
  deployedStrategyId?: string;
  deployedMessage?: string;
}

interface AdvisorState {
  scanHistory: ScanHistoryEntry[];
  activeScanId: string | null;

  startScan: (topN?: number) => void;
  cancelScan: () => void;
  deleteScan: (id: string) => void;
  clearHistory: () => void;
  setPlan: (scanId: string, plan: InvestmentPlan, amount: number) => void;
  setDeployed: (scanId: string, strategyId: string, message: string) => void;
  clearPlan: (scanId: string) => void;
}

// Runtime-only: not persisted
let _abortController: AbortController | null = null;

export const useAdvisorStore = create<AdvisorState>()(
  persist(
    (set, get) => ({
      scanHistory: [],
      activeScanId: null,

      startScan: (topN = 100) => {
        // Cancel any existing scan first
        if (get().activeScanId) {
          get().cancelScan();
        }

        const id = crypto.randomUUID();
        const entry: ScanHistoryEntry = {
          id,
          timestamp: Date.now(),
          status: "running",
          pairs_scanned: 0,
          pairs_scored: 0,
          results: [],
          market_profile: null,
        };

        set((s) => ({
          scanHistory: [entry, ...s.scanHistory],
          activeScanId: id,
        }));

        const controller = new AbortController();
        _abortController = controller;

        api
          .post<{
            pairs_scanned: number;
            pairs_scored: number;
            results: ScoredCrypto[];
            market_profile?: MarketProfile;
          }>("/advisor/scan", { top_n: topN }, { signal: controller.signal })
          .then((data) => {
            set((s) => ({
              activeScanId: null,
              scanHistory: s.scanHistory.map((h) =>
                h.id === id
                  ? {
                      ...h,
                      status: "completed" as const,
                      pairs_scanned: data.pairs_scanned,
                      pairs_scored: data.pairs_scored,
                      results: data.results,
                      market_profile: data.market_profile ?? null,
                    }
                  : h,
              ),
            }));
            _abortController = null;
          })
          .catch((err) => {
            if (err.name === "AbortError") {
              set((s) => ({
                activeScanId: null,
                scanHistory: s.scanHistory.map((h) =>
                  h.id === id ? { ...h, status: "cancelled" as const } : h,
                ),
              }));
            } else {
              set((s) => ({
                activeScanId: null,
                scanHistory: s.scanHistory.map((h) =>
                  h.id === id
                    ? { ...h, status: "failed" as const, error: err.message }
                    : h,
                ),
              }));
            }
            _abortController = null;
          });
      },

      cancelScan: () => {
        _abortController?.abort();
        _abortController = null;
      },

      deleteScan: (id: string) => {
        const { activeScanId } = get();
        if (activeScanId === id) {
          get().cancelScan();
        }
        set((s) => ({
          activeScanId: s.activeScanId === id ? null : s.activeScanId,
          scanHistory: s.scanHistory.filter((h) => h.id !== id),
        }));
      },

      clearHistory: () => {
        if (get().activeScanId) {
          get().cancelScan();
        }
        set({ scanHistory: [], activeScanId: null });
      },

      setPlan: (scanId, plan, amount) => {
        set((s) => ({
          scanHistory: s.scanHistory.map((h) =>
            h.id === scanId ? { ...h, plan, planAmount: amount } : h,
          ),
        }));
      },

      setDeployed: (scanId, strategyId, message) => {
        set((s) => ({
          scanHistory: s.scanHistory.map((h) =>
            h.id === scanId
              ? { ...h, deployedStrategyId: strategyId, deployedMessage: message }
              : h,
          ),
        }));
      },

      clearPlan: (scanId) => {
        set((s) => ({
          scanHistory: s.scanHistory.map((h) =>
            h.id === scanId
              ? { ...h, plan: undefined, planAmount: undefined, deployedStrategyId: undefined, deployedMessage: undefined }
              : h,
          ),
        }));
      },
    }),
    {
      name: "sf-advisor",
      version: 1,
      partialize: (state) => ({
        scanHistory: state.scanHistory
          .map((h) =>
            // If app was closed while a scan was running, mark it as failed
            h.status === "running" ? { ...h, status: "failed" as const, error: "Interrupted" } : h,
          )
          .slice(0, 10),
      }),
    },
  ),
);
