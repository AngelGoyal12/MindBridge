
import { useMemo } from "react";
import {
  Activity,
  ClipboardList,
  Clock3,
  Layers3,
  CheckCircle2,
  TrendingUp,
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

const CHART_COLORS = [
  "#789B91",
  "#D6A66B",
  "#8297B8",
  "#C58C91",
  "#A99AC8",
  "#8DAA73",
  "#B6A18C",
];

function labelFor(value) {
  if (!value) return "Unassigned";

  return String(value)
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function MetricCard({ icon: Icon, label, value, note }) {
  return (
    <article className="admin-metric-card">
      <div className="admin-metric-top">
        <span>{label}</span>

        <span className="admin-metric-icon">
          <Icon size={18} aria-hidden="true" />
        </span>
      </div>

      <strong>{value}</strong>
      <small>{note}</small>
    </article>
  );
}

function HorizontalBars({
  title,
  description,
  items,
  emptyText,
}) {
  const max = Math.max(1, ...items.map((item) => item.value));

  return (
    <section className="admin-chart-panel" aria-label={title}>
      <div className="admin-chart-heading">
        <div>
          <h3>{title}</h3>
          <p>{description}</p>
        </div>
      </div>

      {items.length ? (
        <div className="admin-bars">
          {items.map((item, index) => (
            <div className="admin-bar-row" key={item.label}>
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
                    background: CHART_COLORS[index % CHART_COLORS.length],
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="admin-empty-chart">{emptyText}</p>
      )}
    </section>
  );
}

function DonutChart({ items }) {
  const total = items.reduce((sum, item) => sum + item.value, 0);
  const radius = 48;
  const circumference = 2 * Math.PI * radius;

  let offset = 0;

  return (
    <section className="admin-chart-panel" aria-label="Case status distribution">
      <div className="admin-chart-heading">
        <div>
          <h3>Case status distribution</h3>
          <p>How cases are progressing</p>
        </div>
      </div>

      {total > 0 ? (
        <div style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexWrap: "wrap",
          gap: "24px",
          padding: "12px 0",
        }}>
          <div style={{ width: "150px", height: "150px", position: "relative" }}>
            <svg viewBox="0 0 120 120" width="100%" role="img"
              aria-label={`Donut chart showing ${total} cases`}>
              <circle
                cx="60"
                cy="60"
                r={radius}
                fill="none"
                stroke="var(--color-border)"
                strokeWidth="15"
              />

              {items.map((item, index) => {
                const segment = (item.value / total) * circumference;
                const currentOffset = offset;
                offset += segment;

                return (
                  <circle
                    key={item.label}
                    cx="60"
                    cy="60"
                    r={radius}
                    fill="none"
                    stroke={CHART_COLORS[index % CHART_COLORS.length]}
                    strokeWidth="15"
                    strokeDasharray={`${segment} ${circumference - segment}`}
                    strokeDashoffset={-currentOffset}
                    transform="rotate(-90 60 60)"
                  />
                );
              })}
            </svg>

            <div style={{
              position: "absolute",
              inset: 0,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              pointerEvents: "none",
            }}>
              <strong style={{ fontSize: "25px", color: "var(--color-text)" }}>
                {total}
              </strong>
              <span style={{ fontSize: "10px", color: "var(--color-muted)" }}>
                Total cases
              </span>
            </div>
          </div>

          <div style={{
            display: "grid",
            gap: "11px",
            minWidth: "145px",
          }}>
            {items.map((item, index) => (
              <div key={item.label} style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                fontSize: "12px",
              }}>
                <span style={{
                  width: "9px",
                  height: "9px",
                  borderRadius: "50%",
                  flexShrink: 0,
                  background: CHART_COLORS[index % CHART_COLORS.length],
                }} />

                <span style={{ color: "var(--color-muted)", flex: 1 }}>
                  {item.label}
                </span>

                <strong>{item.value}</strong>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <p className="admin-empty-chart">No case status data is available yet.</p>
      )}
    </section>
  );
}

function SubmissionTrend({ items }) {
  const max = Math.max(1, ...items.map((item) => item.value));

  return (
    <section className="admin-chart-panel" aria-label="Case submission trend">
      <div className="admin-chart-heading">
        <div>
          <h3>Case submissions over time</h3>
          <p>Cases grouped by their creation date</p>
        </div>
      </div>

      {items.length ? (
        <div style={{
          display: "flex",
          alignItems: "flex-end",
          gap: "12px",
          height: "175px",
          padding: "15px 4px 0",
          overflowX: "auto",
        }}>
          {items.map((item) => (
            <div key={item.label} style={{
              flex: "1 0 38px",
              minWidth: "38px",
              height: "100%",
              display: "flex",
              flexDirection: "column",
              justifyContent: "flex-end",
              alignItems: "center",
              gap: "8px",
            }}>
              <strong style={{ fontSize: "11px" }}>
                {item.value}
              </strong>

              <div
                title={`${item.label}: ${item.value} cases`}
                style={{
                  width: "min(100%, 34px)",
                  height: `${Math.max(5, (item.value / max) * 105)}px`,
                  background: "#789B91",
                  borderRadius: "5px 5px 0 0",
                  transition: "height 200ms ease",
                }}
              />

              <span style={{
                fontSize: "10px",
                color: "var(--color-muted)",
                whiteSpace: "nowrap",
              }}>
                {item.label}
              </span>
            </div>
          ))}
        </div>
      ) : (
        <p className="admin-empty-chart">No submission date data is available yet.</p>
      )}
    </section>
  );
}

export default function AdminAnalyticsOverview({
  cases = [],
  tasks = [],
}) {
  const analytics = useMemo(() => {
    const safeCases = Array.isArray(cases) ? cases : [];
    const safeTasks = Array.isArray(tasks) ? tasks : [];

    const countBy = (records, key, formatter = labelFor) => {
      const counts = new Map();

      records.forEach((record) => {
        const label = formatter(record[key]);

        counts.set(label, (counts.get(label) || 0) + 1);
      });

      return [...counts.entries()]
        .map(([label, value]) => ({ label, value }))
        .sort((a, b) => b.value - a.value)
        .slice(0, 7);
    };

    const openCases = safeCases.filter(
      (item) => !["resolved", "closed"].includes(item.status)
    ).length;

    const completedTasks = safeTasks.filter(
      (item) => item.status === "completed"
    ).length;

    const overdueTasks = safeTasks.filter(
      (item) => item.is_overdue
    ).length;

    const dates = new Map();

    safeCases.forEach((item) => {
      if (!item.created_at) return;

      const date = item.created_at.slice(0, 10);

      dates.set(date, (dates.get(date) || 0) + 1);
    });

    const submissionTrend = [...dates.entries()]
      .sort(([a], [b]) => a.localeCompare(b))
      .slice(-7)
      .map(([date, value]) => ({
        label: new Date(`${date}T00:00:00`).toLocaleDateString(
          "en-IN",
          { day: "2-digit", month: "short" }
        ),
        value,
      }));

    return {
      openCases,
      completedTasks,
      overdueTasks,

      caseStatuses: countBy(
        safeCases,
        "status",
        (status) => STATUS_LABELS[status] || labelFor(status)
      ),

      categories: countBy(safeCases, "category"),

      departments: countBy(safeCases, "department"),

      taskDepartments: countBy(safeTasks, "department"),

      submissionTrend,
    };
  }, [cases, tasks]);

  return (
    <section
      className="admin-analytics"
      aria-labelledby="admin-analytics-title"
    >
      <div className="admin-section-heading">
        <div>
          <span className="section-overline">SYSTEM OVERVIEW</span>

          <h2 id="admin-analytics-title">
            Support at a glance
          </h2>

          <p>
            Operational insights from the cases and tasks
            currently available to your account.
          </p>
        </div>

        <span className="admin-data-note">
          <Activity size={14} aria-hidden="true" />
          Live workspace data
        </span>
      </div>

      <div className="admin-metrics-grid">
        <MetricCard
          icon={ClipboardList}
          label="Cases in view"
          value={cases.length}
          note="Records returned by the cases API"
        />

        <MetricCard
          icon={Layers3}
          label="Open cases"
          value={analytics.openCases}
          note="Not yet resolved or closed"
        />

        <MetricCard
          icon={CheckCircle2}
          label="Completed tasks"
          value={analytics.completedTasks}
          note={`Out of ${tasks.length} tasks in view`}
        />

        <MetricCard
          icon={Clock3}
          label="Overdue tasks"
          value={analytics.overdueTasks}
          note="Based on backend overdue flags"
        />
      </div>

      <div className="admin-charts-grid">
        <DonutChart items={analytics.caseStatuses} />

        <SubmissionTrend items={analytics.submissionTrend} />

        <HorizontalBars
          title="Cases by department"
          description="Cases currently assigned to each department"
          items={analytics.departments}
          emptyText="No department assignments are available yet."
        />

        <HorizontalBars
          title="Cases by category"
          description="Most common support categories"
          items={analytics.categories}
          emptyText="Category data will appear when cases are available."
        />

        <HorizontalBars
          title="Tasks by department"
          description="Tasks currently associated with each department"
          items={analytics.taskDepartments}
          emptyText="No department task data is available yet."
        />
      </div>

      <p className="admin-privacy-note">
        <span aria-hidden="true">✳</span>{" "}
        This overview uses the redacted case and task data
        provided to the Admin role. It does not display
        student identity or contact details.
      </p>
    </section>
  );
}
