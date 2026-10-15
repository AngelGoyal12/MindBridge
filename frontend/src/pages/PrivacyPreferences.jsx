
import { useState } from "react";
import { Link } from "react-router-dom";
import {
    ArrowLeft,
    Check,
    Eye,
    EyeOff,
    LockKeyhole,
    ShieldCheck,
    UserRound,
    UsersRound,
} from "lucide-react";

import {
    getIdentityPreference,
    saveIdentityPreference,
} from "../services/privacyService";

const identityOptions = [
    {
        value: "identified",
        title: "Share my identity",
        description:
            "Your identity may be visible to authorized staff handling your case, according to their permissions.",
        icon: UserRound,
    },
    {
        value: "restricted",
        title: "Restrict identity sharing",
        description:
            "Limit identity visibility to specifically authorized staff where the workflow supports it.",
        icon: EyeOff,
    },
    {
        value: "anonymous",
        title: "Submit anonymously",
        description:
            "Request that your identity not be shared with case handlers. Some workflows may require contact details or may not support full anonymity.",
        icon: Eye,
    },
];

export default function PrivacyPreferences() {
    const [identityMode, setIdentityMode] = useState(
        () => getIdentityPreference()
    );
    const [saved, setSaved] = useState(false);
    const [saveError, setSaveError] = useState("");

    function handleSave() {
        try {
            saveIdentityPreference(identityMode);
            setSaveError("");
            setSaved(true);
        } catch (error) {
            setSaved(false);
            setSaveError(error.message);
        }
    }

    function handleModeChange(value) {
        setIdentityMode(value);
        setSaved(false);
    }

    return (
        <main className="page-container privacy-settings-page">
            <Link to="/dashboard" className="back-link">
                <ArrowLeft size={16} aria-hidden="true" />
                Back to dashboard
            </Link>

            <header className="privacy-settings-heading">
                <span className="eyebrow">YOUR CONTROL, YOUR CHOICE</span>
                <h1>Privacy & preferences</h1>
                <p>
                    Understand your options before sharing a concern. Your safety and
                    privacy should be considered throughout the support process.
                </p>
            </header>

            <section className="privacy-settings-card">
                <div className="privacy-settings-section-heading">
                    <div className="privacy-settings-icon">
                        <ShieldCheck size={22} aria-hidden="true" />
                    </div>
                    <div>
                        <h2>Identity-sharing preference</h2>
                        <p>
                            Choose your preferred identity-sharing setting for future
                            submissions in this demo.
                        </p>
                    </div>
                </div>

                <div className="privacy-settings-options">
                    {identityOptions.map((option) => {
                        const Icon = option.icon;
                        const selected = identityMode === option.value;

                        return (
                            <label
                                key={option.value}
                                className={`privacy-settings-option ${selected ? "selected" : ""
                                    }`}
                            >
                                <input
                                    type="radio"
                                    name="identityMode"
                                    value={option.value}
                                    checked={selected}
                                    onChange={() => handleModeChange(option.value)}
                                />

                                <span className="privacy-settings-option-icon">
                                    <Icon size={20} aria-hidden="true" />
                                </span>

                                <span className="privacy-settings-option-copy">
                                    <strong>{option.title}</strong>
                                    <span>{option.description}</span>
                                </span>

                                {selected && (
                                    <span className="privacy-settings-selected">
                                        <Check size={16} aria-hidden="true" />
                                    </span>
                                )}
                            </label>
                        );
                    })}
                </div>

                <div className="privacy-settings-notice">
                    <LockKeyhole size={19} aria-hidden="true" />
                    <p>
                        This preference is not a guarantee of anonymity. Actual access
                        controls, data retention, and identity disclosure must be enforced
                        by the backend and explained in the applicable privacy policy.
                    </p>
                </div>

                <div className="privacy-settings-footer">
                    <p>
                        <strong>Current selection:</strong>{" "}
                        {identityOptions.find(
                            (option) => option.value === identityMode
                        )?.title}
                    </p>

                    <button
                        type="button"
                        className="primary-button"
                        onClick={handleSave}
                    >
                        Save preference
                    </button>
                </div>

                {saved && (
                    <p className="privacy-settings-feedback" role="status">
                        <Check size={17} aria-hidden="true" />
                        Your preference has been saved in this browser and will be used as the default for future submissions.
                    </p>
                )}
                {saveError && (
                    <p className="privacy-settings-error" role="alert">
                        {saveError}
                    </p>
                )}
            </section>

            <section className="privacy-principles-grid">
                <article className="privacy-principle">
                    <div className="privacy-principle-icon">
                        <UsersRound size={21} aria-hidden="true" />
                    </div>
                    <h3>Need-to-know access</h3>
                    <p>
                        Only authorized roles should access the information required for
                        their responsibilities.
                    </p>
                </article>

                <article className="privacy-principle">
                    <div className="privacy-principle-icon">
                        <EyeOff size={21} aria-hidden="true" />
                    </div>
                    <h3>Respect your choice</h3>
                    <p>
                        Identity-sharing choices should be communicated clearly and
                        handled according to the approved workflow.
                    </p>
                </article>

                <article className="privacy-principle">
                    <div className="privacy-principle-icon">
                        <LockKeyhole size={21} aria-hidden="true" />
                    </div>
                    <h3>Secure handling</h3>
                    <p>
                        Authentication, access permissions, and safe data handling must
                        be implemented on the server.
                    </p>
                </article>
            </section>

            <p className="privacy-settings-demo-note">
                This is a frontend prototype. Your saved preference sets the default
                for future submissions in this browser. It does not change existing
                cases or enforce identity access controls on a server.
            </p>
        </main>
    );
}
