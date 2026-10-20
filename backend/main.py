
import hashlib
import json
import logging
import os
import re
import secrets
import smtplib
import threading
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional, Literal

from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    Query,
    Response,
    Request,
)
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

import models

from auth.schemas import (
    LoginRequest,
    ProfileUpdate,
    ResendVerificationRequest,
    RegisterRequest,
    UserResponse,
    VerifyEmailRequest,
    validate_strong_password,
)
from auth.email_verification import (
    coordinator_invitation_expiration,
    frontend_base_url,
    generate_invitation_token,
    generate_otp,
    hash_invitation_token,
    hash_otp,
    otp_matches,
    otp_settings,
    send_coordinator_assignment_email,
    send_coordinator_invitation_email,
    send_verification_email,
    validate_college_email,
    validate_smtp_configuration,
)
from auth.security import hash_password, verify_password
from auth.sessions import (
    create_session,
    revoke_session,
    clear_session_cookie,
)
from auth.roles import Role
from auth.dependencies import (
    get_db,
    get_current_user,
    require_roles,
    require_csrf_token,
    SESSION_COOKIE_NAME,
)


app = FastAPI(
    title="MindBridge API",
    description="Privacy-First Student Support & Case Coordination",
    version="1.0.0",
)
logger = logging.getLogger(__name__)


@app.exception_handler(RequestValidationError)
async def validation_error_response(
    _request: Request,
    error: RequestValidationError,
) -> JSONResponse:
    sensitive_fields = {
        "password",
        "confirm_password",
        "otp",
        "token",
        "invitation_token",
    }
    redact_input = _request.url.path.startswith("/api/v1/auth/")
    sanitized_errors = []
    for item in error.errors():
        location = item.get("loc", ())
        if redact_input or any(field in sensitive_fields for field in location):
            item = {key: value for key, value in item.items() if key != "input"}
        sanitized_errors.append(item)
    return JSONResponse(
        status_code=422,
        content=jsonable_encoder({"detail": sanitized_errors}),
    )


_DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(32))
LOGIN_RATE_WINDOW_SECONDS = 15 * 60
LOGIN_ACCOUNT_LIMIT = 5
LOGIN_IP_LIMIT = 20
_login_attempts: dict[str, list[float]] = {}
_login_attempts_lock = threading.Lock()
_email_flow_attempts: dict[str, list[float]] = {}


def reset_login_attempts() -> None:
    with _login_attempts_lock:
        _login_attempts.clear()
        _email_flow_attempts.clear()


def _limit_email_flow(key: str, limit: int, window_seconds: int) -> int | None:
    now = time.monotonic()
    cutoff = now - window_seconds
    with _login_attempts_lock:
        recent = [
            timestamp
            for timestamp in _email_flow_attempts.get(key, [])
            if timestamp > cutoff
        ]
        _email_flow_attempts[key] = recent
        if len(recent) >= limit:
            return max(1, int(recent[0] + window_seconds - now) + 1)
        recent.append(now)
        _email_flow_attempts[key] = recent
    return None


def _login_rate_limit_retry_after(remote_host: str, email: str) -> int | None:
    now = time.monotonic()
    cutoff = now - LOGIN_RATE_WINDOW_SECONDS
    ip_key = f"ip:{remote_host}"
    account_key = f"account:{email}"

    with _login_attempts_lock:
        for key in list(_login_attempts):
            active = [
                attempt
                for attempt in _login_attempts[key]
                if attempt > cutoff
            ]
            if active:
                _login_attempts[key] = active
            else:
                del _login_attempts[key]

        ip_attempts = _login_attempts.get(ip_key, [])
        account_attempts = _login_attempts.get(account_key, [])
        limits = (
            (ip_attempts, LOGIN_IP_LIMIT),
            (account_attempts, LOGIN_ACCOUNT_LIMIT),
        )
        remaining = [
            int(attempts[0] + LOGIN_RATE_WINDOW_SECONDS - now) + 1
            for attempts, limit in limits
            if len(attempts) >= limit
        ]
        if remaining:
            return max(remaining)

    return None


def _record_failed_login(remote_host: str, email: str) -> None:
    now = time.monotonic()
    cutoff = now - LOGIN_RATE_WINDOW_SECONDS
    keys = (f"ip:{remote_host}", f"account:{email}")
    with _login_attempts_lock:
        for key in list(_login_attempts):
            active = [
                attempt
                for attempt in _login_attempts[key]
                if attempt > cutoff
            ]
            if active:
                _login_attempts[key] = active
            else:
                del _login_attempts[key]

        for key in keys:
            _login_attempts.setdefault(key, []).append(now)

        while len(_login_attempts) > 10000:
            del _login_attempts[next(iter(_login_attempts))]


DEFAULT_FRONTEND_ORIGINS = {
    "http://localhost:5173",
    "http://127.0.0.1:5173",
}
configured_origins = os.getenv("FRONTEND_ORIGINS")
FRONTEND_ORIGINS = (
    {
        origin.strip().rstrip("/")
        for origin in configured_origins.split(",")
        if origin.strip()
    }
    if configured_origins is not None
    else DEFAULT_FRONTEND_ORIGINS
)
if not FRONTEND_ORIGINS or "*" in FRONTEND_ORIGINS:
    raise RuntimeError(
        "FRONTEND_ORIGINS must contain explicit trusted web origins."
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(FRONTEND_ORIGINS),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token"],
)


API_CONTENT_SECURITY_POLICY = (
    "default-src 'none'; "
    "base-uri 'none'; "
    "form-action 'none'; "
    "frame-ancestors 'none'; "
    "object-src 'none'"
)
API_DOCS_CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'none'; "
    "object-src 'none'; "
    "img-src 'self' data: https://fastapi.tiangolo.com; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "connect-src 'self'"
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=()"
    )
    response.headers["Content-Security-Policy"] = (
        API_DOCS_CONTENT_SECURITY_POLICY
        if request.url.path in {"/docs", "/redoc"}
        else API_CONTENT_SECURITY_POLICY
    )
    if (
        os.getenv("APP_ENV", "development").strip().lower()
        in {"production", "prod"}
        and os.getenv("SESSION_COOKIE_SECURE", "").strip().lower() == "true"
    ):
        response.headers["Strict-Transport-Security"] = "max-age=31536000"
    return response


# ---------------- CASE SCHEMAS ----------------

CaseStatus = Literal[
    "submitted",
    "in_review",
    "in_progress",
    "resolved",
    "closed",
]
DepartmentIdentityConsentRecipient = "assigned department"
DepartmentIdentityConsentPurpose = "Department response"
DepartmentIdentityConsentScope = "Student name and contact details"

class CaseIdentityUpdate(BaseModel):
    identity_mode: Literal["identified", "restricted", "anonymous"]


class CaseCreate(BaseModel):
    category: str = Field(min_length=2, max_length=50)
    title: str = Field(min_length=3, max_length=150)
    description: str = Field(min_length=10, max_length=5000)
    identity_mode: Literal["identified", "restricted", "anonymous"] = "identified"
    department_consent_level: Literal[
        "anonymous", "restricted", "full_disclosure"
    ] = "anonymous"
    department_consent_fields: list[
        Literal["name", "email", "phone", "department"]
    ] = Field(default_factory=list, max_length=4)
    department_identity_consent: bool | None = None

    @model_validator(mode="after")
    def validate_department_consent(self):
        if (
            self.department_identity_consent is not None
            and "department_consent_level" not in self.model_fields_set
        ):
            if self.department_identity_consent:
                self.department_consent_level = (
                    "full_disclosure"
                )
        if (
            self.department_consent_level != "restricted"
            and self.department_consent_fields
        ):
            raise ValueError(
                "Select identity fields only for restricted consent."
            )
        return self



class CaseUpdate(BaseModel):
    category: Optional[str] = Field(
        default=None, min_length=2, max_length=50
    )
    title: Optional[str] = Field(
        default=None, min_length=3, max_length=150
    )
    description: Optional[str] = Field(
        default=None, min_length=10, max_length=5000
    )
    status: Optional[CaseStatus] = None

class CaseAssignmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    coordinator_id: int | None = Field(default=None, gt=0)
    coordinator_email: EmailStr | None = None

    @field_validator("coordinator_email", mode="before")
    @classmethod
    def normalize_coordinator_email(cls, email: object) -> object:
        return email.strip().lower() if isinstance(email, str) else email

    @model_validator(mode="after")
    def require_one_coordinator_identifier(self):
        if (self.coordinator_id is None) == (self.coordinator_email is None):
            raise ValueError(
                "Provide exactly one coordinator account ID or email address."
            )
        return self


class CoordinatorInvitationAcceptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=32, max_length=256)
    name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=12, max_length=128)
    confirm_password: str = Field(min_length=1, max_length=128)

    @field_validator("name", mode="before")
    @classmethod
    def trim_invited_name(cls, name: object) -> object:
        return name.strip() if isinstance(name, str) else name

    @field_validator("password")
    @classmethod
    def enforce_invited_password_policy(cls, password: str) -> str:
        return validate_strong_password(password)

    @model_validator(mode="after")
    def invited_passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError("Password and confirm password must match.")
        return self

class DepartmentAssignmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    department: str = Field(min_length=2, max_length=100)


class CoordinatorCaseUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["in_review", "in_progress", "closed"]
    closure_outcome: str | None = Field(
        default=None,
        min_length=2,
        max_length=2000,
    )

    @model_validator(mode="after")
    def require_closure_outcome(self):
        if self.status == "closed" and not (self.closure_outcome or "").strip():
            raise ValueError("A closure outcome is required to close a case.")
        return self


class CoordinatorProgressUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=2, max_length=150)
    message: str = Field(min_length=2, max_length=2000)

    @field_validator("title", "message")
    @classmethod
    def trim_required_text(cls, value: str) -> str:
        return value.strip()


class DepartmentActionRequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_type: Literal["update", "closure_request"]
    message: str = Field(min_length=2, max_length=2000)

    @field_validator("message")
    @classmethod
    def trim_required_message(cls, value: str) -> str:
        return value.strip()


class DepartmentActionRequestDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["handled", "dismissed"]

# ---------------- DEPARTMENT TASK SCHEMAS ----------------

TaskPriority = Literal["low", "normal", "high", "urgent"]
TASK_OPEN_STATUSES = ("assigned", "in_progress")
TASK_STATUSES = ("assigned", "in_progress", "completed", "cancelled")
# Statuses department staff may move a task into, keyed by current status.
TASK_STAFF_TRANSITIONS = {
    "assigned": {"in_progress", "completed"},
    "in_progress": {"completed"},
}
# Institution-local calendar day (IST) used for due dates and overdue checks.
TASK_LOCAL_TZ = timezone(timedelta(hours=5, minutes=30))


def task_today() -> date:
    return datetime.now(TASK_LOCAL_TZ).date()


class DepartmentTaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    department: str = Field(min_length=2, max_length=100)
    title: str = Field(min_length=3, max_length=150)
    instructions: str = Field(min_length=5, max_length=2000)
    priority: TaskPriority = "normal"
    due_date: date | None = None
    # Optional: hand the task straight to one staff member of the department.
    assigned_staff_id: int | None = Field(default=None, gt=0)

    @field_validator("department", "title", "instructions", mode="before")
    @classmethod
    def trim_task_text(cls, value: object) -> object:
        # Trim before length checks so whitespace-only text is rejected.
        return value.strip() if isinstance(value, str) else value

    @field_validator("due_date")
    @classmethod
    def due_date_not_in_past(cls, value: date | None) -> date | None:
        if value is not None and value < task_today():
            raise ValueError("Due date cannot be in the past.")
        return value


class DepartmentTaskStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["in_progress", "completed"]
    note: str | None = Field(default=None, max_length=2000)

    @field_validator("note")
    @classmethod
    def trim_task_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @model_validator(mode="after")
    def require_completion_note(self):
        if self.status == "completed" and (
            self.note is None or len(self.note) < 2
        ):
            raise ValueError(
                "Add a short completion note describing what was done."
            )
        return self


class CoordinatorTaskDecision(BaseModel):
    """Coordinator review of a task: cancel it, or reopen a completed one."""

    model_config = ConfigDict(extra="forbid")

    action: Literal["cancel", "reopen"]
    note: str | None = Field(default=None, max_length=2000)

    @field_validator("note")
    @classmethod
    def trim_decision_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @model_validator(mode="after")
    def require_reopen_reason(self):
        if self.action == "reopen" and (
            self.note is None or len(self.note) < 2
        ):
            raise ValueError("Explain what still needs to be done.")
        return self


class TaskAssigneeUpdate(BaseModel):
    """Hand an open task to one staff member, or return it to the pool."""

    model_config = ConfigDict(extra="forbid")

    staff_id: int | None = Field(default=None, gt=0)


class InternalMessageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recipient_type: Literal["main_coordinator", "coordinator", "department"]
    recipient_user_id: int | None = Field(default=None, gt=0)
    recipient_department: str | None = Field(default=None, max_length=100)
    case_id: int | None = Field(default=None, gt=0)
    subject: str = Field(min_length=2, max_length=150)
    body: str = Field(min_length=2, max_length=2000)

    @field_validator("subject", "body", "recipient_department", mode="before")
    @classmethod
    def trim_message_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def check_recipient_fields(self):
        if self.recipient_type == "coordinator" and self.recipient_user_id is None:
            raise ValueError("Choose the coordinator to message.")
        if self.recipient_type == "department" and not self.recipient_department:
            raise ValueError("Choose the department to message.")
        if self.recipient_type != "coordinator":
            self.recipient_user_id = None
        if self.recipient_type != "department":
            self.recipient_department = None
        return self


class ConsentRequest(BaseModel):
    purpose: str = Field(min_length=2, max_length=255)
    recipient: str = Field(min_length=2, max_length=255)
    scope: str = Field(min_length=2, max_length=2000)


class DisclosureRequest(BaseModel):
    purpose: str = Field(min_length=2, max_length=255)
    scope: str = Field(min_length=2, max_length=2000)


# ---------------- RESPONSE HELPER ----------------

def case_to_dict(case, viewer=None):
    is_owner = (
        viewer is not None
        and getattr(viewer, "id", None) == case.student_id
    )

    data = {
        "id": case.id,
        "category": case.category,
        "title": case.title,
        "status": case.status,
        "created_at": case.created_at,
    }

    # Student identity is never serialized. Only the case owner can see the
    # full description and their own identity-mode setting.
    if is_owner:
        data["description"] = case.description
        data["identity_mode"] = case.identity_mode

    return data


def case_progress_to_dict(update):
    return {
        "id": update.id,
        "type": update.update_type,
        "title": update.title,
        "message": update.message,
        "created_at": update.created_at,
    }


def get_case_progress_updates(db: Session, case_id: int):
    updates = (
        db.query(models.CaseProgressUpdate)
        .filter(models.CaseProgressUpdate.case_id == case_id)
        .order_by(
            models.CaseProgressUpdate.created_at.asc(),
            models.CaseProgressUpdate.id.asc(),
        )
        .all()
    )
    return [case_progress_to_dict(update) for update in updates]


def department_identity_consent_granted(db: Session, case):
    return department_consent_to_dict(db, case)["active"]


def latest_department_identity_consent(db: Session, case):
    consent = (
        db.query(models.CaseConsent)
        .filter(
            models.CaseConsent.case_id == case.id,
            models.CaseConsent.granted_by_user_id == case.student_id,
            models.CaseConsent.recipient
            == DepartmentIdentityConsentRecipient,
            models.CaseConsent.purpose == DepartmentIdentityConsentPurpose,
        )
        .order_by(
            models.CaseConsent.created_at.desc(),
            models.CaseConsent.id.desc(),
        )
        .first()
    )
    return consent


def department_consent_to_dict(db: Session, case):
    consent = latest_department_identity_consent(db, case)
    if consent is None:
        return {"level": "anonymous", "fields": [], "active": False}

    try:
        stored_scope = json.loads(consent.scope)
    except (TypeError, json.JSONDecodeError):
        stored_scope = None

    if isinstance(stored_scope, dict) and stored_scope.get("level") in {
        "anonymous",
        "restricted",
        "full_disclosure",
    }:
        level = stored_scope["level"]
        fields = stored_scope.get("fields", [])
        if not isinstance(fields, list):
            fields = []
        allowed_fields = {"name", "email", "phone", "department"}
        fields = sorted(
            {field for field in fields if isinstance(field, str)}
            & allowed_fields
        )
        if level == "anonymous":
            fields = []
        elif level == "full_disclosure":
            fields = sorted(allowed_fields)
    else:
        # Prior Boolean consent covered name, email, and phone only.
        level = "full_disclosure" if consent.granted else "anonymous"
        fields = ["name", "email", "phone"] if consent.granted else []

    granted_at = consent.granted_at
    if granted_at is not None and granted_at.tzinfo is None:
        granted_at = granted_at.replace(tzinfo=timezone.utc)
    active = bool(
        consent.granted
        and consent.withdrawn_at is None
        and granted_at is not None
        and granted_at <= datetime.now(timezone.utc)
    )
    return {"level": level, "fields": fields, "active": active}


def student_case_to_dict(db: Session, case, viewer):
    data = case_to_dict(case, viewer)
    department_consent = department_consent_to_dict(db, case)
    data.update(
        {
            "department": case.department,
            "department_identity_consent": department_consent["active"],
            "department_consent": department_consent,
            "progress_updates": get_case_progress_updates(db, case.id),
        }
    )
    return data


def redact_known_student_identity(text: str, student) -> str:
    if student is None:
        return text
    identity_values = sorted(
        {
            value.strip()
            for value in (
                student.name,
                student.email,
                student.phone,
                student.department,
            )
            if value and value.strip()
        },
        key=len,
        reverse=True,
    )
    for value in identity_values:
        text = re.sub(re.escape(value), "[redacted]", text, flags=re.IGNORECASE)
    return text


def coordinator_case_to_dict(db: Session, case):
    student = (
        db.query(models.User)
        .filter(models.User.id == case.student_id)
        .first()
    )
    department_consent = department_consent_to_dict(db, case)
    return {
        "id": case.id,
        "category": case.category,
        "title": case.title,
        "description": case.description,
        "status": case.status,
        "department": case.department,
        "department_identity_consent": department_consent["active"],
        "department_consent": department_consent,
        "student_name": student.name if student is not None else None,
        "student_email": student.email if student is not None else None,
        "student_phone": student.phone if student is not None else None,
        "student_department": (
            student.department if student is not None else None
        ),
        "created_at": case.created_at,
        "progress_updates": get_case_progress_updates(db, case.id),
    }


def department_case_to_dict(db: Session, case):
    student = (
        db.query(models.User)
        .filter(models.User.id == case.student_id)
        .first()
    )
    consent = department_consent_to_dict(db, case)
    consent_fields = set(consent["fields"]) if consent["active"] else set()
    data = {
        "id": case.id,
        "category": case.category,
        "title": case.title,
        "description": case.description,
        "status": case.status,
        "department_identity_consent": consent["active"],
        "department_consent": consent,
        "coordinator_available": case.assigned_coordinator_id is not None,
        "created_at": case.created_at,
    }
    if student is not None and consent["active"]:
        if "name" in consent_fields:
            data["student_name"] = student.name
        if "email" in consent_fields:
            data["student_email"] = student.email
        if "phone" in consent_fields and student.phone:
            data["student_phone"] = student.phone
        if "department" in consent_fields and student.department:
            data["student_department"] = student.department
    if student is not None:
        data["title"] = redact_unselected_student_identity(
            data["title"], student, consent_fields
        )
        data["description"] = redact_unselected_student_identity(
            data["description"], student, consent_fields
        )
    return data


def redact_unselected_student_identity(text: str, student, allowed_fields):
    profile_fields = {
        "name": student.name,
        "email": student.email,
        "phone": student.phone,
        "department": student.department,
    }
    for field, value in profile_fields.items():
        if field not in allowed_fields and value:
            text = re.sub(
                re.escape(value.strip()),
                "[redacted]",
                text,
                flags=re.IGNORECASE,
            )
    return text


def student_case_action_request_to_dict(action_request):
    return {
        "id": action_request.id,
        "case_id": action_request.case_id,
        "request_type": action_request.request_type,
        "message": action_request.message,
        "status": action_request.status,
        "created_at": action_request.created_at,
        "handled_at": action_request.handled_at,
    }


def admin_case_to_dict(db: Session, case, coordinator_email=None):
    student = (
        db.query(models.User)
        .filter(models.User.id == case.student_id)
        .first()
    )
    title = redact_admin_content(case.title, student)
    summary = redact_admin_content(case.description, student)
    summary = summary[:500]
    if len(case.description) > 500:
        summary = summary.rstrip() + "..."
    return {
        "id": case.id,
        "category": case.category,
        "title": title,
        "summary": summary,
        "status": case.status,
        "created_at": case.created_at,
        "assigned_coordinator_id": case.assigned_coordinator_id,
        "assigned_coordinator_email": coordinator_email,
        "department": case.department,
    }


def redact_admin_content(text: str, student) -> str:
    text = redact_known_student_identity(text, student)
    text = re.sub(
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
        "[redacted]",
        text,
        flags=re.IGNORECASE,
    )
    return re.sub(
        r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)",
        "[redacted]",
        text,
    )


# ---------------- HOME ----------------

@app.get("/")
def home():
    return {
        "message": "Welcome to MindBridge API!",
        "status": "running",
    }




# ---------------- AUTHENTICATION ----------------

