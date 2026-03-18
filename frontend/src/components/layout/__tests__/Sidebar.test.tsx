import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Sidebar } from "../Sidebar";

describe("Sidebar", () => {
  test("renders navigation links", () => {
    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    );
    expect(screen.getByText("Portfolio")).toBeInTheDocument();
    expect(screen.getByText("AI Advisor")).toBeInTheDocument();
    expect(screen.getByText("Trades")).toBeInTheDocument();
  });

  test("renders logo text", () => {
    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    );
    expect(screen.getByText("SignalForgeAI")).toBeInTheDocument();
  });

  test("renders all navigation items", () => {
    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    );
    expect(screen.getByText("Strategies")).toBeInTheDocument();
    expect(screen.getByText("Analytics")).toBeInTheDocument();
    expect(screen.getByText("Settings")).toBeInTheDocument();
  });
});
