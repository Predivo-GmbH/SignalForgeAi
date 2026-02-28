import { useEffect } from "react";
import { PasswordGate } from "./components/PasswordGate";
import { LoginPage } from "./pages/Login";
import { useTheme } from "./lib/theme";

function App() {
  const { theme } = useTheme();

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
  }, []);

  return (
    <PasswordGate>
      <LoginPage />
    </PasswordGate>
  );
}

export default App;
