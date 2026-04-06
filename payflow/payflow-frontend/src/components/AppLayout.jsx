import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

// Cambiado de Layout a AppLayout
function AppLayout({ title, subtitle, children }) {
  const { logout, isAuthenticated, currentUser } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  const getNavLinkClass = ({ isActive }) =>
    isActive ? "nav-link nav-link-active" : "nav-link";

  return (
    <div className="app-shell">
      {isAuthenticated && (
        <header className="topbar">
          <div className="topbar-inner">
            <NavLink to="/dashboard" className="brand brand-link">
              PayFlow
            </NavLink>

            <nav className="nav-links" aria-label="Main navigation">
              <NavLink to="/dashboard" className={getNavLinkClass}>
                Dashboard
              </NavLink>

              <NavLink to="/wallet" className={getNavLinkClass}>
                Wallet
              </NavLink>

              <NavLink to="/payments" className={getNavLinkClass}>
                Payments
              </NavLink>

              <NavLink to="/payments/history" className={getNavLinkClass}>
                Payment History
              </NavLink>

              <NavLink to="/audit-logs" className={getNavLinkClass}>
                Audit Logs
              </NavLink>

              <NavLink to="/metrics" className={getNavLinkClass}>
                Metrics
              </NavLink>

              {currentUser?.email && (
                <span style={{ opacity: 0.85 }}>{currentUser.email}</span>
              )}

              <button type="button" className="btn btn-primary" onClick={handleLogout}>
                Logout
              </button>
            </nav>
          </div>
        </header>
      )}

      <main className="page-container">
        <div className="page-header">
          <h1 className="page-title">{title}</h1>
          {subtitle && <p className="page-subtitle">{subtitle}</p>}
        </div>

        {children}
      </main>
    </div>
  );
}

// Cambiado de export default Layout a AppLayout
export default AppLayout;