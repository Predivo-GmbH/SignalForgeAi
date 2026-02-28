import { render, screen } from "@testing-library/react";
import { QueryClientProvider, QueryClient } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { StrategyConfigPage } from "../StrategyConfig";

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

describe("StrategyConfigPage", () => {
  test("renders page heading and create button", () => {
    render(<StrategyConfigPage />, { wrapper });
    expect(screen.getByText("Strategies")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /new strategy/i })
    ).toBeInTheDocument();
  });

  test("renders page description", () => {
    render(<StrategyConfigPage />, { wrapper });
    expect(
      screen.getByText("Configure and manage trading strategies")
    ).toBeInTheDocument();
  });
});
