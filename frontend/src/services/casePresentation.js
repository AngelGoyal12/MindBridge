const statusLabels = {
  submitted: "Submitted",
  awaiting_review: "Awaiting review",
  open: "Submitted",
  in_review: "In review",
  under_review: "In review",
  in_progress: "In progress",
  resolved: "Resolved",
  closed: "Closed",
};

export function normalizeCaseStatus(status) {
  if (typeof status !== "string" || !status.trim()) return "unknown";
  return status.trim().toLowerCase().replaceAll("-", "_").replaceAll(" ", "_");
}

export function caseStatusLabel(status) {
  const normalized = normalizeCaseStatus(status);
  return (
    statusLabels[normalized] ??
    normalized.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase())
  );
}

export function formatTimestamp(value, options = {}) {
  if (!value) return "Date unavailable";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Date unavailable";
  return new Intl.DateTimeFormat("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
    ...options,
  }).format(date);
}

export function statusTimestamp(value) {
  return formatTimestamp(value, { hour: "2-digit", minute: "2-digit" });
}

const taskStatusLabels = {
  assigned: "Assigned",
  in_progress: "In progress",
  completed: "Completed",
  cancelled: "Cancelled",
};

export function taskStatusLabel(status) {
  return taskStatusLabels[status] ?? caseStatusLabel(status);
}

export function formatDueDate(value) {
  if (!value) return "No due date";
  // Due dates are plain calendar days (YYYY-MM-DD); avoid timezone shifts.
  const [year, month, day] = String(value).split("-").map(Number);
  const date = new Date(year, (month || 1) - 1, day || 1);
  if (Number.isNaN(date.getTime())) return "No due date";
  return new Intl.DateTimeFormat("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(date);
}

export function todayInputValue() {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}

// What people see. The internal role values (admin, coordinator,
// department_staff) never change; only these labels do.
const roleLabels = {
  student: "Student",
  admin: "Main Coordinator",
  coordinator: "Department Coordinator",
  department_staff: "Department Staff",
};

export function roleLabel(role) {
  return roleLabels[role] ?? String(role || "").replaceAll("_", " ");
}
