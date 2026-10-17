import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/authContext";
import { getCurrentUser } from "../services/authService";

const ROLE_LABELS = {
  student: "Student",
  coordinator: "Coordinator",
  admin: "Administrator",
  department_staff: "Department staff",
};

export default function Profile() {
  const { updateProfile } = useAuth();
  const [profile, setProfile] = useState(null);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    let cancelled = false;

    getCurrentUser()
      .then((user) => {
        if (cancelled) return;
        setProfile(user);
        setName(user.name);
        setPhone(user.phone || "");
      })
      .catch((loadError) => {
        if (!cancelled) {
          setError(loadError.message || "Could not load your profile.");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    setSaving(true);

    try {
      const updated = await updateProfile({
        name,
        ...(phone.trim() ? { phone: phone.trim() } : {}),
      });
      setProfile(updated);
      setName(updated.name);
      setPhone(updated.phone || "");
      setMessage("Your profile has been updated.");
    } catch (saveError) {
      setError(saveError.message || "Could not update your profile.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <main className="page-container profile-page">
        <p role="status" className="profile-status">Loading your profile...</p>
      </main>
    );
  }

  if (!profile) {
    return (
      <main className="page-container profile-page">
        <p role="alert" className="profile-status field-error">
          {error || "Your profile is unavailable."}
        </p>
      </main>
    );
  }

  return (
    <main className="page-container profile-page">
      <section className="profile-card">
        <header className="profile-header">
          <div>
            <span className="section-overline">ACCOUNT</span>
            <h1>Your profile</h1>
            <p>These details come from your authenticated MindBridge account.</p>
          </div>
          <Link
            to="/profile#edit-profile"
            className="subtle-link profile-edit-link"
          >
            Edit Profile
          </Link>
        </header>

        <dl className="profile-details">
          <div className="profile-detail">
            <dt>Name</dt>
            <dd>{profile.name}</dd>
          </div>
          <div className="profile-detail">
            <dt>Email</dt>
            <dd>{profile.email}</dd>
          </div>
          <div className="profile-detail">
            <dt>Phone</dt>
            <dd>{profile.phone || "Not provided"}</dd>
          </div>
          <div className="profile-detail">
            <dt>Role</dt>
            <dd>{ROLE_LABELS[profile.role] || profile.role}</dd>
          </div>
          {profile.department && (
            <div className="profile-detail">
              <dt>Department</dt>
              <dd>{profile.department}</dd>
            </div>
          )}
          <div className="profile-detail">
            <dt>Account created</dt>
            <dd>
              {profile.created_at
                ? new Date(profile.created_at).toLocaleDateString()
                : "Not available"}
            </dd>
          </div>
        </dl>

        <form id="edit-profile" className="profile-form" onSubmit={handleSubmit}>
          <div className="profile-form-heading">
            <h2>Edit profile</h2>
            <p>Update the contact details associated with your account.</p>
          </div>
          <div className="profile-form-grid">
            <div className="field-group">
              <label htmlFor="profile-name">Display name</label>
              <input
                id="profile-name"
                type="text"
                autoComplete="name"
                minLength={2}
                maxLength={100}
                required
                value={name}
                onChange={(event) => setName(event.target.value)}
              />
            </div>
            <div className="field-group">
              <label htmlFor="profile-phone">Phone number</label>
              <input
                id="profile-phone"
                type="tel"
                inputMode="tel"
                autoComplete="tel"
                placeholder="+91 98765 43210"
                value={phone}
                onChange={(event) => setPhone(event.target.value)}
                aria-describedby="profile-phone-hint"
              />
              <span id="profile-phone-hint" className="field-meta">
                Use a 10-digit Indian mobile number, optionally with +91.
                Leaving this blank keeps your current number unchanged.
              </span>
            </div>
          </div>
          {error && (
            <p role="alert" className="field-error profile-feedback">
              {error}
            </p>
          )}
          {message && (
            <p role="status" className="profile-feedback">
              {message}
            </p>
          )}
          <button
            type="submit"
            disabled={saving || name.trim().length < 2}
            className="button-primary profile-save-button"
          >
            {saving ? "Saving..." : "Save profile"}
          </button>
        </form>
      </section>
    </main>
  );
}
