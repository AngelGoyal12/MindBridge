
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Bell,
  CheckCheck,
  Clock3,
  MessageCircle,
  ShieldCheck,
} from "lucide-react";
import { getMyNotifications } from "../services/authService";

const STORAGE_KEY = "mindbridge_notifications_read";

function readReadStatus() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
  } catch {
    return {};
  }
}

function getDateParts(dateValue) {
  if (!dateValue) {
    return { date: "Date unavailable", time: "" };
  }

  const date = new Date(dateValue);

  if (Number.isNaN(date.getTime())) {
    return { date: "Date unavailable", time: "" };
  }

  return {
    date: date.toLocaleDateString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    }),
    time: date.toLocaleTimeString("en-IN", {
      hour: "2-digit",
      minute: "2-digit",
    }),
  };
}

function createNotifications(items, readStatus) {
  return items
    .map((item) => {
      const id = item.id;
      const { date, time } = getDateParts(
        item.created_at
      );

      return {
        id,
        type: "status",
        title: "Your concern has been submitted",
        message: `"${item.title}" has been recorded. Current status: ${
          {
            submitted: "Submitted",
            in_review: "Under review",
            in_progress: "In progress",
            resolved: "Resolved",
            closed: "Closed",
          }[item.status] ?? item.status ?? "Submitted"
        }.`,
        caseId: item.case_id,
        date,
        time,
        icon: Clock3,
        unread: !readStatus[id],
        sortDate: new Date(
          item.created_at ?? 0
        ).getTime(),
      };
    })
    .sort((a, b) => b.sortDate - a.sortDate);
}

function NotificationCard({ notification, onMarkRead }) {
  const Icon = notification.icon;

  return (
    <article
      className={`notification-card ${
        notification.unread ? "is-unread" : ""
      }`}
    >
      <div className="notification-icon">
        <Icon size={20} aria-hidden="true" />
      </div>

      <div className="notification-content">
        <div className="notification-title-row">
          <h3>{notification.title}</h3>

          {notification.unread && (
            <span
              className="notification-unread-dot"
              aria-label="Unread"
            />
          )}
        </div>

        <p>{notification.message}</p>

        <div className="notification-meta">
          <span>{notification.date}</span>

          {notification.time && (
            <>
              <span aria-hidden="true">·</span>
              <span>{notification.time}</span>
            </>
          )}
        </div>

        <div className="notification-actions">
          <Link to={`/cases/${notification.caseId}`}>
            View case
          </Link>

          {notification.unread && (
            <button
              type="button"
              className="notification-mark-read"
              onClick={() => onMarkRead(notification.id)}
            >
              Mark as read
            </button>
          )}
        </div>
      </div>
    </article>
  );
}

export default function Notifications() {
  const [items, setItems] = useState([]);
  const [readStatus, setReadStatus] = useState(readReadStatus);
  const [filter, setFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function loadNotifications() {
      try {
        setLoading(true);
        setError("");

        const data = await getMyNotifications();

        if (!cancelled) {
          setItems(Array.isArray(data) ? data : []);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message || "Could not load notifications.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadNotifications();

    return () => {
      cancelled = true;
    };
  }, []);

  const notifications = createNotifications(items, readStatus);

  const unreadCount = notifications.filter(
    (notification) => notification.unread
  ).length;

  const visibleNotifications = notifications.filter((notification) =>
    filter === "unread" ? notification.unread : true
  );

  function saveReadStatus(updatedStatus) {
    try {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify(updatedStatus)
      );

      setReadStatus(updatedStatus);
    } catch (err) {
      console.error("Could not save read status:", err);
      setError("Could not save notification read status.");
    }
  }

  function markAsRead(notificationId) {
    saveReadStatus({
      ...readStatus,
      [notificationId]: true,
    });
  }

  function markAllAsRead() {
    const updatedStatus = { ...readStatus };

    notifications.forEach((notification) => {
      updatedStatus[notification.id] = true;
    });

    saveReadStatus(updatedStatus);
  }

  return (
    <main className="page-container notifications-page">
      <Link to="/dashboard" className="back-link">
        ← Back to dashboard
      </Link>

      <section className="notifications-heading">
        <div>
          <span className="eyebrow">YOUR UPDATES</span>
          <h1>Notifications</h1>
          <p>
            Updates generated from your submitted concerns.
          </p>
        </div>

        <div className="notifications-heading-icon">
          <Bell size={25} aria-hidden="true" />

          {unreadCount > 0 && (
            <span className="notification-count">
              {unreadCount}
            </span>
          )}
        </div>
      </section>

      <section className="notifications-panel">
        <div className="notifications-toolbar">
          <div>
            <h2>Your activity</h2>
            <p>
              {loading
                ? "Loading your notifications..."
                : error
                  ? "Notifications could not be loaded."
                  : unreadCount === 0
                    ? "You're all caught up."
                    : `You have ${unreadCount} unread ${
                        unreadCount === 1
                          ? "notification"
                          : "notifications"
                      }.`}
            </p>
          </div>

          {!loading && !error && unreadCount > 0 && (
            <button
              type="button"
              className="notification-mark-all"
              onClick={markAllAsRead}
            >
              <CheckCheck size={16} aria-hidden="true" />
              Mark all as read
            </button>
          )}
        </div>

        <div
          className="notification-filters"
          aria-label="Filter notifications"
        >
          <button
            type="button"
            className={filter === "all" ? "active" : ""}
            aria-pressed={filter === "all"}
            onClick={() => setFilter("all")}
          >
            All ({notifications.length})
          </button>

          <button
            type="button"
            className={filter === "unread" ? "active" : ""}
            aria-pressed={filter === "unread"}
            onClick={() => setFilter("unread")}
          >
            Unread ({unreadCount})
          </button>
        </div>

        <div className="notifications-list">
          {loading ? (
            <p role="status">Fetching cases from the server...</p>
          ) : error ? (
            <div role="alert" className="notifications-empty">
              <MessageCircle size={25} aria-hidden="true" />
              <h3>Couldn't load notifications</h3>
              <p>{error}</p>
              <button
                type="button"
                onClick={() => window.location.reload()}
              >
                Try again
              </button>
            </div>
          ) : visibleNotifications.length > 0 ? (
            visibleNotifications.map((notification) => (
              <NotificationCard
                key={notification.id}
                notification={notification}
                onMarkRead={markAsRead}
              />
            ))
          ) : (
            <div className="notifications-empty">
              <MessageCircle size={25} aria-hidden="true" />
              <h3>
                {filter === "unread"
                  ? "No unread notifications"
                  : "No notifications yet"}
              </h3>
              <p>
                {filter === "unread"
                  ? "You're all caught up."
                  : "Notifications will appear here after you submit a concern."}
              </p>
            </div>
          )}
        </div>

        <p className="notification-demo-note">
          <ShieldCheck size={15} aria-hidden="true" />
          Notifications are retrieved from your own cases through the
          authenticated backend. Read status is saved in this browser.
        </p>
      </section>
    </main>
  );
}
