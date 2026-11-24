import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import type { UserRole } from "../types/api";

interface ProtectedRouteProps {
  requiredRole?: UserRole;
  children: ReactNode;
}

export function ProtectedRoute({ requiredRole, children }: ProtectedRouteProps) {
  const { isAuthenticated, isAdmin, user } = useAuth();

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace />;
  }

  if (requiredRole === "admin" && !isAdmin) {
    return <Navigate to="/dashboard" replace />;
  }

  if (requiredRole === "user" && user.role !== "user" && user.role !== "admin") {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}
