import { useEffect, useState } from "react";

import { useAuth } from "../context/authContext";
import {
  assignCoordinator,
  assignDepartment,
  getAdminCases,
  getAuthorizedDepartments,
  getCoordinatorCases,
  getDepartmentCases,
  requestCoordinatorIdentityDisclosure,
  updateCoordinatorCaseStatus,
} from "../services/caseService";

const statusOptions = [
  "submitted",
  "in_review",
  "in_progress",
  "resolved",
  "closed",
];

const labels = {
  coordinator: "Coordinator workspace",
  admin: "Administration",
  department_staff: "Department workspace",
};

function CaseRows({ cases, departments, role, onUpdate }) {
  const [assignments, setAssignments] = useState({});
  const [assignmentErrors, setAssignmentErrors] = useState({});
  const [assignmentLoading, setAssignmentLoading] = useState({});
  const [departmentErrors, setDepartmentErrors] = useState({});
  const [departmentLoading, setDepartmentLoading] = useState({});
  const [disclosureRequests, setDisclosureRequests] = useState({});
  const [disclosures, setDisclosures] = useState({});
  const [disclosureErrors, setDisclosureErrors] = useState({});
  const [disclosureLoading, setDisclosureLoading] = useState({});
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function saveCoordinator(caseItem) {
    const coordinatorEmail = (
      assignments[caseItem.id] ??
      caseItem.assigned_coordinator_email ??
      ""
    ).trim();
    if (!coordinatorEmail) {
      setAssignmentErrors((current) => ({
        ...current,
        [caseItem.id]: "Enter a coordinator email address.",
      }));
      return;
    }

    try {
      setAssignmentErrors((current) => ({ ...current, [caseItem.id]: "" }));
      setMessage("");
      setAssignmentLoading((current) => ({
        ...current,
        [caseItem.id]: true,
      }));
      const result = await assignCoordinator(caseItem.id, coordinatorEmail);
      onUpdate(result.case);
      setAssignments((current) => ({
        ...current,
        [caseItem.id]: result.coordinator_email,
      }));
      setMessage(
        result.assignment_status === "invitation_sent"
          ? `Coordinator invitation emailed for case ${caseItem.id}.`
          : `Case ${caseItem.id} assigned to ${result.coordinator_email}.`,
      );
    } catch (err) {
      setAssignmentErrors((current) => ({
        ...current,
        [caseItem.id]: err.message || "Could not assign coordinator.",
      }));
    } finally {
      setAssignmentLoading((current) => ({
        ...current,
        [caseItem.id]: false,
      }));
    }
  }

  async function saveDepartment(caseItem) {
    const department =
      assignments[`department-${caseItem.id}`] ?? caseItem.department ?? "";
    if (!department) {
      setDepartmentErrors((current) => ({
        ...current,
        [caseItem.id]: "Select an authorized department.",
      }));
      return;
    }

    try {
      setDepartmentErrors((current) => ({ ...current, [caseItem.id]: "" }));
      setMessage("");
      setDepartmentLoading((current) => ({
        ...current,
        [caseItem.id]: true,
      }));
      const result = await assignDepartment(caseItem.id, department);
      onUpdate(result.case);
      setAssignments((current) => ({
        ...current,
        [`department-${caseItem.id}`]: result.case.department,
      }));
      setMessage(
        `Case ${caseItem.id} routed to ${result.case.department}.`,
      );
    } catch (err) {
      setDepartmentErrors((current) => ({
        ...current,
        [caseItem.id]: err.message || "Could not route case to department.",
      }));
    } finally {
      setDepartmentLoading((current) => ({
        ...current,
        [caseItem.id]: false,
      }));
    }
  }

  async function changeStatus(caseItem, status) {
    try {
      setError("");
      setMessage("");
      const result = await updateCoordinatorCaseStatus(caseItem.id, status);
      onUpdate(result.case);
      setMessage(`Case ${caseItem.id} status updated.`);
    } catch (err) {
      setError(err.message || "Could not update case status.");
    }
  }

  async function requestDisclosure(caseItem) {
    const request = disclosureRequests[caseItem.id] || {};
    setDisclosureLoading((current) => ({ ...current, [caseItem.id]: true }));
    setDisclosureErrors((current) => ({ ...current, [caseItem.id]: "" }));
    try {
      const identity = await requestCoordinatorIdentityDisclosure(caseItem.id, {
        purpose: request.purpose?.trim() || "",
        scope: request.scope?.trim() || "",
      });
      setDisclosures((current) => ({ ...current, [caseItem.id]: identity }));
    } catch (err) {
      setDisclosureErrors((current) => ({
        ...current,
        [caseItem.id]: err.status === 403
          ? "Identity disclosure was denied. Active consent for this exact purpose and scope is required."
          : err.message || "Could not request identity disclosure.",
      }));
    } finally {
      setDisclosureLoading((current) => ({ ...current, [caseItem.id]: false }));
    }
  }

  if (!cases.length) {
    return <p>No cases are currently available for this workspace.</p>;
  }

  return (
    <div className="role-case-list">
      {error && <p role="alert" className="field-error">{error}</p>}
      {message && <p role="status">{message}</p>}
      {cases.map((caseItem) => (
        <article className="role-case-card" key={caseItem.id}>
          <div className="role-case-heading">
            <div>
              <span className="section-overline">CASE {caseItem.id}</span>
              <h2>{caseItem.category}</h2>
            </div>
            <span className={`status-badge case-status-${caseItem.status}`}>
              {caseItem.status.replaceAll("_", " ")}
            </span>
          </div>

          {role === "coordinator" && (
            <>
              <p>
                Student identity and free-text report content are withheld in
                routine review. Review the available category and status only.
              </p>
              <label className="field-group">
                Update status
                <select
                  value={caseItem.status}
                  onChange={(event) =>
                    changeStatus(caseItem, event.target.value)
                  }
                >
                  {statusOptions.map((status) => (
                    <option key={status} value={status}>
                      {status.replaceAll("_", " ")}
                    </option>
                  ))}
                </select>
              </label>
              <details className="coordinator-disclosure">
                <summary>Request consent-authorized identity disclosure</summary>
                <p>
                  This request succeeds only if the student has granted active
                  consent to you for the exact purpose and scope below. Anonymous
                  cases cannot disclose identity.
                </p>
                <label className="field-group">
                  Purpose from the consent grant
                  <input
                    minLength={2}
                    maxLength={255}
                    value={disclosureRequests[caseItem.id]?.purpose || ""}
                    onChange={(event) => setDisclosureRequests((current) => ({
                      ...current,
                      [caseItem.id]: {
                        ...current[caseItem.id],
                        purpose: event.target.value,
                      },
                    }))}
                  />
                </label>
                <label className="field-group">
                  Scope from the consent grant
                  <textarea
                    minLength={2}
                    maxLength={2000}
                    value={disclosureRequests[caseItem.id]?.scope || ""}
                    onChange={(event) => setDisclosureRequests((current) => ({
                      ...current,
                      [caseItem.id]: {
                        ...current[caseItem.id],
                        scope: event.target.value,
                      },
                    }))}
                  />
                </label>
                <button
                  type="button"
                  className="secondary-button"
                  disabled={
                    disclosureLoading[caseItem.id] ||
                    (disclosureRequests[caseItem.id]?.purpose || "").trim().length < 2 ||
                    (disclosureRequests[caseItem.id]?.scope || "").trim().length < 2
                  }
                  onClick={() => requestDisclosure(caseItem)}
                >
                  {disclosureLoading[caseItem.id]
                    ? "Checking consent..."
                    : "Check consent and request identity"}
                </button>
                {disclosureErrors[caseItem.id] && (
                  <p role="alert" className="field-error">
                    {disclosureErrors[caseItem.id]}
                  </p>
                )}
                {disclosures[caseItem.id] && (
                  <div role="status" className="coordinator-disclosed-identity">
                    <strong>Identity disclosed under the recorded consent</strong>
                    <p>{disclosures[caseItem.id].student_name}</p>
                    <p>{disclosures[caseItem.id].student_email}</p>
                    <p>
                      Purpose: {disclosures[caseItem.id].purpose}. Scope:{" "}
                      {disclosures[caseItem.id].scope}
                    </p>
                  </div>
                )}
              </details>
            </>
          )}

          {role === "admin" && (
            <div className="role-assignment-controls">
              <label className="field-group">
                Coordinator email
                <input
                  type="email"
                  autoComplete="off"
                  placeholder="coordinator@institution.edu"
                  value={
                    assignments[caseItem.id] ??
                    caseItem.assigned_coordinator_email ??
                    ""
                  }
                  onChange={(event) =>
                    setAssignments((current) => ({
                      ...current,
                      [caseItem.id]: event.target.value,
                    }))
                  }
                />
              </label>
              <button
                type="button"
                className="secondary-button"
                disabled={assignmentLoading[caseItem.id]}
                onClick={() => saveCoordinator(caseItem)}
              >
                {assignmentLoading[caseItem.id]
                  ? "Sending..."
                  : "Assign / invite coordinator"}
              </button>
              {assignmentErrors[caseItem.id] && (
                <p role="alert" className="field-error">
                  {assignmentErrors[caseItem.id]}
                </p>
              )}
              <p>
                Existing coordinator accounts are assigned directly. New
                addresses receive a one-time activation invitation.
              </p>
            </div>
          )}

          {(role === "admin" || role === "coordinator") && (
            <div className="role-assignment-controls">
              {role === "coordinator" && (
                <p>
                  Route this assigned case to the department that matches its
                  category and support needs. Only provisioned department
                  teams are available.
                </p>
              )}
              <p>
                Current department:{" "}
                <strong>{caseItem.department || "Not routed"}</strong>
              </p>
              <label className="field-group">
                Route to department
                <select
                  value={
                    assignments[`department-${caseItem.id}`] ??
                    caseItem.department ??
                    ""
                  }
                  onChange={(event) =>
                    setAssignments((current) => ({
                      ...current,
                      [`department-${caseItem.id}`]: event.target.value,
                    }))
                  }
                  required
                >
                  <option value="" disabled>
                    Select an authorized department
                  </option>
                  {departments.map((department) => (
                    <option key={department} value={department}>
                      {department}
                    </option>
                  ))}
                </select>
              </label>
              <button
                type="button"
                className="secondary-button"
                disabled={
                  departmentLoading[caseItem.id] ||
                  !departments.length ||
                  !(assignments[`department-${caseItem.id}`] ?? caseItem.department)
                }
                onClick={() => saveDepartment(caseItem)}
              >
                {departmentLoading[caseItem.id]
                  ? "Routing..."
                  : "Route department"}
              </button>
              {!departments.length && (
                <p role="status">
                  No department teams have been provisioned yet.
                </p>
              )}
              {departmentErrors[caseItem.id] && (
                <p role="alert" className="field-error">
                  {departmentErrors[caseItem.id]}
                </p>
              )}
            </div>
          )}

          {role === "department_staff" && (
            <p>
              Routed to your department. Student identity and report details
              are not available in this view.
            </p>
          )}
        </article>
      ))}
    </div>
  );
}

