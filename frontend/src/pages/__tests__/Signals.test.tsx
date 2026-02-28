import { render, screen } from "@testing-library/react";
import { QueryClientProvider, QueryClient } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { SignalsPage } from "../Signals";
import type { ReactNode } from "react";

const wrapper = ({ children }: { children: ReactNode }) => (
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

describe("SignalsPage", () => {
  test("renders page heading", () => {
    render(<SignalsPage />, { wrapper });
    expect(screen.getByText("Signals")).toBeInTheDocument();
  });

  test("renders generate signal button", () => {
    render(<SignalsPage />, { wrapper });
    expect(
      screen.getByRole("button", { name: /generate/i }),
    ).toBeInTheDocument();
  });
});
