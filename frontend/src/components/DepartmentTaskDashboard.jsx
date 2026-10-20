import { useCallback, useEffect, useMemo, useState } from "react";

import {
  claimDepartmentTask,
  getDepartmentTaskSummary,
  getDepartmentTasks,
  updateDepartmentTaskStatus,
} from "../services/caseService";
import {
  formatDueDate,
  statusTimestamp,
  taskStatusLabel,
} from "../services/casePresentation";

const FILTERS = [
  { id: "open", label: "Open" },
  { id: "mine", label: "Assigned to me" },
  { id: "pool", label: "Unclaimed" },
  { id: "completed", label: "Completed" },
  { id: "all", label: "All" },
];

const SUMMARY_TILES = [
  { key: "mine", label: "Assigned to me" },
  { key: "unassigned", label: "Unclaimed" },
  { key: "assigned", label: "Not started" },
  { key: "in_progress", label: "In progress" },
  { key: "completed", label: "Completed" },
  { key: "overdue", label: "Overdue" },
];

const PRIORITY_ORDER = { urgent: 0, high: 1, normal: 2, low: 3 };

function matchesFilter(task, filter) {
  if (filter === "open") {
    return task.status === "assigned" || task.status === "in_progress";
  }
  const open = task.status === "assigned" || task.status === "in_progress";
  if (filter === "mine") return open && Boolean(task.assigned_to_me);
  if (filter === "pool") return open && !task.assigned_staff_id;
  if (filter === "completed") return task.status === "completed";
  return true;
}

function sortTasks(tasks) {
  return [...tasks].sort((a, b) => {
    const aOpen = a.status === "assigned" || a.status === "in_progress";
    const bOpen = b.status === "assigned" || b.status === "in_progress";
    if (aOpen !== bOpen) return aOpen ? -1 : 1;
    if (a.is_overdue !== b.is_overdue) return a.is_overdue ? -1 : 1;
    const priority =
      (PRIORITY_ORDER[a.priority] ?? 2) - (PRIORITY_ORDER[b.priority] ?? 2);
    if (priority !== 0) return priority;
    return b.id - a.id;
  });
}

