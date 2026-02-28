import { useAuth } from "../auth";

describe("auth store", () => {
  beforeEach(() => {
    localStorage.clear();
    useAuth.setState({
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
    });
  });

  test("login sets tokens and isAuthenticated", () => {
    useAuth.getState().setTokens("access-123", "refresh-456");
    const state = useAuth.getState();
    expect(state.accessToken).toBe("access-123");
    expect(state.refreshToken).toBe("refresh-456");
    expect(state.isAuthenticated).toBe(true);
  });

  test("logout clears tokens", () => {
    useAuth.getState().setTokens("a", "r");
    useAuth.getState().logout();
    const state = useAuth.getState();
    expect(state.accessToken).toBeNull();
    expect(state.isAuthenticated).toBe(false);
  });

  test("persists to localStorage", () => {
    useAuth.getState().setTokens("a", "r");
    const stored = JSON.parse(localStorage.getItem("sf-auth") || "{}");
    expect(stored.state?.accessToken).toBe("a");
  });
});