@app.post("/api/v1/auth/register", status_code=202)
def register(
    data: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    name = data.name.strip()
    email = str(data.email).strip().lower()

    if len(name) < 2:
        raise HTTPException(
            status_code=422,
            detail="Please enter a valid name.",
        )

    if not validate_college_email(email):
        raise HTTPException(
            status_code=422,
            detail="Use a valid college email address ending in .edu.in.",
        )

    remote_host = request.client.host if request.client else "unknown"

    retry_after = _limit_email_flow(
        f"registration-ip:{remote_host}",
        10,
        3600,
    )

    if retry_after is not None:
        raise HTTPException(
            status_code=429,
            detail="Too many registration attempts. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    _, resend_cooldown_seconds, _, _ = otp_settings()

    generic_response = {
        "message": (
            "If the address is eligible, a verification email will be sent."
        ),
        "resend_cooldown_seconds": resend_cooldown_seconds,
    }

    # Check for an existing account and pending registration.
    try:
        existing_user = (
            db.query(models.User.id)
            .filter(models.User.email == email)
            .first()
        )

        if existing_user:
            return generic_response

        pending = (
            db.query(models.PendingEmailVerification)
            .filter(models.PendingEmailVerification.email == email)
            .with_for_update()
            .first()
        )

    except SQLAlchemyError:
        db.rollback()
        logger.exception("Database error while checking student registration")
        raise HTTPException(
            status_code=503,
            detail="Registration is temporarily unavailable. Please try again later.",
        ) from None

    now = datetime.now(timezone.utc)

    if pending is not None:
        expiry = pending.expires_at

        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)

        # Do not replace an active pending verification.
        if expiry > now:
            return generic_response

        # Remove an expired pending registration.
        try:
            db.delete(pending)
            db.flush()
        except SQLAlchemyError:
            db.rollback()
            logger.exception("Could not remove expired pending registration")
            raise HTTPException(
                status_code=503,
                detail="Registration is temporarily unavailable. Please try again later.",
            ) from None

    # Validate SMTP configuration separately so database RuntimeErrors
    # are not incorrectly reported as email-configuration errors.
    try:
        validate_smtp_configuration()
    except RuntimeError:
        db.rollback()
        raise HTTPException(
            status_code=503,
            detail=(
                "Email verification is not configured on this server. "
                "Please contact support or try again later."
            ),
        ) from None

    otp = generate_otp()
    expiration_seconds, _, _, _ = otp_settings()

    pending = models.PendingEmailVerification(
        name=name,
        email=email,
        phone=data.phone,
        department_course=data.department_course,
        current_semester=data.current_semester,
        password_hash=hash_password(data.password),
        otp_hash=hash_otp(email, otp),
        expires_at=now + timedelta(seconds=expiration_seconds),
        attempt_count=0,
        resend_count=0,
        last_sent_at=now,
    )

    db.add(pending)

    # Persist the pending account before attempting email delivery.
    try:
        db.commit()
        db.refresh(pending)

    except IntegrityError:
        db.rollback()
        return generic_response

    except SQLAlchemyError:
        db.rollback()
        logger.exception("Database error while creating pending registration")
        raise HTTPException(
            status_code=503,
            detail="Registration is temporarily unavailable. Please try again later.",
        ) from None

    pending_id = pending.id
    pending_otp_hash = pending.otp_hash

    # Send the OTP only after the pending registration has been committed.
    try:
        send_verification_email(
            email,
            otp,
            expiration_seconds,
        )

    except (OSError, RuntimeError, smtplib.SMTPException):
        # Remove only the pending record created by this request.
        try:
            db.query(models.PendingEmailVerification).filter(
                models.PendingEmailVerification.id == pending_id,
                models.PendingEmailVerification.otp_hash == pending_otp_hash,
            ).delete(synchronize_session=False)

            db.commit()

        except SQLAlchemyError:
            db.rollback()
            logger.error(
                "Could not clean an undelivered pending student registration "
                "(record id=%s).",
                pending_id,
                exc_info=True,
            )

        raise HTTPException(
            status_code=503,
            detail=(
                "Verification email could not be sent. "
                "Please try again later."
            ),
        ) from None

    return generic_response

@app.post("/api/v1/auth/verify-email")
def verify_email(
    payload: VerifyEmailRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    email = str(payload.email).strip().lower()
    remote_host = request.client.host if request.client else "unknown"
    retry_after = _limit_email_flow(f"verification-ip:{remote_host}", 30, 3600)
    if retry_after is not None:
        raise HTTPException(
            status_code=429,
            detail="Too many verification attempts. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )
    pending = (
        db.query(models.PendingEmailVerification)
        .filter(models.PendingEmailVerification.email == email)
        .with_for_update()
        .first()
    )
    if pending is None:
        raise HTTPException(
            status_code=400,
            detail="Verification could not be completed. Request a new code.",
        )

    now = datetime.now(timezone.utc)
    expires_at = pending.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        raise HTTPException(
            status_code=400,
            detail="This verification code has expired. Request a new code.",
        )

    _, _, _, attempt_limit = otp_settings()
    if pending.attempt_count >= attempt_limit:
        raise HTTPException(
            status_code=429,
            detail="Too many incorrect codes. Request a new verification code.",
        )
    if not otp_matches(pending, payload.otp):
        pending.attempt_count += 1
        exhausted = pending.attempt_count >= attempt_limit
        db.commit()
        raise HTTPException(
            status_code=429 if exhausted else 400,
            detail=(
                "Too many incorrect codes. Request a new verification code."
                if exhausted
                else "Verification could not be completed. Check the code and try again."
            ),
        )

    user = models.User(
        name=pending.name,
        email=email,
        phone=pending.phone,
        department_course=pending.department_course,
        current_semester=pending.current_semester,
        password_hash=pending.password_hash,
        role=Role.STUDENT.value,
        department=None,
    )
    db.add(user)
    db.delete(pending)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Verification could not be completed. Request a new code.",
        )
    return {"message": "Email verified. You can now sign in."}


@app.post("/api/v1/auth/resend-verification", status_code=202)
def resend_verification(
    payload: ResendVerificationRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    email = str(payload.email).strip().lower()
    remote_host = request.client.host if request.client else "unknown"
    retry_after = _limit_email_flow(f"resend-ip:{remote_host}", 10, 3600)
    if retry_after is not None:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    _, cooldown_seconds, _, _ = otp_settings()
    generic_response = {
        "message": (
            "If a pending verification exists, a code was sent when "
            "resend limits permit."
        ),
        "resend_cooldown_seconds": cooldown_seconds,
    }
    pending = (
        db.query(models.PendingEmailVerification)
        .filter(models.PendingEmailVerification.email == email)
        .with_for_update()
        .first()
    )
    if pending is None:
        return generic_response

    now = datetime.now(timezone.utc)
    last_sent_at = pending.last_sent_at
    if last_sent_at.tzinfo is None:
        last_sent_at = last_sent_at.replace(tzinfo=timezone.utc)
    expiration_seconds, cooldown_seconds, resend_limit, _ = otp_settings()
    retry_after = max(
        0,
        int(last_sent_at.timestamp() + cooldown_seconds - now.timestamp()) + 1,
    )
    if retry_after > 0:
        return generic_response
    if pending.resend_count >= resend_limit:
        return generic_response

    try:
        validate_smtp_configuration()
    except RuntimeError:
        raise HTTPException(
            status_code=503,
            detail=(
                "Email verification is not configured on this server. "
                "Please contact support or try again later."
            ),
        ) from None

    otp = generate_otp()
    previous_state = (
        pending.otp_hash,
        pending.expires_at,
        pending.attempt_count,
        pending.resend_count,
        pending.last_sent_at,
    )
    pending.otp_hash = hash_otp(email, otp)
    pending.expires_at = now + timedelta(seconds=expiration_seconds)
    pending.attempt_count = 0
    pending.resend_count += 1
    pending.last_sent_at = now
    db.commit()

    try:
        send_verification_email(email, otp, expiration_seconds)
    except (OSError, RuntimeError, smtplib.SMTPException):
        try:
            current_pending = (
                db.query(models.PendingEmailVerification)
                .filter(
                    models.PendingEmailVerification.id == pending.id,
                    models.PendingEmailVerification.otp_hash == pending.otp_hash,
                )
                .with_for_update()
                .first()
            )
            if current_pending is not None:
                (
                    current_pending.otp_hash,
                    current_pending.expires_at,
                    current_pending.attempt_count,
                    current_pending.resend_count,
                    current_pending.last_sent_at,
                ) = previous_state
                db.commit()
        except SQLAlchemyError:
            db.rollback()
            logger.error(
                "Could not restore pending student verification after a "
                "resend delivery failure.",
                exc_info=True,
            )
        raise HTTPException(
            status_code=503,
            detail="Verification email could not be sent. Please try again later.",
        ) from None
    return generic_response


@app.post("/api/v1/auth/login")
def login(
    credentials: LoginRequest,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
):
    email = str(credentials.email).strip().lower()
    remote_host = request.client.host if request.client else "unknown"
    retry_after = _login_rate_limit_retry_after(remote_host, email)
    if retry_after is not None:
        raise HTTPException(
            status_code=429,
            detail="Too many unsuccessful login attempts. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    user = (
        db.query(models.User)
        .filter(models.User.email == email)
        .first()
    )

    valid_password = verify_password(
        credentials.password,
        user.password_hash if user is not None else _DUMMY_PASSWORD_HASH,
    )
    if user is None or not valid_password:
        _record_failed_login(remote_host, email)
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password.",
        )

    if (
        user.role not in {role.value for role in Role}
        or (
            user.role == Role.DEPARTMENT_STAFF.value
            and not (user.department or "").strip()
        )
    ):
        raise HTTPException(
            status_code=403,
            detail="Account role or department assignment is not authorized.",
        )

    csrf_token = create_session(db, user, response)

    return {
        "message": "Login successful",
        "user": UserResponse.model_validate(user),
        "csrf_token": csrf_token,
    }


@app.get(
    "/api/v1/auth/me",
    response_model=UserResponse,
)
def get_me(
    current_user: models.User = Depends(get_current_user),
):
    return current_user


@app.patch(
    "/api/v1/auth/me",
    response_model=UserResponse,
)
def update_me(
    payload: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    _: None = Depends(require_csrf_token),
):
    name = payload.name.strip()
    if len(name) < 2:
        raise HTTPException(
            status_code=422,
            detail="Please enter a valid name.",
        )

    current_user.name = name
    if payload.phone is not None:
        current_user.phone = payload.phone
    db.commit()
    db.refresh(current_user)
    return current_user


# Issue a fresh CSRF token for an existing authenticated session.
@app.post("/api/v1/auth/csrf")
def refresh_csrf_token(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    origin = request.headers.get("origin")

    if origin not in FRONTEND_ORIGINS:
        raise HTTPException(
            status_code=403,
            detail="Untrusted request origin.",
        )

    session_token = request.cookies.get(SESSION_COOKIE_NAME)

    if not session_token:
        raise HTTPException(
            status_code=401,
            detail="Authentication required.",
        )

    session_hash = hashlib.sha256(
        session_token.encode("utf-8")
    ).hexdigest()

    session_record = (
        db.query(models.UserSession)
        .filter(
            models.UserSession.token_hash == session_hash,
            models.UserSession.user_id == current_user.id,
            models.UserSession.revoked_at.is_(None),
            models.UserSession.expires_at > datetime.now(timezone.utc),
        )
        .first()
    )

    if session_record is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session.",
        )

    csrf_token = secrets.token_urlsafe(32)

    session_record.csrf_token_hash = hashlib.sha256(
        csrf_token.encode("utf-8")
    ).hexdigest()

    db.commit()

    return {"csrf_token": csrf_token}


@app.post("/api/v1/auth/logout")
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    _: None = Depends(require_csrf_token),
):
    token = request.cookies.get(SESSION_COOKIE_NAME)

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Authentication required.",
        )

    revoke_session(db, token)
    clear_session_cookie(response)

    return {"message": "Logout successful."}


# ---------------- CASES ----------------

# Create case: authenticated students only.
@app.post("/api/v1/cases", status_code=201)
def create_case(
    case: CaseCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles(Role.STUDENT.value)),
    _: None = Depends(require_csrf_token),
):
    new_case = models.Case(
        student_id=current_user.id,
        category=case.category,
        title=case.title,
        description=case.description,
        status="submitted",
        identity_mode=case.identity_mode,
    )
    db.add(new_case)
    db.flush()
    if case.department_consent_level == "restricted":
        consent_fields = sorted(set(case.department_consent_fields))
    elif case.department_consent_level == "full_disclosure":
        consent_fields = ["name", "email", "phone", "department"]
    else:
        consent_fields = []
    consent_granted = bool(consent_fields)
    consent_at = datetime.now(timezone.utc) if consent_granted else None
    consent_scope = json.dumps(
        {
            "level": case.department_consent_level,
            "fields": consent_fields,
        },
        separators=(",", ":"),
    )
    db.add(
        models.CaseConsent(
            case_id=new_case.id,
            granted_by_user_id=current_user.id,
            purpose=DepartmentIdentityConsentPurpose,
            recipient=DepartmentIdentityConsentRecipient,
            scope=consent_scope,
            granted=consent_granted,
            granted_at=consent_at,
            withdrawn_at=None,
        )
    )
    db.add(
        models.CaseDisclosureAudit(
            case_id=new_case.id,
            actor_user_id=current_user.id,
            recipient=DepartmentIdentityConsentRecipient,
            purpose=DepartmentIdentityConsentPurpose,
            decision=(
                "consent_granted" if consent_granted else "consent_denied"
            ),
            reason=(
                f"Student selected {case.department_consent_level} "
                "department identity disclosure."
                if consent_granted
                else "Student did not consent to identity disclosure."
            ),
        )
    )
    db.add(
        models.CaseProgressUpdate(
            case_id=new_case.id,
            author_user_id=current_user.id,
            update_type="status",
            title="Case submitted",
            message="Your case was submitted successfully.",
        )
    )
    db.commit()
    db.refresh(new_case)

    return student_case_to_dict(db, new_case, current_user)