export default function RoleDashboard() {
  const { user } = useAuth();
  const role = user.role;
  const [cases, setCases] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function loadWorkspace() {
      try {
        setLoading(true);
        setError("");
        const caseLoader = {
          coordinator: getCoordinatorCases,
          admin: getAdminCases,
          department_staff: getDepartmentCases,
        }[role];
        const [caseData, departmentData] = await Promise.all([
          caseLoader(),
          role === "admin" || role === "coordinator"
            ? getAuthorizedDepartments()
            : Promise.resolve([]),
        ]);
        if (!cancelled) {
          setCases(caseData);
          setDepartments(departmentData);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message || "Could not load this workspace.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadWorkspace();
    return () => {
      cancelled = true;
    };
  }, [role]);

  function updateCase(updatedCase) {
    setCases((current) =>
      current.map((item) =>
        item.id === updatedCase.id ? { ...item, ...updatedCase } : item,
      ),
    );
  }

  return (
    <main className="dashboard page-container">
      <section className="dashboard-welcome">
        <div className="dashboard-welcome-copy">
          <div className="eyebrow">
            <span className="eyebrow-dot" />
            {labels[role]}
          </div>
          <h1>
            Welcome, <em>{user.name}.</em>
          </h1>
          <p>
            {role === "coordinator" &&
              "Review only the cases assigned to you. Student identity is withheld unless the student grants active, purpose-specific consent."}
            {role === "admin" &&
              "Manage case routing and assignments. Administrative access does not include protected student identity or report descriptions."}
            {role === "department_staff" &&
              `Only cases routed to ${user.department} are listed. This view contains minimum necessary case information.`}
          </p>
        </div>
      </section>

      <section className="role-workspace-panel">
        {loading ? (
          <p role="status">Loading authorized cases...</p>
        ) : error ? (
          <p role="alert">{error}</p>
        ) : (
          <CaseRows
            cases={cases}
            departments={departments}
            role={role}
            onUpdate={updateCase}
          />
        )}
      </section>
    </main>
  );
}
