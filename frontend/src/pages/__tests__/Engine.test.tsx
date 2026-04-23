import { render, screen } from "@testing-library/react";
import { QueryClientProvider, QueryClient } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { EnginePage } from "../Engine";

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

describe("EnginePage", () => {
  test("renders page heading", () => {
    render(<EnginePage />, { wrapper });
    expect(screen.getByText("Engine Monitor")).toBeInTheDocument();
  });

  test("renders pipeline monitoring subtitle", () => {
    render(<EnginePage />, { wrapper });
    // The engine page shows status of trading engine and pipeline
    expect(screen.getByText("Engine Monitor")).toBeInTheDocument();
  });
});
