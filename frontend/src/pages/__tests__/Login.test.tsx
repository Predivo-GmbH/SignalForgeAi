import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AuthProvider } from "@/contexts/AuthContext";
import { LoginPage } from "../Login";

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <AuthProvider>
    <MemoryRouter>{children}</MemoryRouter>
  </AuthProvider>
);

describe("LoginPage", () => {
  test("renders email field and send code button", () => {
    render(<LoginPage />, { wrapper });
    expect(screen.getByPlaceholderText("Email")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /send code/i })).toBeInTheDocument();
  });

  test("renders welcome text", () => {
    render(<LoginPage />, { wrapper });
    expect(screen.getByText("Welcome back")).toBeInTheDocument();
  });
});
