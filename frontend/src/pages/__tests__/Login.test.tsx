import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AuthProvider } from "@/contexts/AuthContext";

const LoginPage = (await import("../auth/LoginPage")).default;

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <AuthProvider>
    <MemoryRouter>{children}</MemoryRouter>
  </AuthProvider>
);

describe("LoginPage", () => {
  test("renders sign in heading", () => {
    render(<LoginPage />, { wrapper });
    expect(screen.getByText(/sign in to signalforgeai/i)).toBeInTheDocument();
  });

  test("renders sign up link", () => {
    render(<LoginPage />, { wrapper });
    expect(screen.getByText("Sign up")).toBeInTheDocument();
  });
});
