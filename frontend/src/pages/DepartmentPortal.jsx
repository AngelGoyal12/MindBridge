import { useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { ArrowLeft, ArrowRight, LockKeyhole } from "lucide-react";
import { useAuth } from "../context/authContext";

export default function DepartmentPortal() {
  const navigate = useNavigate();
  const { user, signIn, signOut } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      const authenticatedUser = await signIn(email.trim(), password);
      setPassword("");
      if (authenticatedUser.role !== "department_staff") {
        await signOut();
        setError("This account is not authorized for department staff access.");
        return;
      }
      navigate("/dashboard/department", { replace: true });
    } catch (err) {
      setError(
        err.status === 401
          ? "Invalid email or password."
          : err.status === 403
            ? err.message || "This account is not authorized for department access."
            : err.message || "Unable to sign in. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleSignOut() {
    setError("");
    try {
      await signOut();
    } catch (err) {
      setError(err.message || "Could not safely end this session. Please retry.");
    }
  }

  return (
    <main className="page-container department-entry-page">
      <NavLink to="/" className="back-link">
        <ArrowLeft size={16} aria-hidden="true" />
        Return to MindBridge
      </NavLink>

      <section className="department-entry-card">
        <span className="section-overline">AUTHORIZED STAFF ACCESS</span>
        <h1>Department Portal</h1>
        <p>
          Department staff can sign in to view cases explicitly routed to their
          provisioned department. Access is limited to the minimum case
          information needed for routing.
        </p>

        {user?.role === "department_staff" ? (
          <div className="department-entry-actions">
            <p role="status">
              Signed in as authorized staff for {user.department}.
            </p>
            <Link to="/dashboard/department" className="button-primary">
              Open department dashboard <ArrowRight size={17} />
            </Link>
          </div>
        ) : user ? (
          <div className="department-entry-actions">
            <p role="alert" className="field-error">
              This account is not authorized for department staff access.
            </p>
            <button
              type="button"
              className="secondary-button"
              onClick={handleSignOut}
            >
              Sign out to use staff login
            </button>
          </div>
        ) : (
          <form className="department-entry-actions" onSubmit={handleSubmit}>
            <div className="field-group">
              <label htmlFor="department-email">Staff email address</label>
              <input
                id="department-email"
                type="email"
                autoComplete="username"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
              />
            </div>
            <div className="field-group">
              <label htmlFor="department-password">Password</label>
              <input
                id="department-password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
            </div>
            {error && (
              <p role="alert" className="field-error">
                {error}
              </p>
            )}
            <button
              type="submit"
              className="button-primary"
              disabled={loading}
            >
              {loading ? "Signing in..." : "Department Staff Login"}
              {!loading && <ArrowRight size={17} />}
            </button>
          </form>
        )}

        <div className="department-request-note">
          <LockKeyhole size={20} aria-hidden="true" />
          <div>
            <h2>Request department access</h2>
            <p>
              Department access is provisioned by an authorized MindBridge
              administrator after validating the staff member and department.
              Self-service registration is not available; a public form must
              not create department privileges.
            </p>
            <p>
              Contact your institution&apos;s authorized MindBridge
              administrator through its established access-request process.
              Once provisioned, sign in here with your staff account.
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}
