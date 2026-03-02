import { render, screen } from "@testing-library/react";
import { QueryClientProvider, QueryClient } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { vi } from "vitest";
import { StrategyDetailPage } from "../StrategyDetail";

vi.mock("@/hooks/useStrategies", () => ({
  useStrategy: () => ({ data: undefined, isLoading: false }),
  useToggleStrategy: () => ({ mutate: vi.fn(), isPending: false }),
  useDeleteStrategy: () => ({ mutate: vi.fn(), isPending: false }),
}));

vi.mock("@/hooks/useSignals", () => ({
  useSignals: () => ({ data: undefined, isLoading: false }),
}));

vi.mock("@/hooks/useTrades", () => ({
  useTradeStats: () => ({ data: undefined }),
}));

vi.mock("@/hooks/useStrategyBacktest", () => ({
  useRunStrategyBacktest: () => ({
    mutate: vi.fn(),
    isPending: false,
    data: null,
    error: null,
  }),
}));

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider
    client={
      new QueryClient({
        defaultOptions: { queries: { retry: false } },
      })
    }
  >
    <MemoryRouter initialEntries={["/strategies/test-id-123"]}>
      <Routes>
        <Route path="/strategies/:id" element={children} />
      </Routes>
    </MemoryRouter>
  </QueryClientProvider>
);

describe("StrategyDetailPage", () => {
  test("renders back link when strategy not found", () => {
    render(<StrategyDetailPage />, { wrapper });
    expect(screen.getByText("Back to Strategies")).toBeInTheDocument();
  });

  test("renders not-found message for invalid strategy id", () => {
    render(<StrategyDetailPage />, { wrapper });
    expect(screen.getByText("Strategy not found.")).toBeInTheDocument();
  });
});
