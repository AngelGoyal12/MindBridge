import { useEffect, useState } from 'react';
import { Link, NavLink, useLocation, useParams } from 'react-router-dom';
import {
  ArrowLeft,
  ArrowUpRight,
  CalendarDays,
  Clock3,
  FileText,
  LockKeyhole,
  ShieldCheck,
  CircleHelp,
} from 'lucide-react';
import CaseProgressTracker from "../components/CaseProgressTracker";
import { caseStatusLabel, normalizeCaseStatus, statusTimestamp } from "../services/casePresentation";

import {
  getCaseById,
  getCaseConsents,
  getCaseDisclosureAudit,
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

  const createdAt = item.created_at ?? item.createdAt;

  const date = createdAt
    ? createdAt.slice(0, 10)
    : item.date ?? '';
  const progressUpdates = Array.isArray(item.progress_updates)
    ? item.progress_updates
    : [];

  return {
    ...item,
    identityMode: item.identity_mode ?? item.identityMode ?? 'restricted',
    departmentIdentityConsent: Boolean(item.department_identity_consent),
    departmentConsent: item.department_consent ?? {
      level: 'anonymous',
      fields: [],
      active: false,
    },
    category:
      categoryLabels[item.category] ??
      item.categoryLabel ??
      item.category ??
      'Other support',

  categoryValue: item.categoryValue ?? item.category,
  statusValue: normalizeCaseStatus(item.status),
  status: caseStatusLabel(item.status),
  date,

    progress_updates: progressUpdates,
  };
}

const privacyDetails = {
  identified: {
    title: 'Identity linked to your account',
    description:
      'The assigned Coordinator can see your identity. Department access follows the separate consent choice recorded for this case.',
    icon: ShieldCheck,
  },
  restricted: {
    title: 'Restricted identity preference',
    description:
      'Your case is linked to your account. Department identity disclosure is controlled by your case-specific consent.',
    icon: LockKeyhole,
  },
  anonymous: {
    title: 'Identity preference: restricted',
    description:
      'This preference does not replace your department consent decision. Details in your report may still identify you.',
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
  const [identitySaving, setIdentitySaving] = useState(false);
  const [withdrawingConsentId, setWithdrawingConsentId] = useState(null);

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
    setConsentMessage('');
    try {
      const response = await updateCaseIdentity(caseId, identityMode);
      setCaseItem((current) => ({
        ...current,
        identityMode: response.case.identity_mode,
      }));
      setConsentMessage('Identity preference updated.');
    } catch (err) {
      setConsentError(err.message || 'Could not update the identity preference.');
    } finally {
      setIdentitySaving(false);
    }
  }

  async function handleWithdrawConsent(consentId) {
    if (withdrawingConsentId !== null) return;
    if (!window.confirm("Withdraw this case's active department identity consent?")) {
      return;
    }
    setConsentError('');
    setConsentMessage('');
    setWithdrawingConsentId(consentId);
    try {
      await withdrawCaseConsent(caseId, consentId);
      setConsents(await getCaseConsents(caseId));
      setDisclosureAudit(await getCaseDisclosureAudit(caseId));
      setCaseItem((current) => ({
        ...current,
        departmentIdentityConsent: false,
        departmentConsent: {
          ...current.departmentConsent,
          active: false,
        },
      }));
      setConsentMessage('Consent has been withdrawn.');
    } catch (err) {
      setConsentError(err.message || 'Could not withdraw consent.');
    } finally {
      setWithdrawingConsentId(null);
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
            Submitted {statusTimestamp(caseItem.created_at)}
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
                {caseItem.progress_updates.length} recorded updates
              </span>
            </div>
            <CaseProgressTracker caseItem={caseItem} />
          </section>

          <section className="detail-panel">
            <div className="detail-panel-heading">
              <div>
                <span className="section-overline">DEPARTMENT CONSENT</span>
                <h2>Identity sharing choice</h2>
              </div>
            </div>
            <p>
              The assigned Coordinator can see your identity and full case
              details. The assigned department receives only the identity fields
              selected below. You can withdraw an active consent below.
            </p>
            <div className="field-group" style={{ marginTop: '18px' }}>
              <strong>
                Consent level: {caseItem.departmentConsent.level.replaceAll('_', ' ')}
              </strong>
              <div>
                Selected fields: {caseItem.departmentConsent.fields.length
                  ? caseItem.departmentConsent.fields.join(', ')
                  : 'none'}
                {caseItem.departmentConsent.active ? '' : ' (no active disclosure)'}
              </div>
              <div>
                Current routing: {caseItem.department || 'Not yet assigned'}
              </div>
            </div>
            <div className="field-group" style={{ marginTop: '18px' }}>
              <label htmlFor="case-identity-mode">
                Additional identity preference
              </label>
              <select
                id="case-identity-mode"
                value={caseItem.identityMode}
                onChange={handleIdentityChange}
                disabled={identitySaving}
              >
                <option value="identified">Identified</option>
                <option value="restricted">Restricted</option>
                <option value="anonymous">No additional identity preference</option>
              </select>
              <p>
                This preference does not change department consent. Coordinators
                assigned to the case can view your identity.
              </p>
            </div>

            {consentError && <p role="alert" className="field-error">{consentError}</p>}
            {consentMessage && <p role="status">{consentMessage}</p>}

            <h3 style={{ marginTop: '28px' }}>Consent record</h3>
            {consentLoading ? (
              <p role="status">Loading consent history...</p>
            ) : consents.length === 0 ? (
              <p>No department consent record is available for this case.</p>
            ) : (
              <ul>
                {consents.map((consent) => (
                  <li key={consent.id} style={{ marginBlock: '12px' }}>
                    <strong>Assigned department — {consent.scope}</strong>
                    <div>
                      {consent.granted && !consent.withdrawn_at
                        ? 'Consent active'
                        : consent.granted
                          ? 'Consent withdrawn'
                          : 'Consent declined'}
                    </div>
                    {consent.granted && !consent.withdrawn_at && (
                      <button
                        type="button"
                        className="secondary-button"
                        disabled={withdrawingConsentId !== null}
                        onClick={() => handleWithdrawConsent(consent.id)}
                      >
                        {withdrawingConsentId === consent.id ? 'Withdrawing...' : 'Withdraw'}
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            )}

            <h3 style={{ marginTop: '28px' }}>Consent access history</h3>
            {disclosureAudit.length === 0 ? (
              <p>No identity access actions have been recorded.</p>
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
                <span>Department</span>
                <strong>{caseItem.department || 'Not yet assigned'}</strong>
              </div>

              <div>
                <span>Current status</span>
                <strong>{caseItem.status}</strong>
              </div>

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
            <p className="case-capability-note">
              This case view does not provide a student-to-staff message or
              attachment endpoint.
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
