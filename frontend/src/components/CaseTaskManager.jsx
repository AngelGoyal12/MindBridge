import { useEffect, useState } from "react";

import {
  assignTaskToStaff,
  createAdminDepartmentTask,
  createDepartmentTask,
  getDepartmentStaff,
  reviewAdminTask,
  reviewDepartmentTask,
} from "../services/caseService";
import {
  formatDueDate,
  statusTimestamp,
  taskStatusLabel,
  todayInputValue,
} from "../services/casePresentation";

const EMPTY_FORM = {
  department: "",
  title: "",
  instructions: "",
  priority: "normal",
  due_date: "",
  assigned_staff_id: "",
};

// Loads the staff of one department so a task can be handed to a person.
function useDepartmentStaff(department, enabled) {
  const [state, setState] = useState({ key: "", staff: [], error: "" });
  const key = enabled && department ? department : "";

  useEffect(() => {
    if (!key) return undefined;
    let cancelled = false;
    getDepartmentStaff(key)
      .then((staff) => {
        if (!cancelled) setState({ key, staff, error: "" });
      })
      .catch((err) => {
        if (!cancelled) {
          setState({
            key,
            staff: [],
            error: err.message || "Could not load department staff.",
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [key]);

  const ready = Boolean(key) && state.key === key;
  return {
    staff: ready ? state.staff : [],
    error: ready ? state.error : "",
    loading: Boolean(key) && !ready,
  };
}

function StaffAssigner({ task, asAdmin, onChanged }) {
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState(
    task.assigned_staff_id ? String(task.assigned_staff_id) : "",
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const { staff, error: loadError, loading } = useDepartmentStaff(
    task.department,
    open,
  );

  async function save(staffId) {
    if (saving) return;
    setSaving(true);
    setError("");
    try {
      const result = await assignTaskToStaff(task.id, staffId, { asAdmin });
      setOpen(false);
      onChanged(
        result.task,
        result.task.assigned_staff_name
          ? `Task ${task.id} assigned to ${result.task.assigned_staff_name}.`
          : `Task ${task.id} returned to the ${task.department} pool.`,
      );
    } catch (err) {
      setError(err.message || "Could not update the assignment.");
    } finally {
      setSaving(false);
    }
  }

  if (!open) {
    return (
      <button
        type="button"
        className="secondary-button"
        onClick={() => setOpen(true)}
      >
        {task.assigned_staff_id ? "Reassign staff" : "Assign to staff"}
      </button>
    );
  }

  return (
    <div className="task-complete-form">
      <label className="field-group">
        Staff member in {task.department}
        <select
          aria-label={`Staff member for task ${task.id}`}
          value={selected}
          disabled={saving || loading}
          onChange={(event) => setSelected(event.target.value)}
        >
          <option value="">Select a staff member</option>
          {staff.map((member) => (
            <option key={member.id} value={member.id}>
              {member.name}
            </option>
          ))}
        </select>
      </label>
      <button
        type="button"
        className="button-primary"
        disabled={saving || loading || !selected}
        onClick={() => save(Number(selected))}
      >
        {saving ? "Saving..." : "Assign"}
      </button>
      {task.assigned_staff_id && (
        <button
          type="button"
          className="secondary-button"
          disabled={saving}
          onClick={() => save(null)}
        >
          Return to department pool
        </button>
      )}
      <button
        type="button"
        className="secondary-button"
        disabled={saving}
        onClick={() => setOpen(false)}
      >
        Cancel
      </button>
      {(loadError || error) && (
        <p role="alert" className="field-error">
          {error || loadError}
        </p>
      )}
    </div>
  );
}

function TaskItem({ task, caseClosed, onChanged, asAdmin }) {
  const [reopening, setReopening] = useState(false);
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function review(action) {
    if (saving) return;
    if (action === "cancel" && !window.confirm(`Cancel task ${task.id}?`)) return;
    if (action === "reopen" && note.trim().length < 2) {
      setError("Explain what still needs to be done.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const reviewTask = asAdmin ? reviewAdminTask : reviewDepartmentTask;
      const result = await reviewTask(
        task.id,
        action,
        action === "reopen" ? note.trim() : undefined,
      );
      setNote("");
      setReopening(false);
      onChanged(
        result.task,
        action === "cancel" ? `Task ${task.id} cancelled.` : `Task ${task.id} reopened.`,
      );
    } catch (err) {
      setError(err.message || "Could not update this task.");
    } finally {
      setSaving(false);
    }
  }

  const isOpen = task.status === "assigned" || task.status === "in_progress";

  return (
    <li className="case-task-item">
      <div className="case-task-heading">
        <strong>{task.title}</strong>
        <span className={`status-badge task-status-${task.status}`}>
          {taskStatusLabel(task.status)}
        </span>
      </div>
      <p>
        {task.department} · <span className={`priority-badge priority-${task.priority}`}>{task.priority}</span>
        {" · "}
        <span className={task.is_overdue ? "task-overdue" : undefined}>
          Due: {formatDueDate(task.due_date)}
          {task.is_overdue && " — overdue"}
        </span>
      </p>
      {isOpen && (
        <p className="task-assignee">
          {task.assigned_staff_name
            ? `Assigned to ${task.assigned_staff_name}`
            : "Not yet assigned to a staff member (department pool)"}
        </p>
      )}
      {task.status === "completed" && (
        <p className="task-completion">
          Completed {statusTimestamp(task.completed_at)}
          {task.completion_note ? ` — ${task.completion_note}` : ""}
        </p>
      )}
      {task.events?.length > 0 && (
        <details className="task-history">
          <summary>History ({task.events.length})</summary>
          <p>{task.instructions}</p>
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
      {isOpen && (
        <StaffAssigner task={task} asAdmin={asAdmin} onChanged={onChanged} />
      )}
      {isOpen && (
        <button
          type="button"
          className="secondary-button"
          disabled={saving}
          onClick={() => review("cancel")}
        >
          Cancel task
        </button>
      )}
      {task.status === "completed" && !caseClosed && !reopening && (
        <button
          type="button"
          className="secondary-button"
          onClick={() => setReopening(true)}
        >
          Reopen task
        </button>
      )}
      {reopening && (
        <div className="task-complete-form">
          <label className="field-group">
            What still needs to be done?
            <textarea
              aria-label={`Reason for reopening task ${task.id}`}
              maxLength={2000}
              value={note}
              onChange={(event) => setNote(event.target.value)}
            />
          </label>
          <button
            type="button"
            className="button-primary"
            disabled={saving || note.trim().length < 2}
            onClick={() => review("reopen")}
          >
            {saving ? "Saving..." : "Confirm reopen"}
          </button>
          <button
            type="button"
            className="secondary-button"
            disabled={saving}
            onClick={() => {
              setReopening(false);
              setNote("");
              setError("");
            }}
          >
            Cancel
          </button>
        </div>
      )}
      {error && (
        <p role="alert" className="field-error">
          {error}
        </p>
      )}
    </li>
  );
}

export default function CaseTaskManager({
  caseItem,
  departments,
  tasks,
  onTaskSaved,
  onFeedback,
  asAdmin = false,
}) {
  const [form, setForm] = useState({
    ...EMPTY_FORM,
    department: caseItem.department || "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const { staff: departmentStaff } = useDepartmentStaff(form.department, true);
  const caseClosed = caseItem.status === "closed";
  const openCount = tasks.filter(
    (task) => task.status === "assigned" || task.status === "in_progress",
  ).length;
  const canSubmit =
    form.department &&
    form.title.trim().length >= 3 &&
    form.instructions.trim().length >= 5;

  function setField(field, value) {
    setForm((current) => ({
      ...current,
      [field]: value,
      // A staff member only makes sense within the chosen department.
      ...(field === "department" ? { assigned_staff_id: "" } : {}),
    }));
  }

  async function submit(event) {
    event.preventDefault();
    if (saving || !canSubmit) return;
    setSaving(true);
    setError("");
    try {
      const create = asAdmin ? createAdminDepartmentTask : createDepartmentTask;
      const result = await create(caseItem.id, {
        department: form.department,
        title: form.title.trim(),
        instructions: form.instructions.trim(),
        priority: form.priority,
        ...(form.due_date ? { due_date: form.due_date } : {}),
        ...(form.assigned_staff_id
          ? { assigned_staff_id: Number(form.assigned_staff_id) }
          : {}),
      });
      onTaskSaved(result.task);
      onFeedback(`Task assigned to ${result.task.department} for case ${caseItem.id}.`);
      setForm({ ...EMPTY_FORM, department: form.department });
    } catch (err) {
      setError(err.message || "Could not assign this task.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section
      className="case-task-manager"
      aria-label={`Department tasks for case ${caseItem.id}`}
    >
      <h3>Department tasks</h3>
      <p>
        {tasks.length === 0
          ? "No tasks assigned yet."
          : `${tasks.length} task(s), ${openCount} open.`}
        {openCount > 0 && " Open tasks must be completed or cancelled before the case can be closed."}
      </p>

      {tasks.length > 0 && (
        <ul className="case-task-list">
          {tasks.map((task) => (
            <TaskItem
              key={task.id}
              task={task}
              caseClosed={caseClosed}
              asAdmin={asAdmin}
              onChanged={(updated, feedback) => {
                onTaskSaved(updated);
                onFeedback(feedback);
              }}
            />
          ))}
        </ul>
      )}

      {caseClosed ? (
        <p>This case is closed; new tasks cannot be assigned.</p>
      ) : (
        <details className="case-task-form">
          <summary>
            {asAdmin
              ? "Send a new task to a department"
              : "Assign a new task to a department"}
          </summary>
          <form onSubmit={submit}>
            <label className="field-group">
              Department
              <select
                value={form.department}
                onChange={(event) => setField("department", event.target.value)}
              >
                <option value="">Select a department</option>
                {departments.map((department) => (
                  <option key={department} value={department}>
                    {department}
                  </option>
                ))}
              </select>
            </label>
            {form.department && (
              <label className="field-group">
                Staff member (optional)
                <select
                  value={form.assigned_staff_id}
                  onChange={(event) =>
                    setField("assigned_staff_id", event.target.value)
                  }
                >
                  <option value="">Leave in the department pool</option>
                  {departmentStaff.map((member) => (
                    <option key={member.id} value={member.id}>
                      {member.name}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <label className="field-group">
              Task title
              <input
                type="text"
                minLength={3}
                maxLength={150}
                value={form.title}
                onChange={(event) => setField("title", event.target.value)}
              />
            </label>
            <label className="field-group">
              Instructions
              <textarea
                minLength={5}
                maxLength={2000}
                value={form.instructions}
                onChange={(event) => setField("instructions", event.target.value)}
              />
            </label>
            <p className="task-form-hint">
              Share only what the department needs to act. Student identity is
              released according to the student&apos;s consent.
            </p>
            <label className="field-group">
              Priority
              <select
                value={form.priority}
                onChange={(event) => setField("priority", event.target.value)}
              >
                <option value="low">Low</option>
                <option value="normal">Normal</option>
                <option value="high">High</option>
                <option value="urgent">Urgent</option>
              </select>
            </label>
            <label className="field-group">
              Due date (optional)
              <input
                type="date"
                min={todayInputValue()}
                value={form.due_date}
                onChange={(event) => setField("due_date", event.target.value)}
              />
            </label>
            {!departments.length && (
              <p>No department teams have been provisioned yet.</p>
            )}
            <button
              type="submit"
              className="button-primary"
              disabled={saving || !canSubmit}
            >
              {saving ? "Sending..." : asAdmin ? "Send task" : "Assign task"}
            </button>
            {error && (
              <p role="alert" className="field-error">
                {error}
              </p>
            )}
          </form>
        </details>
      )}
    </section>
  );
}
