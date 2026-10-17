import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { ArrowRight, MailCheck } from "lucide-react";
import {
  resendStudentVerification,
  verifyStudentEmail,
} from "../services/authService";

export default function VerifyEmail() {
  const location = useLocation();
  const navigate = useNavigate();
  const [email, setEmail] = useState(location.state?.email || "");
  const [otp, setOtp] = useState("");
  const [cooldownRemaining, setCooldownRemaining] = useState(() => {
    const seconds = Number(location.state?.resendCooldownSeconds);
    return Number.isFinite(seconds) ? Math.max(0, seconds) : 0;
  });
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!cooldownRemaining) return undefined;
    const timeoutId = window.setTimeout(
      () => setCooldownRemaining((remaining) => Math.max(0, remaining - 1)),
      1000,
    );
    return () => window.clearTimeout(timeoutId);
  }, [cooldownRemaining]);

  async function submit(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    setLoading(true);
    try {
      await verifyStudentEmail(email.trim(), otp);
      navigate("/login", {
        replace: true,
        state: { message: "Email verified. You can now sign in." },
      });
    } catch (verifyError) {
      setError(verifyError.message || "Could not verify this code.");
    } finally {
      setLoading(false);
    }
  }

  async function resend() {
    setError("");
    setMessage("");
    setResending(true);
    try {
      const result = await resendStudentVerification(email.trim());
      setMessage(result.message);
      const cooldown = Number(result.resend_cooldown_seconds);
      setCooldownRemaining(
        Number.isFinite(cooldown) && cooldown > 0 ? cooldown : 60,
      );
      setOtp("");
    } catch (resendError) {
      setError(resendError.message || "Could not request another code.");
    } finally {
      setResending(false);
    }
  }

  return (
    <main className="page-container" style={{ paddingBlock: "56px" }}>
      <section
        style={{
          maxWidth: "480px",
          margin: "0 auto",
          padding: "32px",
          background: "#fff",
          border: "1px solid #e5e7eb",
          borderRadius: "16px",
        }}
      >
        <MailCheck size={26} aria-hidden="true" />
        <h1 style={{ marginTop: "18px" }}>Verify your college email</h1>
        <p>
          Enter the six-digit code sent to your official college email. If a
          code has expired, you can request another one below.
        </p>
        <form onSubmit={submit}>
          <div className="field-group" style={{ marginTop: "20px" }}>
            <label htmlFor="verification-email">College email</label>
            <input
              id="verification-email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </div>
          <div className="field-group" style={{ marginTop: "16px" }}>
            <label htmlFor="verification-otp">Verification code</label>
            <input
              id="verification-otp"
              inputMode="numeric"
              autoComplete="one-time-code"
              pattern="[0-9]{6}"
              minLength={6}
              maxLength={6}
              required
              value={otp}
              onChange={(event) =>
                setOtp(event.target.value.replace(/\D/g, "").slice(0, 6))
              }
            />
          </div>
          {error && <p role="alert" className="field-error">{error}</p>}
          {message && <p role="status">{message}</p>}
          <button
            type="submit"
            className="button-primary"
            disabled={loading || otp.length !== 6}
            style={{ marginTop: "20px", width: "100%" }}
          >
            {loading ? "Verifying..." : "Verify email"}
            {!loading && <ArrowRight size={17} />}
          </button>
        </form>
        <button
          type="button"
          className="secondary-button"
          disabled={resending || !email.trim() || cooldownRemaining > 0}
          onClick={resend}
          style={{ marginTop: "16px" }}
        >
          {resending
            ? "Requesting..."
            : cooldownRemaining > 0
              ? `Resend available in ${cooldownRemaining}s`
              : "Resend code"}
        </button>
        <p className="field-meta" style={{ marginTop: "10px" }}>
          Resend requests may be delayed by a cooldown or limited for security.
        </p>
        <p style={{ marginTop: "18px" }}>
          <Link to="/login">Return to sign in</Link>
        </p>
      </section>
    </main>
  );
}
