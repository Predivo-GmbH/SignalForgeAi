import { render, screen } from "@testing-library/react";
import { QueryClientProvider, QueryClient } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { AnalyticsPage } from "../Analytics";

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

describe("AnalyticsPage", () => {
  test("renders page heading", () => {
    render(<AnalyticsPage />, { wrapper });
    expect(screen.getByText("Analytics")).toBeInTheDocument();
  });

  test("renders subtitle text", () => {
    render(<AnalyticsPage />, { wrapper });
    expect(
      screen.getByText("Portfolio performance, risk metrics, and strategy comparison")
    ).toBeInTheDocument();
  });

  test("renders strategy comparison loading state", () => {
    render(<AnalyticsPage />, { wrapper });
    expect(screen.getByText("Loading strategy comparison...")).toBeInTheDocument();
  });
});
