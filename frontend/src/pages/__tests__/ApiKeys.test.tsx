import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ApiKeysPage } from "../ApiKeys";

function renderWithProviders(ui: React.ReactNode) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ApiKeysPage", () => {
  test("renders page heading", () => {
    renderWithProviders(<ApiKeysPage />);
    expect(screen.getByText("API Connections")).toBeInTheDocument();
  });

  test("renders connect broker button", () => {
    renderWithProviders(<ApiKeysPage />);
    expect(screen.getByText("Connect Broker")).toBeInTheDocument();
  });

  test("renders description text", () => {
    renderWithProviders(<ApiKeysPage />);
    expect(
      screen.getByText("Manage exchange credentials and trading mode"),
    ).toBeInTheDocument();
  });
});
