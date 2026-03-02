import { render, screen } from "@testing-library/react";
import { QueryClientProvider, QueryClient } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { BacktestPage } from "../Backtest";

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider
    client={
      new QueryClient({
        defaultOptions: { queries: { retry: false } },
      })
    }
  >
    <MemoryRouter>{children}</MemoryRouter>
  </QueryClientProvider>
);

describe("BacktestPage", () => {
  test("renders page heading", () => {
    render(<BacktestPage />, { wrapper });
    expect(screen.getByRole("heading", { level: 1, name: "Strategy Validation" })).toBeInTheDocument();
  });

  test("renders page description", () => {
    render(<BacktestPage />, { wrapper });
    expect(
      screen.getByText("Test how a strategy or AI Advisor plan would have performed on historical data")
    ).toBeInTheDocument();
  });
});
