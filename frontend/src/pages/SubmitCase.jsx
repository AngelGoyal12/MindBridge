
import { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
    ArrowLeft,
    ArrowRight,
    Check,
    ChevronDown,
    ShieldCheck,
    LockKeyhole,
    Eye,
    EyeOff,
    Info,
} from 'lucide-react';

import {
    getIdentityPreference,
    saveIdentityPreference,
} from "../services/privacyService";

import { createCase } from "../services/caseService";

const categories = [
    { value: 'academic_support', label: 'Academic support' },
    { value: 'hostel_issue', label: 'Hostel & accommodation' },
    { value: 'ragging_bullying', label: 'Bullying or ragging' },
    { value: 'emotional_support', label: 'Emotional support' },
    { value: 'financial_assistance', label: 'Financial assistance' },
    { value: 'other', label: 'Something else' },
];

const privacyOptions = [
    {
        value: 'identified',
        title: 'Identified case, consent-gated disclosure',
        description:
            'Your case is linked to your account. Coordinators still cannot see your identity unless you grant active, purpose-specific consent.',
        icon: Eye,
    },
    {
        value: 'restricted',
        title: 'Restricted, consent-gated disclosure',
        description:
            'Your case is linked to your account, but coordinator identity disclosure requires active consent matching the recipient, purpose, and scope.',
        icon: LockKeyhole,
    },
    {
        value: 'anonymous',
        title: 'Block coordinator identity disclosure',
        description:
            'Coordinator identity disclosure is blocked for this case. This does not remove your account link or guarantee anonymity; details you write may still identify you.',
        icon: EyeOff,
    },
];

