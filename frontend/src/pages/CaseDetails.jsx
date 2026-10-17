import { useEffect, useState } from 'react';
import { Link, NavLink, useLocation, useParams } from 'react-router-dom';
import {
  ArrowLeft,
  ArrowUpRight,
  CalendarDays,
  Check,
  Clock3,
  FileText,
  LockKeyhole,
  ShieldCheck,
  CircleHelp,
  CircleCheck,
} from 'lucide-react';

import {
  getCaseById,
  getCaseConsents,
  getCaseDisclosureAudit,
  grantCaseConsent,
  updateCaseIdentity,
  withdrawCaseConsent,
} from "../services/caseService";

// Temporary demo data. Later, Person 2's API will provide case records.
// const demoCases = [
//   {
//     id: 'MB-1024',
//     title: 'Hostel maintenance concern',
//     category: 'Hostel & accommodation',
//     categoryValue: 'hostel_issue',
//     date: '2026-10-12',
//     status: 'In progress',
//     statusValue: 'in_progress',
//     description:
//       'A maintenance concern submitted for review by the relevant support team.',
//     identityMode: 'restricted',
//     updates: [
//       {
//         date: '12 Oct 2026',
//         title: 'Concern submitted',
//         description: 'Your concern was recorded in the demo.',
//         type: 'complete',
//       },
//       {
//         date: '13 Oct 2026',
//         title: 'Review started',
//         description: 'The relevant team has started reviewing the concern.',
//         type: 'complete',
//       },
//       {
//         date: '14 Oct 2026',
//         title: 'Follow-up in progress',
//         description: 'The concern is being handled by the relevant team.',
//         type: 'current',
//       },
//     ],
//   },
//   {
//     id: 'MB-1018',
//     title: 'Academic guidance request',
//     category: 'Academic support',
//     categoryValue: 'academic_support',
//     date: '2026-10-08',
//     status: 'Under review',
//     statusValue: 'under_review',
//     description:
//       'A request for academic guidance and help identifying next steps.',
//     identityMode: 'identified',
//     updates: [
//       {
//         date: '08 Oct 2026',
//         title: 'Concern submitted',
//         description: 'Your concern was recorded in the demo.',
//         type: 'complete',
//       },
//       {
//         date: '10 Oct 2026',
//         title: 'Under review',
//         description: 'A coordinator is reviewing the request.',
//         type: 'current',
//       },
//     ],
//   },
//   {
//     id: 'MB-1009',
//     title: 'Fee assistance enquiry',
//     category: 'Financial assistance',
//     categoryValue: 'financial_assistance',
//     date: '2026-10-02',
//     status: 'Resolved',
//     statusValue: 'resolved',
//     description:
//       'An enquiry about available financial assistance options.',
//     identityMode: 'restricted',
//     updates: [
//       {
//         date: '02 Oct 2026',
//         title: 'Concern submitted',
//         description: 'Your concern was recorded in the demo.',
//         type: 'complete',
//       },
//       {
//         date: '03 Oct 2026',
//         title: 'Request reviewed',
//         description: 'The request was reviewed in this demo.',
//         type: 'complete',
//       },
//       {
//         date: '04 Oct 2026',
//         title: 'Marked as resolved',
//         description: 'The demo case was marked as resolved.',
//         type: 'complete',
//       },
//     ],
//   },
//   {
//     id: 'MB-1003',
//     title: 'Request for student support',
//     category: 'Other support',
//     categoryValue: 'other',
//     date: '2026-09-27',
//     status: 'Awaiting review',
//     statusValue: 'awaiting_review',
//     description:
//       'A general support request awaiting an initial review.',
//     identityMode: 'anonymous',
//     updates: [
//       {
//         date: '27 Sep 2026',
//         title: 'Concern submitted',
//         description: 'Your concern was recorded in the demo.',
//         type: 'complete',
//       },
//       {
//         date: 'Awaiting update',
//         title: 'Waiting for initial review',
//         description: 'No review update has been recorded in this demo yet.',
//         type: 'current',
//       },
//     ],
//   },
// ];

