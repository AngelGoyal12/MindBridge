
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.sql import func

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(16), nullable=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(30), nullable=False, default="student", index=True)
    department = Column(String(100), nullable=True)
    department_course = Column(String(100), nullable=True)
    current_semester = Column(Integer, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    csrf_token_hash = Column(String(64), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class PendingEmailVerification(Base):
    __tablename__ = "pending_email_verifications"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    phone = Column(String(16), nullable=True)
    department_course = Column(String(100), nullable=True)
    current_semester = Column(Integer, nullable=True)
    password_hash = Column(String(255), nullable=False)
    otp_hash = Column(String(64), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    attempt_count = Column(Integer, nullable=False, default=0)
    resend_count = Column(Integer, nullable=False, default=0)
    last_sent_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class CoordinatorInvitation(Base):
    __tablename__ = "coordinator_invitations"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(
        Integer,
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    invited_by_user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    email = Column(String(255), nullable=False, index=True)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class Case(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, index=True)

    student_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )

    assigned_coordinator_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )

    # Set only through the admin-controlled department assignment endpoint.
    # Never derive staff access from a department self-reported at registration.
    department = Column(String(100), nullable=True, index=True)

    category = Column(String(50), nullable=False, index=True)
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=False)

    status = Column(
        String(30),
        nullable=False,
        default="submitted",
        index=True,
    )

    identity_mode = Column(
        String(20),
        nullable=False,
        default="identified",
        server_default="identified",
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class CaseConsent(Base):
    __tablename__ = "case_consents"

    id = Column(Integer, primary_key=True, index=True)

    case_id = Column(
        Integer,
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    granted_by_user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    purpose = Column(String(255), nullable=False)
    recipient = Column(String(255), nullable=False)
    scope = Column(Text, nullable=False)

    granted = Column(Boolean, nullable=False, default=False)
    granted_at = Column(DateTime(timezone=True), nullable=True)
    withdrawn_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class CaseDisclosureAudit(Base):
    __tablename__ = "case_disclosure_audits"

    id = Column(Integer, primary_key=True, index=True)

    case_id = Column(
        Integer,
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    actor_user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    recipient = Column(String(255), nullable=False)
    purpose = Column(String(255), nullable=False)
    decision = Column(String(30), nullable=False)
    reason = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class CaseProgressUpdate(Base):
    __tablename__ = "case_progress_updates"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(
        Integer,
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    update_type = Column(String(30), nullable=False)
    title = Column(String(150), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class DepartmentActionRequest(Base):
    __tablename__ = "department_action_requests"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(
        Integer,
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    coordinator_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    sender_user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    request_type = Column(String(30), nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="open")
    handled_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class DepartmentTask(Base):
    """A unit of work a Coordinator assigns to a department for one case.

    Staff see only tasks addressed to their own department. Student identity
    is never stored here; it is resolved at read time through the existing
    consent-aware serializers.
    """

    __tablename__ = "department_tasks"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(
        Integer,
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    department = Column(String(100), nullable=False, index=True)
    assigned_by_user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    title = Column(String(150), nullable=False)
    instructions = Column(Text, nullable=False)
    priority = Column(
        String(20),
        nullable=False,
        default="normal",
        server_default="normal",
    )
    due_date = Column(Date, nullable=True)
    # assigned -> in_progress -> completed, or cancelled by the Coordinator.
    status = Column(
        String(20),
        nullable=False,
        default="assigned",
        server_default="assigned",
        index=True,
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    completed_by_user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
    )
    completion_note = Column(Text, nullable=True)
    # Optional: the specific staff member responsible for the task. While this
    # is NULL the task sits in the department pool and any staff member of the
    # department can claim it.
    assigned_staff_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )
    assigned_staff_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class DepartmentTaskEvent(Base):
    """Append-only history of task status changes."""

    __tablename__ = "department_task_events"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(
        Integer,
        ForeignKey("department_tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    from_status = Column(String(20), nullable=True)
    to_status = Column(String(20), nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class InternalMessage(Base):
    """One delivered copy of an internal message.

    A message sent to a group (the Main Coordinator group or a whole
    department) is fanned out into one row per recipient so each person has
    their own read state. Rows that came from the same send share group_id.
    """

    __tablename__ = "internal_messages"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(String(36), nullable=False, index=True)
    sender_user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    recipient_user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    # Human-readable audience, e.g. "Main Coordinator" or "Accounts".
    audience_label = Column(String(150), nullable=False)
    case_id = Column(
        Integer,
        ForeignKey("cases.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    subject = Column(String(150), nullable=False)
    body = Column(Text, nullable=False)
    read_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