# Students can list their own cases only.
@app.get("/api/v1/cases")
def get_cases(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    status: Optional[CaseStatus] = None,
    category: Optional[str] = None,
    sort_order: str = Query(
        default="desc",
        pattern="^(asc|desc)$",
    ),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles(Role.STUDENT.value)),
):
    query = db.query(models.Case).filter(
        models.Case.student_id == current_user.id
    )

    if status is not None:
        query = query.filter(models.Case.status == status)

    if category:
        query = query.filter(models.Case.category == category)

    if sort_order == "asc":
        query = query.order_by(models.Case.id.asc())
    else:
        query = query.order_by(models.Case.id.desc())

    cases = query.offset(skip).limit(limit).all()

    return [
        student_case_to_dict(db, case, current_user)
        for case in cases
    ]


# Students can count their own cases only.
@app.get("/api/v1/cases/count")
def get_case_count(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles(Role.STUDENT.value)),
):
    total = (
        db.query(models.Case)
        .filter(models.Case.student_id == current_user.id)
        .count()
    )

    return {"total_cases": total}


@app.patch(
    "/api/v1/cases/{case_id}/assign",
)
def assign_case(
    case_id: int,
    payload: CaseAssignmentRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles(Role.ADMIN.value)),
    _: None = Depends(require_csrf_token),
):
    case = (
        db.query(models.Case)
        .filter(models.Case.id == case_id)
        .first()
    )

    if case is None:
        raise HTTPException(
            status_code=404,
            detail="Case not found."
        )

    try:
        validate_smtp_configuration()
        base_url = frontend_base_url()
        invitation_hours = coordinator_invitation_expiration()
    except RuntimeError:
        raise HTTPException(
            status_code=503,
            detail="Coordinator email is not configured on this server.",
        ) from None

    coordinator_email = (
        str(payload.coordinator_email).strip().lower()
        if payload.coordinator_email is not None
        else None
    )
    if payload.coordinator_id is not None:
        coordinator = (
            db.query(models.User)
            .filter(models.User.id == payload.coordinator_id)
            .first()
        )
        if coordinator is not None:
            coordinator_email = coordinator.email.strip().lower()
    else:
        coordinator = (
            db.query(models.User)
            .filter(func.lower(models.User.email) == coordinator_email)
            .first()
        )

    if coordinator is not None and coordinator.role != Role.COORDINATOR.value:
        raise HTTPException(
            status_code=400,
            detail="The email belongs to an account that is not a coordinator.",
        )
    if payload.coordinator_id is not None and coordinator is None:
        raise HTTPException(
            status_code=400,
            detail="A valid provisioned coordinator account is required.",
        )
    if coordinator_email is None:
        raise HTTPException(
            status_code=400,
            detail="A coordinator email address is required.",
        )

    now = datetime.now(timezone.utc)
    pending_invitations = (
        db.query(models.CoordinatorInvitation)
        .filter(
            models.CoordinatorInvitation.case_id == case.id,
            models.CoordinatorInvitation.accepted_at.is_(None),
            models.CoordinatorInvitation.revoked_at.is_(None),
        )
        .all()
    )
    for invitation in pending_invitations:
        invitation.revoked_at = now

    if coordinator is not None:
        previous_coordinator_id = case.assigned_coordinator_id
        case.assigned_coordinator_id = coordinator.id
        db.commit()
        try:
            send_coordinator_assignment_email(
                coordinator_email,
                case.id,
                case.category,
            )
        except (OSError, RuntimeError, smtplib.SMTPException):
            try:
                current_case = (
                    db.query(models.Case)
                    .filter(models.Case.id == case.id)
                    .first()
                )
                if (
                    current_case is not None
                    and current_case.assigned_coordinator_id == coordinator.id
                ):
                    current_case.assigned_coordinator_id = previous_coordinator_id
                    db.commit()
            except SQLAlchemyError:
                db.rollback()
                logger.error(
                    "Could not restore case assignment after email failure."
                )
            raise HTTPException(
                status_code=503,
                detail=(
                    "Coordinator assignment email could not be sent. "
                    "The case assignment was not changed."
                ),
            ) from None
        if previous_coordinator_id != coordinator.id:
            db.add(
                models.CaseProgressUpdate(
                    case_id=case.id,
                    author_user_id=current_user.id,
                    update_type="assignment",
                    title="Coordinator assigned",
                    message="A Coordinator has been assigned to your case.",
                )
            )
            db.commit()
        db.refresh(case)
        return {
            "message": "Case assigned and coordinator notified.",
            "assignment_status": "assigned",
            "coordinator_email": coordinator_email,
            "login_url": f"{base_url}/login",
            "dashboard_url": f"{base_url}/dashboard/coordinator",
            "case": admin_case_to_dict(db, case, coordinator_email),
        }

    raw_token = generate_invitation_token()
    invitation = models.CoordinatorInvitation(
        case_id=case.id,
        invited_by_user_id=current_user.id,
        email=coordinator_email,
        token_hash=hash_invitation_token(raw_token),
        expires_at=now + timedelta(hours=invitation_hours),
    )
    db.add(invitation)
    # A pending invitation is not an active coordinator assignment.
    # Clearing the old assignment immediately revokes its access.
    previous_coordinator_id = case.assigned_coordinator_id
    case.assigned_coordinator_id = None
    db.commit()
    try:
        send_coordinator_invitation_email(
            coordinator_email,
            raw_token,
            case.id,
            case.category,
        )
    except (OSError, RuntimeError, smtplib.SMTPException):
        try:
            saved_invitation = (
                db.query(models.CoordinatorInvitation)
                .filter(
                    models.CoordinatorInvitation.token_hash
                    == invitation.token_hash
                )
                .first()
            )
            if saved_invitation is not None and saved_invitation.accepted_at is None:
                db.delete(saved_invitation)
            current_case = (
                db.query(models.Case)
                .filter(models.Case.id == case.id)
                .first()
            )
            if (
                current_case is not None
                and current_case.assigned_coordinator_id is None
            ):
                current_case.assigned_coordinator_id = previous_coordinator_id
            db.commit()
        except SQLAlchemyError:
            db.rollback()
            logger.error(
                "Could not clean up coordinator invitation after email failure."
            )
        raise HTTPException(
            status_code=503,
            detail=(
                "Coordinator invitation email could not be sent. "
                "The case assignment was not changed."
            ),
        ) from None
    return {
        "message": "Coordinator invitation sent.",
        "assignment_status": "invitation_sent",
        "coordinator_email": coordinator_email,
        "login_url": f"{base_url}/login",
        "dashboard_url": f"{base_url}/dashboard/coordinator",
        "case": admin_case_to_dict(db, case),
    }


@app.post("/api/v1/coordinator-invitations/accept", status_code=201)
def accept_coordinator_invitation(
    payload: CoordinatorInvitationAcceptRequest,
    db: Session = Depends(get_db),
):
    token_hash = hash_invitation_token(payload.token)
    invitation = (
        db.query(models.CoordinatorInvitation)
        .filter(models.CoordinatorInvitation.token_hash == token_hash)
        .with_for_update()
        .first()
    )
    now = datetime.now(timezone.utc)
    if invitation is None or invitation.accepted_at is not None:
        raise HTTPException(
            status_code=400,
            detail="This coordinator invitation is invalid or has already been used.",
        )
    if invitation.revoked_at is not None:
        raise HTTPException(
            status_code=400,
            detail="This coordinator invitation is no longer active.",
        )
    expiry = invitation.expires_at
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    if expiry <= now:
        raise HTTPException(
            status_code=400,
            detail="This coordinator invitation has expired.",
        )

    existing_user = (
        db.query(models.User)
        .filter(func.lower(models.User.email) == invitation.email)
        .first()
    )
    if existing_user is not None:
        raise HTTPException(
            status_code=409,
            detail="An account already exists for this email. Please sign in.",
        )
    case = (
        db.query(models.Case)
        .filter(models.Case.id == invitation.case_id)
        .first()
    )
    if case is None:
        raise HTTPException(
            status_code=404,
            detail="The invited case is no longer available.",
        )
    if case.assigned_coordinator_id is not None:
        invitation.revoked_at = now
        db.commit()
        raise HTTPException(
            status_code=409,
            detail="This case has since been assigned to another coordinator.",
        )

    coordinator = models.User(
        name=payload.name.strip(),
        email=invitation.email,
        password_hash=hash_password(payload.password),
        role=Role.COORDINATOR.value,
    )
    db.add(coordinator)
    db.flush()
    case.assigned_coordinator_id = coordinator.id
    invitation.accepted_at = now
    db.add(
        models.CaseProgressUpdate(
            case_id=case.id,
            author_user_id=coordinator.id,
            update_type="assignment",
            title="Coordinator assigned",
            message="A Coordinator has been assigned to your case.",
        )
    )
    db.commit()

    try:
        base_url = frontend_base_url()
    except RuntimeError:
        base_url = next(iter(FRONTEND_ORIGINS))
    return {
        "message": "Coordinator account activated and case assigned.",
        "login_url": f"{base_url}/login",
        "dashboard_url": f"{base_url}/dashboard/coordinator",
    }


@app.patch(
    "/api/v1/cases/{case_id}/department",
    dependencies=[
        Depends(
            require_roles(
                Role.ADMIN.value,
                Role.COORDINATOR.value,
            )
        ),
        Depends(require_csrf_token),
    ],
)
def assign_case_department(
    case_id: int,
    payload: DepartmentAssignmentRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_roles(Role.ADMIN.value, Role.COORDINATOR.value)
    ),
):
    case = db.query(models.Case).filter(models.Case.id == case_id).first()

    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")

    if (
        current_user.role == Role.COORDINATOR.value
        and case.assigned_coordinator_id != current_user.id
    ):
        raise HTTPException(
            status_code=404,
            detail="Assigned case not found.",
        )

    department_name = payload.department.strip()
    trusted_department = (
        db.query(models.User.department)
        .filter(
            models.User.role == Role.DEPARTMENT_STAFF.value,
            models.User.department.is_not(None),
        )
        .order_by(func.lower(models.User.department), models.User.department)
        .all()
    )
    canonical_department = next(
        (
            name.strip()
            for (name,) in trusted_department
            if name
            and name.strip()
            and name.strip().casefold() == department_name.casefold()
        ),
        None,
    )
    if canonical_department is None:
        raise HTTPException(
            status_code=400,
            detail="Department must have a provisioned department staff account.",
        )

    department_changed = case.department != canonical_department
    case.department = canonical_department
    if department_changed:
        db.add(
            models.CaseProgressUpdate(
                case_id=case.id,
                author_user_id=current_user.id,
                update_type="routing",
                title="Department assigned",
                message=(
                    f"Your case has been routed to {canonical_department}."
                ),
            )
        )
    db.commit()
    db.refresh(case)

    serialized_case = (
        coordinator_case_to_dict(db, case)
        if current_user.role == Role.COORDINATOR.value
        else admin_case_to_dict(db, case)
    )
    return {
        "message": "Case routed to department successfully.",
        "case": serialized_case,
    }


def get_provisioned_departments(db: Session) -> list[str]:
    provisioned_departments = (
        db.query(models.User.department)
        .filter(
            models.User.role == Role.DEPARTMENT_STAFF.value,
            models.User.department.is_not(None),
        )
        .order_by(func.lower(models.User.department), models.User.department)
        .all()
    )
    departments_by_key = {}
    for (department,) in provisioned_departments:
        if department and department.strip():
            normalized_department = department.strip()
            departments_by_key.setdefault(
                normalized_department.casefold(),
                normalized_department,
            )
    return sorted(departments_by_key.values(), key=str.casefold)