export default function SubmitCase() {
    const navigate = useNavigate();

    const [form, setForm] = useState({
        title: '',
        category: '',
        description: '',
        incidentDate: '',
        incidentLocation: '',
        peopleInvolved: '',
        identityMode: getIdentityPreference(),
        consentConfirmed: false,
    });

    const [errors, setErrors] = useState({});
    const [submitted, setSubmitted] = useState(false);

    const selectedCategory = categories.find(
        (item) => item.value === form.category
    );

    const isSensitiveCategory = [
        'ragging_bullying',
        'emotional_support',
    ].includes(form.category);

    function updateField(event) {
        const { name, value, type, checked } = event.target;

        setForm((current) => ({
            ...current,
            [name]: type === 'checkbox' ? checked : value,
        }));

        setErrors((current) => ({
            ...current,
            [name]: '',
            form: '',
        }));
    }

    function validateForm() {
        const nextErrors = {};

        if (!form.title.trim()) {
            nextErrors.title = 'Please add a short title.';
        } else if (form.title.trim().length < 5) {
            nextErrors.title = 'Please use at least 5 characters.';
        }

        if (!form.category) {
            nextErrors.category = 'Please choose a category.';
        }

        if (!form.description.trim()) {
            nextErrors.description = 'Please describe your concern.';
        } else if (form.description.trim().length < 20) {
            nextErrors.description =
                'Please provide a little more detail (at least 20 characters).';
        }


        if (form.incidentDate) {
            const today = new Date();
            const todayString = [
                today.getFullYear(),
                String(today.getMonth() + 1).padStart(2, "0"),
                String(today.getDate()).padStart(2, "0"),
            ].join("-");

            if (
                !/^\d{4}-\d{2}-\d{2}$/.test(form.incidentDate) ||
                form.incidentDate > todayString ||
                Number.isNaN(Date.parse(form.incidentDate))
            ) {
                nextErrors.incidentDate =
                    "Please enter a valid date that is not in the future.";
            }
        }


        if (!form.consentConfirmed) {
            nextErrors.consentConfirmed =
                'Please confirm that you understand the privacy information.';
        }

        setErrors(nextErrors);
        return Object.keys(nextErrors).length === 0;
    }


async function handleSubmit(event) {
    event.preventDefault();

    if (!validateForm()) {
        return;
    }

    try {
        setErrors((current) => ({ ...current, form: '' }));

        await createCase({
            title: form.title.trim(),
            category: form.category,
            description: form.description.trim(),
            identity_mode: form.identityMode,
        });

        setSubmitted(true);
    } catch (error) {
        setErrors((current) => ({
            ...current,
            form: error.message || 'Could not submit your concern. Please try again.',
        }));
    }
}


    if (submitted) {
        return (
            <main className="submit-page page-container">
                <section className="submit-success">
                    <div className="success-icon">
                        <Check size={29} />
                    </div>
                    <span className="section-overline">SUBMISSION CONFIRMED</span>
                    <h1>Your concern is ready for its <em>next step.</em></h1>
                    <p>
                    Your concern has been submitted successfully. You can return
                    to your dashboard to continue.
                    </p>
                    <div className="success-summary">
                        <span>Concern title</span>
                        <strong>{form.title}</strong>
                        <span>Category</span>
                        <strong>{selectedCategory?.label}</strong>
                        <span>Identity preference</span>
                        <strong>
                            {privacyOptions.find(
                                (option) => option.value === form.identityMode
                            )?.title}
                        </strong>
                    </div>
                    <div className="success-actions">
                        <button
                            type="button"
                            className="button-primary"
                            onClick={() => navigate('/dashboard')}
                        >
                            Return to dashboard <ArrowRight size={17} />
                        </button>
                        <button
                            type="button"
                            className="secondary-button"
                            onClick={() => {
                                setSubmitted(false);
                                setForm({
                                    title: '',
                                    category: '',
                                    description: '',
                                    incidentDate: '',
                                    incidentLocation: '',
                                    peopleInvolved: '',
                                    identityMode: getIdentityPreference(),
                                    consentConfirmed: false,
                                });
                            }}
                        >
                            Start another draft
                        </button>
                    </div>
                </section>
            </main>
        );
    }

    function handleIdentityChange(value) {
        setForm((current) => ({
            ...current,
            identityMode: value,
        }));

        setErrors((current) => ({
            ...current,
            identityMode: '',
            form: '',
        }));

        try {
            saveIdentityPreference(value);
        } catch (error) {
            console.error('Could not save identity preference:', error);
        }
    }

    return (
        <main className="submit-page page-container">
            <NavLink to="/dashboard" className="back-link">
                <ArrowLeft size={15} /> Back to your space
            </NavLink>

            <section className="submit-heading">
                <div className="eyebrow">
                    <span className="eyebrow-dot" />
                    A PRIVATE SPACE TO BEGIN
                </div>
                <h1>You can start with <em>what you know.</em></h1>
                <p>
                    Share what you feel comfortable sharing. You don't need
                    perfect words, and you can review your choices before submitting.
                </p>
            </section>

            <div className="submit-layout">
                <form className="concern-form" onSubmit={handleSubmit} noValidate>
                    <section className="form-section">
                        <div className="form-section-heading">
                            <span className="form-step">01</span>
                            <div>
                                <h2>Tell us about your concern</h2>
                                <p>Start with the details that help us understand.</p>
                            </div>
                        </div>

                        <div className="field-group">
                            <label htmlFor="title">A short title <span>*</span></label>
                            <input
                                id="title"
                                name="title"
                                value={form.title}
                                onChange={updateField}
                                placeholder="e.g. Need help with a hostel concern"
                                maxLength={120}
                                aria-invalid={Boolean(errors.title)}
                                aria-describedby={errors.title ? 'title-error' : undefined}
                            />
                            {errors.title && (
                                <span className="field-error" id="title-error">
                                    {errors.title}
                                </span>
                            )}
                        </div>

                        <div className="field-group">
                            <label htmlFor="category">What is this about? <span>*</span></label>
                            <div className="select-wrap">
                                <select
                                    id="category"
                                    name="category"
                                    value={form.category}
                                    onChange={updateField}
                                    aria-invalid={Boolean(errors.category)}
                                    aria-describedby={
                                        errors.category ? 'category-error' : undefined
                                    }
                                >
                                    <option value="">Choose the closest category</option>
                                    {categories.map((category) => (
                                        <option key={category.value} value={category.value}>
                                            {category.label}
                                        </option>
                                    ))}
                                </select>
                                <ChevronDown size={17} aria-hidden="true" />
                            </div>
                            {errors.category && (
                                <span className="field-error" id="category-error">
                                    {errors.category}
                                </span>
                            )}
                        </div>

                        <div className="field-group">
                            <label htmlFor="description">
                                Tell us what happened <span>*</span>
                            </label>
                            <textarea
                                id="description"
                                name="description"
                                value={form.description}
                                onChange={updateField}
                                placeholder="Describe what's happening, how it's affecting you, or what kind of support you need..."
                                rows={6}
                                maxLength={5000}
                                aria-invalid={Boolean(errors.description)}
                                aria-describedby={
                                    errors.description
                                        ? 'description-error'
                                        : 'description-hint'
                                }
                            />
                            <div className="field-meta">
                                {errors.description ? (
                                    <span className="field-error" id="description-error">
                                        {errors.description}
                                    </span>
                                ) : (
                                    <span id="description-hint">
                                        Routine coordinator review does not include this text. Avoid details that could identify you if you do not want them recorded in your case.
                                    </span>
                                )}
                                <span>{form.description.length}/5000</span>
                            </div>
                        </div>
                    </section>

                    <section className="form-section">
                        <div className="form-section-heading">
                            <span className="form-step">02</span>
                            <div>
                                <h2>Additional details</h2>
                                <p>
                                    These fields are optional. Add them if they help explain
                                    your concern.
                                </p>
                            </div>
                        </div>

                        <div className="form-two-columns">
                            <div className="field-group">
                                <label htmlFor="incidentDate">When did it happen?</label>
                                <input
                                    id="incidentDate"
                                    name="incidentDate"
                                    type="date"
                                    value={form.incidentDate}
                                    onChange={updateField}
                                    max={new Date().toISOString().slice(0, 10)}
                                />
                                {errors.incidentDate && (
                                    <span className="field-error" role="alert">
                                        {errors.incidentDate}
                                    </span>
                                )}
                            </div>

                            <div className="field-group">
                                <label htmlFor="incidentLocation">Where did it happen?</label>
                                <input
                                    id="incidentLocation"
                                    name="incidentLocation"
                                    value={form.incidentLocation}
                                    onChange={updateField}
                                    placeholder="e.g. Hostel common area"
                                    maxLength={200}
                                />
                            </div>
                        </div>

                        {isSensitiveCategory && (
                            <div className="field-group">
                                <label htmlFor="peopleInvolved">
                                    People or other relevant details (optional)
                                </label>
                                <textarea
                                    id="peopleInvolved"
                                    name="peopleInvolved"
                                    value={form.peopleInvolved}
                                    onChange={updateField}
                                    placeholder="Add relevant details or witnesses if you feel comfortable. Avoid sharing unnecessary personal information."
                                    rows={3}
                                    maxLength={2000}
                                />
                            </div>
                        )}

                        <div className="optional-note">
                            <Info size={16} />
                            <p>
                                You can leave optional fields blank. Only include details
                                relevant to understanding and addressing your concern.
                            </p>
                        </div>
                    </section>

                    <section className="form-section privacy-form-section">
                        <div className="form-section-heading">
                            <span className="form-step">03</span>
                            <div>
                                <h2>Choose your identity preference</h2>
                                <p>
                                    Consider who may need to know your identity to respond.
                                </p>
                            </div>
                        </div>

                        <div className="privacy-options">
                            {privacyOptions.map((option) => {
                                const Icon = option.icon;
                                const selected = form.identityMode === option.value;

                                return (
                                    <label
                                        className={`privacy-option ${selected ? 'selected' : ''}`}
                                        key={option.value}
                                    >
                                        <input
                                            type="radio"
                                            name="identityMode"
                                            value={option.value}
                                            checked={selected}
                                            onChange={() => handleIdentityChange(option.value)}
                                        />
                                        <span className="privacy-option-icon">
                                            <Icon size={19} />
                                        </span>
                                        <span className="privacy-option-copy">
                                            <strong>{option.title}</strong>
                                            <span>{option.description}</span>
                                        </span>
                                        <span className="privacy-radio">
                                            {selected && <span />}
                                        </span>
                                    </label>
                                );
                            })}
                        </div>

                        <div className="privacy-disclaimer">
                            <ShieldCheck size={18} />
                            <p>
                                <strong>What this means:</strong> Your selection records
                                the identity mode for this case. Coordinators never see your
                                identity during routine review; identified and restricted
                                cases still require your active, purpose-specific consent for
                                disclosure. The block-disclosure mode prevents that endpoint
                                from revealing identity, but does not unlink your account or
                                guarantee anonymity. Avoid putting identifying details in text
                                if you do not want them recorded in the case.
                            </p>
                        </div>

                        <label className="consent-row">
                            <input
                                type="checkbox"
                                name="consentConfirmed"
                                checked={form.consentConfirmed}
                                onChange={updateField}
                                aria-invalid={Boolean(errors.consentConfirmed)}
                            />
                            <span>
                                I understand the identity-sharing option I selected and
                                how the information above may be used to review my concern.
                            </span>
                        </label>
                        {errors.consentConfirmed && (
                            <span className="field-error consent-error">
                                {errors.consentConfirmed}
                            </span>
                        )}
                    </section>

                    {errors.form && (
                        <p className="field-error" role="alert">{errors.form}</p>
                    )}

                    <div className="form-submit-row">
                        <span><span>*</span> Required fields</span>
                        <button type="submit" className="button-primary">
                            Review my concern <ArrowRight size={17} />
                        </button>
                    </div>
                </form>

                <aside className="form-sidebar">
                    <div className="form-sidebar-art">
                        <div className="sidebar-art-circle">✳</div>
                        <span>One thing at a time.</span>
                    </div>

                    <span className="section-overline">BEFORE YOU BEGIN</span>
                    <h2>There is no right way to feel.</h2>
                    <p>
                        Your experience matters. Share the information that helps
                        explain what you need; you don't have to write a perfect report.
                    </p>

                    <div className="sidebar-divider" />

                    <div className="sidebar-guideline">
                        <span>01</span>
                        <p>Be as clear as you can, in your own words.</p>
                    </div>
                    <div className="sidebar-guideline">
                        <span>02</span>
                        <p>Include dates or locations when relevant and known.</p>
                    </div>
                    <div className="sidebar-guideline">
                        <span>03</span>
                        <p>Choose the identity option that best matches your preference.</p>
                    </div>

                    <div className="sidebar-confidentiality">
                        <ShieldCheck size={17} />
                        <span>Your information is sent securely to the server.</span>
                    </div>
                </aside>
            </div>
        </main>
    );
}
