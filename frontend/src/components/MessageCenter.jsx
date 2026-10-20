import { useCallback, useEffect, useMemo, useState } from "react";

import {
  getMessageInbox,
  getMessageRecipients,
  getSentMessages,
  markMessageRead,
  sendInternalMessage,
} from "../services/caseService";
import { statusTimestamp } from "../services/casePresentation";

const EMPTY_FORM = { recipient: "", case_id: "", subject: "", body: "" };

// Recipient choices are encoded as "main", "coord:<id>" or "dept:<name>".
function buildRecipientOptions(recipients) {
  if (!recipients) return [];
  const options = [];
  if (recipients.main_coordinator) {
    options.push({ value: "main", label: "Main Coordinator" });
  }
  (recipients.coordinators || []).forEach((coordinator) => {
    options.push({
      value: `coord:${coordinator.id}`,
      label: `${coordinator.name} (Department Coordinator)`,
    });
  });
  (recipients.departments || []).forEach((department) => {
    options.push({
      value: `dept:${department}`,
      label: `${department} department`,
    });
  });
  return options;
}

function recipientToPayload(value) {
  if (value === "main") return { recipient_type: "main_coordinator" };
  if (value.startsWith("coord:")) {
    return {
      recipient_type: "coordinator",
      recipient_user_id: Number(value.slice("coord:".length)),
    };
  }
  return {
    recipient_type: "department",
    recipient_department: value.slice("dept:".length),
  };
}

function replyTargetToValue(target) {
  if (!target) return "";
  if (target.recipient_type === "main_coordinator") return "main";
  if (target.recipient_type === "coordinator") {
    return `coord:${target.recipient_user_id}`;
  }
  return `dept:${target.recipient_department}`;
}