@app.get("/api/v1/departments")
def get_authorized_departments(
    db: Session = Depends(get_db),
    _: models.User = Depends(
        require_roles(Role.ADMIN.value, Role.COORDINATOR.value)
    ),
):
    return get_provisioned_departments(db)


@app.get("/api/v1/admin/cases")
def get_admin_cases(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_roles(Role.ADMIN.value)),
):
    cases = (
        db.query(models.Case)
        .order_by(models.Case.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    coordinator_ids = {
        case.assigned_coordinator_id
        for case in cases
        if case.assigned_coordinator_id is not None
    }
    coordinator_emails = (
        dict(
            db.query(models.User.id, models.User.email)
            .filter(models.User.id.in_(coordinator_ids))
            .all()
        )
        if coordinator_ids
        else {}
    )
    return [
        admin_case_to_dict(
            db,
            case,
            coordinator_emails.get(case.assigned_coordinator_id),
        )
        for case in cases
    ]


@app.get("/api/v1/admin/coordinators")
def get_admin_coordinators(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_roles(Role.ADMIN.value)),
):
    coordinators = (
        db.query(models.User)
        .filter(models.User.role == Role.COORDINATOR.value)
        .order_by(models.User.name.asc())
        .all()
    )
    return [
        {"id": user.id, "name": user.name, "email": user.email}
        for user in coordinators
    ]

@app.get("/api/v1/coordinator/cases")
def get_assigned_cases(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    status: Optional[CaseStatus] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_roles(Role.COORDINATOR.value)
    ),
):
    query = db.query(models.Case).filter(
        models.Case.assigned_coordinator_id == current_user.id
    )

    if status is not None:
        query = query.filter(models.Case.status == status)

    cases = (
        query
        .order_by(models.Case.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    # Query is scoped to this coordinator's assignments; protected text and
    # student identity are omitted from the response.
    return [coordinator_case_to_dict(db, case) for case in cases]


@app.get("/api/v1/coordinator/cases/{case_id}")
def get_assigned_case(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_roles(Role.COORDINATOR.value)
    ),
):
    case = (
        db.query(models.Case)
        .filter(
            models.Case.id == case_id,
            models.Case.assigned_coordinator_id == current_user.id,
        )
        .first()
    )
    if case is None:
        raise HTTPException(
            status_code=404,
            detail="Assigned case not found.",
        )
    return coordinator_case_to_dict(db, case)


@app.patch("/api/v1/coordinator/cases/{case_id}/status")
def update_assigned_case_status(
    case_id: int,
    payload: CoordinatorCaseUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_roles(Role.COORDINATOR.value)
    ),
    _: None = Depends(require_csrf_token),
):
    case = (
        db.query(models.Case)
        .filter(
            models.Case.id == case_id,
            models.Case.assigned_coordinator_id == current_user.id,
        )
        .first()
    )

    if case is None:
        # Do not reveal whether another coordinator owns this case
        raise HTTPException(
            status_code=404,
            detail="Assigned case not found."
        )

    if payload.status == "closed" and case.status != "closed":
        open_tasks = count_open_tasks(db, case.id)
        if open_tasks:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"{open_tasks} department task(s) are still open. "
                    "Complete or cancel them before closing this case."
                ),
            )

    if case.status != payload.status:
        case.status = payload.status
        if payload.status == "closed":
            update_type = "closure"
            title = "Case closed"
            message = payload.closure_outcome.strip()
        else:
            update_type = "status"
            title = {
                "in_review": "Review started",
                "in_progress": "Case in progress",
            }[payload.status]
            message = title + "."
        db.add(
            models.CaseProgressUpdate(
                case_id=case.id,
                author_user_id=current_user.id,
                update_type=update_type,
                title=title,
                message=message,
            )
        )
    db.commit()
    db.refresh(case)

    return {
        "message": "Case status updated successfully.",
        "case": coordinator_case_to_dict(db, case),
    }


@app.post("/api/v1/coordinator/cases/{case_id}/updates", status_code=201)
def create_coordinator_progress_update(
    case_id: int,
    payload: CoordinatorProgressUpdateRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_roles(Role.COORDINATOR.value)
    ),
    _: None = Depends(require_csrf_token),
):
    case = (
        db.query(models.Case)
        .filter(
            models.Case.id == case_id,
            models.Case.assigned_coordinator_id == current_user.id,
        )
        .first()
    )
    if case is None:
        raise HTTPException(status_code=404, detail="Assigned case not found.")

    update = models.CaseProgressUpdate(
        case_id=case.id,
        author_user_id=current_user.id,
        update_type="follow_up",
        title=payload.title.strip(),
        message=payload.message.strip(),
    )
    db.add(update)
    db.commit()
    db.refresh(update)
    return {"update": case_progress_to_dict(update)}


@app.get("/api/v1/coordinator/action-requests")
def get_coordinator_action_requests(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_roles(Role.COORDINATOR.value)
    ),
):
    requests = (
        db.query(models.DepartmentActionRequest)
        .join(
            models.Case,
            models.Case.id == models.DepartmentActionRequest.case_id,
        )
        .filter(
            models.DepartmentActionRequest.coordinator_id == current_user.id,
            models.Case.assigned_coordinator_id == current_user.id,
        )
        .order_by(
            models.DepartmentActionRequest.created_at.desc(),
            models.DepartmentActionRequest.id.desc(),
        )
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [
        student_case_action_request_to_dict(action_request)
        for action_request in requests
    ]


@app.patch("/api/v1/coordinator/action-requests/{request_id}")
def decide_coordinator_action_request(
    request_id: int,
    payload: DepartmentActionRequestDecision,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_roles(Role.COORDINATOR.value)
    ),
    _: None = Depends(require_csrf_token),
):
    action_request = (
        db.query(models.DepartmentActionRequest)
        .join(
            models.Case,
            models.Case.id == models.DepartmentActionRequest.case_id,
        )
        .filter(
            models.DepartmentActionRequest.id == request_id,
            models.DepartmentActionRequest.coordinator_id == current_user.id,
            models.Case.assigned_coordinator_id == current_user.id,
        )
        .first()
    )
    if action_request is None:
        raise HTTPException(
            status_code=404,
            detail="Coordinator action request not found.",
        )
    action_request.status = payload.status
    action_request.handled_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(action_request)
    return student_case_action_request_to_dict(action_request)


@app.get("/api/v1/department/cases")
def get_department_cases(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_roles(Role.DEPARTMENT_STAFF.value)
    ),
):
    cases = (
        db.query(models.Case)
        .filter(models.Case.department == current_user.department)
        .order_by(models.Case.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [department_case_to_dict(db, case) for case in cases]


@app.get("/api/v1/department/cases/{case_id}")
def get_department_case(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_roles(Role.DEPARTMENT_STAFF.value)
    ),
):
    case = (
        db.query(models.Case)
        .filter(
            models.Case.id == case_id,
            models.Case.department == current_user.department,
        )
        .first()
    )
    if case is None:
        raise HTTPException(
            status_code=404,
            detail="Department case not found.",
        )
    return department_case_to_dict(db, case)


@app.post(
    "/api/v1/department/cases/{case_id}/action-requests",
    status_code=201,
)
def create_department_action_request(
    case_id: int,
    payload: DepartmentActionRequestCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_roles(Role.DEPARTMENT_STAFF.value)
    ),
    _: None = Depends(require_csrf_token),
):
    case = (
        db.query(models.Case)
        .filter(
            models.Case.id == case_id,
            models.Case.department == current_user.department,
        )
        .first()
    )
    if case is None:
        raise HTTPException(
            status_code=404,
            detail="Department case not found.",
        )
    if case.assigned_coordinator_id is None:
        raise HTTPException(
            status_code=409,
            detail="This case has no assigned coordinator to contact.",
        )
    action_request = models.DepartmentActionRequest(
        case_id=case.id,
        coordinator_id=case.assigned_coordinator_id,
        sender_user_id=current_user.id,
        request_type=payload.request_type,
        message=payload.message.strip(),
        status="open",
    )
    db.add(action_request)
    db.commit()
    db.refresh(action_request)
    return student_case_action_request_to_dict(action_request)


# ---------------- DEPARTMENT TASKS ----------------

def task_is_overdue(task) -> bool:
    return (
        task.due_date is not None
        and task.status in TASK_OPEN_STATUSES
        and task.due_date < task_today()
    )


def task_event_to_dict(event, actor_name):
    return {
        "id": event.id,
        "from_status": event.from_status,
        "to_status": event.to_status,
        "note": event.note,
        "actor_name": actor_name,
        "created_at": event.created_at,
    }


def get_task_events(db: Session, task_id: int):
    rows = (
        db.query(models.DepartmentTaskEvent, models.User.name)
        .join(
            models.User,
            models.User.id == models.DepartmentTaskEvent.actor_user_id,
        )
        .filter(models.DepartmentTaskEvent.task_id == task_id)
        .order_by(
            models.DepartmentTaskEvent.created_at.asc(),
            models.DepartmentTaskEvent.id.asc(),
        )
        .all()
    )
    return [task_event_to_dict(event, name) for event, name in rows]


def task_base_dict(task):
    return {
        "id": task.id,
        "case_id": task.case_id,
        "department": task.department,
        "title": task.title,
        "instructions": task.instructions,
        "priority": task.priority,
        "due_date": task.due_date,
        "status": task.status,
        "is_overdue": task_is_overdue(task),
        "started_at": task.started_at,
        "completed_at": task.completed_at,
        "completion_note": task.completion_note,
        "assigned_staff_id": task.assigned_staff_id,
        "assigned_staff_at": task.assigned_staff_at,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
    }


def _user_name(db: Session, user_id: int | None) -> str | None:
    if user_id is None:
        return None
    return (
        db.query(models.User.name).filter(models.User.id == user_id).scalar()
    )


def coordinator_task_to_dict(db: Session, task):
    data = task_base_dict(task)
    data["assigned_staff_name"] = _user_name(db, task.assigned_staff_id)
    data["events"] = get_task_events(db, task.id)
    return data


def admin_task_to_dict(db: Session, task):
    """Main Coordinator view: free text is redacted like the case briefs."""
    case = db.query(models.Case).filter(models.Case.id == task.case_id).first()
    student = None
    if case is not None and case.student_id is not None:
        student = (
            db.query(models.User)
            .filter(models.User.id == case.student_id)
            .first()
        )
    data = coordinator_task_to_dict(db, task)
    data["title"] = redact_admin_content(data["title"], student)
    data["instructions"] = redact_admin_content(data["instructions"], student)
    if data["completion_note"]:
        data["completion_note"] = redact_admin_content(
            data["completion_note"], student
        )
    for event in data["events"]:
        if event["note"]:
            event["note"] = redact_admin_content(event["note"], student)
    return data


def department_task_to_dict(db: Session, task, include_case=True, viewer=None):
    """Need-to-know view: identity is limited to what the student consented to,
    and free text written by the Coordinator is scrubbed of other identifiers."""
    case = db.query(models.Case).filter(models.Case.id == task.case_id).first()
    data = task_base_dict(task)
    data["assigned_staff_name"] = _user_name(db, task.assigned_staff_id)
    data["assigned_to_me"] = (
        viewer is not None and task.assigned_staff_id == viewer.id
    )
    data["events"] = get_task_events(db, task.id)
    if case is None:
        return data
    student = (
        db.query(models.User)
        .filter(models.User.id == case.student_id)
        .first()
    )
    case_view = department_case_to_dict(db, case)
    if student is not None:
        allowed = (
            set(case_view["department_consent"]["fields"])
            if case_view["department_identity_consent"]
            else set()
        )
        data["title"] = redact_unselected_student_identity(
            data["title"], student, allowed
        )
        data["instructions"] = redact_unselected_student_identity(
            data["instructions"], student, allowed
        )
    if include_case:
        data["case"] = case_view
    return data