function formatStoredCase(item) {

  const categoryLabels = {
    ragging_bullying: 'Ragging & bullying',
    emotional_support: 'Emotional support',
    academic_support: 'Academic support',
    academic: 'Academic',
    hostel_issue: 'Hostel & accommodation',
    financial_assistance: 'Financial assistance',
    other: 'Other support',
  };

  const statusLabels = {
    submitted: 'Submitted',
    in_review: 'Under review',
    in_progress: 'In progress',
    resolved: 'Resolved',
    closed: 'Closed',
  };

  const createdAt = item.created_at ?? item.createdAt;

  const date = createdAt
    ? createdAt.slice(0, 10)
    : item.date ?? '';

  return {
    ...item,
    identityMode: item.identity_mode ?? item.identityMode ?? 'restricted',
    category:
      categoryLabels[item.category] ??
      item.categoryLabel ??
      item.category ??
      'Other support',

  categoryValue: item.categoryValue ?? item.category,
  statusValue: item.statusValue ?? item.status ?? 'submitted',
  status:
    statusLabels[item.status] ??
    item.statusLabel ??
    item.status ??
    'Submitted',
  date,

    updates: item.updates ?? [
  {
    date: date || 'Date unavailable',
    title: 'Concern submitted',
    description: 'Your concern has been saved.',
    type: 'complete',
  },
],
  };
}

const privacyDetails = {
  identified: {
    title: 'Identified case; disclosure still requires consent',
    description:
      'Your case is linked to your account. Coordinators do not see your identity in routine review; exact, active consent is still required.',
    icon: ShieldCheck,
  },
  restricted: {
    title: 'Restricted identity sharing',
    description:
      'Your case is linked to your account. Coordinators do not see your identity in routine review; disclosure requires exact, active consent.',
    icon: LockKeyhole,
  },
  anonymous: {
    title: 'Coordinator identity disclosure blocked',
    description:
      'Identity disclosure is blocked for this case. The case remains linked to your account, and details you submitted may still identify you.',
    icon: ShieldCheck,
  },
};

function formatDate(date) {
  if (!date) return 'Not available';

  return new Date(`${date}T00:00:00`).toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });
}

function StatusBadge({ status, statusValue }) {
  return (
    <span className={`status-badge case-status-${statusValue}`}>
      <span className="status-dot" />
      {status}
    </span>
  );
}


