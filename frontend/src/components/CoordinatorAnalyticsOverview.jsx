import { useMemo } from "react";
import {
  AlertCircle,
  ClipboardCheck,
  Clock3,
  FolderOpen,
  MessageSquareText,
} from "lucide-react";

const STATUS_LABELS = {
  submitted: "Submitted",
  awaiting_review: "Awaiting review",
  under_review: "Under review",
  in_review: "In review",
  in_progress: "In progress",
  resolved: "Resolved",
  closed: "Closed",
};

function formatLabel(value) {
  if (!value) return "Unspecified";

  return String(value)
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function CoordinatorMetric({ icon: Icon, label, value, hint }) {
  return (
    <article className="admin-metric-card">
      <div className="admin-metric-top">
        <span>{label}</span>
        <span className="admin-metric-icon">
          <Icon size={18} aria-hidden="true" />
        </span>
      </div>

      <strong>{value}</strong>
      <small>{hint}</small>
    </article>
  );
}

function CoordinatorBars({ title, caption, data }) {
  const max = Math.max(1, ...data.map((item) => item.value));

  return (
    <section className="admin-chart-panel" aria-label={title}>
      <div className="admin-chart-heading">
        <div>
          <h3>{title}</h3>
          <p>{caption}</p>
        </div>
      </div>

      {data.length ? (
        <div className="admin-bars">
          {data.map((item) => (
            <div key={item.label}>
              <div className="admin-bar-label">
                <span>{item.label}</span>
                <strong>{item.value}</strong>
              </div>

              <div
                className="admin-bar-track"
                role="img"
                aria-label={`${item.label}: ${item.value}`}
              >
                <span
                  style={{
                    width: `${(item.value / max) * 100}%`,
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="admin-empty-chart">
          No data available yet.
        </p>
      )}
    </section>
  );
}

export default function CoordinatorAnalyticsOverview({
  cases,
  tasks,
  requests,
}) {
  const summary = useMemo(() => {
    const openCases = cases.filter(
      (item) =>
        !["resolved", "closed"].includes(item.status)
    );

    const awaiting = cases.filter((item) =>
      ["submitted", "awaiting_review"].includes(item.status)
    );

    const overdue = tasks.filter(
      (item) => item.is_overdue
    );

    const openRequests = requests.filter(
      (item) => item.status === "open"
    );

    const counts = new Map();

    cases.forEach((item) => {
      const label =
        STATUS_LABELS[item.status] || formatLabel(item.status);

      counts.set(label, (counts.get(label) || 0) + 1);
    });

    const statuses = [...counts.entries()]
      .map(([label, value]) => ({ label, value }))
      .sort((a, b) => b.value - a.value);

    return {
      openCases,
      awaiting,
      overdue,
      openRequests,
      statuses,
    };
  }, [cases, tasks, requests]);

  const attentionItems = [
    ...summary.awaiting.slice(0, 3).map((item) => ({
      key: `case-${item.id}`,
      title: `Case ${item.id} awaiting review`,
      detail: item.category || "Support case",
    })),

    ...summary.overdue.slice(0, 3).map((item) => ({
      key: `task-${item.id}`,
      title: item.title || `Task for case ${item.case_id}`,
      detail: `Overdue · ${item.department || "Department task"}`,
    })),

    ...summary.openRequests.slice(0, 3).map((item) => ({
      key: `request-${item.id}`,
      title: `Request for case ${item.case_id}`,
      detail:
        item.request_type === "closure_request"
          ? "Closure request"
          : "Department update",
    })),
  ].slice(0, 6);

  return (
    <section
      className="admin-analytics"
      aria-labelledby="coordinator-analytics-title"
    >
      <div className="admin-section-heading">
        <div>
          <span className="section-overline">
            COORDINATION OVERVIEW
          </span>

          <h2 id="coordinator-analytics-title">
            Your cases, in focus
          </h2>

          <p>
            A quick view of case progress, department tasks,
            and items that may need your attention.
          </p>
        </div>

        <span className="admin-data-note">
          <ClipboardCheck size={14} aria-hidden="true" />
          Coordinator workspace
        </span>
      </div>

      <div className="admin-metrics-grid">
        <CoordinatorMetric
          icon={FolderOpen}
          label="Cases assigned"
          value={cases.length}
          hint="Cases returned for your account"
        />

        <CoordinatorMetric
          icon={Clock3}
          label="Awaiting review"
          value={summary.awaiting.length}
          hint="Submitted and awaiting-review cases"
        />

        <CoordinatorMetric
          icon={AlertCircle}
          label="Overdue tasks"
          value={summary.overdue.length}
          hint="Flagged overdue by the backend"
        />

        <CoordinatorMetric
          icon={MessageSquareText}
          label="Open requests"
          value={summary.openRequests.length}
          hint="Department updates and requests"
        />
      </div>

      <div className="admin-charts-grid">
        <CoordinatorBars
          title="Case progress"
          caption="Your current case status distribution"
          data={summary.statuses}
        />

        <section
          className="admin-chart-panel coordinator-attention"
          aria-labelledby="coordinator-attention-title"
        >
          <div className="admin-chart-heading">
            <div>
              <h3 id="coordinator-attention-title">
                Needs attention
              </h3>
              <p>Items to review or follow up on</p>
            </div>
          </div>

          {attentionItems.length ? (
            <ul className="coordinator-attention-list">
              {attentionItems.map((item) => (
                <li key={item.key}>
                  <span
                    className="attention-marker"
                    aria-hidden="true"
                  />

                  <span>
                    <strong>{item.title}</strong>
                    <small>{item.detail}</small>
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="admin-empty-chart">
              Nothing is currently flagged for attention.
            </p>
          )}
        </section>
      </div>

      <p className="admin-privacy-note">
        <span aria-hidden="true">✳</span>{" "}
        This dashboard reflects only cases and tasks available
        to your coordinator account. Use the case workspace
        below to review details and take action.
      </p>
    </section>
  );
}