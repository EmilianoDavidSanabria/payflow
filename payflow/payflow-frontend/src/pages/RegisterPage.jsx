import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client";

function RegisterPage() {
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage("");

    const normalizedEmail = email.trim().toLowerCase();

    if (!normalizedEmail || !password || !confirmPassword) {
      setErrorMessage("Enter your email, password, and password confirmation.");
      return;
    }

    if (password !== confirmPassword) {
      setErrorMessage("Passwords do not match.");
      return;
    }

    try {
      setSubmitting(true);

      await api.post("/users/register/", {
        email: normalizedEmail,
        password,
      });

      navigate("/", {
        replace: true,
        state: {
          registrationSuccess: "Account created successfully. Sign in to continue.",
          registeredEmail: normalizedEmail,
        },
      });
    } catch (error) {
      console.error("REGISTER ERROR:", error);
      const data = error.response?.data;

      if (data?.email?.length) {
        setErrorMessage(data.email[0]);
      } else if (data?.password?.length) {
        setErrorMessage(data.password[0]);
      } else if (data?.detail) {
        setErrorMessage(data.detail);
      } else {
        setErrorMessage("Could not create your account.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="login-shell">
      <div className="card login-card">
        <p className="eyebrow">PAYFLOW</p>
        <h1 className="login-title">Create account</h1>
        <p className="login-subtitle">
          Register with your email and password, then sign in to use PayFlow.
        </p>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="label">Email</label>
            <input
              className="input"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              autoComplete="email"
            />
          </div>

          <div className="form-group">
            <label className="label">Password</label>
            <input
              className="input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Create your password"
              autoComplete="new-password"
            />
          </div>

          <div className="form-group">
            <label className="label">Confirm password</label>
            <input
              className="input"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Repeat your password"
              autoComplete="new-password"
            />
          </div>

          <button className="btn btn-primary" type="submit" disabled={submitting}>
            {submitting ? "Creating account..." : "Create account"}
          </button>
        </form>

        {errorMessage && (
          <div className="message message-error">{errorMessage}</div>
        )}

        <p style={{ marginTop: "16px", marginBottom: 0 }}>
          Already have an account?{" "}
          <Link to="/" className="link-inline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}

export default RegisterPage;