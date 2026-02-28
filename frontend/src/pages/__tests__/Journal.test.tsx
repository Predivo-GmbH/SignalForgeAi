import { render, screen } from "@testing-library/react";
import { QueryClientProvider, QueryClient } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { JournalPage } from "../Journal";

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

describe("JournalPage", () => {
  test("renders page heading", () => {
    render(<JournalPage />, { wrapper });
    expect(screen.getByText("Trade Journal")).toBeInTheDocument();
  });

  test("renders AI-powered subtitle text", () => {
    render(<JournalPage />, { wrapper });
    expect(
      screen.getByText("AI-powered trade analysis and review")
    ).toBeInTheDocument();
  });

  test("renders Pattern Summary section title", () => {
    render(<JournalPage />, { wrapper });
    expect(screen.getByText("Pattern Summary")).toBeInTheDocument();
  });

  test("renders Recent Trades section title", () => {
    render(<JournalPage />, { wrapper });
    expect(screen.getByText("Recent Trades")).toBeInTheDocument();
  });
});
