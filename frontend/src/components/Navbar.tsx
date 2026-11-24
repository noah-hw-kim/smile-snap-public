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
    <nav className={`navbar navbar-expand-lg navbar-dark bg-${variant}`}>
      <div className="container">
        <span className="navbar-brand">{title}</span>
        <div className="d-flex align-items-center">
          <span className="text-white me-3">{subtitle}</span>
          {showBackToAdmin && (
            <Link to="/admin" className="btn btn-outline-light btn-sm me-2">
              <i className="bi bi-arrow-left" /> Back to Admin
            </Link>
          )}
          {showUserViewLink && (
            <Link to="/dashboard" className="btn btn-outline-light btn-sm me-2">
              <i className="bi bi-person" /> User View
            </Link>
          )}
          {onLogout && (
            <button type="button" className="btn btn-outline-light btn-sm" onClick={onLogout}>
              <i className="bi bi-box-arrow-right" /> Logout
            </button>
          )}
        </div>
      </div>
    </nav>
  );
}
