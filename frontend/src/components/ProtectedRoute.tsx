import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";

export function ProtectedRoute() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-(--color-bg-base)" role="status" aria-live="polite">
        <div className="text-(--color-text-secondary)">Loading...</div>
      </div>
    );
  }

  return user ? <Outlet /> : <Navigate to="/login" replace />;
}
