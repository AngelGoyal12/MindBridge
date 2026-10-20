import { Link } from "react-router-dom";
import {
  Bell,
  CheckCheck,
  Clock3,
  MessageCircle,
  ShieldCheck,
} from "lucide-react";

import { useNotifications } from "../context/notificationContext";
import { statusTimestamp } from "../services/casePresentation";

function NotificationCard({ notification, unread, onMarkRead }) {
  return (
    <article className={`notification-card${unread ? " is-unread" : ""}`}>
      <div className="notification-icon">
        <Clock3 size={20} aria-hidden="true" />
      </div>
      <div className="notification-content">
        <div className="notification-title-row">
          <h3>{notification.title}</h3>
          {unread && (
            <span className="notification-unread-dot" aria-label="Unread" />
          )}
        </div>
        <p className="notification-case-reference">
          Case {notification.caseId}
          {notification.caseTitle ? ` · ${notification.caseTitle}` : ""}
        </p>
        {notification.message && <p>{notification.message}</p>}
        <div className="notification-meta">
          <span>{statusTimestamp(notification.createdAt)}</span>
          {notification.type && (
            <>
              <span aria-hidden="true">·</span>
              <span>{notification.type.replaceAll("_", " ")}</span>
            </>
          )}
        </div>
        <div className="notification-actions">
          <Link to={`/cases/${notification.caseId}`}>View case</Link>
          {unread && (
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
  const {
    items,
    unreadCount,
    loading,
    error,
    readStateError,
    refresh,
    markAsRead,
    markAllAsRead,
    isRead,
  } = useNotifications();

  return (
    <main className="page-container notifications-page">
      <Link to="/dashboard" className="back-link">
        ← Back to dashboard
      </Link>

      <section className="notifications-heading">
        <div>
          <span className="eyebrow">YOUR UPDATES</span>
          <h1>Notifications</h1>
          <p>Updates recorded in your cases and visible to you.</p>
        </div>
        <div className="notifications-heading-icon" aria-hidden="true">
          <Bell size={25} />
          {unreadCount > 0 && (
            <span className="notification-count">{unreadCount}</span>
          )}
        </div>
      </section>

      <section className="notifications-panel">
        <div className="notifications-toolbar">
          <div>
            <h2>Case activity</h2>
            <p>
              {loading
                ? "Loading case updates..."
                : error
                  ? "Case updates could not be loaded."
                  : unreadCount
                    ? `${unreadCount} unread in this browser`
                    : "No unread updates in this browser."}
            </p>
          </div>
          <div className="notification-toolbar-actions">
            <button
              type="button"
              className="notification-mark-all"
              onClick={refresh}
              disabled={loading}
            >
              {loading ? "Refreshing..." : "Refresh updates"}
            </button>
            {!loading && unreadCount > 0 && (
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
        </div>

        <div className="notifications-list">
          {loading ? (
            <p role="status">Fetching your case activity...</p>
          ) : error ? (
            <div role="alert" className="notifications-empty">
              <MessageCircle size={25} aria-hidden="true" />
              <h3>Couldn't load updates</h3>
              <p>{error}</p>
              <button type="button" onClick={refresh}>
                Try again
              </button>
            </div>
          ) : items.length ? (
            items.map((notification) => (
              <NotificationCard
                key={notification.id}
                notification={notification}
                unread={!isRead(notification.id)}
                onMarkRead={markAsRead}
              />
            ))
          ) : (
            <div className="notifications-empty">
              <MessageCircle size={25} aria-hidden="true" />
              <h3>No case updates yet</h3>
              <p>Updates will appear here when they are recorded on a case.</p>
            </div>
          )}
        </div>

        <p className="notification-capability-note">
          <ShieldCheck size={15} aria-hidden="true" />
          Updates come from your own case progress timeline. Read status is
          saved in this browser only. Private Department-to-Coordinator
          messages are not available in this student feed.
        </p>
        {readStateError && (
          <p role="alert" className="field-error">
            {readStateError}
          </p>
        )}
      </section>
    </main>
  );
}
