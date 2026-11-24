import { Link } from "react-router-dom";

interface NavbarProps {
  title: string;
  variant?: "primary" | "danger";
  subtitle: string;
  showBackToAdmin?: boolean;
  showUserViewLink?: boolean;
  onLogout?: () => void;
}

export function Navbar({
  title,
  variant = "primary",
  subtitle,
  showBackToAdmin = false,
  showUserViewLink = false,
  onLogout,
}: NavbarProps) {
  return (
    <nav className="navbar navbar-expand-lg ss-navbar">
      <div className="container">
        <div className="d-flex align-items-center gap-2">
          <span className="ss-brand">{title}</span>
          {variant === "danger" && (
            <span className="badge rounded-pill ss-badge-admin">Admin</span>
          )}
        </div>
        <div className="d-flex align-items-center gap-2">
          <span className="text-muted small me-2 d-none d-sm-inline">{subtitle}</span>
          {showBackToAdmin && (
            <Link to="/admin" className="btn btn-outline-secondary btn-sm">
              <i className="bi bi-arrow-left me-1" />
              Back to Admin
            </Link>
          )}
          {showUserViewLink && (
            <Link to="/dashboard" className="btn btn-outline-secondary btn-sm">
              <i className="bi bi-person me-1" />
              User View
            </Link>
          )}
          {onLogout && (
            <button
              type="button"
              className="btn btn-outline-secondary btn-sm"
              onClick={onLogout}
            >
              <i className="bi bi-box-arrow-right me-1" />
              Logout
            </button>
          )}
        </div>
      </div>
    </nav>
  );
}