export default function MessageCenter({ cases = [], onUnreadChange }) {
  const [tab, setTab] = useState("inbox");
  const [recipients, setRecipients] = useState(null);
  const [inbox, setInbox] = useState([]);
  const [sent, setSent] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [feedback, setFeedback] = useState("");
  const [reloadKey, setReloadKey] = useState(0);
  const [form, setForm] = useState(EMPTY_FORM);
  const [sending, setSending] = useState(false);
  const [formError, setFormError] = useState("");

  const unread = useMemo(
    () => inbox.filter((message) => !message.read).length,
    [inbox],
  );
  const options = useMemo(() => buildRecipientOptions(recipients), [recipients]);

  useEffect(() => {
    if (onUnreadChange) onUnreadChange(unread);
  }, [unread, onUnreadChange]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        setLoading(true);
        setError("");
        const [recipientData, inboxData, sentData] = await Promise.all([
          getMessageRecipients(),
          getMessageInbox(),
          getSentMessages(),
        ]);
        if (!cancelled) {
          setRecipients(recipientData);
          setInbox(inboxData);
          setSent(sentData);
        }
      } catch (err) {
        if (!cancelled) setError(err.message || "Could not load messages.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  const setField = useCallback((field, value) => {
    setForm((current) => ({ ...current, [field]: value }));
  }, []);

  async function openMessage(message) {
    if (message.read) return;
    try {
      await markMessageRead(message.id);
      setInbox((current) =>
        current.map((item) =>
          item.id === message.id ? { ...item, read: true } : item,
        ),
      );
    } catch (err) {
      setFeedback(err.message || "Could not mark the message as read.");
    }
  }

  function startReply(message) {
    setForm({
      recipient: replyTargetToValue(message.reply_target),
      case_id: message.case_id ? String(message.case_id) : "",
      subject: message.subject.startsWith("Re: ")
        ? message.subject
        : `Re: ${message.subject}`.slice(0, 150),
      body: "",
    });
    setFormError("");
    setFeedback("");
    setTab("compose");
  }

  async function submit(event) {
    event.preventDefault();
    if (sending) return;
    if (!form.recipient) {
      setFormError("Choose who should receive this message.");
      return;
    }
    setSending(true);
    setFormError("");
    setFeedback("");
    try {
      const result = await sendInternalMessage({
        ...recipientToPayload(form.recipient),
        ...(form.case_id ? { case_id: Number(form.case_id) } : {}),
        subject: form.subject.trim(),
        body: form.body.trim(),
      });
      setFeedback(result.message);
      setForm(EMPTY_FORM);
      setTab("sent");
      setSent(await getSentMessages());
    } catch (err) {
      setFormError(err.message || "Could not send this message.");
    } finally {
      setSending(false);
    }
  }

  const canSend =
    form.recipient && form.subject.trim().length >= 2 && form.body.trim().length >= 2;

  return (
    <section className="message-center" aria-labelledby="message-center-heading">
      <h2 id="message-center-heading">
        Messages{unread > 0 ? ` (${unread} unread)` : ""}
      </h2>

      <div className="task-filters" role="group" aria-label="Message folders">
        {[
          { id: "inbox", label: unread > 0 ? `Inbox (${unread})` : "Inbox" },
          { id: "sent", label: "Sent" },
          { id: "compose", label: "New message" },
        ].map((item) => (
          <button
            key={item.id}
            type="button"
            className={`task-filter${tab === item.id ? " active" : ""}`}
            aria-pressed={tab === item.id}
            onClick={() => setTab(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>

      {feedback && (
        <p role="status" className="role-feedback">
          {feedback}
        </p>
      )}

      {loading ? (
        <p role="status">Loading messages...</p>
      ) : error ? (
        <div role="alert" className="workspace-error">
          <p>{error}</p>
          <button
            type="button"
            className="secondary-button"
            onClick={() => setReloadKey((key) => key + 1)}
          >
            Retry loading messages
          </button>
        </div>
      ) : (
        <>
          {tab === "inbox" &&
            (inbox.length === 0 ? (
              <p>No messages yet.</p>
            ) : (
              <ul className="message-list">
                {inbox.map((message) => (
                  <li
                    key={message.id}
                    className={`message-item${message.read ? "" : " unread"}`}
                  >
                    <details onToggle={(event) => event.currentTarget.open && openMessage(message)}>
                      <summary>
                        <strong>{message.subject}</strong>
                        <span className="message-meta">
                          {" "}
                          from {message.sender_name} ({message.sender_role_label}
                          {message.sender_department ? `, ${message.sender_department}` : ""})
                          {" · "}
                          {statusTimestamp(message.created_at)}
                          {!message.read && " · New"}
                        </span>
                      </summary>
                      {message.case_id && (
                        <p className="message-meta">
                          About case {message.case_id}
                          {message.case_title ? `: ${message.case_title}` : ""}
                        </p>
                      )}
                      <p className="message-body">{message.body}</p>
                      {message.reply_target && (
                        <button
                          type="button"
                          className="secondary-button"
                          onClick={() => startReply(message)}
                        >
                          Reply to {message.reply_target.label}
                        </button>
                      )}
                    </details>
                  </li>
                ))}
              </ul>
            ))}

          {tab === "sent" &&
            (sent.length === 0 ? (
              <p>You have not sent any messages.</p>
            ) : (
              <ul className="message-list">
                {sent.map((message) => (
                  <li key={message.group_id} className="message-item">
                    <details>
                      <summary>
                        <strong>{message.subject}</strong>
                        <span className="message-meta">
                          {" "}
                          to {message.audience_label} · {statusTimestamp(message.created_at)}
                          {" · "}
                          read by {message.read_count} of {message.recipient_count}
                        </span>
                      </summary>
                      {message.case_id && (
                        <p className="message-meta">About case {message.case_id}</p>
                      )}
                      <p className="message-body">{message.body}</p>
                    </details>
                  </li>
                ))}
              </ul>
            ))}

          {tab === "compose" && (
            <form onSubmit={submit} className="message-form">
              <label className="field-group">
                To
                <select
                  value={form.recipient}
                  onChange={(event) => setField("recipient", event.target.value)}
                >
                  <option value="">Choose a recipient</option>
                  {options.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              {!options.length && (
                <p role="status">
                  There is nobody you can message yet. Departments and
                  coordinators appear here once they are set up and linked to
                  your work.
                </p>
              )}
              <label className="field-group">
                Related case (optional)
                <select
                  value={form.case_id}
                  onChange={(event) => setField("case_id", event.target.value)}
                >
                  <option value="">No related case</option>
                  {cases.map((caseItem) => (
                    <option key={caseItem.id} value={caseItem.id}>
                      Case {caseItem.id}
                      {caseItem.title ? ` — ${caseItem.title}` : ""}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field-group">
                Subject
                <input
                  type="text"
                  minLength={2}
                  maxLength={150}
                  value={form.subject}
                  onChange={(event) => setField("subject", event.target.value)}
                />
              </label>
              <label className="field-group">
                Message
                <textarea
                  minLength={2}
                  maxLength={2000}
                  value={form.body}
                  onChange={(event) => setField("body", event.target.value)}
                />
              </label>
              <p className="task-form-hint">
                Do not include a student&apos;s name or contact details unless
                the student has agreed to share them. Identity is hidden from
                recipients who are not authorized to see it.
              </p>
              <button
                type="submit"
                className="button-primary"
                disabled={sending || !canSend}
              >
                {sending ? "Sending..." : "Send message"}
              </button>
              {formError && (
                <p role="alert" className="field-error">
                  {formError}
                </p>
              )}
            </form>
          )}
        </>
      )}
    </section>
  );
}
