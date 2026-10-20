import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ArrowRight,
  Eye,
  EyeOff,
  ShieldCheck,
  UserPlus,
} from "lucide-react";
import { registerStudent } from "../services/authService";

function isValidCollegeEmail(value) {
  const parts = value.trim().split("@");
  if (parts.length !== 2) return false;
  const [localPart, domain] = parts;
  const validDomainLabel = /^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$/i;
  return (
    localPart.length <= 64 &&
    /^[a-z0-9.!#$%&'*+/=?^_`{|}~-]+$/i.test(localPart) &&
    !localPart.startsWith(".") &&
    !localPart.endsWith(".") &&
    !localPart.includes("..") &&
    domain.length <= 253 &&
    domain.toLowerCase().endsWith(".edu.in") &&
    domain
      .split(".")
      .every(
        (label) => label.length <= 63 && validDomainLabel.test(label),
      )
  );
}

function getFieldErrors(form) {
  const errors = {};

  if (form.name.trim().length < 2) {
    errors.name = "Enter your full name (at least 2 characters).";
  }
  if (!isValidCollegeEmail(form.email)) {
    errors.email = "Use a valid college email address ending in .edu.in.";
  }

  const compactPhone = form.phone.replace(/[\s()-]/g, "");
  const nationalNumber = compactPhone.startsWith("+91")
    ? compactPhone.slice(3)
    : compactPhone.startsWith("91") && compactPhone.length === 12
      ? compactPhone.slice(2)
      : compactPhone;
  if (!/^[6-9]\d{9}$/.test(nationalNumber)) {
    errors.phone =
      "Enter a valid 10-digit Indian mobile number, optionally with +91.";
  }

  if (!form.departmentCourse.trim()) {
    errors.departmentCourse = "Enter your Department/Course.";
  } else if (form.departmentCourse.trim().length > 100) {
    errors.departmentCourse = "Use no more than 100 characters.";
  }
  if (!form.currentSemester) {
    errors.currentSemester = "Choose your current semester.";
  } else if (!/^[1-8]$/.test(form.currentSemester)) {
    errors.currentSemester = "Choose a semester from 1 to 8.";
  }

  const missingRequirements = [];
  if (form.password.length < 12) missingRequirements.push("12 characters");
  if (!/[A-Z]/.test(form.password)) {
    missingRequirements.push("an uppercase letter");
  }
  if (!/[a-z]/.test(form.password)) {
    missingRequirements.push("a lowercase letter");
  }
  if (!/[0-9]/.test(form.password)) missingRequirements.push("a digit");
  if (!/[^A-Za-z0-9]/.test(form.password)) {
    missingRequirements.push("a special character");
  }
  if (missingRequirements.length) {
    errors.password = `Add ${missingRequirements.join(", ")}.`;
  }
  if (form.confirmPassword !== form.password) {
    errors.confirmPassword = "Passwords do not match.";
  }

  return errors;
}

export default function Register() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    name: "",
    email: "",
    phone: "",
    departmentCourse: "",
    currentSemester: "",
    password: "",
    confirmPassword: "",
  });
  const [touched, setTouched] = useState({});
  const [submitted, setSubmitted] = useState(false);
  const [showPasswords, setShowPasswords] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const fieldErrors = getFieldErrors(form);

  function handleChange(event) {
    setForm((current) => ({
      ...current,
      [event.target.name]: event.target.value,
    }));
    setError("");
  }

  function visibleError(field) {
    return touched[field] || submitted ? fieldErrors[field] : "";
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSubmitted(true);
    if (Object.keys(fieldErrors).length) return;

    setLoading(true);
    try {
      const result = await registerStudent({
        name: form.name.trim(),
        email: form.email.trim(),
        phone: form.phone.trim(),
        departmentCourse: form.departmentCourse.trim(),
        currentSemester: Number(form.currentSemester),
        password: form.password,
        confirmPassword: form.confirmPassword,
      });

      navigate("/verify-email", {
        replace: true,
        state: {
          email: form.email.trim(),
          resendCooldownSeconds: result.resend_cooldown_seconds,
        },
      });
    } catch (registrationError) {
      setError(registrationError.message || "Unable to create account.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main
      className="page-container"
      style={{ paddingTop: "48px", paddingBottom: "64px" }}
    >
      <section
        style={{
          maxWidth: "520px",
          margin: "0 auto",
          padding: "32px",
          background: "#fff",
          border: "1px solid #e5e7eb",
          borderRadius: "16px",
          boxShadow: "0 12px 35px rgba(47,79,79,0.08)",
        }}
      >
        <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
          <UserPlus size={25} />
          <span className="section-overline">MINDBRIDGE STUDENT SPACE</span>
        </div>

        <h1 style={{ marginTop: "20px" }}>
          Create <em>Account</em>
        </h1>
        <p>Verify your official college email before signing in.</p>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            marginTop: "18px",
            fontSize: "14px",
            color: "#52645c",
          }}
        >
          <ShieldCheck size={18} />
          <span>New accounts remain inactive until email verification.</span>
        </div>

        <form onSubmit={handleSubmit} noValidate>
          <div className="field-group" style={{ marginTop: "22px" }}>
            <label htmlFor="register-name">Full name</label>
            <input
              id="register-name"
              name="name"
              type="text"
              autoComplete="name"
              placeholder="Enter your full name"
              minLength={2}
              maxLength={100}
              value={form.name}
              onChange={handleChange}
              onBlur={() => setTouched((current) => ({ ...current, name: true }))}
              required
              aria-invalid={Boolean(visibleError("name"))}
              aria-describedby={
                visibleError("name") ? "register-name-error" : undefined
              }
            />
            {visibleError("name") && (
              <span id="register-name-error" className="field-error">
                {visibleError("name")}
              </span>
            )}
          </div>

          <div className="field-group">
            <label htmlFor="register-department-course">
              Department/Course
            </label>
            <input
              id="register-department-course"
              name="departmentCourse"
              type="text"
              autoComplete="organization-title"
              placeholder="Enter your department or course"
              maxLength={100}
              value={form.departmentCourse}
              onChange={handleChange}
              onBlur={() =>
                setTouched((current) => ({
                  ...current,
                  departmentCourse: true,
                }))
              }
              required
              aria-invalid={Boolean(visibleError("departmentCourse"))}
              aria-describedby={
                visibleError("departmentCourse")
                  ? "register-department-course-error"
                  : undefined
              }
            />
            {visibleError("departmentCourse") && (
              <span
                id="register-department-course-error"
                className="field-error"
              >
                {visibleError("departmentCourse")}
              </span>
            )}
          </div>

          <div className="field-group">
            <label htmlFor="register-current-semester">Current Semester</label>
            <select
              id="register-current-semester"
              name="currentSemester"
              value={form.currentSemester}
              onChange={handleChange}
              onBlur={() =>
                setTouched((current) => ({
                  ...current,
                  currentSemester: true,
                }))
              }
              required
              aria-invalid={Boolean(visibleError("currentSemester"))}
              aria-describedby={
                visibleError("currentSemester")
                  ? "register-current-semester-error"
                  : undefined
              }
            >
              <option value="">Select your current semester</option>
              {Array.from({ length: 8 }, (_, index) => index + 1).map(
                (semester) => (
                  <option key={semester} value={semester}>
                    Semester {semester}
                  </option>
                ),
              )}
            </select>
            {visibleError("currentSemester") && (
              <span
                id="register-current-semester-error"
                className="field-error"
              >
                {visibleError("currentSemester")}
              </span>
            )}
          </div>

          <div className="field-group">
            <label htmlFor="register-email">College email address</label>
            <input
              id="register-email"
              name="email"
              type="email"
              autoComplete="email"
              placeholder="you@yourcollege.edu.in"
              value={form.email}
              onChange={handleChange}
              onBlur={() =>
                setTouched((current) => ({ ...current, email: true }))
              }
              required
              aria-invalid={Boolean(visibleError("email"))}
              aria-describedby={
                visibleError("email") ? "register-email-error" : undefined
              }
            />
            {visibleError("email") && (
              <span id="register-email-error" className="field-error">
                {visibleError("email")}
              </span>
            )}
          </div>

          <div className="field-group">
            <label htmlFor="register-phone">Phone number</label>
            <input
              id="register-phone"
              name="phone"
              type="tel"
              inputMode="tel"
              autoComplete="tel"
              placeholder="+91 98765 43210"
              value={form.phone}
              onChange={handleChange}
              onBlur={() =>
                setTouched((current) => ({ ...current, phone: true }))
              }
              required
              aria-invalid={Boolean(visibleError("phone"))}
              aria-describedby={
                visibleError("phone") ? "register-phone-error" : undefined
              }
            />
            {visibleError("phone") && (
              <span id="register-phone-error" className="field-error">
                {visibleError("phone")}
              </span>
            )}
          </div>

          <div className="field-group">
            <label htmlFor="register-password">Password</label>
            <div className="auth-password-input">
              <input
                id="register-password"
                name="password"
                type={showPasswords ? "text" : "password"}
                autoComplete="new-password"
                minLength={12}
                maxLength={128}
                placeholder="Create a strong password"
                value={form.password}
                onChange={handleChange}
                onBlur={() =>
                  setTouched((current) => ({ ...current, password: true }))
                }
                required
                aria-invalid={Boolean(visibleError("password"))}
                aria-describedby={
                  visibleError("password")
                    ? "register-password-requirements register-password-error"
                    : "register-password-requirements"
                }
              />
              <button
                type="button"
                className="auth-password-toggle"
                aria-label={showPasswords ? "Hide passwords" : "Show passwords"}
                onClick={() => setShowPasswords((shown) => !shown)}
              >
                {showPasswords ? <EyeOff size={17} /> : <Eye size={17} />}
              </button>
            </div>
            <ul
              id="register-password-requirements"
              className="password-requirements"
              aria-label="Password requirements"
            >
              <li className={form.password.length >= 12 ? "is-met" : ""}>
                At least 12 characters
              </li>
              <li className={/[A-Z]/.test(form.password) ? "is-met" : ""}>
                One uppercase letter
              </li>
              <li className={/[a-z]/.test(form.password) ? "is-met" : ""}>
                One lowercase letter
              </li>
              <li className={/[0-9]/.test(form.password) ? "is-met" : ""}>
                One number
              </li>
              <li className={/[^A-Za-z0-9]/.test(form.password) ? "is-met" : ""}>
                One special character
              </li>
            </ul>
            {visibleError("password") && (
              <span id="register-password-error" className="field-error">
                {visibleError("password")}
              </span>
            )}
          </div>

          <div className="field-group">
            <label htmlFor="register-confirm-password">Confirm password</label>
            <div className="auth-password-input">
              <input
                id="register-confirm-password"
                name="confirmPassword"
                type={showPasswords ? "text" : "password"}
                autoComplete="new-password"
                maxLength={128}
                placeholder="Re-enter your password"
                value={form.confirmPassword}
                onChange={handleChange}
                onBlur={() =>
                  setTouched((current) => ({
                    ...current,
                    confirmPassword: true,
                  }))
                }
                required
                aria-invalid={Boolean(visibleError("confirmPassword"))}
                aria-describedby={
                  visibleError("confirmPassword")
                    ? "register-confirm-password-error"
                    : undefined
                }
              />
              <button
                type="button"
                className="auth-password-toggle"
                aria-label={showPasswords ? "Hide passwords" : "Show passwords"}
                onClick={() => setShowPasswords((shown) => !shown)}
              >
                {showPasswords ? <EyeOff size={17} /> : <Eye size={17} />}
              </button>
            </div>
            {visibleError("confirmPassword") && (
              <span
                id="register-confirm-password-error"
                className="field-error"
              >
                {visibleError("confirmPassword")}
              </span>
            )}
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
            {loading ? "Creating account..." : "Create Account"}
            {!loading && <ArrowRight size={17} />}
          </button>
        </form>

        <p style={{ marginTop: "22px", fontSize: "14px" }}>
          Already have an account?{" "}
          <Link
            to="/login"
            style={{
              color: "#2f4f4f",
              fontWeight: "600",
              textDecoration: "underline",
            }}
          >
            Sign in
          </Link>
        </p>
      </section>
    </main>
  );
}
