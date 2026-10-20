import { Check, Clock3 } from "lucide-react";

import {
  caseStatusLabel,
  normalizeCaseStatus,
  statusTimestamp,
} from "../services/casePresentation";

function matchingUpdate(updates, predicate) {
  return [...updates].reverse().find((update) => predicate(update));
}

function statusUpdate(updates, phrase) {
  return matchingUpdate(
    updates,
    (update) =>
      update.type === "status" &&
      `${update.title || ""} ${update.message || ""}`
        .toLowerCase()
        .includes(phrase),
  );
}

export default function CaseProgressTracker({ caseItem }) {
  const updates = Array.isArray(caseItem.progress_updates)
    ? caseItem.progress_updates
    : [];
  const status = normalizeCaseStatus(caseItem.status);
  const reviewUpdate = statusUpdate(updates, "review");
  const progressUpdate = statusUpdate(updates, "progress");
  const closureUpdate = matchingUpdate(
    updates,
    (update) => update.type === "closure",
  );
  const assignmentUpdate = matchingUpdate(
    updates,
    (update) => update.type === "assignment",
  );
  const routingUpdate = matchingUpdate(
    updates,
    (update) => update.type === "routing",
  );

  const milestones = [
    {
      title: "Submitted",
      update: matchingUpdate(
        updates,
        (update) => update.title?.toLowerCase() === "case submitted",
      ),
      date: caseItem.created_at,
      complete: true,
    },
    {
      title: "Coordinator Assigned",
      update: assignmentUpdate,
      complete:
        Boolean(assignmentUpdate) ||
        ["in_review", "under_review", "in_progress", "resolved", "closed"].includes(status),
    },
    {
      title: "In Review",
      update: reviewUpdate,
      complete:
        Boolean(reviewUpdate) ||
        ["in_review", "under_review", "in_progress", "resolved", "closed"].includes(status),
    },
    {
      title: "Department Routed",
      update: routingUpdate,
      complete: Boolean(caseItem.department || routingUpdate),
    },
    {
      title: "In Progress",
      update: progressUpdate,
      complete:
        Boolean(progressUpdate) ||
        ["in_progress", "resolved", "closed"].includes(status),
    },
    {
      title: "Closed",
      update: closureUpdate,
      complete:
        ["resolved", "closed"].includes(status) || Boolean(closureUpdate),
    },
  ];
  const currentIndex = milestones.findIndex((milestone) => !milestone.complete);

  return (
    <section className="case-progress-tracker" aria-label="Case progress">
      <div className="case-progress-track">
        {milestones.map((milestone, index) => {
          const current = index === currentIndex;
          const date = milestone.update?.created_at || milestone.date;
          return (
            <div
              className={`progress-step${milestone.complete ? " completed" : ""}${current ? " current" : ""}`}
              key={milestone.title}
              aria-current={current ? "step" : undefined}
            >
              <div className="progress-step-marker" aria-hidden="true">
                {milestone.complete ? (
                  <Check size={14} />
                ) : current ? (
                  <Clock3 size={14} />
                ) : (
                  <span>{String(index + 1).padStart(2, "0")}</span>
                )}
              </div>
              <div className="progress-step-copy">
                <strong>{milestone.title}</strong>
                <span>
                  {date
                    ? statusTimestamp(date)
                    : milestone.complete
                      ? "Date unavailable"
                      : "Not recorded"}
                </span>
                {milestone.update?.message && <p>{milestone.update.message}</p>}
              </div>
            </div>
          );
        })}
      </div>

      <div className="case-progress-current" aria-live="polite">
        Current case status: <strong>{caseStatusLabel(caseItem.status)}</strong>
        {" · "}Department: <strong>{caseItem.department || "Not yet routed"}</strong>
      </div>

      {updates.length > 0 && (
        <section className="case-progress-updates" aria-label="Recorded follow-ups and updates">
          <h3>Recorded updates</h3>
          <ol>
            {updates.map((update) => (
              <li key={update.id}>
                <div className="case-progress-update-heading">
                  <strong>{update.title}</strong>
                  <time dateTime={update.created_at || undefined}>
                    {statusTimestamp(update.created_at)}
                  </time>
                </div>
                <p>{update.message}</p>
              </li>
            ))}
          </ol>
        </section>
      )}
    </section>
  );
}
