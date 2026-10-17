
import hashlib
import logging
import os
import secrets
import smtplib
import threading
import time
from datetime import datetime, timedelta, timezone
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
from sqlalchemy import func
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

class CaseIdentityUpdate(BaseModel):
    identity_mode: Literal["identified", "restricted", "anonymous"]


class CaseCreate(BaseModel):
    category: str = Field(min_length=2, max_length=50)
    title: str = Field(min_length=3, max_length=150)
    description: str = Field(min_length=10, max_length=5000)
    identity_mode: Literal["identified", "restricted", "anonymous"] = "identified"



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
    status: CaseStatus

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


def coordinator_case_to_dict(case):
    return {
        "id": case.id,
        "category": case.category,
        "status": case.status,
        "department": case.department,
        "created_at": case.created_at,
    }

def department_case_to_dict(case):
    return {
        "id": case.id,
        "category": case.category,
        "status": case.status,
        "created_at": case.created_at,
    }


def admin_case_to_dict(case, coordinator_email=None):
    return {
        "id": case.id,
        "category": case.category,
        "status": case.status,
        "created_at": case.created_at,
        "assigned_coordinator_id": case.assigned_coordinator_id,
        "assigned_coordinator_email": coordinator_email,
        "department": case.department,
    }


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
    db.commit()
    db.refresh(new_case)

    return case_to_dict(new_case, current_user)


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

    return [case_to_dict(case, current_user) for case in cases]


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
        db.refresh(case)
        return {
            "message": "Case assigned and coordinator notified.",
            "assignment_status": "assigned",
            "coordinator_email": coordinator_email,
            "login_url": f"{base_url}/login",
            "dashboard_url": f"{base_url}/dashboard/coordinator",
            "case": admin_case_to_dict(case, coordinator_email),
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
        "case": admin_case_to_dict(case),
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

    case.department = canonical_department
    db.commit()
    db.refresh(case)

    serialized_case = (
        coordinator_case_to_dict(case)
        if current_user.role == Role.COORDINATOR.value
        else admin_case_to_dict(case)
    )
    return {
        "message": "Case routed to department successfully.",
        "case": serialized_case,
    }


@app.get("/api/v1/departments")
def get_authorized_departments(
    db: Session = Depends(get_db),
    _: models.User = Depends(
        require_roles(Role.ADMIN.value, Role.COORDINATOR.value)
    ),
):
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
    return [coordinator_case_to_dict(case) for case in cases]


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
    return coordinator_case_to_dict(case)


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

    case.status = payload.status

    db.commit()
    db.refresh(case)

    return {
        "message": "Case status updated successfully.",
        "case": coordinator_case_to_dict(case),
    }


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
    return [department_case_to_dict(case) for case in cases]


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
    return department_case_to_dict(case)


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

    return case_to_dict(case, current_user)


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
        "case": case_to_dict(case, current_user),
    }

