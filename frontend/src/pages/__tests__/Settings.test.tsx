import { render, screen } from "@testing-library/react";
import { QueryClientProvider, QueryClient } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { AuthProvider } from "@/contexts/AuthContext";
import { SettingsPage } from "../Settings";

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider
    client={
      new QueryClient({
        defaultOptions: { queries: { retry: false } },
      })
    }
  >
    <AuthProvider>
      <MemoryRouter>{children}</MemoryRouter>
    </AuthProvider>
  </QueryClientProvider>
);

describe("SettingsPage", () => {
  test("renders page heading", () => {
    render(<SettingsPage />, { wrapper });
    expect(screen.getByText("Settings")).toBeInTheDocument();
  });

  test("renders page description", () => {
    render(<SettingsPage />, { wrapper });
    expect(
      screen.getByText("Manage broker connections, notifications, and AI usage")
    ).toBeInTheDocument();
  });

  test("renders tab buttons", () => {
    render(<SettingsPage />, { wrapper });
    expect(screen.getByText("Connections")).toBeInTheDocument();
    expect(screen.getByText("AI Usage")).toBeInTheDocument();
  });
});