def _canonical_department(db: Session, name: str) -> str | None:
    wanted = name.strip().casefold()
    return next(
        (
            department
            for department in get_provisioned_departments(db)
            if department.casefold() == wanted
        ),
        None,
    )


def _get_coordinator_case(db: Session, case_id: int, coordinator):
    case = (
        db.query(models.Case)
        .filter(
            models.Case.id == case_id,
            models.Case.assigned_coordinator_id == coordinator.id,
        )
        .first()
    )
    if case is None:
        raise HTTPException(status_code=404, detail="Assigned case not found.")
    return case


def _get_coordinator_task(db: Session, task_id: int, coordinator):
    task = (
        db.query(models.DepartmentTask)
        .join(
            models.Case,
            models.Case.id == models.DepartmentTask.case_id,
        )
        .filter(
            models.DepartmentTask.id == task_id,
            models.Case.assigned_coordinator_id == coordinator.id,
        )
        .first()
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    return task


def _require_staff_department(staff) -> str:
    department = (staff.department or "").strip()
    if not department:
        raise HTTPException(
            status_code=403,
            detail="This account has no provisioned department.",
        )
    return department


def _staff_task_filter(staff):
    """Tasks a staff member may see: their own plus the unclaimed pool."""
    return or_(
        models.DepartmentTask.assigned_staff_id.is_(None),
        models.DepartmentTask.assigned_staff_id == staff.id,
    )


def _department_staff_users(db: Session, department: str):
    wanted = (department or "").strip().casefold()
    users = (
        db.query(models.User)
        .filter(
            models.User.role == Role.DEPARTMENT_STAFF.value,
            models.User.department.is_not(None),
        )
        .order_by(func.lower(models.User.name), models.User.id)
        .all()
    )
    return [
        user for user in users
        if (user.department or "").strip().casefold() == wanted
    ]


def _get_department_task(db: Session, task_id: int, staff):
    department = _require_staff_department(staff)
    task = (
        db.query(models.DepartmentTask)
        .filter(
            models.DepartmentTask.id == task_id,
            models.DepartmentTask.department == department,
            _staff_task_filter(staff),
        )
        .first()
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    return task


def _record_task_event(db, task, actor, from_status, to_status, note=None):
    db.add(
        models.DepartmentTaskEvent(
            task_id=task.id,
            actor_user_id=actor.id,
            from_status=from_status,
            to_status=to_status,
            note=note,
        )
    )


def _student_task_update(db, case, author, title, message):
    # Student-visible text is deliberately generic: it never repeats the
    # Coordinator's instructions or the department's notes.
    db.add(
        models.CaseProgressUpdate(
            case_id=case.id,
            author_user_id=author.id,
            update_type="task",
            title=title,
            message=message,
        )
    )


def count_open_tasks(db: Session, case_id: int) -> int:
    return (
        db.query(func.count(models.DepartmentTask.id))
        .filter(
            models.DepartmentTask.case_id == case_id,
            models.DepartmentTask.status.in_(TASK_OPEN_STATUSES),
        )
        .scalar()
        or 0
    )


def _set_task_assignee(db: Session, task, staff_id: int | None, actor) -> bool:
    """Assign an open task to one staff member of its department, or return
    it to the department pool. Returns True when something changed."""
    if task.status not in TASK_OPEN_STATUSES:
        raise HTTPException(
            status_code=409,
            detail="Only open tasks can be assigned to a staff member.",
        )
    if staff_id is None:
        if task.assigned_staff_id is None:
            return False
        task.assigned_staff_id = None
        task.assigned_staff_at = None
        _record_task_event(
            db, task, actor, task.status, task.status,
            "Returned to the department pool.",
        )
        return True

    staff = next(
        (
            user for user in _department_staff_users(db, task.department)
            if user.id == staff_id
        ),
        None,
    )
    if staff is None:
        raise HTTPException(
            status_code=400,
            detail=f"Choose a staff member who works in {task.department}.",
        )
    if task.assigned_staff_id == staff.id:
        return False
    task.assigned_staff_id = staff.id
    task.assigned_staff_at = datetime.now(timezone.utc)
    _record_task_event(
        db, task, actor, task.status, task.status,
        f"Assigned to {staff.name}.",
    )
    return True


def _create_task_for_case(db: Session, case, payload, actor):
    if case.status == "closed":
        raise HTTPException(
            status_code=409,
            detail="Tasks cannot be added to a closed case.",
        )
    department = _canonical_department(db, payload.department)
    if department is None:
        raise HTTPException(
            status_code=400,
            detail="Department must have a provisioned department staff account.",
        )

    task = models.DepartmentTask(
        case_id=case.id,
        department=department,
        assigned_by_user_id=actor.id,
        title=payload.title,
        instructions=payload.instructions,
        priority=payload.priority,
        due_date=payload.due_date,
        status="assigned",
    )
    db.add(task)
    db.flush()
    _record_task_event(db, task, actor, None, "assigned")
    if payload.assigned_staff_id is not None:
        _set_task_assignee(db, task, payload.assigned_staff_id, actor)
    _student_task_update(
        db,
        case,
        actor,
        "Support task assigned",
        f"A support task was assigned to {department}.",
    )
    return task


@app.post("/api/v1/coordinator/cases/{case_id}/tasks", status_code=201)
def create_department_task(
    case_id: int,
    payload: DepartmentTaskCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_roles(Role.COORDINATOR.value)
    ),
    _: None = Depends(require_csrf_token),
):
    case = _get_coordinator_case(db, case_id, current_user)
    task = _create_task_for_case(db, case, payload, current_user)
    db.commit()
    db.refresh(task)
    return {
        "message": "Task assigned to department.",
        "task": coordinator_task_to_dict(db, task),
    }


@app.post("/api/v1/admin/cases/{case_id}/tasks", status_code=201)
def admin_create_department_task(
    case_id: int,
    payload: DepartmentTaskCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles(Role.ADMIN.value)),
    _: None = Depends(require_csrf_token),
):
    """The Main Coordinator sends a task to a department for any case."""
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    task = _create_task_for_case(db, case, payload, current_user)
    db.commit()
    db.refresh(task)
    return {
        "message": "Task sent to department.",
        "task": admin_task_to_dict(db, task),
    }


@app.get("/api/v1/coordinator/cases/{case_id}/tasks")
def get_case_tasks(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_roles(Role.COORDINATOR.value)
    ),
):
    case = _get_coordinator_case(db, case_id, current_user)
    tasks = (
        db.query(models.DepartmentTask)
        .filter(models.DepartmentTask.case_id == case.id)
        .order_by(
            models.DepartmentTask.created_at.desc(),
            models.DepartmentTask.id.desc(),
        )
        .all()
    )
    return [coordinator_task_to_dict(db, task) for task in tasks]


@app.get("/api/v1/coordinator/tasks")
def get_coordinator_tasks(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    status: Optional[Literal[
        "assigned", "in_progress", "completed", "cancelled"
    ]] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_roles(Role.COORDINATOR.value)
    ),
):
    query = (
        db.query(models.DepartmentTask)
        .join(
            models.Case,
            models.Case.id == models.DepartmentTask.case_id,
        )
        .filter(models.Case.assigned_coordinator_id == current_user.id)
    )
    if status is not None:
        query = query.filter(models.DepartmentTask.status == status)
    tasks = (
        query.order_by(
            models.DepartmentTask.created_at.desc(),
            models.DepartmentTask.id.desc(),
        )
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [coordinator_task_to_dict(db, task) for task in tasks]


def _apply_task_review(db: Session, task, payload, actor) -> None:
    previous = task.status

    if payload.action == "cancel":
        if previous not in TASK_OPEN_STATUSES:
            raise HTTPException(
                status_code=409,
                detail="Only open tasks can be cancelled.",
            )
        task.status = "cancelled"
    else:
        if previous != "completed":
            raise HTTPException(
                status_code=409,
                detail="Only completed tasks can be reopened.",
            )
        case = (
            db.query(models.Case)
            .filter(models.Case.id == task.case_id)
            .first()
        )
        if case is not None and case.status == "closed":
            raise HTTPException(
                status_code=409,
                detail="Tasks on a closed case cannot be reopened.",
            )
        task.status = "assigned"
        task.started_at = None
        task.completed_at = None
        task.completed_by_user_id = None
        task.completion_note = None

    _record_task_event(db, task, actor, previous, task.status, payload.note)


@app.patch("/api/v1/coordinator/tasks/{task_id}")
def review_department_task(
    task_id: int,
    payload: CoordinatorTaskDecision,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_roles(Role.COORDINATOR.value)
    ),
    _: None = Depends(require_csrf_token),
):
    task = _get_coordinator_task(db, task_id, current_user)
    _apply_task_review(db, task, payload, current_user)
    db.commit()
    db.refresh(task)
    return {
        "message": "Task updated.",
        "task": coordinator_task_to_dict(db, task),
    }


@app.patch("/api/v1/coordinator/tasks/{task_id}/assignee")
def assign_task_to_staff(
    task_id: int,
    payload: TaskAssigneeUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_roles(Role.COORDINATOR.value)
    ),
    _: None = Depends(require_csrf_token),
):
    """The Department Coordinator hands a task to one staff member."""
    task = _get_coordinator_task(db, task_id, current_user)
    _set_task_assignee(db, task, payload.staff_id, current_user)
    db.commit()
    db.refresh(task)
    return {
        "message": "Task assignment updated.",
        "task": coordinator_task_to_dict(db, task),
    }


@app.get("/api/v1/department-staff")
def get_department_staff(
    department: str = Query(min_length=2, max_length=100),
    db: Session = Depends(get_db),
    _: models.User = Depends(
        require_roles(Role.ADMIN.value, Role.COORDINATOR.value)
    ),
):
    canonical = _canonical_department(db, department)
    if canonical is None:
        raise HTTPException(status_code=404, detail="Department not found.")
    return [
        {"id": user.id, "name": user.name, "email": user.email}
        for user in _department_staff_users(db, canonical)
    ]


# ---- Main Coordinator (admin) task oversight ----

def _get_admin_task(db: Session, task_id: int):
    task = (
        db.query(models.DepartmentTask)
        .filter(models.DepartmentTask.id == task_id)
        .first()
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    return task


@app.get("/api/v1/admin/tasks")
def get_admin_tasks(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    status: Optional[Literal[
        "assigned", "in_progress", "completed", "cancelled"
    ]] = None,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_roles(Role.ADMIN.value)),
):
    query = db.query(models.DepartmentTask)
    if status is not None:
        query = query.filter(models.DepartmentTask.status == status)
    tasks = (
        query.order_by(
            models.DepartmentTask.created_at.desc(),
            models.DepartmentTask.id.desc(),
        )
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [admin_task_to_dict(db, task) for task in tasks]


@app.patch("/api/v1/admin/tasks/{task_id}")
def admin_review_department_task(
    task_id: int,
    payload: CoordinatorTaskDecision,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles(Role.ADMIN.value)),
    _: None = Depends(require_csrf_token),
):
    task = _get_admin_task(db, task_id)
    _apply_task_review(db, task, payload, current_user)
    db.commit()
    db.refresh(task)
    return {"message": "Task updated.", "task": admin_task_to_dict(db, task)}


@app.patch("/api/v1/admin/tasks/{task_id}/assignee")
def admin_assign_task_to_staff(
    task_id: int,
    payload: TaskAssigneeUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles(Role.ADMIN.value)),
    _: None = Depends(require_csrf_token),
):
    task = _get_admin_task(db, task_id)
    _set_task_assignee(db, task, payload.staff_id, current_user)
    db.commit()
    db.refresh(task)
    return {
        "message": "Task assignment updated.",
        "task": admin_task_to_dict(db, task),
    }


