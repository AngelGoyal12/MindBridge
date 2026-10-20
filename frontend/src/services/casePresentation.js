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
