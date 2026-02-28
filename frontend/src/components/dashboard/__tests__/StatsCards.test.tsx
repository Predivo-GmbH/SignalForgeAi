import { render, screen } from "@testing-library/react";
import { StatsCards } from "../StatsCards";

describe("StatsCards", () => {
  test("renders stat cards with values", () => {
    render(
      <StatsCards
        stats={{
          total_trades: 42,
          win_rate: 65.5,
          profit_factor: 1.85,
          total_pnl: 2340.5,
          avg_pnl: 55.73,
          best_trade: 450.0,
          worst_trade: -180.0,
        }}
      />,
    );
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByText("65.5%")).toBeInTheDocument();
    expect(screen.getByText("1.85")).toBeInTheDocument();
  });

  test("renders positive P&L with + prefix", () => {
    render(
      <StatsCards
        stats={{
          total_trades: 10,
          win_rate: 60,
          profit_factor: 1.5,
          total_pnl: 500.0,
          avg_pnl: 50,
          best_trade: 200,
          worst_trade: -100,
        }}
      />,
    );
    expect(screen.getByText("+$500.00")).toBeInTheDocument();
  });

  test("renders negative P&L with - prefix", () => {
    render(
      <StatsCards
        stats={{
          total_trades: 5,
          win_rate: 40,
          profit_factor: 0.8,
          total_pnl: -250.0,
          avg_pnl: -50,
          best_trade: 100,
          worst_trade: -200,
        }}
      />,
    );
    expect(screen.getByText("-$250.00")).toBeInTheDocument();
  });

  test("renders loading state", () => {
    render(<StatsCards stats={null} />);
    expect(screen.getAllByTestId("stat-skeleton")).toHaveLength(4);
  });
});
