import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext"; 

function ProtectedRoute({ children }) {
  const { isAuthenticated, authResolved } = useAuth();

  if (!authResolved) {
    return <p style={{ padding: "24px" }}>Loading session...</p>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  return children;
}

export default ProtectedRoute;