import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { JournalPage } from "../Journal";

describe("JournalPage", () => {
  test("renders page heading", () => {
    render(
      <MemoryRouter>
        <JournalPage />
      </MemoryRouter>
    );
    expect(screen.getByText("Trade Journal")).toBeInTheDocument();
  });

  test("renders coming soon message", () => {
    render(
      <MemoryRouter>
        <JournalPage />
      </MemoryRouter>
    );
    expect(
      screen.getByText("AI-assisted trade review coming in Phase 5")
    ).toBeInTheDocument();
  });

  test("renders planned features", () => {
    render(
      <MemoryRouter>
        <JournalPage />
      </MemoryRouter>
    );
    expect(screen.getByText("AI Pattern Recognition")).toBeInTheDocument();
    expect(screen.getByText("Trade Annotations")).toBeInTheDocument();
    expect(screen.getByText("Natural Language Queries")).toBeInTheDocument();
  });
});