function TaskCard({ task, onChanged }) {
  const [note, setNote] = useState("");
  const [completing, setCompleting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const isOpen = task.status === "assigned" || task.status === "in_progress";
  const caseInfo = task.case || {};

  async function claim() {
    if (saving) return;
    setSaving(true);
    setError("");
    try {
      const result = await claimDepartmentTask(task.id);
      onChanged(result.task, `Task ${task.id} is now assigned to you.`);
    } catch (err) {
      setError(err.message || "Could not claim this task.");
    } finally {
      setSaving(false);
    }
  }

  async function changeStatus(status) {
    if (saving) return;
    if (status === "completed" && note.trim().length < 2) {
      setError("Add a short note describing what was done.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const result = await updateDepartmentTaskStatus(
        task.id,
        status,
        status === "completed" ? note.trim() : undefined,
      );
      setNote("");
      setCompleting(false);
      onChanged(result.task, `Task ${task.id} marked ${taskStatusLabel(status).toLowerCase()}.`);
    } catch (err) {
      setError(err.message || "Could not update this task.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <article className="role-case-card task-card">
      <div className="role-case-heading">
        <div>
          <span className="section-overline">
            TASK {task.id} · CASE {task.case_id}
          </span>
          <h3 className="task-title">{task.title}</h3>
        </div>
        <div className="task-badges">
          <span className={`priority-badge priority-${task.priority}`}>
            {task.priority}
          </span>
          <span className={`status-badge task-status-${task.status}`}>
            {taskStatusLabel(task.status)}
          </span>
        </div>
      </div>

      <p className={task.is_overdue ? "task-due task-overdue" : "task-due"}>
        Due: {formatDueDate(task.due_date)}
        {task.is_overdue && " — overdue"}
      </p>

      <p className="task-assignee">
        {task.assigned_to_me
          ? "Assigned to you"
          : task.assigned_staff_id
            ? `Assigned to ${task.assigned_staff_name || "a colleague"}`
            : "Unclaimed — anyone in your department can take it"}
      </p>

      <h4>Instructions from the Coordinator</h4>
      <p className="task-instructions">{task.instructions}</p>

      <details className="task-case-details">
        <summary>Case information (minimum necessary)</summary>
        <p>
          Category: <strong>{caseInfo.category || "—"}</strong>
        </p>
        {caseInfo.title && <p>Case title: {caseInfo.title}</p>}
        {caseInfo.description && <p>{caseInfo.description}</p>}
        <p>
          Identity consent:{" "}
          <strong>
            {(caseInfo.department_consent?.level || "anonymous").replaceAll("_", " ")}
          </strong>
          {caseInfo.department_consent?.level === "restricted" &&
            ` — fields shared: ${(caseInfo.department_consent.fields || []).join(", ") || "none"}`}
        </p>
        {caseInfo.department_identity_consent && (
          <div>
            {caseInfo.student_name && <p>Student: {caseInfo.student_name}</p>}
            {caseInfo.student_email && <p>Email: {caseInfo.student_email}</p>}
            {caseInfo.student_phone && <p>Phone: {caseInfo.student_phone}</p>}
            {caseInfo.student_department && (
              <p>Student department: {caseInfo.student_department}</p>
            )}
          </div>
        )}
      </details>

      {task.status === "completed" && (
        <p className="task-completion">
          Completed {statusTimestamp(task.completed_at)}
          {task.completion_note ? ` — ${task.completion_note}` : ""}
        </p>
      )}

      {isOpen && (
        <div className="task-actions">
          {!task.assigned_staff_id && (
            <button
              type="button"
              className="secondary-button"
              disabled={saving}
              onClick={claim}
            >
              {saving ? "Saving..." : "Claim this task"}
            </button>
          )}
          {task.status === "assigned" && (
            <button
              type="button"
              className="secondary-button"
              disabled={saving}
              onClick={() => changeStatus("in_progress")}
            >
              {saving ? "Saving..." : "Start work"}
            </button>
          )}
          {!completing ? (
            <button
              type="button"
              className="button-primary"
              disabled={saving}
              onClick={() => setCompleting(true)}
            >
              Mark completed
            </button>
          ) : (
            <div className="task-complete-form">
              <label className="field-group">
                Completion note
                <textarea
                  aria-label={`Completion note for task ${task.id}`}
                  maxLength={2000}
                  value={note}
                  onChange={(event) => setNote(event.target.value)}
                />
              </label>
              <button
                type="button"
                className="button-primary"
                disabled={saving || note.trim().length < 2}
                onClick={() => changeStatus("completed")}
              >
                {saving ? "Saving..." : "Confirm completion"}
              </button>
              <button
                type="button"
                className="secondary-button"
                disabled={saving}
                onClick={() => {
                  setCompleting(false);
                  setNote("");
                  setError("");
                }}
              >
                Cancel
              </button>
            </div>
          )}
        </div>
      )}
      {error && (
        <p role="alert" className="field-error">
          {error}
        </p>
      )}

      {task.events?.length > 0 && (
        <details className="task-history">
          <summary>Task history</summary>
          <ol>
            {task.events.map((event) => (
              <li key={event.id}>
                <strong>{taskStatusLabel(event.to_status)}</strong>{" "}
                <span>{statusTimestamp(event.created_at)}</span>
                {event.actor_name ? ` · ${event.actor_name}` : ""}
                {event.note ? <p>{event.note}</p> : null}
              </li>
            ))}
          </ol>
        </details>
      )}
    </article>
  );
}

export default function DepartmentTaskDashboard({ department }) {
  const [tasks, setTasks] = useState([]);
  const [summary, setSummary] = useState(null);
  const [filter, setFilter] = useState("open");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        setLoading(true);
        setError("");
        const [taskData, summaryData] = await Promise.all([
          getDepartmentTasks(),
          getDepartmentTaskSummary(),
        ]);
        if (!cancelled) {
          setTasks(taskData);
          setSummary(summaryData);
        }
      } catch (err) {
        if (!cancelled) setError(err.message || "Could not load tasks.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  const handleChanged = useCallback((updatedTask, feedback) => {
    setTasks((current) =>
      current.map((item) => (item.id === updatedTask.id ? updatedTask : item)),
    );
    setMessage(feedback);
    // Counts are authoritative on the server; refresh them quietly.
    getDepartmentTaskSummary()
      .then(setSummary)
      .catch(() => {});
  }, []);

  const visible = useMemo(
    () => sortTasks(tasks.filter((task) => matchesFilter(task, filter))),
    [tasks, filter],
  );

  return (
    <section aria-labelledby="department-tasks-heading" className="task-dashboard">
      <h2 id="department-tasks-heading">Tasks for {department}</h2>

      {loading ? (
        <p role="status">Loading tasks...</p>
      ) : error ? (
        <div role="alert" className="workspace-error">
          <p>{error}</p>
          <button
            type="button"
            className="secondary-button"
            onClick={() => setReloadKey((key) => key + 1)}
          >
            Retry loading tasks
          </button>
        </div>
      ) : (
        <>
          {summary && (
            <div className="task-summary" aria-label="Task summary">
              {SUMMARY_TILES.map((tile) => (
                <div
                  key={tile.key}
                  className={`task-summary-tile${tile.key === "overdue" && summary.overdue ? " alert" : ""}`}
                >
                  <strong>{summary[tile.key] ?? 0}</strong>
                  <span>{tile.label}</span>
                </div>
              ))}
            </div>
          )}

          <div className="task-filters" role="group" aria-label="Filter tasks">
            {FILTERS.map((item) => (
              <button
                key={item.id}
                type="button"
                className={`task-filter${filter === item.id ? " active" : ""}`}
                aria-pressed={filter === item.id}
                onClick={() => setFilter(item.id)}
              >
                {item.label}
              </button>
            ))}
          </div>

          {message && (
            <p role="status" className="role-feedback">
              {message}
            </p>
          )}

          {visible.length === 0 ? (
            <p>
              {filter === "open"
                ? "No open tasks. New assignments from the Main Coordinator or a Department Coordinator will appear here."
                : "No tasks match this filter."}
            </p>
          ) : (
            <div className="role-case-list">
              {visible.map((task) => (
                <TaskCard key={task.id} task={task} onChanged={handleChanged} />
              ))}
            </div>
          )}
        </>
      )}
    </section>
  );
}
