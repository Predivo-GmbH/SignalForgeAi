import { render, screen } from "@testing-library/react";
import { QueryClientProvider, QueryClient } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { StrategiesPage } from "../Strategies";

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

describe("StrategiesPage", () => {
  test("renders page heading", () => {
    render(<StrategiesPage />, { wrapper });
    expect(screen.getByText("Strategies")).toBeInTheDocument();
  });

  test("renders page description", () => {
    render(<StrategiesPage />, { wrapper });
    expect(
      screen.getByText("Monitor and manage your active trading strategies")
    ).toBeInTheDocument();
  });
});
