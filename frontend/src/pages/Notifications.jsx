import { useState } from "react";
import { Link } from "react-router-dom";
import {
  Bell,
  CheckCheck,
  CircleCheck,
  Clock3,
  FileText,
  MessageCircle,
  ShieldCheck,
} from "lucide-react";
import { getCases } from "../services/mockCaseService";

const STORAGE_KEY = "mindbridge_notifications_read";

const initialNotifications = [
  {
    id: "sample-status-1018",
    type: "status",
    title: "Your concern is under review",
    message:
      "Your academic guidance request has been received and is awaiting further review.",
    caseId: "MB-1018",
    date: "12 Oct 2026",
    time: "10:30 AM",
    icon: Clock3,
  },
  {
    id: "sample-update-1024",
    type: "update",
    title: "A case status has changed",
    message:
      "Your hostel maintenance concern is now marked as in progress.",
    caseId: "MB-1024",
    date: "11 Oct 2026",
    time: "3:15 PM",
    icon: FileText,
  },
  {
    id: "sample-privacy",
    type: "privacy",
    title: "Your privacy matters",
    message:
      "You can review your identity-sharing choice before submitting a new concern.",
    caseId: null,
    date: "10 Oct 2026",
    time: "9:00 AM",
    icon: ShieldCheck,
  },
  {
    id: "sample-resolved-1009",
    type: "resolved",
    title: "Your concern has been resolved",
    message:
      "The fee assistance enquiry in this demo has been marked as resolved.",
    caseId: "MB-1009",
    date: "8 Oct 2026",
    time: "1:45 PM",
    icon: CircleCheck,
  },
];

function readReadStatus() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
  } catch {
    return {};
  }
}

function getDateParts(dateValue) {
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

function getCaseNotifications() {
  const cases = getCases();
  const readStatus = readReadStatus();

  return cases.map((item) => {
    const createdAt = item.createdAt || new Date().toISOString();
    const { date, time } = getDateParts(createdAt);

    return {
      id: `case-submitted-${item.id}`,
      type: "status",
      title: "Your concern has been submitted",
      message: `"${item.title}" has been recorded in this browser demo and is awaiting review.`,
      caseId: item.id,
      date,
      time,
      icon: Clock3,
      unread: !Boolean(readStatus[`case-submitted-${item.id}`]),
    };
  });
}

function getAllNotifications() {
  const readStatus = readReadStatus();


  const sampleItems = initialNotifications.map((item) => {
    const defaultUnread = ![
      "sample-privacy",
      "sample-resolved-1009",
    ].includes(item.id);

    return {
      ...item,
      unread: readStatus[item.id] === undefined
        ? defaultUnread
        : !readStatus[item.id],
    };
  });


  return [...getCaseNotifications(), ...sampleItems];
}

function NotificationCard({ notification, onMarkRead }) {
  const Icon = notification.icon;

  return (
    <article
      className={`notification-card ${notification.unread ? "is-unread" : ""
        }`}
    >
      <div className="notification-icon">
        <Icon size={20} aria-hidden="true" />
      </div>

      <div className="notification-content">
        <div className="notification-title-row">
          <h3>{notification.title}</h3>
          {notification.unread && (
            <span className="notification-unread-dot" aria-label="Unread" />
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
          {notification.caseId && (
            <Link to={`/cases/${notification.caseId}`}>View case</Link>
          )}

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
  const [notifications, setNotifications] = useState(getAllNotifications);
  const [filter, setFilter] = useState("all");

  const unreadCount = notifications.filter(
    (notification) => notification.unread
  ).length;

  const visibleNotifications = notifications.filter((notification) => {
    return filter === "unread" ? notification.unread : true;
  });

  function markAsRead(notificationId) {
    const updatedReadStatus = {
      ...readReadStatus(),
      [notificationId]: true,
    };

    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(updatedReadStatus));
    } catch (error) {
      console.error("Could not save notification read status:", error);
      return;
    }

    setNotifications((current) =>
      current.map((notification) =>
        notification.id === notificationId
          ? { ...notification, unread: false }
          : notification
      )
    );
  }

  function markAllAsRead() {
    const updatedReadStatus = { ...readReadStatus() };

    notifications.forEach((notification) => {
      updatedReadStatus[notification.id] = true;
    });

    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(updatedReadStatus));
    } catch (error) {
      console.error("Could not save notification read status:", error);
      return;
    }

    setNotifications((current) =>
      current.map((notification) => ({ ...notification, unread: false }))
    );
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
          <p>Important updates about your concerns, all in one place.</p>
        </div>

        <div className="notifications-heading-icon">
          <Bell size={25} aria-hidden="true" />
          {unreadCount > 0 && (
            <span className="notification-count">{unreadCount}</span>
          )}
        </div>
      </section>

      <section className="notifications-panel">
        <div className="notifications-toolbar">
          <div>
            <h2>Your activity</h2>
            <p>
              {unreadCount === 0
                ? "You're all caught up."
                : `You have ${unreadCount} unread ${unreadCount === 1 ? "notification" : "notifications"
                }.`}
            </p>
          </div>

          {unreadCount > 0 && (
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

        <div className="notification-filters" aria-label="Filter notifications">
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
          {visibleNotifications.length > 0 ? (
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
              <h3>No unread notifications</h3>
              <p>New updates will appear here when they are available.</p>
            </div>
          )}
        </div>

        <p className="notification-demo-note">
          <ShieldCheck size={15} aria-hidden="true" />
          Case notifications are generated from local demo data. Live support
          team updates will require backend integration.
        </p>
      </section>
    </main>
  );
}