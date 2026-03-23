import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";

function LoginPage() {
  const navigate = useNavigate();
  const { login } = useAuth();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage("");

    if (!username || !password) {
      setErrorMessage("Username and password are required.");
      return;
    }

    try {
      setSubmitting(true);

      const response = await api.post("/api/token/", {
        username,
        password,
      });

      const { access, refresh } = response.data;

      login(access, refresh);
      navigate("/dashboard");
    } catch (error) {
      console.error("LOGIN ERROR:", error);
      setErrorMessage("Invalid username or password.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="login-shell">
      <div className="card login-card">
        <p className="eyebrow">Digital wallet demo</p>
        <h1 className="login-title">PayFlow</h1>
        <p className="login-subtitle">
          A payment platform with wallet funding, payment requests, audit trails,
          metrics, and provider-ready flows.
        </p>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="label">Username</label>
            <input
              className="input"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter your username"
              autoComplete="username"
            />
          </div>

          <div className="form-group">
            <label className="label">Password</label>
            <input
              className="input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
              autoComplete="current-password"
            />
          </div>

          <button className="btn btn-primary" type="submit" disabled={submitting}>
            {submitting ? "Signing in..." : "Login"}
          </button>
        </form>

        {errorMessage && (
          <div className="message message-error">{errorMessage}</div>
        )}
      </div>
    </div>
  );
}

export default LoginPage;