import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ArrowRight, ShieldCheck } from "lucide-react";
import { acceptCoordinatorInvitation } from "../services/caseService";

const passwordRequirements = [
  ["12 or more characters", (value) => value.length >= 12],
  ["An uppercase letter", (value) => /[A-Z]/.test(value)],
  ["A lowercase letter", (value) => /[a-z]/.test(value)],
  ["A number", (value) => /[0-9]/.test(value)],
  ["A special character", (value) => /[^A-Za-z0-9]/.test(value)],
];

export default function CoordinatorInvitation() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get("token") || "";
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState(
    token ? "" : "This invitation link is missing its security token.",
  );
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    if (!token) {
      setError("This invitation link is missing its security token.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Password and confirm password must match.");
      return;
    }
    if (!passwordRequirements.every(([, isSatisfied]) => isSatisfied(password))) {
      setError("Choose a password that meets all the requirements below.");
      return;
    }

    setLoading(true);
    try {
      await acceptCoordinatorInvitation({
        token,
        name: name.trim(),
        password,
        confirm_password: confirmPassword,
      });
      navigate("/login", {
        replace: true,
        state: {
          message: "Coordinator account activated. Sign in to view your assigned case.",
        },
      });
    } catch (requestError) {
      setError(
        requestError.message ||
          "Could not activate this coordinator invitation. Request a new invitation if it has expired.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="page-container department-entry-page">
      <section className="department-entry-card">
        <div className="department-entry-heading">
          <ShieldCheck aria-hidden="true" />
          <span className="section-overline">COORDINATOR ACCOUNT ACTIVATION</span>
        </div>
        <h1>Activate your account</h1>
        <p>
          Set your name and a secure password to accept this coordinator
          invitation. The link is single-use and expires.
        </p>

        <form className="department-entry-actions" onSubmit={handleSubmit}>
          <div className="field-group">
            <label htmlFor="coordinator-name">Full name</label>
            <input
              id="coordinator-name"
              autoComplete="name"
              minLength={2}
              maxLength={100}
              required
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </div>
          <div className="field-group">
            <label htmlFor="coordinator-password">Create password</label>
            <input
              id="coordinator-password"
              type="password"
              autoComplete="new-password"
              minLength={12}
              maxLength={128}
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
            <ul aria-label="Password requirements">
              {passwordRequirements.map(([label, isSatisfied]) => (
                <li key={label} aria-label={`${label}${isSatisfied(password) ? ", met" : ""}`}>
                  {label}
                </li>
              ))}
            </ul>
          </div>
          <div className="field-group">
            <label htmlFor="coordinator-confirm-password">Confirm password</label>
            <input
              id="coordinator-confirm-password"
              type="password"
              autoComplete="new-password"
              minLength={12}
              maxLength={128}
              required
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
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
            {loading ? "Activating account..." : "Activate coordinator account"}
            {!loading && <ArrowRight size={17} />}
          </button>
        </form>
        <p>
          Already activated? <Link to="/login">Sign in</Link>
        </p>
      </section>
    </main>
  );
}
