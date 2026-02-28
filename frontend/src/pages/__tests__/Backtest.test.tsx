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
  test("renders both tabs", () => {
    render(<BacktestPage />, { wrapper });
    expect(screen.getByText("Single Backtest")).toBeInTheDocument();
    expect(screen.getByText("Walk-Forward")).toBeInTheDocument();
  });

  test("renders configuration form", () => {
    render(<BacktestPage />, { wrapper });
    expect(screen.getByText("Backtest Lab")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /run backtest/i })
    ).toBeInTheDocument();
  });

  test("renders empty results state", () => {
    render(<BacktestPage />, { wrapper });
    expect(
      screen.getByText("Run a backtest to see results")
    ).toBeInTheDocument();
  });

  test("renders timeframe options", () => {
    render(<BacktestPage />, { wrapper });
    expect(screen.getByText("1h")).toBeInTheDocument();
    expect(screen.getByText("4h")).toBeInTheDocument();
    expect(screen.getByText("1D")).toBeInTheDocument();
  });
});
