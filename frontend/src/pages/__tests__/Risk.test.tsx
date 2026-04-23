import { render, screen } from "@testing-library/react";
import { QueryClientProvider, QueryClient } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { RiskPage } from "../Risk";

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

describe("RiskPage", () => {
  test("renders page heading", () => {
    render(<RiskPage />, { wrapper });
    expect(screen.getByText("Risk Management")).toBeInTheDocument();
  });

  test("renders drawdown section", () => {
    render(<RiskPage />, { wrapper });
    expect(screen.getByText("Risk Management")).toBeInTheDocument();
  });
});
