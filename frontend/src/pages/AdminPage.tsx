import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { AlertBanner, type AlertState } from "../components/AlertBanner";
import { Navbar } from "../components/Navbar";
import { useAuth } from "../context/AuthContext";
import type { User } from "../types/api";

export function AdminPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [deletingUserId, setDeletingUserId] = useState<string | null>(null);
  const [alert, setAlert] = useState<AlertState | null>(null);

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getAdminUsers();
      setUsers(data);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      setAlert({ message: `Failed to load users: ${message}`, variant: "danger" });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchUsers();
  }, [fetchUsers]);

  const handleViewUser = (targetUserId: string) => {
    navigate(`/dashboard?viewUser=${encodeURIComponent(targetUserId)}`);
  };

  const handleDeleteUser = async (targetUser: User) => {
    if (targetUser.userId === user?.userId) {
      setAlert({
        message: "You cannot delete your own account from the admin panel.",
        variant: "warning",
      });
      return;
    }

    const confirmMessage =
      `⚠️ WARNING: This action cannot be undone!\n\n` +
      `This will permanently delete user "${targetUser.email}" and:\n` +
      `- All their photos\n` +
      `- All their diary entries\n` +
      `- All associated data\n\n` +
      `Type "DELETE" to confirm:`;

    const userInput = window.prompt(confirmMessage);
    if (userInput === "DELETE") {
      const finalConfirm = window.confirm(
        `Are you absolutely sure you want to delete user "${targetUser.email}"?`
      );
      if (!finalConfirm) return;

      setDeletingUserId(targetUser.userId);
      try {
        await api.deleteUser(targetUser.userId);
        setAlert({
          message: `User "${targetUser.email}" has been permanently deleted.`,
          variant: "success",
        });
        await fetchUsers();
      } catch (error) {
        const message = error instanceof Error ? error.message : "Unknown error";
        setAlert({ message: `Failed to delete user: ${message}`, variant: "danger" });
      } finally {
        setDeletingUserId(null);
      }
    } else if (userInput !== null) {
      setAlert({
        message: 'User deletion cancelled. You must type "DELETE" exactly.',
        variant: "warning",
      });
    }
  };

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  return (
    <>
      <Navbar
        title="👨‍💼 Admin Dashboard"
        variant="danger"
        subtitle={`Admin: ${user?.email ?? ""}`}
        showUserViewLink
        onLogout={handleLogout}
      />

      <div className="container mt-3">
        <AlertBanner alert={alert} onDismiss={() => setAlert(null)} />
      </div>

      <div className="container mt-4">
        <div className="row">
          <div className="col-12">
            <div className="card">
              <div className="card-header d-flex justify-content-between align-items-center">
                <div>
                  <h5 className="mb-0">👥 User Management</h5>
                  <small className="text-muted">Manage all users and their data</small>
                </div>
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  onClick={() => void fetchUsers()}
                >
                  <i className="bi bi-arrow-clockwise" /> Refresh
                </button>
              </div>
              <div className="card-body">
                {loading ? (
                  <div className="text-center">
                    <div className="spinner-border text-primary" role="status">
                      <span className="visually-hidden">Loading users...</span>
                    </div>
                  </div>
                ) : users.length === 0 ? (
                  <p className="text-muted text-center mb-0">No users found.</p>
                ) : (
                  users.map((targetUser) => {
                    const isDeleting = deletingUserId === targetUser.userId;
                    return (
                      <div key={targetUser.userId} className="card mb-2 user-item">
                        <div className="card-body">
                          <div className="d-flex justify-content-between align-items-start">
                            <div
                              className="flex-grow-1"
                              onClick={() => handleViewUser(targetUser.userId)}
                            >
                              <h6 className="mb-1">
                                {targetUser.displayName ?? targetUser.email}
                              </h6>
                              <p className="mb-1">
                                <strong>Email:</strong> {targetUser.email}
                              </p>
                              <p className="mb-1">
                                <strong>Role:</strong>{" "}
                                <span
                                  className={`badge ${
                                    targetUser.role === "admin" ? "bg-danger" : "bg-primary"
                                  }`}
                                >
                                  {targetUser.role}
                                </span>
                              </p>
                              <p className="mb-0">
                                <small className="text-muted">
                                  <i className="bi bi-calendar3" /> Registered:{" "}
                                  {new Date(targetUser.createdAt).toLocaleString()}
                                </small>
                              </p>
                            </div>
                            <div className="ms-3 d-flex flex-column gap-1">
                              <button
                                type="button"
                                className="btn btn-sm btn-outline-primary"
                                onClick={() => handleViewUser(targetUser.userId)}
                              >
                                <i className="bi bi-eye" /> View
                              </button>
                              <button
                                type="button"
                                className="btn btn-sm btn-danger"
                                disabled={isDeleting}
                                onClick={() => void handleDeleteUser(targetUser)}
                              >
                                {isDeleting ? (
                                  <>
                                    <span className="spinner-border spinner-border-sm me-2" />
                                    Loading...
                                  </>
                                ) : (
                                  <>
                                    <i className="bi bi-trash" /> Delete
                                  </>
                                )}
                              </button>
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