export default function CaseDetails() {
  const { caseId } = useParams();
  const location = useLocation();

  const [caseItem, setCaseItem] = useState(
    location.state?.caseData
      ? formatStoredCase(location.state.caseData)
      : null
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [consents, setConsents] = useState([]);
  const [disclosureAudit, setDisclosureAudit] = useState([]);
  const [consentLoading, setConsentLoading] = useState(true);
  const [consentError, setConsentError] = useState('');
  const [consentMessage, setConsentMessage] = useState('');
  const [consentForm, setConsentForm] = useState({
    recipient: '',
    purpose: '',
    scope: '',
  });
  const [identitySaving, setIdentitySaving] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadCase() {
      try {
        setLoading(true);
        setError('');

        const data = await getCaseById(caseId);

        if (!cancelled) {
          setCaseItem(formatStoredCase(data));
        }
        const [consentResult, auditResult] = await Promise.allSettled([
          getCaseConsents(caseId),
          getCaseDisclosureAudit(caseId),
        ]);
        if (!cancelled) {
          setConsentError('');
          if (consentResult.status === 'fulfilled') {
            setConsents(consentResult.value);
          } else {
            setConsentError(
              consentResult.reason?.message || 'Could not load consent history.',
            );
          }
          if (auditResult.status === 'fulfilled') {
            setDisclosureAudit(auditResult.value);
          } else {
            setConsentError((current) =>
              current || auditResult.reason?.message ||
                'Could not load disclosure audit history.',
            );
          }
        }
      } catch (err) {
        if (!cancelled) {
          setCaseItem(null);
          setError(err.message || 'Could not load this case.');
        }
      } finally {
        if (!cancelled) setConsentLoading(false);
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadCase();

    return () => {
      cancelled = true;
    };
  }, [caseId]);

  async function handleIdentityChange(event) {
    const identityMode = event.target.value;
    setIdentitySaving(true);
    setConsentError('');
    try {
      const response = await updateCaseIdentity(caseId, identityMode);
      setCaseItem((current) => ({
        ...current,
        identityMode: response.case.identity_mode,
      }));
    } catch (err) {
      setConsentError(err.message || 'Could not update the identity preference.');
    } finally {
      setIdentitySaving(false);
    }
  }

  async function handleGrantConsent(event) {
    event.preventDefault();
    setConsentError('');
    setConsentMessage('');
    try {
      await grantCaseConsent(caseId, {
        ...consentForm,
        recipient: consentForm.recipient.trim(),
        purpose: consentForm.purpose.trim(),
        scope: consentForm.scope.trim(),
      });
      setConsentForm({ recipient: '', purpose: '', scope: '' });
      setConsents(await getCaseConsents(caseId));
      setDisclosureAudit(await getCaseDisclosureAudit(caseId));
      setConsentMessage('Your consent has been recorded.');
    } catch (err) {
      setConsentError(err.message || 'Could not record consent.');
    }
  }

  async function handleWithdrawConsent(consentId) {
    setConsentError('');
    setConsentMessage('');
    try {
      await withdrawCaseConsent(caseId, consentId);
      setConsents(await getCaseConsents(caseId));
      setDisclosureAudit(await getCaseDisclosureAudit(caseId));
      setConsentMessage('Consent has been withdrawn.');
    } catch (err) {
      setConsentError(err.message || 'Could not withdraw consent.');
    }
  }

  if (loading) {
  return (
    <main className="case-details-page page-container">
      <p role="status">Loading case details...</p>
    </main>
  );
}


  if (!caseItem) {
    return (
      <main className="case-details-page page-container">
        <NavLink to="/cases" className="back-link">
          <ArrowLeft size={15} />
          Back to my cases
        </NavLink>

        <section className="case-not-found">
          <div className="case-not-found-icon">
            <CircleHelp size={25} />
          </div>
          <span className="section-overline">CASE NOT FOUND</span>
          <h1>We couldn't find that <em>case.</em></h1>
          <p>
  {error || "This case could not be found or may not be available."}
</p>
          <Link to="/cases" className="button-primary">
            Return to My Cases <ArrowUpRight size={16} />
          </Link>
        </section>
      </main>
    );
  }

  const privacy =
    privacyDetails[caseItem.identityMode] ?? privacyDetails.restricted;
  const PrivacyIcon = privacy.icon;

  const steps = [
    {
      title: 'Concern submitted',
      description: 'Your concern has been recorded.',
      completed: true,
    },
    {
      title: 'Initial review',
      description: 'A coordinator checks the information and next steps.',
      completed: [
  'in_review',
  'under_review',
  'in_progress',
  'resolved',
  'closed',
].includes(caseItem.statusValue),
    },
    {
      title: 'Action and follow-up',
      description: 'The relevant team handles the agreed next steps.',
      completed: ['in_progress', 'resolved'].includes(caseItem.statusValue),
    },
    {
      title: 'Resolution',
      description: 'The case is marked resolved after follow-up.',
      completed: ['resolved', 'closed'].includes(caseItem.statusValue),
    },
  ];

  const currentStep = steps.findIndex((step) => !step.completed);

  return (
    <main className="case-details-page page-container">
      <NavLink to="/cases" className="back-link">
        <ArrowLeft size={15} />
        Back to my cases
      </NavLink>

      <section className="case-detail-heading">
        <div className="eyebrow">
          <span className="eyebrow-dot" />
          YOUR SUPPORT JOURNEY
        </div>

        <div className="case-detail-title-row">
          <div>
            <div className="case-reference">
              <FileText size={15} />
              <span>{caseItem.id}</span>
            </div>
            <h1>{caseItem.title}</h1>
            <p>{caseItem.category}</p>
          </div>

          <StatusBadge
            status={caseItem.status}
            statusValue={caseItem.statusValue}
          />
        </div>

        <div className="case-detail-meta">
          <span>
            <CalendarDays size={15} />
            Submitted {formatDate(caseItem.date)}
          </span>
          <span className="case-detail-meta-divider" />
          <span>
            <Clock3 size={15} />
            Status: {caseItem.status}
          </span>
        </div>
      </section>

      <div className="case-detail-layout">
        <div className="case-detail-main">
          <section className="detail-panel">
            <div className="detail-panel-heading">
              <div>
                <span className="section-overline">PROGRESS</span>
                <h2>Where things stand</h2>
              </div>
              <span className="timeline-count">
                {caseItem.updates?.length ?? 0} updates
              </span>
            </div>

            <div className="case-progress-track">
              {steps.map((step, index) => (
                <div
                  className={`progress-step ${step.completed ? 'completed' : ''
                    } ${!step.completed &&
                      index === currentStep
                      ? 'current'
                      : ''
                    }`}
                  key={step.title}
                >
                  <div className="progress-step-marker">
                    {step.completed ? (
                      <Check size={14} />
                    ) : (
                      <span>{String(index + 1).padStart(2, '0')}</span>
                    )}
                  </div>
                  <div className="progress-step-copy">
                    <strong>{step.title}</strong>
                    <span>{step.description}</span>
                  </div>
                </div>
              ))}
            </div>

            <p className="demo-disclaimer">
  <CircleHelp size={15} />
  The current case status comes from the backend. Historical
  status changes are not available yet.
</p>
          </section>

          <section className="detail-panel">
            <div className="detail-panel-heading">
              <div>
                <span className="section-overline">IDENTITY & CONSENT</span>
                <h2>Manage identity access</h2>
              </div>
            </div>
            <p>
              Identity is not shared with coordinators by default. A coordinator
              can receive it only for the exact purpose and scope you authorize.
              The block-disclosure mode prevents identity disclosure but does not
              unlink your account or guarantee anonymity.
            </p>
            <div className="field-group" style={{ marginTop: '18px' }}>
              <label htmlFor="case-identity-mode">Identity preference</label>
              <select
                id="case-identity-mode"
                value={caseItem.identityMode}
                onChange={handleIdentityChange}
                disabled={identitySaving}
              >
                <option value="identified">Identified</option>
                <option value="restricted">Restricted</option>
                <option value="anonymous">Block coordinator identity disclosure</option>
              </select>
            </div>

            <form onSubmit={handleGrantConsent} style={{ marginTop: '24px' }}>
              <h3>Grant purpose-specific consent</h3>
              <p>
                The recipient must be the coordinator currently assigned to
                this case. Enter their account email.
              </p>
              <div className="field-group" style={{ marginTop: '16px' }}>
                <label htmlFor="consent-recipient">Coordinator email</label>
                <input
                  id="consent-recipient"
                  type="email"
                  required
                  value={consentForm.recipient}
                  onChange={(event) => setConsentForm((current) => ({
                    ...current,
                    recipient: event.target.value,
                  }))}
                />
              </div>
              <div className="field-group" style={{ marginTop: '16px' }}>
                <label htmlFor="consent-purpose">Purpose</label>
                <input
                  id="consent-purpose"
                  required
                  minLength={2}
                  maxLength={255}
                  value={consentForm.purpose}
                  onChange={(event) => setConsentForm((current) => ({
                    ...current,
                    purpose: event.target.value,
                  }))}
                />
              </div>
              <div className="field-group" style={{ marginTop: '16px' }}>
                <label htmlFor="consent-scope">Scope</label>
                <textarea
                  id="consent-scope"
                  required
                  minLength={2}
                  maxLength={2000}
                  value={consentForm.scope}
                  onChange={(event) => setConsentForm((current) => ({
                    ...current,
                    scope: event.target.value,
                  }))}
                />
              </div>
              <button
                type="submit"
                className="button-primary"
                style={{ marginTop: '16px' }}
                disabled={caseItem.identityMode === 'anonymous'}
              >
                Grant consent
              </button>
              {caseItem.identityMode === 'anonymous' && (
                <p>Change the identity mode before granting identity disclosure consent.</p>
              )}
            </form>

            {consentError && <p role="alert" className="field-error">{consentError}</p>}
            {consentMessage && <p role="status">{consentMessage}</p>}

            <h3 style={{ marginTop: '28px' }}>Consent history</h3>
            {consentLoading ? (
              <p role="status">Loading consent history...</p>
            ) : consents.length === 0 ? (
              <p>No consent grants have been recorded for this case.</p>
            ) : (
              <ul>
                {consents.map((consent) => (
                  <li key={consent.id} style={{ marginBlock: '12px' }}>
                    <strong>{consent.purpose}</strong>
                    <div>{consent.recipient} — {consent.scope}</div>
                    <div>
                      {consent.granted && !consent.withdrawn_at
                        ? caseItem.identityMode === 'anonymous'
                          ? 'Grant active; disclosure blocked by current identity mode'
                          : 'Active'
                        : 'Withdrawn'}
                    </div>
                    {consent.granted && !consent.withdrawn_at && (
                      <button
                        type="button"
                        className="secondary-button"
                        onClick={() => handleWithdrawConsent(consent.id)}
                      >
                        Withdraw
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            )}

            <h3 style={{ marginTop: '28px' }}>Identity disclosure audit</h3>
            {disclosureAudit.length === 0 ? (
              <p>No identity disclosure actions have been recorded.</p>
            ) : (
              <ul>
                {disclosureAudit.map((entry, index) => (
                  <li key={`${entry.created_at}-${index}`}>
                    {entry.decision}: {entry.purpose} — {entry.recipient}
                    {entry.created_at && ` (${formatDate(entry.created_at.slice(0, 10))})`}
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="detail-panel">
            <div className="detail-panel-heading">
              <div>
                <span className="section-overline">CASE INFORMATION</span>
                <h2>Your concern</h2>
              </div>
            </div>

            <div className="case-description-block">
              <span>Summary</span>
              <p>{caseItem.description}</p>
            </div>


            <div className="case-info-grid">
              <div>
                <span>Reference ID</span>
                <strong>{caseItem.id}</strong>
              </div>

              <div>
                <span>Category</span>
                <strong>{caseItem.category}</strong>
              </div>

              <div>
                <span>Date submitted</span>
                <strong>{formatDate(caseItem.date)}</strong>
              </div>

              <div>
                <span>Current status</span>
                <strong>{caseItem.status}</strong>
              </div>

              <div>
                <span>Incident date</span>
                <strong>
                  {caseItem.incidentDate
                    ? formatDate(caseItem.incidentDate)
                    : 'Not provided'}
                </strong>
              </div>

              <div>
                <span>Incident location</span>
                <strong>
                  {caseItem.incidentLocation?.trim() || 'Not provided'}
                </strong>
              </div>

              <div>
                <span>People involved</span>
                <strong>
                  {caseItem.peopleInvolved?.trim() || 'Not provided'}
                </strong>
              </div>
            </div>

          </section>

          <section className="detail-panel">
            <div className="detail-panel-heading">
              <div>
                <span className="section-overline">ACTIVITY</span>
                <h2>Update history</h2>
              </div>
            </div>

            <div className="activity-timeline">
              {(caseItem.updates ?? []).map((update, index) => (
                <article className="activity-item" key={`${update.title}-${index}`}>
                  <div
                    className={`activity-marker ${update.type === 'current' ? 'active' : ''
                      }`}
                  >
                    {update.type === 'current' ? (
                      <Clock3 size={15} />
                    ) : (
                      <CircleCheck size={15} />
                    )}
                  </div>
                  <div className="activity-copy">
                    <span>{update.date}</span>
                    <h3>{update.title}</h3>
                    <p>{update.description}</p>
                  </div>
                </article>
              ))}
            </div>
          </section>
        </div>

        <aside className="case-detail-sidebar">
          <section className="privacy-detail-card">
            <div className="privacy-detail-icon">
              <PrivacyIcon size={21} />
            </div>
            <span className="section-overline">YOUR PRIVACY</span>
            <h2>{privacy.title}</h2>
            <p>{privacy.description}</p>
            <div className="privacy-detail-divider" />
            <div className="privacy-detail-footnote">
              <LockKeyhole size={15} />
              <span>
                Your preference must be enforced by backend access controls.
              </span>
            </div>
          </section>

          <section className="case-help-card">
            <span className="section-overline">NEED TO ADD SOMETHING?</span>
            <h2>Your concern may need more context.</h2>
            <p>
              If you need to provide more information, contact the authorized
              support team through the process your institution establishes.
            </p>
            <p className="demo-small-note">
              Replies and attachments are not enabled in this frontend demo.
            </p>
          </section>

          <NavLink to="/cases" className="case-return-link">
            <ArrowLeft size={15} />
            Back to all cases
          </NavLink>
        </aside>
      </div>
    </main>
  );
}