@app.post("/api/v1/cases/{case_id}/consent", status_code=201)
def grant_case_consent(
    case_id: int,
    payload: ConsentRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles(Role.STUDENT.value)),
    _: None = Depends(require_csrf_token),
):
    purpose = payload.purpose.strip()
    recipient_email = payload.recipient.strip().lower()
    scope = payload.scope.strip()
    if not purpose or not recipient_email or not scope:
        raise HTTPException(
            status_code=422,
            detail="Consent recipient, purpose, and scope are required.",
        )

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

    if case.identity_mode not in {"identified", "restricted"}:
        raise HTTPException(
            status_code=403,
            detail="Identity disclosure consent cannot be granted for an anonymous case.",
        )

    # Consent is tied to the specific coordinator currently assigned to this case.
    coordinator = (
        db.query(models.User)
        .join(
            models.Case,
            models.Case.assigned_coordinator_id == models.User.id,
        )
        .filter(
            models.Case.id == case.id,
            models.User.role == "coordinator",
            models.User.email == recipient_email,
        )
        .first()
    )
    if coordinator is None:
        raise HTTPException(
            status_code=400,
            detail="Consent recipient must be the coordinator assigned to this case.",
        )

    consent = models.CaseConsent(
        case_id=case.id,
        granted_by_user_id=current_user.id,
        purpose=purpose,
        recipient=coordinator.email.strip().lower(),
        scope=scope,
        granted=True,
        granted_at=datetime.now(timezone.utc),
        withdrawn_at=None,
    )

    db.add(consent)
    db.add(
        models.CaseDisclosureAudit(
            case_id=case.id,
            actor_user_id=current_user.id,
            recipient=coordinator.email.strip().lower(),
            purpose=purpose,
            decision="consent_granted",
            reason="Student explicitly granted consent.",
        )
    )

    db.commit()

    return {"message": "Consent recorded successfully."}


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
        .filter(models.CaseConsent.case_id == case_id)
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
def check_case_disclosure_consent(
    db: Session,
    case_id: int,
    recipient: str,
    purpose: str,
    scope: str,
) -> bool:
    # Select the newest record first, including withdrawn records. Otherwise,
    # an older grant could incorrectly become active after a later withdrawal.
    consent = (
        db.query(models.CaseConsent)
        .join(
            models.Case,
            models.CaseConsent.case_id == models.Case.id,
        )
        .filter(
            models.CaseConsent.case_id == case_id,
            models.CaseConsent.recipient == recipient,
            models.CaseConsent.purpose == purpose,
            models.CaseConsent.scope == scope,
            models.CaseConsent.granted_by_user_id
            == models.Case.student_id,
        )
        .order_by(
            models.CaseConsent.created_at.desc(),
            models.CaseConsent.id.desc(),
        )
        .first()
    )

    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    granted_at = consent.granted_at if consent is not None else None
    if granted_at is not None and granted_at.tzinfo is None:
        granted_at = granted_at.replace(tzinfo=timezone.utc)

    return bool(
        case is not None
        and case.identity_mode in {"identified", "restricted"}
        and consent is not None
        and consent.granted
        and granted_at is not None
        and granted_at <= datetime.now(timezone.utc)
        and consent.withdrawn_at is None
    )

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
    """Return case-owner identity only to the assigned coordinator with active consent."""

    recipient = current_user.email.strip().lower()
    purpose = payload.purpose.strip()
    scope = payload.scope.strip()
    if not purpose or not scope:
        raise HTTPException(
            status_code=422,
            detail="Disclosure purpose and scope are required.",
        )

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

    # Match the latest consent for this exact case, coordinator, purpose and scope.
    consent = (
        db.query(models.CaseConsent)
        .filter(
            models.CaseConsent.case_id == case_id,
            models.CaseConsent.granted_by_user_id == case.student_id,
            models.CaseConsent.recipient == recipient,
            models.CaseConsent.purpose == purpose,
            models.CaseConsent.scope == scope,
        )
        .order_by(
            models.CaseConsent.created_at.desc(),
            models.CaseConsent.id.desc(),
        )
        .first()
    )

    granted_at = consent.granted_at if consent is not None else None
    if granted_at is not None and granted_at.tzinfo is None:
        granted_at = granted_at.replace(tzinfo=timezone.utc)

    allowed = bool(
        case.identity_mode in {"identified", "restricted"}
        and consent is not None
        and consent.granted
        and granted_at is not None
        and granted_at <= datetime.now(timezone.utc)
        and consent.withdrawn_at is None
    )

    record_disclosure_decision(
        db=db,
        case_id=case_id,
        actor_user_id=current_user.id,
        recipient=recipient,
        purpose=purpose,
        allowed=allowed,
        reason=(
            "Active consent matched coordinator, purpose, and scope."
            if allowed
            else "Disclosure denied: no active matching consent for this coordinator, purpose, and scope."
        ),
    )

    if not allowed:
        raise HTTPException(
            status_code=403,
            detail="Disclosure denied: active consent is required.",
        )

    student = (
        db.query(models.User)
        .filter(models.User.id == case.student_id)
        .first()
    )
    if student is None:
        # Do not return case data if the linked owner record is missing.
        raise HTTPException(status_code=404, detail="Case owner not found.")

    return {
        "case_id": case.id,
        "student_name": student.name,
        "student_email": student.email,
        "purpose": purpose,
        "scope": scope,
        "message": "Identity disclosure authorized by active consent.",
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
