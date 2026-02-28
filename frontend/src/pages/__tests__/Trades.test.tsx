import { render, screen } from "@testing-library/react";
import { QueryClientProvider, QueryClient } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { TradesPage } from "../Trades";

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

describe("TradesPage", () => {
  test("renders page heading", () => {
    render(<TradesPage />, { wrapper });
    expect(screen.getByText("Trade History")).toBeInTheDocument();
  });

  test("renders stats cards section", () => {
    render(<TradesPage />, { wrapper });
    expect(
      screen.getByText("Execution log with performance metrics")
    ).toBeInTheDocument();
  });

  test("renders table column headers", () => {
    render(<TradesPage />, { wrapper });
    expect(screen.getByText("Symbol")).toBeInTheDocument();
    expect(screen.getByText("Exit Reason")).toBeInTheDocument();
  });
});
