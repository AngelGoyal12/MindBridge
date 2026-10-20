import { useEffect, useState } from "react";

import CaseTaskManager from "../components/CaseTaskManager";
import DepartmentTaskDashboard from "../components/DepartmentTaskDashboard";
import MessageCenter from "../components/MessageCenter";
import { useAuth } from "../context/authContext";
import { caseStatusLabel, statusTimestamp } from "../services/casePresentation";
import {
  assignCoordinator,
  assignDepartment,
  getAdminCases,
  getAdminTasks,
  getAuthorizedDepartments,
  createCoordinatorProgressUpdate,
  createDepartmentActionRequest,
  getCoordinatorCases,
  getCoordinatorActionRequests,
  getCoordinatorTasks,
  getDepartmentCases,
  decideCoordinatorActionRequest,
  updateCoordinatorCaseStatus,
} from "../services/caseService";

const statusOptions = ["in_review", "in_progress", "closed"];

// Display names only: the internal role values stay admin / coordinator /
// department_staff.
const labels = {
  coordinator: "Department Coordinator workspace",
  admin: "Main Coordinator workspace",
  department_staff: "Department Staff workspace",
};

function CaseRows({ cases, departments, role, onUpdate, tasks = [], onTaskSaved }) {
  const [assignments, setAssignments] = useState({});
  const [assignmentErrors, setAssignmentErrors] = useState({});
  const [assignmentLoading, setAssignmentLoading] = useState({});
  const [departmentErrors, setDepartmentErrors] = useState({});
  const [departmentLoading, setDepartmentLoading] = useState({});
  const [closureOutcomes, setClosureOutcomes] = useState({});
  const [progressForms, setProgressForms] = useState({});
  const [progressErrors, setProgressErrors] = useState({});
  const [progressLoading, setProgressLoading] = useState({});
  const [actionForms, setActionForms] = useState({});
  const [actionErrors, setActionErrors] = useState({});
  const [actionLoading, setActionLoading] = useState({});
  const [statusLoading, setStatusLoading] = useState({});
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function saveCoordinator(caseItem) {
    if (assignmentLoading[caseItem.id]) return;
    const coordinatorEmail = (
      assignments[caseItem.id] ??
      caseItem.assigned_coordinator_email ??
      ""
    ).trim();
    if (!coordinatorEmail) {
      setAssignmentErrors((current) => ({
        ...current,
        [caseItem.id]: "Enter a Department Coordinator email address.",
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
          ? `Department Coordinator invitation sent for case ${caseItem.id}.`
          : `Department Coordinator assigned successfully to case ${caseItem.id}.`,
      );
    } catch (err) {
      setAssignmentErrors((current) => ({
        ...current,
        [caseItem.id]: err.message || "Could not assign Department Coordinator.",
      }));
    } finally {
      setAssignmentLoading((current) => ({
        ...current,
        [caseItem.id]: false,
      }));
    }
  }

  async function saveDepartment(caseItem) {
    if (departmentLoading[caseItem.id]) return;
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
      setMessage(`Case ${caseItem.id} routed to ${result.case.department}.`);
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
    if (statusLoading[caseItem.id] || status === caseItem.status) return;
    const closing = status === "closed";
    const outcome = closureOutcomes[caseItem.id]?.trim();
    if (closing && !outcome) {
      setError(`Add a closure outcome for case ${caseItem.id} before closing it.`);
      return;
    }
    if (closing && !window.confirm(`Close case ${caseItem.id} with the outcome below?`)) return;
    try {
      setError("");
      setMessage("");
      setStatusLoading((current) => ({ ...current, [caseItem.id]: true }));
      const result = await updateCoordinatorCaseStatus(
        caseItem.id,
        status,
        closing ? outcome : undefined,
      );
      onUpdate(result.case);
      if (closing) {
        setClosureOutcomes((current) => ({ ...current, [caseItem.id]: "" }));
        setMessage(`Case ${caseItem.id} closed successfully.`);
      } else {
        setMessage(`Case ${caseItem.id} status updated to ${caseStatusLabel(status)}.`);
      }
    } catch (err) {
      setError(err.message || "Could not update case status.");
    } finally {
      setStatusLoading((current) => ({ ...current, [caseItem.id]: false }));
    }
  }

  async function addProgressUpdate(caseItem) {
    if (progressLoading[caseItem.id]) return;
    const update = progressForms[caseItem.id] || {};
    setProgressLoading((current) => ({ ...current, [caseItem.id]: true }));
    setProgressErrors((current) => ({ ...current, [caseItem.id]: "" }));
    try {
      const result = await createCoordinatorProgressUpdate(caseItem.id, {
        title: update.title?.trim() || "",
        message: update.message?.trim() || "",
      });
      onUpdate({
        ...caseItem,
        progress_updates: [...(caseItem.progress_updates || []), result.update],
      });
      setProgressForms((current) => ({
        ...current,
        [caseItem.id]: { title: "", message: "" },
      }));
      setMessage(`Follow-up added to case ${caseItem.id}.`);
    } catch (err) {
      setProgressErrors((current) => ({
        ...current,
        [caseItem.id]: err.message || "Could not add the follow-up.",
      }));
    } finally {
      setProgressLoading((current) => ({ ...current, [caseItem.id]: false }));
    }
  }

  async function sendActionRequest(caseItem) {
    if (actionLoading[caseItem.id]) return;
    const request = actionForms[caseItem.id] || {};
    setActionLoading((current) => ({ ...current, [caseItem.id]: true }));
    setActionErrors((current) => ({ ...current, [caseItem.id]: "" }));
    try {
      await createDepartmentActionRequest(caseItem.id, {
        request_type: request.request_type || "update",
        message: request.message?.trim() || "",
      });
      setActionForms((current) => ({
        ...current,
        [caseItem.id]: { request_type: "update", message: "" },
      }));
      setMessage(`Update sent to the Department Coordinator for case ${caseItem.id}.`);
    } catch (err) {
      setActionErrors((current) => ({
        ...current,
        [caseItem.id]: err.message || "Could not send this message.",
      }));
    } finally {
      setActionLoading((current) => ({ ...current, [caseItem.id]: false }));
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
              {caseStatusLabel(caseItem.status)}
            </span>
          </div>

          {role === "coordinator" && (
            <>
              <h3>{caseItem.title}</h3>
              <p>
                {caseItem.description}
              </p>
              <p>
                Department consent:{" "}
                <strong>
                  {(caseItem.department_consent?.level || "anonymous").replaceAll("_", " ")}
                </strong>
                {caseItem.department_consent?.level === "restricted" &&
                  ` — fields selected: ${(caseItem.department_consent.fields || []).join(", ") || "none"}`}
              </p>
              <p>
                Student: <strong>{caseItem.student_name || "Unavailable"}</strong>
                {caseItem.student_email ? ` · ${caseItem.student_email}` : ""}
                {caseItem.student_phone ? ` · ${caseItem.student_phone}` : ""}
                {caseItem.student_department ? ` · ${caseItem.student_department}` : ""}
              </p>
              <label className="field-group">
                Update status
                <select
                  value={caseItem.status}
                  disabled={Boolean(statusLoading[caseItem.id])}
                  aria-label={`Update status for case ${caseItem.id}`}
                  onChange={(event) =>
                    changeStatus(caseItem, event.target.value)
                  }
                >
                  {!statusOptions.includes(caseItem.status) && (
                    <option value={caseItem.status} disabled>
                      {caseItem.status.replaceAll("_", " ")}
                    </option>
                  )}
                  {statusOptions.map((status) => (
                    <option key={status} value={status}>
                      {caseStatusLabel(status)}
                    </option>
                  ))}
                </select>
              </label>
              {caseItem.status !== "closed" && (
                <label className="field-group">
                  Closure outcome (required to close)
                  <textarea
                    minLength={2}
                    maxLength={2000}
                    required
                    aria-label={`Closure outcome for case ${caseItem.id}`}
                    disabled={Boolean(statusLoading[caseItem.id])}
                    value={closureOutcomes[caseItem.id] || ""}
                    onChange={(event) => setClosureOutcomes((current) => ({
                      ...current,
                      [caseItem.id]: event.target.value,
                    }))}
                  />
                </label>
              )}
              <details>
                <summary>Record a student-visible follow-up</summary>
                <label className="field-group">
                  Update title
                  <input
                    minLength={2}
                    maxLength={150}
                    value={progressForms[caseItem.id]?.title || ""}
                    onChange={(event) => setProgressForms((current) => ({
                      ...current,
                      [caseItem.id]: { ...current[caseItem.id], title: event.target.value },
                    }))}
                  />
                </label>
                <label className="field-group">
                  Progress or follow-up
                  <textarea
                    minLength={2}
                    maxLength={2000}
                    value={progressForms[caseItem.id]?.message || ""}
                    onChange={(event) => setProgressForms((current) => ({
                      ...current,
                      [caseItem.id]: { ...current[caseItem.id], message: event.target.value },
                    }))}
                  />
                </label>
                <button
                  type="button"
                  className="secondary-button"
                  disabled={
                    progressLoading[caseItem.id] ||
                    !progressForms[caseItem.id]?.title?.trim() ||
                    !progressForms[caseItem.id]?.message?.trim()
                  }
                  onClick={() => addProgressUpdate(caseItem)}
                >
                  {progressLoading[caseItem.id] ? "Saving..." : "Add follow-up"}
                </button>
                {progressErrors[caseItem.id] && (
                  <p role="alert" className="field-error">
                    {progressErrors[caseItem.id]}
                  </p>
                )}
              </details>
            </>
          )}

          {role === "admin" && (
            <>
            <section
              className="role-case-brief"
              aria-label={`Redacted brief for case ${caseItem.id}`}
            >
              <h3>{caseItem.title}</h3>
              <p>{caseItem.summary}</p>
              <p>
                Submitted:{" "}
                {caseItem.created_at
                  ? statusTimestamp(caseItem.created_at)
                  : "Unavailable"}
              </p>
              {caseItem.urgency && <p>Urgency: {caseItem.urgency}</p>}
            </section>
            <div className="role-assignment-controls">
              <label className="field-group">
                Department Coordinator email
                <input
                  type="email"
                  autoComplete="off"
                  placeholder="coordinator@institution.edu"
                  aria-label={`Department Coordinator email for case ${caseItem.id}`}
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
                disabled={
                  assignmentLoading[caseItem.id] ||
                  !(assignments[caseItem.id] ?? caseItem.assigned_coordinator_email ?? "").trim()
                }
                onClick={() => saveCoordinator(caseItem)}
              >
                {assignmentLoading[caseItem.id]
                  ? "Sending..."
                  : "Assign / invite Department Coordinator"}
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
            </>
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

          {(role === "coordinator" || role === "admin") && onTaskSaved && (
            <CaseTaskManager
              caseItem={caseItem}
              departments={departments}
              tasks={tasks.filter((task) => task.case_id === caseItem.id)}
              onTaskSaved={onTaskSaved}
              onFeedback={setMessage}
              asAdmin={role === "admin"}
            />
          )}

          {role === "department_staff" && (
            <>
              <h3>{caseItem.title}</h3>
              <p>{caseItem.description}</p>
              <p>
                Identity consent:{" "}
                <strong>
                  {(caseItem.department_consent?.level || "anonymous").replaceAll("_", " ")}
                </strong>
                {caseItem.department_consent?.level === "restricted" &&
                  ` — fields shared: ${(caseItem.department_consent.fields || []).join(", ") || "none"}`}
              </p>
              {caseItem.department_identity_consent && (
                <div>
                  {caseItem.student_name && <p>Student: {caseItem.student_name}</p>}
                  {caseItem.student_email && <p>Email: {caseItem.student_email}</p>}
                  {caseItem.student_phone && <p>Phone: {caseItem.student_phone}</p>}
                  {caseItem.student_department && <p>Student department: {caseItem.student_department}</p>}
                </div>
              )}
              {caseItem.coordinator_available ? (
                <details>
                <summary>Send an update or action request to the Department Coordinator</summary>
                <label className="field-group">
                  Request type
                  <select
                    value={actionForms[caseItem.id]?.request_type || "update"}
                    onChange={(event) => setActionForms((current) => ({
                      ...current,
                      [caseItem.id]: {
                        ...current[caseItem.id],
                        request_type: event.target.value,
                      },
                    }))}
                  >
                    <option value="update">Case-related update</option>
                    <option value="closure_request">Request case closure</option>
                  </select>
                </label>
                <label className="field-group">
                  Message
                  <textarea
                    aria-label={`Message to Department Coordinator for case ${caseItem.id}`}
                    minLength={2}
                    maxLength={2000}
                    value={actionForms[caseItem.id]?.message || ""}
                    onChange={(event) => setActionForms((current) => ({
                      ...current,
                      [caseItem.id]: {
                        ...current[caseItem.id],
                        message: event.target.value,
                      },
                    }))}
                  />
                </label>
                <button
                  type="button"
                  className="secondary-button"
                  disabled={
                    actionLoading[caseItem.id] ||
                    (actionForms[caseItem.id]?.message || "").trim().length < 2
                  }
                  onClick={() => sendActionRequest(caseItem)}
                >
                  {actionLoading[caseItem.id] ? "Sending..." : "Send to Department Coordinator"}
                </button>
                {actionErrors[caseItem.id] && (
                  <p role="alert" className="field-error">
                    {actionErrors[caseItem.id]}
                  </p>
                )}
                </details>
              ) : (
                <p>This case has no assigned Department Coordinator to contact yet.</p>
              )}
              <p>Department staff cannot change the case status or close cases.</p>
            </>
          )}
        </article>
      ))}
    </div>
  );
}

function CoordinatorActionRequests({ requests, cases, onDecision, loadingById }) {
  if (!requests.length) {
    return <p>No department updates or action requests.</p>;
  }

  return (
    <div className="role-case-list">
      {requests.map((request) => {
        const relatedCase = cases.find((item) => item.id === request.case_id);
        return (
        <article className="role-case-card" key={request.id}>
          <div className="role-case-heading">
            <div>
              <span className="section-overline">CASE {request.case_id}</span>
              <h3>
                {request.request_type === "closure_request"
                  ? "Closure request"
                  : "Department update"}
              </h3>
              {relatedCase?.title && <p>{relatedCase.title}</p>}
            </div>
            <span>{request.status}</span>
          </div>
          <p className="request-created-at">
            Received {statusTimestamp(request.created_at)}
          </p>
          <p>{request.message}</p>
          {request.status === "open" && (
            <div className="role-assignment-controls">
              <button
                type="button"
                className="secondary-button"
                disabled={Boolean(loadingById[request.id])}
                onClick={() => onDecision(request.id, "handled")}
              >
                {loadingById[request.id] ? "Saving..." : "Mark handled"}
              </button>
              <button
                type="button"
                className="secondary-button"
                disabled={Boolean(loadingById[request.id])}
                onClick={() => onDecision(request.id, "dismissed")}
              >
                Dismiss request
              </button>
              {request.request_type === "closure_request" && (
                <p>
                  Review the case and use its status control to close it with
                  an outcome if appropriate. This request does not close the case.
                </p>
              )}
            </div>
          )}
        </article>
        );
      })}
    </div>
  );
}

export default function RoleDashboard() {
  const { user } = useAuth();
  const role = user.role;
  const [cases, setCases] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [actionRequests, setActionRequests] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);
  const [requestLoading, setRequestLoading] = useState({});
  const [requestError, setRequestError] = useState("");
  const [requestMessage, setRequestMessage] = useState("");
  const [loadWarnings, setLoadWarnings] = useState([]);
  const [unreadMessages, setUnreadMessages] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function loadWorkspace() {
      try {
        setLoading(true);
        setError("");
        setLoadWarnings([]);
        const caseLoader = {
          coordinator: getCoordinatorCases,
          admin: getAdminCases,
          department_staff: getDepartmentCases,
        }[role];
        if (!caseLoader) {
          throw new Error("Your account does not have a workspace.");
        }
        // The case list is essential. Everything else is optional, so a
        // failure there shows a notice instead of blanking the dashboard.
        const caseData = await caseLoader();
        const optional = [
          {
            name: "departments",
            run:
              role === "admin" || role === "coordinator"
                ? getAuthorizedDepartments
                : null,
          },
          {
            name: "department requests",
            run: role === "coordinator" ? getCoordinatorActionRequests : null,
          },
          {
            name: "tasks",
            run:
              role === "coordinator"
                ? getCoordinatorTasks
                : role === "admin"
                  ? getAdminTasks
                  : null,
          },
        ];
        const settled = await Promise.allSettled(
          optional.map((item) => (item.run ? item.run() : Promise.resolve([]))),
        );
        if (!cancelled) {
          const valueOf = (index) =>
            settled[index].status === "fulfilled" &&
            Array.isArray(settled[index].value)
              ? settled[index].value
              : [];
          setCases(Array.isArray(caseData) ? caseData : []);
          setDepartments(valueOf(0));
          setActionRequests(valueOf(1));
          setTasks(valueOf(2));
          setLoadWarnings(
            optional
              .filter((_, index) => settled[index].status === "rejected")
              .map((item) => item.name),
          );
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
  }, [role, reloadKey]);

  function updateCase(updatedCase) {
    setCases((current) =>
      current.map((item) =>
        item.id === updatedCase.id ? { ...item, ...updatedCase } : item,
      ),
    );
  }

  function saveTask(savedTask) {
    setTasks((current) =>
      current.some((item) => item.id === savedTask.id)
        ? current.map((item) => (item.id === savedTask.id ? savedTask : item))
        : [savedTask, ...current],
    );
  }

  async function decideActionRequest(requestId, status) {
    if (requestLoading[requestId]) return;
    setRequestLoading((current) => ({ ...current, [requestId]: true }));
    setRequestError("");
    setRequestMessage("");
    try {
      const updatedRequest = await decideCoordinatorActionRequest(
        requestId,
        status,
      );
      setActionRequests((current) =>
        current.map((item) =>
          item.id === requestId ? updatedRequest : item,
        ),
      );
      setRequestMessage(
        status === "handled"
          ? "Department request marked as handled."
          : "Department request dismissed.",
      );
    } catch (err) {
      setRequestError(err.message || "Could not update the department request.");
    } finally {
      setRequestLoading((current) => ({ ...current, [requestId]: false }));
    }
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
              "Review the full case details and student identity for cases assigned to you. Assign work to staff in the departments, and control case status, closure, and student-visible follow-ups."}
            {role === "admin" &&
              "Receive cases, invite Department Coordinators, and send tasks to departments such as Counselling or Academics using redacted case briefs. This role does not include student identity or contact details."}
            {role === "department_staff" &&
              `Tasks sent to ${user.department} are listed here. Claim a task from your department's pool or work on the tasks assigned to you. Case details are limited to the minimum necessary information.`}
          </p>
        </div>
      </section>

      <section className="role-workspace-panel">
        {loading ? (
          <p role="status">Loading authorized cases...</p>
        ) : error ? (
          <div role="alert" className="workspace-error">
            <p>{error}</p>
            <button
              type="button"
              className="secondary-button"
              onClick={() => setReloadKey((key) => key + 1)}
            >
              Retry loading workspace
            </button>
          </div>
        ) : (
          <>
            {loadWarnings.length > 0 && (
              <div role="alert" className="workspace-error">
                <p>
                  Some information could not be loaded ({loadWarnings.join(", ")}).
                  The rest of your workspace is available.
                </p>
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => setReloadKey((key) => key + 1)}
                >
                  Retry
                </button>
              </div>
            )}
            {requestError && <p role="alert" className="field-error">{requestError}</p>}
            {requestMessage && <p role="status" className="role-feedback">{requestMessage}</p>}
            {role === "coordinator" && (
              <section aria-labelledby="department-requests-heading">
                <h2 id="department-requests-heading">
                  Department updates and requests
                </h2>
                <CoordinatorActionRequests
                  requests={actionRequests}
                  cases={cases}
                  onDecision={decideActionRequest}
                  loadingById={requestLoading}
                />
              </section>
            )}
            {role === "department_staff" && (
              <DepartmentTaskDashboard department={user.department} />
            )}
            <MessageCenter cases={cases} onUnreadChange={setUnreadMessages} />
            {unreadMessages > 0 && (
              <p role="status" className="role-feedback">
                You have {unreadMessages} unread message{unreadMessages === 1 ? "" : "s"}.
              </p>
            )}
            <h2>{role === "department_staff" ? "Routed cases" : "Cases"}</h2>
            <CaseRows
              cases={cases}
              departments={departments}
              role={role}
              onUpdate={updateCase}
              tasks={tasks}
              onTaskSaved={role === "coordinator" || role === "admin" ? saveTask : undefined}
            />
          </>
        )}
      </section>
    </main>
  );
}
