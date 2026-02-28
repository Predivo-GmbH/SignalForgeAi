import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { ApiKeysPage } from "../ApiKeys";

describe("ApiKeysPage", () => {
  test("renders page heading", () => {
    render(
      <MemoryRouter>
        <ApiKeysPage />
      </MemoryRouter>
    );
    expect(
      screen.getByText("API Keys & Broker Connections")
    ).toBeInTheDocument();
  });

  test("renders broker cards", () => {
    render(
      <MemoryRouter>
        <ApiKeysPage />
      </MemoryRouter>
    );
    expect(screen.getByText("Alpaca")).toBeInTheDocument();
    expect(screen.getByText("Binance")).toBeInTheDocument();
  });

  test("renders phase 5 note", () => {
    render(
      <MemoryRouter>
        <ApiKeysPage />
      </MemoryRouter>
    );
    expect(
      screen.getByText(/backend broker crud coming in phase 5/i)
    ).toBeInTheDocument();
  });
});