@app.get("/api/v1/department/tasks/summary")
def get_department_task_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_roles(Role.DEPARTMENT_STAFF.value)
    ),
):
    department = _require_staff_department(current_user)
    tasks = (
        db.query(models.DepartmentTask)
        .filter(
            models.DepartmentTask.department == department,
            _staff_task_filter(current_user),
        )
        .all()
    )
    summary = {status: 0 for status in TASK_STATUSES}
    for task in tasks:
        summary[task.status] = summary.get(task.status, 0) + 1
    summary["overdue"] = sum(1 for task in tasks if task_is_overdue(task))
    summary["total"] = len(tasks)
    open_tasks = [task for task in tasks if task.status in TASK_OPEN_STATUSES]
    summary["mine"] = sum(
        1 for task in open_tasks if task.assigned_staff_id == current_user.id
    )
    summary["unassigned"] = sum(
        1 for task in open_tasks if task.assigned_staff_id is None
    )
    return summary


@app.get("/api/v1/department/tasks")
def get_department_tasks(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    status: Optional[Literal[
        "assigned", "in_progress", "completed", "cancelled"
    ]] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_roles(Role.DEPARTMENT_STAFF.value)
    ),
):
    department = _require_staff_department(current_user)
    query = db.query(models.DepartmentTask).filter(
        models.DepartmentTask.department == department,
        _staff_task_filter(current_user),
    )
    if status is not None:
        query = query.filter(models.DepartmentTask.status == status)
    tasks = (
        query.order_by(
            models.DepartmentTask.created_at.desc(),
            models.DepartmentTask.id.desc(),
        )
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [
        department_task_to_dict(db, task, viewer=current_user)
        for task in tasks
    ]


@app.get("/api/v1/department/tasks/{task_id}")
def get_department_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_roles(Role.DEPARTMENT_STAFF.value)
    ),
):
    task = _get_department_task(db, task_id, current_user)
    return department_task_to_dict(db, task, viewer=current_user)


@app.patch("/api/v1/department/tasks/{task_id}/status")
def update_department_task_status(
    task_id: int,
    payload: DepartmentTaskStatusUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_roles(Role.DEPARTMENT_STAFF.value)
    ),
    _: None = Depends(require_csrf_token),
):
    task = _get_department_task(db, task_id, current_user)
    previous = task.status
    if payload.status not in TASK_STAFF_TRANSITIONS.get(previous, set()):
        raise HTTPException(
            status_code=409,
            detail=(
                f"A task that is {previous.replace('_', ' ')} cannot be "
                f"marked {payload.status.replace('_', ' ')}."
            ),
        )

    now = datetime.now(timezone.utc)
    if task.assigned_staff_id is None:
        # Working on a pool task makes it yours.
        task.assigned_staff_id = current_user.id
        task.assigned_staff_at = now
    task.status = payload.status
    if payload.status == "in_progress":
        task.started_at = now
    else:
        if task.started_at is None:
            task.started_at = now
        task.completed_at = now
        task.completed_by_user_id = current_user.id
        task.completion_note = payload.note
    _record_task_event(
        db, task, current_user, previous, payload.status, payload.note
    )

    if payload.status == "completed":
        case = (
            db.query(models.Case)
            .filter(models.Case.id == task.case_id)
            .first()
        )
        if case is not None:
            _student_task_update(
                db,
                case,
                current_user,
                "Support task completed",
                f"{task.department} completed a support task.",
            )
    db.commit()
    db.refresh(task)
    return {
        "message": "Task status updated.",
        "task": department_task_to_dict(db, task, viewer=current_user),
    }


@app.post("/api/v1/department/tasks/{task_id}/claim")
def claim_department_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_roles(Role.DEPARTMENT_STAFF.value)
    ),
    _: None = Depends(require_csrf_token),
):
    """Take an unassigned task from the department pool."""
    task = _get_department_task(db, task_id, current_user)
    if task.status not in TASK_OPEN_STATUSES:
        raise HTTPException(
            status_code=409,
            detail="Only open tasks can be claimed.",
        )
    if task.assigned_staff_id is not None:
        raise HTTPException(
            status_code=409,
            detail="This task is already assigned to you."
            if task.assigned_staff_id == current_user.id
            else "This task has already been claimed.",
        )
    now = datetime.now(timezone.utc)
    # Conditional update so two staff members cannot both win a claim.
    claimed = (
        db.query(models.DepartmentTask)
        .filter(
            models.DepartmentTask.id == task.id,
            models.DepartmentTask.assigned_staff_id.is_(None),
            models.DepartmentTask.status.in_(TASK_OPEN_STATUSES),
        )
        .update(
            {
                "assigned_staff_id": current_user.id,
                "assigned_staff_at": now,
            },
            synchronize_session=False,
        )
    )
    if claimed != 1:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="This task has just been claimed by someone else.",
        )
    db.refresh(task)
    _record_task_event(
        db, task, current_user, task.status, task.status,
        f"Claimed by {current_user.name}.",
    )
    db.commit()
    db.refresh(task)
    return {
        "message": "Task claimed.",
        "task": department_task_to_dict(db, task, viewer=current_user),
    }


# ---------------- INTERNAL MESSAGING ----------------
# Main Coordinator (admin), Department Coordinators (coordinator) and
# department staff can message each other. Students never use this inbox.

MESSAGE_ROLES = (
    Role.ADMIN.value,
    Role.COORDINATOR.value,
    Role.DEPARTMENT_STAFF.value,
)
ROLE_LABELS = {
    Role.ADMIN.value: "Main Coordinator",
    Role.COORDINATOR.value: "Department Coordinator",
    Role.DEPARTMENT_STAFF.value: "Department Staff",
    Role.STUDENT.value: "Student",
}
MAIN_COORDINATOR_LABEL = "Main Coordinator"


def _admin_users(db: Session):
    return (
        db.query(models.User)
        .filter(models.User.role == Role.ADMIN.value)
        .order_by(models.User.id)
        .all()
    )


def _user_can_view_case(db: Session, user, case) -> bool:
    if user.role == Role.ADMIN.value:
        return True
    if user.role == Role.COORDINATOR.value:
        return case.assigned_coordinator_id == user.id
    if user.role == Role.DEPARTMENT_STAFF.value:
        department = (user.department or "").strip()
        if not department:
            return False
        if case.department == department:
            return True
        return (
            db.query(models.DepartmentTask.id)
            .filter(
                models.DepartmentTask.case_id == case.id,
                models.DepartmentTask.department == department,
            )
            .first()
            is not None
        )
    return False


def _messageable_coordinators(db: Session, sender):
    if sender.role == Role.ADMIN.value:
        users = (
            db.query(models.User)
            .filter(models.User.role == Role.COORDINATOR.value)
            .order_by(func.lower(models.User.name), models.User.id)
            .all()
        )
        return users
    if sender.role != Role.DEPARTMENT_STAFF.value:
        return []
    department = (sender.department or "").strip()
    routed = (
        db.query(models.Case.assigned_coordinator_id)
        .filter(
            models.Case.department == department,
            models.Case.assigned_coordinator_id.is_not(None),
        )
        .all()
    )
    tasked = (
        db.query(models.Case.assigned_coordinator_id)
        .join(
            models.DepartmentTask,
            models.DepartmentTask.case_id == models.Case.id,
        )
        .filter(
            models.DepartmentTask.department == department,
            models.Case.assigned_coordinator_id.is_not(None),
        )
        .all()
    )
    coordinator_ids = {row[0] for row in routed} | {row[0] for row in tasked}
    if not coordinator_ids:
        return []
    return (
        db.query(models.User)
        .filter(
            models.User.id.in_(coordinator_ids),
            models.User.role == Role.COORDINATOR.value,
        )
        .order_by(func.lower(models.User.name), models.User.id)
        .all()
    )


def _messageable_departments(db: Session, sender) -> list[str]:
    departments = get_provisioned_departments(db)
    if sender.role == Role.DEPARTMENT_STAFF.value:
        own = (sender.department or "").strip().casefold()
        departments = [
            name for name in departments if name.casefold() != own
        ]
    return departments


def _message_targets(db: Session, sender) -> dict:
    return {
        "main_coordinator": sender.role
        in (Role.COORDINATOR.value, Role.DEPARTMENT_STAFF.value),
        "coordinators": _messageable_coordinators(db, sender),
        "departments": _messageable_departments(db, sender),
    }


@app.get("/api/v1/messages/recipients")
def get_message_recipients(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles(*MESSAGE_ROLES)),
):
    targets = _message_targets(db, current_user)
    return {
        "main_coordinator": targets["main_coordinator"],
        "coordinators": [
            {"id": user.id, "name": user.name}
            for user in targets["coordinators"]
        ],
        "departments": targets["departments"],
    }


def _message_reply_target(sender, viewer):
    """Where a Reply button should send its answer (validated again on send)."""
    if sender.id == viewer.id:
        return None
    if sender.role == Role.ADMIN.value:
        return {
            "recipient_type": "main_coordinator",
            "label": MAIN_COORDINATOR_LABEL,
        }
    if sender.role == Role.COORDINATOR.value:
        return {
            "recipient_type": "coordinator",
            "recipient_user_id": sender.id,
            "label": sender.name,
        }
    department = (sender.department or "").strip()
    if not department:
        return None
    return {
        "recipient_type": "department",
        "recipient_department": department,
        "label": department,
    }


def _redact_message_text(db: Session, text: str, viewer, case, student) -> str:
    if viewer.role == Role.ADMIN.value:
        return redact_admin_content(text, student)
    if (
        viewer.role == Role.DEPARTMENT_STAFF.value
        and case is not None
        and student is not None
    ):
        consent = department_consent_to_dict(db, case)
        allowed = set(consent["fields"]) if consent["active"] else set()
        return redact_unselected_student_identity(text, student, allowed)
    return text


def _serialize_inbox_messages(db: Session, rows, viewer):
    if not rows:
        return []
    user_ids = {row.sender_user_id for row in rows}
    users = {
        user.id: user
        for user in db.query(models.User)
        .filter(models.User.id.in_(user_ids))
        .all()
    }
    case_ids = {row.case_id for row in rows if row.case_id is not None}
    cases = (
        {
            case.id: case
            for case in db.query(models.Case)
            .filter(models.Case.id.in_(case_ids))
            .all()
        }
        if case_ids
        else {}
    )
    students = {}
    for case in cases.values():
        if case.student_id is not None and case.student_id not in students:
            students[case.student_id] = (
                db.query(models.User)
                .filter(models.User.id == case.student_id)
                .first()
            )

    result = []
    for row in rows:
        sender = users.get(row.sender_user_id)
        case = cases.get(row.case_id) if row.case_id is not None else None
        student = students.get(case.student_id) if case is not None else None
        case_title = None
        if case is not None and _user_can_view_case(db, viewer, case):
            case_title = _redact_message_text(
                db, case.title, viewer, case, student
            )
        result.append(
            {
                "id": row.id,
                "group_id": row.group_id,
                "sender_id": row.sender_user_id,
                "sender_name": sender.name if sender else "Unknown sender",
                "sender_role": sender.role if sender else None,
                "sender_role_label": (
                    ROLE_LABELS.get(sender.role, sender.role)
                    if sender
                    else None
                ),
                "sender_department": (
                    (sender.department or None)
                    if sender is not None
                    and sender.role == Role.DEPARTMENT_STAFF.value
                    else None
                ),
                "audience_label": row.audience_label,
                "case_id": row.case_id,
                "case_title": case_title,
                "subject": _redact_message_text(
                    db, row.subject, viewer, case, student
                ),
                "body": _redact_message_text(
                    db, row.body, viewer, case, student
                ),
                "read": row.read_at is not None,
                "read_at": row.read_at,
                "created_at": row.created_at,
                "reply_target": (
                    _message_reply_target(sender, viewer)
                    if sender is not None
                    else None
                ),
            }
        )
    return result


