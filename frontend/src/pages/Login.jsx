
import { useState } from "react";
import { Link, NavLink, useNavigate, useLocation } from "react-router-dom";
import { ArrowRight, ShieldCheck } from "lucide-react";
import { useAuth } from "../context/authContext";

const DASHBOARD_PATHS = {
  student: "/dashboard/student",
  coordinator: "/dashboard/coordinator",
  admin: "/dashboard/admin",
  department_staff: "/dashboard/department",
};
const ROLE_DASHBOARD_PATHS = new Set(Object.values(DASHBOARD_PATHS));

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const { signIn } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const successMessage = location.state?.message;

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      const authenticatedUser = await signIn(email.trim(), password);
      const roleDashboard = DASHBOARD_PATHS[authenticatedUser.role];
      const requestedPath = location.state?.from;
      const destination = ROLE_DASHBOARD_PATHS.has(requestedPath)
        ? roleDashboard || "/"
        : requestedPath || roleDashboard || "/dashboard";
      navigate(destination, { replace: true });
    } catch (err) {
      setError(err.message || "Login failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main
      className="page-container"
      style={{ paddingTop: "64px", paddingBottom: "64px" }}
    >
      <section
        style={{
          maxWidth: "460px",
          margin: "0 auto",
          padding: "32px",
          border: "1px solid #e5e7eb",
          borderRadius: "16px",
        }}
      >
        <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
          <ShieldCheck size={24} />
          <span className="section-overline">
            MINDBRIDGE STUDENT SPACE
          </span>
        </div>

        <h1 style={{ marginTop: "20px" }}>
          Welcome <em>back.</em>
        </h1>

        <p>Sign in to access your MindBridge workspace.</p>

        {successMessage && (
          <p
            role="status"
            style={{
              marginTop: "16px",
              padding: "12px",
              borderRadius: "8px",
              backgroundColor: "#ecfdf5",
              color: "#065f46",
              fontSize: "14px",
            }}
          >
            {successMessage}
          </p>
        )}

        <form onSubmit={handleSubmit}>
          <div className="field-group" style={{ marginTop: "24px" }}>
            <label htmlFor="login-email">Email address</label>
            <input
              id="login-email"
              type="email"
              autoComplete="username"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </div>

          <div className="field-group" style={{ marginTop: "16px" }}>
            <label htmlFor="login-password">Password</label>
            <input
              id="login-password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </div>

          {error && (
            <p
              role="alert"
              className="field-error"
              style={{ marginTop: "16px" }}
            >
              {error}
            </p>
          )}

          <button
            type="submit"
            className="button-primary"
            disabled={loading}
            style={{
              marginTop: "24px",
              width: "100%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "8px",
            }}
          >
            {loading ? "Signing in..." : "Sign in"}
            {!loading && <ArrowRight size={17} />}
          </button>
        </form>

        <p style={{ marginTop: "20px", fontSize: "14px" }}>
          <NavLink to="/">Return to home</NavLink>
        </p>

        <p style={{ marginTop: "16px", fontSize: "14px" }}>
          Don't have an account?{" "}
          <Link
            to="/register"
            style={{
              color: "#2f4f4f",
              fontWeight: "600",
              textDecoration: "underline",
            }}
          >
            Create account
          </Link>
        </p>
      </section>
    </main>
  );
}
