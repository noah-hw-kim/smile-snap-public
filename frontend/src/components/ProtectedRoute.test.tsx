import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import { AuthProvider } from "../context/AuthContext";
import { ProtectedRoute } from "./ProtectedRoute";

function renderRoutes(initialEntry: string) {
  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route path="/login" element={<div>Login View</div>} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <div>Dashboard View</div>
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin"
            element={
              <ProtectedRoute requiredRole="admin">
                <div>Admin View</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    </AuthProvider>
  );
}

describe("ProtectedRoute", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("redirects unauthenticated users to /login", () => {
    renderRoutes("/dashboard");
    expect(screen.getByText("Login View")).toBeInTheDocument();
  });

  it("redirects non-admin users away from /admin to /dashboard", () => {
    localStorage.setItem("authToken", "user-token");
    localStorage.setItem(
      "user",
      JSON.stringify({
        userId: "u1",
        email: "user@example.com",
        displayName: "Regular User",
        role: "user",
      })
    );

    renderRoutes("/admin");
    expect(screen.getByText("Dashboard View")).toBeInTheDocument();
  });

  it("allows admin users to access /admin", () => {
    localStorage.setItem("authToken", "admin-token");
    localStorage.setItem(
      "user",
      JSON.stringify({
        userId: "a1",
        email: "admin@example.com",
        displayName: "Admin User",
        role: "admin",
      })
    );

    renderRoutes("/admin");
    expect(screen.getByText("Admin View")).toBeInTheDocument();
  });
});