@app.post("/api/v1/messages", status_code=201)
def send_internal_message(
    payload: InternalMessageCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles(*MESSAGE_ROLES)),
    _: None = Depends(require_csrf_token),
):
    targets = _message_targets(db, current_user)

    if payload.recipient_type == "main_coordinator":
        if not targets["main_coordinator"]:
            raise HTTPException(
                status_code=403,
                detail="You cannot message the Main Coordinator.",
            )
        recipients = [
            user for user in _admin_users(db) if user.id != current_user.id
        ]
        audience = MAIN_COORDINATOR_LABEL
    elif payload.recipient_type == "coordinator":
        recipient = next(
            (
                user for user in targets["coordinators"]
                if user.id == payload.recipient_user_id
            ),
            None,
        )
        if recipient is None:
            raise HTTPException(
                status_code=403,
                detail="That coordinator is not available for you to message.",
            )
        recipients = [recipient]
        audience = f"{recipient.name} (Department Coordinator)"
    else:
        wanted = (payload.recipient_department or "").casefold()
        department = next(
            (
                name for name in targets["departments"]
                if name.casefold() == wanted
            ),
            None,
        )
        if department is None:
            raise HTTPException(
                status_code=400,
                detail="Choose another provisioned department to message.",
            )
        recipients = [
            user
            for user in _department_staff_users(db, department)
            if user.id != current_user.id
        ]
        audience = department

    if not recipients:
        raise HTTPException(
            status_code=409,
            detail="There is nobody to receive this message yet.",
        )

    if payload.case_id is not None:
        case = (
            db.query(models.Case)
            .filter(models.Case.id == payload.case_id)
            .first()
        )
        if case is None or not _user_can_view_case(db, current_user, case):
            raise HTTPException(status_code=404, detail="Case not found.")

    group_id = str(uuid.uuid4())
    for recipient in recipients:
        db.add(
            models.InternalMessage(
                group_id=group_id,
                sender_user_id=current_user.id,
                recipient_user_id=recipient.id,
                audience_label=audience,
                case_id=payload.case_id,
                subject=payload.subject,
                body=payload.body,
            )
        )
    db.commit()
    return {
        "message": f"Message sent to {audience}.",
        "group_id": group_id,
        "recipient_count": len(recipients),
    }


@app.get("/api/v1/messages/inbox")
def get_message_inbox(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    unread_only: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles(*MESSAGE_ROLES)),
):
    query = db.query(models.InternalMessage).filter(
        models.InternalMessage.recipient_user_id == current_user.id
    )
    if unread_only:
        query = query.filter(models.InternalMessage.read_at.is_(None))
    rows = (
        query.order_by(
            models.InternalMessage.created_at.desc(),
            models.InternalMessage.id.desc(),
        )
        .offset(skip)
        .limit(limit)
        .all()
    )
    return _serialize_inbox_messages(db, rows, current_user)


@app.get("/api/v1/messages/unread-count")
def get_unread_message_count(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles(*MESSAGE_ROLES)),
):
    unread = (
        db.query(func.count(models.InternalMessage.id))
        .filter(
            models.InternalMessage.recipient_user_id == current_user.id,
            models.InternalMessage.read_at.is_(None),
        )
        .scalar()
        or 0
    )
    return {"unread": unread}


@app.get("/api/v1/messages/sent")
def get_sent_messages(
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles(*MESSAGE_ROLES)),
):
    rows = (
        db.query(models.InternalMessage)
        .filter(models.InternalMessage.sender_user_id == current_user.id)
        .order_by(
            models.InternalMessage.created_at.desc(),
            models.InternalMessage.id.desc(),
        )
        .limit(500)
        .all()
    )
    groups: dict[str, dict] = {}
    for row in rows:
        group = groups.get(row.group_id)
        if group is None:
            if len(groups) >= limit:
                continue
            group = groups[row.group_id] = {
                "group_id": row.group_id,
                "audience_label": row.audience_label,
                "case_id": row.case_id,
                "subject": row.subject,
                "body": row.body,
                "created_at": row.created_at,
                "recipient_count": 0,
                "read_count": 0,
            }
        group["recipient_count"] += 1
        if row.read_at is not None:
            group["read_count"] += 1
    return list(groups.values())


@app.patch("/api/v1/messages/{message_id}/read")
def mark_message_read(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles(*MESSAGE_ROLES)),
    _: None = Depends(require_csrf_token),
):
    message = (
        db.query(models.InternalMessage)
        .filter(
            models.InternalMessage.id == message_id,
            models.InternalMessage.recipient_user_id == current_user.id,
        )
        .first()
    )
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found.")
    if message.read_at is None:
        message.read_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(message)
    return {"id": message.id, "read": True, "read_at": message.read_at}


@app.get("/api/v1/notifications")
def get_student_notifications(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_roles(Role.STUDENT.value)
    ),
):
    cases = (
        db.query(models.Case)
        .filter(models.Case.student_id == current_user.id)
        .order_by(models.Case.created_at.desc())
        .all()
    )
    return [
        {
            "id": f"case-submitted-{case.id}",
            "case_id": case.id,
            "title": case.title,
            "status": case.status,
            "created_at": case.created_at,
        }
        for case in cases
    ]


# Students can access their own cases only.
@app.get("/api/v1/cases/{case_id}")
def get_case(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles(Role.STUDENT.value)),
):
    case = (
        db.query(models.Case)
        .filter(
            models.Case.id == case_id,
            models.Case.student_id == current_user.id,
        )
        .first()
    )

    if case is None:
        raise HTTPException(
            status_code=404,
            detail="Case not found.",
        )

    return student_case_to_dict(db, case, current_user)


# Updates remain disabled until coordinator scope is implemented.
@app.patch(
    "/api/v1/cases/{case_id}",
    dependencies=[
        Depends(require_roles(Role.COORDINATOR.value)),
        Depends(require_csrf_token),
    ],
)
def update_case(
    case_id: int,
):
    # Fail closed until assignment and case scope checks exist.
    raise HTTPException(
        status_code=403,
        detail=(
            f"Coordinator case scope must be verified before updates "
            f"to case {case_id} are enabled."
        ),
    )

@app.patch("/api/v1/cases/{case_id}/identity")
def update_case_identity(
    case_id: int,
    payload: CaseIdentityUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles(Role.STUDENT.value)),
    _: None = Depends(require_csrf_token),
):
    case = (
        db.query(models.Case)
        .filter(
            models.Case.id == case_id,
            models.Case.student_id == current_user.id,
        )
        .first()
    )

    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")

    case.identity_mode = payload.identity_mode
    db.commit()
    db.refresh(case)

    return {
        "message": "Identity mode updated successfully.",
        "case": student_case_to_dict(db, case, current_user),
    }

@app.post("/api/v1/cases/{case_id}/consent", status_code=201)
def grant_case_consent(
    case_id: int,
    payload: ConsentRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles(Role.STUDENT.value)),
    _: None = Depends(require_csrf_token),
):
    case = (
        db.query(models.Case)
        .filter(
            models.Case.id == case_id,
            models.Case.student_id == current_user.id,
        )
        .first()
    )

    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")

    raise HTTPException(
        status_code=403,
        detail=(
            "Identity consent is recorded at submission for the assigned "
            "department. Assigned Coordinators already have case-scoped access."
        ),
    )


@app.patch("/api/v1/cases/{case_id}/consent/{consent_id}/withdraw")
def withdraw_case_consent(
    case_id: int,
    consent_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles(Role.STUDENT.value)),
    _: None = Depends(require_csrf_token),
):
    consent = (
        db.query(models.CaseConsent)
        .join(models.Case, models.CaseConsent.case_id == models.Case.id)
        .filter(
            models.CaseConsent.id == consent_id,
            models.CaseConsent.case_id == case_id,
            models.Case.student_id == current_user.id,
        )
        .first()
    )

    if consent is None:
        raise HTTPException(status_code=404, detail="Consent not found.")

    if consent.withdrawn_at is None:
        consent.granted = False
        consent.withdrawn_at = datetime.now(timezone.utc)

        db.add(
            models.CaseDisclosureAudit(
                case_id=case_id,
                actor_user_id=current_user.id,
                recipient=consent.recipient,
                purpose=consent.purpose,
                decision="consent_withdrawn",
                reason="Student withdrew consent.",
            )
        )

        db.commit()

    return {"message": "Consent withdrawal recorded."}

@app.get("/api/v1/cases/{case_id}/consent")
def get_case_consent(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles(Role.STUDENT.value)),
):
    case = (
        db.query(models.Case)
        .filter(
            models.Case.id == case_id,
            models.Case.student_id == current_user.id,
        )
        .first()
    )

    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")

    consents = (
        db.query(models.CaseConsent)
        .filter(
            models.CaseConsent.case_id == case_id,
            models.CaseConsent.recipient
            == DepartmentIdentityConsentRecipient,
        )
        .order_by(models.CaseConsent.created_at.desc())
        .all()
    )

    return [
        {
            "id": consent.id,
            "purpose": consent.purpose,
            "recipient": consent.recipient,
            "scope": consent.scope,
            "granted": consent.granted,
            "granted_at": consent.granted_at,
            "withdrawn_at": consent.withdrawn_at,
        }
        for consent in consents
    ]
@app.post("/api/v1/coordinator/cases/{case_id}/identity-disclosure")
def disclose_case_identity_to_coordinator(
    case_id: int,
    payload: DisclosureRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_roles(Role.COORDINATOR.value)
    ),
    _: None = Depends(require_csrf_token),
):
    case = (
        db.query(models.Case)
        .filter(
            models.Case.id == case_id,
            models.Case.assigned_coordinator_id == current_user.id,
        )
        .first()
    )
    if case is None:
        raise HTTPException(status_code=404, detail="Assigned case not found.")

    student = (
        db.query(models.User)
        .filter(models.User.id == case.student_id)
        .first()
    )
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found.")
    record_disclosure_decision(
        db=db,
        case_id=case_id,
        actor_user_id=current_user.id,
        recipient=current_user.email.strip().lower(),
        purpose=payload.purpose.strip(),
        allowed=True,
        reason="Assigned Coordinator accessed the case identity details.",
    )
    return {
        "student_name": student.name,
        "student_email": student.email,
        "student_phone": student.phone,
        "student_department": student.department,
    }


@app.get("/api/v1/cases/{case_id}/disclosure-audit")
def get_case_disclosure_audit(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles(Role.STUDENT.value)),
):
    case = (
        db.query(models.Case)
        .filter(
            models.Case.id == case_id,
            models.Case.student_id == current_user.id,
        )
        .first()
    )

    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")

    records = (
        db.query(models.CaseDisclosureAudit)
        .filter(models.CaseDisclosureAudit.case_id == case_id)
        .order_by(models.CaseDisclosureAudit.created_at.desc())
        .all()
    )

    return [
        {
            "recipient": record.recipient,
            "purpose": record.purpose,
            "decision": record.decision,
            "reason": record.reason,
            "created_at": record.created_at,
        }
        for record in records
    ]

def record_disclosure_decision(
    db: Session,
    case_id: int,
    actor_user_id: int,
    recipient: str,
    purpose: str,
    allowed: bool,
    reason: str,
):
    audit = models.CaseDisclosureAudit(
        case_id=case_id,
        actor_user_id=actor_user_id,
        recipient=recipient,
        purpose=purpose,
        decision="allowed" if allowed else "denied",
        reason=reason,
    )

    db.add(audit)
    db.commit()
    db.refresh(audit)

    return audit
